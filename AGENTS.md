# Agent Protocol for AI-Extracted Data Cleaning

## Global rules

- Preserve raw values.
- Never silently overwrite or delete records.
- Treat AI-extracted values as provisional until supported by source text, page/table references, or internal consistency.
- Distinguish three categories clearly:
  1. extraction error risk,
  2. statistical outlier,
  3. non-comparable experimental condition.
- For manuscript use, do not convert flagged values into strong mechanistic claims without manual verification.
- For sample-level literature databases, run available-case analysis but report `n` for every variable pair.
- For correlations, Spearman is the default. Grey/de-emphasize `n < 10`; treat `n < 5` as exploratory only.
- Outliers are not deleted by default. Use exclusion only after rule-based or source-based justification.
- Same-paper multiple samples require paper-level sensitivity checks.

## Review priority labels

### P0 — Must check before use

Assign P0 when any of the following is true:

- impossible physical value;
- likely unit scale error;
- conflicting duplicate;
- missing source evidence for a conclusion-critical value;
- high-influence record changes the sign or practical meaning of a trend;
- suspected row shift or copied table artifact;
- performance value mismatched with system or test condition.

### P1 — Should check before figure/manuscript claim

Assign P1 when any of the following is true:

- plausible but extreme value;
- missing key condition such as current density, voltage window, electrolyte, mass loading;
- schema mapping ambiguity;
- sample identity ambiguity;
- one paper dominates a subgroup;
- condition confounding affects comparison.

### P2 — Low-priority documentation check

Assign P2 when any of the following is true:

- minor formatting issue;
- source page missing but value is non-critical;
- redundant metadata missing;
- value is retained only for descriptive statistics.

## Final decision labels

- `KEEP_MAIN`: no major risk; acceptable for main analysis.
- `KEEP_SENSITIVITY`: plausible but should be isolated in sensitivity analysis.
- `REVIEW_P0`: cannot support analysis until manually checked.
- `REVIEW_P1`: usable only with caution; check before final figure/text.
- `EXCLUDE_MAIN`: non-target record, confirmed duplicate, or confirmed invalid.

## Bias checks

Always check at least:

- paper-level dominance;
- year/journal/source missingness;
- system/electrolyte/current-density confounding;
- extraction confidence vs target-value relationship;
- whether a single paper creates a correlation sign.

## Output discipline

Every flagged item must include:

- `paper_id` or DOI/title;
- `sample_id` or sample name;
- field name;
- raw value;
- normalized value if available;
- flag;
- priority;
- reason;
- recommended manual check.
