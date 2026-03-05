---
name: update-specs
description: Interactively walk through all specs affected by a planned change and update them before implementation.
argument-hint: [description of planned change]
allowed-tools: Read, Edit, Glob, Grep, AskUserQuestion
---

# Update Specs

You are updating specification documents before implementing a change.

## Steps

1. Read `CLAUDE.md` and identify which task areas are affected by the planned change: `$ARGUMENTS`
2. For each affected area, read the corresponding spec file from the Read-First table in `CLAUDE.md`
3. For each spec, propose the specific sections that need updating and what changes are needed
4. Ask the user to confirm or adjust each proposed spec update
5. Apply the approved changes to each spec file
6. Summarize all spec changes made

## Rules

- Only modify files under `docs/specs/`
- Never modify source code — this skill is spec-only
- If a spec file doesn't exist yet, create it following the structure of existing specs
- Always show the user what you plan to change before editing
