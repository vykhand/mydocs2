"""Create Atlas Search full-text index on pages collection."""
from lightodm import get_database
from pymongo.operations import SearchIndexModel


def run():
    db = get_database()
    collection = db["pages"]

    definition = {
        "mappings": {
            "dynamic": False,
            "fields": {
                "content": {"type": "string", "analyzer": "lucene.standard"},
                "document_id": {"type": "string", "analyzer": "lucene.keyword"},
            },
        }
    }

    index_model = SearchIndexModel(
        definition=definition, name="ft_pages", type="search"
    )
    collection.create_search_index(model=index_model)
    print("Created search index 'ft_pages' on pages collection.")


if __name__ == "__main__":
    run()
