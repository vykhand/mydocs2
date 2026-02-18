"""Output formatting utilities for the CLI."""

import json
import os
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


def format_docs_list(documents, mode: str) -> None:
    """Format and print a list of documents."""
    if mode == "json":
        print(json.dumps(
            [doc.model_dump(by_alias=False, exclude_none=True) for doc in documents],
            indent=2,
            default=str,
        ))
    elif mode == "quiet":
        print(len(documents))
    else:
        # table
        if not documents:
            print("No documents found.")
            return
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


def format_doc_show(document, mode: str) -> None:
    """Format and print a single document's details."""
    if mode == "json":
        print(document.model_dump_json(indent=2))
    elif mode == "full":
        _print_doc_table(document)
        if document.content:
            print(f"\n--- Content ---\n{document.content}")
    else:
        # table
        _print_doc_table(document)


def _print_doc_table(document) -> None:
    """Print document detail as a key-value table."""
    page_count = (
        document.file_metadata.page_count
        if document.file_metadata and document.file_metadata.page_count
        else 0
    )
    element_count = len(document.elements) if document.elements else 0

    headers = ["Field", "Value"]
    rows = [
        ["ID", document.id],
        ["File", document.original_file_name],
        ["Type", str(document.file_type)],
        ["Status", str(document.status)],
        ["Tags", ",".join(document.tags) if document.tags else ""],
        ["Pages", str(page_count)],
        ["Elements", str(element_count)],
        ["Created", str(document.created_at) if document.created_at else ""],
        ["Modified", str(document.modified_at) if document.modified_at else ""],
    ]
    print_table(headers, rows)


def format_doc_pages(pages, mode: str) -> None:
    """Format and print document pages."""
    if mode == "json":
        print(json.dumps(
            [p.model_dump(by_alias=False, exclude_none=True) for p in pages],
            indent=2,
            default=str,
        ))
    elif mode == "quiet":
        print(len(pages))
    else:
        # table
        if not pages:
            print("No pages found.")
            return
        headers = ["Page", "ID", "Content Length"]
        rows = [
            [
                str(p.page_number),
                p.id,
                str(len(p.content) if p.content else 0),
            ]
            for p in pages
        ]
        print_table(headers, rows)


def format_cases_list(cases, mode: str) -> None:
    """Format and print a list of cases."""
    if mode == "json":
        print(json.dumps(
            [c.model_dump(by_alias=False, exclude_none=True) for c in cases],
            indent=2,
            default=str,
        ))
    elif mode == "quiet":
        print(len(cases))
    else:
        if not cases:
            print("No cases found.")
            return
        headers = ["ID", "Name", "Documents", "Created"]
        rows = [
            [
                c.id,
                c.name,
                str(len(c.document_ids) if c.document_ids else 0),
                str(c.created_at) if c.created_at else "",
            ]
            for c in cases
        ]
        print_table(headers, rows)


def format_case_show(case, mode: str) -> None:
    """Format and print a single case's details."""
    if mode == "json":
        print(case.model_dump_json(indent=2))
    else:
        headers = ["Field", "Value"]
        rows = [
            ["ID", case.id],
            ["Name", case.name],
            ["Description", case.description or ""],
            ["Documents", str(len(case.document_ids) if case.document_ids else 0)],
            ["Document IDs", ",".join(case.document_ids) if case.document_ids else ""],
            ["Created", str(case.created_at) if case.created_at else ""],
            ["Modified", str(case.modified_at) if case.modified_at else ""],
        ]
        print_table(headers, rows)


def format_extraction_result(response, document_name: str, mode: str) -> None:
    """Format and print an extraction response."""
    if mode == "json":
        print(response.model_dump_json(indent=2))
    elif mode == "quiet":
        print(f"{document_name}\t{len(response.results)} fields")
    else:
        headers = ["Field", "Content", "Justification"]
        rows = []
        for field_name, result in response.results.items():
            content = result.get("content", "") if isinstance(result, dict) else (result.content or "")
            justification = result.get("justification", "") if isinstance(result, dict) else (result.justification or "")
            # Truncate long values for table display
            if len(content) > 80:
                content = content[:77] + "..."
            if len(justification) > 60:
                justification = justification[:57] + "..."
            rows.append([field_name, content, justification])
        print_table(headers, rows)
        print(f"\nModel: {response.model_used}")


def format_field_results(records, mode: str) -> None:
    """Format and print stored field result records."""
    if mode == "json":
        print(json.dumps(
            [r.model_dump(by_alias=False, exclude_none=True) for r in records],
            indent=2,
            default=str,
        ))
    elif mode == "quiet":
        print(len(records))
    else:
        headers = ["Field", "Content", "Justification"]
        rows = []
        for r in records:
            content = r.result.content or ""
            justification = r.result.justification or ""
            if len(content) > 80:
                content = content[:77] + "..."
            if len(justification) > 60:
                justification = justification[:57] + "..."
            rows.append([r.field_name, content, justification])
        print_table(headers, rows)


def format_sync_plan(plan, mode: str) -> None:
    """Format and print a sync plan."""
    if mode == "json":
        print(plan.model_dump_json(indent=2))
    elif mode == "quiet":
        for action, count in sorted(plan.summary.items()):
            print(f"{action}: {count}")
    else:
        if not plan.items:
            print("No items in sync plan.")
            return
        headers = ["Action", "Doc ID", "File", "Reason"]
        rows = [
            [
                item.action.value,
                item.doc_id[:12] + "...",
                os.path.basename(item.file_path) if item.file_path else "-",
                item.reason[:60],
            ]
            for item in plan.items
        ]
        print_table(headers, rows)
        print(f"\nSummary: {plan.summary}")
        print(f"Scan path: {plan.scan_path}")


def format_sync_report(report, mode: str) -> None:
    """Format and print a sync report."""
    if mode == "json":
        print(report.model_dump_json(indent=2))
    elif mode == "quiet":
        for action, counts in sorted(report.summary.items()):
            print(f"{action}: success={counts['success']} failed={counts['failed']}")
    else:
        if not report.items:
            print("No items executed.")
            return
        headers = ["Action", "Doc ID", "Status", "Error"]
        rows = [
            [
                r.item.action.value,
                r.item.doc_id[:12] + "...",
                "OK" if r.success else "FAILED",
                (r.error or "")[:50],
            ]
            for r in report.items
        ]
        print_table(headers, rows)
        print(f"\nSummary: {report.summary}")
        elapsed = (report.completed_at - report.started_at).total_seconds()
        print(f"Duration: {elapsed:.1f}s")


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
