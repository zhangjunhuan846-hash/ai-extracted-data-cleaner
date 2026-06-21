#!/usr/bin/env python3
"""
Baseline cleaner for AI-extracted scientific sample-level data.

Design stance:
- Preserve raw data.
- Normalize common numeric fields.
- Flag suspicious values, duplicates, missing conditions, outliers, and paper-level dominance.
- Do not silently delete rows.

Dependencies:
    pip install pandas numpy openpyxl pyyaml
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


DEFAULT_RULES: Dict[str, Any] = {
    "ranges": {
        "carbonization_temp_C": {"impossible_min": 100, "warning_min": 300, "warning_max": 1300, "impossible_max": 2500},
        "BET_m2_g": {"impossible_min": 0, "warning_min": 1, "warning_max": 3500, "impossible_max": 5000},
        "total_pore_volume_cm3_g": {"impossible_min": 0, "warning_max": 3.0, "impossible_max": 6.0},
        "micropore_volume_cm3_g": {"impossible_min": 0, "warning_max": 2.0, "impossible_max": 5.0},
        "d002_nm": {"impossible_min": 0.30, "warning_min": 0.335, "warning_max": 0.430, "impossible_max": 0.80},
        "ID_IG": {"impossible_min": 0, "warning_min": 0.2, "warning_max": 2.5, "impossible_max": 5.0},
        "N_at_percent": {"impossible_min": 0, "warning_max": 15, "impossible_max": 40},
        "O_at_percent": {"impossible_min": 0, "warning_max": 35, "impossible_max": 60},
        "ash_wt_percent": {"impossible_min": 0, "warning_max": 40, "impossible_max": 100},
        "ICE_percent": {"impossible_min": 0, "warning_min": 20, "warning_max": 100, "impossible_max": 120},
        "reversible_capacity_mAh_g": {"impossible_min": 0, "warning_max": 1500, "impossible_max": 3000},
        "specific_capacitance_F_g": {"impossible_min": 0, "warning_max": 800, "impossible_max": 1500},
        "retention_percent": {"impossible_min": 0, "warning_max": 120, "impossible_max": 200},
        "mass_loading_mg_cm2": {"impossible_min": 0, "warning_min": 0.1, "warning_max": 20, "impossible_max": 100},
        "electrode_thickness_um": {"impossible_min": 0, "warning_min": 5, "warning_max": 500, "impossible_max": 5000},
        "compaction_density_g_cm3": {"impossible_min": 0, "warning_min": 0.05, "warning_max": 2.0, "impossible_max": 5.0},
    },
    "system_required_fields": {
        "LIB": ["electrolyte", "current_density", "voltage_window", "ICE_percent"],
        "SIB": ["electrolyte", "current_density", "voltage_window", "ICE_percent"],
        "SC_AQUEOUS": ["electrolyte", "current_density", "voltage_window", "specific_capacitance_F_g"],
    },
}

ALIASES: Dict[str, List[str]] = {
    "paper_id": ["paper", "ref", "reference", "article_id", "paper id"],
    "doi": ["doi", "doi_url"],
    "title": ["title", "paper_title", "article_title"],
    "year": ["year", "publication_year", "pub_year"],
    "sample_id": ["sample_id", "sample", "record_id", "material_id", "id"],
    "sample_name": ["sample_name", "material", "sample_label", "carbon_name", "sample name"],
    "system": ["system", "application", "device", "battery_type", "type"],
    "electrolyte": ["electrolyte", "electrolyte_solution"],
    "voltage_window": ["voltage_window", "voltage", "window"],
    "current_density": ["current_density", "current", "rate", "current density"],
    "carbonization_temp_C": ["carbonization_temp", "carbonization temperature", "pyrolysis temp", "pyrolysis temperature", "temp", "temperature", "T"],
    "carbonization_time_h": ["carbonization_time", "time", "hold time", "holding time"],
    "BET_m2_g": ["BET", "SSA", "specific surface area", "surface area", "BET surface area"],
    "total_pore_volume_cm3_g": ["total pore volume", "pore volume", "Vtot", "total_pore_volume"],
    "micropore_volume_cm3_g": ["micropore volume", "Vmic", "micropore_volume"],
    "d002_nm": ["d002", "d-spacing", "interlayer spacing", "d 002"],
    "ID_IG": ["ID/IG", "I_D/I_G", "Raman", "D/G", "ID IG"],
    "N_at_percent": ["N at%", "N content", "nitrogen", "N_at_percent", "N%"],
    "O_at_percent": ["O at%", "O content", "oxygen", "O_at_percent", "O%"],
    "ash_wt_percent": ["ash", "ash content", "ash_wt_percent"],
    "mass_loading_mg_cm2": ["mass loading", "loading", "areal loading"],
    "electrode_thickness_um": ["thickness", "electrode thickness"],
    "compaction_density_g_cm3": ["density", "compaction density", "tap density"],
    "ICE_percent": ["ICE", "initial coulombic efficiency", "first-cycle CE", "coulombic efficiency"],
    "reversible_capacity_mAh_g": ["capacity", "specific capacity", "reversible capacity", "mAh/g"],
    "specific_capacitance_F_g": ["capacitance", "specific capacitance", "Csp", "F/g"],
    "retention_percent": ["retention", "capacity retention", "capacitance retention"],
    "cycle_number": ["cycle", "cycles", "cycle number"],
    "source_page": ["page", "source_page", "pages"],
    "source_table": ["table", "figure", "source_table"],
    "source_text": ["evidence", "quote", "source_text", "extracted sentence", "text"],
    "ai_confidence": ["confidence", "ai_confidence", "extraction_confidence"],
}

NUMERIC_FIELDS = set(DEFAULT_RULES["ranges"].keys()) | {"year", "carbonization_time_h", "cycle_number", "ai_confidence"}
ID_FIELDS = ["paper_id", "doi", "title", "sample_id", "sample_name", "system"]


def normalize_col(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def build_column_map(columns: Iterable[str]) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
    normalized = {col: normalize_col(col) for col in columns}
    mapping: Dict[str, str] = {}
    report: List[Dict[str, str]] = []
    used_raw = set()

    for canonical, aliases in ALIASES.items():
        candidates = [canonical] + aliases
        norm_candidates = [normalize_col(x) for x in candidates]
        best: Optional[str] = None
        reason = ""
        for col, ncol in normalized.items():
            if col in used_raw:
                continue
            if ncol in norm_candidates:
                best = col
                reason = "exact_alias_match"
                break
        if best is None:
            for col, ncol in normalized.items():
                if col in used_raw:
                    continue
                if any(alias in ncol or ncol in alias for alias in norm_candidates if len(alias) >= 3):
                    best = col
                    reason = "partial_alias_match"
                    break
        if best is not None:
            mapping[best] = canonical
            used_raw.add(best)
            report.append({"raw_column": best, "canonical_field": canonical, "confidence": "high" if reason == "exact_alias_match" else "medium", "reason": reason})

    for col in columns:
        if col not in used_raw:
            safe = "raw_extra_" + re.sub(r"[^A-Za-z0-9_]+", "_", str(col)).strip("_")[:60]
            mapping[col] = safe
            report.append({"raw_column": col, "canonical_field": safe, "confidence": "low", "reason": "unmapped_preserved"})
    return mapping, report


def read_input(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    if path.suffix.lower() == ".tsv":
        return pd.read_csv(path, sep="\t")
    return pd.read_csv(path)


def extract_first_number(value: Any) -> Tuple[float, List[str]]:
    flags: List[str] = []
    if pd.isna(value):
        return np.nan, flags
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value), flags
    text = str(value).strip()
    if not text:
        return np.nan, flags
    low = text.lower()
    if any(x in low for x in ["~", "ca.", "approx", "about", "around"]):
        flags.append("APPROXIMATE_VALUE")
    range_match = re.search(r"([-+]?\d*\.?\d+)\s*[–\-~]\s*([-+]?\d*\.?\d+)", text)
    if range_match:
        a, b = float(range_match.group(1)), float(range_match.group(2))
        flags.append("RANGE_VALUE")
        return (a + b) / 2.0, flags
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text.replace(",", ""))
    if not nums:
        flags.append("NUMERIC_PARSE_FAILED")
        return np.nan, flags
    if len(nums) > 1:
        flags.append("MULTIPLE_NUMBERS_IN_CELL")
    return float(nums[0]), flags


def normalize_units(field: str, raw_value: Any, num_value: float) -> Tuple[float, List[str], str]:
    flags: List[str] = []
    note = ""
    if pd.isna(num_value):
        return num_value, flags, note
    text = "" if pd.isna(raw_value) else str(raw_value).lower()
    val = float(num_value)

    if field == "d002_nm":
        # Common extraction issue: d002 reported in Angstrom as 3.6 Å, should be 0.36 nm.
        if "å" in text or "angstrom" in text or "ang" in text or val > 1.0:
            if val > 1.0:
                val = val / 10.0
                flags.append("UNIT_CONVERTED")
                note = "Converted likely Å to nm for d002."
    elif field == "mass_loading_mg_cm2":
        if "g cm" in text or "g/cm" in text:
            val = val * 1000.0
            flags.append("UNIT_CONVERTED")
            note = "Converted g/cm2 to mg/cm2."
    elif field == "electrode_thickness_um":
        if "mm" in text and "μm" not in text and "um" not in text:
            val = val * 1000.0
            flags.append("UNIT_CONVERTED")
            note = "Converted mm to µm."
    elif field in {"ICE_percent", "retention_percent", "N_at_percent", "O_at_percent", "ash_wt_percent"}:
        # Values like 0.72 may mean 72% if percent symbol absent.
        if 0 < val <= 1.0 and "%" not in text and "percent" not in text:
            val = val * 100.0
            flags.append("UNIT_SCALE_SUSPECT")
            note = "Fraction-like value converted to percent; manually verify."
    return val, flags, note


def add_flag(row_flags: Dict[int, List[str]], idx: int, flag: str) -> None:
    if flag and flag not in row_flags.setdefault(idx, []):
        row_flags[idx].append(flag)


def add_review(reviews: List[Dict[str, Any]], df: pd.DataFrame, idx: int, priority: str, field: str, raw_value: Any, normalized_value: Any, flag: str, reason: str, check: str) -> None:
    row = df.loc[idx]
    reviews.append({
        "priority": priority,
        "row_index": idx,
        "paper_id": row.get("paper_id", ""),
        "doi": row.get("doi", ""),
        "title": row.get("title", ""),
        "sample_id": row.get("sample_id", ""),
        "sample_name": row.get("sample_name", ""),
        "system": row.get("system", ""),
        "field": field,
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "flag": flag,
        "reason": reason,
        "recommended_manual_check": check,
        "source_page": row.get("source_page", ""),
        "source_table": row.get("source_table", ""),
        "source_text": row.get("source_text", ""),
    })


def check_ranges(df: pd.DataFrame, raw_df: pd.DataFrame, rules: Dict[str, Any], row_flags: Dict[int, List[str]], reviews: List[Dict[str, Any]]) -> None:
    ranges = rules.get("ranges", {})
    for field, bounds in ranges.items():
        if field not in df.columns:
            continue
        for idx, val in df[field].items():
            if pd.isna(val):
                continue
            raw_val = raw_df.loc[idx, field] if field in raw_df.columns else val
            impossible = False
            warning = False
            reasons = []
            if "impossible_min" in bounds and val < bounds["impossible_min"]:
                impossible = True
                reasons.append(f"below impossible_min={bounds['impossible_min']}")
            if "impossible_max" in bounds and val > bounds["impossible_max"]:
                impossible = True
                reasons.append(f"above impossible_max={bounds['impossible_max']}")
            if "warning_min" in bounds and val < bounds["warning_min"]:
                warning = True
                reasons.append(f"below warning_min={bounds['warning_min']}")
            if "warning_max" in bounds and val > bounds["warning_max"]:
                warning = True
                reasons.append(f"above warning_max={bounds['warning_max']}")
            if impossible:
                add_flag(row_flags, idx, "IMPOSSIBLE_VALUE")
                add_review(reviews, df, idx, "P0", field, raw_val, val, "IMPOSSIBLE_VALUE", "; ".join(reasons), "Check original table/SI and unit; do not use in main analysis until confirmed.")
            elif warning:
                add_flag(row_flags, idx, "IMPLAUSIBLE_VALUE")
                add_review(reviews, df, idx, "P1", field, raw_val, val, "IMPLAUSIBLE_VALUE", "; ".join(reasons), "Verify against original paper/SI, especially unit and decimal place.")


def robust_outliers(df: pd.DataFrame, row_flags: Dict[int, List[str]], reviews: List[Dict[str, Any]], group_col: str = "system") -> None:
    fields = [c for c in NUMERIC_FIELDS if c in df.columns and c not in {"year", "cycle_number", "ai_confidence"}]
    for field in fields:
        groups = df[group_col].fillna("ALL").astype(str) if group_col in df.columns else pd.Series("ALL", index=df.index)
        for group, idxs in groups.groupby(groups).groups.items():
            vals = pd.to_numeric(df.loc[list(idxs), field], errors="coerce").dropna()
            if len(vals) < 5:
                continue
            median = vals.median()
            mad = (vals - median).abs().median()
            q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
            iqr = q3 - q1
            for idx, val in vals.items():
                rz = np.nan
                if mad and mad > 0:
                    rz = 0.6745 * (val - median) / mad
                iqr_flag = bool(iqr and (val < q1 - 3 * iqr or val > q3 + 3 * iqr))
                rz_flag = bool(not pd.isna(rz) and abs(rz) >= 4.5)
                if iqr_flag or rz_flag:
                    add_flag(row_flags, idx, "ROBUST_OUTLIER")
                    add_review(
                        reviews, df, idx, "P1", field, df.loc[idx, field], val, "ROBUST_OUTLIER",
                        f"group={group}; robust_z={rz:.2f} if available; median={median:.3g}; n={len(vals)}",
                        "Check whether the value is real, a unit/decimal issue, or a non-comparable condition. Keep for sensitivity analysis until verified."
                    )


def duplicate_checks(df: pd.DataFrame, row_flags: Dict[int, List[str]], reviews: List[Dict[str, Any]]) -> None:
    key_cols = [c for c in ["doi", "title", "sample_name", "sample_id", "system"] if c in df.columns]
    if len(key_cols) < 2:
        return
    dup_mask = df.duplicated(subset=key_cols, keep=False)
    for idx in df.index[dup_mask]:
        add_flag(row_flags, idx, "DUPLICATE_RECORD")
        add_review(reviews, df, idx, "P1", "record", "", "", "DUPLICATE_RECORD", f"Duplicate key columns: {key_cols}", "Check whether this is a true repeated condition, a copied row, or a same-paper sample that needs separate ID.")

    # Same paper/sample but conflicting key numerical descriptors.
    group_cols = [c for c in ["doi", "title", "sample_name"] if c in df.columns]
    if len(group_cols) >= 2:
        numeric_fields = [c for c in ["BET_m2_g", "d002_nm", "ID_IG", "ICE_percent", "reversible_capacity_mAh_g", "specific_capacitance_F_g"] if c in df.columns]
        for _, g in df.groupby(group_cols, dropna=False):
            if len(g) <= 1:
                continue
            for field in numeric_fields:
                vals = pd.to_numeric(g[field], errors="coerce").dropna().unique()
                if len(vals) > 1:
                    for idx in g.index:
                        add_flag(row_flags, idx, "CONFLICTING_DUPLICATE")
                        add_review(reviews, df, idx, "P0", field, df.loc[idx, field], df.loc[idx, field], "CONFLICTING_DUPLICATE", f"Same paper/sample has conflicting {field} values: {vals[:5]}", "Check original paper/SI and decide whether these are different samples, different conditions, or extraction conflict.")


def missing_condition_checks(df: pd.DataFrame, rules: Dict[str, Any], row_flags: Dict[int, List[str]], reviews: List[Dict[str, Any]]) -> None:
    required_by_system = rules.get("system_required_fields", {})
    if "system" not in df.columns:
        return
    for idx, system in df["system"].fillna("").astype(str).items():
        normalized_system = system.upper().replace(" ", "_").replace("AQUEOUS_SC", "SC_AQUEOUS")
        required = required_by_system.get(normalized_system, [])
        for field in required:
            if field not in df.columns or pd.isna(df.loc[idx, field]) or str(df.loc[idx, field]).strip() == "":
                add_flag(row_flags, idx, "CRITICAL_CONDITION_MISSING")
                add_review(reviews, df, idx, "P1", field, "", "", "CRITICAL_CONDITION_MISSING", f"Required for system {normalized_system}", "Check original paper/SI for missing test condition or target value.")


def evidence_checks(df: pd.DataFrame, row_flags: Dict[int, List[str]], reviews: List[Dict[str, Any]], target: Optional[str]) -> None:
    evidence_cols = [c for c in ["source_page", "source_table", "source_text"] if c in df.columns]
    if not evidence_cols:
        for idx in df.index:
            add_flag(row_flags, idx, "SOURCE_EVIDENCE_MISSING")
            add_review(reviews, df, idx, "P1", target or "record", "", "", "SOURCE_EVIDENCE_MISSING", "No source page/table/text columns present", "Add source page/table or quote from original paper/SI for traceability.")
        return
    for idx in df.index:
        has_evidence = any(not pd.isna(df.loc[idx, c]) and str(df.loc[idx, c]).strip() for c in evidence_cols)
        if not has_evidence:
            add_flag(row_flags, idx, "SOURCE_EVIDENCE_MISSING")
            add_review(reviews, df, idx, "P1", target or "record", "", "", "SOURCE_EVIDENCE_MISSING", "No source evidence for this row", "Check original paper/SI and add page/table/evidence text.")
    if "ai_confidence" in df.columns:
        conf = pd.to_numeric(df["ai_confidence"], errors="coerce")
        for idx, val in conf.items():
            if not pd.isna(val) and val < 0.65:
                add_flag(row_flags, idx, "LOW_EXTRACTION_CONFIDENCE")
                add_review(reviews, df, idx, "P1", "ai_confidence", df.loc[idx, "ai_confidence"], val, "LOW_EXTRACTION_CONFIDENCE", "ai_confidence < 0.65", "Manually verify key fields from original source.")


def paper_level_audit(df: pd.DataFrame, row_flags: Dict[int, List[str]], target: Optional[str]) -> pd.DataFrame:
    paper_col = "doi" if "doi" in df.columns else ("paper_id" if "paper_id" in df.columns else ("title" if "title" in df.columns else None))
    if paper_col is None:
        return pd.DataFrame()
    records = []
    total_rows = len(df)
    target_series = pd.to_numeric(df[target], errors="coerce") if target and target in df.columns else None
    for paper, g in df.groupby(paper_col, dropna=False):
        idxs = list(g.index)
        flags = sorted({f for i in idxs for f in row_flags.get(i, [])})
        rec = {
            "paper_key": paper,
            "n_rows": len(g),
            "row_share": len(g) / total_rows if total_rows else np.nan,
            "n_flagged_rows": sum(1 for i in idxs if row_flags.get(i)),
            "flags": ";".join(flags),
        }
        if target_series is not None:
            vals = target_series.loc[idxs].dropna()
            rec[f"{target}_n"] = len(vals)
            rec[f"{target}_mean"] = vals.mean() if len(vals) else np.nan
            rec[f"{target}_max"] = vals.max() if len(vals) else np.nan
        if rec["row_share"] >= 0.20 and total_rows >= 10:
            rec["paper_dominance_flag"] = "PAPER_DOMINANCE_BIAS"
        else:
            rec["paper_dominance_flag"] = ""
        records.append(rec)
    return pd.DataFrame(records).sort_values(["n_flagged_rows", "n_rows"], ascending=False)


def assign_actions(df: pd.DataFrame, row_flags: Dict[int, List[str]]) -> List[str]:
    p0_flags = {"IMPOSSIBLE_VALUE", "CONFLICTING_DUPLICATE", "UNIT_SCALE_SUSPECT", "POSSIBLE_ROW_SHIFT"}
    p1_flags = {"IMPLAUSIBLE_VALUE", "ROBUST_OUTLIER", "CRITICAL_CONDITION_MISSING", "SOURCE_EVIDENCE_MISSING", "LOW_EXTRACTION_CONFIDENCE", "DUPLICATE_RECORD"}
    actions = []
    for idx in df.index:
        flags = set(row_flags.get(idx, []))
        if flags & p0_flags:
            actions.append("REVIEW_P0")
        elif flags & {"ROBUST_OUTLIER"}:
            actions.append("KEEP_SENSITIVITY")
        elif flags & p1_flags:
            actions.append("REVIEW_P1")
        else:
            actions.append("KEEP_MAIN")
    return actions


def load_rules(path: Optional[Path]) -> Dict[str, Any]:
    if path and path.exists() and yaml is not None:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return DEFAULT_RULES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input .xlsx/.csv/.tsv file")
    parser.add_argument("--outdir", default=None, help="Output directory")
    parser.add_argument("--rules", default=None, help="YAML rules file")
    parser.add_argument("--profile", default="biomass_carbon_energy_storage")
    parser.add_argument("--target", default=None, help="Primary target field, e.g., ICE_percent")
    args = parser.parse_args()

    input_path = Path(args.input)
    if args.outdir:
        outdir = Path(args.outdir)
    else:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
        outdir = Path("cleaning_outputs") / stamp
    outdir.mkdir(parents=True, exist_ok=True)

    rules = load_rules(Path(args.rules) if args.rules else None)
    raw_input = read_input(input_path)
    raw_input.insert(0, "_raw_row_index", range(len(raw_input)))

    mapping, schema_report = build_column_map(raw_input.columns)
    df = raw_input.rename(columns=mapping).copy()
    raw_renamed = df.copy()

    row_flags: Dict[int, List[str]] = {}
    reviews: List[Dict[str, Any]] = []
    corrections: List[Dict[str, Any]] = []

    # Numeric parsing and unit normalization.
    for field in list(NUMERIC_FIELDS):
        if field not in df.columns:
            continue
        raw_col = df[field].copy()
        parsed_values = []
        for idx, raw_val in raw_col.items():
            parsed, parse_flags = extract_first_number(raw_val)
            normalized, unit_flags, note = normalize_units(field, raw_val, parsed)
            parsed_values.append(normalized)
            for flag in parse_flags + unit_flags:
                add_flag(row_flags, idx, flag)
                priority = "P0" if flag == "UNIT_SCALE_SUSPECT" else "P1"
                add_review(reviews, df, idx, priority, field, raw_val, normalized, flag, note or flag, "Verify value/unit against original source.")
                corrections.append({
                    "row_index": idx,
                    "field": field,
                    "raw_value": raw_val,
                    "normalized_value": normalized,
                    "flag": flag,
                    "note": note,
                })
        df[field] = parsed_values

    # Normalize system labels a little.
    if "system" in df.columns:
        sys_map = {
            "aqueous sc": "SC_AQUEOUS", "sc": "SC_AQUEOUS", "supercapacitor": "SC_AQUEOUS", "aqueous supercapacitor": "SC_AQUEOUS",
            "lib": "LIB", "li-ion": "LIB", "lithium ion battery": "LIB",
            "sib": "SIB", "na-ion": "SIB", "sodium ion battery": "SIB",
        }
        df["system"] = df["system"].apply(lambda x: sys_map.get(str(x).strip().lower(), str(x).strip()) if not pd.isna(x) else x)

    check_ranges(df, raw_renamed, rules, row_flags, reviews)
    duplicate_checks(df, row_flags, reviews)
    missing_condition_checks(df, rules, row_flags, reviews)
    evidence_checks(df, row_flags, reviews, args.target)
    robust_outliers(df, row_flags, reviews)

    df["flags"] = [";".join(row_flags.get(idx, [])) for idx in df.index]
    df["final_action"] = assign_actions(df, row_flags)
    df["review_priority"] = df["final_action"].map({"REVIEW_P0": "P0", "REVIEW_P1": "P1", "KEEP_SENSITIVITY": "P1", "KEEP_MAIN": "", "EXCLUDE_MAIN": "P0"}).fillna("")

    review_df = pd.DataFrame(reviews).drop_duplicates()
    if not review_df.empty:
        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        review_df["_priority_order"] = review_df["priority"].map(priority_order).fillna(9)
        review_df = review_df.sort_values(["_priority_order", "paper_id", "sample_id", "field"]).drop(columns=["_priority_order"])

    flagged = df[df["flags"].astype(str).str.len() > 0].copy()
    paper_audit = paper_level_audit(df, row_flags, args.target)
    correction_df = pd.DataFrame(corrections).drop_duplicates()
    schema_df = pd.DataFrame(schema_report)

    df.to_csv(outdir / "cleaned_database.csv", index=False, encoding="utf-8-sig")
    flagged.to_csv(outdir / "flagged_records.csv", index=False, encoding="utf-8-sig")
    review_df.to_csv(outdir / "secondary_review_queue.csv", index=False, encoding="utf-8-sig")
    paper_audit.to_csv(outdir / "paper_level_audit.csv", index=False, encoding="utf-8-sig")
    correction_df.to_csv(outdir / "correction_log.csv", index=False, encoding="utf-8-sig")
    schema_df.to_csv(outdir / "schema_mapping_report.csv", index=False, encoding="utf-8-sig")

    counts = df["final_action"].value_counts(dropna=False).to_dict()
    p0 = int((df["final_action"] == "REVIEW_P0").sum())
    p1 = int(((df["final_action"] == "REVIEW_P1") | (df["final_action"] == "KEEP_SENSITIVITY")).sum())
    main = int((df["final_action"] == "KEEP_MAIN").sum())

    report = f"""# Data Quality Report

Generated: {dt.datetime.now().isoformat(timespec='seconds')}

Input file: `{input_path}`

Profile: `{args.profile}`

Primary target: `{args.target or 'not specified'}`

## Row summary

- Raw rows: {len(df)}
- KEEP_MAIN: {main}
- REVIEW_P0: {p0}
- REVIEW_P1 or KEEP_SENSITIVITY: {p1}
- Flagged rows: {len(flagged)}

Final action counts:

```json
{json.dumps(counts, ensure_ascii=False, indent=2)}
```

## Interpretation

Outliers were not permanently deleted. Raw rows were preserved. Records were assigned action labels for main analysis, sensitivity analysis, or secondary manual verification.

P0 records should be checked against the original paper/SI before they support any manuscript figure, table, or conclusion. P1 records should be checked before final submission if they influence a trend, correlation, or design rule.

## Main output files

- `cleaned_database.csv`
- `flagged_records.csv`
- `secondary_review_queue.csv`
- `paper_level_audit.csv`
- `correction_log.csv`
- `schema_mapping_report.csv`
"""
    (outdir / "data_quality_report.md").write_text(report, encoding="utf-8")

    print(report)


if __name__ == "__main__":
    main()
