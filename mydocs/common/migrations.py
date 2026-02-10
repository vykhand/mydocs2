"""Migration runner for database index management."""

import importlib.util
import os
import re
from datetime import datetime, timezone

from lightodm import get_database
from tinystructlog import get_logger

import mydocs.config as C

log = get_logger(__name__)

MIGRATIONS_FOLDER = os.path.join(C.ROOT_FOLDER, "migrations")
MIGRATIONS_COLLECTION = "_migrations"
SCRIPT_PATTERN = re.compile(r"^(\d{3})_.+\.py$")


def _get_migrations_collection():
    db = get_database()
    return db[MIGRATIONS_COLLECTION]


def discover_migrations() -> list[dict]:
    """Scan the migrations/ directory for scripts matching {NNN}_{description}.py."""
    if not os.path.isdir(MIGRATIONS_FOLDER):
        return []

    migrations = []
    for filename in sorted(os.listdir(MIGRATIONS_FOLDER)):
        if SCRIPT_PATTERN.match(filename):
            filepath = os.path.join(MIGRATIONS_FOLDER, filename)
            if os.path.isfile(filepath):
                migrations.append({"filename": filename, "filepath": filepath})

    return migrations


def get_executed_migrations() -> set[str]:
    """Return the set of already-executed migration filenames."""
    coll = _get_migrations_collection()
    return {doc["file_name"] for doc in coll.find({}, {"file_name": 1})}


def _execute_migration(filename: str, filepath: str):
    """Execute a single migration script.

    Imports the module and calls run() if it exists, otherwise
    relies on top-level code execution during import.
    """
    module_name = f"migration_{filename.removesuffix('.py')}"
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "run") and callable(module.run):
        module.run()


def run_migrations() -> list[dict]:
    """Run all pending migrations and track them in _migrations collection.

    Returns a list of dicts with 'filename' and 'status' for each migration.
    """
    migrations = discover_migrations()
    executed = get_executed_migrations()
    coll = _get_migrations_collection()

    results = []
    for migration in migrations:
        filename = migration["filename"]
        filepath = migration["filepath"]

        if filename in executed:
            log.info(f"Skipping migration {filename} (already executed)")
            results.append({"filename": filename, "status": "skipped"})
            continue

        log.info(f"Running migration {filename}...")
        try:
            _execute_migration(filename, filepath)
            coll.insert_one({
                "file_name": filename,
                "run_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            })
            log.info(f"Migration {filename} completed successfully.")
            results.append({"filename": filename, "status": "executed"})
        except Exception as e:
            log.error(f"Migration {filename} failed: {e}")
            results.append({"filename": filename, "status": f"failed: {e}"})

    return results


def list_migrations() -> list[dict]:
    """List all migrations with their execution status.

    Returns a list of dicts with 'filename', 'status', and 'run_at'.
    """
    migrations = discover_migrations()
    coll = _get_migrations_collection()

    executed_details = {}
    for doc in coll.find({}, {"file_name": 1, "run_at": 1}):
        executed_details[doc["file_name"]] = doc.get("run_at", "")

    results = []
    for migration in migrations:
        filename = migration["filename"]
        if filename in executed_details:
            results.append({
                "filename": filename,
                "status": "executed",
                "run_at": executed_details[filename],
            })
        else:
            results.append({
                "filename": filename,
                "status": "pending",
                "run_at": "",
            })

    return results
