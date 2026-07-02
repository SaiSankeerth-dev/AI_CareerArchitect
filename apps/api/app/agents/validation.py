from app.agents.base import BaseAgent
from app.agents.state import CareerState
from app.services.validation import check_grounding, validate_suggestion


class FactValidationAgent(BaseAgent):
    """Gate every suggestion through the six-question truth check. Runs the
    deterministic grounding check always; adds LLM cross-exam when available."""

    name = "fact_validation"

    async def run(self, state: CareerState) -> dict:
        evidence_by_id = {e["id"]: e["content"] for e in state.get("evidence", [])}
        all_texts = list(evidence_by_id.values())
        validated, rejected = [], []
        for draft in state.get("suggestions", []):
            texts = [evidence_by_id[i] for i in draft.get("evidence_ids", [])
                     if i in evidence_by_id] or all_texts
            verdict = await validate_suggestion(draft, texts, state.get("target_role", ""))
            if verdict.ok:
                validated.append(draft)
            else:
                rejected.append({**draft, "rejection_reason": verdict.reason})
        return {
            "validated": validated,
            "rejected": rejected,
            "events": [f"fact_validation: {len(validated)} passed, {len(rejected)} rejected"],
        }

    def fallback(self, state: CareerState) -> dict:
        evidence_by_id = {e["id"]: e["content"] for e in state.get("evidence", [])}
        all_texts = list(evidence_by_id.values())
        validated, rejected = [], []
        for draft in state.get("suggestions", []):
            texts = [evidence_by_id[i] for i in draft.get("evidence_ids", [])
                     if i in evidence_by_id] or all_texts
            if not draft.get("evidence_ids"):
                rejected.append({**draft, "rejection_reason": "No evidence references."})
                continue
            verdict = check_grounding(draft.get("suggested", ""), texts)
            if verdict.ok:
                validated.append(draft)
            else:
                rejected.append({**draft, "rejection_reason": verdict.reason})
        return {
            "validated": validated,
            "rejected": rejected,
            "events": [f"fact_validation: {len(validated)} passed, "
                       f"{len(rejected)} rejected (deterministic)"],
        }
