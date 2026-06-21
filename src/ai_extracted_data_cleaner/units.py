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
    return (
        str(value)
        .lower()
        .replace("−", "-")
        .replace("⁻", "-")
        .replace("²", "2")
        .replace("³", "3")
        .replace("·", " ")
        .replace("μ", "µ")
    )


def normalize_value(field: str, value: Any) -> tuple[float | None, dict[str, Any] | None]:
    num = parse_number(value)
    if num is None:
        return None, None
    text = unit_text(value)
    original = value

    if field == "carbonization_temperature_C" and _has_kelvin(text):
        cleaned = num - 273.15
        return cleaned, _corr(field, original, cleaned, "unit_conversion", "K converted to °C", "high")

    # d002 often appears in Angstrom. Convert to nm when unit is explicit.
    if field == "d002_nm" and _has_angstrom(text):
        cleaned = num / 10.0
        return cleaned, _corr(field, original, cleaned, "unit_conversion", "Å converted to nm", "high")

    # If d002 is 2.5-5 without unit, likely Angstrom for carbon interlayer spacing.
    if field == "d002_nm" and 2.5 <= num <= 5.0 and not any(u in text for u in ["nm", "å", "angstrom", "angström", "Å"]):
        cleaned = num / 10.0
        return cleaned, _corr(field, original, cleaned, "possible_unit_conversion", "d002 value looks like Å; converted to nm with medium confidence", "medium")

    if field == "BET_m2_g" and _contains_any(text, ["cm2/g", "cm^2/g", "cm2 g", "cm2g-1", "cm2 g-1"]):
        cleaned = num / 10000.0
        return cleaned, _corr(field, original, cleaned, "unit_conversion", "cm2/g converted to m2/g", "high")

    if field == "current_density_A_g" and _contains_any(text, ["ma/g", "ma g", "ma g-1", "mag-1"]):
        cleaned = num / 1000.0
        return cleaned, _corr(field, original, cleaned, "unit_conversion", "mA/g converted to A/g", "high")

    if field == "capacity_mAh_g" and _has_ampere_hour_per_g(text):
        cleaned = num * 1000.0
        return cleaned, _corr(field, original, cleaned, "unit_conversion", "Ah/g converted to mAh/g", "high")

    if field == "mass_loading_mg_cm2" and _contains_any(text, ["g/m2", "g m-2", "g m2"]):
        cleaned = num * 0.1
        return cleaned, _corr(field, original, cleaned, "unit_conversion", "g/m2 converted to mg/cm2", "high")

    if field in {"XPS_N_at_pct", "XPS_O_at_pct", "ICE_pct"} and 0 < num <= 1 and "%" in text:
        # Avoid changing bare fractions. Only convert when a percent sign is explicitly present and OCR/parser retained a 0-1 value.
        cleaned = num * 100.0
        return cleaned, _corr(field, original, cleaned, "possible_percent_scale", "0-1 value with percent sign converted to percent", "medium")

    return num, None


def _has_angstrom(text: str) -> bool:
    if any(symbol in text for symbol in ["å", "Å", "angstrom", "angström"]):
        return True
    return bool(re.search(r"(?:^|\s)\d*\.?\d+\s*a(?:\s|$)", text))


def _has_kelvin(text: str) -> bool:
    return bool(re.search(r"(?:^|\s)\d*\.?\d+\s*k(?:\s|$)", text)) or " kelvin" in text


def _has_ampere_hour_per_g(text: str) -> bool:
    # Match Ah/g but not mAh/g.
    return bool(re.search(r"(?<!m)ah\s*/?\s*g(?:-1)?", text))


def _contains_any(text: str, needles: list[str]) -> bool:
    compact = re.sub(r"\s+", " ", text)
    nospace = compact.replace(" ", "")
    return any(n in compact or n.replace(" ", "") in nospace for n in needles)


def _corr(field: str, original: Any, cleaned: float, ctype: str, reason: str, confidence: str) -> dict[str, Any]:
    return {
        "field": field,
        "original_value": original,
        "cleaned_value": cleaned,
        "correction_type": ctype,
        "confidence": confidence,
        "reason": reason,
    }
