# infra/postgres

Notes on the Postgres + pgvector setup. For local dev, `docker-compose.yml` uses the
`pgvector/pgvector:pg16` image directly, so no custom init scripts are needed — the `pgcrypto`
and `vector` extensions are enabled by the first Alembic migration
(`apps/api/alembic/versions/0001_initial_schema.py`), not by a DB-side init script, so the same
migration works against any managed Postgres provider that supports the `vector` extension.
