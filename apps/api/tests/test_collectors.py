from pathlib import Path

import pytest

from app.collectors.registry import detect_platform, get_collector
from app.collectors.resume import ResumeCollector, split_sections


def test_detect_platform():
    assert detect_platform("https://github.com/torvalds") == "github"
    assert detect_platform("https://www.linkedin.com/in/someone") == "linkedin"
    assert detect_platform("https://leetcode.com/u/someone/") == "leetcode"
    assert detect_platform("https://janedoe.dev") == "portfolio"


def test_get_collector_types():
    assert get_collector("github").platform == "github"
    assert get_collector("resume").platform == "resume"
    assert get_collector("linkedin").platform == "linkedin"


def test_split_sections():
    text = (
        "Jane Doe\njane@example.com\n"
        "Skills\nPython, React, Docker\n"
        "Experience\nBuilt a weather dashboard\n"
        "Education\nB.Tech Computer Science\n"
    )
    sections = split_sections(text)
    assert "python" in sections["skills"].lower()
    assert "weather" in sections["experience"].lower()
    assert "b.tech" in sections["education"].lower()


@pytest.mark.asyncio
async def test_resume_collector_txt(tmp_path: Path):
    resume = tmp_path / "resume.txt"
    resume.write_text(
        "Jane Doe\nSkills\nPython, FastAPI\nProjects\nweather-app dashboard\n",
        encoding="utf-8",
    )
    data = await ResumeCollector().collect(str(resume))
    assert data["platform"] == "resume"
    assert "fastapi" in data["text"].lower()
    names = {item["name"] for item in data["items"]}
    assert "skills" in names and "projects" in names


@pytest.mark.asyncio
async def test_github_collector_parses_profile_and_repos(monkeypatch):
    import httpx

    from app.collectors.github import GitHubCollector

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/users/janedoe":
            return httpx.Response(200, json={
                "name": "Jane Doe", "bio": "Builder", "public_repos": 2,
                "followers": 5, "avatar_url": "", "blog": "",
            })
        if path == "/users/janedoe/repos":
            return httpx.Response(200, json=[
                {"name": "weather-app", "description": "React weather dashboard",
                 "language": "JavaScript", "stargazers_count": 12,
                 "topics": ["react"], "license": {"key": "mit"},
                 "updated_at": "2026-01-01T00:00:00Z", "html_url": "x", "fork": False},
                {"name": "forked-thing", "fork": True},
            ])
        if path.endswith("/readme"):
            return httpx.Response(404)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        data = await GitHubCollector(client=client).collect("https://github.com/janedoe")

    assert data["metadata"]["username"] == "janedoe"
    repos = [i for i in data["items"] if i["type"] == "repo"]
    assert len(repos) == 1  # fork excluded
    assert repos[0]["name"] == "weather-app"
    assert repos[0]["has_readme"] is False
    assert repos[0]["has_license"] is True
    assert "weather-app" in data["text"]
