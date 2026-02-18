"""mydocs extract command — run extraction and view results."""

import sys

from mydocs.cli.formatters import format_extraction_result, format_field_results
from mydocs.extracting.extractor import BaseExtractor
from mydocs.extracting.models import ExtractionRequest, FieldResultRecord
from mydocs.models import Case, Document


def register(subparsers):
    parser = subparsers.add_parser("extract", help="Field extraction")
    sub = parser.add_subparsers(dest="extract_action")

    # extract run <case_id>
    run_parser = sub.add_parser("run", help="Extract fields for a case")
    run_parser.add_argument("case_id", help="Case ID")
    run_parser.add_argument("--document-type", default="generic", help="Document type (default: generic)")
    run_parser.add_argument("--fields", default=None, help="Comma-separated field names to extract (default: all)")
    run_parser.add_argument("--content-mode", choices=["markdown", "html"], default="markdown", help="Content mode (default: markdown)")
    run_parser.add_argument("--reference-granularity", choices=["full", "page", "none"], default="none", help="Reference granularity (default: none)")
    run_parser.add_argument("--subdocument-id", default=None, help="SubDocument ID to scope extraction to")

    # extract results <case_id>
    results_parser = sub.add_parser("results", help="Show extraction results for a case")
    results_parser.add_argument("case_id", help="Case ID")

    parser.add_argument(
        "--output",
        choices=["json", "table", "quiet"],
        default="table",
        help="Output format (default: table)",
    )
    parser.set_defaults(func=handle)


async def handle(args):
    action = getattr(args, "extract_action", None)
    output = getattr(args, "output", "table")

    if action == "run":
        await _handle_run(args, output)
    elif action == "results":
        await _handle_results(args, output)
    else:
        print("Error: specify a subcommand: run or results", file=sys.stderr)
        sys.exit(2)


async def _handle_run(args, output):
    case = await Case.aget(args.case_id)
    if not case:
        raise ValueError(f"Case {args.case_id} not found")

    if not case.document_ids:
        print("No documents in this case.", file=sys.stderr)
        return

    fields = None
    if args.fields:
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    print(f"Extracting fields for case: {case.name} ({len(case.document_ids)} documents)", file=sys.stderr)

    for i, doc_id in enumerate(case.document_ids):
        doc = await Document.aget(doc_id)
        doc_name = doc.original_file_name if doc else doc_id
        print(f"\n[{i + 1}/{len(case.document_ids)}] {doc_name}", file=sys.stderr)

        request = ExtractionRequest(
            case_id=args.case_id,
            case_type=case.type,
            document_type=args.document_type,
            document_ids=[doc_id],
            fields=fields,
            content_mode=args.content_mode,
            reference_granularity=args.reference_granularity,
            subdocument_id=getattr(args, "subdocument_id", None),
        )

        try:
            extractor = BaseExtractor(request)
            response = await extractor.run()
            format_extraction_result(response, doc_name, output)
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)


async def _handle_results(args, output):
    case = await Case.aget(args.case_id)
    if not case:
        raise ValueError(f"Case {args.case_id} not found")

    if not case.document_ids:
        print("No documents in this case.", file=sys.stderr)
        return

    for doc_id in case.document_ids:
        doc = await Document.aget(doc_id)
        doc_name = doc.original_file_name if doc else doc_id

        records = await FieldResultRecord.afind({"document_id": doc_id})
        if records:
            print(f"\n--- {doc_name} ---")
            format_field_results(records, output)
        else:
            print(f"\n--- {doc_name} --- (no results)")
