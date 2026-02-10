"""mydocs search command."""

from mydocs.cli.formatters import format_search_result
from mydocs.retrieval import search
from mydocs.retrieval.models import SearchFilters, SearchRequest


def register(subparsers):
    parser = subparsers.add_parser("search", help="Search documents and pages")
    parser.add_argument("query", help="Search query string")
    parser.add_argument("--mode", choices=["fulltext", "vector", "hybrid"], default="hybrid", help="Search mode (default: hybrid)")
    parser.add_argument("--target", choices=["pages", "documents"], default="pages", help="Search target (default: pages)")
    parser.add_argument("--top-k", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--tags", default=None, help="Filter by tags (comma-separated)")
    parser.add_argument("--output", choices=["json", "table", "quiet", "full"], default="table", help="Output format (default: table)")
    parser.set_defaults(func=handle)


async def handle(args):
    filters = SearchFilters(tags=args.tags.split(",") if args.tags else None)
    request = SearchRequest(
        query=args.query,
        search_mode=args.mode,
        search_target=args.target,
        top_k=args.top_k,
        filters=filters,
    )
    if args.output == "full":
        request.include_content_fields = ["content", "content_markdown"]

    response = await search(request)
    format_search_result(response, args.output)
