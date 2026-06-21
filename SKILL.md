# ai-extracted-data-cleaner

## Purpose

This skill cleans, normalizes, and audits AI-extracted scientific literature datasets for chemical and materials engineering.

Use this skill when the user has data extracted from papers by ChatGPT, OCR, MinerU, PDF parsers, manual curation, or mixed spreadsheets, and wants to prepare the data for database construction, review-manuscript source data, correlation analysis, Bayesian-optimization replay, or machine-learning analysis.

## Chinese positioning

面向化工与材料文献数据的 AI 提取结果清洗 Skill：用于字段标准化、单位统一、异常值识别、重复样本检查和二次原文核查队列生成。

## Version

Current package version: `1.1.0`.

Important v1.1.0 behavior:

- Default YAML configs are bundled inside the Python package, so the CLI works after normal installation.
- The CLI accepts custom `--aliases` and `--rules` paths.
- The workflow writes `cleaning_manifest.json` with version, input path, output files, flags, corrections, and decision.
- Empty flag files retain headers for downstream scripts.
- `mAh/g` and `Ah/g` are distinguished to avoid false capacity scaling.

## Core tasks

1. Normalize field names.
2. Harmonize units.
3. Detect physically implausible values.
4. Detect duplicate or near-duplicate samples.
5. Generate a secondary source-verification queue.
6. Preserve all corrections in a correction log.
7. Pass intermediate state using JSON files to reduce token usage.

## Expected inputs

- Excel or CSV extracted from literature.
- Optional source-location columns such as paper_id, DOI, table number, figure number, SI page, or source note.
- Optional system labels such as SIB, LIB, aqueous supercapacitor, battery, catalyst, adsorbent, etc.

## Expected outputs

- cleaned_database.csv
- flagged_records.csv
- secondary_review_queue.csv
- paper_level_audit.csv
- correction_log.csv
- data_quality_report.md
- cleaning_manifest.json
- state/*.json

## Agent protocol

Agents should not repeatedly read the full dataset when avoidable. The first pass creates compact JSON state files. Later agents read only relevant JSON slices.

Workflow:

1. Schema Agent -> state/01_schema_map.json
2. Unit Agent -> state/02_unit_normalized.json
3. Physics Agent -> state/03_physics_flags.json
4. Duplicate Agent -> state/04_duplicate_flags.json
5. Review Queue Agent -> secondary_review_queue.csv and data_quality_report.md

## Severity levels

- P0: must fix before reuse.
- P1: strongly recommended source verification.
- P2: optional but useful improvement.

## Important behavior

Do not silently overwrite suspicious values without recording the original value, cleaned value, confidence, and reason in correction_log.csv.

Do not remove rows unless the user explicitly asks for row deletion. Prefer flagging rows for source verification.

For high-stakes research conclusions, recommend checking the original paper or SI rather than treating the cleaned value as final truth.

If the cleaned data will be used for ML/BO, prioritize verification of target variables, units, duplicate samples, paper-level dominance, and missing engineering parameters.
