from __future__ import annotations

from typing import Any

import pandas as pd


def detect_duplicates(df: pd.DataFrame) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if "sample_id" in df.columns:
        s = df["sample_id"].map(_norm_key)
        duplicated = df[s.ne("") & s.duplicated(keep=False)]
        for idx, row in duplicated.iterrows():
            flags.append(_dup(idx, row, "sample_id", str(row.get("sample_id", "")), "P1", "sample_id 重复出现", "确认是否同一样本重复录入，或是否需要添加测试条件后缀"))

    if {"paper_id", "sample_name"}.issubset(df.columns):
        paper = df["paper_id"].map(_norm_key)
        sample = df["sample_name"].map(_norm_key)
        key = paper + "||" + sample
        duplicated = df[paper.ne("") & sample.ne("") & key.duplicated(keep=False)]
        for idx, row in duplicated.iterrows():
            value = f"{row.get('paper_id', '')} | {row.get('sample_name', '')}"
            flags.append(_dup(idx, row, "paper_id+sample_name", value, "P1", "同一论文中 sample_name 重复", "检查是否为同一样本、不同倍率/循环数，或真实重复记录"))

    key_cols = [c for c in ["paper_id", "BET_m2_g", "d002_nm", "ID_IG", "ICE_pct", "capacity_mAh_g", "capacitance_F_g", "current_density_A_g"] if c in df.columns]
    if len(key_cols) >= 4:
        markers = df[key_cols].apply(_row_marker, axis=1)
        informative = markers.map(lambda x: x.count("=") >= 4)
        duplicated = df[informative & markers.duplicated(keep=False)]
        for idx, row in duplicated.iterrows():
            flags.append(_dup(idx, row, "near_duplicate_values", markers.loc[idx], "P2", "关键描述符、测试条件和性能值完全重复", "确认是否为复制残留、同一样本重复记录，或同一材料在不同表格中重复出现"))
    return flags


def _row_marker(row: pd.Series) -> str:
    parts = []
    for col, value in row.items():
        norm = _norm_value(value)
        if norm != "":
            parts.append(f"{col}={norm}")
    return "||".join(parts)


def _norm_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, (int, float)):
        return f"{float(value):.6g}"
    text = str(value).strip().lower()
    if text in {"", "nan", "none", "null", "n/a", "na", "-"}:
        return ""
    return " ".join(text.split())


def _norm_key(value: Any) -> str:
    return _norm_value(value)


def _dup(idx: int, row: pd.Series, field: str, value: str, risk: str, reason: str, action: str) -> dict[str, Any]:
    return {
        "row_index": int(idx),
        "paper_id": str(row.get("paper_id", "")) if not pd.isna(row.get("paper_id", "")) else "",
        "sample_id": str(row.get("sample_id", "")) if not pd.isna(row.get("sample_id", "")) else "",
        "field": field,
        "value": value,
        "risk_level": risk,
        "reason": reason,
        "required_action": action,
    }
