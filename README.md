# DocuMind

DocuMind is an AI-powered document research assistant. This repository is being built incrementally as a learning project covering FastAPI, PostgreSQL, pgvector, RAG, Docker, and production-quality frontend engineering.

**Current status:** Milestone 1 complete — data foundation.

![DocuMind Milestone 1](docs/screenshots/milestone-1.png)

## What works today

- React + TypeScript frontend built with **Rsbuild/Rspack**
- Tailwind CSS v4 design tokens
- TanStack Query reads live API and database state
- FastAPI application with liveness and readiness endpoints
- SQLAlchemy 2 models, synchronous sessions, and Psycopg 3
- **Alembic** migrations, applied automatically when the API container starts
- PostgreSQL 16 with the **pgvector 0.8.3** extension enabled
- A single seeded development owner, read through `GET /api/v1/me`
- One consistent error envelope for every API failure
- Docker Compose for the web app, API, and database, with health checks
- **Rstest** + React Testing Library component tests
- Pytest integration tests against a real PostgreSQL database
- Ruff and TypeScript checks

Document upload, retrieval, and RAG are intentionally not implemented yet.

## Architecture

```text
Browser
  |
  | HTTP
  v
React + Rsbuild + Tailwind
  |
  | /api/v1 (proxied by the Rsbuild dev server)
  v
FastAPI
  |
  +-- /api/v1/health        readiness, checks PostgreSQL
  +-- /api/v1/health/live   liveness, checks nothing
  +-- /api/v1/me            seeded development owner
  |
  v
SQLAlchemy 2 (synchronous) + Psycopg 3
  |
  v
PostgreSQL 16 + pgvector
  +-- users
  +-- alembic_version
```

The browser calls relative `/api/v1/*` URLs. In development, Rsbuild proxies those requests to the API container. This avoids exposing API keys to the frontend and keeps the browser origin consistent.

## Quick start

Requirements:

- Docker with Compose
- An OpenAI API key is only needed from Milestone 3 onward

```bash
cd /home/tracxn-lp-784/Desktop/documind
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Open:

- Web application: <http://localhost:5173>
- API readiness: <http://localhost:8000/api/v1/health>
- API docs: <http://localhost:8000/api/docs>

Expected readiness response:

```json
{
  "status": "ok",
  "service": "DocuMind API",
  "version": "0.1.0",
  "environment": "development",
  "dependencies": {
    "database": { "status": "up", "latency_ms": 1.8, "error": null }
  }
}
```

Migrations run before Uvicorn starts, so a fresh volume is provisioned automatically. When PostgreSQL is unreachable the readiness endpoint returns `503` with `"status": "degraded"`, while the liveness endpoint keeps returning `200`.

## Local development without Docker

### API

```bash
cd services/api
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000
```

`alembic upgrade head` needs a reachable PostgreSQL. The default URL targets `localhost:5432/documind`; override it with `DATABASE_URL`.

### Web

```bash
cd apps/web
pnpm install
pnpm dev
```

The Rsbuild proxy targets `http://localhost:8000` unless `API_PROXY_TARGET` is set.

## Tests and checks

### Backend

```bash
cd services/api
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
```

Integration tests create and migrate a separate `documind_test` database, then wrap each test in a transaction that is rolled back. PostgreSQL must be reachable; set `DOCUMIND_TEST_DATABASE_URL` to point somewhere else.

### Frontend

```bash
cd apps/web
pnpm typecheck
pnpm test
pnpm build
```

## Repository layout

```text
documind/
  apps/web/                React application
    src/app/               Router, providers, system status page
    src/components/        Shared UI components
    src/lib/               API client and utilities
    src/styles/            Tailwind entry point and design tokens
    tests/                 Rstest setup, component and client tests
  services/api/            FastAPI application
    app/api/v1/            Versioned routes
    app/core/              Settings, database engine, error handling
    app/models/            SQLAlchemy models
    app/repositories/      Focused query functions
    app/schemas/           Pydantic request and response models
    migrations/            Alembic environment and versions
    tests/                 API and migration tests
  infra/postgres/          PostgreSQL initialization
  docs/                    Architecture, API, RAG, and learning notes
  docker-compose.yml       Local development services
```

## Current boundaries

- Single local user; authentication is not implemented.
- One document owner, seeded by migration `0002`.
- No PDF upload, chunking, embedding, retrieval, or chat.
- No vector columns or indexes yet; pgvector is installed and ready.
- Scanned PDFs will not be supported in the MVP unless OCR is explicitly added later.
- No secrets are present in the frontend. The OpenAI key belongs in the backend `.env` only.

## Next milestone

Milestone 2 will add PDF upload, durable storage, page-aware text extraction, chunking, and the ingestion queue with visible document status.
