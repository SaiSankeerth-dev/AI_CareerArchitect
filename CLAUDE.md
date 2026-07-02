# AI Career Architect — Project Notes

## What this project is

AI Career Operating System. Analyze user real professional presence (LinkedIn, GitHub, resume, portfolio, coding profiles) → truthful, evidence-based, user-approved improvements. Never fabricate professional info. Zero cost by default.

## Architecture

- Backend: FastAPI in `apps/api`. Async SQLAlchemy, SQLite default (`career.db`), optional PostgreSQL + pgvector via docker-compose.
- Frontend: Next.js 14 + Tailwind CSS in `apps/web`.
- Agent pipeline: `apps/api/app/agents/orchestrator.py`. 29 agents, 9 sequential phases, agents inside phase run parallel via asyncio.gather. LangGraph optional; phased asyncio primary.
- Every agent need deterministic fallback — work without LLM. Zero cost, zero external deps.
- Fact validation gate: `apps/api/app/services/validation.py`. Deterministic evidence grounding (metric/entity not in evidence corpus → reject) + optional LLM six-question cross-exam.
- Platform updates never mutate accounts. Approved suggestions → artifact files under `apps/api/data/output/run_<id>/`.

## Development environment

- Python not on PATH. Use `.venv\Scripts\python.exe`.
- Default LLM: local Ollama `qwen3:8b`, in `.env` as `ollama/qwen3:8b`.
- Network flaky. pip/npm need retry loops + long timeouts (`--timeout 90 --retries 10` for pip).
- Playwright browsers not installed; web collector fall back to httpx. Install: `.venv\Scripts\python -m playwright install chromium`.

## Commands

- Backend tests: `cd apps/api` then `..\..\.venv\Scripts\python.exe -m pytest -q` (20 tests, all pass).
- Frontend build: `cd apps/web` then `npm run build`.
- Both dev servers: `.\scripts\dev.ps1` (API port 8000, UI port 3000).

## Conventions

- All backend code async. Logging via structlog. Network calls wrapped in tenacity retries.
- New platform collectors: register in `apps/api/app/collectors/registry.py`.
- New roles: add to `ROLE_TAXONOMY` in `apps/api/app/agents/research.py`.
- Suggestions must carry `evidence_ids` referencing Evidence rows; no evidence → validator reject.
