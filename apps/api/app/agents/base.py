from abc import ABC, abstractmethod

from app.agents.state import CareerState, SuggestionDraft
from app.core.llm import LLMUnavailableError, complete, parse_json
from app.core.logging import get_logger

log = get_logger(__name__)

TRUTH_SYSTEM_PROMPT = (
    "You are part of AI Career Architect, a truth-only career improvement system. "
    "HARD RULES: Never invent projects, skills, employers, certifications, metrics, "
    "dates, or achievements. Only use facts present in the provided evidence. "
    "If evidence is insufficient, say so instead of guessing. "
    "Reply with valid JSON only."
)


class BaseAgent(ABC):
    """One agent = one responsibility. Agents return partial state updates
    merged by the orchestrator. All LLM use goes through ask(), which
    enforces the truth-only system prompt; fallback() keeps the pipeline
    working with zero LLM (fully free, deterministic)."""

    name: str = "base"

    async def ask(self, prompt: str) -> dict | list:
        raw = await complete(prompt, system=TRUTH_SYSTEM_PROMPT, json_mode=True)
        return parse_json(raw)

    @abstractmethod
    async def run(self, state: CareerState) -> dict:
        """Return a partial CareerState update."""

    async def safe_run(self, state: CareerState) -> dict:
        try:
            return await self.run(state)
        except LLMUnavailableError:
            log.info("agent.llm_unavailable_fallback", agent=self.name)
            return self.fallback(state)
        except Exception as exc:  # noqa: BLE001 - one agent failing must not kill the run
            log.error("agent.failed", agent=self.name, error=str(exc))
            return {"events": [f"{self.name}: failed ({exc})"]}

    def fallback(self, state: CareerState) -> dict:
        """Deterministic result when no LLM is available. Override where a
        useful zero-LLM behavior exists; default is a no-op."""
        return {"events": [f"{self.name}: skipped (LLM unavailable)"]}

    def draft(
        self,
        platform: str,
        field: str,
        current: str,
        suggested: str,
        reason: str,
        benefit: str,
        evidence_ids: list[int] | None = None,
    ) -> SuggestionDraft:
        return SuggestionDraft(
            agent=self.name,
            platform=platform,
            field=field,
            current=current or "",
            suggested=suggested,
            reason=reason,
            benefit=benefit,
            evidence_ids=evidence_ids or [],
        )


def merge_update(state: CareerState, update: dict) -> None:
    """Merge a partial update into state. Lists append, dicts update,
    scalars replace."""
    for key, value in update.items():
        if key in state and isinstance(state[key], list) and isinstance(value, list):
            state[key].extend(value)
        elif key in state and isinstance(state[key], dict) and isinstance(value, dict):
            state[key].update(value)
        else:
            state[key] = value
