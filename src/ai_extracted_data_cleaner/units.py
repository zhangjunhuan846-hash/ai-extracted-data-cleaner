from __future__ import annotations

import re
from typing import Any

import pandas as pd

NUMERIC_FIELDS = {
    "carbonization_temperature_C",
    "BET_m2_g",
    "d002_nm",
    "ID_IG",
    "XPS_N_at_pct",
    "XPS_O_at_pct",
    "pore_volume_cm3_g",
    "micropore_volume_cm3_g",
    "mass_loading_mg_cm2",
    "electrode_thickness_um",
    "compacted_density_g_cm3",
    "ICE_pct",
    "capacity_mAh_g",
    "capacitance_F_g",
    "current_density_A_g",
}


def parse_number(value: Any) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    text = text.replace(",", "")
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def unit_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).lower()


def normalize_value(field: str, value: Any) -> tuple[float | None, dict[str, Any] | None]:
    num = parse_number(value)
    if num is None:
        return None, None
    text = unit_text(value)
    original = value
    correction = None

    # d002 often appears in Angstrom. Convert to nm when unit is explicit.
    if field == "d002_nm" and ("å" in text or "angstrom" in text or "a" == text.strip().split()[-1:] or "Å" in text):
        cleaned = num / 10.0
        correction = _corr(field, original, cleaned, "unit_conversion", "Å converted to nm", "high")
        return cleaned, correction

    # If d002 is 3-5 without unit, likely Angstrom for carbon interlayer spacing; flag via correction confidence medium.
    if field == "d002_nm" and 2.5 <= num <= 5.0 and not any(u in text for u in ["nm", "å", "angstrom", "Å"]):
        cleaned = num / 10.0
        correction = _corr(field, original, cleaned, "possible_unit_conversion", "d002 value looks like Å; converted to nm with medium confidence", "medium")
        return cleaned, correction

    # surface area in cm2/g to m2/g when explicit.
    if field == "BET_m2_g" and ("cm2/g" in text or "cm^2/g" in text or "cm2 g" in text):
        cleaned = num / 10000.0
        correction = _corr(field, original, cleaned, "unit_conversion", "cm2/g converted to m2/g", "high")
        return cleaned, correction

    # current density mA/g to A/g when explicit.
    if field == "current_density_A_g" and ("ma/g" in text or "ma g" in text or "ma·g" in text):
        cleaned = num / 1000.0
        correction = _corr(field, original, cleaned, "unit_conversion", "mA/g converted to A/g", "high")
        return cleaned, correction

    return num, None


def _corr(field: str, original: Any, cleaned: float, ctype: str, reason: str, confidence: str) -> dict[str, Any]:
    return {
        "field": field,
        "original_value": original,
        "cleaned_value": cleaned,
        "correction_type": ctype,
        "confidence": confidence,
        "reason": reason,
    }
