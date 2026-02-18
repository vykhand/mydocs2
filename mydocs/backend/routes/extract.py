"""Extraction API routes."""

from fastapi import APIRouter, HTTPException, Query
from tinystructlog import get_logger

from mydocs.extracting.extractor import BaseExtractor
from mydocs.extracting.models import (
    ContentMode,
    ExtractionRequest,
    ExtractionResponse,
    FieldResultRecord,
    SplitClassifyResult,
)
from mydocs.extracting.prompt_utils import (
    get_prompt,
    get_split_classify_prompt,
    load_case_type_config,
)
from mydocs.extracting.splitter import split_and_classify

log = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["extraction"])


@router.post("/extract", response_model=ExtractionResponse)
async def extract_fields(request: ExtractionRequest):
    """Extract fields from documents using LLM-based extraction."""
    try:
        extractor = BaseExtractor(request)
        response = await extractor.run()
        return response
    except Exception as e:
        log.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/field-results")
async def get_field_results(document_id: str = Query(..., description="Document ID to fetch results for")):
    """Get stored extraction results for a document."""
    try:
        records = await FieldResultRecord.afind({"document_id": document_id})
        return [r.model_dump(by_alias=False) for r in records]
    except Exception as e:
        log.error(f"Failed to fetch field results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SplitClassifyRequest(ExtractionRequest):
    """Request model for split-classify operations.

    Extends ExtractionRequest — the document_type field is used to
    locate the split_classify prompt config.
    """
    pass


@router.post("/split-classify", response_model=SplitClassifyResult)
async def split_classify(request: SplitClassifyRequest):
    """Split and classify a multi-document file into typed segments."""
    if not request.document_ids or len(request.document_ids) != 1:
        raise HTTPException(
            status_code=400,
            detail="Exactly one document_id is required for split-classify"
        )

    try:
        case_type = request.case_type

        # Load case type config to check if split_classify is enabled
        case_config = load_case_type_config(case_type)
        if not case_config.split_classify.enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Split-classify is not enabled for case_type '{case_type}'"
            )

        # Load the split-classify prompt
        prompt_config = get_split_classify_prompt(
            case_type, case_config.split_classify.prompt_name
        )

        result = await split_and_classify(
            document_id=request.document_ids[0],
            prompt_config=prompt_config,
            content_mode=request.content_mode,
            case_type=case_type,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Split-classify failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
