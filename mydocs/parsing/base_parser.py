from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from tinystructlog import get_logger

from mydocs.parsing.config import ParserConfig
from mydocs.parsing.models import Document, DocumentPage, DocumentStatusEnum

log = get_logger(__name__)


class DocumentLockedException(Exception):
    pass


class DocumentParser(ABC):
    """
    Abstract base for document parsing.
    Used as an async context manager to handle document locking.
    """

    def __init__(self, document: Document, parser_config: ParserConfig):
        self.document = document
        self.parser_config = parser_config
        self.pages: List[DocumentPage] = []
        self.parser_config_hash = parser_config.dump_config().config_hash

    async def __aenter__(self) -> "DocumentParser":
        """Load existing document state and acquire processing lock."""
        existing = await Document.afind_one({"_id": self.document.id})
        if existing:
            self.document = existing
            self.document.parser_config_hash = self.parser_config_hash
            self.document.modified_at = datetime.now()
        else:
            self.document.parser_config_hash = self.parser_config_hash
            self.document.created_at = datetime.now()

        if self.document.locked:
            log.warning(f"Document {self.document.id} is already locked.")
            raise DocumentLockedException(f"Document {self.document.id} is locked by another process.")

        self.document.locked = True
        self.document.status = DocumentStatusEnum.PARSING
        log.info(f"Locking document: {self.document.id}, config hash: {self.parser_config_hash}")
        await self.document.asave()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Release processing lock and handle errors."""
        if self.document:
            self.document.locked = False
            if exc_type:
                self.document.status = DocumentStatusEnum.FAILED
                log.error(f"Error during processing document {self.document.id}: {exc_val}")
            else:
                self.document.status = DocumentStatusEnum.PARSED
            self.document.modified_at = datetime.now()
            log.info(f"Releasing lock on document: {self.document.id}, status: {self.document.status}")
            await self.document.asave()

        return False

    @abstractmethod
    async def parse(self) -> Document:
        """Parse the document and return it with elements and pages populated."""
        ...
