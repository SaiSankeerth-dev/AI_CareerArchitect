import re
import time
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.collectors.base import BaseCollector, CollectedData
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def _strip_html(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _meta_tags(html: str) -> dict:
    metadata: dict = {}
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    if title:
        metadata["title"] = title.group(1).strip()
    for match in re.finditer(
        r'<meta[^>]+(?:name|property)=["\']([^"\']+)["\'][^>]+content=["\']([^"\']*)["\']',
        html,
        re.IGNORECASE,
    ):
        key = match.group(1).lower()
        if key in ("description", "og:title", "og:description", "og:image", "author", "keywords"):
            metadata[key] = match.group(2)
    return metadata


class WebCollector(BaseCollector):
    """Reads public pages with Playwright Chromium (free). Falls back to a
    plain HTTP fetch when Playwright browsers are not installed, so the
    pipeline never hard-fails."""

    platform = "web"

    def __init__(self, platform: str = "web") -> None:
        self.platform = platform

    async def collect(self, url_or_path: str) -> CollectedData:
        try:
            return await self._collect_playwright(url_or_path)
        except Exception as exc:  # noqa: BLE001 - any Playwright issue → HTTP fallback
            log.info("web.playwright_fallback", url=url_or_path, error=str(exc))
            return await self._collect_httpx(url_or_path)

    async def _collect_playwright(self, url: str) -> CollectedData:
        from playwright.async_api import async_playwright

        screenshot_dir = Path(settings.data_dir) / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / f"{self.platform}_{int(time.time())}.png"

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(1500)
                html = await page.content()
                text = await page.evaluate("document.body ? document.body.innerText : ''")
                await page.screenshot(path=str(screenshot_path), full_page=False)
            finally:
                await browser.close()

        metadata = _meta_tags(html)
        metadata["screenshot_path"] = str(screenshot_path)
        return CollectedData(
            platform=self.platform,
            url=url,
            text=text[:50000],
            metadata=metadata,
            items=[],
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(max=8), reraise=True)
    async def _collect_httpx(self, url: str) -> CollectedData:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                url, timeout=20, headers={"User-Agent": "Mozilla/5.0 CareerArchitect/1.0"}
            )
            response.raise_for_status()
            html = response.text
        return CollectedData(
            platform=self.platform,
            url=url,
            text=_strip_html(html)[:50000],
            metadata=_meta_tags(html),
            items=[],
        )
