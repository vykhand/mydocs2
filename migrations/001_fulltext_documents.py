"""Create Atlas Search full-text index on documents collection."""
from lightodm import get_database
from pymongo.operations import SearchIndexModel


def run():
    db = get_database()
    collection = db["documents"]

    definition = {
        "mappings": {
            "dynamic": False,
            "fields": {
                "content": {"type": "string", "analyzer": "lucene.standard"},
                "tags": {"type": "string", "analyzer": "lucene.keyword"},
                "file_name": {"type": "string", "analyzer": "lucene.standard"},
                "status": {"type": "string", "analyzer": "lucene.keyword"},
                "document_type": {"type": "string", "analyzer": "lucene.keyword"},
            },
        }
    }

    index_model = SearchIndexModel(
        definition=definition, name="ft_documents", type="search"
    )
    collection.create_search_index(model=index_model)
    print("Created search index 'ft_documents' on documents collection.")


if __name__ == "__main__":
    run()
