# Architecture

## Current state

Milestone 0 establishes the infrastructure. The application is intentionally almost empty so that each subsequent layer can be understood in isolation.

```text
Browser
  |
  | HTTP / JSON
  v
React + TypeScript + Rsbuild
  |
  | /api/v1 (development proxy)
  v
FastAPI
  |
  +-- app/api/v1/health.py
  |
  v
PostgreSQL + pgvector
```

## Runtime services

### `web`

- React 19 and TypeScript
- Rsbuild 2 (Rspack 2) for development, production build, and preview
- Tailwind CSS v4 through `@rsbuild/plugin-tailwindcss`
- TanStack Query for server state
- React Router for SPA routing
- Rstest + React Testing Library for component tests

The web container runs the Rsbuild dev server on port `5173`. The dev server proxies `/api` to `http://api:8000` inside Compose.

### `api`

- Python 3.12
- FastAPI and Pydantic v2
- Uvicorn for local serving
- Pydantic Settings for environment-based configuration
- Pytest + HTTPX for API tests
- Ruff for linting and formatting

The API exposes versioned routes under `/api/v1`. OpenAPI documentation is available at `/api/docs`.

### `db`

- PostgreSQL 16
- pgvector extension, enabled by `infra/postgres/init.sql` on first database initialization
- A named volume persists database data across container restarts

The database does not contain application tables yet. Alembic migrations begin in Milestone 1.

## Configuration

All backend settings use the `DOCUMIND_` prefix:

```text
DOCUMIND_ENVIRONMENT
DOCUMIND_CORS_ORIGINS
DOCUMIND_LOG_LEVEL
```

The frontend does not receive backend secrets. It only needs a relative API path, which Rsbuild proxies in development.

## Planned extension points

- `app/core/db.py` will own engine and session creation.
- `app/models/` will contain SQLAlchemy models.
- `app/repositories/` will contain focused query modules, not a generic repository framework.
- `app/services/` will contain PDF extraction, chunking, embedding, retrieval, and RAG workflows.
- `app/workers/` will contain the PostgreSQL-backed ingestion worker.
- `apps/web/src/features/` will contain document, research, and evaluation features.

## Architectural decisions

### Rsbuild instead of Vite

Rsbuild provides a React-ready application build tool on top of Rspack. It supplies the dev server, production build, HTML generation, TypeScript/JSX transforms, Tailwind integration, and proxy configuration. Bare Rspack would require reimplementing those defaults. Using Rsbuild also keeps development and production on the same bundler.

### Rstest instead of Vitest

Rstest reuses the Rsbuild configuration through `@rstest/adapter-rsbuild`, so aliases, plugins, and transforms stay consistent. It provides a Vitest-compatible test API and avoids a second build tool.

### Synchronous SQLAlchemy, planned

The MVP will use synchronous SQLAlchemy with Psycopg 3. FastAPI runs synchronous endpoints in a thread pool, which is adequate for a single-user local application and keeps transaction boundaries and tests simple. Async can be reconsidered when streaming or higher concurrency becomes a requirement.

### PostgreSQL for relational data and vectors, planned

Chunks, metadata, embeddings, conversations, and messages will live in one PostgreSQL database. pgvector avoids the operational overhead of a second vector database and allows vector search to participate in normal SQL filtering and transactions.

### A lightweight ingestion worker, planned

PDF extraction and embedding calls will run in a separate worker process that polls PostgreSQL. This avoids non-durable FastAPI background jobs without introducing Redis or Celery before they are justified.

## Security boundaries

- API keys exist only in backend environment variables.
- `.env` is gitignored; `.env.example` contains no secrets.
- The current single-user setup has no authentication.
- Ownership boundaries will be represented in the data model from Milestone 1 so authentication can be added later.
- Uploaded PDFs and extracted text must be treated as untrusted data.
