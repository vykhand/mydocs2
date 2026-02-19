"""mydocs sync command — storage-to-DB synchronization."""

import sys

from mydocs.cli.formatters import format_sync_plan, format_sync_report, format_migrate_plan, format_migrate_report
from mydocs.models import StorageBackendEnum
from mydocs.sync.models import SyncAction


def register(subparsers):
    parser = subparsers.add_parser("sync", help="Storage-to-DB synchronization")
    sub = parser.add_subparsers(dest="sync_action")

    # sync status
    status_parser = sub.add_parser("status", help="Scan and show sync plan (read-only)")
    status_parser.add_argument("--scan-path", default=None, help="Override managed storage path")
    status_parser.add_argument("--verify-content", action="store_true", help="Verify file content via SHA256")
    status_parser.add_argument("--backend", choices=["local", "azure_blob"], default=None, help="Storage backend (default: from config)")

    # sync run
    run_parser = sub.add_parser("run", help="Execute sync plan")
    run_parser.add_argument("--scan-path", default=None, help="Override managed storage path")
    run_parser.add_argument("--verify-content", action="store_true", help="Verify file content via SHA256")
    run_parser.add_argument("--reparse", action="store_true", help="Re-parse documents with cache")
    run_parser.add_argument("--backend", choices=["local", "azure_blob"], default=None, help="Storage backend (default: from config)")
    run_parser.add_argument(
        "--actions",
        default=None,
        help="Comma-separated actions to execute (default: all). Options: "
             + ", ".join(a.value for a in SyncAction),
    )
    run_parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")

    # sync write-sidecars
    ws_parser = sub.add_parser("write-sidecars", help="Write missing sidecars from DB records")
    ws_parser.add_argument("--scan-path", default=None, help="Override managed storage path")
    ws_parser.add_argument("--backend", choices=["local", "azure_blob"], default=None, help="Storage backend (default: from config)")

    # sync migrate
    migrate_parser = sub.add_parser("migrate", help="Migrate documents between storage backends")
    migrate_parser.add_argument("--from", dest="from_backend", required=True, choices=["local", "azure_blob"], help="Source storage backend")
    migrate_parser.add_argument("--to", dest="to_backend", required=True, choices=["local", "azure_blob"], help="Target storage backend")
    migrate_parser.add_argument("--delete-source", action="store_true", help="Delete source files after successful copy")
    migrate_parser.add_argument("--dry-run", action="store_true", help="Show migration plan without executing")

    parser.add_argument(
        "--output",
        choices=["json", "table", "quiet"],
        default="table",
        help="Output format (default: table)",
    )
    parser.set_defaults(func=handle)


async def handle(args):
    action = getattr(args, "sync_action", None)
    output = getattr(args, "output", "table")

    if action == "status":
        await _handle_status(args, output)
    elif action == "run":
        await _handle_run(args, output)
    elif action == "write-sidecars":
        await _handle_write_sidecars(args, output)
    elif action == "migrate":
        await _handle_migrate(args, output)
    else:
        print("Error: specify a subcommand: status, run, write-sidecars, or migrate", file=sys.stderr)
        sys.exit(2)


async def _handle_status(args, output):
    from mydocs.sync.scanner import build_sync_plan

    backend = StorageBackendEnum(args.backend) if getattr(args, "backend", None) else None
    plan = await build_sync_plan(
        scan_path=args.scan_path,
        verify_content=args.verify_content,
        storage_backend=backend,
    )
    format_sync_plan(plan, output)


async def _handle_run(args, output):
    from mydocs.sync.reconciler import execute_sync_plan
    from mydocs.sync.scanner import build_sync_plan

    backend = StorageBackendEnum(args.backend) if getattr(args, "backend", None) else None
    plan = await build_sync_plan(
        scan_path=args.scan_path,
        verify_content=args.verify_content,
        storage_backend=backend,
    )

    if args.dry_run:
        format_sync_plan(plan, output)
        return

    actions = args.actions.split(",") if args.actions else None
    report = await execute_sync_plan(
        plan=plan,
        reparse=args.reparse,
        actions=actions,
    )
    format_sync_report(report, output)


async def _handle_write_sidecars(args, output):
    from mydocs.sync.reconciler import execute_sync_plan
    from mydocs.sync.scanner import build_sync_plan

    backend = StorageBackendEnum(args.backend) if getattr(args, "backend", None) else None
    plan = await build_sync_plan(
        scan_path=args.scan_path,
        storage_backend=backend,
    )

    report = await execute_sync_plan(
        plan=plan,
        actions=["sidecar_missing"],
    )
    format_sync_report(report, output)


async def _handle_migrate(args, output):
    from mydocs.parsing.storage import get_storage
    from mydocs.sync.migrator import build_migrate_plan, execute_migrate_plan

    source = StorageBackendEnum(args.from_backend)
    target = StorageBackendEnum(args.to_backend)

    if source == target:
        print("Error: --from and --to must be different backends", file=sys.stderr)
        sys.exit(2)

    plan = await build_migrate_plan(source, target)

    if args.dry_run:
        format_migrate_plan(plan, output)
        return

    source_storage = get_storage(source)
    dest_storage = get_storage(target)

    report = await execute_migrate_plan(
        plan=plan,
        source_storage=source_storage,
        dest_storage=dest_storage,
        delete_source=args.delete_source,
    )
    format_migrate_report(report, output)
