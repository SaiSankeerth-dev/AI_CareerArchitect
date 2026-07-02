import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.collectors.base import BaseCollector, CollectedData, CollectorError
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

API = "https://api.github.com"


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def parse_username(url: str) -> str:
    path = url.split("github.com/")[-1].strip("/")
    username = path.split("/")[0].split("?")[0]
    if not username:
        raise CollectorError(f"Cannot parse GitHub username from {url}")
    return username


class GitHubCollector(BaseCollector):
    """Reads public GitHub data via the free REST API (no key required;
    optional GITHUB_TOKEN raises rate limits — still free)."""

    platform = "github"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(max=8), reraise=True)
    async def _get(self, client: httpx.AsyncClient, path: str, **params) -> httpx.Response:
        response = await client.get(f"{API}{path}", headers=_headers(), params=params, timeout=20)
        response.raise_for_status()
        return response

    async def collect(self, url_or_path: str) -> CollectedData:
        username = parse_username(url_or_path)
        own_client = self._client is None
        client = self._client or httpx.AsyncClient()
        try:
            profile = (await self._get(client, f"/users/{username}")).json()
            repos = (
                await self._get(
                    client, f"/users/{username}/repos", sort="updated", per_page=30
                )
            ).json()
            items: list[dict] = []
            text_parts = [
                f"GitHub profile: {profile.get('name') or username}",
                f"Bio: {profile.get('bio') or ''}",
                f"Public repos: {profile.get('public_repos', 0)}",
                f"Followers: {profile.get('followers', 0)}",
            ]
            for repo in repos:
                if repo.get("fork"):
                    continue
                readme_present = await self._has_readme(client, username, repo["name"])
                item = {
                    "type": "repo",
                    "name": repo["name"],
                    "description": repo.get("description") or "",
                    "language": repo.get("language") or "",
                    "stars": repo.get("stargazers_count", 0),
                    "topics": repo.get("topics", []),
                    "has_readme": readme_present,
                    "has_license": bool(repo.get("license")),
                    "updated_at": repo.get("updated_at", ""),
                    "url": repo.get("html_url", ""),
                }
                items.append(item)
                text_parts.append(
                    f"Repo {item['name']}: {item['description']} "
                    f"[{item['language']}] stars={item['stars']} topics={','.join(item['topics'])}"
                )
            return CollectedData(
                platform=self.platform,
                url=url_or_path,
                text="\n".join(text_parts),
                metadata={
                    "username": username,
                    "name": profile.get("name") or "",
                    "bio": profile.get("bio") or "",
                    "public_repos": profile.get("public_repos", 0),
                    "followers": profile.get("followers", 0),
                    "avatar_url": profile.get("avatar_url", ""),
                    "blog": profile.get("blog") or "",
                },
                items=items,
            )
        except httpx.HTTPStatusError as exc:
            raise CollectorError(f"GitHub API error: {exc.response.status_code}") from exc
        finally:
            if own_client:
                await client.aclose()

    async def _has_readme(self, client: httpx.AsyncClient, user: str, repo: str) -> bool:
        try:
            response = await client.get(
                f"{API}/repos/{user}/{repo}/readme", headers=_headers(), timeout=10
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False
