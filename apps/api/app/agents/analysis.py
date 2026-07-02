import json

from app.agents.base import BaseAgent
from app.agents.state import CareerState


def _source(state: CareerState, platform: str) -> dict | None:
    for source in state.get("sources", []):
        if source["platform"] == platform:
            return source
    return None


class _PlatformAnalysisAgent(BaseAgent):
    """Shared machinery: deterministic checks + optional LLM commentary."""

    platform = "generic"

    def deterministic(self, state: CareerState) -> dict:
        return {}

    async def run(self, state: CareerState) -> dict:
        analysis = self.deterministic(state)
        source = _source(state, self.platform)
        if source and analysis:
            commentary = await self.ask(
                f"You are analyzing a {self.platform} presence for a "
                f"{state.get('target_role')} candidate. Deterministic findings: "
                f"{json.dumps(analysis)[:2000]}. Content excerpt: {source['text'][:3000]}.\n"
                'Return JSON {"strengths": [str], "weaknesses": [str], "priority_fixes": [str]} '
                "based ONLY on the provided content."
            )
            if isinstance(commentary, dict):
                analysis.update(commentary)
        return {"analyses": {self.platform: analysis},
                "events": [f"{self.name}: done"]}

    def fallback(self, state: CareerState) -> dict:
        return {"analyses": {self.platform: self.deterministic(state)},
                "events": [f"{self.name}: done (deterministic)"]}


class GitHubAnalysisAgent(_PlatformAnalysisAgent):
    name = "github_analysis"
    platform = "github"

    def deterministic(self, state: CareerState) -> dict:
        source = _source(state, "github")
        if not source:
            return {}
        repos = [i for i in source["items"] if i.get("type") == "repo"]
        with_readme = [r for r in repos if r.get("has_readme")]
        with_license = [r for r in repos if r.get("has_license")]
        with_description = [r for r in repos if r.get("description")]
        return {
            "present": True,
            "repo_count": len(repos),
            "readme_pct": round(100 * len(with_readme) / len(repos)) if repos else 0,
            "license_pct": round(100 * len(with_license) / len(repos)) if repos else 0,
            "described_pct": round(100 * len(with_description) / len(repos)) if repos else 0,
            "has_bio": bool(source["metadata"].get("bio")),
            "languages": sorted({r["language"] for r in repos if r.get("language")}),
            "total_stars": sum(r.get("stars", 0) for r in repos),
            "repos_missing_readme": [r["name"] for r in repos if not r.get("has_readme")],
            "repos_missing_description": [r["name"] for r in repos if not r.get("description")],
        }


class LinkedInAnalysisAgent(_PlatformAnalysisAgent):
    name = "linkedin_analysis"
    platform = "linkedin"

    def deterministic(self, state: CareerState) -> dict:
        source = _source(state, "linkedin")
        if not source:
            return {}
        text = source["text"].lower()
        role = state.get("role_research", {})
        keywords = role.get("core_skills", []) + role.get("keywords", [])
        found = [k for k in keywords if k.lower() in text]
        return {
            "present": True,
            "text_length": len(source["text"]),
            "title": source["metadata"].get("title", ""),
            "role_keywords_found": found,
            "role_keyword_coverage_pct": round(100 * len(found) / len(keywords)) if keywords else 0,
        }


class ResumeAnalysisAgent(_PlatformAnalysisAgent):
    name = "resume_analysis"
    platform = "resume"

    def deterministic(self, state: CareerState) -> dict:
        source = _source(state, "resume")
        if not source:
            return {}
        sections = {i["name"] for i in source["items"] if i.get("type") == "section"}
        text = source["text"].lower()
        role = state.get("role_research", {})
        keywords = role.get("core_skills", []) + role.get("keywords", [])
        found = [k for k in keywords if k.lower() in text]
        import re

        bullets = re.findall(r"^\s*[•\-\*]\s*(.+)$", source["text"], re.MULTILINE)
        quantified = [b for b in bullets if re.search(r"\d", b)]
        return {
            "present": True,
            "sections": sorted(sections),
            "missing_sections": sorted({"skills", "experience", "education", "projects"} - sections),
            "role_keywords_found": found,
            "role_keyword_coverage_pct": round(100 * len(found) / len(keywords)) if keywords else 0,
            "bullet_count": len(bullets),
            "quantified_bullets_pct": round(100 * len(quantified) / len(bullets)) if bullets else 0,
            "word_count": len(source["text"].split()),
        }


class PortfolioAnalysisAgent(_PlatformAnalysisAgent):
    name = "portfolio_analysis"
    platform = "portfolio"

    def deterministic(self, state: CareerState) -> dict:
        source = _source(state, "portfolio")
        if not source:
            return {}
        metadata = source["metadata"]
        return {
            "present": True,
            "title": metadata.get("title", ""),
            "has_meta_description": bool(metadata.get("description")),
            "has_og_tags": any(k.startswith("og:") for k in metadata),
            "text_length": len(source["text"]),
            "mentions_contact": any(w in source["text"].lower()
                                    for w in ("contact", "email", "reach me")),
        }


class CodingProfileAnalysisAgent(_PlatformAnalysisAgent):
    name = "coding_profile_analysis"
    platform = "coding"

    CODING_PLATFORMS = ("leetcode", "hackerrank", "codeforces", "kaggle", "stackoverflow")

    def deterministic(self, state: CareerState) -> dict:
        found = {}
        for source in state.get("sources", []):
            if source["platform"] in self.CODING_PLATFORMS:
                found[source["platform"]] = {
                    "url": source["url"],
                    "title": source["metadata"].get("title", ""),
                    "text_length": len(source["text"]),
                }
        return {"present": bool(found), "profiles": found} if found else {}

    async def run(self, state: CareerState) -> dict:
        analysis = self.deterministic(state)
        return {"analyses": {"coding": analysis}, "events": [f"{self.name}: done"]}


class BrandAnalysisAgent(BaseAgent):
    """Cross-platform identity consistency."""

    name = "brand_analysis"

    async def run(self, state: CareerState) -> dict:
        return {"analyses": {"brand": self._consistency(state)},
                "events": ["brand_analysis: done"]}

    def fallback(self, state: CareerState) -> dict:
        return {"analyses": {"brand": self._consistency(state)},
                "events": ["brand_analysis: done (deterministic)"]}

    @staticmethod
    def _consistency(state: CareerState) -> dict:
        names, titles = [], []
        for source in state.get("sources", []):
            metadata = source.get("metadata", {})
            if metadata.get("name"):
                names.append(metadata["name"])
            if metadata.get("title"):
                titles.append(metadata["title"])
        consistent = len({n.lower() for n in names}) <= 1 if names else True
        return {
            "platform_count": len(state.get("sources", [])),
            "names_seen": names,
            "name_consistent": consistent,
            "titles_seen": titles[:5],
        }
