from azure.ai.documentintelligence.models import (
    DocumentKeyValuePair,
    DocumentParagraph,
    DocumentTable,
    ParagraphRole,
)

from mydocs.models import DocumentElementTypeEnum


def table_to_markdown(table: DocumentTable) -> str:
    """Convert a DocumentTable to markdown format with row numbers."""
    markdown = ""
    max_columns = max(cell.column_index for cell in table.cells) + 1

    headers = [""] * (max_columns + 1)
    headers[0] = "Row #"
    rows = {}

    for cell in table.cells:
        if cell.row_index == 0:
            headers[cell.column_index + 1] = cell.content
        else:
            if cell.row_index not in rows:
                rows[cell.row_index] = [""] * (max_columns + 1)
                rows[cell.row_index][0] = str(cell.row_index)
            rows[cell.row_index][cell.column_index + 1] = cell.content

    markdown += "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join(["---"] * (max_columns + 1)) + " |\n"

    for row_index in sorted(rows.keys()):
        markdown += "| " + " | ".join(rows[row_index]) + " |\n"
    return markdown


def kv_to_markdown(kv: DocumentKeyValuePair) -> str:
    """Convert a key-value pair to markdown format."""
    if not kv.value:
        return f"** Key: {kv.key.content} (no value) **\n"
    return f"**{kv.key.content}** = {kv.value.content}\n"


def get_element_markdown(element_dict: dict, element_type: DocumentElementTypeEnum, short_id: str = None) -> str:
    """Convert element_dict to Markdown with optional short ID and role handling."""
    prefix = f"[{short_id}] " if short_id else ""

    if element_type == DocumentElementTypeEnum.PARAGRAPH:
        el = DocumentParagraph(element_dict)
        content = el.content or ""

        if el.role == ParagraphRole.TITLE:
            return f"{prefix}#### {content}\n"
        elif el.role == ParagraphRole.SECTION_HEADING:
            return f"{prefix}##### {content}\n"
        elif el.role:
            return f"{prefix}**[{el.role}]** {content}\n"

        return f"{prefix}{content}\n"

    elif element_type == DocumentElementTypeEnum.TABLE:
        el = DocumentTable(element_dict)
        md = table_to_markdown(el)
        return f"Table {prefix}\n\n{md}" if short_id else md

    elif element_type == DocumentElementTypeEnum.KEY_VALUE_PAIR:
        el = DocumentKeyValuePair(element_dict)
        md = kv_to_markdown(el)
        return f"{prefix}{md}"

    else:
        content = element_dict.get("content", "")
        return f"{prefix}{content}"
