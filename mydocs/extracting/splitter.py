"""Document splitting and classification.

Splits multi-document files into segments and classifies each segment
by document type using batched LLM calls.  Persists classified segments
as SubDocument objects on the parent Document.
"""

import json
from datetime import datetime, timezone

import litellm
from lightodm import generate_composite_id
from tinystructlog import get_logger

from mydocs.extracting.context import get_context
from mydocs.extracting.models import (
    ContentMode,
    LLMSplitClassifyBatchResult,
    PromptConfig,
    SplitClassifyResult,
    SplitSegment,
)
from mydocs.models import Document, DocumentPage, SubDocument, SubDocumentPageRef

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Batching
# ---------------------------------------------------------------------------

def batch_pages_with_overlap(
    pages: list[DocumentPage],
    batch_size: int = 12,
    overlap_factor: int = 3,
) -> list[list[DocumentPage]]:
    """Divide pages into overlapping batches.

    Args:
        pages: Sorted list of pages.
        batch_size: Number of pages per batch.
        overlap_factor: Number of pages to overlap between consecutive batches.

    Returns:
        List of page batches.
    """
    if not pages:
        return []

    batches = []
    step = max(1, batch_size - overlap_factor)
    for start in range(0, len(pages), step):
        batch = pages[start : start + batch_size]
        batches.append(batch)
        if start + batch_size >= len(pages):
            break

    return batches


# ---------------------------------------------------------------------------
# Context Generation
# ---------------------------------------------------------------------------

def generate_split_context(
    pages: list[DocumentPage],
    content_mode: ContentMode = ContentMode.MARKDOWN,
) -> str:
    """Generate context string for a batch of pages."""
    context, _ = get_context(pages, content_mode)
    return context


# ---------------------------------------------------------------------------
# LLM Call
# ---------------------------------------------------------------------------

async def run_llm_split_classify(
    context: str,
    prompt_config: PromptConfig,
    batch_num: int,
    total_batches: int,
) -> LLMSplitClassifyBatchResult:
    """Run the LLM to classify pages in a single batch.

    Uses litellm with structured output and a two-level retry strategy:
    - Transport retries (transport_retries): Handled by litellm internally.
    - Validation retries (validation_retries): Outer loop retries on schema
      validation failures.
    """
    sys_prompt = prompt_config.sys_prompt_template
    user_prompt = prompt_config.user_prompt_template.format(
        context=context,
        batch_num=batch_num,
        total_batches=total_batches,
    )

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_error = None
    for attempt in range(prompt_config.validation_retries):
        try:
            response = await litellm.acompletion(
                model=prompt_config.model,
                messages=messages,
                response_format=LLMSplitClassifyBatchResult,
                num_retries=prompt_config.transport_retries,
                **prompt_config.llm_kwargs,
            )

            content = response.choices[0].message.content
            return LLMSplitClassifyBatchResult.model_validate_json(content)

        except litellm.exceptions.APIError:
            raise  # Transport errors already retried by litellm; don't retry again

        except Exception as e:
            last_error = e
            log.warning(
                f"Validation attempt {attempt + 1}/{prompt_config.validation_retries} "
                f"failed: {e}"
            )

    raise last_error


# ---------------------------------------------------------------------------
# Overlap Merging
# ---------------------------------------------------------------------------

def combine_overlapping_results(
    batch_results: list[LLMSplitClassifyBatchResult],
    batches: list[list[DocumentPage]],
) -> list[SplitSegment]:
    """Merge batch results, resolving overlapping page classifications.

    For overlapping pages, the classification from the batch where the
    page is more centrally positioned (not at the boundary) is preferred.
    """
    # Build page_number → document_type mapping
    page_classifications: dict[int, str] = {}

    for batch_idx, (batch_result, batch_pages) in enumerate(
        zip(batch_results, batches)
    ):
        batch_page_numbers = {p.page_number for p in batch_pages}

        for segment in batch_result.result:
            for page_num in segment.page_numbers:
                if page_num not in batch_page_numbers:
                    continue

                if page_num not in page_classifications:
                    page_classifications[page_num] = segment.document_type
                else:
                    # Prefer classification from a batch where this page
                    # is not at the boundary (more central position)
                    batch_page_list = sorted(batch_page_numbers)
                    if batch_page_list:
                        mid = len(batch_page_list) // 2
                        page_pos = batch_page_list.index(page_num) if page_num in batch_page_list else -1
                        # If this page is in the middle half, prefer this classification
                        if abs(page_pos - mid) < len(batch_page_list) // 4 + 1:
                            page_classifications[page_num] = segment.document_type

    # Convert to contiguous segments
    if not page_classifications:
        return []

    sorted_pages = sorted(page_classifications.keys())
    segments: list[SplitSegment] = []
    current_type = page_classifications[sorted_pages[0]]
    current_pages = [sorted_pages[0]]

    for page_num in sorted_pages[1:]:
        if page_classifications[page_num] == current_type:
            current_pages.append(page_num)
        else:
            segments.append(SplitSegment(
                document_type=current_type,
                page_numbers=current_pages,
            ))
            current_type = page_classifications[page_num]
            current_pages = [page_num]

    segments.append(SplitSegment(
        document_type=current_type,
        page_numbers=current_pages,
    ))

    return segments


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

async def _build_subdocuments(
    document_id: str,
    case_type: str,
    segments: list[SplitSegment],
    pages: list[DocumentPage],
) -> list[SubDocument]:
    """Build SubDocument objects from split segments.

    Resolves page numbers to page IDs and creates deterministic SubDocument IDs.
    """
    # Build page_number → page lookup
    page_by_number = {p.page_number: p for p in pages}

    subdocuments = []
    for segment in segments:
        page_refs = []
        for pn in segment.page_numbers:
            page = page_by_number.get(pn)
            if page:
                page_refs.append(SubDocumentPageRef(
                    document_id=document_id,
                    page_id=str(page.id),
                    page_number=pn,
                ))

        if not page_refs:
            continue

        min_page = min(pr.page_number for pr in page_refs)
        subdoc_id = generate_composite_id([
            document_id, case_type, segment.document_type, str(min_page),
        ])

        subdocuments.append(SubDocument(
            id=subdoc_id,
            case_type=case_type,
            document_type=segment.document_type,
            page_refs=page_refs,
            created_at=datetime.now(timezone.utc),
        ))

    return subdocuments


async def split_and_classify(
    document_id: str,
    prompt_config: PromptConfig,
    content_mode: ContentMode = ContentMode.MARKDOWN,
    case_type: str = "generic",
) -> SplitClassifyResult:
    """Split and classify a document into typed segments.

    Args:
        document_id: The document to split.
        prompt_config: Prompt configuration with batch_size and overlap_factor.
        content_mode: Which content representation to use.
        case_type: Case type for SubDocument creation.

    Returns:
        SplitClassifyResult with classified segments and persisted subdocuments.
    """
    batch_size = prompt_config.batch_size or 12
    overlap_factor = prompt_config.overlap_factor or 3

    # Fetch all pages for the document
    pages = await DocumentPage.afind({"document_id": document_id})
    pages = sorted(pages, key=lambda p: p.page_number)

    if not pages:
        log.warning(f"No pages found for document {document_id}")
        return SplitClassifyResult(segments=[])

    log.info(f"Splitting document {document_id}: {len(pages)} pages")

    # Create batches
    batches = batch_pages_with_overlap(pages, batch_size, overlap_factor)
    total_batches = len(batches)

    log.info(f"Created {total_batches} batches (batch_size={batch_size}, overlap={overlap_factor})")

    # Classify each batch
    batch_results: list[LLMSplitClassifyBatchResult] = []
    for batch_num, batch in enumerate(batches, start=1):
        context = generate_split_context(batch, content_mode)
        result = await run_llm_split_classify(
            context, prompt_config, batch_num, total_batches
        )
        batch_results.append(result)
        log.debug(f"Batch {batch_num}/{total_batches}: {len(result.result)} segments")

    # Merge overlapping results
    segments = combine_overlapping_results(batch_results, batches)

    log.info(f"Split result: {len(segments)} segments")

    # Build and persist SubDocuments on the parent Document
    subdocuments = await _build_subdocuments(document_id, case_type, segments, pages)
    if subdocuments:
        doc = await Document.aget(document_id)
        if doc:
            doc.subdocuments = subdocuments
            await doc.asave()
            log.info(f"Persisted {len(subdocuments)} subdocuments on document {document_id}")
        else:
            log.warning(f"Document {document_id} not found, subdocuments not persisted")

    return SplitClassifyResult(segments=segments, subdocuments=subdocuments)
