"""Capture Berlin's official traffic feeds and build a local GIS comparison bundle.

The frozen route probe is the prediction. VIZ traffic and closure reports are
independent display layers. Raw VIZ responses stay ignored until redistribution
rights and event-hour observation semantics have been checked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from shapely.geometry import LineString
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from urbanimpact.citypack.fetch import sha256_file

CITY = ROOT / "data/citypacks/berlin-marathon-2026/citypack.json"
PROBE = ROOT / "evidence/events/berlin-2026-incremental-pre-onset-probe.json"
CANDIDATES = ROOT / "data/event_cases/berlin-marathon-2026-closure-candidates.json"
RAW = ROOT / "data/raw/berlin-validation"
LOCAL_BUNDLE = ROOT / "web/public/validation/berlin-local.json"
BBOX = (13.33, 52.50, 13.44, 52.55)
TRAFFIC_URL = "https://api.viz.berlin.de/geoserver/mdh/ows"
REPORT_URL = "https://api.viz.berlin.de/tic3/baustellen_sperrungen_tic.json"
INCREMENTAL_ONSET = datetime.fromisoformat("2026-09-26T05:00:00+00:00")
MAX_FEED_AGE_S = 900


def _collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def _metric_line(coordinates: list[list[float]]) -> LineString:
    # Local Berlin equirectangular projection, used only for short segment
    # matching. Scores retain the original WGS84 geometries for map display.
    return transform(lambda x, y, z=None: (x * 67650.0, y * 111130.0), LineString(coordinates))


def _same_direction(first: LineString, second: LineString) -> bool:
    ax = first.coords[-1][0] - first.coords[0][0]
    ay = first.coords[-1][1] - first.coords[0][1]
    bx = second.coords[-1][0] - second.coords[0][0]
    by = second.coords[-1][1] - second.coords[0][1]
    norm = (ax * ax + ay * ay) ** 0.5 * (bx * bx + by * by) ** 0.5
    return norm > 0 and (ax * bx + ay * by) / norm >= 0.5


def _unique_features(features: list[dict], label: str) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for feature in features:
        key = feature["properties"].get("unique_id")
        if not isinstance(key, str) or not key or key in indexed:
            raise ValueError(f"{label} has missing or duplicate VIZ unique_id")
        indexed[key] = feature
    return indexed


def _receipt_feed_time(receipt: dict, label: str) -> tuple[datetime, int]:
    """Require fresh, timezone-aware traffic bytes before scoring a live pair."""
    captured = datetime.fromisoformat(receipt["captured_at_utc"])
    feed = datetime.fromisoformat(receipt["traffic"]["feed_time_stamp"])
    if captured.tzinfo is None or feed.tzinfo is None:
        raise ValueError(f"{label} traffic timestamp lacks timezone")
    age_s = round((captured - feed).total_seconds())
    if not -120 <= age_s <= MAX_FEED_AGE_S:
        raise ValueError(f"{label} traffic feed is stale or future-dated: {age_s} s")
    return feed, age_s


def _comparison_timing(baseline: dict, event: dict) -> dict:
    baseline_feed, baseline_age = _receipt_feed_time(baseline, "baseline")
    event_feed, event_age = _receipt_feed_time(event, "event")
    baseline_capture = datetime.fromisoformat(baseline["captured_at_utc"])
    event_capture = datetime.fromisoformat(event["captured_at_utc"])
    if not baseline_capture < INCREMENTAL_ONSET <= event_capture:
        raise ValueError("capture times do not straddle the announced onset")
    if not baseline_feed < INCREMENTAL_ONSET <= event_feed:
        raise ValueError("traffic feed timestamps do not straddle the announced onset")
    if event_feed <= baseline_feed:
        raise ValueError("event feed must follow baseline feed")
    return {
        "announced_onset_utc": INCREMENTAL_ONSET.isoformat(),
        "baseline_feed_utc": baseline_feed.isoformat(),
        "event_feed_utc": event_feed.isoformat(),
        "baseline_feed_age_s": baseline_age,
        "event_feed_age_s": event_age,
        "maximum_allowed_feed_age_s": MAX_FEED_AGE_S,
    }


def compare_snapshots(predicted: list[dict], before: list[dict], after: list[dict]) -> tuple[list[dict], dict]:
    """Score matched VIZ segments; unknown/unmatched segments are not negatives."""
    prediction_lines = [_metric_line(f["geometry"]["coordinates"]) for f in predicted]
    prediction_area = unary_union([line.buffer(18) for line in prediction_lines])
    evaluation_area = prediction_area.buffer(1000)
    earlier = _unique_features(before, "baseline")
    later = _unique_features(after, "event")
    observed = []
    covered_predictions: set[int] = set()
    counts = {"hit": 0, "miss": 0, "false_alarm": 0, "correct_negative": 0, "unscored": 0}
    for feature in after:
        props = feature["properties"]
        key = props["unique_id"]
        geometry = _metric_line(feature["geometry"]["coordinates"])
        if not geometry.intersects(evaluation_area):
            continue
        matches = [
            index for index, line in enumerate(prediction_lines)
            if line.distance(geometry) <= 18
            and _same_direction(line, geometry)
            and line.buffer(18).intersection(geometry).length >= min(geometry.length * 0.25, 25)
        ]
        aligned = bool(matches)
        covered_predictions.update(matches)
        old = earlier.get(key)
        old_p = old["properties"] if old else {}
        old_geometry = _metric_line(old["geometry"]["coordinates"]) if old else None
        old_speed = old_p.get("speedavg")
        new_speed = props.get("speedavg")
        if old is None:
            change = "unscored_missing_baseline"
            slowdown = None
        elif not _same_direction(old_geometry, geometry) or old_geometry.hausdorff_distance(geometry) > 25:
            change = "unscored_geometry_changed"
            slowdown = None
        elif old_p.get("closed") != 1 and props.get("closed") == 1:
            change = "newly_reported_closed"
            slowdown = None
        elif old_p.get("closed") == 1 or props.get("closed") == 1:
            change = "unscored_preexisting_closure"
            slowdown = None
        elif not isinstance(old_speed, (int, float)) or not isinstance(new_speed, (int, float)) or old_speed <= 0 or new_speed <= 0:
            change = "unscored_missing_speed"
            slowdown = None
        else:
            slowdown = (old_speed - new_speed) / old_speed
            change = "speed_drop_30pct" if slowdown >= 0.3 else "no_large_speed_drop"
        if change.startswith("unscored"):
            verdict = "unscored"
        elif change in {"newly_reported_closed", "speed_drop_30pct"}:
            verdict = "hit" if aligned else "miss"
        else:
            verdict = "false_alarm" if aligned else "correct_negative"
        counts[verdict] += 1
        observed.append({
            "type": "Feature",
            "geometry": feature["geometry"],
            "properties": {
                "unique_id": key,
                "predicted_overlap": aligned,
                "change_class": change,
                "verdict": verdict,
                "baseline_speed_kph": old_speed,
                "event_speed_kph": new_speed,
                "slowdown_fraction": slowdown,
                "baseline_closed": old_p.get("closed"),
                "event_closed": props.get("closed"),
            },
        })
    for key, feature in earlier.items():
        event_feature = later.get(key)
        if event_feature and _metric_line(event_feature["geometry"]["coordinates"]).intersects(evaluation_area):
            continue
        geometry = _metric_line(feature["geometry"]["coordinates"])
        if not geometry.intersects(evaluation_area):
            continue
        event_props = event_feature["properties"] if event_feature else {}
        counts["unscored"] += 1
        observed.append({
            "type": "Feature",
            "geometry": feature["geometry"],
            "properties": {
                "unique_id": key,
                "predicted_overlap": None,
                "change_class": "unscored_geometry_moved_out" if event_feature else "unscored_missing_event",
                "verdict": "unscored",
                "baseline_speed_kph": feature["properties"].get("speedavg"),
                "event_speed_kph": event_props.get("speedavg"),
                "slowdown_fraction": None,
                "baseline_closed": feature["properties"].get("closed"),
                "event_closed": event_props.get("closed"),
            },
        })
    positive = counts["hit"] + counts["false_alarm"]
    actual = counts["hit"] + counts["miss"]
    metrics = {
        **counts,
        "comparison_unit": "VIZ directed unique_id segment",
        "scored_segments": sum(counts.values()) - counts["unscored"],
        "predicted_edge_count": len(prediction_lines),
        "predicted_edges_with_viz_match": len(covered_predictions),
        "predicted_edges_without_viz_match": len(prediction_lines) - len(covered_predictions),
        "matched_prediction_indices": sorted(covered_predictions),
        "matched_viz_segments": sum(f["properties"]["predicted_overlap"] is True for f in observed),
        "scored_matched_viz_segments": sum(
            f["properties"]["predicted_overlap"] is True and f["properties"]["verdict"] != "unscored"
            for f in observed
        ),
        "precision": counts["hit"] / positive if positive else None,
        "recall": counts["hit"] / actual if actual else None,
        "rule": "Within 1 km of the frozen predicted paths; same travel direction (endpoint cosine >=0.5), geometric overlap within 18 m and at least min(25 m,25%) of VIZ segment; newly reported closure or >=30% lower positive nonclosed speed is a change. Different-hour snapshots cannot isolate the event effect.",
    }
    return observed, metrics


def _within(geometry: list[list[float]], bbox: tuple[float, ...] = BBOX) -> bool:
    xmin, ymin, xmax, ymax = bbox
    return any(xmin <= point[0] <= xmax and ymin <= point[1] <= ymax for point in geometry)


def _download(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "CiviFlux/0.1 (open-source event validation)"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError(f"official source HTTP {response.status}")
        return response.read(), response.headers.get("Date", "")


def capture(name: str) -> dict:
    if not name.isascii() or not name.replace("-", "").isalnum() or len(name) > 48:
        raise ValueError("name must be a short ASCII alphanumeric/hyphen label")
    RAW.mkdir(parents=True, exist_ok=True)
    traffic_path = RAW / f"{name}-traffic.json"
    reports_path = RAW / f"{name}-reports.json"
    receipt_path = RAW / f"{name}-receipt.json"
    if any(path.exists() for path in (traffic_path, reports_path, receipt_path)):
        raise FileExistsError("snapshot name already exists; captures are immutable")
    query = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "mdh:vmzlos-step",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "bbox": ",".join(map(str, BBOX)) + ",EPSG:4326",
        "count": "10000",
    }
    traffic_url = TRAFFIC_URL + "?" + urllib.parse.urlencode(query)
    traffic_bytes, traffic_http_date = _download(traffic_url)
    reports_bytes, reports_http_date = _download(REPORT_URL)
    traffic = json.loads(traffic_bytes)
    reports = json.loads(reports_bytes)
    if traffic.get("type") != "FeatureCollection" or reports.get("type") != "FeatureCollection":
        raise ValueError("official source did not return GeoJSON")
    if traffic.get("numberMatched", 0) > 10000 or not traffic.get("features"):
        raise ValueError("traffic bbox response missing or truncated")
    for feature in traffic["features"]:
        props = feature.get("properties", {})
        if feature.get("geometry", {}).get("type") != "LineString" or "unique_id" not in props:
            raise ValueError("traffic feed schema changed")
    captured_at = datetime.now(UTC).isoformat()
    receipt = {
        "captured_at_utc": captured_at,
        "traffic": {
            "url": traffic_url,
            "http_date": traffic_http_date,
            "feed_time_stamp": traffic.get("timeStamp"),
            "sha256": hashlib.sha256(traffic_bytes).hexdigest(),
            "feature_count": len(traffic["features"]),
            "local_path": str(traffic_path.relative_to(ROOT)),
        },
        "reports": {
            "url": REPORT_URL,
            "http_date": reports_http_date,
            "sha256": hashlib.sha256(reports_bytes).hexdigest(),
            "feature_count": len(reports["features"]),
            "local_path": str(reports_path.relative_to(ROOT)),
        },
        "interpretation": "VIZ live traffic fields are a time-stamped service snapshot. A zero speed on a closed link is not a measured speed. VIZ closure reports may be scheduled and are not proof of field execution.",
    }
    traffic_path.write_bytes(traffic_bytes)
    reports_path.write_bytes(reports_bytes)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


def build(snapshot_name: str, output: Path = LOCAL_BUNDLE, event_name: str | None = None) -> dict:
    receipt_path = RAW / f"{snapshot_name}-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    traffic_path = ROOT / receipt["traffic"]["local_path"]
    reports_path = ROOT / receipt["reports"]["local_path"]
    if sha256_file(traffic_path) != receipt["traffic"]["sha256"] or sha256_file(reports_path) != receipt["reports"]["sha256"]:
        raise ValueError("snapshot bytes changed after capture")
    city_path, probe_path, candidates_path = CITY, PROBE, CANDIDATES
    city = json.loads(city_path.read_text())
    probe = json.loads(probe_path.read_text())
    candidates = json.loads(candidates_path.read_text())
    if sha256_file(city_path) != probe["citypack_sha256"] or sha256_file(candidates_path) != probe["closure_candidates_sha256"]:
        raise ValueError("prediction no longer matches frozen city/candidate inputs")
    edges = {edge["id"]: edge for edge in city["edges"]}
    changed = [
        route for route in probe["routes"]
        if route["known_active_candidate_arm"] != route["active_plus_upcoming_candidate_arm"]
    ]
    affected_ids = {edge_id for route in changed for edge_id in route["known_active_candidate_arm"]["edge_ids"]}
    candidate_ids = {edge_id for case in candidates["cases"] for edge_id in case["candidate_directed_edge_ids"]}
    if not affected_ids or not affected_ids <= edges.keys() or not candidate_ids <= edges.keys():
        raise ValueError("frozen prediction references unknown roads")

    def road_feature(edge_id: str, layer: str) -> dict:
        edge = edges[edge_id]
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": edge["geometry"]},
            "properties": {
                "id": edge_id,
                "name": edge["name"],
                "layer": layer,
                "source_id": edge["source_id"],
                "route_labels": [r["label"] for r in changed if edge_id in r["known_active_candidate_arm"]["edge_ids"]],
            },
        }

    # A sparse visual context keeps the browser responsive. The comparison
    # layers below always retain every frozen candidate and prediction edge.
    context = [
        road_feature(eid, "context") for eid, e in edges.items()
        if e["geometry"] and e["name"] and e["length_m"] >= 50 and _within(e["geometry"])
    ]
    traffic = json.loads(traffic_path.read_text())
    predicted = [road_feature(eid, "predicted_route_impact") for eid in sorted(affected_ids)]
    _, pre_event_coverage = compare_snapshots(predicted, traffic["features"], traffic["features"])
    if pre_event_coverage["hit"] or pre_event_coverage["miss"]:
        raise ValueError("same-snapshot spatial control reported a traffic change")
    covered_indices = set(pre_event_coverage["matched_prediction_indices"])
    for index, feature in enumerate(predicted):
        feature["properties"]["viz_baseline_coverage"] = index in covered_indices
    report_source = json.loads(reports_path.read_text())
    reports = [
        feature for feature in report_source["features"]
        if "marathon" in str(feature.get("properties", {}).get("content", "")).lower()
    ]
    event_receipt = None
    observed_change: list[dict] = []
    comparison_metrics = None
    if event_name:
        event_receipt = json.loads((RAW / f"{event_name}-receipt.json").read_text())
        event_traffic_path = ROOT / event_receipt["traffic"]["local_path"]
        if sha256_file(event_traffic_path) != event_receipt["traffic"]["sha256"]:
            raise ValueError("event traffic bytes changed after capture")
        timing = _comparison_timing(receipt, event_receipt)
        event_traffic = json.loads(event_traffic_path.read_text())
        observed_change, comparison_metrics = compare_snapshots(
            predicted,
            traffic["features"],
            event_traffic["features"],
        )
        comparison_metrics["timing"] = timing
    bundle = {
        "schema_version": "civiflux-validation-map-v1",
        "event_id": "berlin-marathon-2026",
        "prediction_frozen_at_utc": probe["frozen_at_utc"],
        "prediction_sha256": sha256_file(probe_path),
        "citypack_sha256": sha256_file(city_path),
        "observation_snapshot": receipt,
        "event_snapshot": event_receipt,
        "status": "TWO_SNAPSHOT_SPATIAL_COMPARISON" if event_receipt else "PRE_EVENT_BASELINE_ONLY",
        "comparison_metrics": comparison_metrics,
        "pre_event_coverage": {
            "predicted_edges_with_viz_match": pre_event_coverage["predicted_edges_with_viz_match"],
            "predicted_edges_without_viz_match": pre_event_coverage["predicted_edges_without_viz_match"],
            "matched_viz_segments": pre_event_coverage["matched_viz_segments"],
            "scored_matched_viz_segments": pre_event_coverage["scored_matched_viz_segments"],
            "interpretation": "Spatial observation coverage only, frozen from the baseline feed; unmatched prediction edges cannot be scored as hits or false alarms.",
        },
        "counts": {
            "context_roads": len(context),
            "predicted_route_impact_edges": len(affected_ids),
            "restriction_input_edges": len(candidate_ids),
            "traffic_segments": len(traffic["features"]),
            "marathon_reports": len(reports),
        },
        "layers": {
            "context_roads": _collection(context),
            "predicted_route_impact": _collection(predicted),
            "restriction_inputs": _collection([road_feature(eid, "restriction_input") for eid in sorted(candidate_ids)]),
            "viz_traffic": _collection(traffic["features"]),
            "viz_marathon_reports": _collection(reports),
            "observed_change": _collection(observed_change),
        },
        "comparison_note": "The orange paths are frozen plugin routing outputs for two declared OD pairs, not closure inputs. Purple paths are announcement-derived restriction inputs. The VIZ speed/LOS layer is a pre-onset baseline here. Two-snapshot spatial scores are descriptive and cannot isolate event causation from time-of-day or other changes.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + "\n")
    return {"output": str(output), "counts": bundle["counts"], "status": bundle["status"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("name")
    build_parser = sub.add_parser("build")
    build_parser.add_argument("snapshot_name")
    build_parser.add_argument("--event-name")
    build_parser.add_argument("--output", type=Path, default=LOCAL_BUNDLE)
    args = parser.parse_args()
    result = capture(args.name) if args.command == "capture" else build(args.snapshot_name, args.output, args.event_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
