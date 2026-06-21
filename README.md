# ai-extracted-data-cleaner

A local skill for cleaning AI-extracted scientific literature data.

## Install

Copy this folder into your local skills directory, for example:

```text
skills/ai-extracted-data-cleaner/
```

Then in Codex/OpenClaw, use a prompt like:

```text
Use the ai-extracted-data-cleaner skill. Clean data/extracted/my_ai_extracted_data.xlsx using the biomass_carbon_energy_storage profile. Preserve raw values, normalize units, flag outliers and bias, and produce a secondary verification queue of paper/sample/field combinations that must be checked against the original papers/SI.
```

## Quick script usage

```bash
python scripts/clean_ai_extracted_data.py --input data/extracted/my_ai_extracted_data.xlsx --outdir cleaning_outputs/run_001 --profile biomass_carbon_energy_storage --target ICE_percent
```

The script is a practical baseline. For high-stakes manuscript use, combine script output with the multi-agent protocol in `SKILL.md` and `AGENTS.md`.

## Outputs

- `cleaned_database.csv`
- `flagged_records.csv`
- `secondary_review_queue.csv`
- `paper_level_audit.csv`
- `correction_log.csv`
- `data_quality_report.md`
