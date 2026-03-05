---
name: add-endpoint
description: Scaffold a new API endpoint with route, models, spec entry, openapi.yaml update, and frontend API client.
argument-hint: [endpoint description, e.g. "GET /api/v1/cases/{id}/summary"]
---

# Add Endpoint

You are scaffolding a new API endpoint end-to-end.

## Steps

1. Parse the endpoint description from: `$ARGUMENTS`
2. Read `docs/specs/backend.md` and `openapi.yaml` to understand existing patterns
3. Update the spec (`docs/specs/backend.md`) with the new endpoint definition
4. Create or update the route handler in the appropriate file under `mydocs/backend/routes/`
5. Add Pydantic request/response models if needed
6. Add the endpoint to `openapi.yaml`
7. Create the frontend API client method in `mydocs-ui/src/api/`
8. Update `docs/BACKEND.md` with the new endpoint

## Rules

- Follow existing route patterns: async handlers, Pydantic models, `/api/v1` prefix
- Group routes by domain in `mydocs/backend/routes/`
- Use snake_case for Python, camelCase for TypeScript
- Include proper error handling and status codes
