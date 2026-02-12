"""mydocs docs command — document management."""

import sys

from mydocs.cli.formatters import format_doc_pages, format_doc_show, format_docs_list
from mydocs.models import Document, DocumentPage, DocumentStatusEnum


def register(subparsers):
    parser = subparsers.add_parser("docs", help="Document management")
    sub = parser.add_subparsers(dest="docs_action")

    # docs list
    list_parser = sub.add_parser("list", help="List documents")
    list_parser.add_argument(
        "--status",
        choices=[s.value for s in DocumentStatusEnum],
        default=None,
        help="Filter by document status",
    )
    list_parser.add_argument("--tags", default=None, help="Comma-separated tags to filter by")

    # docs show <doc_id>
    show_parser = sub.add_parser("show", help="Show document details")
    show_parser.add_argument("doc_id", help="Document ID")

    # docs pages <doc_id>
    pages_parser = sub.add_parser("pages", help="List pages of a document")
    pages_parser.add_argument("doc_id", help="Document ID")
    pages_parser.add_argument("--page", type=int, default=None, help="Show a single page by number")

    # docs tag <doc_id> <tags>
    tag_parser = sub.add_parser("tag", help="Add or remove tags")
    tag_parser.add_argument("doc_id", help="Document ID")
    tag_parser.add_argument("tags", help="Comma-separated tags")
    tag_parser.add_argument("--remove", action="store_true", help="Remove tags instead of adding")

    # docs delete <doc_id>
    del_parser = sub.add_parser("delete", help="Delete document and pages")
    del_parser.add_argument("doc_id", help="Document ID")
    del_parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    parser.add_argument(
        "--output",
        choices=["json", "table", "quiet", "full"],
        default="table",
        help="Output format (default: table)",
    )
    parser.set_defaults(func=handle)


async def handle(args):
    action = getattr(args, "docs_action", None)
    output = getattr(args, "output", "table")

    if action == "list":
        await _handle_list(args, output)
    elif action == "show":
        await _handle_show(args, output)
    elif action == "pages":
        await _handle_pages(args, output)
    elif action == "tag":
        await _handle_tag(args, output)
    elif action == "delete":
        await _handle_delete(args)
    else:
        print("Error: specify a subcommand: list, show, pages, tag, or delete", file=sys.stderr)
        sys.exit(2)


async def _handle_list(args, output):
    filter_dict = {}
    if args.tags:
        filter_dict["tags"] = {"$all": args.tags.split(",")}
    if args.status:
        filter_dict["status"] = args.status
    docs = await Document.afind(filter_dict)
    format_docs_list(docs, output)


async def _handle_show(args, output):
    doc = await Document.aget(args.doc_id)
    if not doc:
        raise ValueError(f"Document {args.doc_id} not found")
    format_doc_show(doc, output)


async def _handle_pages(args, output):
    doc = await Document.aget(args.doc_id)
    if not doc:
        raise ValueError(f"Document {args.doc_id} not found")

    if args.page is not None:
        page = await DocumentPage.afind_one(
            {"document_id": args.doc_id, "page_number": args.page}
        )
        if not page:
            raise ValueError(f"Page {args.page} not found for document {args.doc_id}")
        pages = [page]
    else:
        pages = await DocumentPage.afind({"document_id": args.doc_id})

    format_doc_pages(pages, output)


async def _handle_tag(args, output):
    doc = await Document.aget(args.doc_id)
    if not doc:
        raise ValueError(f"Document {args.doc_id} not found")

    tag_list = [t.strip() for t in args.tags.split(",") if t.strip()]

    if args.remove:
        for tag in tag_list:
            await Document.aupdate_one(
                {"_id": args.doc_id},
                {"$pull": {"tags": tag}},
            )
    else:
        await Document.aupdate_one(
            {"_id": args.doc_id},
            {"$addToSet": {"tags": {"$each": tag_list}}},
        )

    updated = await Document.aget(args.doc_id)
    format_doc_show(updated, output)


async def _handle_delete(args):
    doc = await Document.aget(args.doc_id)
    if not doc:
        raise ValueError(f"Document {args.doc_id} not found")

    if not args.force:
        answer = input(f"Delete document {args.doc_id} ({doc.original_file_name})? [y/N] ")
        if answer.lower() != "y":
            print("Aborted.")
            return

    await DocumentPage.adelete_many({"document_id": args.doc_id})
    await doc.adelete()
    print(f"Deleted document {args.doc_id} ({doc.original_file_name})")
