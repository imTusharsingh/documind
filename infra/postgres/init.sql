-- This script only runs when PostgreSQL initializes a new data volume.
-- It makes pgvector available before the first Alembic migration.
CREATE EXTENSION IF NOT EXISTS vector;
