from abc import ABC, abstractmethod

from mydocs.models import FileMetadata


class FileStorage(ABC):
    """Abstract base class for file storage backends."""

    @abstractmethod
    async def copy_to_managed(self, source_path: str, doc_id: str) -> tuple[str, str]:
        """Copy a file to managed storage as <doc_id>.<original_extension>.

        Args:
            source_path: Path to the source file.
            doc_id: Document ID to use as the managed file name stem.

        Returns:
            Tuple of (managed_path, managed_file_name)
        """
        ...

    @abstractmethod
    async def write_metadata_sidecar(self, source_path: str, doc_id: str, metadata: dict) -> str:
        """Write a <doc_id>.metadata.json sidecar file alongside the source file.

        Returns:
            Path to the sidecar file.
        """
        ...

    @abstractmethod
    async def get_file_bytes(self, path: str) -> bytes:
        """Read file contents as bytes."""
        ...

    @abstractmethod
    async def get_file_metadata(self, path: str) -> FileMetadata:
        """Compute and return file metadata."""
        ...
