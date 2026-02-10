# MyDocs

AI-powered document management and intelligent search system. Ingest, parse, and extract structured information from documents, then search across them using full-text, vector (semantic), or hybrid search.

## Features

- **Document ingestion** — Upload or ingest files from the local filesystem (PDF, DOCX, XLSX, PPTX, JPEG, PNG, BMP, TIFF, TXT)
- **AI-powered parsing** — Extract paragraphs, tables, key-value pairs, images, and barcodes using Azure Document Intelligence
- **Semantic search** — Vector search powered by Azure OpenAI embeddings (`text-embedding-3-large`)
- **Full-text search** — Traditional keyword search via MongoDB Atlas Search
- **Hybrid search** — Combine full-text and vector results using Reciprocal Rank Fusion (RRF) or weighted sum
- **Tag management** — Organize documents with custom tags
- **Web UI** — Vue 3 single-page application for browsing, searching, and viewing documents
- **CLI** — Full-featured command-line interface for all operations
- **REST API** — FastAPI backend with OpenAPI documentation

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│   Vue 3 UI   │────>│  Nginx (port 80) │────>│  FastAPI (port 8000) │
│  (Tailwind)  │     │  reverse proxy   │     │  REST API backend    │
└──────────────┘     └──────────────────┘     └──────┬───────────────┘
                                                     │
                            ┌────────────────────────┼────────────────────────┐
                            │                        │                        │
                   ┌────────▼────────┐   ┌───────────▼──────────┐   ┌────────▼─────────┐
                   │    MongoDB      │   │  Azure Document      │   │  Azure OpenAI    │
                   │  Atlas Search   │   │  Intelligence        │   │  Embeddings      │
                   │  + Vector Index │   │  (document parsing)  │   │  (text-emb-3-lg) │
                   └─────────────────┘   └──────────────────────┘   └──────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, Pydantic, Uvicorn |
| Frontend | Vue 3, TypeScript 5.7, Tailwind CSS 4, Vite 6 |
| Database | MongoDB Atlas (documents, vector index, full-text index) |
| Document Parsing | Azure Document Intelligence (`prebuilt-layout`) |
| Embeddings | Azure OpenAI (`text-embedding-3-large`, 3072 dims) via LiteLLM |
| State Management | Pinia (with persisted state) |
| PDF Rendering | pdfjs-dist |
| Deployment | Docker, Docker Compose, Nginx |

## Prerequisites

- **Python** >= 3.13
- **Node.js** >= 22
- **MongoDB Atlas** cluster with Atlas Search and Vector Search enabled
- **Azure Document Intelligence** resource
- **Azure OpenAI** resource with `text-embedding-3-large` deployment
- **Docker & Docker Compose** (for containerized deployment)

## Getting Started

### 1. Clone the repository

```bash
git clone <repo-url>
cd mydocs2
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# MongoDB
MONGO_URL=mongodb+srv://cluster.mongodb.net
MONGO_USER=myuser
MONGO_PASSWORD=mypassword
MONGO_DB_NAME=mydocs

# Azure Document Intelligence
AZURE_DI_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_DI_API_KEY=your-api-key

# Azure OpenAI (used by LiteLLM for embeddings)
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_API_BASE=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Optional
DATA_FOLDER=./data
CONFIG_ROOT=./config
SERVICE_NAME=mydocs
LOG_LEVEL=INFO
```

### 3. Run with Docker Compose

```bash
# Build and start all services (foreground)
docker compose up --build

# Or start in detached (background) mode
docker compose up --build -d
```

This starts:
- **Backend** at `http://localhost:8000` (API + health check)
- **UI** at `http://localhost` (serves frontend, proxies `/api/` to backend)

### Stop services

```bash
# Stop running containers (preserves volumes and images)
docker compose down
```

### Cleanup

```bash
# Stop containers and remove volumes
docker compose down -v

# Stop containers, remove volumes and built images
docker compose down -v --rmi local
```

### 4. Run database migrations

```bash
mydocs migrate run
```

## Local Development

### Backend

```bash
# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Run the development server
uvicorn mydocs.backend.app:create_app --factory --reload --port 8000
```

### Frontend

```bash
cd mydocs-ui
npm install
npm run dev
```

The Vite dev server starts at `http://localhost:5173` with API proxying configured.

### Build frontend for production

```bash
cd mydocs-ui
npm run build
```

Output goes to `mydocs-ui/dist/`.

## CLI Usage

The `mydocs` CLI is installed as a console script with the Python package.

### Document Management

```bash
# List all documents
mydocs docs list

# List documents filtered by status and tags
mydocs docs list --status parsed --tags invoice,receipt

# Show document details
mydocs docs show <document_id>

# View document pages
mydocs docs pages <document_id>
mydocs docs pages <document_id> --page 1

# Add tags to a document
mydocs docs tag <document_id> tag1,tag2

# Remove a tag
mydocs docs tag <document_id> old-tag --remove

# Delete a document
mydocs docs delete <document_id> --force
```

### File Ingestion

```bash
# Ingest files from a local directory (recursive by default)
mydocs ingest /path/to/documents --tags batch1

# Ingest in external mode (reference files without copying)
mydocs ingest /path/to/documents --mode external

# Non-recursive ingestion
mydocs ingest /path/to/documents --no-recursive
```

### Parsing

```bash
# Parse a single document
mydocs parse <document_id>

# Batch parse by filter
mydocs parse --batch --status new
mydocs parse --batch --tags invoice
```

### Search

```bash
# Hybrid search (default)
mydocs search "quarterly revenue report"

# Vector (semantic) search
mydocs search "financial summary" --mode vector

# Full-text search
mydocs search "invoice 2024" --mode fulltext

# Search with filters
mydocs search "contract terms" --target pages --top-k 20 --tags legal

# Output as JSON
mydocs search "budget" -o json
```

### Configuration

```bash
# Show current parser configuration
mydocs config show

# Validate configuration
mydocs config validate

# Show environment variables (secrets redacted)
mydocs config env
```

### Migrations

```bash
# Run pending migrations
mydocs migrate run

# List available migrations
mydocs migrate list
```

### Global Options

```bash
mydocs -v ...              # Enable verbose (DEBUG) logging
mydocs --config-root ...   # Override config directory
mydocs --data-folder ...   # Override data directory
mydocs --env-file ...      # Load specific .env file
```

## API Reference

Base URL: `/api/v1`

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/documents` | List documents (paginated, filterable, sortable) |
| `GET` | `/documents/{id}` | Get document by ID |
| `GET` | `/documents/{id}/file` | Download document file |
| `GET` | `/documents/{id}/pages` | List document pages |
| `GET` | `/documents/{id}/pages/{page_number}` | Get specific page |
| `POST` | `/documents/upload` | Upload files (multipart form) |
| `POST` | `/documents/ingest` | Ingest from local filesystem |
| `POST` | `/documents/parse` | Batch parse documents |
| `POST` | `/documents/{id}/parse` | Parse single document |
| `POST` | `/documents/{id}/tags` | Add tags |
| `DELETE` | `/documents/{id}/tags/{tag}` | Remove tag |
| `DELETE` | `/documents/{id}` | Delete document |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/search/` | Execute search (full-text, vector, or hybrid) |
| `GET` | `/search/indices` | List available search indices |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |

Interactive API docs are available at `http://localhost:8000/docs` (Swagger UI) when the backend is running.

## Search Modes

### Full-Text Search
Uses MongoDB Atlas `$search` with fuzzy matching. Searches across document content, tags, status, and document type.

### Vector Search
Generates a query embedding via Azure OpenAI (`text-embedding-3-large`) and performs a `$vectorSearch` against stored page/document embeddings using dot product similarity.

### Hybrid Search
Runs both full-text and vector searches, then combines results using one of:
- **Reciprocal Rank Fusion (RRF)** — Merges rankings with configurable k parameter (default: 60)
- **Weighted Sum** — Normalizes scores via min-max and applies configurable weights (default: 0.5 / 0.5)

## Project Structure

```
mydocs2/
├── mydocs/                     # Python package
│   ├── backend/                # FastAPI application
│   │   ├── app.py              #   App factory
│   │   ├── dependencies.py     #   Request/response models
│   │   └── routes/             #   API route handlers
│   ├── cli/                    # Command-line interface
│   │   ├── main.py             #   Entry point & arg parser
│   │   ├── formatters.py       #   Output formatting
│   │   └── commands/           #   Subcommands (docs, parse, search, ingest, config, migrate)
│   ├── parsing/                # Document parsing pipeline
│   │   ├── models.py           #   Document/Page/Element models
│   │   ├── pipeline.py         #   Parsing orchestration
│   │   ├── azure_di/           #   Azure Document Intelligence parser
│   │   └── storage/            #   Storage backends (local, extensible)
│   ├── retrieval/              # Search & retrieval engine
│   │   ├── search.py           #   Search orchestrator
│   │   ├── vector_retriever.py #   Vector search implementation
│   │   ├── fulltext_retriever.py # Full-text search implementation
│   │   ├── hybrid.py           #   Result combination (RRF, weighted)
│   │   └── embeddings.py       #   Embedding generation
│   ├── common/                 # Shared utilities
│   └── config.py               # Global configuration
│
├── mydocs-ui/                  # Vue 3 frontend
│   └── src/
│       ├── views/              #   Page components
│       ├── components/         #   Reusable UI components
│       ├── stores/             #   Pinia state stores
│       ├── api/                #   Axios API client layer
│       ├── composables/        #   Vue composition functions
│       └── types/              #   TypeScript types
│
├── deploy/                     # Deployment configs
│   └── nginx.conf              #   Nginx reverse proxy
├── docs/specs/                 # Design specifications
├── config/                     # Parser configuration (YAML)
├── data/                       # Local document storage
├── migrations/                 # Database migration scripts
│
├── pyproject.toml              # Python project config
├── docker-compose.yml          # Docker Compose services
├── Dockerfile.backend          # Backend container (Python 3.13-slim)
├── Dockerfile.ui               # Frontend container (Node 22 + Nginx 1.27)
└── .env.example                # Environment variable template
```

## Docker

### Backend image

Multi-stage build: Python 3.13-slim builder installs dependencies, runtime image copies only what's needed. Exposes port 8000 and runs Uvicorn.

### UI image

Multi-stage build: Node 22-alpine builds the Vue app with Vite, then copies the static output to an Nginx 1.27-alpine image. Nginx serves the SPA and reverse-proxies `/api/` requests to the backend. Supports up to 100MB file uploads.

### Compose services

```yaml
services:
  backend:   # port 8000, health-checked, mounts data/ and config/
  ui:        # port 80, depends on healthy backend
```

## Author

Andrey Vykhodtsev
