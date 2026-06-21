from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_extracted_data_cleaner.cleaner import clean_table  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean AI-extracted materials literature data.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()
    result = clean_table(args.input, args.outdir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
