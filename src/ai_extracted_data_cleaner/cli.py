from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cleaner import clean_table


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean AI-extracted materials literature datasets.")
    sub = parser.add_subparsers(dest="command")

    clean = sub.add_parser("clean", help="Clean an Excel/CSV dataset")
    clean.add_argument("--input", required=True, help="Input .csv/.xlsx file")
    clean.add_argument("--outdir", required=True, help="Output directory")
    clean.add_argument("--aliases", default=None, help="Optional custom field_aliases.yaml")
    clean.add_argument("--rules", default=None, help="Optional custom validation_rules.yaml")

    args = parser.parse_args()
    if args.command == "clean":
        result = clean_table(
            Path(args.input),
            Path(args.outdir),
            alias_path=Path(args.aliases) if args.aliases else None,
            rules_path=Path(args.rules) if args.rules else None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
