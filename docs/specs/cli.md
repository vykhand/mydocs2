# CLI Specification

**Package**: `mydocs.cli`
**Version**: 1.0
**Status**: Draft

**Related Specs**: [parsing-engine.md](parsing-engine.md) (pipeline functions), [retrieval-engine.md](retrieval-engine.md) (search), [backend.md](backend.md) (HTTP API), [migrations.md](migrations.md) (database migrations)

---

## 1. Overview

The `mydocs` CLI provides command-line access to the parsing pipeline, retrieval engine, document management, and database migrations. It is a thin wrapper around the existing async Python functions, using `argparse` for argument parsing and an async bridge for running coroutines.

---

## 2. Entry Point

Defined in `pyproject.toml`:

```toml
[project.scripts]
mydocs = "mydocs.cli.main:cli_main"
```

After installation via `uv`, the `mydocs` command is available system-wide.

---

## 3. Architecture

### 3.1 Async Bridge

The CLI uses an async bridge pattern to call async pipeline functions from synchronous `argparse` handlers:

```python
import asyncio

def cli_main():
    """Synchronous entry point for the CLI."""
    args = parse_args()
    asyncio.run(async_main(args))

async def async_main(args):
    """Async dispatcher that routes to subcommand handlers."""
    await args.func(args)
```

### 3.2 Package Structure

```
mydocs/
  cli/
    __init__.py
    main.py                     # Entry point, argparse setup, async bridge
    commands/
      __init__.py
      ingest.py                 # mydocs ingest
      parse.py                  # mydocs parse
      search.py                 # mydocs search
      docs.py                   # mydocs docs
      config.py                 # mydocs config
      migrate.py                # mydocs migrate
    formatters.py               # Output formatting (table, json, quiet, full)
```

---

## 4. Subcommands

### 4.1 `mydocs ingest <source>`

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
mydocs ingest ./documents/
mydocs ingest ./report.pdf --mode external --tags quarterly,finance
mydocs ingest /data/pdfs --no-recursive --output json
```

### 4.2 `mydocs parse`

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
mydocs parse abc123
mydocs parse --batch --tags quarterly --status new
```

### 4.3 `mydocs search <query>`

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
mydocs search "quarterly revenue"
mydocs search "budget analysis" --mode vector --top-k 5
mydocs search "policy" --target documents --tags legal --output json
```

### 4.4 `mydocs docs`

Document management subcommands.

```
mydocs docs list                    # List all documents
    --status new|parsed|failed      # Filter by status
    --tags tag1,tag2                # Filter by tags
    --output json|table|quiet       # Output format (default: table)

mydocs docs show <doc_id>           # Show document details
    --output json|table|full        # Output format (default: table)

mydocs docs pages <doc_id>          # List pages of a document
    --output json|table|quiet       # Output format (default: table)

mydocs docs tag <doc_id> <tags>     # Add tags to a document
    --remove                        # Remove tags instead of adding

mydocs docs delete <doc_id>         # Delete a document and its pages
    --force                         # Skip confirmation prompt
```

### 4.5 `mydocs config`

Configuration utilities.

```
mydocs config show                  # Show current parser configuration
mydocs config validate              # Validate configuration files
mydocs config env                   # Show environment variable values (redacted secrets)
```

### 4.6 `mydocs migrate`

Database migration management. See [migrations.md](migrations.md).

```
mydocs migrate run                  # Run all pending migrations
mydocs migrate list                 # List available migration scripts
```

---

## 5. Output Formatting

All subcommands support the `--output` flag with the following modes:

| Mode | Description |
|------|-------------|
| `table` | Human-readable table format (default) |
| `json` | Machine-readable JSON output |
| `quiet` | Minimal output (IDs and counts only) |
| `full` | Verbose output with all fields (where applicable) |

The `table` format uses simple aligned columns, no external table library required.

---

## 6. Global Options

Available on all subcommands:

| Flag | Default | Description |
|------|---------|-------------|
| `--verbose` / `-v` | `False` | Enable verbose logging (sets `LOG_LEVEL=DEBUG`) |
| `--config-root` | `./config` | Path to configuration directory |
| `--data-folder` | `./data` | Path to data directory |
| `--env-file` | `.env` | Path to environment file |

---

## 7. Error Handling

### 7.1 Output Convention

- Normal output goes to **stdout**
- Error messages and logs go to **stderr**
- Progress indicators go to **stderr**

### 7.2 Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Invalid arguments / usage error |
| `3` | Connection error (MongoDB, Azure DI, etc.) |
| `4` | Document not found |

### 7.3 Connection Errors

When the CLI cannot connect to MongoDB or external services, it prints a user-friendly message to stderr with troubleshooting hints:

```
Error: Could not connect to MongoDB at localhost:27017
  - Check that MongoDB is running
  - Verify MONGO_URL in your .env file
  - Run 'mydocs config env' to check your configuration
```

---

## 8. Package Structure

```
mydocs2/                            # Project root
  pyproject.toml                    # scripts entry: mydocs = "mydocs.cli.main:cli_main"
  mydocs/
    cli/
      __init__.py
      main.py                       # Entry point, argparse, async bridge
      commands/
        __init__.py
        ingest.py
        parse.py
        search.py
        docs.py
        config.py
        migrate.py
      formatters.py                 # Output formatting utilities
```

---

## 9. Dependencies

No additional dependencies required. The CLI uses:
- `argparse` (stdlib)
- `asyncio` (stdlib)
- Existing `mydocs.parsing.pipeline` functions
- Existing `mydocs.retrieval` search functions
