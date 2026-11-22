"""Instagram posting for Vision.

Primary path: Meta Graph API (official, never breaks).
Fallback: Playwright browser automation.

SETUP (one time, 20 minutes):
1. Go to developers.facebook.com → My Apps → Create App → Business
2. Add product: Instagram Graph API
3. Connect your Instagram professional account (must be Creator or Business)
4. Generate a long-lived token (Tools > Access Token Tool > Generate User Token,
   select instagram_basic, instagram_content_publish, pages_read_engagement)
5. Add to .env:
      INSTAGRAM_ACCESS_TOKEN=...
      INSTAGRAM_USER_ID=...   (your numeric Instagram user ID, shown in the token tool)

For Reels: the video must be accessible via a public URL.
The simplest free option: upload to Cloudflare R2 (free tier) or put it in a public GitHub release.
"""
import asyncio
import os
from pathlib import Path

import httpx

GRAPH_BASE = "https://graph.facebook.com/v18.0"


def _token():
    return os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()


def _user_id():
    return os.environ.get("INSTAGRAM_USER_ID", "").strip()


def is_configured() -> bool:
    return bool(_token() and _user_id())


async def post_reel(video_url: str, caption: str, cover_url: str = "") -> dict:
    """
    Post a Reel using the Meta Graph API.
    video_url must be a publicly accessible URL (https://).
    Returns {"status": "published", "post_id": "..."} or {"status": "error", "message": "..."}
    """
    if not is_configured():
        return {
            "status": "not_configured",
            "message": (
                "Instagram Graph API is not set up. "
                "Add INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID to .env. "
                "See app/instagram.py for the 5-step setup."
            ),
        }

    async with httpx.AsyncClient(timeout=120) as client:
        # Step 1: Create a media container
        params = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": _token(),
        }
        if cover_url:
            params["cover_url"] = cover_url

        r = await client.post(f"{GRAPH_BASE}/{_user_id()}/media", params=params)
        if r.status_code != 200:
            return {"status": "error", "message": f"Container creation failed: {r.text}"}

        container_id = r.json().get("id")

        # Step 2: Poll until processing is complete (up to 5 minutes)
        for _ in range(30):
            await asyncio.sleep(10)
            status_r = await client.get(
                f"{GRAPH_BASE}/{container_id}",
                params={"fields": "status_code", "access_token": _token()},
            )
            status_code = status_r.json().get("status_code", "")
            if status_code == "FINISHED":
                break
            if status_code == "ERROR":
                return {"status": "error", "message": "Video processing failed on Instagram's side"}
        else:
            return {"status": "error", "message": "Video processing timed out after 5 minutes"}

        # Step 3: Publish
        pub_r = await client.post(
            f"{GRAPH_BASE}/{_user_id()}/media_publish",
            params={"creation_id": container_id, "access_token": _token()},
        )
        if pub_r.status_code != 200:
            return {"status": "error", "message": f"Publish failed: {pub_r.text}"}

        post_id = pub_r.json().get("id")
        return {"status": "published", "post_id": post_id,
                "url": f"https://www.instagram.com/p/{post_id}/"}


async def post_reel_via_browser(video_path: str, caption: str) -> dict:
    """
    Fallback: upload a Reel using the browser when the Graph API isn't set up.
    video_path is a local file path.
    """
    try:
        from . import browser
    except ImportError:
        return {"status": "error", "message": "Browser module not available"}

    ctx = await browser._context("instagram")
    page = await ctx.new_page()

    try:
        await page.goto("https://www.instagram.com", wait_until="networkidle", timeout=30000)

        if "login" in page.url:
            await ctx.close()
            return {
                "status": "needs_login",
                "message": "Instagram session expired. Run: python save_session.py instagram",
            }

        # Click the new post button
        new_post = page.get_by_role("link", name="New post")
        if not await new_post.is_visible(timeout=5000):
            new_post = page.locator("[aria-label='New post']")

        await new_post.click()
        await page.wait_for_timeout(1500)

        # Upload the video file
        file_input = page.locator("input[type='file']")
        await file_input.set_input_files(video_path)
        await page.wait_for_timeout(2000)

        # Click through the upload flow (crop → filters → details)
        for _ in range(3):
            next_btn = page.get_by_role("button", name="Next")
            if await next_btn.is_visible(timeout=3000):
                await next_btn.click()
                await page.wait_for_timeout(1500)

        # Add caption
        caption_box = page.get_by_placeholder("Write a caption...")
        if await caption_box.is_visible(timeout=5000):
            await caption_box.fill(caption)

        await browser._save_context(ctx, "instagram")
        await ctx.close()
        return {
            "status": "ready_to_share",
            "message": "Video uploaded, caption added. Click Share on Instagram to publish.",
        }

    except Exception as e:
        await ctx.close()
        return {"status": "error", "message": str(e)}
