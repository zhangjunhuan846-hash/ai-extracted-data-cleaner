from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd


def paper_level_audit(flags: list[dict[str, Any]]) -> pd.DataFrame:
    if not flags:
        return pd.DataFrame(columns=["paper_id", "P0", "P1", "P2", "total_flags"])
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
    return pd.DataFrame(rows).sort_values(["P0", "P1", "P2", "total_flags"], ascending=False)


def build_quality_report(n_raw: int, n_cols: int, flags: list[dict[str, Any]], corrections: list[dict[str, Any]], unknown_columns: list[str]) -> str:
    counts = Counter(f["risk_level"] for f in flags)
    decision = "NOT READY" if counts.get("P0", 0) > 0 else ("REVIEW NEEDED" if counts.get("P1", 0) > 0 else "PASS WITH NOTES")
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
        "## 主要风险解释",
        "",
        "- P0：通常表示物理上不可能、单位严重错误或关键性能越界，进入数据库或建模前必须修正。",
        "- P1：通常表示物理上可疑、可能存在 OCR 小数点/单位错误，建议回查原文或 SI。",
        "- P2：通常表示字段缺失、来源位置缺失或工程参数不足。",
        "",
    ]
    if unknown_columns:
        lines += ["## 未识别字段", ""]
        for c in unknown_columns:
            lines.append(f"- `{c}`")
        lines.append("")
    if flags:
        lines += ["## 前 10 条高优先级核查项", ""]
        order = {"P0": 0, "P1": 1, "P2": 2}
        for f in sorted(flags, key=lambda x: (order.get(x["risk_level"], 9), x["row_index"]))[:10]:
            lines.append(f"- **{f['risk_level']}** row={f['row_index']}, sample={f.get('sample_id','')}, field=`{f['field']}`：{f['reason']}；建议：{f['required_action']}")
        lines.append("")
    lines += [
        "## 建议下一步",
        "",
        "1. 先处理所有 P0 项。",
        "2. 对 P1 项回查原文表格、图注或 SI。",
        "3. 对 P2 项补充 source_location、mass loading、电极厚度等工程信息。",
        "4. 将清洗后的 `cleaned_database.csv` 作为综述审计或机器学习建模的输入。",
    ]
    return "\n".join(lines) + "\n"
