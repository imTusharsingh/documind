# Architecture

## Current state

Milestone 3 adds embeddings and semantic retrieval to document ingestion. The application accepts PDF uploads, stores them durably, extracts text page by page, splits it into token chunks, generates vectors, and searches ready passages through pgvector. The pipeline is deliberately explicit: no LangChain, no separate vector database, no hidden queue.

```text
Browser
  |
  | HTTP / JSON / multipart
  v
React + TypeScript + Rsbuild
  |
  | /api/v1 (development proxy)
  v
FastAPI
  |
  +-- app/api/v1/health.py       liveness and readiness
  +-- app/api/v1/me.py           seeded development owner
  +-- app/api/v1/documents.py    upload, list, get, delete
  |
  v
app/core/db.py
  |  engine -> pool -> Psycopg 3
  v
PostgreSQL 16 + pgvector
  +-- users
  +-- documents
  +-- document_chunks
  +-- alembic_version

Ingestion worker (separate process)
  |  claims pending rows, reads PDFs, writes chunks
  +--> PostgreSQL
  +--> shared uploads volume
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
- PyMuPDF for PDF extraction and `tiktoken` for chunking
- `python-multipart` for streaming multipart uploads
- Pytest + HTTPX for integration tests
- Ruff for linting and formatting

The API exposes versioned routes under `/api/v1`. OpenAPI documentation is available at `/api/docs`.

Uploads are streamed to disk in 1 MB chunks instead of being buffered in memory. The handler validates the filename extension, checks for the `%PDF-` signature, enforces the configured size limit while writing, and moves a `.part` file into place only after success. The document id determines the stored filename, which removes path traversal and same-name collisions.

### `worker`

- Python process running `python -m app.workers.ingest`
- Polls PostgreSQL for one claimable document at a time
- Extracts page text with PyMuPDF
- Splits pages into token windows with `tiktoken`
- Writes chunks and final status in one transaction

The worker shares the `uploads` Docker volume with the API, so it reads files by the path stored on the document row. It starts only after the API is healthy, which guarantees migrations have run.

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

`User` is still the only identity model. Ownership is modelled on documents even though there is no authentication: adding auth later becomes a change in which user a request resolves to, not a schema redesign.

`Document` holds the uploaded file metadata and ingestion state. Status is stored as `VARCHAR(20)` with an explicit check constraint rather than a native PostgreSQL enum, because adding a status later is a normal migration instead of an enum alteration. `page_count` and `chunk_count` are written in the same transaction that marks a document `ready`, so they never describe a partial ingest.

`DocumentChunk` holds one retrievable passage. `chunk_index` is unique per document, and `page_number` is always the page the text came from because chunking never crosses a page boundary.

### Migrations

Alembic reads the database URL from the same settings object the API uses, so there is exactly one source of truth per environment.

- `0001` creates `users`.
- `0002` seeds the fixed development owner with `ON CONFLICT (id) DO NOTHING`.
- `0003` creates `documents` and `document_chunks`, including the status check constraint and the `(status, created_at)` index used by the worker claim.
- `0004` adds the nullable 1536-dimensional `embedding` vector and HNSW cosine index, then requeues existing ready documents for embedding.

The seed lives in a migration rather than in application startup code because it is data the schema depends on, it must be idempotent, and it must apply identically to local and test databases. The owner id is a constant UUID so tests and future seeded data can reference it without a lookup.

Migrations run in the `api` container command before Uvicorn starts. If the migration fails, the container fails to start, which is the correct outcome — a running API against a half-migrated schema is worse than no API.

### Test database

Integration tests use PostgreSQL, not SQLite, because the schema uses native UUIDs, timezone-aware timestamps, and pgvector. The fixture:

1. Creates `documind_test` if absent, connecting to the `postgres` maintenance database.
2. Runs `alembic upgrade head` once per session.
3. Opens a connection and an outer transaction per test.
4. Binds the request session to that connection with `join_transaction_mode="create_savepoint"`.
5. Rolls the outer transaction back after the test.

This gives each test a clean, migrated database without truncating tables or recreating the schema.

## Ingestion pipeline

### Queue protocol

The `documents` table is the queue; there is no broker. The protocol is the set of status transitions:

```text
upload -> pending -> processing -> ready
                              \-> failed
```

A worker claims work with a single `UPDATE` whose candidate subquery uses `FOR UPDATE SKIP LOCKED`:

1. Select one `pending` row, or one `processing` row older than the stale threshold, ordered by creation time.
2. Skip rows another worker has locked.
3. Update the chosen row to `processing`, record `processing_started_at`, and clear previous counts and errors.
4. Commit the claim before extraction.

Committing before extraction is deliberate. Holding the row lock for the duration of PDF parsing and embedding would serialize every worker behind the slowest file. `SKIP LOCKED` lets workers poll concurrently without blocking or duplicating work.

If a worker crashes after claiming, the row remains `processing`. Once `processing_started_at` is older than `worker_stale_after_seconds` (default 300), another worker can reclaim it. `replace_chunks` deletes existing chunks before inserting, so a reclaim never produces duplicates.

### Extraction

PyMuPDF opens the stored file and returns one `ExtractedPage` per page. Page numbers are 1-based because they are shown to users and stored in citations. A page with no text still counts toward `page_count`, but contributes no chunks.

If the document has pages and none contain extractable text, extraction raises `ScannedPdfError`. The worker records `failed` with an explicit message — "Scanned PDFs are not supported" — instead of silently marking an empty document ready.

### Chunking

Chunks use the `cl100k_base` tokenizer with a 350-token window and 50-token overlap, so each window advances by 300 tokens. Overlap preserves context across boundaries. The window never spans two pages, which guarantees that every chunk can be cited to exactly one page. `token_count` records the real tokenizer output, not an approximation from characters.

Chunk indexes are sequential across the whole document, not per page, which keeps citations and retrieval ordering simple.

### Failure handling

Expected extraction failures roll back the chunk transaction and mark the document `failed` with a user-facing message. Unexpected failures do the same with a generic message, while the worker log keeps the traceback. The API never exposes that traceback.

## Error handling

`app/core/errors.py` registers four handlers:

- `AppError` — expected domain failures with a stable code and status.
- `RequestValidationError` — normalized `422` with field details.
- `StarletteHTTPException` — unknown routes and wrong methods become `404` / `405` in the same envelope.
- `Exception` — logs the traceback and returns a generic `500`.

The envelope is `{"error": {"code", "message", "details"}}`. Two rules matter:

1. Clients branch on `code`, so messages stay human-readable but not machine-load-bearing.
2. Internal exception text is never returned. The unhandled-error test asserts that a raised secret string does not appear in the response.

Upload failures use `AppError` subclasses so they keep the same envelope: `PayloadTooLargeError` returns `413 PAYLOAD_TOO_LARGE`, and `UnsupportedMediaTypeError` returns `415 UNSUPPORTED_MEDIA_TYPE`.

## Health model

Liveness and readiness answer different questions.

- `/api/v1/health/live` proves the process can serve requests. It checks nothing. Restarting a container fixes a failed liveness probe.
- `/api/v1/health` proves the API can talk to PostgreSQL. It returns `503` when it cannot. Restarting the API does not fix a failed readiness probe, so these are not the same signal.

Verified behaviour: with PostgreSQL stopped, readiness returns `503` with `"status": "degraded"` and liveness still returns `200`. After PostgreSQL restarts, readiness recovers without restarting the API because of `pool_pre_ping`.

## Planned extension points

- `app/models/` gains embeddings, conversations, and messages.
- `app/repositories/` continues to grow focused query modules rather than a generic repository framework.
- `app/services/` gains embeddings, retrieval, and RAG workflows alongside storage, extraction, chunking, and ingestion.
- `app/workers/` may gain an embedding pass, or ingestion may extend its current transaction once embeddings exist.
- `apps/web/src/` gains research and evaluation pages on top of the current routing and API-client pattern.

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

PDF extraction and chunking run in a separate worker process that polls PostgreSQL. Keeping work out of the request means an upload returns quickly and a crash does not lose the job: the document row retains its status. This avoids non-durable FastAPI background jobs without introducing Redis or Celery before they are justified. The same protocol can later run as a second replica or move to a dedicated queue if throughput demands it.

### Page-boundary chunking

Chunks never span pages. Cross-page windows can improve retrieval slightly by avoiding truncated sentences, but they make citations ambiguous and complicate validation. Precise page citations are a product requirement here, so the boundary is enforced in the chunker and tested explicitly.

## Security boundaries

- API keys exist only in backend environment variables.
- `.env` is gitignored; `.env.example` contains no secrets.
- The current single-user setup has no authentication.
- Ownership is represented in the data model so authentication can be added without a redesign.
- Uploaded PDFs and extracted text must be treated as untrusted data.
- Uploads are validated by extension, PDF signature, and size; filenames are reduced to a bare name and storage paths are derived from server-generated ids.
- Stored files are removed when a document is deleted or when the database insert fails after a successful write.
- Error responses expose stable codes, never internal exception text.
