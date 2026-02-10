"""mydocs config command."""

import sys

import mydocs.config as C
from mydocs.cli.formatters import format_config
from mydocs.parsing.config import ParserConfig


# Environment variables to display, with secrets flagged for redaction
_ENV_VARS = [
    ("SERVICE_NAME", False),
    ("ROOT_FOLDER", False),
    ("DATA_FOLDER", False),
    ("CONFIG_ROOT", False),
    ("LOG_LEVEL", False),
    ("MONGO_URL", False),
    ("MONGO_USER", False),
    ("MONGO_PASSWORD", True),
    ("MONGO_DB_NAME", False),
    ("AZURE_DI_ENDPOINT", False),
    ("AZURE_DI_API_KEY", True),
    ("AZURE_DI_API_VERSION", False),
    ("AZURE_OPENAI_API_KEY", True),
    ("AZURE_OPENAI_API_BASE", False),
    ("AZURE_OPENAI_API_VERSION", False),
]


def _redact(value: str | None) -> str:
    if value is None:
        return "<not set>"
    if len(value) <= 4:
        return "****"
    return value[:4] + "****"


def register(subparsers):
    parser = subparsers.add_parser("config", help="Configuration utilities")
    sub = parser.add_subparsers(dest="config_action")

    sub.add_parser("show", help="Show current parser configuration")
    sub.add_parser("validate", help="Validate configuration files")
    sub.add_parser("env", help="Show environment variable values (redacted secrets)")

    parser.add_argument("--output", choices=["json", "table", "quiet"], default="table", help="Output format (default: table)")
    parser.set_defaults(func=handle)


async def handle(args):
    action = getattr(args, "config_action", None)

    if action == "show":
        config = ParserConfig()
        fmt = "json" if getattr(args, "output", "table") == "json" else "yaml"
        serialized = config.dump_config(format=fmt)
        format_config(serialized, getattr(args, "output", "table"))

    elif action == "validate":
        try:
            ParserConfig()
            print("Configuration is valid.")
        except Exception as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            sys.exit(1)

    elif action == "env":
        for var_name, is_secret in _ENV_VARS:
            value = getattr(C, var_name, None)
            display = _redact(value) if is_secret else (value if value is not None else "<not set>")
            print(f"{var_name}={display}")

    else:
        print("Error: specify a subcommand: show, validate, or env", file=sys.stderr)
        sys.exit(2)
