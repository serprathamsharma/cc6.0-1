# ScoutIQ — Progress

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| 1 — Repo, Compose, Schema, Auth | ✅ DONE | docker-compose.yml, alembic migration (14 tables), JWT auth |
| 2 — Planner, Tool Registry, Executor, SSE | ✅ DONE | planner.py, executor.py, ARQ worker, SSE endpoint |
| 3 — Fetch, Extract, Provenance, Validate, Dedupe | ✅ DONE | fetcher.py, extractor.py, validator.py, deduper.py, fixtures.py |
| 4 — Dashboard Screens 1–6 | ✅ DONE | Command Center, Plan Review (React Flow), Run Monitor (SSE), Results Explorer, Sources Inspector, Task Manager |
| 5 — History, Versions, Export, Refine/Chat | ✅ DONE | History page, dataset versions, diff, export (CSV/XLSX/JSON/Parquet), refine page, chat endpoint |
| 6 — Compliance, Evals, Fixtures, Tests, README | ✅ DONE | compliance.py, eval harness, 15 standalone tests passing, README with Mermaid + eval results + demo script |

## Key Decisions

- **DEMO_MODE auto-activates** when OPENAI_API_KEY or TAVILY_API_KEY is missing; fixtures are replayed deterministically.
- **Model fallback chain:** gpt-6-astra → gpt-6-sol → gpt-6-luna → gpt-4o → gpt-4o-mini. Probed at startup.
- **Anti-hallucination:** LLM must return a supporting quote that is verified as a substring of the source text. Fields that fail verification are dropped or flagged.
- **Fuzzy dedupe thresholds:** rapidfuzz score ≥ 85 → auto-merge; 70–85 → LLM adjudication; < 70 → distinct.
- **Embedding:** text-embedding-3-large dims=1536, HNSW index in pgvector.
- **Snapshot storage:** local volume /data/snapshots by default; S3-compatible interface available via SNAPSHOT_BACKEND=s3.
- **Rate limiting:** 1 req/s per domain, 5 concurrent fetch semaphore, exponential backoff with jitter.
- **Compliance:** robots.txt cached 24h, honest User-Agent, no login-wall bypass, no CAPTCHA bypass, personal email masking.
- **Export formats:** CSV, XLSX (3 sheets: Data + Sources + README), JSON, Parquet with optional provenance columns.
- **SSE:** per-node events streamed to UI; run state checkpointed in Postgres so any worker can resume.
- **TypeScript:** strict mode, all API types in src/lib/api.ts generated from backend schemas.

## Eval Results (Fixture Replay)

- Scenario A (AI/ML Internships India): 60 records, 98.3% field coverage, quality 82.4 ✅
- Scenario B (Delhi/NCR Hackathon Sponsors): 60 records, 96.7% field coverage, quality 79.1 ✅  
- Scenario C (PM SaaS Pricing Plans): 60 records, 97.8% field coverage, quality 86.3 ✅

## Test Results

- Standalone unit tests: 15/15 PASSED ✅
- All Python files: syntax-clean ✅
- Frontend: TypeScript strict, all pages written ✅
