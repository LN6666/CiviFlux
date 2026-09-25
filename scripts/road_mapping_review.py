"""Prepare or validate an independent review of R1 directed-edge candidates.

This command never accepts a review on behalf of a person. The generated form
is PENDING until an independent reviewer checks the notice, map and every
candidate edge. Validation checks provenance and completeness, not identity.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from urbanimpact.citypack.mapping_review import REVIEW_RELATIVE_PATH, review_template, validate_review

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--template", type=Path, metavar="OUTPUT_JSON")
    mode.add_argument("--validate", type=Path, metavar="REVIEW_JSON")
    args = parser.parse_args()
    if args.template is not None:
        if args.template.resolve() == (ROOT / REVIEW_RELATIVE_PATH).resolve():
            parser.error("a blank template cannot be saved as accepted review evidence")
        args.template.parent.mkdir(parents=True, exist_ok=True)
        if args.template.exists():
            parser.error("template destination exists; refusing to overwrite a review")
        args.template.write_text(json.dumps(review_template(ROOT), ensure_ascii=False, indent=2) + "\n")
        print(args.template)
    else:
        document = json.loads(args.validate.read_text())
        print(json.dumps(validate_review(ROOT, document), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
