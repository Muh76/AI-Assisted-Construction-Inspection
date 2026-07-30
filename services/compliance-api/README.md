# Compliance API

Minimal FastAPI service for construction compliance workflows.

## Prerequisites

- Python 3.11+
- pip

## Setup

From the service directory:

```bash
cd services/compliance-api
python -m venv .venv
```

Activate the virtual environment:

**Windows (PowerShell)**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -e .
```

## Run

Start the development server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Alternatively, use the app factory directly:

```bash
uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

## Health check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok"}
```

Interactive API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).
