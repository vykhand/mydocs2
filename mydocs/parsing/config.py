from typing import List, Optional

from pydantic import BaseModel

from mydocs.common.base_config import BaseConfig


class EmbeddingConfig(BaseModel):
    model: str = "text-embedding-3-large"
    field_to_embed: str = "content_markdown"
    target_field: str = "emb_content_markdown_text_embedding_3_large"
    dimensions: int = 3072


class ParserConfig(BaseConfig):
    config_name: str = "parser"
    azure_di_model: str = "prebuilt-layout"
    azure_di_kwargs: dict = {
        "output_content_format": "markdown",
        "features": ["keyValuePairs"],
    }
    page_embeddings: Optional[List[EmbeddingConfig]] = None
    document_embeddings: Optional[List[EmbeddingConfig]] = None
    use_cache: bool = False
