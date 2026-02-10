"""mydocs parse command."""

import sys

from mydocs.cli.formatters import format_batch_result, format_parse_result
from mydocs.parsing.pipeline import batch_parse, parse_document


def register(subparsers):
    parser = subparsers.add_parser("parse", help="Parse documents")
    parser.add_argument("doc_id", nargs="?", default=None, help="Document ID to parse")
    parser.add_argument("--batch", action="store_true", help="Batch parse documents")
    parser.add_argument("--tags", default=None, help="Filter by tags (batch mode, comma-separated)")
    parser.add_argument("--status", default="new", help="Filter by status (batch mode, default: new)")
    parser.add_argument("--output", choices=["json", "table", "quiet"], default="table", help="Output format (default: table)")
    parser.set_defaults(func=handle)


async def handle(args):
    if args.doc_id:
        document = await parse_document(args.doc_id)
        format_parse_result(document, args.output)
    elif args.batch:
        tags = args.tags.split(",") if args.tags else None
        parsed, skipped = await batch_parse(
            tags=tags,
            status_filter=args.status,
        )
        format_batch_result(parsed, skipped, args.output)
    else:
        print("Error: provide a document ID or use --batch", file=sys.stderr)
        sys.exit(2)
