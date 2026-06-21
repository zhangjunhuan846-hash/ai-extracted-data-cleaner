from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

DEFAULT_ALIASES = Path(__file__).resolve().parents[2] / "config" / "field_aliases.yaml"


def normalize_name(name: str) -> str:
    name = str(name).strip().lower()
    name = name.replace("²", "2").replace("⁻", "-")
    name = re.sub(r"[^a-z0-9%/]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def load_aliases(path: str | Path | None = None) -> dict[str, list[str]]:
    alias_path = Path(path) if path else DEFAULT_ALIASES
    data = yaml.safe_load(alias_path.read_text(encoding="utf-8"))
    result: dict[str, list[str]] = {}
    for canonical, spec in data.get("canonical_fields", {}).items():
        aliases = [canonical] + list(spec.get("aliases", []))
        result[canonical] = [normalize_name(a) for a in aliases]
    return result


def build_column_map(columns: list[str], alias_path: str | Path | None = None) -> tuple[dict[str, str], list[str]]:
    aliases = load_aliases(alias_path)
    column_map: dict[str, str] = {}
    unknown: list[str] = []
    for col in columns:
        norm = normalize_name(col)
        matched = None
        for canonical, alias_list in aliases.items():
            if norm in alias_list:
                matched = canonical
                break
        if matched is None:
            # partial matching for common units in parentheses
            stripped = re.sub(r"\s*\([^)]*\)", "", norm).strip()
            for canonical, alias_list in aliases.items():
                if stripped in alias_list:
                    matched = canonical
                    break
        if matched:
            column_map[col] = matched
        else:
            unknown.append(col)
    return column_map, unknown


def schema_state(columns: list[str], column_map: dict[str, str], unknown: list[str]) -> dict[str, Any]:
    recommended = ["paper_id", "sample_id", "sample_name", "source_location"]
    mapped_values = set(column_map.values())
    missing = [c for c in recommended if c not in mapped_values]
    return {
        "agent": "schema_agent",
        "version": "1.0.0",
        "summary": {
            "n_raw_columns": len(columns),
            "n_mapped_columns": len(column_map),
            "n_unknown_columns": len(unknown),
        },
        "column_map": column_map,
        "unknown_columns": unknown,
        "missing_recommended_fields": missing,
        "warnings": [
            {"risk_level": "P2", "field": c, "reason": "推荐字段缺失，建议补充以提高可追溯性"}
            for c in missing
        ],
    }
