"""
HTTP client that calls the Windows host tools server from inside Docker.
All tool calls go to http://host.docker.internal:8081
"""
from __future__ import annotations
import asyncio, json, os
from typing import Any, Optional

HOST_URL = os.environ.get("HOST_TOOLS_URL", "http://host.docker.internal:8081")
_timeout = 120  # seconds


async def _post(path: str, payload: dict) -> dict:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=_timeout) as client:
            r = await client.post(f"{HOST_URL}{path}", json=payload)
            return r.json()
    except Exception as e:
        return {"status": "error", "message": f"Host tools unreachable: {e}. Is C:\\Vision\\host_tools\\start.bat running?"}


async def _get(path: str) -> dict:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{HOST_URL}{path}")
            return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Health check ──────────────────────────────────────────────────────────

async def health() -> dict:
    return await _get("/health")


# ── Computer control ──────────────────────────────────────────────────────

async def run_command(cmd: str, cwd: Optional[str] = None, timeout: int = 30) -> dict:
    """Run a shell command on the Windows host."""
    return await _post("/computer/run", {"cmd": cmd, "cwd": cwd, "timeout": timeout})


async def read_file(path: str) -> dict:
    """Read a file from the Windows host filesystem."""
    return await _post("/computer/file/read", {"path": path})


async def write_file(path: str, content: str) -> dict:
    """Write a file on the Windows host filesystem."""
    return await _post("/computer/file/write", {"path": path, "content": content})


async def open_app(target: str) -> dict:
    """Open a URL in the browser or launch a Windows app."""
    return await _post("/computer/open", {"target": target})


async def list_dir(path: str) -> dict:
    """List directory contents on the Windows host."""
    return await _post("/computer/ls", {"path": path})


# ── Browser automation ────────────────────────────────────────────────────

async def whatsapp_post(community_name: str, message: str) -> dict:
    """Post a message to a WhatsApp community or group."""
    return await _post("/browser/whatsapp", {"community_name": community_name, "message": message})


async def notebooklm_audio(script: str, title: str = "Vision AI") -> dict:
    """Create a NotebookLM Audio Overview from a script."""
    return await _post("/browser/notebooklm", {"script": script, "title": title})


async def browser_open(url: str, site: str = "default") -> dict:
    """Open a URL in the browser and get a screenshot."""
    return await _post("/browser/open", {"url": url, "site": site})


async def save_session(site: str) -> dict:
    """Save a browser login session for a site."""
    return await _post("/browser/save-session", {"site": site})


# ── Video creation ────────────────────────────────────────────────────────

async def create_reel(script: str, title: str = "Neesh AI",
                      style: str = "branded", output_name: Optional[str] = None) -> dict:
    """Create an Instagram Reel (1080x1920 MP4) from a script."""
    return await _post("/video/create", {
        "script": script, "title": title, "style": style, "output_name": output_name
    })


async def upload_instagram(video_path: str, caption: str) -> dict:
    """Upload a video to Instagram as a Reel."""
    return await _post("/video/upload-instagram", {"video_path": video_path, "caption": caption})


# ── Reddit ────────────────────────────────────────────────────────────────

async def reddit_post(subreddit: str, title: str, content: str,
                      url: Optional[str] = None) -> dict:
    """Post to a subreddit."""
    return await _post("/reddit/post", {"subreddit": subreddit, "title": title,
                                         "content": content, "url": url})


async def reddit_comment(post_url: str, comment: str) -> dict:
    """Comment on a Reddit post."""
    return await _post("/reddit/comment", {"post_url": post_url, "comment": comment})


async def reddit_trending(subreddits: list = None, limit: int = 5) -> dict:
    """Get trending posts from AI/startup subreddits."""
    return await _post("/reddit/trending", {
        "subreddits": subreddits or ["artificial", "MachineLearning", "AIpromptEngineering", "singularity"],
        "limit": limit,
    })


async def reddit_opportunities() -> dict:
    """Find Reddit posts where Neesh AI could add value."""
    return await _post("/reddit/opportunities", {})


# ── Tool registry (used by core.py for the ReAct loop) ───────────────────

TOOL_REGISTRY = {
    # Computer
    "computer.run": (run_command, "run_command(cmd, cwd?, timeout?)"),
    "computer.read_file": (read_file, "read_file(path)"),
    "computer.write_file": (write_file, "write_file(path, content)"),
    "computer.open": (open_app, "open_app(target)"),
    "computer.ls": (list_dir, "list_dir(path)"),
    # Browser
    "browser.whatsapp": (whatsapp_post, "whatsapp_post(community_name, message)"),
    "browser.notebooklm": (notebooklm_audio, "notebooklm_audio(script, title?)"),
    "browser.open": (browser_open, "browser_open(url, site?)"),
    "browser.save_session": (save_session, "save_session(site)"),
    # Video
    "video.create_reel": (create_reel, "create_reel(script, title?, style?, output_name?)"),
    "video.upload_instagram": (upload_instagram, "upload_instagram(video_path, caption)"),
    # Reddit
    "reddit.post": (reddit_post, "reddit_post(subreddit, title, content, url?)"),
    "reddit.comment": (reddit_comment, "reddit_comment(post_url, comment)"),
    "reddit.trending": (reddit_trending, "reddit_trending(subreddits?, limit?)"),
    "reddit.opportunities": (reddit_opportunities, "reddit_opportunities()"),
}

TOOL_DESCRIPTIONS = """
# Available tools (use TOOL_CALL: module.function(args) to invoke)

## Computer control
- TOOL_CALL: computer.run(cmd="<shell command>") — run a Windows shell command
- TOOL_CALL: computer.read_file(path="<path>") — read any file on Windows
- TOOL_CALL: computer.write_file(path="<path>", content="<text>") — write a file
- TOOL_CALL: computer.open(target="<URL or app path>") — open URL or app
- TOOL_CALL: computer.ls(path="<directory>") — list directory contents

## Browser automation
- TOOL_CALL: browser.whatsapp(community_name="<group>", message="<text>") — post to WhatsApp
- TOOL_CALL: browser.notebooklm(script="<text>", title="<title>") — create NotebookLM audio
- TOOL_CALL: browser.open(url="<URL>") — open URL and screenshot

## Video creation
- TOOL_CALL: video.create_reel(script="<narration>", title="<title>") — make Instagram Reel MP4
- TOOL_CALL: video.upload_instagram(video_path="<path>", caption="<text>") — post to Instagram

## Reddit growth
- TOOL_CALL: reddit.post(subreddit="<sub>", title="<title>", content="<body>") — post to Reddit
- TOOL_CALL: reddit.comment(post_url="<url>", comment="<text>") — comment on a post
- TOOL_CALL: reddit.trending() — get trending AI posts
- TOOL_CALL: reddit.opportunities() — find posts to helpfully engage with
"""
