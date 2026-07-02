"""Approval Manager, Platform Update and Verification agents.

The Approval Manager persists validated suggestions for user review — nothing
is applied without an explicit per-suggestion approval recorded in the DB.

Platform Update performs only *supported actions*: generating ready-to-use
artifacts (README files, resume text, bio text) under data/output/. Live
account mutation via Playwright is intentionally NOT enabled by default —
platforms like LinkedIn prohibit automated writes, so the system produces
copy-paste-ready artifacts and step-by-step apply instructions instead.
The registry below is the plugin point for adding real automated actions
where a platform officially supports them.
"""

import re
from pathlib import Path

from app.agents.base import BaseAgent
from app.agents.state import CareerState
from app.core.config import settings

# platform -> whether automated apply is supported (vs artifact generation)
SUPPORTED_ACTIONS: dict[str, str] = {
    "github": "artifact",     # README/description drafts saved as files
    "resume": "artifact",     # improved text saved as files
    "linkedin": "artifact",   # copy-paste text artifacts
    "portfolio": "artifact",  # HTML/meta snippets
    "web": "artifact",
}


def _safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)[:80]


class ApprovalManagerAgent(BaseAgent):
    """Marks validated suggestions as awaiting user approval. The API layer
    exposes them; users decide per suggestion."""

    name = "approval_manager"

    async def run(self, state: CareerState) -> dict:
        count = len(state.get("validated", []))
        return {"events": [f"approval_manager: {count} suggestions await user approval"]}

    def fallback(self, state: CareerState) -> dict:
        return {"events": ["approval_manager: ready"]}


def apply_suggestion_artifact(run_id: int, suggestion_id: int, platform: str,
                              field: str, suggested: str) -> str:
    """Supported action: write the approved content as a file the user can
    apply (copy-paste or commit). Returns the artifact path."""
    action = SUPPORTED_ACTIONS.get(platform, "artifact")
    output_dir = Path(settings.data_dir) / "output" / f"run_{run_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    extension = ".md" if "readme" in field.lower() else ".txt"
    path = output_dir / f"{suggestion_id}_{_safe_name(platform)}_{_safe_name(field)}{extension}"
    header = (
        f"# Approved suggestion — {platform} / {field}\n"
        f"# Action type: {action}\n"
        "# Apply this content to your account/profile, then re-run verification.\n\n"
    )
    path.write_text(header + suggested, encoding="utf-8")
    return str(path)


class PlatformUpdateAgent(BaseAgent):
    name = "platform_update"

    async def run(self, state: CareerState) -> dict:
        # Actual application happens through the approval service when the
        # user clicks Apply; this agent reports capability.
        return {"events": ["platform_update: artifact generation ready"]}

    def fallback(self, state: CareerState) -> dict:
        return {"events": ["platform_update: artifact generation ready"]}


class VerificationAgent(BaseAgent):
    """Re-collects a platform after the user applies changes and reports
    whether the suggested content is now present."""

    name = "verification"

    async def run(self, state: CareerState) -> dict:
        return {"events": ["verification: ready (run via /runs/{id}/verify)"]}

    def fallback(self, state: CareerState) -> dict:
        return {"events": ["verification: ready"]}


async def verify_applied(url: str, platform: str, expected_snippets: list[str]) -> dict:
    """Re-scrape and check that approved content now appears."""
    from app.collectors.registry import get_collector

    data = await get_collector(platform).collect(url)
    text = data["text"].lower()
    found = [s for s in expected_snippets if s.lower()[:80] in text]
    return {
        "platform": platform,
        "url": url,
        "verified": len(found) == len(expected_snippets) and bool(expected_snippets),
        "found": len(found),
        "expected": len(expected_snippets),
    }
