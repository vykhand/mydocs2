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
    async def write_managed_sidecar(self, doc_id: str, metadata: dict) -> str:
        """Write a <doc_id>.metadata.json sidecar file in managed storage.

        Returns:
            Path to the sidecar file.
        """
        ...

    @abstractmethod
    async def read_sidecar(self, sidecar_path: str) -> dict:
        """Read and parse a metadata sidecar JSON file.

        Returns:
            Parsed sidecar dict.
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

    @abstractmethod
    async def delete_file(self, path: str) -> None:
        """Delete a file from storage."""
        ...

    @abstractmethod
    async def list_files(self, prefix: str | None = None) -> list[dict]:
        """List files in managed storage.

        Returns:
            List of dicts with keys: name, path, size_bytes.
        """
        ...

    async def generate_download_url(self, path: str, expiry_hours: int = 1) -> str | None:
        """Generate a temporary download URL. Returns None if not supported (e.g. local)."""
        return None
