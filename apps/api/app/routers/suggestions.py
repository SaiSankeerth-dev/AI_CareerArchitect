from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import get_current_user
from app.models.entities import AnalysisRun, Suggestion, User
from app.schemas.dto import DecisionRequest, SuggestionOut
from app.services import approval

router = APIRouter(tags=["suggestions"])


@router.get("/runs/{run_id}/suggestions", response_model=list[SuggestionOut])
async def get_suggestions(run_id: int, session: AsyncSession = Depends(get_session),
                          user: User = Depends(get_current_user)):
    run = (await session.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )).scalar_one_or_none()
    if run is None or run.user_id != user.id:
        raise HTTPException(404, "Run not found")
    return await approval.list_suggestions(session, run_id)


@router.post("/suggestions/{suggestion_id}/decision", response_model=SuggestionOut)
async def decide(suggestion_id: int, body: DecisionRequest,
                 session: AsyncSession = Depends(get_session),
                 user: User = Depends(get_current_user)):
    suggestion = (await session.execute(
        select(Suggestion).where(Suggestion.id == suggestion_id)
    )).scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(404, "Suggestion not found")
    run = (await session.execute(
        select(AnalysisRun).where(AnalysisRun.id == suggestion.run_id)
    )).scalar_one()
    if run.user_id != user.id:
        raise HTTPException(404, "Suggestion not found")
    try:
        return await approval.decide(session, suggestion_id, body.approve)
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.post("/runs/{run_id}/apply", response_model=list[SuggestionOut])
async def apply_run(run_id: int, session: AsyncSession = Depends(get_session),
                    user: User = Depends(get_current_user)):
    run = (await session.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )).scalar_one_or_none()
    if run is None or run.user_id != user.id:
        raise HTTPException(404, "Run not found")
    applied = await approval.apply_approved(session, run_id)
    return applied
