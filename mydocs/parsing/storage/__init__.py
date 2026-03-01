"""Storage backend factory."""

import mydocs.config as C
from mydocs.models import StorageBackendEnum
from mydocs.parsing.storage.base import FileStorage

_azure_blob_singleton: FileStorage | None = None


def get_storage(backend: StorageBackendEnum = None, **kwargs) -> FileStorage:
    """Return a storage backend instance.

    Azure Blob backend is returned as a singleton to share the underlying
    aiohttp connection pool across concurrent requests.

    Uses lazy imports to avoid loading azure-storage-blob when using local backend.

    Args:
        backend: Storage backend to use. Defaults to MYDOCS_STORAGE_BACKEND config.
        **kwargs: Passed to the storage backend constructor.

    Returns:
        FileStorage implementation instance.
    """
    global _azure_blob_singleton
    backend = backend or StorageBackendEnum(C.STORAGE_BACKEND)

    if backend == StorageBackendEnum.LOCAL:
        from mydocs.parsing.storage.local import LocalFileStorage
        return LocalFileStorage(**kwargs)
    elif backend == StorageBackendEnum.AZURE_BLOB:
        if _azure_blob_singleton is None or kwargs:
            from mydocs.parsing.storage.azure_blob import AzureBlobStorage
            instance = AzureBlobStorage(**kwargs)
            if not kwargs:
                _azure_blob_singleton = instance
            return instance
        return _azure_blob_singleton
    else:
        raise ValueError(f"Unsupported storage backend: {backend}")
