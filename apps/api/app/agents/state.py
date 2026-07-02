from typing import Any, TypedDict

from app.collectors.base import CollectedData


class SuggestionDraft(TypedDict):
    agent: str
    platform: str
    field: str
    current: str
    suggested: str
    reason: str
    benefit: str
    evidence_ids: list[int]


class CareerState(TypedDict, total=False):
    run_id: int
    target_role: str
    links: list[str]
    resume_path: str

    sources: list[CollectedData]
    evidence: list[dict]  # {id: int, platform: str, content: str}
    unified_profile: dict[str, Any]

    role_research: dict[str, Any]
    market_research: dict[str, Any]
    benchmarks: dict[str, Any]

    analyses: dict[str, dict]  # platform -> analysis
    gaps: dict[str, list]  # gap kind -> items

    suggestions: list[SuggestionDraft]
    validated: list[SuggestionDraft]
    rejected: list[dict]

    report: dict[str, Any]
    events: list[str]
