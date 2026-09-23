#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["freeze", "ablate", "benchmark", "report", "external"])
    args = parser.parse_args()
    if args.command == "freeze":
        from experiments.dataset import freeze

        result = freeze(ROOT)
    elif args.command == "ablate":
        from experiments.evaluation import ablate

        result = ablate(ROOT)
    elif args.command == "benchmark":
        from experiments.evaluation import benchmark

        result = benchmark(ROOT)
    elif args.command == "external":
        from experiments.external import reproduce

        result = reproduce(ROOT)
    else:
        from experiments.reporting import report

        result = report(ROOT)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("status", "").startswith("FAIL"):
        sys.exit(1)


if __name__ == "__main__":
    main()
