#!/usr/bin/env python3
"""Explicit local CLI for WP1 data import; no implicit network activity."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT))
from urbanimpact.citypack.fetch import fetch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "build", "review"])
    parser.add_argument("--allow-egress", action="store_true")
    parser.add_argument("--source", choices=["osm", "gtfs", "all"], default="all")
    args = parser.parse_args()
    if args.command == "fetch":
        sources = ["osm", "gtfs"] if args.source == "all" else [args.source]
        result = [fetch(s, ROOT / "data/raw", allow_egress=args.allow_egress) for s in sources]
    elif args.command == "build":
        from urbanimpact.citypack.build import build

        result = build(ROOT)
    else:
        from urbanimpact.citypack.cases import review

        result = review(ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
