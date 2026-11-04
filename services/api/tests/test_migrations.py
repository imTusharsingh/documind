from sqlalchemy import Engine, inspect, text


def test_migrations_are_at_head(engine: Engine) -> None:
    with engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()

    assert version == "0002"


def test_users_table_has_expected_columns(engine: Engine) -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("users")}

    assert columns == {"id", "email", "display_name", "created_at"}


def test_email_is_unique(engine: Engine) -> None:
    names = {constraint["name"] for constraint in inspect(engine).get_unique_constraints("users")}

    assert "uq_users_email" in names


def test_development_owner_is_seeded_once(engine: Engine) -> None:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT email, display_name FROM users WHERE id = :id"),
            {"id": "00000000-0000-0000-0000-000000000001"},
        ).all()

    assert rows == [("owner@documind.local", "Development Owner")]
