"""mydocs migrate command."""

import sys

from mydocs.cli.formatters import print_table
from mydocs.common.migrations import list_migrations, run_migrations


def register(subparsers):
    parser = subparsers.add_parser("migrate", help="Database migration management")
    migrate_sub = parser.add_subparsers(dest="migrate_action")
    migrate_sub.add_parser("run", help="Run all pending migrations")
    migrate_sub.add_parser("list", help="List available migration scripts")
    parser.set_defaults(func=handle)


async def handle(args):
    if args.migrate_action == "run":
        _handle_run()
    elif args.migrate_action == "list":
        _handle_list()
    else:
        print("Error: specify 'run' or 'list'", file=sys.stderr)
        sys.exit(2)


def _handle_run():
    results = run_migrations()
    executed = [r for r in results if r["status"] == "executed"]
    skipped = [r for r in results if r["status"] == "skipped"]
    failed = [r for r in results if r["status"].startswith("failed")]

    if executed:
        headers = ["Migration", "Status"]
        rows = [[r["filename"], r["status"]] for r in executed]
        print_table(headers, rows)

    if not executed and not failed:
        print("No pending migrations.")

    if failed:
        print(f"\nFailed: {len(failed)}", file=sys.stderr)
        for r in failed:
            print(f"  {r['filename']}: {r['status']}", file=sys.stderr)
        sys.exit(1)

    print(f"\nExecuted: {len(executed)}, Skipped: {len(skipped)}")


def _handle_list():
    results = list_migrations()
    if not results:
        print("No migration scripts found.")
        return

    headers = ["Migration", "Status", "Run At"]
    rows = [[r["filename"], r["status"], r["run_at"]] for r in results]
    print_table(headers, rows)