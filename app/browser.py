"""
Browser automation for Vision.
All Playwright calls are routed to the Windows host tools server
(http://host.docker.internal:8081) because Docker has no display.

Passwords are never stored. Users log in once via save_session.py.
"""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(os.environ.get("VISION_HOME", Path(__file__).resolve().parent.parent))
_HOST = os.environ.get("HOST_TOOLS_URL", "http://host.docker.internal:8081")


async def _post(path: str, payload: dict) -> dict:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(f"{_HOST}{path}", json=payload)
            return r.json()
    except Exception as e:
        return {"status": "error", "message": f"Host tools unreachable: {e}. Is host_tools/start.bat running?"}


# ── Public API (matches the original function names used by core.py procedures) ──

async def notebooklm_create_audio(script: str, notebook_title: str = "Vision Reel") -> dict:
    """Create a NotebookLM Audio Overview from a script."""
    return await _post("/browser/notebooklm", {"script": script, "title": notebook_title})


async def whatsapp_post_to_community(community_name: str, message: str) -> dict:
    """Post a message to a WhatsApp community or group."""
    return await _post("/browser/whatsapp", {"community_name": community_name, "message": message})


async def open_tab(url: str, site: str = "default") -> dict:
    """Open a URL in the browser and get a screenshot."""
    return await _post("/browser/open", {"url": url, "site": site})


async def save_session(site: str) -> dict:
    """Save a browser login session for a site (opens browser for manual login)."""
    return await _post("/browser/save-session", {"site": site})


# Legacy alias kept for existing procedures
async def claude_chat_in_session(chat_title_keyword: str, message: str) -> dict:
    """Route to host tools — opens Claude.ai with saved Google session."""
    return await _post("/browser/open", {
        "url": f"https://claude.ai",
        "site": "claude",
    })
