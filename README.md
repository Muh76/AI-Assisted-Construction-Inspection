# AI-Assisted Construction Inspection

Monorepo for an AI-assisted building compliance inspection workflow. Upload architectural drawings, extract schedule data, populate a project model (rooms, doors, corridors, exits, fire protection), and run rule checks against seeded regulation clauses. Results are available via a REST API, a Next.js web UI, and PDF export.

## Repository layout

| Path | Purpose |
|------|---------|
| `apps/compliance-web/` | Next.js frontend (project list, detail forms, drawing review) |
| `services/compliance-api/` | FastAPI backend, SQLAlchemy models, Alembic migrations, compliance rules |
| `data/raw/` | Uploaded drawing PDFs (created at runtime) |
| `docker-compose.yml` | Local Postgres + API + web stack |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- Python **3.11+** (for migrations, seeds, and tests on the host)
- Node.js **20+** (optional — only if running the frontend outside Docker)

## Local setup

### 1. Configure environment

From the repository root:

```bash
cp .env.example .env
```

The defaults in `.env.example` work for local Docker Compose. Key variables:

| Variable | Purpose |
|----------|---------|
| `POSTGRES_*` | Postgres credentials and database name |
| `DATABASE_URL` | SQLAlchemy URL for the API (uses hostname `postgres` inside Compose) |
| `JWT_SECRET_KEY` | Secret for API auth tokens (required) |
| `API_BASE_URL` | URL the web app uses for server-side API calls (`http://compliance-api:8000` in Compose) |

### 2. Start services

```bash
docker compose up --build
```

This starts:

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **API** | http://localhost:8000 |
| **Postgres** | `localhost:5432` (for host-side migrations/seeds) |

Wait until the API health check responds:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 3. Run database migrations

The API container does not run migrations automatically. From your host machine:

```bash
cd services/compliance-api
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install ".[dev]"
cp .env.example .env
alembic upgrade head
```

Use the `services/compliance-api/.env.example` values — `DATABASE_URL` points at `localhost:5432`, which is the published Postgres port from Compose.

### 4. Seed data

Still in `services/compliance-api` with the virtualenv activated:

```bash
seed-regulations
seed-example
```

- **`seed-regulations`** — inserts OBC regulation clauses used by compliance rules (idempotent).
- **`seed-example`** — creates a sample user, project, rooms, doors, corridors, exits, and fire protection items.

Sample login after seeding:

| Field | Value |
|-------|-------|
| Email | `seed@example.com` |
| Password | `seed-password-change-me` |

Or register a new account at http://localhost:3000/register.

### 5. Use the application

1. Open http://localhost:3000 and sign in.
2. Create or open a project, add building data, and view the compliance report.
3. Upload a PDF drawing on a project page — text extraction and review flows run automatically.
4. Explore the API interactively at http://localhost:8000/docs (Swagger UI).

## Running tests

Backend tests live in `services/compliance-api/tests/`. They use an in-memory SQLite database for speed and do not require Docker to be running.

```bash
cd services/compliance-api
python -m venv .venv
source .venv/bin/activate          # or .\.venv\Scripts\activate on Windows
pip install ".[dev]"
pytest
```

CI (`.github/workflows/test.yml`) also runs `alembic upgrade head` against Postgres before `pytest` to verify migrations apply cleanly.

Optional utilities:

```bash
audit-rules        # report which rules wire regulation_clause_id vs hardcoded thresholds
```

## Local URLs

| Resource | URL |
|----------|-----|
| Web app | http://localhost:3000 |
| API health | http://localhost:8000/health |
| Swagger UI | http://localhost:8000/docs |
| OpenAPI JSON | http://localhost:8000/openapi.json |

## Optional: run apps without Docker

You can run the API and web app directly on the host while keeping Postgres in Docker:

```bash
# Postgres only
docker compose up postgres -d

# API (from services/compliance-api, after migrations/seeds above)
uvicorn app.main:app --reload --port 8000

# Web (from apps/compliance-web)
npm install
# Create apps/compliance-web/.env.local with:
# API_BASE_URL=http://localhost:8000
npm run dev
```

The dev frontend will be at http://localhost:3000.

## Stopping services

```bash
docker compose down
```

Add `-v` to remove the Postgres volume and wipe database data.
