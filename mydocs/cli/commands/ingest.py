"""mydocs ingest command."""

from mydocs.cli.formatters import format_ingest_result
from mydocs.models import StorageModeEnum
from mydocs.parsing.pipeline import ingest_files


def register(subparsers):
    parser = subparsers.add_parser("ingest", help="Ingest files into the system")
    parser.add_argument("source", help="Path to file or directory")
    parser.add_argument("--mode", choices=["managed", "external"], default="managed", help="Storage mode (default: managed)")
    parser.add_argument("--tags", default=None, help="Comma-separated tags to assign")
    parser.add_argument("--no-recursive", action="store_true", help="Don't recurse into subdirectories")
    parser.add_argument("--output", choices=["json", "table", "quiet"], default="table", help="Output format (default: table)")
    parser.set_defaults(func=handle)


async def handle(args):
    tags = args.tags.split(",") if args.tags else None
    storage_mode = StorageModeEnum(args.mode)
    recursive = not args.no_recursive

    documents, skipped = await ingest_files(
        source=args.source,
        storage_mode=storage_mode,
        tags=tags,
        recursive=recursive,
    )

    format_ingest_result(documents, skipped, args.output)
