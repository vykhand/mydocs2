"""Cache store abstraction for parsing artifacts (DI results, embeddings)."""

import json
import os
from abc import ABC, abstractmethod

from tinystructlog import get_logger

log = get_logger(__name__)


class CacheStore(ABC):
    """Abstract cache store for reading/writing JSON cache files."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check whether a cache entry exists."""
        ...

    @abstractmethod
    async def read_json(self, key: str) -> dict | list:
        """Read and parse a JSON cache entry."""
        ...

    @abstractmethod
    async def write_json(self, key: str, data) -> None:
        """Write data as a JSON cache entry."""
        ...

    async def close(self) -> None:
        """Release any resources held by the cache store."""
        pass


class LocalCacheStore(CacheStore):
    """Cache store backed by the local filesystem."""

    async def exists(self, key: str) -> bool:
        return os.path.exists(key)

    async def read_json(self, key: str) -> dict | list:
        with open(key, "r") as f:
            return json.load(f)

    async def write_json(self, key: str, data) -> None:
        os.makedirs(os.path.dirname(key) or ".", exist_ok=True)
        with open(key, "w") as f:
            json.dump(data, f)


class BlobCacheStore(CacheStore):
    """Cache store backed by an Azure Blob Storage container."""

    def __init__(self, container_name: str):
        from mydocs.parsing.storage.azure_helpers import create_blob_service_client

        self._client = create_blob_service_client()
        self._container_client = self._client.get_container_client(container_name)
        self._container_name = container_name

    async def exists(self, key: str) -> bool:
        blob_client = self._container_client.get_blob_client(key)
        return await blob_client.exists()

    async def read_json(self, key: str) -> dict | list:
        blob_client = self._container_client.get_blob_client(key)
        stream = await blob_client.download_blob()
        data = await stream.readall()
        return json.loads(data)

    async def write_json(self, key: str, data) -> None:
        try:
            blob_client = self._container_client.get_blob_client(key)
            payload = json.dumps(data).encode()
            await blob_client.upload_blob(payload, overwrite=True)
        except Exception as e:
            log.warning(f"Failed to write cache blob '{key}' in container '{self._container_name}': {e}")

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
