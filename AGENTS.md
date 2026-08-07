# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
This monorepo currently contains a single real service: the **Compliance API**
(`services/compliance-api/`), a FastAPI backend for construction building-code
compliance workflows (projects, drawings, rooms/doors/exits, a rules engine, and
PDF report generation). The `apps/`, `packages/`, `infra/`, `tests/`, and `docs/`
top-level folders are currently empty placeholders. All commands below run from
`services/compliance-api/` unless noted.

### Python environment
Dependencies are installed by the startup update script into a virtualenv at
`services/compliance-api/.venv`. Run tools via that venv, e.g.
`.venv/bin/pytest`, `.venv/bin/uvicorn`, `.venv/bin/alembic`. The venv is not
activated for you; either prefix `.venv/bin/` or `source .venv/bin/activate`.

### Tests / lint (no services required)
`.venv/bin/pytest` runs the full suite. Tests use an in-memory SQLite DB and
monkeypatch `JWT_SECRET_KEY`, so **PostgreSQL is not needed for tests**. There is
no separate linter configured; tests are the check.

### Running the API (requires PostgreSQL + `.env`)
PostgreSQL is installed but is **not auto-started** on a fresh VM. Start it each
session, then ensure `.env` exists, then run migrations and the server:

```bash
sudo pg_ctlcluster 16 main start          # start Postgres (idempotent)
cp -n .env.example .env                    # JWT_SECRET_KEY must be set for auth
.venv/bin/alembic upgrade head             # apply migrations
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The Postgres superuser is `postgres`/`postgres` on `localhost:5432`, and the
`compliance` database is created during setup. `DATABASE_URL` defaults to
`postgresql+psycopg2://postgres:postgres@localhost:5432/compliance` when unset.
Health check: `curl http://localhost:8000/health` → `{"status":"ok"}`.
Interactive docs: `http://localhost:8000/docs`.

### Seeding
`.venv/bin/seed-regulations` loads regulation clauses used for compliance
citations and works fine. **`seed-example` currently fails** with a PostgreSQL
enum error (`invalid input value for enum fire_protection_item_type:
"FIRE_EXTINGUISHER"`): the DB enum stores lowercase values but SQLAlchemy emits
the enum member name. This is a pre-existing bug affecting `seed-example` and any
insert into `fire_protection_items`; it does not block the rest of the API. Seed
regulations, then create data via the API for end-to-end testing.

### Optional dependencies
`poppler-utils` is installed (needed by `pdf2image` for rendering drawing PDF
pages). The corridor-width **vision** parsing path needs `OPENAI_API_KEY`; every
other endpoint works without it.
