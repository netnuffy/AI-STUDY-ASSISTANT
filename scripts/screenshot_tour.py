"""Screenshot tour of the locally running AI Study Assistant.

Generates the README screenshots in docs/screenshots/.

Prereqs:
- Backend on :8000 and frontend on :3000 (the backend's default CORS
  config allows http://localhost:3000 — use a different port only if you
  also update CORS_ORIGINS).
- Demo user demo@demo.com / demo1234 registered and seeded
  (backend/seed_demo.py).
- Playwright with Firefox: pip install playwright && python -m playwright
  install firefox

Usage (from the repo root):

    python scripts/screenshot_tour.py
"""

import os

import httpx
from playwright.sync_api import sync_playwright

BASE = os.environ.get("PREVIEW_BASE", "http://localhost:3000")
API = "http://localhost:8000/api/v1"
BIO_DOC_ID = "b63939a6-7377-4c48-9e37-a25350d19b74"
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "screenshots",
)


def login_tokens() -> tuple[str, str]:
    resp = httpx.post(
        f"{API}/auth/login",
        data={"username": "demo@demo.com", "password": "demo1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"], data["refresh_token"]


def shoot(page, path: str, name: str) -> None:
    page.goto(BASE + path, wait_until="networkidle")
    page.wait_for_timeout(1500)  # let client-side data render
    page.screenshot(path=os.path.join(OUT, name))
    print(f"saved {name} ({path})")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    access, refresh = login_tokens()
    with sync_playwright() as p:
        browser = p.firefox.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        # Public pages first (no login).
        shoot(page, "/", "landing.png")
        shoot(page, "/login", "login.png")
        # Log in by setting the tokens the app itself uses.
        page.goto(BASE + "/login", wait_until="domcontentloaded")
        page.evaluate(
            "([a, r]) => { localStorage.setItem('asa_access_token', a); "
            "localStorage.setItem('asa_refresh_token', r); }",
            [access, refresh],
        )
        shoot(page, "/dashboard", "dashboard.png")
        shoot(page, "/upload", "upload.png")
        shoot(page, f"/chat?doc={BIO_DOC_ID}", "chat.png")
        shoot(page, f"/flashcards?doc={BIO_DOC_ID}", "flashcards.png")
        shoot(page, f"/quiz?doc={BIO_DOC_ID}", "quiz.png")
        shoot(page, "/planner", "planner.png")
        browser.close()
    print("done.")


if __name__ == "__main__":
    main()
