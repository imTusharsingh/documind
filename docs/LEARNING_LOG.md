# Learning log

## Milestone 0 — Architecture and setup

**Date:** 2026-11-02

### What was built

- Monorepo at `Desktop/documind`
- React + TypeScript frontend built with Rsbuild/Rspack
- Tailwind CSS v4 design tokens and a restrained system-status screen
- FastAPI backend with a versioned health endpoint
- Pydantic response model and environment-based settings
- PostgreSQL 16 container with pgvector enabled
- Docker Compose services with health checks and persistent volumes
- Rstest + React Testing Library setup
- Pytest, HTTPX, and Ruff setup

### Concepts learned

**Monorepo boundaries**

The frontend and backend are separate deployable applications inside one repository. Docker Compose defines how they communicate at runtime. The web container does not import backend code; it only makes HTTP requests.

**Docker Compose**

Compose creates a private network where services resolve each other by name. The web development proxy targets `http://api:8000`, not `localhost:8000`, because `localhost` inside a container refers to that container.

**Health checks**

A container can be running but not ready to serve traffic. Compose health checks use `pg_isready` for PostgreSQL, a Python HTTP request for FastAPI, and a Node `fetch` request for the Rsbuild dev server. `depends_on` with `condition: service_healthy` prevents startup from racing.

**FastAPI routing and dependencies**

`APIRouter` groups routes. `Depends(get_settings)` injects configuration. Using `Annotated[Settings, Depends(...)]` keeps function defaults clean and satisfies Ruff's rule against calls in default arguments.

**Pydantic Settings**

`BaseSettings` loads environment variables with the `DOCUMIND_` prefix. The settings object is cached per process with `lru_cache`, so repeated dependency resolution does not re-parse configuration.

**Rsbuild and Rspack**

Rspack is the Rust bundler; Rsbuild is the application build tool on top of it. Rsbuild supplies React, Tailwind, TypeScript, HTML, dev server, proxy, and history fallback configuration. It runs the same bundler in development and production.

**Rstest**

Rstest is Rsbuild-native and reuses `rsbuild.config.ts` through `@rstest/adapter-rsbuild`. React Testing Library still supplies rendering and queries. `jest-dom` matchers are registered with `expect.extend`, and the Rstest `Assertion` interface is augmented for TypeScript.

**Tailwind CSS v4**

Tailwind v4 uses CSS-first configuration. The `@theme inline` block maps CSS variables to utility names such as `bg-surface`, `text-muted`, and `border-border`. This keeps the design system centralized instead of scattering arbitrary colors through components.

**pgvector**

pgvector is a PostgreSQL extension that adds vector types and distance operators. The extension is enabled during database initialization here; vector columns and indexes arrive in Milestone 3.

### Execution flow

1. Docker Compose starts PostgreSQL and waits for its health check.
2. The API container installs FastAPI and starts Uvicorn.
3. The API health check succeeds.
4. The web container installs dependencies and starts Rsbuild.
5. The browser loads the React app.
6. TanStack Query requests `/api/v1/health`.
7. Rsbuild proxies the request to `http://api:8000/api/v1/health`.
8. FastAPI validates dependencies and returns the Pydantic health response.
9. The status card displays the API status.

### Verification performed

```bash
docker compose up --build -d
docker compose ps
curl http://localhost:8000/api/v1/health
curl http://localhost:5173/api/v1/health
curl -I http://localhost:5173/research
docker compose exec -T db psql -U documind -d documind \
  -Atc "SELECT extname || ' ' || extversion FROM pg_extension WHERE extname='vector';"
```

Observed results:

- `api`, `db`, and `web` containers reached healthy state.
- API health returned `status: ok`.
- The web proxy returned the same health response.
- `/research` returned `200 text/html`, confirming SPA fallback.
- pgvector reported version `0.8.3`.
- Rstest passed 2 tests.
- Pytest passed 2 tests.
- Ruff passed.
- TypeScript typecheck passed.
- Rsbuild production build completed.

### Common failure cases

- **Web cannot reach API:** check that `API_PROXY_TARGET=http://api:8000` inside Compose and that the API is healthy.
- **Database empty after restart:** named volumes persist data. Use `docker compose down -v` only when intentionally resetting local data.
- **CORS error:** the development proxy should make requests same-origin. If bypassing the proxy, add the browser origin to `DOCUMIND_CORS_ORIGINS`.
- **Port already in use:** change `API_PORT`, `WEB_PORT`, or `POSTGRES_PORT` in `.env`.
- **pgvector missing:** the init script only runs on a fresh PostgreSQL volume. Reset the volume or create the extension manually.

### Interview questions

1. Why is Rspack the bundler while Rsbuild is the application build tool? What does Rsbuild provide that bare Rspack does not?
2. Why does the frontend proxy `/api` during development instead of calling `http://localhost:8000` directly?
3. What is the difference between a container being “running” and being “healthy” in Docker Compose?
4. Why is `Depends(get_settings)` preferable to reading environment variables inside every route handler?
5. Why does Rstest still need `@testing-library/react` and `@testing-library/jest-dom` if it provides the test runner and assertions?
6. Why is it safer to keep the embedding provider behind an interface instead of calling it directly from route handlers?

### Next milestone

Milestone 1 adds SQLAlchemy, Psycopg 3, Alembic migrations, database connectivity in the health check, consistent error responses, and integration tests.

---

## Milestone 1 — Data foundation

**Date:** 2026-11-04

### What was built

- SQLAlchemy 2 engine, session factory, and request-scoped `get_session` dependency
- Psycopg 3 as the synchronous PostgreSQL driver
- `users` table with a deterministic seeded development owner
- Alembic environment plus migrations `0001` (schema) and `0002` (seed)
- Migrations run automatically before Uvicorn starts in Compose
- Split health model: liveness (`/health/live`) and readiness (`/health`)
- `GET /api/v1/me` returning the seeded owner
- One error envelope for `AppError`, validation errors, HTTP errors, and crashes
- Integration tests against a real `documind_test` PostgreSQL database
- Frontend displays database state, latency, and the owner record
- API client parses the error envelope and treats `503` readiness as data

### Concepts learned

**Engine, connection, session**

The engine is a process-wide factory that owns a connection pool. A connection is a TCP session to PostgreSQL. A SQLAlchemy `Session` is a unit-of-work and identity map that borrows a connection only when it needs one. Closing a session returns its connection to the pool; it does not close the TCP connection.

**Session lifecycle in a web request**

`get_session` yields a session, rolls back if the handler raises, and closes in `finally`. The rollback matters because an aborted transaction leaves the connection in a failed state; returning it to the pool without a rollback poisons the next request that borrows it.

**`pool_pre_ping`**

Connections can die while idle — a database restart, a proxy timeout, a network reset. Without a health check, the pool hands out a dead connection and the request fails. `pool_pre_ping` issues a lightweight check before use and transparently replaces broken connections. This is why readiness recovered after PostgreSQL restarted without restarting the API.

**Migrations versus `create_all`**

`Base.metadata.create_all()` can build tables, but it cannot express changes to existing tables, cannot run data migrations, and leaves no version history. Alembic records each applied revision in `alembic_version` and applies changes in order. Schema creation belongs to migrations from the first table, otherwise the first real schema change becomes a manual repair.

**Naming conventions**

Unnamed constraints get generated names. Those names can differ between environments and cannot be referenced reliably by later migrations. A `MetaData` naming convention makes `pk_users`, `uq_users_email`, and future foreign keys deterministic.

**Seed data in a migration**

The development owner is data the application depends on. Seeding it in `0002` means local and test databases start in the same state, the operation is versioned, and `ON CONFLICT (id) DO NOTHING` makes repeated startup idempotent. Seeding at application startup would be a side effect hidden in the web process.

**Fixed identifiers**

A constant UUID (`00000000-0000-0000-0000-000000000001`) lets tests and future seeded rows reference the owner without a lookup, and makes the seed's conflict target meaningful.

**A single error envelope**

Without handlers, FastAPI returns three different shapes: `{"detail": ...}` for HTTP errors, a list for validation errors, and plain text or nothing for crashes. Clients then parse messages. Registering handlers for `AppError`, `RequestValidationError`, `StarletteHTTPException`, and `Exception` gives one shape and one rule: branch on `error.code`, never on `error.message`.

**Liveness versus readiness**

Liveness answers "is this process able to serve?" and must not depend on the database, because restarting the process will not fix a down database. Readiness answers "can this instance serve real traffic?" and must check dependencies. Conflating them causes restart loops during database outages.

**Integration tests with real PostgreSQL**

SQLite would not exercise native UUIDs, timezone-aware timestamps, or the cast behaviour that broke the first seed migration. Testing on PostgreSQL caught a real defect: a text-bound UUID parameter was inferred as `VARCHAR` and rejected by the UUID column until it was cast explicitly.

**Transactional test isolation**

Each test runs inside an outer transaction on a dedicated connection, with the request session bound using `join_transaction_mode="create_savepoint"`. Rolling back the outer transaction removes all writes without truncating tables or rebuilding the schema. This is faster than recreating the database and still leaves tests independent.

**Dependency overrides**

`app.dependency_overrides[get_session]` swaps the session for a test-bound one. Because the override goes through the same dependency mechanism as production, the test exercises routing, dependency resolution, and serialization rather than calling functions directly.

### Execution flow

1. `docker compose up` starts PostgreSQL and waits for `pg_isready`.
2. The API container runs `alembic upgrade head` before Uvicorn.
3. Alembic reads `DATABASE_URL` from the same settings object the app uses.
4. `0001` creates `users`; `0002` inserts the development owner if absent.
5. Uvicorn starts; the Compose health check calls `/api/v1/health`.
6. Readiness borrows a pooled connection and runs `SELECT 1`.
7. The browser loads the app; TanStack Query requests health and owner data.
8. Rsbuild proxies both requests to the API container.
9. The readiness card shows database status and latency; the owner card shows the seeded row.

### Verification performed

```bash
cd services/api
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q

cd apps/web
pnpm typecheck
pnpm test
pnpm build

cd ../..
docker compose up --build -d
docker compose ps
curl -sS http://localhost:8000/api/v1/health
curl -sS http://localhost:8000/api/v1/health/live
curl -sS http://localhost:8000/api/v1/me
curl -sS http://localhost:8000/api/v1/nope
docker compose stop db
curl -sS -w '%{http_code}' http://localhost:8000/api/v1/health
docker compose start db
curl -sS http://localhost:8000/api/v1/health
```

Observed results:

- 14 backend tests passed, including migration assertions and the unhandled-exception leak check.
- 5 frontend tests passed; typecheck and production build succeeded.
- All three containers reached healthy state.
- Readiness returned `200` with `database.status = "up"` and measured latency.
- Liveness returned `200` with empty dependencies.
- `/api/v1/me` returned the seeded owner; the same response worked through the web proxy.
- Unknown route returned `404` in the error envelope.
- With PostgreSQL stopped, readiness returned `503` and `"status": "degraded"` while liveness stayed `200`.
- After PostgreSQL restarted, readiness returned to `200` without restarting the API.
- Rendered DOM contained `Database connected`, `Development Owner`, and the owner email.

### Common failure cases

- **`alembic upgrade head` cannot connect:** check `DATABASE_URL`, and note that `localhost` means the host when running on the host but the API container when running inside Compose.
- **Seed migration fails with a UUID type error:** parameters inferred as text must be cast, for example `CAST(:id AS uuid)`. This actually happened during development.
- **`DEVELOPMENT_OWNER_MISSING`:** the seed migration has not run, or the row was deleted. Run `alembic upgrade head`.
- **Readiness `503` but liveness `200`:** the database is unreachable or rejecting connections. The API itself is fine.
- **Tests hang on a stale connection:** ensure the test database is reachable and that `pool_pre_ping` is enabled for long-lived pools.
- **A test leaves data behind:** the session must be bound to the test connection with `join_transaction_mode="create_savepoint"`; otherwise commits escape the outer rollback.

### Interview questions

1. Why is `alembic_version` a table instead of a file on disk?
2. What is the difference between an engine, a connection, and a session in SQLAlchemy?
3. Why must `get_session` roll back on exception before closing?
4. How does `pool_pre_ping` prevent errors after a database restart, and what does it cost?
5. Why should liveness never check the database?
6. Why is seeding the owner in a migration better than seeding it in application startup?
7. Why do integration tests use PostgreSQL instead of SQLite here?
8. How does the savepoint-based test fixture isolate tests without truncating tables?
9. Why does the API return `details` for validation errors but hide exception text for `500`s?
10. What would change in the data model and repositories when authentication replaces the seeded owner?

### Next milestone

Milestone 2 adds PDF upload, durable file storage, page-aware extraction, chunking, and the PostgreSQL-backed ingestion queue with document status.

---

## Milestone 2 — Document ingestion

**Date:** 2026-11-04

### What was built

- `documents` and `document_chunks` tables with migration `0003`
- A status check constraint and a `(status, created_at)` index for worker claims
- Streaming PDF upload with extension, signature, and size validation
- Durable storage keyed by server-generated document id
- Page-aware text extraction with PyMuPDF
- Token chunking with `tiktoken` (`cl100k_base`, 350 tokens, 50 overlap)
- A separate PostgreSQL-backed ingestion worker using `FOR UPDATE SKIP LOCKED`
- Stale-claim recovery and idempotent chunk replacement
- `POST`, `GET`, `GET /{id}`, and `DELETE /documents` routes
- A documents page with upload, status badges, automatic polling, and delete
- Sidebar navigation and a documents entry point from the system page
- 41 backend tests and 15 frontend tests

### Concepts learned

**The table is the queue**

The MVP does not add Redis or Celery. A document row already has durable state, an owner, timestamps, and a natural lifecycle. Polling that table and using status transitions as the protocol means a worker restart loses nothing: pending work is still pending, and finished work is still finished. A broker becomes justified when fan-out, priorities, or scheduled retries cannot be expressed reasonably in SQL.

**`FOR UPDATE SKIP LOCKED`**

Two workers polling at the same time must not receive the same document. `SKIP LOCKED` tells PostgreSQL to ignore rows another transaction has locked instead of waiting on them. Combining it with a single `UPDATE ... RETURNING` makes claiming one atomic step. Without `SKIP LOCKED`, workers serialize behind each other; without the row lock, both can claim the same row.

**Commit the claim, then work**

The claim transaction commits before PDF extraction. Holding a row lock for seconds of parsing would block every other worker and keep a connection idle. The trade-off is that a crash can leave a row in `processing`, which is why the stale timestamp exists. A worker may reclaim a claim older than the threshold, and replays are safe.

**Idempotent retries**

A worker can die after writing some chunks but before marking the document ready. On retry, `replace_chunks` deletes all chunks for that document before inserting the new set. The unique constraint on `(document_id, chunk_index)` is a second line of defence. Retry safety is a property of the write sequence, not a hope.

**Streaming uploads**

Reading the entire upload into memory would let one large file exhaust the API. The handler writes chunks of 1 MB, counts bytes as they arrive, and rejects the upload while writing. The client's `Content-Length` header is not trusted because it can lie. The file is written as `.part` and renamed only on success, so a rejected upload never leaves a file that looks valid.

**Magic bytes versus extensions**

A `.pdf` extension proves nothing. The handler checks for `%PDF-` near the start of the file, then PyMuPDF validates whether the structure is readable. Both checks are needed: the signature rejects obvious mistakes cheaply, while parsing is the real test.

**Server-generated storage paths**

The stored filename is `{document_id}.pdf`, not the client filename. A name such as `../../passwd.pdf` becomes harmless because it never reaches the path. The original name is kept only as metadata for display.

**Page boundaries make citations possible**

Chunks never span pages. Page numbers are 1-based and stored on every chunk. This slightly reduces retrieval quality at boundaries but guarantees that a citation can name one page. Citation precision is a product requirement, so the constraint belongs in the chunker and in its tests.

**Token windows, not character windows**

`tiktoken` with `cl100k_base` measures the units the embedding model actually sees. A 350-token window with 50-token overlap advances 300 tokens per chunk, so adjacent chunks share 50 tokens of context. Token counts are stored rather than recomputed later. Character splitting would produce wildly uneven tokens and misleading counts.

**Expected failure versus crash**

A scanned PDF is an expected failure: the user can fix it, so the message is user-facing and stored on the document. An unexpected exception is a bug: the document gets a generic message and the worker log keeps the traceback. The API never returns internal exception text.

**Worker process topology**

The worker is a second process with its own engine and session factory. It shares the API image and the uploads volume but not memory. This is why the API cannot pass Python objects to the worker — the file path and document id in PostgreSQL are the only handoff. It also means the worker can be scaled or restarted independently.

**Polling in the UI**

TanStack Query polls only while at least one document is `pending` or `processing`. Once everything is terminal, `refetchInterval` returns `false` and polling stops. That avoids a permanent background request loop while keeping status fresh during work.

**Mutation-driven cache invalidation**

After upload or delete, the mutation invalidates the `['documents']` query instead of manually splicing the list. The next fetch is the source of truth, so the UI cannot drift from the server after a failed write.

### Execution flow

1. The browser submits `POST /api/v1/documents` with a multipart PDF.
2. FastAPI validates the filename, streams the file to the uploads volume, and checks the PDF signature and size.
3. The API inserts a `documents` row with status `pending` and returns `201`.
4. The documents page inserts the response into its TanStack Query cache and starts polling every 2 seconds.
5. The worker polls PostgreSQL, claims the row atomically, and commits it as `processing`.
6. The worker reads the stored path, extracts page text, and chunks each page.
7. It replaces any previous chunks and marks the document `ready` with page and chunk counts.
8. The next poll returns `ready`; the UI shows both counts and stops polling.
9. If extraction finds no text, the worker marks the document `failed` with an explicit message; the UI shows it in the row.

### Verification performed

```bash
cd services/api
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q

cd apps/web
pnpm typecheck
pnpm test
pnpm build

cd ../..
docker compose up --build -d
docker compose ps
curl -F 'file=@ingestion-sample.pdf;type=application/pdf' \
  http://localhost:5173/api/v1/documents
curl http://localhost:5173/api/v1/documents/<id>
docker compose exec -T db psql -U documind -d documind -c \
  "SELECT page_number, chunk_index, token_count, left(content, 60) FROM document_chunks ORDER BY chunk_index;"
curl -X DELETE http://localhost:5173/api/v1/documents/<id>
curl -F 'file=@notes.txt;type=text/plain' http://localhost:5173/api/v1/documents
```

Observed results:

- 41 backend tests and 15 frontend tests passed; typecheck and production build succeeded.
- `api`, `db`, `web`, and `worker` started; the API and web containers became healthy.
- A three-page PDF uploaded through the web proxy returned `201 pending`.
- Polling showed `processing`, then `ready` with `page_count = 3` and `chunk_count = 3`.
- Stored chunks had page numbers 1, 2, and 3, sequential indexes, and token counts of 26, 26, and 28.
- A text-free PDF became `failed` with "This PDF has no extractable text. Scanned PDFs are not supported."
- Deleting the failed document returned `204`, a follow-up `GET` returned `404`, and its file disappeared from the uploads volume.
- Uploading a `.txt` returned `415 UNSUPPORTED_MEDIA_TYPE`.
- The rendered documents page contained both filenames, two `Ready` badges, the upload form, and the library heading, with no browser console errors.
- Screenshot captured at `docs/screenshots/milestone-2.png`.

### Common failure cases

- **`RuntimeError: Form data requires "python-multipart"`:** the API image was built before the dependency was added. Rebuild with `docker compose up --build -d`.
- **Document stays `pending`:** the worker is not running or cannot reach PostgreSQL. Check `docker compose ps` and `docker compose logs worker`.
- **Document stays `processing` forever:** the worker crashed after claiming. It becomes reclaimable after `DOCUMIND_WORKER_STALE_AFTER_SECONDS` (default 300).
- **`413` on a file below the limit:** `MAX_UPLOAD_MB` is applied to bytes streamed, not to the reported size. Check the actual file size and the `.env` value.
- **`415` for a valid-looking PDF:** the first 1 KB must contain `%PDF-`, and PyMuPDF must be able to open the file. Some exporters produce unusual headers or encrypted files.
- **Worker cannot find the file:** the API and worker must mount the same `uploads` volume, and `UPLOAD_DIR` must match in both containers.
- **Failed chunks remain after a retry:** this should not happen because `replace_chunks` deletes first. If it does, check that the reclaim path and the claim use the same document id.
- **Alembic constraint name has a double prefix:** the project naming convention prefixes explicit names too. Use a bare name such as `name="document_status"` and expect `ck_documents_document_status` in the database. This happened during development.
- **`pymupdf 2.x` pulls heavy extras:** `pymupdf-layout` and `pymupdf4llm` bring ONNX runtime. The project pins `pymupdf>=1.28,<2` because only the base parser is needed.

### Interview questions

1. Why can the `documents` table act as a durable queue, and when would you replace it with a broker?
2. How does `FOR UPDATE SKIP LOCKED` prevent two workers from claiming the same row?
3. Why does the worker commit the claim before extraction instead of holding the lock for the whole job?
4. What happens if a worker crashes between writing chunks and marking the document ready, and why is a retry safe?
5. Why is a stale `processing` timestamp necessary if the claim is atomic?
6. Why stream an upload in chunks instead of reading it all into memory before checking the size?
7. Why is checking the `%PDF-` signature not enough to trust a file?
8. Why derive the storage path from the document id instead of sanitizing and using the client filename?
9. Why do chunks never cross page boundaries, and what retrieval quality trade-off does that make?
10. What does the 50-token overlap buy, and why must the overlap be smaller than the window?
11. Why store `token_count` instead of counting words or characters at read time?
12. Why does the worker record expected failures on the document while logging unexpected ones with a traceback?
13. How does TanStack Query stop polling once every document reaches a terminal state?
14. Why invalidate the documents query after a mutation instead of updating the cached list by hand?
15. What changes if two workers, then ten, run against the same table?

## Milestone 3 — Embeddings and semantic retrieval

**Date:** 2026-11-04

### What was built

- OpenAI embedding provider with batching, retries, dimension checks, and safe error messages
- Nullable 1536-dimensional vectors on `document_chunks` through migration `0004`
- HNSW cosine index for PostgreSQL-side nearest-neighbour search
- Ingestion now generates vectors before marking a document `ready`
- `POST /api/v1/search` with owner, readiness, document selection, result count, and similarity filtering
- Reprocessing endpoint for failed or ready documents
- Search UI that displays ranked passages with document and page provenance

### Concepts learned

Embedding generation is an external side effect, so it happens after the durable worker claim and before the final database commit. A provider failure marks the document failed instead of leaving a misleading `ready` state. The vector column is nullable for safe migration, while the application only marks documents ready after every chunk has a vector.

The database owns retrieval: cosine distance, owner filtering, readiness filtering, and ordering are one SQL statement. This keeps tenant boundaries enforceable in the query and lets PostgreSQL use the HNSW index as the collection grows.

The provider is hidden behind a small protocol. Tests inject a deterministic local implementation, so batching, persistence, filtering, and ranking are testable without network calls or API keys.

### Verification notes

Ruff checks pass. Backend integration tests require a reachable PostgreSQL instance, and the local environment did not provide one. Chunking tests also require the cached `cl100k_base` tokenizer data; this environment cannot download it because outbound DNS is unavailable. Frontend checks are configured but cannot run here because Node and pnpm are not installed.

### Interview questions

1. Why generate embeddings in the worker instead of inside the upload request?
2. Why must a document stay non-`ready` until every chunk has a vector?
3. Why is the embedding column nullable during the migration?
4. Why is the embedding dimension fixed in the database schema, and what must change if the model dimension changes?
5. What does cosine distance measure, and why is it converted to a similarity score for the API?
6. Why does the search query filter by owner and `ready` status inside SQL instead of filtering results in Python?
7. What is the purpose of the HNSW index, and what trade-off does it introduce?
8. Why does the provider wrapper batch inputs and validate response order and vector dimensions?
9. How does the application behave when `OPENAI_API_KEY` is missing during ingestion?
10. Why should provider errors be logged internally but not returned verbatim to users?
11. How does `POST /documents/{id}/reprocess` make a failed embedding job recoverable?
12. Why can old chunks remain temporarily when a ready document is requeued?
13. How would you test semantic search without calling an external embedding provider?
14. What happens to existing ready documents when migration `0004` is applied?
15. What would you measure to decide whether exact search, HNSW search, or a hybrid retrieval strategy is best?

### Next milestone

## Milestone 4 — Grounded answers and citations

**Date:** 2026-11-04

### What was built

- Conversation, message, and citation tables through migration `0005`
- OpenAI structured-output answer provider with a testable provider protocol
- `POST /api/v1/chat` with retrieval, recent conversation history, and explicit insufficient-evidence handling
- Citation validation that only accepts chunk ids retrieved for the current request
- Owner-scoped conversation list and detail endpoints
- Chat UI with source previews and page-level citations

### Concepts learned

Retrieval is the trust boundary for grounded answers. The model receives only passages selected by the database, and its citation ids are treated as untrusted output. The application maps those ids back to the retrieved set, discards invalid ids, and refuses to present a confident answer when no valid evidence remains.

Conversation persistence is separate from retrieval. A user message and assistant response are stored in one conversation, while citations are normalized into their own table so source metadata, usage, latency, and message history remain inspectable.

The provider is isolated behind a protocol, which makes the complete API flow testable with deterministic embeddings and answers. Production failures return stable dependency errors while detailed provider failures remain in logs.

### Interview questions

1. Why must model citations be validated against retrieved chunks?
2. How does the application prevent a model from citing a document it was not given?
3. Why return an explicit insufficient-evidence answer instead of an empty answer?
4. Why persist citations separately from assistant message text?
5. How are conversation ids scoped to the current owner?
6. Why include recent history in the prompt, and why cap its length?
7. What should happen if the answer provider returns valid JSON but only invalid citation ids?
8. How would you test citation validity without making an LLM request?
9. Why store token usage and latency with the assistant message?
10. How would streaming answers change the persistence and validation protocol?

### Next milestone

Milestone 5 will add retrieval evaluation and quality metrics.

