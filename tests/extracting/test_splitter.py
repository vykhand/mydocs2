"""Tests for mydocs.extracting.splitter — merge algorithm and idempotency."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mydocs.extracting.models import (
    LLMSplitClassifyBatchResult,
    SplitSegment,
)
from mydocs.extracting.splitter import (
    _PageTag,
    _centrality_score,
    combine_overlapping_results,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_page(page_number: int, document_id: str = "doc1") -> MagicMock:
    """Create a mock DocumentPage with the given page_number."""
    page = MagicMock()
    page.page_number = page_number
    page.document_id = document_id
    page.id = f"page_{page_number}"
    return page


def _make_batch_result(segments: list[tuple[str, list[int]]]) -> LLMSplitClassifyBatchResult:
    """Create a batch result from (document_type, page_numbers) tuples."""
    return LLMSplitClassifyBatchResult(
        result=[
            SplitSegment(document_type=dt, page_numbers=pns)
            for dt, pns in segments
        ]
    )


# ---------------------------------------------------------------------------
# Tests: combine_overlapping_results
# ---------------------------------------------------------------------------

class TestCombineOverlappingResults:
    """Tests for the 4-phase merge algorithm."""

    def test_empty_input(self):
        """Empty batch results return an empty list."""
        result = combine_overlapping_results([], [])
        assert result == []

    def test_single_batch_single_segment(self):
        """A single batch with one segment passes through."""
        pages = [_make_page(i) for i in range(1, 6)]
        batch_result = _make_batch_result([("invoice", [1, 2, 3, 4, 5])])

        result = combine_overlapping_results([batch_result], [pages])

        assert len(result) == 1
        assert result[0].document_type == "invoice"
        assert result[0].page_numbers == [1, 2, 3, 4, 5]

    def test_single_batch_multiple_same_type_segments(self):
        """Multiple same-type segments in a single batch stay separate.

        This is the core bug fix — 3 receipts must remain 3 segments.
        """
        pages = [_make_page(i) for i in range(1, 7)]
        batch_result = _make_batch_result([
            ("receipt", [1, 2]),
            ("receipt", [3, 4]),
            ("receipt", [5, 6]),
        ])

        result = combine_overlapping_results([batch_result], [pages])

        assert len(result) == 3
        assert all(s.document_type == "receipt" for s in result)
        assert result[0].page_numbers == [1, 2]
        assert result[1].page_numbers == [3, 4]
        assert result[2].page_numbers == [5, 6]

    def test_single_batch_mixed_types(self):
        """Different document types produce separate segments."""
        pages = [_make_page(i) for i in range(1, 7)]
        batch_result = _make_batch_result([
            ("invoice", [1, 2, 3]),
            ("receipt", [4, 5, 6]),
        ])

        result = combine_overlapping_results([batch_result], [pages])

        assert len(result) == 2
        assert result[0].document_type == "invoice"
        assert result[0].page_numbers == [1, 2, 3]
        assert result[1].document_type == "receipt"
        assert result[1].page_numbers == [4, 5, 6]

    def test_cross_batch_document_spanning_boundary(self):
        """A document spanning a batch boundary is stitched together.

        Batch 1: pages 1-5 (overlap pages 4,5)
        Batch 2: pages 4-8 (overlap pages 4,5)
        Both batches assign pages 4,5 to the same segment type — they
        share a common segment in the overlap, so they should be merged.
        """
        batch1_pages = [_make_page(i) for i in range(1, 6)]  # pages 1-5
        batch2_pages = [_make_page(i) for i in range(4, 9)]  # pages 4-8

        batch1_result = _make_batch_result([
            ("invoice", [1, 2, 3, 4, 5]),
        ])
        batch2_result = _make_batch_result([
            ("invoice", [4, 5, 6, 7, 8]),
        ])

        result = combine_overlapping_results(
            [batch1_result, batch2_result],
            [batch1_pages, batch2_pages],
        )

        assert len(result) == 1
        assert result[0].document_type == "invoice"
        assert result[0].page_numbers == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_same_type_at_batch_boundary_different_documents(self):
        """Same type at batch boundary but different documents stays separate.

        Batch 1: pages 1-5, two receipts (1-3) and (4-5)
        Batch 2: pages 4-8, receipt (4-5) and invoice (6-8)

        The receipt ending at page 5 in batch 1 (segment 1) and the
        receipt at pages 4-5 in batch 2 (segment 0) share the same
        pages in the overlap — they should stitch. But if batch 1 has
        receipt (1-3) ending, and batch 2 has a NEW receipt (4-5) starting,
        those should NOT stitch since they are different segments.
        """
        batch1_pages = [_make_page(i) for i in range(1, 6)]  # pages 1-5
        batch2_pages = [_make_page(i) for i in range(4, 9)]  # pages 4-8

        # Batch 1: receipt1=[1,2,3], receipt2=[4,5]
        batch1_result = _make_batch_result([
            ("receipt", [1, 2, 3]),
            ("receipt", [4, 5]),
        ])
        # Batch 2: receipt=[4,5], invoice=[6,7,8]
        batch2_result = _make_batch_result([
            ("receipt", [4, 5]),
            ("invoice", [6, 7, 8]),
        ])

        result = combine_overlapping_results(
            [batch1_result, batch2_result],
            [batch1_pages, batch2_pages],
        )

        # receipt1=[1,2,3] stays separate, receipt2=[4,5] stitched, invoice=[6,7,8]
        assert len(result) == 3
        assert result[0].document_type == "receipt"
        assert result[0].page_numbers == [1, 2, 3]
        assert result[1].document_type == "receipt"
        assert result[1].page_numbers == [4, 5]
        assert result[2].document_type == "invoice"
        assert result[2].page_numbers == [6, 7, 8]

    def test_ten_receipts_single_batch(self):
        """10 single-page receipts in one batch remain 10 segments."""
        pages = [_make_page(i) for i in range(1, 11)]
        batch_result = _make_batch_result([
            ("receipt", [i]) for i in range(1, 11)
        ])

        result = combine_overlapping_results([batch_result], [pages])

        assert len(result) == 10
        for i, seg in enumerate(result):
            assert seg.document_type == "receipt"
            assert seg.page_numbers == [i + 1]

    def test_overlapping_pages_prefer_central_batch(self):
        """Overlapping pages prefer classification from the more central batch."""
        # Batch 1: pages 1-4, all invoice
        # Batch 2: pages 3-6, pages 3-4 reclassified as receipt, 5-6 receipt
        # Page 3 is at the boundary of batch 1 but central in batch 2
        # Page 4 is more central in batch 1
        batch1_pages = [_make_page(i) for i in range(1, 5)]  # pages 1-4
        batch2_pages = [_make_page(i) for i in range(3, 7)]  # pages 3-6

        batch1_result = _make_batch_result([
            ("invoice", [1, 2, 3, 4]),
        ])
        batch2_result = _make_batch_result([
            ("receipt", [3, 4, 5, 6]),
        ])

        result = combine_overlapping_results(
            [batch1_result, batch2_result],
            [batch1_pages, batch2_pages],
        )

        # Both batches provide classifications for pages 3 and 4.
        # The selected types depend on centrality scores.
        # Verify all pages are covered.
        all_pages = []
        for seg in result:
            all_pages.extend(seg.page_numbers)
        assert sorted(all_pages) == [1, 2, 3, 4, 5, 6]

    def test_empty_batch_result(self):
        """A batch result with no segments in result list."""
        pages = [_make_page(i) for i in range(1, 4)]
        batch_result = _make_batch_result([])

        result = combine_overlapping_results([batch_result], [pages])
        assert result == []

    def test_pages_outside_batch_ignored(self):
        """Pages referenced by LLM but not in the batch are ignored."""
        pages = [_make_page(i) for i in range(1, 4)]
        # LLM references page 99 which isn't in the batch
        batch_result = _make_batch_result([
            ("invoice", [1, 2, 3, 99]),
        ])

        result = combine_overlapping_results([batch_result], [pages])

        assert len(result) == 1
        assert result[0].page_numbers == [1, 2, 3]


class TestCentralityScore:
    """Tests for _centrality_score helper."""

    def test_single_page_batch(self):
        pages = [_make_page(1)]
        assert _centrality_score(1, pages) == 1.0

    def test_center_page(self):
        pages = [_make_page(i) for i in range(1, 6)]
        score = _centrality_score(3, pages)
        assert score == 1.0  # page 3 is index 2, mid=2.0

    def test_edge_page(self):
        pages = [_make_page(i) for i in range(1, 6)]
        score_edge = _centrality_score(1, pages)
        score_center = _centrality_score(3, pages)
        assert score_edge < score_center


# ---------------------------------------------------------------------------
# Tests: split_and_classify idempotency
# ---------------------------------------------------------------------------

class TestSplitAndClassifyIdempotency:
    """Tests for hash-based idempotency in split_and_classify."""

    @pytest.mark.asyncio
    async def test_matching_hashes_skip_llm(self):
        """When hashes match, LLM is not called and existing subdocuments are returned."""
        from mydocs.extracting.splitter import split_and_classify
        from mydocs.models import (
            SplitClassifyMeta,
            SubDocument,
            SubDocumentPageRef,
        )
        from mydocs.extracting.models import PromptConfig

        # Build a mock document with existing subdocuments and matching meta
        mock_subdocs = [
            SubDocument(
                id="sd1",
                case_type="generic",
                document_type="receipt",
                page_refs=[
                    SubDocumentPageRef(document_id="doc1", page_id="p1", page_number=1),
                    SubDocumentPageRef(document_id="doc1", page_id="p2", page_number=2),
                ],
            )
        ]

        prompt_config = PromptConfig(
            name="test",
            sys_prompt_template="test",
            user_prompt_template="test {context} {batch_num} {total_batches}",
            batch_size=12,
            overlap_factor=3,
        )

        import json as _json
        config_hash_value = __import__("mydocs.extracting.prompt_utils", fromlist=["calculate_content_hash"]).calculate_content_hash(
            _json.dumps(prompt_config.model_dump(), sort_keys=True)
        )

        mock_meta = SplitClassifyMeta(
            file_sha256="abc123",
            config_hash=config_hash_value,
            case_type="generic",
            completed_at=datetime.now(timezone.utc),
        )

        mock_doc = MagicMock()
        mock_doc.subdocuments = mock_subdocs
        mock_doc.split_classify_meta = mock_meta
        mock_doc.file_metadata = MagicMock()
        mock_doc.file_metadata.sha256 = "abc123"

        with patch("mydocs.extracting.splitter.Document") as MockDocument, \
             patch("mydocs.extracting.splitter.run_llm_split_classify") as mock_llm:

            MockDocument.aget = AsyncMock(return_value=mock_doc)

            result = await split_and_classify(
                document_id="doc1",
                prompt_config=prompt_config,
                case_type="generic",
            )

            # LLM should NOT have been called
            mock_llm.assert_not_called()

            # Should return existing subdocuments
            assert result.subdocuments == mock_subdocs
            assert len(result.segments) == 1
            assert result.segments[0].document_type == "receipt"
            assert result.segments[0].page_numbers == [1, 2]

    @pytest.mark.asyncio
    async def test_different_file_hash_triggers_llm(self):
        """When file hash differs, LLM is called."""
        from mydocs.extracting.splitter import split_and_classify
        from mydocs.models import SplitClassifyMeta, SubDocument, SubDocumentPageRef
        from mydocs.extracting.models import PromptConfig

        prompt_config = PromptConfig(
            name="test",
            sys_prompt_template="test",
            user_prompt_template="test {context} {batch_num} {total_batches}",
            batch_size=12,
            overlap_factor=3,
        )

        mock_meta = SplitClassifyMeta(
            file_sha256="old_hash",  # Different from current
            config_hash="whatever",
            case_type="generic",
            completed_at=datetime.now(timezone.utc),
        )

        mock_doc = MagicMock()
        mock_doc.subdocuments = [MagicMock()]
        mock_doc.split_classify_meta = mock_meta
        mock_doc.file_metadata = MagicMock()
        mock_doc.file_metadata.sha256 = "new_hash"  # Changed
        mock_doc.asave = AsyncMock()

        mock_pages = [_make_page(1)]

        with patch("mydocs.extracting.splitter.Document") as MockDocument, \
             patch("mydocs.extracting.splitter.DocumentPage") as MockDocPage, \
             patch("mydocs.extracting.splitter.generate_split_context", return_value="mock context"), \
             patch("mydocs.extracting.splitter.run_llm_split_classify") as mock_llm, \
             patch("mydocs.extracting.splitter._build_subdocuments", new_callable=AsyncMock) as mock_build:

            MockDocument.aget = AsyncMock(return_value=mock_doc)
            MockDocPage.afind = AsyncMock(return_value=mock_pages)
            mock_llm.return_value = _make_batch_result([("receipt", [1])])
            mock_build.return_value = []

            await split_and_classify(
                document_id="doc1",
                prompt_config=prompt_config,
                case_type="generic",
            )

            # LLM SHOULD have been called
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_different_config_hash_triggers_llm(self):
        """When config hash differs, LLM is called."""
        from mydocs.extracting.splitter import split_and_classify
        from mydocs.models import SplitClassifyMeta
        from mydocs.extracting.models import PromptConfig

        prompt_config = PromptConfig(
            name="test",
            sys_prompt_template="test",
            user_prompt_template="test {context} {batch_num} {total_batches}",
            batch_size=12,
            overlap_factor=3,
        )

        mock_meta = SplitClassifyMeta(
            file_sha256="abc123",
            config_hash="old_config_hash",  # Different from current
            case_type="generic",
            completed_at=datetime.now(timezone.utc),
        )

        mock_doc = MagicMock()
        mock_doc.subdocuments = [MagicMock()]
        mock_doc.split_classify_meta = mock_meta
        mock_doc.file_metadata = MagicMock()
        mock_doc.file_metadata.sha256 = "abc123"
        mock_doc.asave = AsyncMock()

        mock_pages = [_make_page(1)]

        with patch("mydocs.extracting.splitter.Document") as MockDocument, \
             patch("mydocs.extracting.splitter.DocumentPage") as MockDocPage, \
             patch("mydocs.extracting.splitter.generate_split_context", return_value="mock context"), \
             patch("mydocs.extracting.splitter.run_llm_split_classify") as mock_llm, \
             patch("mydocs.extracting.splitter._build_subdocuments", new_callable=AsyncMock) as mock_build:

            MockDocument.aget = AsyncMock(return_value=mock_doc)
            MockDocPage.afind = AsyncMock(return_value=mock_pages)
            mock_llm.return_value = _make_batch_result([("receipt", [1])])
            mock_build.return_value = []

            await split_and_classify(
                document_id="doc1",
                prompt_config=prompt_config,
                case_type="generic",
            )

            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_bypasses_idempotency(self):
        """force=True runs LLM even when all hashes match."""
        from mydocs.extracting.splitter import split_and_classify
        from mydocs.models import SplitClassifyMeta
        from mydocs.extracting.models import PromptConfig
        from mydocs.extracting.prompt_utils import calculate_content_hash

        prompt_config = PromptConfig(
            name="test",
            sys_prompt_template="test",
            user_prompt_template="test {context} {batch_num} {total_batches}",
            batch_size=12,
            overlap_factor=3,
        )

        config_hash_value = calculate_content_hash(
            json.dumps(prompt_config.model_dump(), sort_keys=True)
        )

        mock_meta = SplitClassifyMeta(
            file_sha256="abc123",
            config_hash=config_hash_value,
            case_type="generic",
            completed_at=datetime.now(timezone.utc),
        )

        mock_doc = MagicMock()
        mock_doc.subdocuments = [MagicMock()]
        mock_doc.split_classify_meta = mock_meta
        mock_doc.file_metadata = MagicMock()
        mock_doc.file_metadata.sha256 = "abc123"
        mock_doc.asave = AsyncMock()

        mock_pages = [_make_page(1)]

        with patch("mydocs.extracting.splitter.Document") as MockDocument, \
             patch("mydocs.extracting.splitter.DocumentPage") as MockDocPage, \
             patch("mydocs.extracting.splitter.generate_split_context", return_value="mock context"), \
             patch("mydocs.extracting.splitter.run_llm_split_classify") as mock_llm, \
             patch("mydocs.extracting.splitter._build_subdocuments", new_callable=AsyncMock) as mock_build:

            MockDocument.aget = AsyncMock(return_value=mock_doc)
            MockDocPage.afind = AsyncMock(return_value=mock_pages)
            mock_llm.return_value = _make_batch_result([("receipt", [1])])
            mock_build.return_value = []

            await split_and_classify(
                document_id="doc1",
                prompt_config=prompt_config,
                case_type="generic",
                force=True,
            )

            # LLM SHOULD have been called despite matching hashes
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_prior_meta_triggers_llm(self):
        """When split_classify_meta is None, LLM is called (first run)."""
        from mydocs.extracting.splitter import split_and_classify
        from mydocs.extracting.models import PromptConfig

        prompt_config = PromptConfig(
            name="test",
            sys_prompt_template="test",
            user_prompt_template="test {context} {batch_num} {total_batches}",
            batch_size=12,
            overlap_factor=3,
        )

        mock_doc = MagicMock()
        mock_doc.subdocuments = None
        mock_doc.split_classify_meta = None
        mock_doc.file_metadata = MagicMock()
        mock_doc.file_metadata.sha256 = "abc123"
        mock_doc.asave = AsyncMock()

        mock_pages = [_make_page(1)]

        with patch("mydocs.extracting.splitter.Document") as MockDocument, \
             patch("mydocs.extracting.splitter.DocumentPage") as MockDocPage, \
             patch("mydocs.extracting.splitter.generate_split_context", return_value="mock context"), \
             patch("mydocs.extracting.splitter.run_llm_split_classify") as mock_llm, \
             patch("mydocs.extracting.splitter._build_subdocuments", new_callable=AsyncMock) as mock_build:

            MockDocument.aget = AsyncMock(return_value=mock_doc)
            MockDocPage.afind = AsyncMock(return_value=mock_pages)
            mock_llm.return_value = _make_batch_result([("invoice", [1])])
            mock_build.return_value = []

            await split_and_classify(
                document_id="doc1",
                prompt_config=prompt_config,
                case_type="generic",
            )

            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_meta_persisted_after_classification(self):
        """After successful classification, SplitClassifyMeta is saved on the document."""
        from mydocs.extracting.splitter import split_and_classify
        from mydocs.extracting.models import PromptConfig
        from mydocs.models import SplitClassifyMeta

        prompt_config = PromptConfig(
            name="test",
            sys_prompt_template="test",
            user_prompt_template="test {context} {batch_num} {total_batches}",
            batch_size=12,
            overlap_factor=3,
        )

        mock_doc = MagicMock()
        mock_doc.subdocuments = None
        mock_doc.split_classify_meta = None
        mock_doc.file_metadata = MagicMock()
        mock_doc.file_metadata.sha256 = "abc123"
        mock_doc.asave = AsyncMock()

        mock_pages = [_make_page(1)]

        with patch("mydocs.extracting.splitter.Document") as MockDocument, \
             patch("mydocs.extracting.splitter.DocumentPage") as MockDocPage, \
             patch("mydocs.extracting.splitter.generate_split_context", return_value="mock context"), \
             patch("mydocs.extracting.splitter.run_llm_split_classify") as mock_llm, \
             patch("mydocs.extracting.splitter._build_subdocuments", new_callable=AsyncMock) as mock_build:

            MockDocument.aget = AsyncMock(return_value=mock_doc)
            MockDocPage.afind = AsyncMock(return_value=mock_pages)
            mock_llm.return_value = _make_batch_result([("invoice", [1])])
            mock_build.return_value = []

            await split_and_classify(
                document_id="doc1",
                prompt_config=prompt_config,
                case_type="generic",
            )

            # Verify meta was set on the document
            assert mock_doc.split_classify_meta is not None
            assert isinstance(mock_doc.split_classify_meta, SplitClassifyMeta)
            assert mock_doc.split_classify_meta.file_sha256 == "abc123"
            assert mock_doc.split_classify_meta.case_type == "generic"

            # Verify document was saved
            mock_doc.asave.assert_called_once()
