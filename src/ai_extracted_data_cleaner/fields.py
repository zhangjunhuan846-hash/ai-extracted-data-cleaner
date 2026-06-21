from __future__ import annotations

import re
from collections import Counter, defaultdict
from importlib import resources
from pathlib import Path
from typing import Any

import yaml


def normalize_name(name: str) -> str:
    """Normalize a spreadsheet column name for robust alias matching."""
    text = str(name).strip().lower()
    text = (
        text.replace("²", "2")
        .replace("³", "3")
        .replace("⁻", "-")
        .replace("−", "-")
        .replace("·", " ")
        .replace("_", " ")
    )
    text = re.sub(r"[^a-z0-9%/+-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def default_alias_path() -> Path:
    """Return the package-bundled alias configuration path.

    A copy is also kept under the repository-level ``config/`` directory for
    easy editing, but runtime code should rely on bundled package data so the
    console script works after a normal pip installation.
    """
    return Path(str(resources.files("ai_extracted_data_cleaner.config") / "field_aliases.yaml"))


def load_aliases(path: str | Path | None = None) -> dict[str, list[str]]:
    alias_path = Path(path) if path else default_alias_path()
    data = yaml.safe_load(alias_path.read_text(encoding="utf-8")) or {}
    result: dict[str, list[str]] = {}
    for canonical, spec in data.get("canonical_fields", {}).items():
        aliases = [canonical] + list((spec or {}).get("aliases", []))
        result[canonical] = sorted({_canonicalize_alias(a) for a in aliases if str(a).strip()})
    return result


def build_column_map(columns: list[str], alias_path: str | Path | None = None) -> tuple[dict[str, str], list[str]]:
    aliases = load_aliases(alias_path)
    column_map: dict[str, str] = {}
    unknown: list[str] = []
    for col in columns:
        candidates = _column_candidates(col)
        matched = None
        for canonical, alias_list in aliases.items():
            if any(candidate in alias_list for candidate in candidates):
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

    counts = Counter(column_map.values())
    duplicate_targets = {field: count for field, count in counts.items() if count > 1}
    reverse: dict[str, list[str]] = defaultdict(list)
    for raw, canonical in column_map.items():
        reverse[canonical].append(raw)

    warnings: list[dict[str, Any]] = [
        {"risk_level": "P2", "field": c, "reason": "推荐字段缺失，建议补充以提高可追溯性"}
        for c in missing
    ]
    warnings.extend(
        {
            "risk_level": "P1",
            "field": canonical,
            "reason": f"多个原始字段映射到同一标准字段：{', '.join(reverse[canonical])}",
        }
        for canonical in duplicate_targets
    )

    return {
        "agent": "schema_agent",
        "version": "1.1.0",
        "summary": {
            "n_raw_columns": len(columns),
            "n_mapped_columns": len(column_map),
            "n_unknown_columns": len(unknown),
            "n_duplicate_canonical_mappings": len(duplicate_targets),
        },
        "column_map": column_map,
        "unknown_columns": unknown,
        "duplicate_canonical_mappings": {k: reverse[k] for k in duplicate_targets},
        "missing_recommended_fields": missing,
        "warnings": warnings,
    }


def _canonicalize_alias(name: str) -> str:
    return _strip_unit_suffix(normalize_name(name))


def _column_candidates(name: str) -> list[str]:
    norm = normalize_name(name)
    no_parentheses = normalize_name(re.sub(r"\([^)]*\)", " ", str(name)))
    candidates = [norm, no_parentheses, _strip_unit_suffix(norm), _strip_unit_suffix(no_parentheses)]
    # Some extractors append bracketed units or comments without parentheses.
    candidates.append(_strip_after_delimiter(norm))
    return [c for c in dict.fromkeys(candidates) if c]


def _strip_after_delimiter(name: str) -> str:
    # Keep strings such as ID/IG intact, but remove common trailing unit/context fragments.
    parts = re.split(r"\s+(?:unit|units|value|reported|from|source)\s+", name, maxsplit=1)
    return parts[0].strip()


def _strip_unit_suffix(name: str) -> str:
    unit_tokens = {
        "m2/g", "m2 g", "m2 g-1", "cm2/g", "cm2 g", "cm2 g-1",
        "cm3/g", "cm3 g", "cm3 g-1", "mg/cm2", "mg cm2", "mg cm-2",
        "g/cm3", "g cm3", "g cm-3", "mah/g", "mah g", "mah g-1",
        "f/g", "f g", "f g-1", "a/g", "a g", "a g-1", "ma/g", "ma g", "ma g-1",
        "nm", "a", "angstrom", "å", "um", "µm", "at%", "wt%", "%", "c", "deg c", "degree c",
        "v", "mv/s", "mv s", "mv s-1",
    }
    tokens = name.split()
    while tokens and tokens[-1] in unit_tokens:
        tokens.pop()
    return " ".join(tokens).strip()
