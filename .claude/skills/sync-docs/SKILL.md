---
name: sync-docs
description: After implementation, scan changed files and update corresponding documentation to reflect what changed.
allowed-tools: Read, Edit, Glob, Grep, Bash
---

# Sync Docs

You are updating documentation after code changes have been made.

## Steps

1. Run `git diff --name-only HEAD~1` (or check staged changes) to identify which files changed
2. Read `CLAUDE.md` and map each changed file to its task area using the Read-First table
3. For each affected task area that has a doc file (e.g., `docs/BACKEND.md`, `docs/UI.md`):
   - Read the current doc
   - Read the changed source files
   - Update the doc to reflect the new state of the code
4. If API routes were added or modified, update `openapi.yaml`
5. Summarize all documentation updates made

## Rules

- Only modify files under `docs/` and `openapi.yaml`
- Never modify source code — this skill is docs-only
- Match the style and structure of existing documentation
- If a doc file doesn't exist yet for an area, note it but don't create one unless asked
