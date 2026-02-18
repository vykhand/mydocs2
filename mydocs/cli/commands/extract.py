"""mydocs extract command — run extraction, view results, split-classify."""

import sys

from mydocs.cli.formatters import (
    format_extraction_result,
    format_field_results,
    format_split_classify_result,
)
from mydocs.extracting.extractor import BaseExtractor
from mydocs.extracting.models import ExtractionRequest, FieldResultRecord
from mydocs.extracting.prompt_utils import get_split_classify_prompt
from mydocs.extracting.splitter import split_and_classify
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

    # extract split-classify <document_id>
    sc_parser = sub.add_parser("split-classify", help="Split and classify a multi-document file")
    sc_parser.add_argument("document_id", help="Document ID")
    sc_parser.add_argument("--case-type", default="generic", help="Case type (default: generic)")
    sc_parser.add_argument("--content-mode", choices=["markdown", "html"], default="markdown", help="Content mode (default: markdown)")
    sc_parser.add_argument("--force", action="store_true", default=False, help="Force re-classification even if hashes match")

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
    elif action == "split-classify":
        await _handle_split_classify(args, output)
    else:
        print("Error: specify a subcommand: run, results, or split-classify", file=sys.stderr)
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


async def _handle_split_classify(args, output):
    document_id = args.document_id
    case_type = getattr(args, "case_type", "generic")
    content_mode = getattr(args, "content_mode", "markdown")

    doc = await Document.aget(document_id)
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    doc_name = doc.original_file_name or document_id
    print(f"Split-classifying: {doc_name}", file=sys.stderr)

    prompt_config = get_split_classify_prompt(case_type)

    force = getattr(args, "force", False)

    result = await split_and_classify(
        document_id=document_id,
        prompt_config=prompt_config,
        content_mode=content_mode,
        case_type=case_type,
        force=force,
    )
    format_split_classify_result(result, output)
