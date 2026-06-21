from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

DEFAULT_RULES = Path(__file__).resolve().parents[2] / "config" / "validation_rules.yaml"


def load_rules(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_RULES
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def validate_dataframe(df: pd.DataFrame, rules_path: str | Path | None = None) -> list[dict[str, Any]]:
    rules = load_rules(rules_path).get("rules", {})
    flags: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        paper_id = _val(row, "paper_id")
        sample_id = _val(row, "sample_id")
        for field, rule in rules.items():
            if field not in df.columns or pd.isna(row.get(field)):
                continue
            try:
                value = float(row.get(field))
            except (TypeError, ValueError):
                continue

            hard_min = rule.get("hard_min")
            hard_max = rule.get("hard_max")
            soft_min = rule.get("soft_min")
            soft_max = rule.get("soft_max")
            unit = rule.get("unit", "")

            if hard_min is not None and value < hard_min:
                flags.append(_flag(idx, paper_id, sample_id, field, value, "P0", f"{field} = {value:g} {unit} below hard minimum {hard_min}", "回查原文或 SI；该值不能直接用于数据库或建模"))
            elif hard_max is not None and value > hard_max:
                flags.append(_flag(idx, paper_id, sample_id, field, value, "P0", f"{field} = {value:g} {unit} above hard maximum {hard_max}", "回查原文或 SI；优先检查 OCR 小数点、单位和百分号"))
            elif soft_min is not None and value < soft_min:
                flags.append(_flag(idx, paper_id, sample_id, field, value, "P1", f"{field} = {value:g} {unit} below typical range {soft_min}", "建议回查原文；若属实，需在数据库备注中说明"))
            elif soft_max is not None and value > soft_max:
                flags.append(_flag(idx, paper_id, sample_id, field, value, "P1", f"{field} = {value:g} {unit} above typical range {soft_max}", "建议回查原文；优先检查单位、小数点和表格行错位"))

        for required in ["source_location"]:
            if required in df.columns and (pd.isna(row.get(required)) or str(row.get(required)).strip() == ""):
                flags.append(_flag(idx, paper_id, sample_id, required, "", "P2", "缺少来源位置，后续难以回查", "补充表号、图号、SI 页码或原文位置"))

        for engineering in ["mass_loading_mg_cm2", "electrode_thickness_um", "compacted_density_g_cm3"]:
            if engineering in df.columns and (pd.isna(row.get(engineering)) or str(row.get(engineering)).strip() == ""):
                flags.append(_flag(idx, paper_id, sample_id, engineering, "", "P2", f"缺少 {engineering}，影响器件级可比性", "回查实验方法或电极制备部分"))
    return flags


def _val(row: pd.Series, key: str) -> str:
    val = row.get(key, "")
    if pd.isna(val):
        return ""
    return str(val)


def _flag(row_index: int, paper_id: str, sample_id: str, field: str, value: Any, risk: str, reason: str, action: str) -> dict[str, Any]:
    return {
        "row_index": int(row_index),
        "paper_id": paper_id,
        "sample_id": sample_id,
        "field": field,
        "value": value,
        "risk_level": risk,
        "reason": reason,
        "required_action": action,
    }
