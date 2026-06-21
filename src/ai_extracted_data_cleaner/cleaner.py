from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .duplicates import detect_duplicates
from .fields import build_column_map, schema_state
from .report import build_quality_report, paper_level_audit
from .units import NUMERIC_FIELDS, normalize_value
from .utils import ensure_dir, write_json
from .validators import validate_dataframe


def read_table(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(p)
    if p.suffix.lower() in {".csv", ".txt"}:
        return pd.read_csv(p)
    raise ValueError(f"Unsupported input file type: {p.suffix}")


def clean_table(input_path: str | Path, outdir: str | Path) -> dict[str, Any]:
    out = ensure_dir(outdir)
    state_dir = ensure_dir(out / "state")

    raw = read_table(input_path)
    columns = list(raw.columns)
    column_map, unknown = build_column_map(columns)
    write_json(state_dir / "01_schema_map.json", schema_state(columns, column_map, unknown))

    df = raw.rename(columns=column_map).copy()
    # If multiple columns map to same canonical name, keep first and suffix duplicates.
    df = _deduplicate_columns(df)

    corrections: list[dict[str, Any]] = []
    for field in list(df.columns):
        if field in NUMERIC_FIELDS:
            cleaned_values = []
            for idx, value in df[field].items():
                cleaned, corr = normalize_value(field, value)
                cleaned_values.append(cleaned)
                if corr:
                    corr.update({
                        "row_index": int(idx),
                        "paper_id": str(df.loc[idx, "paper_id"]) if "paper_id" in df.columns else "",
                        "sample_id": str(df.loc[idx, "sample_id"]) if "sample_id" in df.columns else "",
                    })
                    corrections.append(corr)
            df[field] = cleaned_values

    unit_state = {
        "agent": "unit_agent",
        "version": "1.0.0",
        "summary": {
            "n_rows": len(df),
            "n_numeric_fields": len([c for c in df.columns if c in NUMERIC_FIELDS]),
            "n_corrections": len(corrections),
        },
        "corrections_preview": corrections[:50],
    }
    write_json(state_dir / "02_unit_normalized.json", unit_state)

    physics_flags = validate_dataframe(df)
    write_json(state_dir / "03_physics_flags.json", {
        "agent": "physics_agent",
        "version": "1.0.0",
        "summary": _count_flags(physics_flags),
        "records": physics_flags,
    })

    duplicate_flags = detect_duplicates(df)
    write_json(state_dir / "04_duplicate_flags.json", {
        "agent": "duplicate_agent",
        "version": "1.0.0",
        "summary": _count_flags(duplicate_flags),
        "records": duplicate_flags,
    })

    all_flags = physics_flags + duplicate_flags
    review_queue = pd.DataFrame(all_flags)
    if not review_queue.empty:
        severity_order = {"P0": 0, "P1": 1, "P2": 2}
        review_queue["_order"] = review_queue["risk_level"].map(severity_order).fillna(9)
        review_queue = review_queue.sort_values(["_order", "paper_id", "sample_id", "row_index"]).drop(columns=["_order"])

    df.to_csv(out / "cleaned_database.csv", index=False, encoding="utf-8-sig")
    review_queue.to_csv(out / "flagged_records.csv", index=False, encoding="utf-8-sig")
    review_queue.to_csv(out / "secondary_review_queue.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(corrections).to_csv(out / "correction_log.csv", index=False, encoding="utf-8-sig")
    paper_level_audit(all_flags).to_csv(out / "paper_level_audit.csv", index=False, encoding="utf-8-sig")

    report = build_quality_report(len(raw), len(raw.columns), all_flags, corrections, unknown)
    (out / "data_quality_report.md").write_text(report, encoding="utf-8")
    write_json(state_dir / "05_review_queue_state.json", {
        "agent": "review_queue_agent",
        "version": "1.0.0",
        "summary": {
            "n_flags": len(all_flags),
            "n_corrections": len(corrections),
            "decision": "NOT_READY" if any(f["risk_level"] == "P0" for f in all_flags) else "REVIEW_NEEDED" if any(f["risk_level"] == "P1" for f in all_flags) else "PASS_WITH_NOTES",
        },
        "outputs": [
            "cleaned_database.csv",
            "flagged_records.csv",
            "secondary_review_queue.csv",
            "paper_level_audit.csv",
            "correction_log.csv",
            "data_quality_report.md",
        ],
    })

    return {
        "outdir": str(out),
        "n_rows": len(df),
        "n_flags": len(all_flags),
        "n_corrections": len(corrections),
    }


def _deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    seen: dict[str, int] = {}
    new_cols = []
    for col in df.columns:
        count = seen.get(col, 0)
        if count == 0:
            new_cols.append(col)
        else:
            new_cols.append(f"{col}__duplicate_{count}")
        seen[col] = count + 1
    df.columns = new_cols
    return df


def _count_flags(flags: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"P0": 0, "P1": 0, "P2": 0, "total": len(flags)}
    for f in flags:
        if f.get("risk_level") in counts:
            counts[f["risk_level"]] += 1
    return counts
