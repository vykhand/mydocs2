"""mydocs cases command — case management."""

import sys

from mydocs.cli.formatters import format_case_show, format_cases_list, format_docs_list
from mydocs.models import Case, Document


def register(subparsers):
    parser = subparsers.add_parser("cases", help="Case management")
    sub = parser.add_subparsers(dest="cases_action")

    # cases list
    list_parser = sub.add_parser("list", help="List cases")
    list_parser.add_argument("--search", default=None, help="Search cases by name")

    # cases show <case_id>
    show_parser = sub.add_parser("show", help="Show case details")
    show_parser.add_argument("case_id", help="Case ID")

    # cases create <name>
    create_parser = sub.add_parser("create", help="Create a new case")
    create_parser.add_argument("name", help="Case name")
    create_parser.add_argument("--description", default=None, help="Case description")

    # cases update <case_id>
    update_parser = sub.add_parser("update", help="Update a case")
    update_parser.add_argument("case_id", help="Case ID")
    update_parser.add_argument("--name", default=None, help="New case name")
    update_parser.add_argument("--description", default=None, help="New case description")

    # cases delete <case_id>
    del_parser = sub.add_parser("delete", help="Delete a case")
    del_parser.add_argument("case_id", help="Case ID")
    del_parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    # cases add-docs <case_id> <doc_ids>
    add_docs_parser = sub.add_parser("add-docs", help="Add documents to a case")
    add_docs_parser.add_argument("case_id", help="Case ID")
    add_docs_parser.add_argument("doc_ids", help="Comma-separated document IDs")

    # cases remove-doc <case_id> <doc_id>
    remove_doc_parser = sub.add_parser("remove-doc", help="Remove a document from a case")
    remove_doc_parser.add_argument("case_id", help="Case ID")
    remove_doc_parser.add_argument("doc_id", help="Document ID to remove")

    # cases docs <case_id>
    docs_parser = sub.add_parser("docs", help="List documents in a case")
    docs_parser.add_argument("case_id", help="Case ID")

    parser.add_argument(
        "--output",
        choices=["json", "table", "quiet"],
        default="table",
        help="Output format (default: table)",
    )
    parser.set_defaults(func=handle)


async def handle(args):
    action = getattr(args, "cases_action", None)
    output = getattr(args, "output", "table")

    if action == "list":
        await _handle_list(args, output)
    elif action == "show":
        await _handle_show(args, output)
    elif action == "create":
        await _handle_create(args, output)
    elif action == "update":
        await _handle_update(args, output)
    elif action == "delete":
        await _handle_delete(args)
    elif action == "add-docs":
        await _handle_add_docs(args, output)
    elif action == "remove-doc":
        await _handle_remove_doc(args, output)
    elif action == "docs":
        await _handle_docs(args, output)
    else:
        print("Error: specify a subcommand: list, show, create, update, delete, add-docs, remove-doc, or docs", file=sys.stderr)
        sys.exit(2)


async def _handle_list(args, output):
    import re as re_mod

    filter_dict = {}
    if args.search:
        filter_dict["name"] = {"$regex": re_mod.escape(args.search), "$options": "i"}
    cases = await Case.afind(filter_dict, sort=[("created_at", -1)])
    format_cases_list(cases, output)


async def _handle_show(args, output):
    case = await Case.aget(args.case_id)
    if not case:
        raise ValueError(f"Case {args.case_id} not found")
    format_case_show(case, output)


async def _handle_create(args, output):
    from datetime import datetime

    now = datetime.utcnow()
    case = Case(
        name=args.name,
        description=args.description,
        created_at=now,
        modified_at=now,
    )
    await case.asave()
    format_case_show(case, output)


async def _handle_update(args, output):
    from datetime import datetime

    case = await Case.aget(args.case_id)
    if not case:
        raise ValueError(f"Case {args.case_id} not found")

    update_fields = {}
    if args.name is not None:
        update_fields["name"] = args.name
    if args.description is not None:
        update_fields["description"] = args.description

    if not update_fields:
        raise ValueError("Nothing to update. Specify --name or --description")

    update_fields["modified_at"] = datetime.utcnow()
    await Case.aupdate_one({"_id": args.case_id}, {"$set": update_fields})
    updated = await Case.aget(args.case_id)
    format_case_show(updated, output)


async def _handle_delete(args):
    case = await Case.aget(args.case_id)
    if not case:
        raise ValueError(f"Case {args.case_id} not found")

    if not args.force:
        answer = input(f"Delete case {args.case_id} ({case.name})? [y/N] ")
        if answer.lower() != "y":
            print("Aborted.")
            return

    await Case.adelete_one({"_id": args.case_id})
    print(f"Deleted case {args.case_id} ({case.name})")


async def _handle_add_docs(args, output):
    from datetime import datetime

    case = await Case.aget(args.case_id)
    if not case:
        raise ValueError(f"Case {args.case_id} not found")

    doc_ids = [d.strip() for d in args.doc_ids.split(",") if d.strip()]
    await Case.aupdate_one(
        {"_id": args.case_id},
        {
            "$addToSet": {"document_ids": {"$each": doc_ids}},
            "$set": {"modified_at": datetime.utcnow()},
        },
    )
    updated = await Case.aget(args.case_id)
    format_case_show(updated, output)


async def _handle_remove_doc(args, output):
    from datetime import datetime

    case = await Case.aget(args.case_id)
    if not case:
        raise ValueError(f"Case {args.case_id} not found")

    await Case.aupdate_one(
        {"_id": args.case_id},
        {
            "$pull": {"document_ids": args.doc_id},
            "$set": {"modified_at": datetime.utcnow()},
        },
    )
    updated = await Case.aget(args.case_id)
    format_case_show(updated, output)


async def _handle_docs(args, output):
    case = await Case.aget(args.case_id)
    if not case:
        raise ValueError(f"Case {args.case_id} not found")

    if not case.document_ids:
        format_docs_list([], output)
        return

    docs = await Document.afind({"_id": {"$in": case.document_ids}})
    format_docs_list(docs, output)
