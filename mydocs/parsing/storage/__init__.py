"""Storage backend factory."""

import mydocs.config as C
from mydocs.models import StorageBackendEnum
from mydocs.parsing.storage.base import FileStorage


def get_storage(backend: StorageBackendEnum = None, **kwargs) -> FileStorage:
    """Create and return a storage backend instance.

    Uses lazy imports to avoid loading azure-storage-blob when using local backend.

    Args:
        backend: Storage backend to use. Defaults to MYDOCS_STORAGE_BACKEND config.
        **kwargs: Passed to the storage backend constructor.

    Returns:
        FileStorage implementation instance.
    """
    backend = backend or StorageBackendEnum(C.STORAGE_BACKEND)

    if backend == StorageBackendEnum.LOCAL:
        from mydocs.parsing.storage.local import LocalFileStorage
        return LocalFileStorage(**kwargs)
    elif backend == StorageBackendEnum.AZURE_BLOB:
        from mydocs.parsing.storage.azure_blob import AzureBlobStorage
        return AzureBlobStorage(**kwargs)
    else:
        raise ValueError(f"Unsupported storage backend: {backend}")
