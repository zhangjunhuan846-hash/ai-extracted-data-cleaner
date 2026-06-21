---
name: ai-extracted-data-cleaner
description: Clean, calibrate, audit, and analyze AI-extracted scientific sample-level data from PDFs/Word/Markdown/OCR outputs. Use when the user has tables extracted by AI from papers and needs unit normalization, descriptor harmonization, outlier/bias flags, paper/sample-level secondary verification queues, and reproducible cleaning reports.
---

# AI-Extracted Data Cleaner Skill

## Purpose

This skill converts AI-extracted literature data into a reproducible, auditable sample-level database. It is designed for materials/chemical-engineering literature datasets where each row is a reported material, sample, or testing condition, and where AI extraction may introduce hallucinated values, unit errors, row shifts, copied table artifacts, duplicated samples, or mixed experimental conditions.

The skill does **not** silently delete data. It preserves raw values, creates normalized fields, assigns flags and confidence scores, and separates records into:

- `KEEP_MAIN`: usable in main analysis.
- `KEEP_SENSITIVITY`: usable only in sensitivity analysis.
- `REVIEW_P0`: must manually verify against the original paper/SI before use.
- `REVIEW_P1`: should verify if this record affects a figure, correlation, or conclusion.
- `EXCLUDE_MAIN`: excluded from main analysis but retained in the audit trail.

## When to use

Use this skill when the user says any of the following:

- “清洗 AI 从文献/文档提取的数据”
- “合并文献样本数据”
- “检查异常值/偏差值/离群点”
- “哪些论文样本需要二次校核”
- “把 AI 提取的 Excel/CSV 变成可分析数据库”
- “多 agent 校准数据”
- “检查数据有没有单位错误、重复样本、错列、错提取”

## Required input

At minimum:

1. An extracted data file: `.xlsx`, `.csv`, or `.tsv`.
2. A target domain profile: for example `biomass_carbon_energy_storage`.
3. A primary analysis target, if known: for example `ICE`, `specific_capacity`, `specific_capacitance`, `retention`, or `rate_performance`.

Recommended columns if available:

- Paper metadata: `paper_id`, `title`, `doi`, `year`, `journal`.
- Sample identity: `sample_id`, `sample_name`, `precursor`, `biomass_source`, `treatment`, `activation`, `carbonization_temp`, `carbonization_time`.
- Structural descriptors: `BET`, `total_pore_volume`, `micropore_volume`, `d002`, `ID_IG`, `N_at_percent`, `O_at_percent`, `ash_content`.
- Testing descriptors: `system`, `electrolyte`, `voltage_window`, `current_density`, `mass_loading`, `electrode_thickness`, `compaction_density`.
- Performance: `ICE`, `capacity`, `specific_capacitance`, `rate_retention`, `cycle_retention`, `cycle_number`.
- Evidence: `source_page`, `source_table`, `source_text`, `extraction_note`, `ai_confidence`.

## Core principles

1. **Raw data is immutable.** Never overwrite raw extracted values. Create normalized columns instead.
2. **Outliers are not automatically false.** Flag them, quarantine them, and test sensitivity. Delete only with explicit evidence.
3. **Paper-level clustering matters.** Multiple samples from one paper are not independent evidence for cross-paper claims.
4. **Do not mix incomparable conditions.** Do not pool SIB/LIB/SC, electrolytes, current densities, voltage windows, or mass-normalized/device-level metrics without explicit grouping.
5. **Every correction needs provenance.** Record correction type, rule, source field, old value, new value, and reason.
6. **Secondary verification is a deliverable.** The output must say which paper/sample/field should be manually checked next.

## Multi-agent workflow

Run the following agents in order. Each agent writes a short report and passes structured flags to the next agent.

### Agent 1 — Schema Mapper

Goal: map messy AI-extracted columns to canonical database fields.

Tasks:

- Detect likely columns using names, units, and values.
- Preserve all unknown columns in `raw_extra_*` fields.
- Create a `schema_mapping_report.md`.
- Flag fields with ambiguous mapping as `SCHEMA_AMBIGUOUS`.

Output:

- Canonical field map.
- Unmapped columns list.
- Required-missing columns list.

### Agent 2 — Unit and Type Normalizer

Goal: normalize units and numeric types.

Tasks:

- Convert temperature to °C.
- Convert BET to m² g⁻¹.
- Convert pore volume to cm³ g⁻¹.
- Convert d-spacing to nm.
- Convert percentages to `%` or `at.%` consistently.
- Parse ranges like `800-900`, `~800`, `ca. 800`, `800 °C`.
- Preserve raw strings.

Output flags:

- `UNIT_CONVERTED`
- `UNIT_UNKNOWN`
- `NUMERIC_PARSE_FAILED`
- `RANGE_VALUE`
- `LOW_EXTRACTION_CONFIDENCE`

### Agent 3 — Domain Rule Checker

Goal: flag impossible, implausible, or conditionally suspicious values.

Default biomass-carbon energy-storage ranges are in `templates/domain_rules.yaml`.

Tasks:

- Check physical ranges.
- Check system-specific compatibility.
- Check whether performance fields match the system.
- Flag likely decimal-place/unit mistakes.
- Flag missing critical testing conditions.

Output flags:

- `IMPOSSIBLE_VALUE`
- `IMPLAUSIBLE_VALUE`
- `UNIT_SCALE_SUSPECT`
- `SYSTEM_CONDITION_MIXING_RISK`
- `CRITICAL_CONDITION_MISSING`

### Agent 4 — Duplicate and Consistency Auditor

Goal: detect repeated samples, copied rows, contradictions, and same-paper inconsistencies.

Tasks:

- Detect duplicate DOI + sample_name + key descriptors.
- Detect same sample with conflicting values.
- Detect row-shift patterns: many values from adjacent columns look plausible only after shifting.
- Detect repeated AI artifacts such as identical values across unrelated samples.

Output flags:

- `DUPLICATE_RECORD`
- `CONFLICTING_DUPLICATE`
- `POSSIBLE_ROW_SHIFT`
- `PAPER_INTERNAL_CONFLICT`
- `AI_COPY_ARTIFACT`

### Agent 5 — Statistical Outlier Agent

Goal: identify outliers without deleting them.

Tasks:

- Compute robust z-scores using median and MAD.
- Compute IQR fences by system and key subgroup.
- Run leave-one-paper-out influence checks for correlations when enough data exist.
- Flag values that strongly change conclusions.

Output flags:

- `ROBUST_OUTLIER`
- `GROUP_OUTLIER`
- `HIGH_INFLUENCE_RECORD`
- `HIGH_INFLUENCE_PAPER`
- `N_TOO_SMALL_FOR_STATISTICS`

### Agent 6 — Bias and Comparability Agent

Goal: identify systematic bias, not just point outliers.

Tasks:

- Check whether one paper dominates high/low performance.
- Check whether missingness is systematic by paper, system, year, or extraction source.
- Check whether AI extraction confidence correlates with performance or descriptors.
- Check whether conditions differ between groups being compared.

Output flags:

- `PAPER_DOMINANCE_BIAS`
- `MISSINGNESS_BIAS`
- `EXTRACTION_CONFIDENCE_BIAS`
- `CONDITION_CONFOUNDING`
- `NON_COMPARABLE_GROUPS`

### Agent 7 — Decision Integrator

Goal: convert all flags into action labels and a secondary verification queue.

Decision logic:

- `REVIEW_P0`: impossible/implausible value, conflicting duplicate, source evidence missing for a conclusion-critical field, likely unit scale error, or high-influence outlier.
- `REVIEW_P1`: group outlier, ambiguous schema, missing critical condition, paper dominance, or condition confounding.
- `KEEP_SENSITIVITY`: plausible but outlying or conditionally comparable record.
- `KEEP_MAIN`: no major flags and required fields present.
- `EXCLUDE_MAIN`: confirmed wrong, non-target system/material, duplicated row, or not a biomass-derived carbon sample.

## Required outputs

Create an output folder named `cleaning_outputs/YYYYMMDD_HHMM/` containing:

1. `cleaned_database.xlsx` or `.csv` — raw + normalized fields + flags + final action.
2. `flagged_records.xlsx` or `.csv` — all records with any flag.
3. `secondary_review_queue.xlsx` or `.csv` — paper/sample/field list ranked P0/P1/P2.
4. `paper_level_audit.csv` — paper-level missingness, dominance, and high-influence summary.
5. `correction_log.csv` — all corrections and conversions.
6. `outlier_sensitivity_plan.md` — what to include/exclude in main vs sensitivity analysis.
7. `data_quality_report.md` — concise human-readable summary.
8. `agent_reports/` — individual agent reports.

## Report format

The final answer to the user should include:

- Number of raw rows.
- Number of rows retained for main analysis.
- Number of rows moved to sensitivity analysis.
- Number of records requiring P0/P1 review.
- Top 10 paper/sample/field combinations requiring secondary verification.
- Clear distinction between “statistical outlier”, “likely extraction error”, and “incomparable testing condition”.
- No unsupported deletion claims.

## Safe default stance

Use the following wording when reporting results:

> I did not permanently delete outliers. I preserved raw rows, assigned exclusion/review labels, and separated main-analysis records from sensitivity-analysis records. Values flagged as extraction-risk or high-influence should be checked against the original paper/SI before they support a manuscript claim.

