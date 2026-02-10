# Migration System Specification

**Version**: 1.0
**Status**: Draft

**Related Specs**: [parsing-engine.md](parsing-engine.md) (standard indexes), [retrieval-engine.md](retrieval-engine.md) (search indexes), [cli.md](cli.md) (`mydocs migrate`)

---

## 1. Overview

The migration system manages database index creation and maintenance for MongoDB. It handles three types of indexes:

- **Standard indexes** -- regular MongoDB indexes for query performance (defined in [parsing-engine.md](parsing-engine.md))
- **Atlas Search indexes** -- full-text search indexes (defined in [retrieval-engine.md](retrieval-engine.md))
- **Atlas Vector Search indexes** -- vector search indexes (defined in [retrieval-engine.md](retrieval-engine.md))

Migrations are implemented as standalone Python scripts, discovered and executed by a migration runner.

---

## 2. Migration Scripts

Migration scripts live in the `migrations/` directory at the project root:

```
migrations/
  001_fulltext_documents.py
  002_fulltext_pages.py
  003_vector_pages_large_dot.py
```

### 2.1 Script Convention

- File names follow the pattern `{NNN}_{description}.py` where `NNN` is a zero-padded sequence number
- Scripts are executed in numerical order
- Each script uses `lightodm.get_database()` to access the MongoDB database directly

### 2.2 Example Migration Script

```python
from lightodm import get_database
from pymongo.operations import SearchIndexModel

db = get_database()
collection = db["pages"]

definition = {
    "fields": [
        {
            "type": "vector",
            "path": "emb_content_markdown_text_embedding_3_large",
            "similarity": "dotProduct",
            "numDimensions": 3072
        },
        {"type": "filter", "path": "document_id"}
    ]
}

index_model = SearchIndexModel(definition=definition, name="vec_pages_large_dot", type="vectorSearch")
collection.create_search_index(model=index_model)
```

---

## 3. Index Definitions

### 3.1 Standard Indexes

Regular MongoDB indexes for query performance:

```
documents:
  - { status: 1 }
  - { tags: 1 }
  - { file_type: 1 }
  - { created_at: -1 }
  - { "file_metadata.sha256": 1 }         # For deduplication

pages:
  - { document_id: 1, page_number: 1 }    # Compound for page lookup
  - { document_id: 1 }                     # For all pages of a document
```

### 3.2 Atlas Search Indexes

| Index Name | Collection | Fields | Description |
|------------|------------|--------|-------------|
| `ft_documents` | `documents` | `content`, `tags`, `file_name`, `status`, `document_type` | Full-text search on documents |
| `ft_pages` | `pages` | `content`, `document_id` | Full-text search on pages |

See [retrieval-engine.md](retrieval-engine.md) Section 2.1 for full index definitions.

### 3.3 Atlas Vector Search Indexes

| Index Name | Collection | Vector Field | Dimensions | Similarity | Filters |
|------------|------------|-------------|------------|------------|---------|
| `vec_pages_large_dot` | `pages` | `emb_content_markdown_text_embedding_3_large` | 3072 | dotProduct | `document_id` |

See [retrieval-engine.md](retrieval-engine.md) Section 3.3 for full index definitions.

---

## 4. Migration Runner

### 4.1 Discovery

The migration runner scans the `migrations/` directory for Python files matching the `{NNN}_*.py` pattern, sorted by sequence number.

### 4.2 Execution

- Scripts are executed sequentially in order
- Each script runs as a standalone Python module
- The runner logs the start and completion of each migration

### 4.3 CLI Integration

Migrations are executed via the CLI:

```bash
mydocs migrate run       # Run all pending migrations
mydocs migrate list      # List available migration scripts
```

See [cli.md](cli.md) for CLI details.

---

## 5. Future Considerations

- **Migration tracking**: Record executed migrations in a `_migrations` collection to avoid re-running
- **Schema migrations**: Support data migrations (field renames, transformations) in addition to index migrations
- **Rollback support**: Add reverse migration scripts for undoing changes
- **Migration status**: `mydocs migrate status` command to show which migrations have been applied
- **Idempotency**: Make all migration scripts idempotent (check if index exists before creating)
