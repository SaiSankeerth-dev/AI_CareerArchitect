import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.security import get_current_user
from app.models.entities import AnalysisRun, CareerReport, ProfileSource, User
from app.schemas.dto import ReportOut, RunStatus
from app.services.pipeline import execute_run, subscribe, unsubscribe

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunStatus)
async def create_run(
    background: BackgroundTasks,
    target_role: str = Form(...),
    links: str = Form("[]"),  # JSON array of URLs
    resume: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    try:
        link_list = json.loads(links)
        assert isinstance(link_list, list)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(422, "links must be a JSON array of URLs")

    run = AnalysisRun(user_id=user.id, target_role=target_role, status="pending")
    session.add(run)
    await session.flush()

    from app.collectors.registry import detect_platform

    for link in link_list:
        session.add(ProfileSource(run_id=run.id, platform=detect_platform(link), url=link))

    if resume is not None and resume.filename:
        uploads = Path(settings.data_dir) / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        suffix = Path(resume.filename).suffix or ".pdf"
        path = uploads / f"run_{run.id}_resume{suffix}"
        path.write_bytes(await resume.read())
        session.add(ProfileSource(run_id=run.id, platform="resume", url=str(path)))

    await session.commit()
    background.add_task(execute_run, run.id)
    return RunStatus(id=run.id, target_role=run.target_role, status=run.status)


async def _owned_run(run_id: int, session: AsyncSession, user: User) -> AnalysisRun:
    run = (await session.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )).scalar_one_or_none()
    if run is None or run.user_id != user.id:
        raise HTTPException(404, "Run not found")
    return run


@router.get("/{run_id}", response_model=RunStatus)
async def get_run(run_id: int, session: AsyncSession = Depends(get_session),
                  user: User = Depends(get_current_user)):
    run = await _owned_run(run_id, session, user)
    return RunStatus(id=run.id, target_role=run.target_role, status=run.status, error=run.error)


@router.get("/{run_id}/events")
async def run_events(run_id: int, session: AsyncSession = Depends(get_session),
                     user: User = Depends(get_current_user)):
    await _owned_run(run_id, session, user)
    queue = subscribe(run_id)

    async def stream():
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps({'event': message})}\n\n"
                if message.startswith("run:done") or message.startswith("run:failed"):
                    break
        finally:
            unsubscribe(run_id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/{run_id}/report", response_model=ReportOut)
async def get_report(run_id: int, session: AsyncSession = Depends(get_session),
                     user: User = Depends(get_current_user)):
    await _owned_run(run_id, session, user)
    report = (await session.execute(
        select(CareerReport).where(CareerReport.run_id == run_id)
    )).scalar_one_or_none()
    if report is None:
        raise HTTPException(404, "Report not ready")
    return ReportOut(run_id=run_id, scores=report.scores, gaps=report.gaps,
                     roadmap=report.roadmap, learning_plan=report.learning_plan)
