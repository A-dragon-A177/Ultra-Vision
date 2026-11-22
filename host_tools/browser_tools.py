"""
Playwright browser automation — runs natively on Windows.
Saves/reuses login sessions so Vision never stores passwords.
"""
from __future__ import annotations
import asyncio, os
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

SESSION_DIR = Path(r"C:\Vision\data\sessions")
SESSION_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR = Path(r"C:\Vision\data\downloads")
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

_browser: Browser | None = None
_pw = None


async def _get_browser(headless: bool = False) -> Browser:
    global _browser, _pw
    if _browser is None or not _browser.is_connected():
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-dev-shm-usage",
            ],
        )
    return _browser


async def _context(site: str, headless: bool = False) -> BrowserContext:
    browser = await _get_browser(headless)
    sf = SESSION_DIR / f"{site}.json"
    ctx = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        storage_state=str(sf) if sf.exists() else None,
        viewport={"width": 1280, "height": 800},
        accept_downloads=True,
    )
    return ctx


async def _save_ctx(ctx: BrowserContext, site: str):
    await ctx.storage_state(path=str(SESSION_DIR / f"{site}.json"))


# Site URLs for login
SITE_URLS = {
    "google": "https://accounts.google.com",
    "notebooklm": "https://notebooklm.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com/accounts/login/",
    "claude": "https://claude.ai/login",
    "reddit": "https://www.reddit.com/login",
    "chatgpt": "https://chat.openai.com/auth/login",
}


# ── Save login session ─────────────────────────────────────────────────────

async def save_login_session(site: str) -> dict:
    """Open browser for user to log in, then save session."""
    url = SITE_URLS.get(site, f"https://{site}.com")
    browser = await _get_browser(headless=False)
    ctx = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = await ctx.new_page()
    await page.goto(url)
    print(f"\n[Vision] Log into {site} in the browser window that opened.")
    print("[Vision] When done, press ENTER here to save your session...")
    await asyncio.get_event_loop().run_in_executor(None, input)
    await _save_ctx(ctx, site)
    if site == "google":
        await _save_ctx(ctx, "notebooklm")
    await ctx.close()
    return {"status": "saved", "site": site, "file": str(SESSION_DIR / f"{site}.json")}


# ── Open URL + screenshot ──────────────────────────────────────────────────

async def open_and_screenshot(url: str, site: str = "default") -> dict:
    ctx = await _context(site)
    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        ss = str(DOWNLOADS_DIR / "last_screenshot.png")
        await page.screenshot(path=ss, full_page=False)
        title = await page.title()
        await _save_ctx(ctx, site)
        await ctx.close()
        return {"status": "ok", "url": page.url, "title": title, "screenshot": ss}
    except Exception as e:
        try: await ctx.close()
        except: pass
        return {"status": "error", "message": str(e)}


# ── WhatsApp Web ───────────────────────────────────────────────────────────

async def whatsapp_post(community_or_group: str, message: str) -> dict:
    ctx = await _context("whatsapp")
    page = await ctx.new_page()
    try:
        await page.goto("https://web.whatsapp.com", wait_until="networkidle", timeout=40000)

        # QR scan needed?
        if await page.locator("canvas").count() > 0:
            await ctx.close()
            return {
                "status": "needs_qr",
                "message": "WhatsApp Web needs QR scan. Run: python save_session.py whatsapp",
            }

        await page.wait_for_selector("[data-testid='chat-list']", timeout=15000)

        # Search for the group/community
        search = page.get_by_placeholder("Search or start new chat")
        await search.click()
        await search.fill(community_or_group)
        await page.wait_for_timeout(2000)

        # Try exact match first, then partial
        result = page.locator(f"span[title='{community_or_group}']").first
        if not await result.is_visible(timeout=3000):
            result = page.get_by_text(community_or_group, exact=False).first

        if not await result.is_visible(timeout=3000):
            await ctx.close()
            return {"status": "not_found", "message": f"Group/community '{community_or_group}' not found"}

        await result.click()
        await page.wait_for_timeout(1000)

        # Type message
        msg_box = page.get_by_role("textbox", name="Type a message")
        await msg_box.click()
        # Use clipboard for multi-line messages
        await page.evaluate(f"navigator.clipboard.writeText({repr(message)})")
        await page.keyboard.press("Control+v")
        await page.wait_for_timeout(500)

        # Send
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2000)

        await _save_ctx(ctx, "whatsapp")
        await ctx.close()
        return {"status": "sent", "group": community_or_group, "chars": len(message)}
    except Exception as e:
        try: await ctx.close()
        except: pass
        return {"status": "error", "message": str(e)}


# ── NotebookLM ────────────────────────────────────────────────────────────

async def notebooklm_create_audio(script: str, title: str = "Vision AI") -> dict:
    # Save script to file so user can manually paste if automation fails
    script_file = Path(r"C:\Vision\brain\outputs\notebooklm-script.txt")
    script_file.parent.mkdir(parents=True, exist_ok=True)
    script_file.write_text(script, encoding="utf-8")

    ctx = await _context("google")
    page = await ctx.new_page()
    try:
        await page.goto("https://notebooklm.google.com", wait_until="networkidle", timeout=40000)

        if "accounts.google.com" in page.url:
            await ctx.close()
            return {
                "status": "needs_login",
                "message": "Google session expired. Run: python save_session.py google",
            }

        # Try to create new notebook
        new_btn = page.get_by_role("button", name="New notebook")
        try:
            await new_btn.wait_for(timeout=8000)
            await new_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)

            # Add script as pasted text source
            paste_btn = page.get_by_role("button", name="Paste text")
            if await paste_btn.is_visible(timeout=5000):
                await paste_btn.click()
                ta = page.locator("textarea").first
                await ta.fill(script[:50000])
                insert = page.get_by_role("button", name="Insert")
                await insert.click()
                await page.wait_for_load_state("networkidle", timeout=15000)

            # Try to generate Audio Overview
            gen = page.locator("button:has-text('Generate')").first
            if await gen.is_visible(timeout=5000):
                await gen.click()
                try:
                    await page.wait_for_selector("[aria-label*='Download']", timeout=300000)
                    link = await page.get_attribute("[aria-label*='Download']", "href") or ""
                    await _save_ctx(ctx, "google")
                    notebook_url = page.url
                    await ctx.close()
                    return {"status": "ready", "audio_url": link, "notebook_url": notebook_url}
                except Exception:
                    pass

        except Exception:
            pass

        notebook_url = page.url
        await _save_ctx(ctx, "google")
        await ctx.close()
        return {
            "status": "partial",
            "notebook_url": notebook_url,
            "script_file": str(script_file),
            "message": (
                f"Notebook opened at {notebook_url}. "
                "Script saved to brain/outputs/notebooklm-script.txt. "
                "Click 'Paste text', paste the script, then click Generate > Audio Overview."
            ),
        }
    except Exception as e:
        try: await ctx.close()
        except: pass
        return {"status": "error", "script_file": str(script_file), "message": str(e)}
