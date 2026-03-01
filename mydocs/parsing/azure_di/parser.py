import os

import litellm
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.core.credentials import AzureKeyCredential
from lightodm import generate_composite_id
from tinystructlog import get_logger

import mydocs.config as C
from mydocs.models import (
    Document,
    DocumentElement,
    DocumentElementTypeEnum,
    DocumentPage,
    StorageBackendEnum,
)
from mydocs.parsing.azure_di.html import get_element_html
from mydocs.parsing.azure_di.markdown import get_element_markdown
from mydocs.parsing.base_parser import DocumentParser
from mydocs.parsing.config import ParserConfig
from mydocs.parsing.storage import get_storage

log = get_logger(__name__)


class AzureDIDocumentParser(DocumentParser):
    """Azure Document Intelligence parser implementation."""

    _analyze_result: AnalyzeResult = None

    def __init__(self, document: Document, parser_config: ParserConfig):
        super().__init__(document, parser_config)
        self._fpath = document.managed_path or document.original_path
        self._storage = get_storage(document.storage_backend)
        self._is_blob = document.storage_backend == StorageBackendEnum.AZURE_BLOB

        # Cache store: remote blob for blob-backed docs, local filesystem otherwise
        if self._is_blob:
            from mydocs.parsing.cache import BlobCacheStore
            self._cache_store = BlobCacheStore(C.AZURE_STORAGE_CACHE_CONTAINER_NAME)
            self._cache_key_prefix = document.id
        else:
            from mydocs.parsing.cache import LocalCacheStore
            self._cache_store = LocalCacheStore()
            self._cache_key_prefix = self._fpath

        self._cache_path = f"{self._cache_key_prefix}.di.json"
        self.client = DocumentIntelligenceClient(
            endpoint=C.AZURE_DI_ENDPOINT,
            credential=AzureKeyCredential(C.AZURE_DI_API_KEY),
            api_version=C.AZURE_DI_API_VERSION,
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the Azure client, cache store, and release the document lock."""
        await self._cache_store.close()
        if self.client:
            await self.client.close()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    async def parse(self) -> Document:
        log.info(f"Processing file: {self._fpath}")
        self._analyze_result = await self._aprocess_file(self._fpath)
        self.document.content = self._analyze_result.content
        self.document.parser_engine = "azure_di"

        log.info("Processing elements.")
        self.document.elements = await self._aprocess_elements()
        await self.document.asave()

        if self.parser_config.document_embeddings:
            await self._embed_document()
        else:
            log.info("Document embeddings are disabled.")

        log.info("Processing pages.")
        self.pages = await self._aprocess_pages()

        if self.parser_config.page_embeddings:
            await self._embed_pages()
        else:
            log.info("Page embeddings are disabled.")

        return self.document

    async def _aprocess_file(self, fpath: str) -> AnalyzeResult:
        """Send file to Azure DI or load from cache."""
        log.info(f"Processing file: {os.path.basename(fpath) if not fpath.startswith('az://') else fpath}.")

        cache_key = self._cache_path
        if self._effective_use_cache and await self._cache_store.exists(cache_key):
            log.info(f"Document intelligence cached results will be loaded from {cache_key}")
            result = AnalyzeResult(await self._cache_store.read_json(cache_key))
        else:
            log.info(f"Parsing file {fpath} with Document Intelligence")
            file_bytes = await self._storage.get_file_bytes(fpath)
            poller = await self.client.begin_analyze_document(
                model_id=self.parser_config.azure_di_model,
                body=file_bytes,
                **self.parser_config.azure_di_kwargs,
            )
            result = await poller.result()
            log.info(f"Saving result to {cache_key}")
            await self._cache_store.write_json(cache_key, result.as_dict())
        return result

    async def _aprocess_elements(self) -> list[DocumentElement]:
        """Extract elements from the analyze result and assign short IDs."""
        if not self._analyze_result or not self.document:
            raise ValueError("Processor is not initialized")

        elements = []
        to_process = []
        if self._analyze_result.paragraphs:
            to_process += [(DocumentElementTypeEnum.PARAGRAPH, el) for el in self._analyze_result.paragraphs]
        if self._analyze_result.key_value_pairs:
            to_process += [(DocumentElementTypeEnum.KEY_VALUE_PAIR, el) for el in self._analyze_result.key_value_pairs]
        if self._analyze_result.tables:
            to_process += [(DocumentElementTypeEnum.TABLE, el) for el in self._analyze_result.tables]

        for typ, el in to_process:
            try:
                if typ == DocumentElementTypeEnum.KEY_VALUE_PAIR:
                    first_bbox = el.key.bounding_regions[0]
                    first_span = el.key.spans[0] if el.key.spans else el.value.spans[0]
                elif typ == DocumentElementTypeEnum.PARAGRAPH:
                    if not el.content:
                        continue
                    first_bbox = el.bounding_regions[0]
                    first_span = el.spans[0]
                else:
                    first_bbox = el.bounding_regions[0]
                    first_span = el.spans[0]
            except Exception as e:
                log.error(f"Error processing element {el}: {e}")
                continue

            element = DocumentElement(
                id=generate_composite_id([self.document.id, first_bbox.page_number, first_span.offset]),
                page_id=generate_composite_id([self.document.id, first_bbox.page_number]),
                page_number=first_bbox.page_number,
                offset=first_span.offset,
                type=typ,
                element_data=el.as_dict(),
            )
            elements.append(element)

        elements = sorted(elements, key=lambda x: x.offset)
        for idx, el in enumerate(elements):
            if el.type == DocumentElementTypeEnum.PARAGRAPH:
                el.short_id = f"p{idx}"
            elif el.type == DocumentElementTypeEnum.TABLE:
                el.short_id = f"t{idx}"
            elif el.type == DocumentElementTypeEnum.KEY_VALUE_PAIR:
                el.short_id = f"kv{idx}"
            else:
                el.short_id = f"el{idx}"

        return elements

    async def _aprocess_pages(self) -> list[DocumentPage]:
        """Build page content from analyze result and elements."""
        if not self._analyze_result or not self.document:
            raise ValueError("Processor is not initialized")
        if not self.document.elements:
            log.warning("No elements found. Skipping page processing.")
            return []

        pages: dict[int, DocumentPage] = {}
        page_elements: dict[int, list[DocumentElement]] = {}

        for page in self._analyze_result.pages:
            pages[page.page_number] = DocumentPage(
                document_id=self.document.id,
                page_number=page.page_number,
                content="\n".join([line.content for line in page.lines]) if page.lines else "",
                width=page.width,
                height=page.height,
                unit=page.unit,
            )

        for element in self.document.elements:
            page_elements.setdefault(element.page_number, []).append(element)

        for page_num, elements in page_elements.items():
            sorted_elements = sorted(elements, key=lambda x: x.offset)

            content_markdown = ""
            content_html = ""

            grouped = {
                "Paragraphs": [e for e in sorted_elements if e.type == DocumentElementTypeEnum.PARAGRAPH],
                "Tables": [e for e in sorted_elements if e.type == DocumentElementTypeEnum.TABLE],
                "Key-Value Pairs": [e for e in sorted_elements if e.type == DocumentElementTypeEnum.KEY_VALUE_PAIR],
            }

            for title, group_elements in grouped.items():
                if not group_elements:
                    continue

                content_markdown += f"### {title}\n\n"
                content_html += f"<h3>{title}</h3>\n"

                for el in group_elements:
                    content_markdown += get_element_markdown(el.element_data, el.type, el.short_id) + "\n"
                    content_html += get_element_html(el.element_data, el.type, el.short_id) + "\n"

            if page_num in pages:
                pages[page_num].content_markdown = content_markdown
                pages[page_num].content_html = content_html
                log.info(f"Saving page {pages[page_num].id}, page_num: {page_num}")
                await pages[page_num].asave()

        return list(pages.values())

    async def _embed_document(self):
        """Generate and store document-level embeddings using litellm."""
        for embedding in self.parser_config.document_embeddings:
            cache_key = f"{self._cache_key_prefix}.doc.{embedding.target_field}.json"
            if self._effective_use_cache and await self._cache_store.exists(cache_key):
                log.info(f"Loading embeddings from cache: {cache_key}")
                embedded_doc = await self._cache_store.read_json(cache_key)
            else:
                log.info("Embedding document.")
                text = getattr(self.document, embedding.field_to_embed) or ""
                response = await litellm.aembedding(
                    model=embedding.model,
                    input=[text],
                )
                embedded_doc = [response.data[0]["embedding"]]
                log.info("Saving embeddings to cache")
                await self._cache_store.write_json(cache_key, embedded_doc)

            await Document.aupdate_one(
                filter={"_id": self.document.id},
                update={"$set": {embedding.target_field: embedded_doc[0]}},
            )
            log.info(f"Document {self.document.id} updated with embedding {embedding.target_field}.")
            self.document = await Document.aget(self.document.id)

    async def _embed_pages(self):
        """Generate and store page-level embeddings using litellm."""
        if not self.pages:
            log.warning("No pages to embed. Skipping page embeddings.")
            return
        for embedding in self.parser_config.page_embeddings:
            cache_key = f"{self._cache_key_prefix}.pages.{embedding.target_field}.json"
            if self._effective_use_cache and await self._cache_store.exists(cache_key):
                log.info(f"Loading embeddings from cache: {cache_key}")
                emb_dict = await self._cache_store.read_json(cache_key)
            else:
                log.info("Embedding pages.")
                pages_to_embed = [p for p in self.pages if getattr(p, embedding.field_to_embed)]
                if not pages_to_embed:
                    log.warning(f"No pages with non-empty {embedding.field_to_embed}. Skipping.")
                    continue
                texts = [getattr(p, embedding.field_to_embed) for p in pages_to_embed]
                response = await litellm.aembedding(
                    model=embedding.model,
                    input=texts,
                )
                embeddings = [item["embedding"] for item in response.data]
                emb_dict = {p.id: emb for p, emb in zip(pages_to_embed, embeddings)}
                log.info("Saving embeddings to cache")
                await self._cache_store.write_json(cache_key, emb_dict)

            for page_id, vector in emb_dict.items():
                log.info(f"Updating page {page_id} with embedding vector, len: {len(vector)}")
                await DocumentPage.aupdate_one(
                    filter={"_id": page_id},
                    update={"$set": {embedding.target_field: vector}},
                )
