# AI Career Architect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a zero-cost, truth-only AI Career Operating System: collect a user's real professional data, run a LangGraph multi-agent pipeline, produce evidence-backed suggestions gated by fact validation and user approval, and render a Career Dashboard.

**Architecture:** FastAPI backend hosting a LangGraph agent pipeline over a Unified Professional Profile with an evidence chain; collectors (GitHub API, resume parser, Playwright); deterministic + LLM fact validation; Next.js frontend consuming REST + SSE.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2 (async), LangGraph, LiteLLM (Ollama default), Playwright, pypdf/python-docx, structlog, tenacity, pytest; Next.js 14, React 18, Tailwind CSS; Docker compose (postgres+pgvector, redis, ollama) with SQLite/in-memory fallback.

## Global Constraints

- Zero-cost default runtime: LLM provider default `ollama/qwen2.5:7b` via LiteLLM; paid providers only via optional env keys.
- No fabrication: suggestions must carry `evidence_ids`; validator hard-rejects claims not grounded in Evidence.
- No platform mutation without an Approval row with status `approved`.
- Works without Docker: `DATABASE_URL` defaults to `sqlite+aiosqlite:///./career.db`; cache falls back to in-process dict.
- All backend code async; structured logging via structlog; network calls wrapped in tenacity retry (3 attempts, exponential).

---

### Task 1: Backend scaffold + infra

**Files:** Create `apps/api/requirements.txt`, `apps/api/app/{__init__,main}.py`, `apps/api/app/core/{__init__,config.py,logging.py,db.py,cache.py,llm.py,security.py}`, `docker-compose.yml`, `.gitignore`, `.env.example`.

**Interfaces (Produces):**
- `core.config.settings: Settings` — fields: `database_url, redis_url, llm_model, llm_api_base, jwt_secret, jwt_algorithm, github_token, cors_origins`.
- `core.db.get_session() -> AsyncSession` (FastAPI dependency), `core.db.Base`, `core.db.init_db()`.
- `core.cache.cache: Cache` — `async get(key) -> str|None`, `async set(key, value, ttl=3600)`. Redis if reachable else dict.
- `core.llm.complete(prompt: str, system: str = "", json_mode: bool = False) -> str` — LiteLLM w/ retry; raises `LLMUnavailableError` when no backend.
- `core.security`: `hash_password`, `verify_password`, `create_token(user_id) -> str`, `get_current_user` dependency.

Steps: write files → `python -c "import app.main"` smoke → commit.

### Task 2: Models + schemas

**Files:** Create `apps/api/app/models/{__init__,entities.py}`, `apps/api/app/schemas/{__init__,dto.py}`; Test `apps/api/tests/test_models.py`.

**Interfaces (Produces):** SQLAlchemy models: `User(id, email, password_hash, created_at)`, `AnalysisRun(id, user_id, target_role, status, created_at)`, `ProfileSource(id, run_id, platform, url, raw_content, screenshot_path, collected_at)`, `Evidence(id, source_id, run_id, kind, content, url)`, `UnifiedProfile(id, run_id, data JSON)`, `Suggestion(id, run_id, agent, platform, field, current, suggested, reason, benefit, evidence_ids JSON, status: proposed|validated|rejected|approved|declined|applied|verified, rejection_reason)`, `CareerReport(id, run_id, scores JSON, roadmap JSON, learning_plan JSON)`. Pydantic DTOs mirror these.

Steps: failing test (create run + suggestion in sqlite memory) → implement → pass → commit.

### Task 3: Collectors

**Files:** Create `apps/api/app/collectors/{__init__,base.py,github.py,resume.py,web.py,registry.py}`; Test `apps/api/tests/test_collectors.py` + fixtures.

**Interfaces (Produces):**
- `BaseCollector.collect(url_or_path: str) -> CollectedData` where `CollectedData = {platform: str, url: str, text: str, metadata: dict, items: list[dict]}`.
- `github.GitHubCollector` — REST API via httpx, public unauth (optional `GITHUB_TOKEN`): profile, repos (name, description, language, stars, topics, has README, license, CI), recent events.
- `resume.ResumeCollector` — pypdf/python-docx local parse → text + heuristic sections (skills, experience, education, projects).
- `web.WebCollector` — Playwright Chromium headless: page text, title, meta/og tags, screenshot to `data/screenshots/`; graceful `PlaywrightUnavailable` fallback to httpx text fetch.
- `registry.detect_platform(url) -> str` + `get_collector(platform)` (plugin dict, easy extension).

Steps per collector: failing test w/ fixture (mock httpx / sample PDF) → implement → pass → commit.

### Task 4: Agent framework + orchestrator

**Files:** Create `apps/api/app/agents/{__init__,base.py,state.py,prompts.py,orchestrator.py,collection.py,research.py,analysis.py,gaps.py,improvement.py,validation.py,approval.py,report.py}`; Test `apps/api/tests/test_orchestrator.py`.

**Interfaces (Produces):**
- `state.CareerState(TypedDict)`: `run_id, target_role, sources: list[CollectedData], unified_profile: dict, role_research: dict, benchmarks: dict, analyses: dict[str, dict], gaps: dict[str, list], suggestions: list[SuggestionDraft], validated: list, rejected: list, report: dict, events: list[str]`.
- `base.BaseAgent`: `name: str`, `async run(state: CareerState) -> dict` (partial state update); LLM helper `self.ask(prompt, json_mode=True)` returns parsed JSON w/ salvage; deterministic fallback when `LLMUnavailableError`.
- `SuggestionDraft = {agent, platform, field, current, suggested, reason, benefit, evidence_ids}`.
- All 29 agents from spec implemented as `BaseAgent` subclasses grouped by module (collection: ProfileCollector/Screenshot/ContentExtraction; research: RoleResearch/MarketResearch/ProfessionalBenchmark; analysis: LinkedIn/GitHub/Resume/Portfolio/CodingProfile/Brand; gaps: Skill/Experience/Project/Certification; improvement: LinkedIn/GitHub/Resume/Portfolio/DocumentationGenerator/ATSOptimizer/RecruiterSimulation; validation: FactValidation; approval: ApprovalManager/PlatformUpdate/Verification; report: CareerReportGenerator).
- `orchestrator.build_graph() -> CompiledGraph`; `orchestrator.run_pipeline(run_id, session, event_cb)` executes phases; intra-phase parallel via `asyncio.gather`; emits events (agent start/finish) through `event_cb` for SSE.
- Role knowledge base `research.ROLE_TAXONOMY: dict[str, dict]` — for each role (ai_engineer, software_engineer, full_stack, backend, frontend, devops, data_scientist, cybersecurity): core_skills, tools, keywords, certifications, project_archetypes. Deterministic, free, offline.

Steps: failing orchestrator test (stub LLM, fixture sources → pipeline yields suggestions + report keys) → implement → pass → commit.

### Task 5: Services

**Files:** Create `apps/api/app/services/{__init__,validation.py,scoring.py,approval.py,report.py,pipeline.py}`; Test `apps/api/tests/test_validation.py`, `apps/api/tests/test_scoring.py`.

**Interfaces (Produces):**
- `validation.validate_suggestion(draft, evidence_texts: list[str]) -> Verdict{ok: bool, reason: str}` — deterministic entity-grounding: named entities/numbers/skills in `suggested` must appear in evidence corpus (case-insensitive, fuzzy ≥0.85 via difflib) unless generic-phrase whitelisted; plus six-question LLM cross-exam when LLM available; rejection reason recorded.
- `scoring.score_platform(platform, analysis: dict, role: dict) -> int` (0-100 rubric: completeness 40, role-keyword coverage 30, activity 15, quality 15); `scoring.ats_score(resume_text, role) -> int`; `scoring.overall(scores: dict) -> int` weighted mean.
- `approval.list_pending(run_id)`, `approval.decide(suggestion_id, approve: bool)`, `approval.apply_approved(run_id)` → PlatformUpdate agent (supported: generates artifacts e.g. README/resume text files under `data/output/`; live Playwright writes stubbed behind `supported_actions` registry) → Verification.
- `report.build_report(state, session) -> CareerReport` — overall, per-platform, ats, recruiter_readiness, interview_readiness, brand_consistency, missing_skills/projects/certs, roadmap (ordered steps), learning_plan (free resources), weekly_progress.
- `pipeline.start_run(user, role, links, resume_path) -> run_id` background task.

Steps: failing tests — fabricated-metric suggestion rejected, grounded suggestion passes; scoring monotonic — implement → pass → commit.

### Task 6: Routers

**Files:** Create `apps/api/app/routers/{__init__,auth.py,runs.py,suggestions.py,dashboard.py}`; wire in `main.py`; Test `apps/api/tests/test_api.py`.

**Interfaces (Produces):** REST: `POST /auth/register`, `POST /auth/login` → JWT; `POST /runs` {target_role, links[], resume?} → run_id (multipart upload for resume); `GET /runs/{id}` status; `GET /runs/{id}/events` SSE; `GET /runs/{id}/suggestions`; `POST /suggestions/{id}/decision` {approve}; `POST /runs/{id}/apply`; `GET /runs/{id}/report`; `GET /dashboard` latest report + trend. CORS for localhost:3000.

Steps: failing httpx ASGI test (register→login→create run w/ stub pipeline→fetch) → implement → pass → commit.

### Task 7: Frontend

**Files:** Create `apps/web/` Next.js 14 app router: `package.json`, `tailwind.config.ts`, `src/lib/api.ts` (fetch wrapper + token), pages: `/` (landing+auth), `/setup` (role select + links + resume upload), `/run/[id]` (SSE progress timeline), `/run/[id]/review` (Before/After cards: Current→Suggested→Reason→Benefit→Evidence, Approve/Reject buttons, Apply bar), `/dashboard` (score rings, platform bars, gaps lists, roadmap, learning plan, weekly trend).

Steps: scaffold → build passes (`npm run build`) → commit.

### Task 8: Tests, docs, verification

**Files:** Create `README.md` (zero-cost setup: Ollama install, optional Docker, run commands), `apps/api/tests/` full suite green, `scripts/dev.ps1`.

Steps: run `pytest` all green → `npm run build` green → README with setup + architecture → final commit.

## Self-Review

Spec coverage: collectors(T3), agents/orchestrator(T4), validation/approval/scoring/report(T5), API(T6), UI(T7), infra/zero-cost(T1), tests/docs(T8) — all spec sections mapped. Placeholders: none — interfaces exact; executor writes bodies per interface contracts. Type consistency: `CollectedData`, `SuggestionDraft`, `CareerState`, `Verdict` used consistently across tasks.
