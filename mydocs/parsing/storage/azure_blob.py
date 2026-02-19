"""Azure Blob Storage backend for managed file storage."""

import hashlib
import json
import os
import zlib
from datetime import datetime, timedelta, timezone

import mydocs.config as C
from mydocs.models import FileMetadata
from mydocs.parsing.storage.base import FileStorage


# --- URI helpers ---

def parse_az_uri(uri: str) -> tuple[str, str]:
    """Parse az://<container>/<blob_path> into (container, blob_path)."""
    if not uri.startswith("az://"):
        raise ValueError(f"Invalid Azure Blob URI: {uri}")
    remainder = uri[len("az://"):]
    container, _, blob_path = remainder.partition("/")
    if not container or not blob_path:
        raise ValueError(f"Invalid Azure Blob URI (missing container or blob): {uri}")
    return container, blob_path


def make_az_uri(container: str, blob_name: str) -> str:
    """Create az://<container>/<blob_name> URI."""
    return f"az://{container}/{blob_name}"


class AzureBlobStorage(FileStorage):
    """Azure Blob Storage backend using async SDK."""

    def __init__(self, container_name: str = None, **kwargs):
        self.container_name = container_name or C.AZURE_STORAGE_CONTAINER_NAME
        self._client = self._create_client()
        self._container_client = self._client.get_container_client(self.container_name)

    def _create_client(self):
        from azure.storage.blob.aio import BlobServiceClient

        if C.AZURE_STORAGE_CONNECTION_STRING:
            return BlobServiceClient.from_connection_string(C.AZURE_STORAGE_CONNECTION_STRING)

        if C.AZURE_STORAGE_ACCOUNT_NAME:
            account_url = f"https://{C.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
            if C.AZURE_STORAGE_ACCOUNT_KEY:
                return BlobServiceClient(account_url, credential=C.AZURE_STORAGE_ACCOUNT_KEY)
            # No key — fall back to DefaultAzureCredential (managed identity, Azure CLI, etc.)
            from azure.identity.aio import DefaultAzureCredential
            return BlobServiceClient(account_url, credential=DefaultAzureCredential())

        raise ValueError(
            "Azure Blob Storage requires either AZURE_STORAGE_CONNECTION_STRING "
            "or AZURE_STORAGE_ACCOUNT_NAME to be set."
        )

    def _blob_name_for_doc(self, doc_id: str, source_path: str) -> str:
        """Generate blob name from doc_id and source extension."""
        _, ext = os.path.splitext(source_path)
        return f"{doc_id}{ext}"

    async def copy_to_managed(self, source_path: str, doc_id: str) -> tuple[str, str]:
        """Upload a local file to blob storage.

        Returns:
            Tuple of (az://container/blob_name, blob_name)
        """
        blob_name = self._blob_name_for_doc(doc_id, source_path)
        blob_client = self._container_client.get_blob_client(blob_name)

        with open(source_path, "rb") as f:
            await blob_client.upload_blob(f, overwrite=True)

        managed_path = make_az_uri(self.container_name, blob_name)
        return managed_path, blob_name

    async def write_metadata_sidecar(self, source_path: str, doc_id: str, metadata: dict) -> str:
        """Write sidecar alongside source file (local, for external mode)."""
        # External-mode sidecars are always written locally next to the source
        import aiofiles
        sidecar_path = os.path.join(os.path.dirname(source_path), f"{doc_id}.metadata.json")
        async with aiofiles.open(sidecar_path, "w") as f:
            await f.write(json.dumps(metadata, indent=2, default=str))
        return sidecar_path

    async def write_managed_sidecar(self, doc_id: str, metadata: dict) -> str:
        """Upload sidecar JSON as blob in managed storage."""
        blob_name = f"{doc_id}.metadata.json"
        blob_client = self._container_client.get_blob_client(blob_name)
        data = json.dumps(metadata, indent=2, default=str).encode()
        await blob_client.upload_blob(data, overwrite=True)
        return make_az_uri(self.container_name, blob_name)

    async def read_sidecar(self, sidecar_path: str) -> dict:
        """Read and parse a sidecar JSON, from blob or local path."""
        if sidecar_path.startswith("az://"):
            container, blob_path = parse_az_uri(sidecar_path)
            blob_client = self._client.get_container_client(container).get_blob_client(blob_path)
            stream = await blob_client.download_blob()
            data = await stream.readall()
            return json.loads(data)
        else:
            # Fall back to local read (external-mode sidecars)
            import aiofiles
            async with aiofiles.open(sidecar_path, "r") as f:
                content = await f.read()
            return json.loads(content)

    async def get_file_bytes(self, path: str) -> bytes:
        """Download blob contents as bytes."""
        if path.startswith("az://"):
            container, blob_path = parse_az_uri(path)
            blob_client = self._client.get_container_client(container).get_blob_client(blob_path)
        else:
            # Treat as blob name within default container
            blob_client = self._container_client.get_blob_client(path)

        stream = await blob_client.download_blob()
        return await stream.readall()

    async def get_file_metadata(self, path: str) -> FileMetadata:
        """Get metadata for a blob or local file.

        For local source files (during ingestion), computes hashes locally.
        For az:// paths, downloads and computes hashes.
        """
        if path.startswith("az://"):
            data = await self.get_file_bytes(path)
            container, blob_path = parse_az_uri(path)
            blob_client = self._client.get_container_client(container).get_blob_client(blob_path)
            props = await blob_client.get_blob_properties()

            sha256_hash = hashlib.sha256(data).hexdigest()
            crc32_value = zlib.crc32(data) & 0xFFFFFFFF

            return FileMetadata(
                size_bytes=props.size,
                created_at=props.creation_time,
                modified_at=props.last_modified,
                sha256=sha256_hash,
                crc32=format(crc32_value, '08x'),
            )
        else:
            # Local file — compute metadata the same way as LocalFileStorage
            stat = os.stat(path)
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

    async def write_managed_bytes(self, doc_id: str, file_name: str, data: bytes) -> str:
        """Write raw bytes to blob storage. Returns az:// URI."""
        blob_client = self._container_client.get_blob_client(file_name)
        await blob_client.upload_blob(data, overwrite=True)
        return make_az_uri(self.container_name, file_name)

    async def delete_file(self, path: str) -> None:
        """Delete a blob from storage."""
        if path.startswith("az://"):
            container, blob_path = parse_az_uri(path)
            blob_client = self._client.get_container_client(container).get_blob_client(blob_path)
        else:
            blob_client = self._container_client.get_blob_client(path)

        await blob_client.delete_blob()

    async def list_files(self, prefix: str | None = None) -> list[dict]:
        """List blobs in the container.

        Returns:
            List of dicts with keys: name, path, size_bytes.
        """
        results = []
        async for blob in self._container_client.list_blobs(name_starts_with=prefix):
            results.append({
                "name": blob.name,
                "path": make_az_uri(self.container_name, blob.name),
                "size_bytes": blob.size,
            })
        return results

    async def generate_download_url(self, path: str, expiry_hours: int = 1) -> str | None:
        """Generate a SAS URL for temporary blob access."""
        from azure.storage.blob import BlobSasPermissions, generate_blob_sas

        if path.startswith("az://"):
            container, blob_path = parse_az_uri(path)
        else:
            container = self.container_name
            blob_path = path

        # Get account details for SAS generation
        account_name = self._client.account_name

        # Determine account key for SAS generation
        account_key = None
        if C.AZURE_STORAGE_ACCOUNT_KEY:
            account_key = C.AZURE_STORAGE_ACCOUNT_KEY
        elif C.AZURE_STORAGE_CONNECTION_STRING:
            from azure.storage.blob import BlobServiceClient as SyncBlobServiceClient
            sync_client = SyncBlobServiceClient.from_connection_string(C.AZURE_STORAGE_CONNECTION_STRING)
            account_key = sync_client.credential.account_key
            sync_client.close()

        if account_key:
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container,
                blob_name=blob_path,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
            )
        else:
            # Use user delegation key with DefaultAzureCredential
            delegation_start = datetime.now(timezone.utc)
            delegation_expiry = delegation_start + timedelta(hours=expiry_hours)
            user_delegation_key = await self._client.get_user_delegation_key(
                delegation_start, delegation_expiry
            )
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container,
                blob_name=blob_path,
                user_delegation_key=user_delegation_key,
                permission=BlobSasPermissions(read=True),
                expiry=delegation_expiry,
            )

        return f"https://{account_name}.blob.core.windows.net/{container}/{blob_path}?{sas_token}"
