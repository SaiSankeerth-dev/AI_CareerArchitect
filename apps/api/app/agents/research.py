import json

from app.agents.base import BaseAgent
from app.agents.state import CareerState

# Free, offline role knowledge base. Deterministic backbone for benchmarking;
# LLM enriches it when available but is never required.
ROLE_TAXONOMY: dict[str, dict] = {
    "ai_engineer": {
        "title": "AI Engineer",
        "core_skills": ["python", "pytorch", "tensorflow", "llm", "rag", "langchain",
                        "prompt engineering", "vector databases", "fine-tuning", "mlops",
                        "transformers", "hugging face"],
        "tools": ["docker", "fastapi", "git", "linux", "aws", "kubernetes"],
        "keywords": ["machine learning", "deep learning", "nlp", "embeddings",
                     "inference", "model deployment", "agents"],
        "certifications": ["AWS Machine Learning Specialty", "Google Professional ML Engineer",
                           "DeepLearning.AI specializations (free to audit)"],
        "project_archetypes": ["RAG chatbot with citations", "fine-tuned domain model",
                               "agentic workflow system", "ML pipeline with monitoring"],
    },
    "software_engineer": {
        "title": "Software Engineer",
        "core_skills": ["data structures", "algorithms", "python", "java", "c++",
                        "system design", "sql", "testing", "oop", "design patterns"],
        "tools": ["git", "docker", "ci/cd", "linux", "debugging tools"],
        "keywords": ["scalable", "distributed systems", "code review", "agile",
                     "microservices", "performance"],
        "certifications": ["AWS Developer Associate", "Oracle Java certification"],
        "project_archetypes": ["distributed system component", "developer tool or CLI",
                               "open source contribution", "high-test-coverage library"],
    },
    "full_stack": {
        "title": "Full Stack Developer",
        "core_skills": ["javascript", "typescript", "react", "node.js", "next.js",
                        "sql", "rest api", "html", "css", "authentication"],
        "tools": ["git", "docker", "postgresql", "mongodb", "tailwind", "vercel"],
        "keywords": ["responsive", "end-to-end", "api design", "state management",
                     "ssr", "web performance"],
        "certifications": ["Meta Full Stack (Coursera, free audit)", "freeCodeCamp certifications"],
        "project_archetypes": ["full SaaS app with auth and payments", "real-time collaborative app",
                               "e-commerce platform", "deployed portfolio with CI/CD"],
    },
    "backend": {
        "title": "Backend Engineer",
        "core_skills": ["python", "java", "go", "sql", "rest api", "grpc", "caching",
                        "message queues", "database design", "authentication"],
        "tools": ["postgresql", "redis", "kafka", "docker", "kubernetes", "git"],
        "keywords": ["scalability", "latency", "throughput", "microservices",
                     "observability", "data modeling"],
        "certifications": ["AWS Solutions Architect Associate", "CKA (Kubernetes)"],
        "project_archetypes": ["high-throughput API service", "event-driven pipeline",
                               "database-heavy application", "rate-limited public API"],
    },
    "frontend": {
        "title": "Frontend Engineer",
        "core_skills": ["javascript", "typescript", "react", "css", "html",
                        "accessibility", "responsive design", "state management", "testing"],
        "tools": ["git", "webpack", "vite", "figma", "storybook", "jest"],
        "keywords": ["ux", "web vitals", "component library", "design system",
                     "seo", "animation"],
        "certifications": ["Meta Front-End (Coursera, free audit)", "freeCodeCamp certifications"],
        "project_archetypes": ["polished component library", "high-Lighthouse-score site",
                               "accessible web app (WCAG)", "interactive data visualization"],
    },
    "devops": {
        "title": "DevOps Engineer",
        "core_skills": ["linux", "bash", "python", "ci/cd", "terraform", "ansible",
                        "kubernetes", "docker", "monitoring", "networking"],
        "tools": ["github actions", "jenkins", "prometheus", "grafana", "aws", "azure"],
        "keywords": ["infrastructure as code", "automation", "reliability", "sre",
                     "observability", "incident response"],
        "certifications": ["CKA", "AWS DevOps Professional", "Terraform Associate"],
        "project_archetypes": ["IaC-managed multi-env deployment", "full CI/CD pipeline",
                               "monitoring stack setup", "self-healing infrastructure demo"],
    },
    "data_scientist": {
        "title": "Data Scientist",
        "core_skills": ["python", "pandas", "numpy", "statistics", "machine learning",
                        "sql", "data visualization", "a/b testing", "scikit-learn"],
        "tools": ["jupyter", "tableau", "power bi", "git", "spark"],
        "keywords": ["insights", "predictive modeling", "feature engineering",
                     "experimentation", "storytelling"],
        "certifications": ["Google Data Analytics (free audit)", "Kaggle competitions"],
        "project_archetypes": ["end-to-end ML project with business impact",
                               "Kaggle competition ranking", "published data analysis",
                               "interactive dashboard"],
    },
    "cybersecurity": {
        "title": "Cybersecurity Engineer",
        "core_skills": ["networking", "linux", "python", "penetration testing",
                        "vulnerability assessment", "siem", "cryptography", "incident response"],
        "tools": ["wireshark", "burp suite", "nmap", "metasploit", "splunk"],
        "keywords": ["threat modeling", "owasp", "zero trust", "compliance",
                     "soc", "red team", "blue team"],
        "certifications": ["CompTIA Security+", "CEH", "OSCP", "TryHackMe/HackTheBox ranks (free tiers)"],
        "project_archetypes": ["CTF writeups", "home lab with SIEM", "security tool on GitHub",
                               "responsible disclosure findings"],
    },
}


def resolve_role(target_role: str) -> dict:
    key = target_role.lower().strip().replace(" ", "_").replace("-", "_")
    if key in ROLE_TAXONOMY:
        return {**ROLE_TAXONOMY[key], "key": key}
    for name, data in ROLE_TAXONOMY.items():
        if key in name or name in key:
            return {**data, "key": name}
    return {**ROLE_TAXONOMY["software_engineer"], "key": "software_engineer",
            "title": target_role}


class RoleResearchAgent(BaseAgent):
    name = "role_research"

    async def run(self, state: CareerState) -> dict:
        role = resolve_role(state["target_role"])
        try:
            enriched = await self.ask(
                f"Role: {role['title']}. Current 2026 baseline: {json.dumps(role)}.\n"
                'Return JSON {"in_demand_skills": [..], "trending_tools": [..], '
                '"interview_focus": [..]} with realistic, current expectations for this role.'
            )
            if isinstance(enriched, dict):
                role["enrichment"] = enriched
        except Exception:  # noqa: BLE001 - enrichment optional
            pass
        return {"role_research": role, "events": ["role_research: done"]}

    def fallback(self, state: CareerState) -> dict:
        return {"role_research": resolve_role(state["target_role"]),
                "events": ["role_research: done (offline taxonomy)"]}


class MarketResearchAgent(BaseAgent):
    name = "market_research"

    async def run(self, state: CareerState) -> dict:
        role = state.get("role_research") or resolve_role(state["target_role"])
        result = await self.ask(
            f"For the role {role['title']}, return JSON "
            '{"market_summary": str, "hiring_signals": [str], "differentiators": [str]} '
            "describing what makes candidates stand out in 2026. Be realistic and generic; "
            "do not invent statistics or cite specific numbers."
        )
        return {"market_research": result if isinstance(result, dict) else {},
                "events": ["market_research: done"]}

    def fallback(self, state: CareerState) -> dict:
        role = state.get("role_research") or resolve_role(state["target_role"])
        return {
            "market_research": {
                "market_summary": f"Candidates for {role['title']} are evaluated on "
                                  "demonstrable projects, core skills and consistent public activity.",
                "hiring_signals": ["public projects with documentation",
                                   "consistent contribution activity",
                                   "role-aligned skills visible on profiles"],
                "differentiators": role.get("project_archetypes", []),
            },
            "events": ["market_research: done (offline)"],
        }


class ProfessionalBenchmarkAgent(BaseAgent):
    name = "professional_benchmark"

    async def run(self, state: CareerState) -> dict:
        role = state.get("role_research") or resolve_role(state["target_role"])
        return {
            "benchmarks": {
                "github": {"repos_with_readme_pct": 90, "pinned_repos": 6,
                           "recent_activity_days": 30, "docs": ["README", "LICENSE", "CI badge"]},
                "linkedin": {"headline_keywords": role["core_skills"][:5],
                             "about_length_words": [120, 300], "skills_listed": 15},
                "resume": {"pages": [1, 2], "quantified_bullets_pct": 60,
                           "keywords": role["core_skills"] + role["keywords"]},
                "portfolio": {"projects_min": 3, "has_contact": True, "responsive": True},
                "coding_profiles": {"recent_activity": True, "profile_complete": True},
            },
            "events": ["professional_benchmark: done"],
        }
