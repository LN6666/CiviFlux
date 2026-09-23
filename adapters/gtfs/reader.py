from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

REQUIRED = {"stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def parse_gtfs_time(value: str) -> int:
    """Seconds since GTFS service-day origin; 25:10 is valid, 12:70 is not."""
    fields = value.split(":")
    if len(fields) != 3 or any(not f.isdigit() for f in fields):
        raise ValueError(f"invalid GTFS time {value!r}")
    h, m, s = map(int, fields)
    if m > 59 or s > 59 or h > 167:
        raise ValueError("GTFS time outside supported one-week horizon")
    return h * 3600 + m * 60 + s


def service_ids_on(day: date, calendar: list[dict], exceptions: list[dict]) -> set[str]:
    key = day.strftime("%Y%m%d")
    active = {
        r["service_id"]
        for r in calendar
        if r["start_date"] <= key <= r["end_date"] and r[WEEKDAYS[day.weekday()]] == "1"
    }
    for row in exceptions:
        if row["date"] == key:
            if row["exception_type"] == "1":
                active.add(row["service_id"])
            elif row["exception_type"] == "2":
                active.discard(row["service_id"])
            else:
                raise ValueError("unknown GTFS exception_type")
    return active


class Feed:
    def __init__(self, path: Path):
        self.archive = ZipFile(path)
        infos = self.archive.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise ValueError("duplicate GTFS ZIP member")
        if any(PurePosixPath(n).is_absolute() or ".." in PurePosixPath(n).parts or "\\" in n for n in names):
            raise ValueError("unsafe GTFS ZIP member path")
        if sum(i.file_size for i in infos) > 2_000_000_000 or any(i.file_size > 1_500_000_000 for i in infos):
            raise ValueError("GTFS uncompressed budget exceeded")
        if not REQUIRED.issubset(names) or not {"calendar.txt", "calendar_dates.txt"}.intersection(names):
            raise ValueError("missing required GTFS tables")
        self.names = names

    def rows(self, name):
        if name in self.names:
            with self.archive.open(name) as raw:
                with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
                    yield from csv.DictReader(text)

    def close(self):
        self.archive.close()


def inspect_feed(path: Path, bbox: list[float]) -> dict:
    """Retain ROI stops/routes/shapes and representative trips, inspect full time table."""
    feed = Feed(path)
    try:
        calendar = list(feed.rows("calendar.txt"))
        exceptions = list(feed.rows("calendar_dates.txt"))
        date_values = [r[k] for r in calendar for k in ["start_date", "end_date"]] + [
            r["date"] for r in exceptions
        ]
        if not date_values:
            raise ValueError("GTFS has no coverage dates")
        start, end = min(date_values), max(date_values)
        start_day = datetime.strptime(start, "%Y%m%d").date()
        end_day = datetime.strptime(end, "%Y%m%d").date()
        if (end_day - start_day).days > 732:
            raise ValueError("GTFS coverage exceeds bounded two-year inspection")
        active_days = sum(
            bool(service_ids_on(start_day + timedelta(days=i), calendar, exceptions))
            for i in range((end_day - start_day).days + 1)
        )
        stops = []
        for row in feed.rows("stops.txt"):
            if not row.get("stop_lon") or not row.get("stop_lat"):
                continue
            lon, lat = float(row["stop_lon"]), float(row["stop_lat"])
            if bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
                stops.append(
                    {
                        "id": "gtfs:stop:" + row["stop_id"],
                        "external_id": row["stop_id"],
                        "name": row["stop_name"],
                        "lon": lon,
                        "lat": lat,
                        "source_id": "S03-GTFS",
                        "location_type": row.get("location_type", "0"),
                    }
                )
        shapes = {}
        shape_point_count = 0
        for row in feed.rows("shapes.txt"):
            lon, lat = float(row["shape_pt_lon"]), float(row["shape_pt_lat"])
            if bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
                shapes.setdefault(row["shape_id"], []).append((int(row["shape_pt_sequence"]), lon, lat))
                shape_point_count += 1
                if shape_point_count > 1_000_000:
                    raise ValueError("ROI shape point budget exceeded")
        shape_ids = set(shapes)
        representative = {}
        relevant_trip_ids = set()
        relevant_routes = set()
        for row in feed.rows("trips.txt"):
            if row.get("shape_id") in shape_ids:
                relevant_trip_ids.add(row["trip_id"])
                relevant_routes.add(row["route_id"])
                key = (row["route_id"], row.get("direction_id", ""), row["shape_id"], row["service_id"])
                if key not in representative or row["trip_id"] < representative[key]["trip_id"]:
                    representative[key] = row
        routes = [
            {
                **r,
                "id": "gtfs:route:" + r["route_id"],
                "name": r.get("route_long_name") or r.get("route_short_name") or r["route_id"],
                "source_id": "S03-GTFS",
                "match_status": "candidate",
            }
            for r in feed.rows("routes.txt")
            if r["route_id"] in relevant_routes
        ]
        shape_routes = {}
        for row in representative.values():
            shape_routes.setdefault(row["shape_id"], set()).add(row["route_id"])
        overnight_count, max_seconds, time_rows = 0, 0, 0
        selected_trip_ids = {r["trip_id"] for r in representative.values()}
        selected_stop_times = []
        for row in feed.rows("stop_times.txt"):
            time_rows += 1
            for field in ["arrival_time", "departure_time"]:
                if row.get(field):
                    seconds = parse_gtfs_time(row[field])
                    max_seconds = max(seconds, max_seconds)
                    overnight_count += seconds >= 86400
            if row["trip_id"] in selected_trip_ids:
                selected_stop_times.append(
                    {
                        k: row[k]
                        for k in ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"]
                    }
                )
        return {
            "source_id": "S03-GTFS",
            "temporality": "current_schedule",
            "coverage": {
                "start_date": start_day.isoformat(),
                "end_date": end_day.isoformat(),
                "active_service_days": active_days,
                "calendar_exceptions": len(exceptions),
                "times_over_24h": overnight_count,
                "maximum_time_seconds": max_seconds,
                "stop_time_rows_inspected": time_rows,
                "historical_case_dates": {
                    "2026-05-15": bool(service_ids_on(date(2026, 5, 15), calendar, exceptions)),
                    "2026-05-23": bool(service_ids_on(date(2026, 5, 23), calendar, exceptions)),
                },
            },
            "stops": sorted(stops, key=lambda x: x["id"]),
            "routes": sorted(routes, key=lambda x: x["route_id"]),
            "representative_trips": sorted(representative.values(), key=lambda x: x["trip_id"]),
            "representative_stop_times": selected_stop_times,
            "total_relevant_trips": len(relevant_trip_ids),
            "calendar": calendar,
            "calendar_dates": exceptions,
            "shapes": [
                {
                    "shape_id": sid,
                    "route_ids": sorted(shape_routes.get(sid, set())),
                    "coordinates": [[x[1], x[2]] for x in sorted(points)],
                    "geometry_status": "roi_clipped_not_full_trip",
                }
                for sid, points in sorted(shapes.items())
            ],
            "shape_match_status": "candidate_only_no_verified_road_matching",
            "historical_transit_validation": "NOT_VALIDATED",
        }
    finally:
        feed.close()
