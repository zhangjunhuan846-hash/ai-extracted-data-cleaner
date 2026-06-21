from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd


def paper_level_audit(flags: list[dict[str, Any]]) -> pd.DataFrame:
    columns = ["paper_id", "P0", "P1", "P2", "total_flags"]
    if not flags:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(flags)
    rows = []
    for paper_id, group in df.groupby("paper_id", dropna=False):
        counts = Counter(group["risk_level"])
        rows.append({
            "paper_id": paper_id,
            "P0": counts.get("P0", 0),
            "P1": counts.get("P1", 0),
            "P2": counts.get("P2", 0),
            "total_flags": len(group),
        })
    return pd.DataFrame(rows, columns=columns).sort_values(["P0", "P1", "P2", "total_flags"], ascending=False)


def build_quality_report(
    n_raw: int,
    n_cols: int,
    flags: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
    unknown_columns: list[str],
    *,
    schema: dict[str, Any] | None = None,
    decision: str | None = None,
) -> str:
    counts = Counter(f["risk_level"] for f in flags)
    decision = decision or ("NOT_READY" if counts.get("P0", 0) > 0 else ("REVIEW_NEEDED" if counts.get("P1", 0) > 0 else "PASS_WITH_NOTES"))
    field_counts = Counter(f["field"] for f in flags)
    correction_counts = Counter(c.get("correction_type", "unknown") for c in corrections)
    schema = schema or {}

    lines = [
        "# AI 提取数据清洗质量报告",
        "",
        "## 总体判断",
        "",
        f"- 决策：**{decision}**",
        f"- 原始样本数：{n_raw}",
        f"- 字段数：{n_cols}",
        f"- 自动修正记录数：{len(corrections)}",
        f"- P0 必须修正：{counts.get('P0', 0)}",
        f"- P1 强烈建议核查：{counts.get('P1', 0)}",
        f"- P2 可选优化：{counts.get('P2', 0)}",
        "",
        "## 决策解释",
        "",
        "- `NOT_READY`：存在 P0，进入数据库、综述图表或机器学习前必须回查并修正。",
        "- `REVIEW_NEEDED`：无 P0 但存在 P1，建议先完成关键样本的原文/SI 核查。",
        "- `PASS_WITH_NOTES`：未发现 P0/P1，但仍应保留 correction log 和 source location。",
        "",
        "## 主要风险解释",
        "",
        "- P0：通常表示物理上不可能、单位严重错误或关键性能越界。",
        "- P1：通常表示物理上可疑、可能存在 OCR 小数点/单位错误，建议回查原文或 SI。",
        "- P2：通常表示字段缺失、来源位置缺失或工程参数不足。",
        "",
    ]

    duplicate_mappings = schema.get("duplicate_canonical_mappings") or {}
    missing_fields = schema.get("missing_recommended_fields") or []
    if missing_fields or duplicate_mappings:
        lines += ["## Schema 审计", ""]
        if missing_fields:
            lines.append("推荐字段缺失：" + ", ".join(f"`{x}`" for x in missing_fields))
        if duplicate_mappings:
            lines.append("多个原始字段映射到同一标准字段，需要确认是否有重复信息：")
            for canonical, raw_cols in duplicate_mappings.items():
                lines.append(f"- `{canonical}` <= {', '.join(f'`{c}`' for c in raw_cols)}")
        lines.append("")

    if unknown_columns:
        lines += ["## 未识别字段", ""]
        for c in unknown_columns:
            lines.append(f"- `{c}`")
        lines.append("")

    if correction_counts:
        lines += ["## 自动修正类型统计", ""]
        for ctype, n in correction_counts.most_common():
            lines.append(f"- `{ctype}`: {n}")
        lines.append("")

    if field_counts:
        lines += ["## 风险字段统计", ""]
        for field, n in field_counts.most_common(20):
            lines.append(f"- `{field}`: {n}")
        lines.append("")

    if flags:
        lines += ["## 前 10 条高优先级核查项", ""]
        order = {"P0": 0, "P1": 1, "P2": 2}
        for f in sorted(flags, key=lambda x: (order.get(x["risk_level"], 9), x["row_index"]))[:10]:
            lines.append(f"- **{f['risk_level']}** row={f['row_index']}, paper={f.get('paper_id','')}, sample={f.get('sample_id','')}, field=`{f['field']}`：{f['reason']}；建议：{f['required_action']}")
        lines.append("")

    lines += [
        "## 建议下一步",
        "",
        "1. 先处理所有 P0 项，尤其是 ICE、容量、BET、d002 的单位和小数点错误。",
        "2. 对 P1 项回查原文表格、图注或 SI；若确认无误，在数据库备注中说明原因。",
        "3. 对 P2 项补充 source_location、mass loading、电极厚度、压实密度等工程信息。",
        "4. 将 `cleaned_database.csv` 与 `correction_log.csv` 一起保存，避免后续图表或模型结果无法追溯。",
    ]
    return "\n".join(lines) + "\n"
