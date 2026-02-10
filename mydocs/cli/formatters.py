"""Output formatting utilities for the CLI."""

import json
import sys


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print a simple column-aligned table to stdout."""
    if not rows:
        return

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("  ".join("-" * w for w in col_widths))

    # Print rows
    for row in rows:
        line = "  ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        print(line)


def format_ingest_result(documents, skipped, mode: str) -> None:
    """Format and print ingest results."""
    if mode == "json":
        result = {
            "documents": [
                {
                    "id": doc.id,
                    "file_name": doc.original_file_name,
                    "file_type": str(doc.file_type),
                    "status": str(doc.status),
                    "tags": doc.tags,
                }
                for doc in documents
            ],
            "skipped": skipped,
        }
        print(json.dumps(result, indent=2))
    elif mode == "quiet":
        print(f"Ingested: {len(documents)}, Skipped: {len(skipped)}")
    else:
        # table
        if documents:
            headers = ["ID", "File", "Type", "Status", "Tags"]
            rows = [
                [
                    doc.id,
                    doc.original_file_name,
                    str(doc.file_type),
                    str(doc.status),
                    ",".join(doc.tags) if doc.tags else "",
                ]
                for doc in documents
            ]
            print_table(headers, rows)
        if skipped:
            print(f"\nSkipped: {len(skipped)}", file=sys.stderr)
            for s in skipped:
                print(f"  {s['path']}: {s['reason']}", file=sys.stderr)
        if not documents and not skipped:
            print("No files found.")


def format_parse_result(document, mode: str) -> None:
    """Format and print a single parse result."""
    elements_count = len(document.elements) if document.elements else 0
    page_count = document.file_metadata.page_count if document.file_metadata and document.file_metadata.page_count else 0

    if mode == "json":
        result = {
            "id": document.id,
            "file_name": document.original_file_name,
            "status": str(document.status),
            "elements": elements_count,
            "pages": page_count,
        }
        print(json.dumps(result, indent=2))
    elif mode == "quiet":
        print(f"{document.id}\t{document.status}")
    else:
        # table
        headers = ["ID", "File", "Status", "Elements", "Pages"]
        rows = [[document.id, document.original_file_name, str(document.status), str(elements_count), str(page_count)]]
        print_table(headers, rows)


def format_batch_result(parsed: int, skipped: int, mode: str) -> None:
    """Format and print batch parse results."""
    if mode == "json":
        print(json.dumps({"parsed": parsed, "skipped": skipped}, indent=2))
    else:
        # table and quiet are the same for batch
        print(f"Parsed: {parsed}, Skipped: {skipped}")


def format_search_result(response, mode: str) -> None:
    """Format and print search results."""
    if mode == "json":
        print(response.model_dump_json(indent=2))
    elif mode == "quiet":
        print(response.total)
    else:
        # table and full
        if response.results:
            headers = ["#", "Score", "ID", "File", "Page", "Tags"]
            rows = [
                [
                    str(i + 1),
                    f"{r.score:.4f}",
                    r.id,
                    r.file_name or "-",
                    str(r.page_number) if r.page_number is not None else "-",
                    ",".join(r.tags) if r.tags else "",
                ]
                for i, r in enumerate(response.results)
            ]
            print_table(headers, rows)
        print(f"\n{response.total} results ({response.search_mode} on {response.search_target})")

        if mode == "full" and response.results:
            print()
            for i, r in enumerate(response.results):
                text = r.content_markdown or r.content or ""
                print(f"--- [{i + 1}] {r.id} ---")
                print(text)
                print()


def format_config(serialized_config, mode: str) -> None:
    """Format and print configuration."""
    if mode == "json":
        if serialized_config.config_json:
            print(serialized_config.config_json)
        else:
            print(json.dumps(serialized_config.config_dict, indent=2))
    else:
        if serialized_config.config_yaml:
            print(serialized_config.config_yaml, end="")
        else:
            print(json.dumps(serialized_config.config_dict, indent=2))
