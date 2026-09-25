# ScoutIQ — Assumptions & Decisions

## API & Models

1. **Model IDs:** gpt-6-astra, gpt-6-sol, gpt-6-luna are used as specified. At startup, availability is probed; if a model is unavailable, the system falls back to gpt-4o (planner), gpt-4o (extractor), gpt-4o-mini (fast). This is logged as a WARNING, not an error.

2. **Structured Outputs:** All LLM calls use `response_format` with strict JSON schemas derived from Pydantic models, as per OpenAI Structured Outputs spec.

3. **Embedding dimensions:** text-embedding-3-large with dimensions=1536 as specified. HNSW index created by Alembic migration.

4. **OpenAI SDK:** Uses the official `openai` Python SDK with the Responses API (not the legacy completions API).

## Data Collection

5. **Search providers:** Tavily is primary; if `TAVILY_API_KEY` is missing, falls back to Brave Search; if both missing, uses `DEMO_MODE` with fixtures.

6. **Playwright:** Only used as last-resort fallback for JS-heavy pages. Async Playwright with stealth plugin disabled (we don't hide our bot nature).

7. **robots.txt caching:** 24-hour TTL cached in Redis. Entries not found in robots.txt are treated as allowed.

8. **Rate limiting:** 1 request/second per domain by default. Configurable via `RATE_LIMIT_DOMAIN_RPS` env var.

## Deduplication

9. **rapidfuzz threshold:** 85+ → auto-merge, 70–85 → LLM adjudication pair, <70 → distinct. Configurable via env.

10. **Embedding similarity:** cosine similarity >0.92 triggers LLM adjudication regardless of fuzzy score.

## Frontend

11. **shadcn/ui:** Using the shadcn/ui component system. Components are initialized via `npx shadcn@latest init`. Base components (button, badge, dialog, input, select, tabs, toast) are expected to be initialized before first run.

12. **React Flow:** Using @xyflow/react v12+. Nodes are positioned automatically using topological sort; users can drag to reposition.

13. **Dark/light theme:** Default is system preference. Stored in localStorage via next-themes.

## Infrastructure

14. **Migrations:** Alembic runs automatically at container startup via `alembic upgrade head` in the api service's `CMD`.

15. **Snapshot storage:** Local volume `/data/snapshots` is the default. S3 interface available by setting `SNAPSHOT_BACKEND=s3` and providing `S3_BUCKET`, `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.

16. **Single workspace:** Auth-lite mode — JWT tokens are workspace-scoped. No multi-tenancy in this version.

17. **Worker concurrency:** Default 5 concurrent fetch tasks, configurable via `FETCH_CONCURRENCY` env var.

## Compliance

18. **PII definition:** Personal email addresses (gmail, yahoo, hotmail, outlook, protonmail, icloud domains) are masked. Business emails (company domains) are kept.

19. **Login detection:** HTTP 401/403 responses and pages containing login forms (detected by `<form>` with password input) are flagged as login-walled and skipped.

20. **User-Agent:** `ScoutIQ/1.0 (+https://github.com/your-org/scoutiq)` — honest, includes contact URL.

## Evals

21. **Fixture data:** All fixture records include realistic (but not real person) data. Company names, stipend amounts, and URLs are plausible but do not correspond to live job postings. This is clearly labeled DEMO MODE in the UI.

22. **Eval golden sets:** Field coverage, quality score, dedupe precision, and source coverage are measured against the fixture data, not live web data.
