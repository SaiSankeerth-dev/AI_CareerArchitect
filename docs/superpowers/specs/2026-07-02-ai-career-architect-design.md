# AI Career Architect — Design Spec (2026-07-02)

## Purpose

AI-powered Career Operating System. Ingests a user's real professional presence (LinkedIn, GitHub, resume, portfolio, coding profiles), benchmarks against a target role, and generates **evidence-based, truthful, user-approved** improvements across every platform. Zero-cost to run: local Ollama LLMs, free-tier/local infrastructure only.

## Non-negotiable principles

1. **Truth-only:** never fabricate projects, skills, employers, metrics, certifications, or activity. Every suggestion must cite evidence from the collected Unified Professional Profile.
2. **User approval gate:** no platform change applied without explicit approval. Flow is always Current → Suggested → Reason → Benefit → Approve → Apply → Verify.
3. **Zero cost:** local Ollama models (qwen2.5 / llama3.2 / deepseek / mistral) via LiteLLM; optional paid keys (OpenAI/Anthropic/Gemini) are opt-in only. PostgreSQL+pgvector+Redis via Docker locally; SQLite + in-memory fallback so it runs with no Docker at all.

## Architecture (monorepo)

```
AI_CareerArchitect/
├── apps/
│   ├── api/            # FastAPI backend (Python 3.11+)
│   │   ├── app/
│   │   │   ├── core/           # config, logging, db, cache, llm (LiteLLM), security
│   │   │   ├── models/         # SQLAlchemy: User, TargetRole, ProfileSource,
│   │   │   │                   # UnifiedProfile, Evidence, Suggestion, Approval,
│   │   │   │                   # AppliedChange, CareerReport
│   │   │   ├── schemas/        # Pydantic DTOs
│   │   │   ├── collectors/     # Playwright + API collectors per platform
│   │   │   ├── agents/         # LangGraph multi-agent system
│   │   │   ├── services/       # validation, approval, scoring, report
│   │   │   └── routers/        # auth, profiles, analysis, suggestions, dashboard
│   │   └── tests/
│   └── web/            # Next.js 14 + React + Tailwind frontend
│       └── src/app/    # sign-in, role select, links, analysis progress,
│                       # before/after review, approvals, dashboard
├── docker-compose.yml  # postgres+pgvector, redis, ollama (all free)
└── docs/
```

## Multi-agent system (LangGraph)

One `BaseAgent` abstraction (name, prompt, run(state)) + a LangGraph `StateGraph` orchestrated by **Career Orchestrator**. Agents grouped into pipeline phases; agents inside a phase run in parallel (asyncio):

1. **Collect:** Profile Collector, Screenshot Agent, Content Extraction → Unified Professional Profile (with `Evidence` rows: source URL, raw excerpt, extraction timestamp).
2. **Research:** Role Research, Market Research, Professional Benchmark (local knowledge base + optional free web fetch).
3. **Analyze (parallel):** LinkedIn / GitHub / Resume / Portfolio / Coding Profile / Brand Analysis.
4. **Gap (parallel):** Skill / Experience / Project / Certification Gap.
5. **Improve (parallel):** LinkedIn / GitHub / Resume / Portfolio Improvement, Documentation Generator, ATS Optimizer, Recruiter Simulation.
6. **Validate:** Fact Validation agent — six-question gate (true? verifiable? evidence exists? improves professionalism? matches role? user approved?). Any "no" → suggestion rejected with reason.
7. **Approve/Apply:** Approval Manager (DB-backed queue), Platform Update (Playwright, only supported actions), Verification (re-scrape, diff).
8. **Report:** Career Report Generator → Career Dashboard scores.

State = single typed `CareerState` (TypedDict) flowing through the graph; every agent appends `Suggestion` objects `{platform, field, current, suggested, reason, benefit, evidence_ids[], status}`.

## Collectors

- **GitHub:** free REST API (no key needed for public data; optional PAT raises rate limits). Repos, READMEs, languages, activity.
- **Resume:** PDF/DOCX upload parsed locally (pypdf / python-docx).
- **LinkedIn / portfolio / coding profiles:** Playwright (Chromium, free) reads public pages user provides; per-platform extractors with a generic fallback (text + metadata + og tags). Screenshots stored locally.
- All raw content stored as `Evidence` for the fact-validation chain.

## Fact validation design

Suggestions may only reference facts present in Evidence. Validator does: (a) deterministic checks — every claim token (skill, project name, metric, employer) must string/semantic-match Evidence (pgvector or fallback substring); (b) LLM cross-exam with structured verdict; (c) hard-reject on any fabricated entity. Rejections stored with reasons for transparency.

## Frontend flow

Sign in (local JWT, no external auth cost) → pick target role → paste links / upload resume → progress screen (SSE stream of agent events) → suggestion review (Before/After cards with Reason, Benefit, Evidence; Approve/Reject each) → apply queue → dashboard (Overall Professional Score, per-platform scores, ATS score, recruiter/interview readiness, brand consistency, missing skills/projects/certs, roadmap, learning plan, weekly progress).

## Scoring

Deterministic rubric per platform (0–100): completeness, keyword-match to role taxonomy, activity, documentation quality. Overall = weighted mean. ATS score from keyword coverage + structure checks. Stored per run → weekly progress trend.

## Error handling & ops

Structured logging (structlog), tenacity retries on LLM/scrape calls, graceful degradation (no Docker → SQLite + in-memory cache + substring matching; no Ollama → clear setup instructions, deterministic-only analysis still works). Plugin registry so new platforms/agents drop in.

## Testing

pytest for backend: validation gate (fabrication rejection), scoring rubric, orchestrator wiring, collectors (fixture HTML), approval flow. Frontend: type-check + build as smoke test.

## Decomposition / build order

1. Scaffold monorepo + infra (compose, config, db models, LLM client with Ollama+fallback).
2. Collectors (GitHub API, resume parser, Playwright generic).
3. Agent framework + orchestrator + all agent implementations.
4. Validation + approval + scoring services, API routers.
5. Frontend (all pages).
6. Tests, docs, README.
