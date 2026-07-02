from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import get_current_user
from app.models.entities import AnalysisRun, CareerReport, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard(session: AsyncSession = Depends(get_session),
                    user: User = Depends(get_current_user)):
    runs = list((await session.execute(
        select(AnalysisRun).where(AnalysisRun.user_id == user.id)
        .order_by(AnalysisRun.created_at)
    )).scalars())
    if not runs:
        return {"latest": None, "trend": []}
    reports = list((await session.execute(
        select(CareerReport).where(CareerReport.run_id.in_([r.id for r in runs]))
        .order_by(CareerReport.created_at)
    )).scalars())
    trend = [
        {"run_id": rep.run_id,
         "date": rep.created_at.isoformat() if rep.created_at else "",
         "overall": rep.scores.get("overall", 0)}
        for rep in reports
    ]
    latest = reports[-1] if reports else None
    return {
        "latest": {
            "run_id": latest.run_id,
            "scores": latest.scores,
            "gaps": latest.gaps,
            "roadmap": latest.roadmap,
            "learning_plan": latest.learning_plan,
        } if latest else None,
        "trend": trend,
        "runs": [{"id": r.id, "role": r.target_role, "status": r.status} for r in runs],
    }
