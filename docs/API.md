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
| `POST` | `/documents` | Upload a PDF | 2 |
| `GET` | `/documents` | List and filter documents | 2 |
| `GET` | `/documents/{id}` | Get document status | 2 |
| `DELETE` | `/documents/{id}` | Delete a document and chunks | 2 |
| `POST` | `/chat` | Ask a grounded question | 4 |
| `GET` | `/conversations` | List conversations | 4 |
| `GET` | `/conversations/{id}` | Get a conversation | 4 |
| `POST` | `/evaluation/run` | Run retrieval evaluation | 6 |
