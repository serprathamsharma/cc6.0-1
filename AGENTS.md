# ScoutIQ — Agent Guide

## Repo Layout
```
scoutiq/
  api/          FastAPI backend (Python 3.12)
  worker/       ARQ async workers
  frontend/     Next.js 15 App Router (TypeScript strict)
  alembic/      DB migrations
  fixtures/     Record-and-replay demo fixtures (A/B/C)
  evals/        Golden-set evaluation harness
  tests/        pytest unit + integration tests
  e2e/          Playwright end-to-end tests
  docker-compose.yml
  Makefile
```

## Commands
```bash
make up          # docker compose up --build -d
make down        # docker compose down -v
make migrate     # alembic upgrade head
make lint        # ruff check . && mypy api/ worker/
make test        # pytest tests/ -x -q
make e2e         # playwright test e2e/
make eval        # python evals/run_evals.py
make dev-api     # uvicorn api.main:app --reload --port 8000
make dev-web     # cd frontend && npm run dev
```

## Rules
- **NO FABRICATION**: every record cell must trace to a source URL + verified snippet.
- If an API key is missing → DEMO MODE using fixtures in fixtures/.
- Tests use disposable fixtures; never touch production services.
- Agents may install deps, run compose, start servers, run tests, and drive headless browser.
- Record assumptions in ASSUMPTIONS.md and continue; stop only for missing credentials.
- Commit after each phase.
