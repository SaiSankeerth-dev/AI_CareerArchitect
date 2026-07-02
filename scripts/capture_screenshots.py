"""One-off script: capture real app screenshots for the README.
Not part of the application; run manually against live dev servers."""

import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

API = "http://localhost:8000"
WEB = "http://localhost:3000"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

EMAIL = "readme-demo@career-architect.dev"
PASSWORD = "readme-demo-pass123"


def get_token() -> str:
    with httpx.Client() as client:
        response = client.post(f"{API}/auth/register",
                               json={"email": EMAIL, "password": PASSWORD})
        if response.status_code != 200:
            response = client.post(f"{API}/auth/login",
                                   json={"email": EMAIL, "password": PASSWORD})
        return response.json()["access_token"]


def ensure_run(client: httpx.Client, headers: dict) -> int:
    runs = client.get(f"{API}/dashboard", headers=headers).json().get("runs", [])
    done = [r for r in runs if r["status"] == "reviewing"]
    if done:
        return done[0]["id"]
    created = client.post(
        f"{API}/runs", headers=headers,
        data={"target_role": "ai_engineer",
              "links": '["https://github.com/torvalds"]'},
    )
    run_id = created.json()["id"]
    for _ in range(30):
        time.sleep(4)
        status = client.get(f"{API}/runs/{run_id}", headers=headers).json()
        if status["status"] in ("reviewing", "done", "failed"):
            break
    return run_id


def main() -> None:
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=30) as client:
        run_id = ensure_run(client, headers)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        page.goto(WEB)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "landing.png"))

        page.evaluate(f"localStorage.setItem('token', '{token}')")

        page.goto(f"{WEB}/setup")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "setup.png"))

        page.goto(f"{WEB}/run/{run_id}/review")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "review.png"), full_page=True)

        page.goto(f"{WEB}/dashboard")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "dashboard.png"), full_page=True)

        browser.close()

    print("Saved screenshots to", OUT)


if __name__ == "__main__":
    main()
