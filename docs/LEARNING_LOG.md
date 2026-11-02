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
