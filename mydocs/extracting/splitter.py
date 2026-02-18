"""Document splitting and classification.

Splits multi-document files into segments and classifies each segment
by document type using batched LLM calls.  Persists classified segments
as SubDocument objects on the parent Document.
"""

import json
from datetime import datetime, timezone
from typing import NamedTuple

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
from mydocs.extracting.prompt_utils import calculate_content_hash
from mydocs.models import (
    Document,
    DocumentPage,
    SplitClassifyMeta,
    SubDocument,
    SubDocumentPageRef,
)

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
# Overlap Merging (4-phase algorithm)
# ---------------------------------------------------------------------------

_PageTag = NamedTuple("_PageTag", [
    ("document_type", str),
    ("batch_idx", int),
    ("segment_idx", int),
])


def _centrality_score(page_num: int, batch_pages: list[DocumentPage]) -> float:
    """Score how central a page is within its batch (higher = more central).

    Returns a value in [0, 1] where 1 means perfectly centered.
    """
    page_numbers = sorted(p.page_number for p in batch_pages)
    if len(page_numbers) <= 1:
        return 1.0
    idx = page_numbers.index(page_num)
    mid = (len(page_numbers) - 1) / 2.0
    return 1.0 - abs(idx - mid) / mid


def combine_overlapping_results(
    batch_results: list[LLMSplitClassifyBatchResult],
    batches: list[list[DocumentPage]],
) -> list[SplitSegment]:
    """Merge batch results preserving within-batch segment boundaries.

    Uses a 4-phase algorithm:
    1. Tag: record (document_type, batch_idx, segment_idx) for every page
    2. Select: for pages in multiple batches, pick the most central tag
    3. Build: walk sorted pages; new segment on tag change
    4. Stitch: merge adjacent segments at batch boundaries if they share
       the same origin in an overlapping batch
    """
    if not batch_results:
        return []

    # --- Phase 1: Tag pages ---
    # page_num → list of (tag, centrality_score)
    page_tags: dict[int, list[tuple[_PageTag, float]]] = {}
    batch_page_sets = [
        {p.page_number for p in batch_pages} for batch_pages in batches
    ]

    for batch_idx, (batch_result, batch_pages) in enumerate(
        zip(batch_results, batches)
    ):
        for segment_idx, segment in enumerate(batch_result.result):
            for page_num in segment.page_numbers:
                if page_num not in batch_page_sets[batch_idx]:
                    continue
                tag = _PageTag(
                    document_type=segment.document_type,
                    batch_idx=batch_idx,
                    segment_idx=segment_idx,
                )
                score = _centrality_score(page_num, batch_pages)
                page_tags.setdefault(page_num, []).append((tag, score))

    if not page_tags:
        return []

    # --- Phase 2: Select preferred tag per page ---
    selected: dict[int, _PageTag] = {}
    for page_num, tag_scores in page_tags.items():
        # Pick the tag with the highest centrality score
        best_tag, _ = max(tag_scores, key=lambda ts: ts[1])
        selected[page_num] = best_tag

    # --- Phase 3: Build segments (respecting tag boundaries) ---
    sorted_pages = sorted(selected.keys())
    raw_segments: list[tuple[_PageTag, list[int]]] = []
    current_tag = selected[sorted_pages[0]]
    current_pages = [sorted_pages[0]]

    for page_num in sorted_pages[1:]:
        tag = selected[page_num]
        if (tag.document_type != current_tag.document_type
                or tag.batch_idx != current_tag.batch_idx
                or tag.segment_idx != current_tag.segment_idx):
            raw_segments.append((current_tag, current_pages))
            current_tag = tag
            current_pages = [page_num]
        else:
            current_pages.append(page_num)

    raw_segments.append((current_tag, current_pages))

    # --- Phase 4: Cross-batch stitch ---
    # Merge adjacent segments at batch boundaries only if they share the
    # same (batch_idx, segment_idx) origin in an overlapping batch.
    merged: list[tuple[_PageTag, list[int]]] = [raw_segments[0]]

    for tag, pages in raw_segments[1:]:
        prev_tag, prev_pages = merged[-1]

        if tag.document_type != prev_tag.document_type:
            merged.append((tag, pages))
            continue

        # Check if the boundary pages share a common tag in any batch
        boundary_page = prev_pages[-1]
        next_page = pages[0]
        should_merge = False

        boundary_tags = page_tags.get(boundary_page, [])
        next_tags = page_tags.get(next_page, [])

        for bt, _ in boundary_tags:
            for nt, _ in next_tags:
                if (bt.batch_idx == nt.batch_idx
                        and bt.segment_idx == nt.segment_idx
                        and bt.document_type == nt.document_type):
                    should_merge = True
                    break
            if should_merge:
                break

        if should_merge:
            merged[-1] = (prev_tag, prev_pages + pages)
        else:
            merged.append((tag, pages))

    return [
        SplitSegment(document_type=tag.document_type, page_numbers=pages)
        for tag, pages in merged
    ]


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
    force: bool = False,
) -> SplitClassifyResult:
    """Split and classify a document into typed segments.

    Args:
        document_id: The document to split.
        prompt_config: Prompt configuration with batch_size and overlap_factor.
        content_mode: Which content representation to use.
        case_type: Case type for SubDocument creation.
        force: If True, skip idempotency check and always re-run LLM calls.

    Returns:
        SplitClassifyResult with classified segments and persisted subdocuments.
    """
    doc = await Document.aget(document_id)
    if not doc:
        log.warning(f"Document {document_id} not found")
        return SplitClassifyResult(segments=[])

    # Compute current hashes for idempotency
    file_sha256 = doc.file_metadata.sha256 if doc.file_metadata else ""
    config_hash = calculate_content_hash(
        json.dumps(prompt_config.model_dump(), sort_keys=True)
    )

    # Idempotency check
    if not force and doc.subdocuments and doc.split_classify_meta:
        meta = doc.split_classify_meta
        if (meta.file_sha256 == file_sha256
                and meta.config_hash == config_hash
                and meta.case_type == case_type):
            log.info(
                f"Document {document_id}: split-classify unchanged "
                f"(file hash and config hash match), reusing "
                f"{len(doc.subdocuments)} subdocuments"
            )
            segments = [
                SplitSegment(
                    document_type=sd.document_type,
                    page_numbers=sorted(
                        pr.page_number for pr in sd.page_refs
                    ),
                )
                for sd in doc.subdocuments
            ]
            return SplitClassifyResult(
                segments=segments, subdocuments=doc.subdocuments
            )

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

    doc.subdocuments = subdocuments
    doc.split_classify_meta = SplitClassifyMeta(
        file_sha256=file_sha256,
        config_hash=config_hash,
        case_type=case_type,
        completed_at=datetime.now(timezone.utc),
    )
    await doc.asave()
    log.info(f"Persisted {len(subdocuments)} subdocuments on document {document_id}")

    return SplitClassifyResult(segments=segments, subdocuments=subdocuments)
