from __future__ import annotations

from typing import Any

import pandas as pd


def detect_duplicates(df: pd.DataFrame) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if "sample_id" in df.columns:
        duplicated = df[df["sample_id"].astype(str).duplicated(keep=False) & df["sample_id"].notna()]
        for idx, row in duplicated.iterrows():
            flags.append(_dup(idx, row, "sample_id", "P1", "sample_id 重复出现", "确认是否同一样本重复录入，或是否需要添加测试条件后缀"))

    if {"paper_id", "sample_name"}.issubset(df.columns):
        key = df["paper_id"].astype(str) + "||" + df["sample_name"].astype(str)
        duplicated = df[key.duplicated(keep=False) & df["sample_name"].notna()]
        for idx, row in duplicated.iterrows():
            flags.append(_dup(idx, row, "paper_id+sample_name", "P1", "同一论文中 sample_name 重复", "检查是否为同一样本、不同倍率/循环数，或真实重复记录"))

    key_cols = [c for c in ["paper_id", "BET_m2_g", "d002_nm", "ID_IG", "ICE_pct", "capacity_mAh_g", "capacitance_F_g"] if c in df.columns]
    if len(key_cols) >= 4:
        subset = df[key_cols].copy()
        marker = subset.astype(str).agg("||".join, axis=1)
        duplicated = df[marker.duplicated(keep=False)]
        for idx, row in duplicated.iterrows():
            flags.append(_dup(idx, row, "near_duplicate_values", "P2", "关键描述符和性能值近似重复", "确认是否为复制残留或同一材料重复记录"))
    return flags


def _dup(idx: int, row: pd.Series, field: str, risk: str, reason: str, action: str) -> dict[str, Any]:
    return {
        "row_index": int(idx),
        "paper_id": str(row.get("paper_id", "")),
        "sample_id": str(row.get("sample_id", "")),
        "field": field,
        "value": str(row.get(field, "")),
        "risk_level": risk,
        "reason": reason,
        "required_action": action,
    }
