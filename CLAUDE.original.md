# AI Career Architect — Project Notes

## What this project is

An AI-powered Career Operating System that analyzes a user's real professional presence (LinkedIn, GitHub, resume, portfolio, coding profiles) and generates truthful, evidence-based, user-approved improvements. It must never fabricate any professional information. Everything runs at zero cost by default.

## Architecture

- The backend is a FastAPI application located in `apps/api`. It uses async SQLAlchemy with a SQLite database by default (`career.db`), and can optionally use PostgreSQL with pgvector via docker-compose.
- The frontend is a Next.js 14 application with Tailwind CSS located in `apps/web`.
- The agent pipeline lives in `apps/api/app/agents/orchestrator.py`. There are 29 agents organized into 9 sequential phases, and agents within each phase run in parallel using asyncio.gather. LangGraph is optional; the phased asyncio implementation is primary.
- Every agent must have a deterministic fallback that works without any LLM, so the product functions with zero cost and zero external dependencies.
- The fact validation gate is in `apps/api/app/services/validation.py`. It performs deterministic evidence grounding (any metric or named entity not found in the collected evidence corpus is rejected) plus an optional LLM six-question cross-examination.
- Platform updates never mutate accounts directly. Approved suggestions become apply-ready artifact files under `apps/api/data/output/run_<id>/`.

## Development environment

- Python is not on PATH on this machine. Use the virtual environment interpreter at `.venv\Scripts\python.exe`.
- The default LLM is the user's local Ollama model `qwen3:8b`, configured in `.env` as `ollama/qwen3:8b`.
- The network connection on this machine is flaky. pip and npm installs need retry loops with long timeouts (`--timeout 90 --retries 10` for pip).
- Playwright browsers are not installed yet; the web collector falls back to plain httpx fetching. Install with `.venv\Scripts\python -m playwright install chromium`.

## Commands

- Run backend tests: `cd apps/api` then `..\..\.venv\Scripts\python.exe -m pytest -q` (20 tests, all should pass).
- Build frontend: `cd apps/web` then `npm run build`.
- Start both dev servers: `.\scripts\dev.ps1` (API on port 8000, UI on port 3000).

## Conventions

- All backend code is async. Structured logging goes through structlog. Network calls are wrapped in tenacity retries.
- New platform collectors are registered in `apps/api/app/collectors/registry.py`.
- New roles are added to `ROLE_TAXONOMY` in `apps/api/app/agents/research.py`.
- Suggestions must always carry `evidence_ids` referencing Evidence rows; suggestions without evidence are rejected by the validator.
