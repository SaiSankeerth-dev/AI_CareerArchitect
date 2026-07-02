from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.approval import apply_suggestion_artifact
from app.core.logging import get_logger
from app.models.entities import Suggestion

log = get_logger(__name__)


async def list_suggestions(session: AsyncSession, run_id: int) -> list[Suggestion]:
    result = await session.execute(
        select(Suggestion).where(Suggestion.run_id == run_id).order_by(Suggestion.platform)
    )
    return list(result.scalars())


async def decide(session: AsyncSession, suggestion_id: int, approve: bool) -> Suggestion:
    suggestion = (await session.execute(
        select(Suggestion).where(Suggestion.id == suggestion_id)
    )).scalar_one()
    if suggestion.status not in ("validated", "approved", "declined"):
        raise ValueError(f"Suggestion {suggestion_id} is {suggestion.status}; "
                         "only validated suggestions can be decided.")
    suggestion.status = "approved" if approve else "declined"
    await session.commit()
    return suggestion


async def apply_approved(session: AsyncSession, run_id: int) -> list[Suggestion]:
    """Supported action: generate apply-ready artifacts for every approved
    suggestion. Never mutates any external account silently."""
    approved = list((await session.execute(
        select(Suggestion).where(Suggestion.run_id == run_id, Suggestion.status == "approved")
    )).scalars())
    for suggestion in approved:
        suggestion.artifact_path = apply_suggestion_artifact(
            run_id, suggestion.id, suggestion.platform, suggestion.field, suggestion.suggested
        )
        suggestion.status = "applied"
        log.info("suggestion.applied", id=suggestion.id, artifact=suggestion.artifact_path)
    await session.commit()
    return approved
