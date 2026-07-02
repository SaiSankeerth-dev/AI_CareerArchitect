from urllib.parse import urlparse

from app.collectors.base import BaseCollector
from app.collectors.github import GitHubCollector
from app.collectors.resume import ResumeCollector
from app.collectors.web import WebCollector

# Domain → platform name. Plugin point: register new platforms here or via
# register_platform().
DOMAIN_PLATFORMS: dict[str, str] = {
    "github.com": "github",
    "linkedin.com": "linkedin",
    "leetcode.com": "leetcode",
    "hackerrank.com": "hackerrank",
    "codeforces.com": "codeforces",
    "kaggle.com": "kaggle",
    "stackoverflow.com": "stackoverflow",
    "devpost.com": "devpost",
    "medium.com": "medium",
    "behance.net": "behance",
    "dribbble.com": "dribbble",
}

_CUSTOM_COLLECTORS: dict[str, type[BaseCollector]] = {}


def register_platform(platform: str, collector_cls: type[BaseCollector]) -> None:
    _CUSTOM_COLLECTORS[platform] = collector_cls


def detect_platform(url: str) -> str:
    host = (urlparse(url).netloc or url).lower().removeprefix("www.")
    for domain, platform in DOMAIN_PLATFORMS.items():
        if host == domain or host.endswith("." + domain):
            return platform
    return "portfolio"


def get_collector(platform: str) -> BaseCollector:
    if platform in _CUSTOM_COLLECTORS:
        return _CUSTOM_COLLECTORS[platform]()
    if platform == "github":
        return GitHubCollector()
    if platform == "resume":
        return ResumeCollector()
    return WebCollector(platform=platform)
