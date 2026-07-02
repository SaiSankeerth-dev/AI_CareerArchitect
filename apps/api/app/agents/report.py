from app.agents.base import BaseAgent
from app.agents.state import CareerState
from app.services import scoring

# Free learning resources per role key — no paid courses required.
FREE_RESOURCES: dict[str, list[dict]] = {
    "ai_engineer": [
        {"skill": "llm", "resource": "Hugging Face NLP Course (free)", "url": "https://huggingface.co/learn"},
        {"skill": "pytorch", "resource": "PyTorch official tutorials (free)", "url": "https://pytorch.org/tutorials/"},
        {"skill": "rag", "resource": "LangChain docs + cookbook (free)", "url": "https://python.langchain.com/docs/"},
    ],
    "software_engineer": [
        {"skill": "algorithms", "resource": "NeetCode roadmap (free)", "url": "https://neetcode.io/roadmap"},
        {"skill": "system design", "resource": "System Design Primer (free)", "url": "https://github.com/donnemartin/system-design-primer"},
    ],
    "full_stack": [
        {"skill": "react", "resource": "react.dev learn track (free)", "url": "https://react.dev/learn"},
        {"skill": "node.js", "resource": "The Odin Project (free)", "url": "https://www.theodinproject.com/"},
    ],
    "backend": [
        {"skill": "sql", "resource": "SQLBolt (free)", "url": "https://sqlbolt.com/"},
        {"skill": "system design", "resource": "System Design Primer (free)", "url": "https://github.com/donnemartin/system-design-primer"},
    ],
    "frontend": [
        {"skill": "css", "resource": "web.dev Learn CSS (free)", "url": "https://web.dev/learn/css"},
        {"skill": "accessibility", "resource": "MDN accessibility docs (free)", "url": "https://developer.mozilla.org/en-US/docs/Web/Accessibility"},
    ],
    "devops": [
        {"skill": "kubernetes", "resource": "Kubernetes official tutorials (free)", "url": "https://kubernetes.io/docs/tutorials/"},
        {"skill": "terraform", "resource": "HashiCorp Learn (free)", "url": "https://developer.hashicorp.com/terraform/tutorials"},
    ],
    "data_scientist": [
        {"skill": "machine learning", "resource": "Kaggle Learn (free)", "url": "https://www.kaggle.com/learn"},
        {"skill": "statistics", "resource": "StatQuest YouTube (free)", "url": "https://www.youtube.com/@statquest"},
    ],
    "cybersecurity": [
        {"skill": "penetration testing", "resource": "TryHackMe free rooms", "url": "https://tryhackme.com/"},
        {"skill": "networking", "resource": "OverTheWire wargames (free)", "url": "https://overthewire.org/wargames/"},
    ],
}


class CareerReportGeneratorAgent(BaseAgent):
    name = "career_report_generator"

    async def run(self, state: CareerState) -> dict:
        return self._build(state)

    def fallback(self, state: CareerState) -> dict:
        return self._build(state)

    def _build(self, state: CareerState) -> dict:
        analyses = state.get("analyses", {})
        platform_scores = {
            platform: scoring.score_platform(platform, analysis)
            for platform, analysis in analyses.items()
            if platform in scoring.SCORERS and analysis
        }
        ats = scoring.ats_score(analyses.get("resume", {}))
        overall = scoring.overall(platform_scores)
        gaps = state.get("gaps", {})
        recruiter = analyses.get("recruiter_sim", {})

        recruiter_readiness = max(0, overall - 10 * len(recruiter.get("blockers", [])))
        interview_readiness = max(
            0, 100 - 12 * len(gaps.get("skills", [])) - 8 * len(gaps.get("projects", []))
        )
        brand = analyses.get("brand", {})
        brand_consistency = scoring.score_brand(brand)

        roadmap = self._roadmap(state, platform_scores)
        role_key = state.get("role_research", {}).get("key", "software_engineer")
        missing_skills = gaps.get("skills", [])
        learning_plan = [
            item for item in FREE_RESOURCES.get(role_key, [])
            if not missing_skills or any(item["skill"] in s.lower() or s.lower() in item["skill"]
                                         for s in missing_skills)
        ] or FREE_RESOURCES.get(role_key, [])

        report = {
            "scores": {
                "overall": overall,
                "platforms": platform_scores,
                "ats": ats,
                "recruiter_readiness": recruiter_readiness,
                "interview_readiness": interview_readiness,
                "brand_consistency": brand_consistency,
            },
            "gaps": {
                "missing_skills": gaps.get("skills", []),
                "missing_projects": gaps.get("projects", []),
                "missing_certifications": gaps.get("certifications", []),
                "experience_notes": gaps.get("experience", []),
            },
            "roadmap": roadmap,
            "learning_plan": learning_plan,
        }
        return {"report": report, "events": ["career_report_generator: done"]}

    @staticmethod
    def _roadmap(state: CareerState, platform_scores: dict) -> list[dict]:
        steps = []
        ordered = sorted(platform_scores.items(), key=lambda kv: kv[1])
        for platform, score in ordered:
            if score < 70:
                steps.append({
                    "step": f"Raise {platform} score from {score}",
                    "detail": f"Apply the approved {platform} suggestions, then re-run analysis.",
                    "priority": "high" if score < 40 else "medium",
                })
        for skill in state.get("gaps", {}).get("skills", [])[:5]:
            steps.append({
                "step": f"Learn and demonstrate: {skill}",
                "detail": "Use the free learning plan resource, then build evidence "
                          "(project/commit) before adding it to any profile.",
                "priority": "medium",
            })
        for project in state.get("gaps", {}).get("projects", [])[:3]:
            steps.append({
                "step": f"Build: {project}",
                "detail": "Create this project for real, publish on GitHub with docs; "
                          "only then reference it on profiles.",
                "priority": "medium",
            })
        return steps
