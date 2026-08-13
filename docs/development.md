# Development

The API keeps a deterministic in-memory adapter for tests and supports a PostgreSQL repository boundary through `DATABASE_URL`. Compose runs PostgreSQL readiness, migrations, and API startup in dependency order. Run migrations with `DATABASE_URL=... scripts/migrate.sh`.
