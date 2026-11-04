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

