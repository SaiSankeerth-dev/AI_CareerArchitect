"""End-to-end pipeline test with no LLM and no network: agents must fall back
deterministically and still produce validated suggestions plus a report."""

import pytest

from app.agents.orchestrator import PHASES, run_pipeline
from app.agents.state import CareerState
from app.collectors.base import CollectedData


@pytest.fixture
def seeded_state() -> CareerState:
    github = CollectedData(
        platform="github",
        url="https://github.com/janedoe",
        text="GitHub profile: Jane Doe. Repo weather-app: React weather dashboard "
             "[JavaScript] stars=12. Repo ml-pipeline:  [Python] stars=0.",
        metadata={"username": "janedoe", "name": "Jane Doe", "bio": "",
                  "public_repos": 2, "followers": 5},
        items=[
            {"type": "repo", "name": "weather-app", "description": "React weather dashboard",
             "language": "JavaScript", "stars": 12, "topics": ["react"],
             "has_readme": True, "has_license": False, "updated_at": "", "url": ""},
            {"type": "repo", "name": "ml-pipeline", "description": "",
             "language": "Python", "stars": 0, "topics": [],
             "has_readme": False, "has_license": False, "updated_at": "", "url": ""},
        ],
    )
    resume = CollectedData(
        platform="resume",
        url="resume.txt",
        text="Jane Doe\nSkills\nPython, JavaScript, React\nExperience\n"
             "- Built weather dashboard used by 200 students\nEducation\nB.Tech CS",
        metadata={"filename": "resume.txt", "sections_found": ["skills", "experience"]},
        items=[
            {"type": "section", "name": "skills", "content": "Python, JavaScript, React"},
            {"type": "section", "name": "experience",
             "content": "Built weather dashboard used by 200 students"},
        ],
    )
    state = CareerState(
        run_id=1, target_role="ai_engineer", links=[], resume_path="",
        sources=[github, resume],
        evidence=[
            {"id": 1, "platform": "github", "content": github["text"]},
            {"id": 2, "platform": "resume", "content": resume["text"]},
        ],
        suggestions=[], validated=[], rejected=[], events=[],
    )
    return state


@pytest.mark.asyncio
async def test_pipeline_deterministic_end_to_end(seeded_state, monkeypatch):
    # Skip the collect phase (sources pre-seeded); keep the rest.
    monkeypatch.setattr(
        "app.agents.orchestrator.PHASES",
        [(name, agents) for name, agents in PHASES if name != "collect"],
    )
    events: list[str] = []

    async def event_cb(message: str) -> None:
        events.append(message)

    state = await run_pipeline(seeded_state, event_cb)

    # Unified profile extracted deterministically.
    profile = state["unified_profile"]
    assert "python" in profile["skills"]
    assert any(p["name"] == "weather-app" for p in profile["projects"])

    # Role research resolved from offline taxonomy.
    assert state["role_research"]["key"] == "ai_engineer"

    # Analyses ran.
    assert state["analyses"]["github"]["repo_count"] == 2
    assert "ml-pipeline" in state["analyses"]["github"]["repos_missing_readme"]

    # Gap agents found missing role skills.
    assert "pytorch" in state["gaps"]["skills"]

    # Improvement agents drafted grounded suggestions; validation kept them.
    assert state["validated"], f"expected validated suggestions, rejected={state['rejected']}"
    for draft in state["validated"]:
        assert draft["evidence_ids"], "validated suggestion must carry evidence"

    # Report generated with scores.
    scores = state["report"]["scores"]
    assert 0 <= scores["overall"] <= 100
    assert "github" in scores["platforms"]

    # Events streamed.
    assert any(e.startswith("phase:report:end") for e in events)


@pytest.mark.asyncio
async def test_fabricated_suggestion_rejected_in_pipeline(seeded_state):
    from app.agents.validation import FactValidationAgent

    seeded_state["suggestions"] = [{
        "agent": "test", "platform": "github", "field": "bio",
        "current": "", "suggested": "Mention your internship at Google and 1,000,000 users.",
        "reason": "", "benefit": "", "evidence_ids": [1, 2],
    }]
    update = FactValidationAgent().fallback(seeded_state)
    assert not update["validated"]
    assert update["rejected"][0]["rejection_reason"]
