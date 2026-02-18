import hashlib
import json
import os
import shutil
import zlib
from datetime import datetime

import aiofiles

import mydocs.config as C
from mydocs.models import FileMetadata
from mydocs.parsing.storage.base import FileStorage


class LocalFileStorage(FileStorage):
    """Local filesystem storage backend."""

    def __init__(self, managed_root: str = None):
        self.managed_root = managed_root or os.path.join(C.DATA_FOLDER, "managed")
        os.makedirs(self.managed_root, exist_ok=True)

    async def copy_to_managed(self, source_path: str, doc_id: str) -> tuple[str, str]:
        """Copy a file to managed storage as <doc_id>.<original_extension>.

        Returns:
            Tuple of (managed_path, managed_file_name)
        """
        _, ext = os.path.splitext(source_path)
        managed_file_name = f"{doc_id}{ext}"
        managed_path = os.path.join(self.managed_root, managed_file_name)

        shutil.copy2(source_path, managed_path)
        return managed_path, managed_file_name

    async def write_metadata_sidecar(self, source_path: str, doc_id: str, metadata: dict) -> str:
        """Write <doc_id>.metadata.json alongside the source file."""
        sidecar_path = os.path.join(os.path.dirname(source_path), f"{doc_id}.metadata.json")
        async with aiofiles.open(sidecar_path, "w") as f:
            await f.write(json.dumps(metadata, indent=2, default=str))
        return sidecar_path

    async def write_managed_sidecar(self, doc_id: str, metadata: dict) -> str:
        """Write <doc_id>.metadata.json in managed storage root."""
        sidecar_path = os.path.join(self.managed_root, f"{doc_id}.metadata.json")
        async with aiofiles.open(sidecar_path, "w") as f:
            await f.write(json.dumps(metadata, indent=2, default=str))
        return sidecar_path

    async def read_sidecar(self, sidecar_path: str) -> dict:
        """Read and parse a metadata sidecar JSON file."""
        async with aiofiles.open(sidecar_path, "r") as f:
            content = await f.read()
        return json.loads(content)

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
