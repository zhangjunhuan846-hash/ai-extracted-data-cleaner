# Multi-Agent Protocol

This file defines the recommended multi-agent workflow for `ai-extracted-data-cleaner`.

## Principle

Current workflow version: `1.1.0`.

The dataset may be large. Do not pass the entire spreadsheet to every agent. Instead, produce compact JSON state files that contain only the information required for the next audit step.

## Agent 01: Schema Agent

**Input**
- raw spreadsheet columns
- first 5–20 sample rows
- config/field_aliases.yaml

**Output**
- state/01_schema_map.json

**Responsibilities**
- Map raw column names to canonical fields.
- Identify unknown columns.
- Identify missing recommended columns.
- Flag ambiguous column mappings.

## Agent 02: Unit Agent

**Input**
- state/01_schema_map.json
- raw numeric values and unit strings

**Output**
- state/02_unit_normalized.json
- correction_log.csv

**Responsibilities**
- Convert recognized units to canonical units.
- Preserve original values.
- Record unit conversions and uncertain conversions.

## Agent 03: Physics Agent

**Input**
- state/02_unit_normalized.json
- config/validation_rules.yaml

**Output**
- state/03_physics_flags.json
- flagged_records.csv

**Responsibilities**
- Detect physically impossible values.
- Detect values outside typical materials ranges.
- Assign P0/P1/P2 severity.

## Agent 04: Duplicate Agent

**Input**
- cleaned table
- paper_id, sample_id, sample_name, key descriptor columns

**Output**
- state/04_duplicate_flags.json

**Responsibilities**
- Detect exact duplicate sample IDs.
- Detect duplicate paper_id + sample_name.
- Detect near-duplicate rows based on key descriptor and target values.

## Agent 05: Review Queue Agent

**Input**
- all state JSON files
- flagged_records.csv
- correction_log.csv

**Output**
- secondary_review_queue.csv
- paper_level_audit.csv
- data_quality_report.md
- cleaning_manifest.json

**Responsibilities**
- Prioritize samples requiring original-paper verification.
- Group risks by paper and sample.
- Generate a readable Chinese quality-control report.

## Conflict handling

If a correction is high impact and uncertain, do not accept it automatically. Put it into the secondary review queue.

Examples:
- BET = 12300 m2/g: do not automatically change to 1230. Mark as P1/P0 and require source check.
- ICE = 105%: mark P0 and require source check.
- d002 = 3.72 with unknown unit: infer possible Å only if context supports it; otherwise flag.
