import asyncio
import json

from app.agents.base import BaseAgent
from app.agents.state import CareerState
from app.collectors.base import CollectedData, CollectorError
from app.collectors.registry import detect_platform, get_collector
from app.core.logging import get_logger

log = get_logger(__name__)


class ProfileCollectorAgent(BaseAgent):
    """Fans out to platform collectors for every link + uploaded resume."""

    name = "profile_collector"

    async def run(self, state: CareerState) -> dict:
        targets: list[tuple[str, str]] = []
        for link in state.get("links", []):
            targets.append((detect_platform(link), link))
        if state.get("resume_path"):
            targets.append(("resume", state["resume_path"]))

        async def collect_one(platform: str, target: str) -> CollectedData | None:
            try:
                return await get_collector(platform).collect(target)
            except CollectorError as exc:
                log.warning("collect.failed", platform=platform, error=str(exc))
                return None
            except Exception as exc:  # noqa: BLE001
                log.warning("collect.crashed", platform=platform, error=str(exc))
                return None

        results = await asyncio.gather(*(collect_one(p, t) for p, t in targets))
        sources = [r for r in results if r is not None]
        events = [f"profile_collector: collected {s['platform']}" for s in sources]
        failed = len(targets) - len(sources)
        if failed:
            events.append(f"profile_collector: {failed} source(s) failed")
        return {"sources": sources, "events": events}

    def fallback(self, state: CareerState) -> dict:
        return {"events": ["profile_collector: no LLM needed"]}


class ScreenshotAgent(BaseAgent):
    """Screenshots are captured by WebCollector during collection; this agent
    surfaces them as evidence entries."""

    name = "screenshot"

    async def run(self, state: CareerState) -> dict:
        shots = [
            s["metadata"]["screenshot_path"]
            for s in state.get("sources", [])
            if s.get("metadata", {}).get("screenshot_path")
        ]
        return {"events": [f"screenshot: {len(shots)} captured"]}


class ContentExtractionAgent(BaseAgent):
    """Builds the Unified Professional Profile from raw sources."""

    name = "content_extraction"

    async def run(self, state: CareerState) -> dict:
        profile = self._deterministic_profile(state)
        corpus = "\n\n".join(
            f"[{s['platform']}] {s['text'][:4000]}" for s in state.get("sources", [])
        )
        if corpus:
            extracted = await self.ask(
                "Extract ONLY facts literally present in this content into JSON "
                '{"skills": [str], "projects": [{"name": str, "description": str}], '
                '"experience": [str], "education": [str], "certifications": [str], '
                '"summary": str}. Do not infer or embellish.\n\nCONTENT:\n' + corpus[:12000]
            )
            if isinstance(extracted, dict):
                for key in ("skills", "projects", "experience", "education", "certifications"):
                    merged = profile.get(key, []) + extracted.get(key, [])
                    seen: set[str] = set()
                    unique = []
                    for item in merged:
                        marker = json.dumps(item, sort_keys=True).lower()
                        if marker not in seen:
                            seen.add(marker)
                            unique.append(item)
                    profile[key] = unique
                if extracted.get("summary"):
                    profile["summary"] = extracted["summary"]
        return {"unified_profile": profile, "events": ["content_extraction: done"]}

    def fallback(self, state: CareerState) -> dict:
        return {"unified_profile": self._deterministic_profile(state),
                "events": ["content_extraction: done (deterministic)"]}

    @staticmethod
    def _deterministic_profile(state: CareerState) -> dict:
        profile: dict = {"skills": [], "projects": [], "experience": [],
                         "education": [], "certifications": [], "summary": "",
                         "platforms": {}}
        for source in state.get("sources", []):
            platform = source["platform"]
            profile["platforms"][platform] = {
                "url": source["url"],
                "metadata": source["metadata"],
            }
            if platform == "github":
                for item in source["items"]:
                    if item.get("type") == "repo":
                        profile["projects"].append(
                            {"name": item["name"], "description": item["description"],
                             "source": "github"}
                        )
                        if item.get("language"):
                            profile["skills"].append(item["language"].lower())
            if platform == "resume":
                for item in source["items"]:
                    if item.get("name") == "skills":
                        tokens = [
                            t.strip().lower()
                            for t in item["content"].replace("\n", ",").split(",")
                            if 1 < len(t.strip()) < 40
                        ]
                        profile["skills"].extend(tokens)
        profile["skills"] = sorted(set(profile["skills"]))
        return profile
