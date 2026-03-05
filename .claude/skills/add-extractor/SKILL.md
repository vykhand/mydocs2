---
name: add-extractor
description: Scaffold a new extraction schema under mydocs/extracting/schemas/ with config YAML.
argument-hint: [schema name, e.g. "invoice"]
---

# Add Extractor

You are scaffolding a new extraction schema for the extraction engine.

## Steps

1. Parse the schema name from: `$ARGUMENTS`
2. Read `docs/specs/extracting-engine.md` and `docs/EXTRACTING.md` to understand the extraction system
3. Read an existing schema (e.g., `mydocs/extracting/schemas/receipt.py`) as a reference
4. Read existing config YAML under `config/extracting/` for the config pattern
5. Update the spec (`docs/specs/extracting-engine.md`) with the new schema
6. Create the schema file at `mydocs/extracting/schemas/{name}.py` following existing patterns
7. Create the config YAML under `config/extracting/`
8. Register the schema in `mydocs/extracting/registry.py` if needed
9. Update `docs/EXTRACTING.md`

## Rules

- Follow the pattern established by existing schemas (e.g., `receipt.py`)
- Use Pydantic models for all data structures
- Config YAML should be under `config/extracting/`
