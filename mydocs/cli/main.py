"""CLI entry point for mydocs."""

import asyncio
import sys

from tinystructlog import get_logger

import mydocs.config as C
from mydocs.cli.commands import cases, config, docs, extract, ingest, migrate, parse, search, sync

log = get_logger(__name__)


def parse_args(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog="mydocs",
        description="AI-powered document parsing and information extraction",
    )

    # Global options
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging (sets LOG_LEVEL=DEBUG)")
    parser.add_argument("--config-root", default=None, help="Path to configuration directory")
    parser.add_argument("--data-folder", default=None, help="Path to data directory")
    parser.add_argument("--env-file", default=None, help="Path to environment file")

    subparsers = parser.add_subparsers(dest="command")

    # Register subcommands
    ingest.register(subparsers)
    parse.register(subparsers)
    docs.register(subparsers)
    config.register(subparsers)
    migrate.register(subparsers)
    search.register(subparsers)
    cases.register(subparsers)
    extract.register(subparsers)
    sync.register(subparsers)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(2)

    return args


def apply_global_options(args):
    """Apply global CLI options to the config module."""
    if args.verbose:
        C.LOG_LEVEL = "DEBUG"

    if args.config_root:
        C.CONFIG_ROOT = args.config_root

    if args.data_folder:
        C.DATA_FOLDER = args.data_folder

    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file, override=True)


async def async_main(args):
    await args.func(args)


def cli_main():
    """Synchronous entry point for the CLI."""
    try:
        args = parse_args()
        apply_global_options(args)
        asyncio.run(async_main(args))
    except SystemExit as e:
        sys.exit(e.code)
    except KeyboardInterrupt:
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(4)
    except ConnectionError as e:
        print(f"Error: Could not connect to service: {e}", file=sys.stderr)
        print("  - Check that MongoDB is running", file=sys.stderr)
        print("  - Verify MONGO_URL in your .env file", file=sys.stderr)
        print("  - Run 'mydocs config env' to check your configuration", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        if "pymongo" in type(e).__module__ if hasattr(type(e), "__module__") else False:
            print(f"Error: Database connection issue: {e}", file=sys.stderr)
            print("  - Check that MongoDB is running", file=sys.stderr)
            print("  - Verify MONGO_URL in your .env file", file=sys.stderr)
            print("  - Run 'mydocs config env' to check your configuration", file=sys.stderr)
            sys.exit(3)
        print(f"Error: {e}", file=sys.stderr)
        if C.LOG_LEVEL == "DEBUG":
            import traceback
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
