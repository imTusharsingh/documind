# DocuMind interview guide

This is the quick-reference version of the interview questions in the learning log. The answers are intentionally short; the linked implementation and learning-log sections provide the deeper explanation.

## Milestone 0 — Architecture and setup

- Why separate the React frontend and FastAPI backend into deployable applications?
- Why does the browser call relative `/api/v1` URLs through the web proxy?
- What is the difference between a liveness check and a readiness check?
- Why are Compose health checks and `depends_on` conditions needed?
- What problem does a settings object with environment variables solve?
- Why use Rspack/Rsbuild and Tailwind’s CSS-first configuration here?
- What belongs in the backend `.env` and why must it never be exposed to the frontend?

## Milestone 1 — Data foundation

- Why use PostgreSQL and SQLAlchemy rather than an in-memory store?
- Why use migrations instead of creating tables from ORM metadata at startup?
- How does the seeded development owner work before authentication exists?
- Why should the API return one error envelope for routing, validation, and application errors?
- What is the difference between a database constraint and application validation?
- Why should readiness return `503` while liveness remains `200` when PostgreSQL is unavailable?
- How would authentication replace the single-owner dependency later?

## Milestone 2 — Document ingestion

- Why stream uploads instead of reading the entire file into memory?
- Why are uploaded files stored under a server-generated document id?
- Why is a PDF signature check not sufficient by itself?
- How does the documents table act as a durable queue?
- How does `FOR UPDATE SKIP LOCKED` prevent two workers from processing the same document?
- Why is the claim committed before extraction begins?
- How does the stale-processing timestamp recover work after a worker crash?
- Why keep chunks page-aware and use token overlap?
- Why does retrying ingestion remain idempotent?
- Why are scanned PDFs reported as failed instead of silently producing empty chunks?

## Milestone 3 — Embeddings and semantic retrieval

- Why generate embeddings in the worker instead of inside the upload request?
- Why is a document only `ready` after all chunk vectors are stored?
- Why is the vector column nullable during migration `0004`?
- Why is the embedding dimension part of the database schema?
- What does cosine distance measure, and why expose similarity to API consumers?
- Why must owner and readiness filters remain inside the SQL query?
- What does HNSW provide, and what does approximate nearest-neighbour search trade away?
- Why batch provider requests and validate response count, order, and dimensions?
- What happens when the embedding provider is unconfigured or unavailable?
- Why hide provider-specific SDK details behind a small protocol?
- How does document reprocessing recover from provider configuration failures?
- How would you test retrieval deterministically without network access?
- What happens to existing ready documents when migration `0004` runs?

## Milestone 4 — Planned grounded answers

- How should a chat request resolve the owner, conversation, and selected documents?
- How can the application guarantee that every citation belongs to retrieved evidence?
- What should the assistant say when retrieval returns insufficient evidence?
- Why should citations contain document ids and page numbers rather than only text?
- How would you prevent the model from using outside knowledge?
- What should be persisted for a reproducible answer: messages, citations, latency, and token usage?

## Cross-cutting production questions

- Where are authorization boundaries enforced, and how would you test for cross-owner leaks?
- Which failures are safe to retry, and which need an explicit conflict response?
- What information belongs in logs but not in user-facing error messages?
- How would you add observability for upload latency, queue age, embedding latency, and retrieval quality?
- How would you migrate to a different embedding model without mixing incompatible vectors?
- When would PostgreSQL-backed work queues stop being sufficient?
- Which tests are unit tests, integration tests, and end-to-end tests in this repository?
