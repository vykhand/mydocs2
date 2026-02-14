"""Case endpoint handlers."""

import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

from mydocs.backend.dependencies import (
    CaseCreateRequest,
    CaseDocumentsRequest,
    CaseListResponse,
    CaseUpdateRequest,
    DocumentListResponse,
)
from mydocs.models import Case, Document

router = APIRouter(prefix="/api/v1/cases")


def _error(status_code: int, error_code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "error_code": error_code, "status_code": status_code},
    )


@router.get("", response_model=CaseListResponse)
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
):
    query = {}
    if search:
        query["name"] = {"$regex": re.escape(search), "$options": "i"}

    skip = (page - 1) * page_size
    total = await Case.acount(query)
    cases = await Case.afind(
        query,
        sort=[("created_at", -1)],
        skip=skip,
        limit=page_size,
    )

    return CaseListResponse(
        cases=[c.model_dump(by_alias=False, exclude_none=True) for c in cases],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("")
async def create_case(request: CaseCreateRequest):
    now = datetime.utcnow()
    case = Case(
        name=request.name,
        description=request.description,
        created_at=now,
        modified_at=now,
    )
    await case.asave()
    return case.model_dump(by_alias=False, exclude_none=True)


@router.get("/{case_id}")
async def get_case(case_id: str):
    case = await Case.aget(case_id)
    if not case:
        return _error(404, "CASE_NOT_FOUND", f"Case {case_id} not found")
    return case.model_dump(by_alias=False, exclude_none=True)


@router.put("/{case_id}")
async def update_case(case_id: str, request: CaseUpdateRequest):
    case = await Case.aget(case_id)
    if not case:
        return _error(404, "CASE_NOT_FOUND", f"Case {case_id} not found")

    update_fields = {}
    if request.name is not None:
        update_fields["name"] = request.name
    if request.description is not None:
        update_fields["description"] = request.description
    update_fields["modified_at"] = datetime.utcnow()

    await Case.aupdate_one({"_id": case_id}, {"$set": update_fields})
    updated = await Case.aget(case_id)
    return updated.model_dump(by_alias=False, exclude_none=True)


@router.delete("/{case_id}")
async def delete_case(case_id: str):
    case = await Case.aget(case_id)
    if not case:
        return _error(404, "CASE_NOT_FOUND", f"Case {case_id} not found")
    await Case.adelete_one({"_id": case_id})
    return Response(status_code=204)


@router.post("/{case_id}/documents")
async def add_documents_to_case(case_id: str, request: CaseDocumentsRequest):
    case = await Case.aget(case_id)
    if not case:
        return _error(404, "CASE_NOT_FOUND", f"Case {case_id} not found")

    await Case.aupdate_one(
        {"_id": case_id},
        {
            "$addToSet": {"document_ids": {"$each": request.document_ids}},
            "$set": {"modified_at": datetime.utcnow()},
        },
    )
    updated = await Case.aget(case_id)
    return updated.model_dump(by_alias=False, exclude_none=True)


@router.delete("/{case_id}/documents/{document_id}")
async def remove_document_from_case(case_id: str, document_id: str):
    case = await Case.aget(case_id)
    if not case:
        return _error(404, "CASE_NOT_FOUND", f"Case {case_id} not found")

    await Case.aupdate_one(
        {"_id": case_id},
        {
            "$pull": {"document_ids": document_id},
            "$set": {"modified_at": datetime.utcnow()},
        },
    )
    updated = await Case.aget(case_id)
    return updated.model_dump(by_alias=False, exclude_none=True)


@router.get("/{case_id}/documents", response_model=DocumentListResponse)
async def list_case_documents(
    case_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    case = await Case.aget(case_id)
    if not case:
        return _error(404, "CASE_NOT_FOUND", f"Case {case_id} not found")

    doc_ids = case.document_ids or []
    if not doc_ids:
        return DocumentListResponse(documents=[], total=0, page=page, page_size=page_size)

    query = {"_id": {"$in": doc_ids}}
    skip = (page - 1) * page_size
    total = await Document.acount(query)
    docs = await Document.afind(
        query,
        sort=[("created_at", -1)],
        skip=skip,
        limit=page_size,
    )

    return DocumentListResponse(
        documents=[d.model_dump(by_alias=False, exclude_none=True) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )
