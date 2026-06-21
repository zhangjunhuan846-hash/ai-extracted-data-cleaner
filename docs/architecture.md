# Architecture

`ai-extracted-data-cleaner` follows a layered design:

1. Deterministic baseline scripts for reproducible cleaning.
2. Package-bundled YAML configs for field aliases and validation rules.
3. JSON state files for token-saving multi-agent workflows.
4. Human-readable Chinese reports for source verification.
5. A manifest file that records the version, input, output files, flags, corrections, and final decision.

## Data flow

```text
raw table
  -> schema mapping
  -> unit normalization
  -> physics-aware validation
  -> duplicate detection
  -> secondary review queue
  -> quality report + manifest
```

## Why JSON states?

For large materials databases, repeatedly feeding the full spreadsheet to every LLM agent is expensive and unstable. The JSON states provide compact summaries and flagged slices so that each agent receives only the context it needs.

## Why not auto-delete rows?

AI-extracted literature data often contains ambiguous errors: OCR mistakes, unit mistakes, table-row shifts, and merged testing conditions. Deleting rows automatically can destroy traceability. The default behavior is therefore to preserve rows, normalize only high-confidence unit cases, and send suspicious records into the secondary review queue.
