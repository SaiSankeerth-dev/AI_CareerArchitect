from app.agents.base import BaseAgent
from app.agents.state import CareerState


def _profile_skills(state: CareerState) -> set[str]:
    return {s.lower() for s in state.get("unified_profile", {}).get("skills", [])
            if isinstance(s, str)}


class SkillGapAgent(BaseAgent):
    name = "skill_gap"

    async def run(self, state: CareerState) -> dict:
        return self._compute(state)

    def fallback(self, state: CareerState) -> dict:
        return self._compute(state)

    def _compute(self, state: CareerState) -> dict:
        role = state.get("role_research", {})
        have = _profile_skills(state)
        corpus = " ".join(s["text"].lower() for s in state.get("sources", []))
        missing = [
            skill for skill in role.get("core_skills", [])
            if skill.lower() not in have and skill.lower() not in corpus
        ]
        return {"gaps": {"skills": missing}, "events": ["skill_gap: done"]}


class ExperienceGapAgent(BaseAgent):
    name = "experience_gap"

    async def run(self, state: CareerState) -> dict:
        return self._compute(state)

    def fallback(self, state: CareerState) -> dict:
        return self._compute(state)

    def _compute(self, state: CareerState) -> dict:
        profile = state.get("unified_profile", {})
        gaps = []
        if not profile.get("experience"):
            gaps.append("No work experience found across platforms — highlight internships, "
                        "freelance work, or substantial project ownership if they exist.")
        if not profile.get("summary"):
            gaps.append("No professional summary found on any platform.")
        return {"gaps": {"experience": gaps}, "events": ["experience_gap: done"]}


class ProjectGapAgent(BaseAgent):
    name = "project_gap"

    async def run(self, state: CareerState) -> dict:
        return self._compute(state)

    def fallback(self, state: CareerState) -> dict:
        return self._compute(state)

    def _compute(self, state: CareerState) -> dict:
        role = state.get("role_research", {})
        projects = state.get("unified_profile", {}).get("projects", [])
        project_text = " ".join(
            f"{p.get('name','')} {p.get('description','')}".lower()
            for p in projects if isinstance(p, dict)
        )
        missing = [
            archetype for archetype in role.get("project_archetypes", [])
            if not any(word in project_text for word in archetype.lower().split()[:2])
        ]
        return {"gaps": {"projects": missing}, "events": ["project_gap: done"]}


class CertificationGapAgent(BaseAgent):
    name = "certification_gap"

    async def run(self, state: CareerState) -> dict:
        return self._compute(state)

    def fallback(self, state: CareerState) -> dict:
        return self._compute(state)

    def _compute(self, state: CareerState) -> dict:
        role = state.get("role_research", {})
        have = " ".join(str(c).lower() for c in
                        state.get("unified_profile", {}).get("certifications", []))
        missing = [c for c in role.get("certifications", []) if c.lower() not in have]
        return {"gaps": {"certifications": missing}, "events": ["certification_gap: done"]}
