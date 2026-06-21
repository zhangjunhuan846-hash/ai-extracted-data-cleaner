# Architecture

`ai-extracted-data-cleaner` follows a layered design:

1. Deterministic baseline scripts for reproducible cleaning.
2. JSON state files for token-saving multi-agent workflows.
3. Human-readable Chinese reports for source verification.

## Data flow

```text
raw table
  -> schema mapping
  -> unit normalization
  -> physics-aware validation
  -> duplicate detection
  -> secondary review queue
  -> quality report
```

## Why JSON states?

For large materials databases, repeatedly feeding the full spreadsheet to every LLM agent is expensive and unstable. The JSON states provide compact summaries and flagged slices so that each agent receives only the context it needs.
