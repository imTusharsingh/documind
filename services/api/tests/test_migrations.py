from sqlalchemy import Engine, inspect, text


def test_migrations_are_at_head(engine: Engine) -> None:
    with engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()

    assert version == "0007"


def test_users_table_has_expected_columns(engine: Engine) -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("users")}

    assert columns == {"id", "email", "display_name", "created_at"}


def test_email_is_unique(engine: Engine) -> None:
    names = {constraint["name"] for constraint in inspect(engine).get_unique_constraints("users")}

    assert "uq_users_email" in names


def test_documents_table_has_expected_columns(engine: Engine) -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("documents")}

    assert columns == {
        "id",
        "owner_id",
        "original_filename",
        "content_type",
        "size_bytes",
        "storage_path",
        "status",
        "page_count",
        "chunk_count",
        "error_message",
        "created_at",
        "updated_at",
        "processing_started_at",
        "processed_at",
    }


def test_documents_status_is_constrained(engine: Engine) -> None:
    checks = {
        constraint["name"] for constraint in inspect(engine).get_check_constraints("documents")
    }

    assert "ck_documents_document_status" in checks


def test_documents_have_a_worker_claim_index(engine: Engine) -> None:
    indexes = {index["name"] for index in inspect(engine).get_indexes("documents")}

    assert "ix_documents_status_created_at" in indexes
    assert "ix_documents_owner_id" in indexes


def test_chunks_are_unique_per_document_and_index(engine: Engine) -> None:
    names = {
        constraint["name"]
        for constraint in inspect(engine).get_unique_constraints("document_chunks")
    }

    assert "uq_document_chunks_document_id_chunk_index" in names


def test_chunks_have_vector_storage_and_similarity_index(engine: Engine) -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("document_chunks")}
    indexes = {index["name"] for index in inspect(engine).get_indexes("document_chunks")}

    assert "embedding" in columns
    assert "ix_document_chunks_embedding_hnsw" in indexes


def test_development_owner_is_seeded_once(engine: Engine) -> None:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT email, display_name FROM users WHERE id = :id"),
            {"id": "00000000-0000-0000-0000-000000000001"},
        ).all()

    assert rows == [("owner@documind.local", "Development Owner")]


def test_conversation_tables_exist(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())

    assert {"conversations", "messages", "message_citations"} <= tables
