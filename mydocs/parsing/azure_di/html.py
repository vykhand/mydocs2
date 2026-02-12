from azure.ai.documentintelligence.models import (
    DocumentKeyValuePair,
    DocumentParagraph,
    DocumentTable,
    ParagraphRole,
)

from mydocs.models import DocumentElementTypeEnum


def table_to_html(table: DocumentTable, short_id: str) -> str:
    """Convert a DocumentTable to HTML with short ID and row/column indices."""
    html = f'<table id="{short_id}">\n'

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

    html += "  <thead>\n    <tr>\n"
    for header in headers:
        html += f"      <th>{header}</th>\n"
    html += "    </tr>\n  </thead>\n"

    html += "  <tbody>\n"
    for row_index in sorted(rows.keys()):
        html += "    <tr>\n"
        for cell_content in rows[row_index]:
            html += f"      <td>{cell_content}</td>\n"
        html += "    </tr>\n"
    html += "  </tbody>\n"

    html += "</table>"
    return html


def kv_to_html(kv: DocumentKeyValuePair, short_id: str) -> str:
    """Convert a key-value pair to HTML with short ID."""
    if not kv.value:
        return f'<div id="{short_id}" class="kv-pair"><strong>Key: {kv.key.content}</strong> (no value)</div>'
    return (
        f'<div id="{short_id}" class="kv-pair">'
        f'<strong class="key">{kv.key.content}</strong> = '
        f'<span class="value">{kv.value.content}</span></div>'
    )


def get_element_html(element_dict: dict, element_type: DocumentElementTypeEnum, short_id: str) -> str:
    """Convert element_dict to HTML with short ID based on element type."""
    if element_type == DocumentElementTypeEnum.PARAGRAPH:
        el = DocumentParagraph(element_dict)
        content = el.content or ""

        if el.role == ParagraphRole.TITLE:
            return f'<h4 id="{short_id}">{content}</h4>'
        elif el.role == ParagraphRole.SECTION_HEADING:
            return f'<h5 id="{short_id}">{content}</h5>'
        elif el.role:
            return f'<p id="{short_id}" data-role="{el.role}">[{el.role.value}] {content}</p>'

        return f'<p id="{short_id}">{content}</p>'

    elif element_type == DocumentElementTypeEnum.TABLE:
        el = DocumentTable(element_dict)
        return table_to_html(el, short_id)

    elif element_type == DocumentElementTypeEnum.KEY_VALUE_PAIR:
        el = DocumentKeyValuePair(element_dict)
        return kv_to_html(el, short_id)

    else:
        return f'<div id="{short_id}">{element_dict.get("content", "")}</div>'
