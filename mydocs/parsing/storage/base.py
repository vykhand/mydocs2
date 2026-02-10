from abc import ABC, abstractmethod

from mydocs.parsing.models import FileMetadata


class FileStorage(ABC):
    """Abstract base class for file storage backends."""

    @abstractmethod
    async def copy_to_managed(self, source_path: str) -> str:
        """Copy a file to managed storage. Returns the managed path."""
        ...

    @abstractmethod
    async def get_file_bytes(self, path: str) -> bytes:
        """Read file contents as bytes."""
        ...

    @abstractmethod
    async def get_file_metadata(self, path: str) -> FileMetadata:
        """Compute and return file metadata."""
        ...
