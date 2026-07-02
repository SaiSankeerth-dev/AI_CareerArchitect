import json

from app.agents.base import BaseAgent
from app.agents.state import CareerState, SuggestionDraft


def _evidence_ids(state: CareerState, platform: str) -> list[int]:
    return [e["id"] for e in state.get("evidence", []) if e["platform"] == platform]


def _all_evidence_ids(state: CareerState) -> list[int]:
    return [e["id"] for e in state.get("evidence", [])]


class _ImprovementAgent(BaseAgent):
    """Shared: deterministic suggestions always; LLM suggestions when available,
    each grounded in platform evidence."""

    platform = "generic"

    def deterministic_suggestions(self, state: CareerState) -> list[SuggestionDraft]:
        return []

    def llm_prompt(self, state: CareerState) -> str | None:
        return None

    async def run(self, state: CareerState) -> dict:
        suggestions = self.deterministic_suggestions(state)
        prompt = self.llm_prompt(state)
        if prompt:
            result = await self.ask(prompt)
            items = result if isinstance(result, list) else result.get("suggestions", [])
            evidence_ids = _evidence_ids(state, self.platform)
            for item in items:
                if not isinstance(item, dict) or not item.get("suggested"):
                    continue
                suggestions.append(self.draft(
                    platform=self.platform,
                    field=str(item.get("field", "general"))[:200],
                    current=str(item.get("current", "")),
                    suggested=str(item["suggested"]),
                    reason=str(item.get("reason", "")),
                    benefit=str(item.get("benefit", "")),
                    evidence_ids=evidence_ids,
                ))
        return {"suggestions": suggestions, "events": [f"{self.name}: {len(suggestions)} drafts"]}

    def fallback(self, state: CareerState) -> dict:
        suggestions = self.deterministic_suggestions(state)
        return {"suggestions": suggestions,
                "events": [f"{self.name}: {len(suggestions)} drafts (deterministic)"]}

    def _llm_suggestion_format(self) -> str:
        return (
            'Return JSON {"suggestions": [{"field": str, "current": str, "suggested": str, '
            '"reason": str, "benefit": str}]}. Every "suggested" value must ONLY restate or '
            "reword facts present in the evidence — never add new projects, skills, employers, "
            "numbers, or achievements. Maximum 5 suggestions."
        )


class GitHubImprovementAgent(_ImprovementAgent):
    name = "github_improvement"
    platform = "github"

    def deterministic_suggestions(self, state: CareerState) -> list[SuggestionDraft]:
        analysis = state.get("analyses", {}).get("github", {})
        if not analysis.get("present"):
            return []
        evidence_ids = _evidence_ids(state, "github")
        drafts = []
        for repo in analysis.get("repos_missing_readme", [])[:5]:
            drafts.append(self.draft(
                "github", f"repo:{repo}:README", "No README",
                f"Add a README to '{repo}' describing what it does, how to run it, "
                "and its tech stack (content to be written from the actual code).",
                "Repositories without a README look unmaintained to recruiters.",
                "Recruiters and hiring managers can understand the project in seconds.",
                evidence_ids,
            ))
        for repo in analysis.get("repos_missing_description", [])[:5]:
            drafts.append(self.draft(
                "github", f"repo:{repo}:description", "No description",
                f"Add a one-line description to '{repo}' summarizing its purpose.",
                "Empty descriptions waste prime profile real estate.",
                "Repo lists become scannable on your profile page.",
                evidence_ids,
            ))
        if not state.get("analyses", {}).get("github", {}).get("has_bio"):
            drafts.append(self.draft(
                "github", "profile:bio", "Empty bio",
                f"Add a short bio stating your focus as a {state.get('target_role')} "
                "using only skills you actually have.",
                "The bio is the first text recruiters see on GitHub.",
                "Immediately signals your specialization.",
                evidence_ids,
            ))
        return drafts

    def llm_prompt(self, state: CareerState) -> str | None:
        source = next((s for s in state.get("sources", []) if s["platform"] == "github"), None)
        if not source:
            return None
        return (
            f"Evidence (GitHub profile of a {state.get('target_role')} candidate):\n"
            f"{source['text'][:5000]}\n\n"
            "Suggest improvements to repository presentation, documentation and profile. "
            + self._llm_suggestion_format()
        )


class LinkedInImprovementAgent(_ImprovementAgent):
    name = "linkedin_improvement"
    platform = "linkedin"

    def deterministic_suggestions(self, state: CareerState) -> list[SuggestionDraft]:
        analysis = state.get("analyses", {}).get("linkedin", {})
        if not analysis.get("present"):
            return []
        evidence_ids = _evidence_ids(state, "linkedin")
        drafts = []
        coverage = analysis.get("role_keyword_coverage_pct", 0)
        missing_keywords = [
            k for k in (state.get("role_research", {}).get("core_skills", []))
            if k not in analysis.get("role_keywords_found", [])
        ]
        have = {s.lower() for s in state.get("unified_profile", {}).get("skills", [])}
        addable = [k for k in missing_keywords if k.lower() in have]
        if coverage < 60 and addable:
            drafts.append(self.draft(
                "linkedin", "skills",
                f"{coverage}% role keyword coverage",
                "Surface these skills you already demonstrate elsewhere on your LinkedIn "
                f"profile: {', '.join(addable[:8])}.",
                "These skills appear in your GitHub/resume evidence but not on LinkedIn.",
                "Recruiter searches filter by listed skills; missing ones hide you.",
                evidence_ids or _all_evidence_ids(state),
            ))
        return drafts

    def llm_prompt(self, state: CareerState) -> str | None:
        source = next((s for s in state.get("sources", []) if s["platform"] == "linkedin"), None)
        if not source:
            return None
        return (
            f"Evidence (public LinkedIn page text of a {state.get('target_role')} candidate):\n"
            f"{source['text'][:5000]}\n\n"
            "Suggest improvements to headline, about section, and skills placement. "
            + self._llm_suggestion_format()
        )


class ResumeImprovementAgent(_ImprovementAgent):
    name = "resume_improvement"
    platform = "resume"

    def deterministic_suggestions(self, state: CareerState) -> list[SuggestionDraft]:
        analysis = state.get("analyses", {}).get("resume", {})
        if not analysis.get("present"):
            return []
        evidence_ids = _evidence_ids(state, "resume")
        drafts = []
        for section in analysis.get("missing_sections", []):
            drafts.append(self.draft(
                "resume", f"section:{section}", "Missing section",
                f"Add a '{section}' section — populate it only with your real {section}.",
                f"ATS parsers and recruiters expect a {section} section.",
                "Improves ATS parse rate and scanability.",
                evidence_ids,
            ))
        if analysis.get("quantified_bullets_pct", 0) < 40 and analysis.get("bullet_count", 0) > 0:
            drafts.append(self.draft(
                "resume", "bullets:metrics",
                f"{analysis.get('quantified_bullets_pct')}% of bullets contain numbers",
                "Where you have real measurable outcomes (users, latency, coverage, size), "
                "add those true numbers to the corresponding bullets. Do not invent metrics.",
                "Quantified bullets read as impact; unquantified read as duties.",
                "Stronger recruiter impression, better ATS relevance.",
                evidence_ids,
            ))
        return drafts

    def llm_prompt(self, state: CareerState) -> str | None:
        source = next((s for s in state.get("sources", []) if s["platform"] == "resume"), None)
        if not source:
            return None
        return (
            f"Evidence (resume text of a {state.get('target_role')} candidate):\n"
            f"{source['text'][:6000]}\n\n"
            "Suggest rewording improvements (clarity, action verbs, keyword placement). "
            "Keep every fact identical. " + self._llm_suggestion_format()
        )


class PortfolioImprovementAgent(_ImprovementAgent):
    name = "portfolio_improvement"
    platform = "portfolio"

    def deterministic_suggestions(self, state: CareerState) -> list[SuggestionDraft]:
        analysis = state.get("analyses", {}).get("portfolio", {})
        if not analysis.get("present"):
            return []
        evidence_ids = _evidence_ids(state, "portfolio")
        drafts = []
        if not analysis.get("has_meta_description"):
            drafts.append(self.draft(
                "portfolio", "seo:meta_description", "No meta description",
                "Add a meta description tag summarizing who you are and what you build.",
                "Search engines and link previews use it.",
                "Better SEO and richer link sharing.",
                evidence_ids,
            ))
        if not analysis.get("has_og_tags"):
            drafts.append(self.draft(
                "portfolio", "seo:og_tags", "No Open Graph tags",
                "Add og:title, og:description and og:image tags.",
                "Links shared on LinkedIn/Twitter render as plain URLs without them.",
                "Professional link previews on every share.",
                evidence_ids,
            ))
        if not analysis.get("mentions_contact"):
            drafts.append(self.draft(
                "portfolio", "content:contact", "No visible contact info",
                "Add a contact section or link (email or LinkedIn).",
                "Recruiters who cannot contact you move on.",
                "Direct inbound opportunities.",
                evidence_ids,
            ))
        return drafts

    def llm_prompt(self, state: CareerState) -> str | None:
        source = next((s for s in state.get("sources", []) if s["platform"] == "portfolio"), None)
        if not source:
            return None
        return (
            f"Evidence (portfolio site text of a {state.get('target_role')} candidate):\n"
            f"{source['text'][:4000]}\n\n"
            "Suggest improvements to structure, project presentation and branding. "
            + self._llm_suggestion_format()
        )


class DocumentationGeneratorAgent(_ImprovementAgent):
    """Generates concrete README/document drafts as artifacts from real repo data."""

    name = "documentation_generator"
    platform = "github"

    async def run(self, state: CareerState) -> dict:
        source = next((s for s in state.get("sources", []) if s["platform"] == "github"), None)
        if not source:
            return {"events": ["documentation_generator: no github source"]}
        repos = [i for i in source["items"] if i.get("type") == "repo" and not i.get("has_readme")]
        suggestions = []
        evidence_ids = _evidence_ids(state, "github")
        for repo in repos[:3]:
            try:
                result = await self.ask(
                    "Write a README draft for this repository using ONLY these known facts. "
                    "Mark anything you cannot know as TODO for the author.\n"
                    f"Facts: {json.dumps(repo)}\n"
                    'Return JSON {"readme_markdown": str}.'
                )
                content = result.get("readme_markdown", "") if isinstance(result, dict) else ""
            except Exception:  # noqa: BLE001
                content = ""
            if not content:
                content = self._template_readme(repo)
            suggestions.append(self.draft(
                "github", f"repo:{repo['name']}:README_draft", "No README",
                content,
                "Draft generated from repository metadata only; TODOs mark unknowns.",
                "Ready-to-edit documentation for the repository.",
                evidence_ids,
            ))
        return {"suggestions": suggestions,
                "events": [f"documentation_generator: {len(suggestions)} drafts"]}

    def fallback(self, state: CareerState) -> dict:
        source = next((s for s in state.get("sources", []) if s["platform"] == "github"), None)
        if not source:
            return {"events": ["documentation_generator: no github source"]}
        repos = [i for i in source["items"] if i.get("type") == "repo" and not i.get("has_readme")]
        evidence_ids = _evidence_ids(state, "github")
        suggestions = [
            self.draft(
                "github", f"repo:{repo['name']}:README_draft", "No README",
                self._template_readme(repo),
                "Template generated from repository metadata only.",
                "Ready-to-edit documentation for the repository.",
                evidence_ids,
            )
            for repo in repos[:3]
        ]
        return {"suggestions": suggestions,
                "events": [f"documentation_generator: {len(suggestions)} drafts (template)"]}

    @staticmethod
    def _template_readme(repo: dict) -> str:
        language = repo.get("language") or "TODO: main language"
        description = repo.get("description") or "TODO: one-line description"
        topics = ", ".join(repo.get("topics", [])) or "TODO: topics"
        return (
            f"# {repo['name']}\n\n{description}\n\n"
            f"## Tech\n- {language}\n- Topics: {topics}\n\n"
            "## Getting Started\nTODO: installation and run instructions\n\n"
            "## Features\nTODO: list real features\n\n"
            "## License\nTODO: add a LICENSE file\n"
        )


class ATSOptimizerAgent(_ImprovementAgent):
    name = "ats_optimizer"
    platform = "resume"

    def deterministic_suggestions(self, state: CareerState) -> list[SuggestionDraft]:
        analysis = state.get("analyses", {}).get("resume", {})
        if not analysis.get("present"):
            return []
        role = state.get("role_research", {})
        have = {s.lower() for s in state.get("unified_profile", {}).get("skills", [])}
        missing_but_owned = [
            k for k in role.get("core_skills", [])
            if k not in analysis.get("role_keywords_found", []) and k.lower() in have
        ]
        if not missing_but_owned:
            return []
        return [self.draft(
            "resume", "ats:keywords",
            f"Keyword coverage {analysis.get('role_keyword_coverage_pct', 0)}%",
            "Work these skills you already have (per your other profiles) into the resume "
            f"where truthfully applicable: {', '.join(missing_but_owned[:10])}.",
            "These appear in your evidence but not in the resume text.",
            "Higher ATS match score for the target role.",
            _all_evidence_ids(state),
        )]


class RecruiterSimulationAgent(BaseAgent):
    """6-second recruiter scan simulation → analysis, feeds report."""

    name = "recruiter_simulation"

    async def run(self, state: CareerState) -> dict:
        summary = {
            platform: analysis
            for platform, analysis in state.get("analyses", {}).items() if analysis
        }
        result = await self.ask(
            f"Act as a technical recruiter screening a {state.get('target_role')} candidate "
            f"for 6 seconds per platform. Findings so far: {json.dumps(summary)[:4000]}.\n"
            'Return JSON {"first_impression": str, "would_shortlist": bool, '
            '"blockers": [str], "standouts": [str]} based only on the findings.'
        )
        return {"analyses": {"recruiter_sim": result if isinstance(result, dict) else {}},
                "events": ["recruiter_simulation: done"]}

    def fallback(self, state: CareerState) -> dict:
        analyses = state.get("analyses", {})
        blockers = []
        github = analyses.get("github", {})
        if github and github.get("readme_pct", 100) < 50:
            blockers.append("Most repositories lack READMEs.")
        resume = analyses.get("resume", {})
        if resume and resume.get("role_keyword_coverage_pct", 100) < 40:
            blockers.append("Resume misses most role keywords.")
        return {
            "analyses": {"recruiter_sim": {
                "first_impression": "Determined without LLM: see blockers.",
                "would_shortlist": not blockers,
                "blockers": blockers,
                "standouts": [],
            }},
            "events": ["recruiter_simulation: done (deterministic)"],
        }
