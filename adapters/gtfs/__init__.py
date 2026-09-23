"""GTFS schedule ingestion without pretending current feeds are historical."""

from .reader import inspect_feed, parse_gtfs_time, service_ids_on

__all__ = ["inspect_feed", "service_ids_on", "parse_gtfs_time"]
