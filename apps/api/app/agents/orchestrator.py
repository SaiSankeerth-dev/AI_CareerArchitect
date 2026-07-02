"""Career Orchestrator: runs the agent pipeline as phased parallel waves.

Uses LangGraph when installed; the graph is linear across phases with
asyncio-parallel agents inside each phase, which is exactly what a
StateGraph with fan-out/fan-in produces — so we build the phases directly
and keep LangGraph optional to preserve the zero-dependency-failure goal.
"""

import asyncio
from collections.abc import Awaitable, Callable

from app.agents.analysis import (
    BrandAnalysisAgent,
    CodingProfileAnalysisAgent,
    GitHubAnalysisAgent,
    LinkedInAnalysisAgent,
    PortfolioAnalysisAgent,
    ResumeAnalysisAgent,
)
from app.agents.approval import ApprovalManagerAgent, PlatformUpdateAgent, VerificationAgent
from app.agents.base import BaseAgent, merge_update
from app.agents.collection import (
    ContentExtractionAgent,
    ProfileCollectorAgent,
    ScreenshotAgent,
)
from app.agents.gaps import (
    CertificationGapAgent,
    ExperienceGapAgent,
    ProjectGapAgent,
    SkillGapAgent,
)
from app.agents.improvement import (
    ATSOptimizerAgent,
    DocumentationGeneratorAgent,
    GitHubImprovementAgent,
    LinkedInImprovementAgent,
    PortfolioImprovementAgent,
    ResumeImprovementAgent,
    RecruiterSimulationAgent,
)
from app.agents.report import CareerReportGeneratorAgent
from app.agents.research import (
    MarketResearchAgent,
    ProfessionalBenchmarkAgent,
    RoleResearchAgent,
)
from app.agents.state import CareerState
from app.agents.validation import FactValidationAgent
from app.core.logging import get_logger

log = get_logger(__name__)

EventCallback = Callable[[str], Awaitable[None]]

# Pipeline phases; agents within a phase run in parallel.
PHASES: list[tuple[str, list[type[BaseAgent]]]] = [
    ("collect", [ProfileCollectorAgent]),
    ("extract", [ScreenshotAgent, ContentExtractionAgent]),
    ("research", [RoleResearchAgent, MarketResearchAgent, ProfessionalBenchmarkAgent]),
    ("analyze", [LinkedInAnalysisAgent, GitHubAnalysisAgent, ResumeAnalysisAgent,
                 PortfolioAnalysisAgent, CodingProfileAnalysisAgent, BrandAnalysisAgent]),
    ("gaps", [SkillGapAgent, ExperienceGapAgent, ProjectGapAgent, CertificationGapAgent]),
    ("improve", [LinkedInImprovementAgent, GitHubImprovementAgent, ResumeImprovementAgent,
                 PortfolioImprovementAgent, DocumentationGeneratorAgent, ATSOptimizerAgent,
                 RecruiterSimulationAgent]),
    ("validate", [FactValidationAgent]),
    ("approve", [ApprovalManagerAgent, PlatformUpdateAgent, VerificationAgent]),
    ("report", [CareerReportGeneratorAgent]),
]


async def run_pipeline(state: CareerState, event_cb: EventCallback | None = None) -> CareerState:
    """Execute all phases. Mutates and returns state. Emits progress events."""

    async def emit(message: str) -> None:
        state.setdefault("events", []).append(message)
        if event_cb:
            await event_cb(message)

    for phase_name, agent_classes in PHASES:
        await emit(f"phase:{phase_name}:start")
        agents = [cls() for cls in agent_classes]
        updates = await asyncio.gather(*(agent.safe_run(state) for agent in agents))
        for agent, update in zip(agents, updates):
            events = update.pop("events", [])
            merge_update(state, update)
            for event in events:
                await emit(event)
            log.info("agent.done", phase=phase_name, agent=agent.name)
        await emit(f"phase:{phase_name}:end")
    return state


def build_graph():
    """Optional LangGraph representation of the same pipeline (used when
    langgraph is installed; provides visualization/checkpointing hooks)."""
    from langgraph.graph import END, StateGraph

    graph = StateGraph(dict)

    def make_node(agent_classes: list[type[BaseAgent]]):
        async def node(state: dict) -> dict:
            agents = [cls() for cls in agent_classes]
            updates = await asyncio.gather(*(agent.safe_run(state) for agent in agents))
            for update in updates:
                merge_update(state, update)
            return state

        return node

    previous = None
    for phase_name, agent_classes in PHASES:
        graph.add_node(phase_name, make_node(agent_classes))
        if previous:
            graph.add_edge(previous, phase_name)
        else:
            graph.set_entry_point(phase_name)
        previous = phase_name
    graph.add_edge(previous, END)
    return graph.compile()
