# mydocs CLI Reference

> **Auto-generated from code inspection.** Describes the current state of the CLI as implemented in `mydocs/cli/`.
>
> **Spec**: [docs/specs/cli.md](specs/cli.md)

---

## Installation & Entry Point

Defined in `pyproject.toml`:

```toml
[project.scripts]
mydocs = "mydocs.cli.main:cli_main"
```

After `uv` installation, the `mydocs` command is available.

---

## Global Options

Available on all subcommands:

| Flag | Default | Description |
|------|---------|-------------|
| `-v` / `--verbose` | `False` | Enable verbose logging (sets `LOG_LEVEL=DEBUG`) |
| `--config-root` | `None` (uses default) | Path to configuration directory |
| `--data-folder` | `None` (uses default) | Path to data directory |
| `--env-file` | `None` | Path to `.env` file (loaded with `dotenv`) |

Defaults are resolved from the `mydocs.config` module, which reads `CONFIG_ROOT` and `DATA_FOLDER` environment variables, falling back to `<project_root>/config` and `<project_root>/data`.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Invalid arguments / usage error |
| `3` | Connection error (MongoDB, Azure DI, pymongo) |
| `4` | Document not found (`ValueError`) |

---

## Commands

### `mydocs ingest <source>`

Ingest files into the system. Wraps `ingest_files()` from `mydocs.parsing.pipeline`.

```
mydocs ingest <source>
    --mode managed|external     # Storage mode (default: managed)
    --tags tag1,tag2            # Comma-separated tags to assign
    --no-recursive              # Don't recurse into subdirectories
    --output json|table|quiet   # Output format (default: table)
```

**Examples**:

```bash
# Ingest a directory (recursive by default)
mydocs ingest ./documents/

# Ingest a single file in external mode with tags
mydocs ingest ./report.pdf --mode external --tags quarterly,finance

# Ingest without recursion, output as JSON
mydocs ingest /data/pdfs --no-recursive --output json

# Quiet output (just counts)
mydocs ingest ./files/ --output quiet
```

**Implementation notes**: Calls `ingest_files(source, storage_mode, tags, recursive)`. Returns ingested documents and skipped files.

---

### `mydocs parse`

Parse documents. Wraps `parse_document()` and `batch_parse()` from `mydocs.parsing.pipeline`.

```
mydocs parse <doc_id>           # Parse a single document
mydocs parse --batch            # Batch parse documents
    --tags tag1,tag2            # Filter by tags (batch mode)
    --status new                # Filter by status (batch mode, default: new)
    --output json|table|quiet   # Output format (default: table)
```

**Examples**:

```bash
# Parse a single document by ID
mydocs parse abc123

# Batch parse all new documents
mydocs parse --batch

# Batch parse documents with specific tags
mydocs parse --batch --tags quarterly --status new

# JSON output for scripting
mydocs parse abc123 --output json
```

**Implementation notes**: If neither `doc_id` nor `--batch` is provided, prints an error and exits with code 2.

---

### `mydocs search <query>`

Search documents and pages. Wraps the retrieval engine search function.

```
mydocs search <query>
    --mode fulltext|vector|hybrid   # Search mode (default: hybrid)
    --target pages|documents        # Search target (default: pages)
    --top-k N                       # Max results (default: 10)
    --tags tag1,tag2                # Filter by tags
    --output json|table|quiet|full  # Output format (default: table)
```

**Examples**:

```bash
# Basic hybrid search
mydocs search "quarterly revenue"

# Vector-only search with limited results
mydocs search "budget analysis" --mode vector --top-k 5

# Search documents (not pages) with tag filter
mydocs search "policy" --target documents --tags legal --output json

# Full output — includes content text for each result
mydocs search "financial summary" --output full

# Quiet mode — prints only the total count
mydocs search "invoice" --output quiet
```

**Implementation notes**: When `--output full` is used, the code sets `include_content_fields = ["content", "content_markdown"]` on the search request to retrieve content for display.

---

### `mydocs docs`

Document management subcommands.

#### `mydocs docs list`

```
mydocs docs list
    --status new|parsed|failed|...  # Filter by document status
    --tags tag1,tag2                # Filter by tags
    --output json|table|quiet|full  # Output format (default: table)
```

**Examples**:

```bash
# List all documents
mydocs docs list

# List only parsed documents
mydocs docs list --status parsed

# List documents tagged "finance"
mydocs docs list --tags finance

# JSON output for scripting
mydocs docs list --output json
```

#### `mydocs docs show <doc_id>`

```
mydocs docs show <doc_id>
    --output json|table|quiet|full  # Output format (default: table)
```

**Examples**:

```bash
# Show document details as a key-value table
mydocs docs show abc123

# Full output — includes document content
mydocs docs show abc123 --output full

# JSON output
mydocs docs show abc123 --output json
```

#### `mydocs docs pages <doc_id>`

```
mydocs docs pages <doc_id>
    --page N                        # Show a single page by number
    --output json|table|quiet|full  # Output format (default: table)
```

The `--page` flag filters to a single page by page number.

**Examples**:

```bash
# List all pages of a document
mydocs docs pages abc123

# Show only page 3
mydocs docs pages abc123 --page 3

# JSON output
mydocs docs pages abc123 --output json
```

#### `mydocs docs tag <doc_id> <tags>`

```
mydocs docs tag <doc_id> <tags>
    --remove                        # Remove tags instead of adding
```

**Examples**:

```bash
# Add tags to a document
mydocs docs tag abc123 finance,quarterly

# Remove tags from a document
mydocs docs tag abc123 quarterly --remove
```

#### `mydocs docs delete <doc_id>`

```
mydocs docs delete <doc_id>
    --force                         # Skip confirmation prompt
```

**Examples**:

```bash
# Delete with confirmation prompt
mydocs docs delete abc123

# Delete without confirmation
mydocs docs delete abc123 --force
```

The `--output` flag is defined at the parent `docs` parser level with choices `json|table|quiet|full`, shared by all subcommands.

---

### `mydocs cases`

Case management subcommands.

#### `mydocs cases list`

```
mydocs cases list
    --search <term>                 # Search cases by name (regex, case-insensitive)
    --output json|table|quiet       # Output format (default: table)
```

**Examples**:

```bash
# List all cases (sorted by creation date, newest first)
mydocs cases list

# Search cases by name
mydocs cases list --search "Q4"

# JSON output
mydocs cases list --output json
```

#### `mydocs cases show <case_id>`

```
mydocs cases show <case_id>
    --output json|table|quiet       # Output format (default: table)
```

**Examples**:

```bash
# Show case details as key-value table
mydocs cases show abc123

# JSON output
mydocs cases show abc123 --output json
```

#### `mydocs cases create <name>`

```
mydocs cases create <name>
    --description "text"            # Optional description
    --output json|table|quiet       # Output format (default: table)
```

**Examples**:

```bash
# Create a new case
mydocs cases create "Q4 Invoices"

# Create with description
mydocs cases create "Q4 Invoices" --description "All invoices from Q4 2024"

# JSON output (useful for capturing the new case ID)
mydocs cases create "Audit 2024" --output json
```

#### `mydocs cases update <case_id>`

```
mydocs cases update <case_id>
    --name "new name"               # New case name
    --description "new desc"        # New case description
    --output json|table|quiet       # Output format (default: table)
```

**Examples**:

```bash
# Update case name
mydocs cases update abc123 --name "Q4 2024 Invoices"

# Update description
mydocs cases update abc123 --description "Updated description"

# Update both
mydocs cases update abc123 --name "New Name" --description "New desc"
```

**Implementation notes**: Raises an error if neither `--name` nor `--description` is provided.

#### `mydocs cases delete <case_id>`

```
mydocs cases delete <case_id>
    --force                         # Skip confirmation prompt
```

**Examples**:

```bash
# Delete with confirmation
mydocs cases delete abc123

# Force delete
mydocs cases delete abc123 --force
```

#### `mydocs cases add-docs <case_id> <doc_ids>`

```
mydocs cases add-docs <case_id> <doc_ids>   # doc_ids is comma-separated
```

**Examples**:

```bash
# Add documents to a case
mydocs cases add-docs abc123 doc1,doc2,doc3
```

#### `mydocs cases remove-doc <case_id> <doc_id>`

```
mydocs cases remove-doc <case_id> <doc_id>
```

**Examples**:

```bash
# Remove a document from a case
mydocs cases remove-doc abc123 doc1
```

#### `mydocs cases docs <case_id>`

```
mydocs cases docs <case_id>
    --output json|table|quiet       # Output format (default: table)
```

**Examples**:

```bash
# List documents in a case
mydocs cases docs abc123

# JSON output
mydocs cases docs abc123 --output json
```

The `--output` flag is defined at the parent `cases` parser level with choices `json|table|quiet`, shared by all subcommands.

---

### `mydocs extract`

Extract fields from documents in a case using LLM-based extraction.

#### `mydocs extract run <case_id>`

```
mydocs extract run <case_id>
    --document-type generic                 # Document type (default: generic)
    --fields field1,field2                  # Comma-separated field names (default: all)
    --content-mode markdown|html            # Content mode (default: markdown)
    --reference-granularity full|page|none  # Reference granularity (default: none)
    --output json|table|quiet               # Output format (default: table)
```

**Examples**:

```bash
# Extract all fields for all documents in a case
mydocs extract run abc123

# Extract specific fields
mydocs extract run abc123 --fields summary,total_amount

# Specify document type
mydocs extract run abc123 --document-type generic --fields summary

# Use HTML content mode with page-level references
mydocs extract run abc123 --content-mode html --reference-granularity page

# JSON output
mydocs extract run abc123 --output json
```

**Implementation notes**: Processes documents one at a time in a loop, printing progress to stderr. Each document gets its own `ExtractionRequest`. Errors per document are caught and printed to stderr without aborting the run.

#### `mydocs extract results <case_id>`

```
mydocs extract results <case_id>
    --output json|table|quiet       # Output format (default: table)
```

**Examples**:

```bash
# Show stored extraction results
mydocs extract results abc123

# JSON output
mydocs extract results abc123 --output json
```

The `--output` flag is defined at the parent `extract` parser level, shared by both `run` and `results`.

---

### `mydocs sync`

Storage-to-DB synchronization. Scans managed storage and compares with database state to rebuild lost records. See [sync spec](specs/sync.md) for the full algorithm.

#### `mydocs sync status`

Scan managed storage and database, display a sync plan without executing.

```
mydocs sync status
    --scan-path PATH                    # Override managed storage path (default: data/managed/)
    --verify-content                    # Verify file content via SHA256 (slower)
    --output json|table|quiet           # Output format (default: table)
```

**Examples**:

```bash
# Show sync status (what would need to be done)
mydocs sync status

# Verify content integrity via SHA256
mydocs sync status --verify-content

# JSON output for scripting
mydocs sync --output json status
```

#### `mydocs sync run`

Execute a sync plan — restore documents from sidecars, write missing sidecars, flag orphans.

```
mydocs sync run
    --scan-path PATH                    # Override managed storage path
    --verify-content                    # Verify file content via SHA256
    --reparse                           # Re-parse restored documents from .di.json cache
    --actions restore,sidecar_missing   # Comma-separated actions to execute (default: all)
    --dry-run                           # Show plan without executing
    --output json|table|quiet           # Output format (default: table)
```

Actions: `restore`, `reparse`, `orphaned_db`, `verified`, `sidecar_missing`.

**Examples**:

```bash
# Full sync (restore + write sidecars + flag orphans)
mydocs sync run

# Restore documents and re-parse from cache
mydocs sync run --reparse

# Only restore, skip other actions
mydocs sync run --actions restore

# Dry run — show what would happen
mydocs sync run --dry-run

# JSON output
mydocs sync --output json run --reparse
```

#### `mydocs sync write-sidecars`

Write missing metadata sidecars for managed files that have DB records but no sidecar on disk.

```
mydocs sync write-sidecars
    --scan-path PATH                    # Override managed storage path
    --output json|table|quiet           # Output format (default: table)
```

**Examples**:

```bash
# Write sidecars for all managed files missing them
mydocs sync write-sidecars
```

#### `mydocs sync migrate`

Migrate documents between storage backends. Copies managed files and sidecars to the target backend. For external documents, only the sidecar JSON is copied (the source file stays in place).

Migration is a **storage-only** operation — no database writes. After migration, rebuild the DB from the target backend:

```
mydocs sync migrate
    --from local|azure_blob         # Source storage backend (required)
    --to local|azure_blob           # Target storage backend (required)
    --delete-source                 # Delete source files after successful copy
    --dry-run                       # Show migration plan without executing
```

**Examples**:

```bash
# Preview what would be migrated
mydocs sync migrate --from local --to azure_blob --dry-run

# Migrate from local to Azure Blob Storage
mydocs sync migrate --from local --to azure_blob

# Migrate and clean up local source files
mydocs sync migrate --from local --to azure_blob --delete-source

# After migration, rebuild DB from target backend
mydocs sync run --backend azure_blob

# Reverse migration (Azure Blob → local)
mydocs sync migrate --from azure_blob --to local
```

The `--output` flag is defined at the parent `sync` parser level with choices `json|table|quiet`, shared by all subcommands.

**Implementation notes**: All sync subcommands call `build_sync_plan()` from `mydocs.sync.scanner` first, then `execute_sync_plan()` from `mydocs.sync.reconciler` for execution. The `write-sidecars` command is a shortcut that filters to only `sidecar_missing` actions.

---

### `mydocs config`

Configuration utilities.

#### `mydocs config show`

Show current parser configuration. Outputs YAML by default, JSON when `--output json`.

```
mydocs config show
    --output json|table|quiet       # Output format (default: table)
```

**Examples**:

```bash
# Show config as YAML
mydocs config show

# Show config as JSON
mydocs config show --output json
```

#### `mydocs config validate`

Validate configuration files. Attempts to instantiate `ParserConfig()` and reports success or failure.

```
mydocs config validate
```

**Examples**:

```bash
mydocs config validate
# Output: "Configuration is valid." or error details
```

#### `mydocs config env`

Show environment variable values with secrets redacted (first 4 characters shown, rest replaced with `****`).

```
mydocs config env
```

**Examples**:

```bash
mydocs config env
# Output:
# SERVICE_NAME=mydocs
# ROOT_FOLDER=/app
# MONGO_URL=mongodb://localhost:27017
# MONGO_PASSWORD=pass****
# AZURE_DI_API_KEY=abc1****
```

**Displayed variables**: `SERVICE_NAME`, `ROOT_FOLDER`, `DATA_FOLDER`, `CONFIG_ROOT`, `LOG_LEVEL`, `MONGO_URL`, `MONGO_USER`, `MONGO_PASSWORD` (redacted), `MONGO_DB_NAME`, `AZURE_DI_ENDPOINT`, `AZURE_DI_API_KEY` (redacted), `AZURE_DI_API_VERSION`, `AZURE_OPENAI_API_KEY` (redacted), `AZURE_OPENAI_API_BASE`, `AZURE_OPENAI_API_VERSION`.

---

### `mydocs migrate`

Database migration management.

#### `mydocs migrate run`

Run all pending migrations.

```
mydocs migrate run
```

**Examples**:

```bash
mydocs migrate run
# Output: table of executed migrations, or "No pending migrations."
```

#### `mydocs migrate list`

List available migration scripts and their status.

```
mydocs migrate list
```

**Examples**:

```bash
mydocs migrate list
# Output: table with Migration, Status, Run At columns
```

**Note**: The `migrate` handlers are synchronous functions (the underlying migration functions are sync). This is intentional.

---

## Output Formats

All subcommands support the `--output` flag (where documented):

| Mode | Description |
|------|-------------|
| `table` | Human-readable column-aligned table (default) |
| `json` | Machine-readable JSON output |
| `quiet` | Minimal output (IDs, counts only) |
| `full` | Verbose output with all fields (only `search` and `docs show`) |

The `table` format uses a built-in column-alignment implementation in `mydocs/cli/formatters.py` — no external library.

---

## Error Handling

- Normal output goes to **stdout**
- Errors and progress indicators go to **stderr**
- Connection errors (MongoDB / pymongo) show troubleshooting hints pointing to `mydocs config env`
- In `--verbose` mode, full tracebacks are printed on unhandled exceptions

---

## Resolved Spec Deviations

The following deviations were found between the spec and code. All have been resolved:

| # | Area | Resolution |
|---|------|------------|
| 1 | Global options | **Spec fixed** — updated to reflect config-module defaults instead of CWD-relative paths |
| 2 | `docs pages` | **Spec fixed** — added `--page N` flag documentation |
| 3 | `docs` output | **Spec fixed** — unified `--output` choices as shared parent-level flag |
| 4 | `cases` output | **Spec fixed** — unified `--output` choices as shared parent-level flag |
| 5 | `migrate` handlers | **Skipped** — sync handlers are intentional (underlying functions are sync) |
| 6 | `migrate` output | **Skipped** — no `--output` flag needed, output is simple enough |
| 7 | `extract run` | **Code fixed** — added `--content-mode` and `--reference-granularity` CLI flags |
| 8 | `config show` | **Spec fixed** — documented YAML default output format |

---

## Package Structure (actual)

```
mydocs/
  cli/
    __init__.py
    main.py                       # Entry point, argparse, async bridge, error handling
    commands/
      __init__.py
      ingest.py                   # mydocs ingest
      parse.py                    # mydocs parse
      search.py                   # mydocs search
      docs.py                     # mydocs docs {list,show,pages,tag,delete}
      cases.py                    # mydocs cases {list,show,create,update,delete,add-docs,remove-doc,docs}
      extract.py                  # mydocs extract {run,results}
      sync.py                     # mydocs sync {status,run,write-sidecars}
      config.py                   # mydocs config {show,validate,env}
      migrate.py                  # mydocs migrate {run,list}
    formatters.py                 # Output formatting (table, json, quiet, full)
```

This matches the spec's package structure.