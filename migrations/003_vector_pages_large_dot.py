"""Create Atlas Vector Search index on pages collection."""
from lightodm import get_database
from pymongo.operations import SearchIndexModel


def run():
    db = get_database()
    collection = db["pages"]

    definition = {
        "fields": [
            {
                "type": "vector",
                "path": "emb_content_markdown_text_embedding_3_large",
                "similarity": "dotProduct",
                "numDimensions": 3072,
            },
            {"type": "filter", "path": "document_id"},
        ]
    }

    index_model = SearchIndexModel(
        definition=definition, name="vec_pages_large_dot", type="vectorSearch"
    )
    collection.create_search_index(model=index_model)
    print("Created vector search index 'vec_pages_large_dot' on pages collection.")


if __name__ == "__main__":
    run()
