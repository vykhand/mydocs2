import hashlib
import os
import shutil
import zlib
from datetime import datetime

import aiofiles

import mydocs.config as C
from mydocs.parsing.models import FileMetadata
from mydocs.parsing.storage.base import FileStorage


class LocalFileStorage(FileStorage):
    """Local filesystem storage backend."""

    def __init__(self, managed_root: str = None):
        self.managed_root = managed_root or os.path.join(C.DATA_FOLDER, "managed")
        os.makedirs(self.managed_root, exist_ok=True)

    async def copy_to_managed(self, source_path: str) -> str:
        """Copy a file to managed storage under data/managed/."""
        file_name = os.path.basename(source_path)
        managed_path = os.path.join(self.managed_root, file_name)

        # Avoid overwriting — add suffix if name collision
        if os.path.exists(managed_path) and os.path.abspath(source_path) != os.path.abspath(managed_path):
            base, ext = os.path.splitext(file_name)
            counter = 1
            while os.path.exists(managed_path):
                managed_path = os.path.join(self.managed_root, f"{base}_{counter}{ext}")
                counter += 1

        shutil.copy2(source_path, managed_path)
        return managed_path

    async def get_file_bytes(self, path: str) -> bytes:
        """Read file contents as bytes."""
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def get_file_metadata(self, path: str) -> FileMetadata:
        """Compute file metadata from local filesystem."""
        stat = os.stat(path)

        # Compute hashes
        sha256_hash = hashlib.sha256()
        crc32_value = 0
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
                crc32_value = zlib.crc32(chunk, crc32_value)

        return FileMetadata(
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_birthtime) if hasattr(stat, 'st_birthtime') else None,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            sha256=sha256_hash.hexdigest(),
            crc32=format(crc32_value & 0xFFFFFFFF, '08x'),
        )
