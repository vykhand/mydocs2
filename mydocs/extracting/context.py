"""Context building utilities for the extraction pipeline.

Converts field definitions to search queries, builds LLM context strings
from retrieved pages, and prepares prompt inputs.
"""

from typing import Optional

from tinystructlog import get_logger

from mydocs.extracting.models import (
    ContentMode,
    FieldDefinition,
    FieldInput,
    FieldPrompt,
    FieldResultRecord,
    PromptInput,
)
from mydocs.models import DocumentPage

log = get_logger(__name__)


def fields_to_query(fields: list[FieldDefinition]) -> str:
    """Convert a list of field definitions into a search query string.

    Concatenates field names and descriptions for use as retriever queries.
    """
    parts = []
    for field in fields:
        parts.append(f"{field.name}: {field.description}")
        if field.prompt:
            parts.append(field.prompt)
    return " ".join(parts)


def get_context(
    pages: list[DocumentPage],
    content_mode: ContentMode = ContentMode.MARKDOWN,
) -> tuple[str, dict[str, str]]:
    """Build LLM context string from retrieved pages.

    Returns:
        A tuple of (context_string, doc_short_to_long) where doc_short_to_long
        maps short document IDs ("1", "2") to actual document IDs.
    """
    if not pages:
        return "", {}

    # Build doc_short_to_long mapping
    unique_doc_ids: list[str] = []
    for page in pages:
        if page.document_id not in unique_doc_ids:
            unique_doc_ids.append(page.document_id)

    doc_long_to_short = {doc_id: str(i + 1) for i, doc_id in enumerate(unique_doc_ids)}
    doc_short_to_long = {v: k for k, v in doc_long_to_short.items()}

    # Group pages by document
    pages_by_doc: dict[str, list[DocumentPage]] = {}
    for page in pages:
        pages_by_doc.setdefault(page.document_id, []).append(page)

    # Build context string
    context_parts = []
    for doc_id in unique_doc_ids:
        short_id = doc_long_to_short[doc_id]
        context_parts.append(f"# Document d{short_id}")

        doc_pages = sorted(pages_by_doc[doc_id], key=lambda p: p.page_number)
        for page in doc_pages:
            context_parts.append(f"## Page {page.page_number}")

            if content_mode == ContentMode.HTML:
                content = page.content_html or page.content_markdown or page.content or ""
            else:
                content = page.content_markdown or page.content or ""

            context_parts.append(content)
            context_parts.append("")  # blank line between pages

    return "\n".join(context_parts), doc_short_to_long


def fields_to_prompts(fields: list[FieldDefinition]) -> list[FieldPrompt]:
    """Convert FieldDefinition objects to FieldPrompt objects for template insertion."""
    prompts = []
    for field in fields:
        prompts.append(FieldPrompt(
            name=field.name,
            description=field.description,
            prompt=field.prompt,
            value_list=field.value_list,
        ))
    return prompts


def format_fields_for_prompt(field_prompts: list[FieldPrompt]) -> str:
    """Format field prompts into a string for insertion into the LLM prompt."""
    parts = []
    for fp in field_prompts:
        entry = f"- **{fp.name}**: {fp.description}"
        if fp.prompt:
            entry += f"\n  Instructions: {fp.prompt.strip()}"
        if fp.value_list:
            options = ", ".join(
                f"{opt.name}" + (f" ({opt.prompt})" if opt.prompt else "")
                for opt in fp.value_list
            )
            entry += f"\n  Allowed values: {options}"
        parts.append(entry)
    return "\n".join(parts)


async def get_prompt_input(
    fields: list[FieldDefinition],
    document_id: str,
    document_type: str,
    subdocument_id: str = "",
) -> PromptInput:
    """Build the complete prompt input for an extraction group.

    Resolves field dependencies by looking up previously extracted
    FieldResultRecords from the database.
    """
    field_prompts = fields_to_prompts(fields)

    # Resolve field dependencies (inputs)
    field_inputs: Optional[list[FieldInput]] = None
    fields_with_inputs = [f for f in fields if f.inputs]

    if fields_with_inputs:
        field_inputs = []
        for field in fields_with_inputs:
            for req in field.inputs:
                # Look up previously extracted result, scoped by subdocument_id
                query = {
                    "document_id": document_id,
                    "field_name": req.field_name,
                    "subdocument_id": subdocument_id,
                }
                records = await FieldResultRecord.afind(query)
                content = None
                if records:
                    content = records[0].result.content

                field_inputs.append(FieldInput(
                    field_name=req.field_name,
                    document_type=req.document_type,
                    content=content,
                ))

    return PromptInput(
        field_prompts=field_prompts,
        field_inputs=field_inputs,
    )
