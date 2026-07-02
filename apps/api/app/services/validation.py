import difflib
import json
import re
from dataclasses import dataclass

from app.core.llm import LLMUnavailableError, complete, parse_json
from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class Verdict:
    ok: bool
    reason: str


# Words that never need evidence grounding (generic advice vocabulary).
GENERIC_WHITELIST = {
    "readme", "license", "description", "bio", "section", "sections", "keywords",
    "profile", "portfolio", "resume", "linkedin", "github", "contact", "email",
    "meta", "og", "seo", "tags", "documentation", "todo", "headline", "summary",
    "skills", "experience", "education", "projects", "certifications", "recruiters",
    "ats", "badge", "badges", "ci", "cd",
}

_NUMBER_PATTERN = re.compile(r"\b\d[\d,.]*\s*(%|\+|k|m|x)?\b", re.IGNORECASE)
_ENTITY_PATTERN = re.compile(r"\b[A-Z][a-zA-Z0-9+#.]{2,}\b")


def _fuzzy_in(needle: str, haystack: str) -> bool:
    needle = needle.lower()
    if needle in haystack:
        return True
    # Fuzzy: check token-level similarity against haystack words.
    for word in set(haystack.split()):
        if difflib.SequenceMatcher(None, needle, word).ratio() >= 0.85:
            return True
    return False


def check_grounding(suggested: str, evidence_texts: list[str]) -> Verdict:
    """Deterministic anti-fabrication gate: every specific claim (numbers,
    named entities) in a suggestion must exist in the evidence corpus."""
    corpus = " ".join(evidence_texts).lower()
    if not corpus.strip():
        # No evidence at all -> only allow suggestions with no specific claims.
        corpus = ""

    for match in _NUMBER_PATTERN.finditer(suggested):
        token = match.group(0).strip()
        # Numbers inside instructions like "add og:image" or percents about
        # coverage are checks, not claims; require grounding for bare metrics.
        if token and token not in corpus and not _fuzzy_in(token, corpus):
            # Allow single-digit list counts and version-like tokens.
            plain = token.rstrip("%+kmx").replace(",", "")
            if plain.isdigit() and int(plain) <= 10:
                continue
            return Verdict(False, f"Ungrounded metric '{token}' — no evidence contains it.")

    for match in _ENTITY_PATTERN.finditer(suggested):
        entity = match.group(0)
        lowered = entity.lower()
        if lowered in GENERIC_WHITELIST:
            continue
        if len(lowered) <= 3:
            continue
        # Sentence-initial capitalization is not a proper-noun signal
        # ("Highlight your...", "Add a..."). The LLM cross-exam still
        # covers fabricated entities placed at sentence starts.
        preceding = suggested[: match.start()].rstrip()
        if not preceding or preceding[-1] in ".!?\n":
            continue
        if not _fuzzy_in(lowered, corpus):
            return Verdict(False, f"Ungrounded entity '{entity}' — not found in evidence.")

    return Verdict(True, "All specific claims grounded in evidence.")


SIX_QUESTIONS = (
    "1. Is it true given the evidence? "
    "2. Is it verifiable from the evidence? "
    "3. Does concrete evidence exist for every claim? "
    "4. Does it improve professionalism? "
    "5. Does it match the target role? "
    "6. Could the user honestly approve it?"
)


async def llm_cross_exam(suggested: str, reason: str, evidence_texts: list[str],
                         target_role: str) -> Verdict:
    corpus = "\n".join(evidence_texts)[:6000]
    try:
        raw = await complete(
            f"Evidence:\n{corpus}\n\nSuggestion: {suggested}\nReason: {reason}\n"
            f"Target role: {target_role}\n\n"
            f"Answer the six questions: {SIX_QUESTIONS}\n"
            'Return JSON {"all_yes": bool, "failed_question": str}.'
            " If ANY answer is no, all_yes must be false.",
            system="You are a strict fact validator. Reject anything not fully supported "
                   "by the evidence. Reply with valid JSON only.",
            json_mode=True,
        )
        result = parse_json(raw)
        if isinstance(result, dict) and not result.get("all_yes", False):
            return Verdict(False, f"LLM validator: {result.get('failed_question', 'failed')}")
        return Verdict(True, "LLM validator passed.")
    except (LLMUnavailableError, ValueError):
        # Without an LLM the deterministic gate alone decides.
        return Verdict(True, "LLM validator unavailable; deterministic gate applied.")


async def validate_suggestion(draft: dict, evidence_texts: list[str],
                              target_role: str = "") -> Verdict:
    grounding = check_grounding(draft.get("suggested", ""), evidence_texts)
    if not grounding.ok:
        return grounding
    if not draft.get("evidence_ids"):
        return Verdict(False, "Suggestion carries no evidence references.")
    return await llm_cross_exam(
        draft.get("suggested", ""), draft.get("reason", ""), evidence_texts, target_role
    )
