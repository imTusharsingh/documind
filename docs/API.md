# API

Base path: `/api/v1`

Interactive OpenAPI documentation: <http://localhost:8000/api/docs>

## Implemented endpoints

### `GET /api/v1/health`

Liveness endpoint used by Docker Compose and the web application.

**Request:** no parameters.

**Success response:** `200 OK`

```json
{
  "status": "ok",
  "service": "DocuMind API",
  "version": "0.1.0",
  "environment": "development"
}
```

**Implementation:** `services/api/app/api/v1/health.py`

**Response schema:** `services/api/app/schemas/health.py`

The endpoint does not query PostgreSQL yet. Database connectivity is added in Milestone 1 so this milestone can keep infrastructure concerns separate from application data access.

## Future endpoints

The following routes are planned but not implemented. They are listed here to keep the API shape visible.

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

## Error format

The consistent error envelope will be introduced in Milestone 1:

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "Document was not found.",
    "details": null
  }
}
```

Validation errors will also be normalized to this format rather than exposing FastAPI's default response directly.
