"""Run lifecycle: create run → collect → agents → persist suggestions/report.

Events stream to subscribers (SSE) through an in-process asyncio queue per run.
"""

import asyncio
from collections import defaultdict

from sqlalchemy import select

from app.agents.orchestrator import run_pipeline
from app.agents.state import CareerState
from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.models.entities import (
    AnalysisRun,
    CareerReport,
    Evidence,
    ProfileSource,
    Suggestion,
    UnifiedProfile,
)

log = get_logger(__name__)

# run_id -> list of subscriber queues
_subscribers: dict[int, list[asyncio.Queue]] = defaultdict(list)
# run_id -> replay buffer so late subscribers see prior events
_event_history: dict[int, list[str]] = defaultdict(list)


def subscribe(run_id: int) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    for event in _event_history.get(run_id, []):
        queue.put_nowait(event)
    _subscribers[run_id].append(queue)
    return queue


def unsubscribe(run_id: int, queue: asyncio.Queue) -> None:
    if queue in _subscribers.get(run_id, []):
        _subscribers[run_id].remove(queue)


async def _publish(run_id: int, message: str) -> None:
    _event_history[run_id].append(message)
    for queue in _subscribers.get(run_id, []):
        queue.put_nowait(message)


async def execute_run(run_id: int) -> None:
    """Background task: full pipeline for one run."""
    async with SessionLocal() as session:
        run = (await session.execute(
            select(AnalysisRun).where(AnalysisRun.id == run_id)
        )).scalar_one()
        state = CareerState(
            run_id=run_id,
            target_role=run.target_role,
            links=[s.url for s in (await session.execute(
                select(ProfileSource).where(ProfileSource.run_id == run_id,
                                            ProfileSource.platform != "resume")
            )).scalars()],
            resume_path=next(
                (s.url for s in (await session.execute(
                    select(ProfileSource).where(ProfileSource.run_id == run_id,
                                                ProfileSource.platform == "resume")
                )).scalars()), ""
            ),
            sources=[], evidence=[], suggestions=[], validated=[], rejected=[], events=[],
        )
        run.status = "collecting"
        await session.commit()

    async def event_cb(message: str) -> None:
        await _publish(run_id, message)
        if message == "phase:collect:end":
            await _persist_sources_and_evidence(run_id, state)
            await _set_status(run_id, "analyzing")

    try:
        await run_pipeline(state, event_cb)
        await _persist_results(run_id, state)
        await _set_status(run_id, "reviewing")
        await _publish(run_id, "run:done")
    except Exception as exc:  # noqa: BLE001
        log.error("run.failed", run_id=run_id, error=str(exc))
        await _set_status(run_id, "failed", error=str(exc))
        await _publish(run_id, f"run:failed:{exc}")


async def _set_status(run_id: int, status: str, error: str = "") -> None:
    async with SessionLocal() as session:
        run = (await session.execute(
            select(AnalysisRun).where(AnalysisRun.id == run_id)
        )).scalar_one()
        run.status = status
        run.error = error
        await session.commit()


async def _persist_sources_and_evidence(run_id: int, state: CareerState) -> None:
    """Store collected content and build the evidence list used by validators."""
    async with SessionLocal() as session:
        for source_data in state.get("sources", []):
            source = ProfileSource(
                run_id=run_id,
                platform=source_data["platform"],
                url=source_data["url"],
                raw_content=source_data["text"][:100000],
                screenshot_path=source_data["metadata"].get("screenshot_path", ""),
            )
            session.add(source)
            await session.flush()
            evidence = Evidence(
                run_id=run_id, source_id=source.id, kind="text",
                content=source_data["text"][:100000], url=source_data["url"],
            )
            session.add(evidence)
            await session.flush()
            state.setdefault("evidence", []).append(
                {"id": evidence.id, "platform": source_data["platform"],
                 "content": evidence.content}
            )
            for item in source_data.get("items", []):
                item_evidence = Evidence(
                    run_id=run_id, source_id=source.id, kind="item",
                    content=str(item), url=source_data["url"],
                )
                session.add(item_evidence)
                await session.flush()
                state["evidence"].append(
                    {"id": item_evidence.id, "platform": source_data["platform"],
                     "content": item_evidence.content}
                )
        await session.commit()


async def _persist_results(run_id: int, state: CareerState) -> None:
    async with SessionLocal() as session:
        session.add(UnifiedProfile(run_id=run_id, data=state.get("unified_profile", {})))
        for draft in state.get("validated", []):
            session.add(Suggestion(
                run_id=run_id, agent=draft["agent"], platform=draft["platform"],
                field=draft["field"], current=draft["current"], suggested=draft["suggested"],
                reason=draft["reason"], benefit=draft["benefit"],
                evidence_ids=draft["evidence_ids"], status="validated",
            ))
        for rejected in state.get("rejected", []):
            session.add(Suggestion(
                run_id=run_id, agent=rejected["agent"], platform=rejected["platform"],
                field=rejected["field"], current=rejected["current"],
                suggested=rejected["suggested"], reason=rejected["reason"],
                benefit=rejected["benefit"], evidence_ids=rejected["evidence_ids"],
                status="rejected", rejection_reason=rejected.get("rejection_reason", ""),
            ))
        report = state.get("report", {})
        session.add(CareerReport(
            run_id=run_id,
            scores=report.get("scores", {}),
            gaps=report.get("gaps", {}),
            roadmap=report.get("roadmap", []),
            learning_plan=report.get("learning_plan", []),
        ))
        await session.commit()
