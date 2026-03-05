# MyDocs - AI Document Management System

## Project Overview
Full-stack document management system: Python/FastAPI backend, Vue 3/TypeScript frontend, MongoDB, Azure AI services.

## Read-First Rules
Before ANY work, read the relevant docs based on your task:

| Task Area | Read First | Spec | Notes |
|---|---|---|---|
| Backend / API | `docs/BACKEND.md` | `docs/specs/backend.md` | |
| Frontend / UI | `docs/UI.md` | `docs/specs/UI.md` | |
| Document Parsing | — | `docs/specs/parsing-engine.md` | No doc yet — spec only |
| Search & Retrieval | — | `docs/specs/retrieval-engine.md` | No doc yet — spec only |
| Extraction Engine | `docs/EXTRACTING.md` | `docs/specs/extracting-engine.md` | |
| CLI | `docs/CLI.md` | `docs/specs/cli.md` | |
| Infrastructure | `docs/INFRA_DEPLOYMENT.md` | `docs/specs/infrastructure.md` | |
| Sync Engine | — | `docs/specs/sync.md` | No doc yet — spec only |
| DB Migrations | — | `docs/specs/migrations.md` | No doc yet — spec only |
| API Contract | `openapi.yaml` | — | |

## Change Protocol
1. **Before coding**: Read relevant spec(s) from the table above. Update the spec with your planned changes.
2. **Implement**: Make code changes following the spec.
3. **After coding**: Update the corresponding `docs/` documentation to reflect what changed.
4. **API changes**: Update `openapi.yaml` when adding/modifying endpoints.

## Tech Stack Quick Ref
- **Backend**: Python 3.13, FastAPI, Pydantic v2, LiteLLM, LangGraph, lightodm (MongoDB)
- **Frontend**: Vue 3.5, TypeScript, Vite 6, Tailwind CSS 4, Pinia, Axios
- **Infra**: Docker, Kubernetes, Nginx, Azure (Doc Intelligence, OpenAI, Blob Storage, Entra ID)
- **Package mgmt**: `uv` (Python), `npm` (frontend)

## Commands
- **Backend**: `uv run uvicorn mydocs.backend.app:app --reload`
- **Frontend**: `cd mydocs-ui && npm run dev`
- **Tests**: `uv run pytest tests/`
- **Lint frontend**: `cd mydocs-ui && npm run lint`

## Agents

Use specialized agents for parallel, scoped work:

- **spec-reviewer**: Before implementation, reads relevant specs and proposes updates. Use for any feature or refactor.
- **doc-updater**: After implementation, updates all affected documentation files and openapi.yaml.
- **backend-dev**: Works on Python backend code (FastAPI routes, services, models). Reads `docs/specs/backend.md` first.
- **frontend-dev**: Works on Vue/TypeScript frontend code. Reads `docs/specs/UI.md` first.
- **test-runner**: Runs `uv run pytest tests/` and `cd mydocs-ui && npm run lint` after changes, reports results.
- **cli-tester**: After implementation, runs relevant `uv run mydocs` CLI commands end-to-end to validate changes work.

## Skills

- **/update-specs**: Interactively walk through all specs affected by a planned change and update them.
- **/sync-docs**: After implementation, scan changed files and update corresponding documentation.
- **/add-endpoint**: Scaffold a new API endpoint: route, models, spec entry, openapi.yaml update, and frontend API client.
- **/add-extractor**: Scaffold a new extraction schema under `mydocs/extracting/schemas/` with config YAML.
- **/cli**: Run a `mydocs` CLI command. Usage: `/cli <command> [args]` → executes `uv run mydocs <command> [args]`.
