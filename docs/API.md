# API

Base path: `/api/v1`

Interactive OpenAPI documentation: <http://localhost:8000/api/docs>

## Implemented endpoints

### `GET /api/v1/health`

Readiness probe. Executes `SELECT 1` through the application's own SQLAlchemy session, so a success means the API can actually obtain a working connection from the pool — not merely that the process is alive.

**Success:** `200 OK`

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

**Degraded:** `503 Service Unavailable`

```json
{
  "status": "degraded",
  "service": "DocuMind API",
  "version": "0.1.0",
  "environment": "development",
  "dependencies": {
    "database": { "status": "down", "latency_ms": null, "error": "Database connection failed." }
  }
}
```

The body intentionally keeps the same shape in both cases. A monitor can branch on `status` without parsing an error response, and the connection failure message stays generic so internal details are never exposed.

### `GET /api/v1/health/live`

Liveness probe. Touches no dependency and returns `200` whenever the process can serve requests. Used to distinguish "the process is stuck" from "a dependency is down"; restarting the container would not fix the latter.

```json
{
  "status": "ok",
  "service": "DocuMind API",
  "version": "0.1.0",
  "environment": "development",
  "dependencies": {}
}
```

### `GET /api/v1/me`

Returns the workspace owner. Until authentication exists, this is the single development owner seeded by migration `0002`.

```json
{
  "id": "00000000-0000-0000-0000-000000000001",
  "email": "owner@documind.local",
  "display_name": "Development Owner",
  "created_at": "2026-11-04T04:08:24.400847Z"
}
```

If the owner row is missing, the API returns `500` with code `DEVELOPMENT_OWNER_MISSING` and a message naming the fix. That is deliberate: a missing seed is a deployment mistake, not a client error.

### `POST /api/v1/documents`

Uploads a PDF as `multipart/form-data`. The field name is `file`.

```bash
curl -F 'file=@report.pdf;type=application/pdf' http://localhost:8000/api/v1/documents
```

**Success:** `201 Created`

```json
{
  "id": "68610ec0-76ce-491e-9af7-8e03719b63a4",
  "original_filename": "report.pdf",
  "content_type": "application/pdf",
  "size_bytes": 1914,
  "status": "pending",
  "page_count": null,
  "chunk_count": null,
  "error_message": null,
  "created_at": "2026-11-04T04:31:02.933351Z",
  "updated_at": "2026-11-04T04:31:02.933351Z"
}
```

The response is created before ingestion runs, so `status` starts as `pending` and the counts are `null`. A background worker processes the document.

Upload-specific failures keep the shared envelope:

- `413 PAYLOAD_TOO_LARGE` when the stream exceeds `MAX_UPLOAD_MB`.
- `415 UNSUPPORTED_MEDIA_TYPE` when the filename is not a `.pdf` or the content does not start with `%PDF-`.
- `422 VALIDATION_ERROR` when the multipart field is missing.

### `GET /api/v1/documents`

Returns the owner's documents, newest first. An optional `status` query parameter filters by `pending`, `processing`, `ready`, or `failed`.

```bash
curl 'http://localhost:8000/api/v1/documents?status=ready'
```

An unknown status value returns `422 VALIDATION_ERROR`.

### `GET /api/v1/documents/{document_id}`

Returns one document in the same shape as the upload response. Unknown ids return `404 NOT_FOUND`; malformed UUIDs return `422 VALIDATION_ERROR`. This is the endpoint the UI polls while ingestion is running.

### `DELETE /api/v1/documents/{document_id}`

Deletes the document row, cascades to its chunks, and removes the stored PDF. Returns `204 No Content`. Unknown ids return `404 NOT_FOUND`.

### `POST /api/v1/documents/{document_id}/reprocess`

Queues a failed or ready document for extraction, chunking, and embedding again. This is useful after configuring the provider or changing the embedding model. A document currently being processed returns `409 CONFLICT`.

### `POST /api/v1/search`

Embeds a query and returns the closest passages from the owner's ready documents using cosine similarity in pgvector.

```json
{
  "query": "What is the revenue outlook?",
  "limit": 5,
  "document_ids": [],
  "min_similarity": 0.2
}
```

The response includes the source document, page number, chunk index, passage content, and a similarity score between `0` and `1`. Documents that are pending, processing, or failed are never searched. If the provider is not configured or unavailable, the endpoint returns `503 EMBEDDING_UNAVAILABLE`.

### `POST /api/v1/chat`

Asks a grounded question over ready document chunks. Omit `conversation_id` to start a conversation; pass it on later requests to include recent history. Optional `document_ids`, `top_k`, and `min_similarity` narrow retrieval.

```json
{
  "question": "What improved in the study?",
  "conversation_id": null,
  "document_ids": [],
  "top_k": 5,
  "min_similarity": 0.15
}
```

The response contains the answer, an `insufficient_evidence` flag, and citations with the chunk id, document name, page number, and source quote. Citations are validated against the chunks retrieved for that request; model-produced ids that were not retrieved are discarded. If no valid citation remains, the response is an explicit insufficient-evidence answer.

### `GET /api/v1/conversations`

Lists the current owner's conversations, newest activity first.

### `GET /api/v1/conversations/{conversation_id}`

Returns one owner-scoped conversation with user and assistant messages and the validated citations saved with each assistant message. Unknown or cross-owner ids return `404 NOT_FOUND`.

### Document lifecycle

```text
pending -> processing -> ready
                     \-> failed
```

`error_message` is populated only for `failed` documents. `page_count` and `chunk_count` are written together with `ready`, so they are never partially filled. A document stuck in `processing` past the worker's stale threshold is reclaimable by another worker.

## Error format

Every failure uses one envelope, including routing failures, validation failures, and unhandled exceptions:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Not Found",
    "details": null
  }
}
```

| HTTP status | `code` | Cause |
| --- | --- | --- |
| `404` | `NOT_FOUND` | Unknown route or missing resource |
| `405` | `METHOD_NOT_ALLOWED` | Route exists, method does not |
| `409` | `CONFLICT` | Reserved for state conflicts |
| `413` | `PAYLOAD_TOO_LARGE` | Upload exceeds `MAX_UPLOAD_MB` |
| `415` | `UNSUPPORTED_MEDIA_TYPE` | Upload is not a PDF |
| `422` | `VALIDATION_ERROR` | Request body, query, or path validation failed |
| `500` | `INTERNAL_ERROR` | Unhandled exception; details are logged, not returned |
| `500` | `DEVELOPMENT_OWNER_MISSING` | Seeded owner row is absent |
| `503` | `SERVICE_UNAVAILABLE` | Reserved for dependency failures in request paths |

Validation errors put a list of field errors in `details`:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request payload is invalid.",
    "details": [
      { "type": "int_parsing", "loc": ["query", "count"], "msg": "Input should be a valid integer" }
    ]
  }
}
```

The frontend relies on `error.code`, not on message text, so wording can change without breaking clients.

## Future endpoints

| Method | Path | Purpose | Milestone |
| --- | --- | --- | --- |
| `POST` | `/evaluation/run` | Run retrieval evaluation | 6 |
