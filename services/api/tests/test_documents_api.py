import io
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.repositories.documents import create_document


def _post_pdf(client: TestClient, path: Path, name: str = "sample.pdf"):
    with path.open("rb") as handle:
        return client.post(
            "/api/v1/documents",
            files={"file": (name, handle, "application/pdf")},
        )


def test_upload_creates_a_pending_document(
    client: TestClient,
    pdf_factory,
    tmp_path: Path,
    test_settings: Settings,
) -> None:
    source = pdf_factory(tmp_path / "source.pdf", ["Hello from page one."])

    response = _post_pdf(client, source)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["original_filename"] == "sample.pdf"
    assert body["page_count"] is None
    assert body["chunk_count"] is None
    assert Path(test_settings.upload_dir, f"{body['id']}.pdf").is_file()


def test_upload_rejects_a_non_pdf_extension(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_upload_rejects_a_file_without_the_pdf_signature(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("fake.pdf", io.BytesIO(b"just text"), "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_upload_rejects_a_file_over_the_size_limit(
    client: TestClient,
    test_settings: Settings,
) -> None:
    payload = b"%PDF-1.7\n" + b"0" * (2 * 1024 * 1024)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("big.pdf", io.BytesIO(payload), "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    upload_dir = Path(test_settings.upload_dir)
    assert not upload_dir.exists() or not any(upload_dir.iterdir())


def test_upload_strips_directories_from_the_client_filename(
    client: TestClient,
    pdf_factory,
    tmp_path: Path,
    test_settings: Settings,
) -> None:
    source = pdf_factory(tmp_path / "source.pdf", ["Path traversal attempt."])

    response = _post_pdf(client, source, name="../../passwd.pdf")

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "passwd.pdf"
    assert Path(test_settings.upload_dir, f"{body['id']}.pdf").is_file()


def test_upload_truncates_a_long_filename_but_keeps_the_pdf_extension(
    client: TestClient,
    pdf_factory,
    tmp_path: Path,
) -> None:
    source = pdf_factory(tmp_path / "source.pdf", ["Long filename."])

    response = _post_pdf(client, source, name=f"{'a' * 400}.pdf")

    assert response.status_code == 201
    filename = response.json()["original_filename"]
    assert len(filename) == 255
    assert filename.endswith(".pdf")


def test_list_returns_newest_first_and_filters_by_status(
    client: TestClient,
    pdf_factory,
    tmp_path: Path,
) -> None:
    source = pdf_factory(tmp_path / "source.pdf", ["Listed document."])
    created = _post_pdf(client, source).json()

    listed = client.get("/api/v1/documents")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created["id"]]

    pending = client.get("/api/v1/documents", params={"status": "pending"})
    assert [item["id"] for item in pending.json()] == [created["id"]]

    ready = client.get("/api/v1/documents", params={"status": "ready"})
    assert ready.json() == []


def test_list_excludes_documents_owned_by_someone_else(
    client: TestClient,
    session: Session,
    pdf_factory,
    tmp_path: Path,
) -> None:
    source = pdf_factory(tmp_path / "source.pdf", ["Owned document."])
    _post_pdf(client, source)

    other_owner = uuid.uuid4()
    session.add(
        User(
            id=other_owner,
            email=f"other-{other_owner}@documind.local",
            display_name="Other Owner",
        )
    )
    session.flush()
    create_document(
        session,
        document_id=uuid.uuid4(),
        owner_id=other_owner,
        original_filename="theirs.pdf",
        content_type="application/pdf",
        size_bytes=10,
        storage_path="/nonexistent/theirs.pdf",
    )

    response = client.get("/api/v1/documents")

    assert [item["original_filename"] for item in response.json()] == ["sample.pdf"]


def test_get_document_and_unknown_ids(client: TestClient, pdf_factory, tmp_path: Path) -> None:
    source = pdf_factory(tmp_path / "source.pdf", ["Fetchable document."])
    created = _post_pdf(client, source).json()

    found = client.get(f"/api/v1/documents/{created['id']}")
    assert found.status_code == 200
    assert found.json()["id"] == created["id"]

    missing = client.get(f"/api/v1/documents/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"

    invalid = client.get("/api/v1/documents/not-a-uuid")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_removes_the_row_chunks_and_file(
    client: TestClient,
    session: Session,
    pdf_factory,
    tmp_path: Path,
    test_settings: Settings,
) -> None:
    source = pdf_factory(tmp_path / "source.pdf", ["Delete me."])
    created = _post_pdf(client, source).json()
    document_id = uuid.UUID(created["id"])

    session.add(
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=document_id,
            page_number=1,
            chunk_index=0,
            content="Delete me.",
            token_count=3,
        )
    )
    session.flush()

    response = client.delete(f"/api/v1/documents/{created['id']}")

    assert response.status_code == 204
    assert not Path(test_settings.upload_dir, f"{created['id']}.pdf").exists()

    session.expire_all()
    assert session.get(Document, document_id) is None
    remaining = session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
    )
    assert remaining == 0
