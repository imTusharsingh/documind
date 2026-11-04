# Architecture

## Current state

Milestone 1 completes the data foundation. The application has no product features yet, but it has a real database, real migrations, and a real identity for future ownership checks.

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
  +-- app/api/v1/health.py       liveness and readiness
  +-- app/api/v1/me.py           seeded development owner
  |
  v
app/core/db.py
  |  engine -> pool -> Psycopg 3
  v
PostgreSQL 16 + pgvector
  +-- users
  +-- alembic_version
```

## Runtime services

### `web`

- React 19 and TypeScript
- Rsbuild 2 (Rspack 2) for development, production build, and preview
- Tailwind CSS v4 through `@rsbuild/plugin-tailwindcss`
- TanStack Query for server state
- React Router for SPA routing
- Rstest + React Testing Library for component and API-client tests

The web container runs the Rsbuild dev server on port `5173`. The dev server proxies `/api` to `http://api:8000` inside Compose.

The client parses the shared error envelope into an `ApiError` carrying `status` and `code`. A `503` from the readiness endpoint is treated as a valid payload rather than a failure, because "degraded" is information the UI must display.

### `api`

- Python 3.12
- FastAPI and Pydantic v2
- SQLAlchemy 2 with synchronous sessions on Psycopg 3
- Alembic migrations, run before Uvicorn starts
- Pydantic Settings for environment-based configuration
- Pytest + HTTPX for integration tests
- Ruff for linting and formatting

The API exposes versioned routes under `/api/v1`. OpenAPI documentation is available at `/api/docs`.

### `db`

- PostgreSQL 16
- pgvector extension, enabled by `infra/postgres/init.sql` on first database initialization
- A named volume persists database data across container restarts
- Application tables are owned by Alembic, not created at application startup

## Data layer

### Engine and sessions

`app/core/db.py` creates one engine per process and one `sessionmaker`. The engine uses `pool_pre_ping=True`, so a connection that died while idle is discarded and replaced instead of surfacing a stale-connection error to a request. `connect_timeout` is bounded so readiness fails quickly rather than hanging.

`get_session` is a FastAPI dependency that yields a session, rolls back if an exception escapes the request, and always closes the session. Closing returns the connection to the pool; it does not close the physical connection.

Repositories decide transaction boundaries explicitly. Route handlers do not commit implicitly, which keeps read paths cheap and makes write paths intentional as they are added.

### Models

`app/models/base.py` defines a `MetaData` naming convention for indexes, unique constraints, checks, foreign keys, and primary keys. Without it, PostgreSQL would invent constraint names and future migrations could not reliably drop or alter them.

`User` is the only model. Ownership is modelled now even though there is no authentication: adding auth later becomes a change in which user a request resolves to, not a schema redesign.

### Migrations

Alembic reads the database URL from the same settings object the API uses, so there is exactly one source of truth per environment.

- `0001` creates `users`.
- `0002` seeds the fixed development owner with `ON CONFLICT (id) DO NOTHING`.

The seed lives in a migration rather than in application startup code because it is data the schema depends on, it must be idempotent, and it must apply identically to local and test databases. The owner id is a constant UUID so tests and future seeded data can reference it without a lookup.

Migrations run in the `api` container command before Uvicorn starts. If the migration fails, the container fails to start, which is the correct outcome — a running API against a half-migrated schema is worse than no API.

### Test database

Integration tests use PostgreSQL, not SQLite, because the schema uses native UUIDs, timezone-aware timestamps, and shortly pgvector. The fixture:

1. Creates `documind_test` if absent, connecting to the `postgres` maintenance database.
2. Runs `alembic upgrade head` once per session.
3. Opens a connection and an outer transaction per test.
4. Binds the request session to that connection with `join_transaction_mode="create_savepoint"`.
5. Rolls the outer transaction back after the test.

This gives each test a clean, migrated database without truncating tables or recreating the schema.

## Error handling

`app/core/errors.py` registers four handlers:

- `AppError` — expected domain failures with a stable code and status.
- `RequestValidationError` — normalized `422` with field details.
- `StarletteHTTPException` — unknown routes and wrong methods become `404` / `405` in the same envelope.
- `Exception` — logs the traceback and returns a generic `500`.

The envelope is `{"error": {"code", "message", "details"}}`. Two rules matter:

1. Clients branch on `code`, so messages stay human-readable but not machine-load-bearing.
2. Internal exception text is never returned. The unhandled-error test asserts that a raised secret string does not appear in the response.

## Health model

Liveness and readiness answer different questions.

- `/api/v1/health/live` proves the process can serve requests. It checks nothing. Restarting a container fixes a failed liveness probe.
- `/api/v1/health` proves the API can talk to PostgreSQL. It returns `503` when it cannot. Restarting the API does not fix a failed readiness probe, so these are not the same signal.

Verified behaviour: with PostgreSQL stopped, readiness returns `503` with `"status": "degraded"` and liveness still returns `200`. After PostgreSQL restarts, readiness recovers without restarting the API because of `pool_pre_ping`.

## Planned extension points

- `app/models/` gains documents, chunks, conversations, and messages.
- `app/repositories/` grows focused query modules rather than a generic repository framework.
- `app/services/` will hold PDF extraction, chunking, embedding, retrieval, and RAG workflows.
- `app/workers/` will hold the PostgreSQL-backed ingestion worker.
- `apps/web/src/features/` will hold document, research, and evaluation features.

## Architectural decisions

### Rsbuild instead of Vite

Rsbuild provides a React-ready application build tool on top of Rspack. It supplies the dev server, production build, HTML generation, TypeScript/JSX transforms, Tailwind integration, and proxy configuration. Bare Rspack would require reimplementing those defaults. Using Rsbuild also keeps development and production on the same bundler.

### Rstest instead of Vitest

Rstest reuses the Rsbuild configuration through `@rstest/adapter-rsbuild`, so aliases, plugins, and transforms stay consistent. It provides a Vitest-compatible test API and avoids a second build tool.

### Synchronous SQLAlchemy

FastAPI runs synchronous endpoints in a thread pool. For a single-user local application this keeps transaction boundaries, debugging, and tests simpler than async sessions. Async becomes worth its complexity when streaming or meaningful concurrency arrives.

### PostgreSQL for relational data and vectors

Chunks, metadata, embeddings, conversations, and messages will live in one PostgreSQL database. pgvector avoids a second datastore and lets vector search participate in normal SQL filtering and transactions.

### A lightweight ingestion worker

PDF extraction and embedding calls will run in a separate worker process that polls PostgreSQL. This avoids non-durable FastAPI background jobs without introducing Redis or Celery before they are justified.

## Security boundaries

- API keys exist only in backend environment variables.
- `.env` is gitignored; `.env.example` contains no secrets.
- The current single-user setup has no authentication.
- Ownership is represented in the data model so authentication can be added without a redesign.
- Uploaded PDFs and extracted text must be treated as untrusted data.
- Error responses expose stable codes, never internal exception text.
