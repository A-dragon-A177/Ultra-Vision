"""
Vision Host Tools Server — runs NATIVELY on Windows (not in Docker).
Docker calls this via http://host.docker.internal:8081

Start: python server.py   (or double-click start.bat)
"""
from __future__ import annotations
import os, subprocess, sys, webbrowser
from pathlib import Path
from typing import Optional

# Load Vision .env so this service shares the same credentials
_env_file = Path(r"C:\Vision\.env")
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Vision Host Tools", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ROOT = Path(r"C:\Vision")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "root": str(ROOT)}


# ── Computer control ──────────────────────────────────────────────────────────

class RunCmd(BaseModel):
    cmd: str
    cwd: Optional[str] = None
    timeout: int = 30

@app.post("/computer/run")
def computer_run(body: RunCmd):
    try:
        r = subprocess.run(
            body.cmd, shell=True, capture_output=True, text=True,
            cwd=body.cwd or str(ROOT), timeout=body.timeout
        )
        return {"stdout": r.stdout[:5000], "stderr": r.stderr[:2000], "code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "code": -1}
    except Exception as e:
        return {"error": str(e), "code": -1}

class FileOp(BaseModel):
    path: str
    content: Optional[str] = None

@app.post("/computer/file/read")
def file_read(body: FileOp):
    try:
        p = Path(body.path)
        if not p.exists():
            return {"error": f"Not found: {body.path}"}
        txt = p.read_text(encoding="utf-8", errors="replace")
        return {"content": txt[:60000], "size": p.stat().st_size, "truncated": len(txt) > 60000}
    except Exception as e:
        return {"error": str(e)}

@app.post("/computer/file/write")
def file_write(body: FileOp):
    try:
        p = Path(body.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body.content or "", encoding="utf-8")
        return {"ok": True, "path": str(p)}
    except Exception as e:
        return {"error": str(e)}

class OpenTarget(BaseModel):
    target: str

@app.post("/computer/open")
def computer_open(body: OpenTarget):
    try:
        if body.target.startswith("http"):
            webbrowser.open(body.target)
        else:
            os.startfile(body.target)
        return {"ok": True, "opened": body.target}
    except Exception as e:
        return {"error": str(e)}

class ListDir(BaseModel):
    path: str

@app.post("/computer/ls")
def list_dir(body: ListDir):
    try:
        p = Path(body.path)
        entries = [{"name": x.name, "is_dir": x.is_dir()} for x in p.iterdir()]
        return {"path": str(p), "entries": entries[:300]}
    except Exception as e:
        return {"error": str(e)}


# ── Browser automation ────────────────────────────────────────────────────────

class WhatsAppBody(BaseModel):
    community_name: str
    message: str

@app.post("/browser/whatsapp")
async def browser_whatsapp(body: WhatsAppBody):
    from browser_tools import whatsapp_post
    return await whatsapp_post(body.community_name, body.message)

class NotebookBody(BaseModel):
    script: str
    title: str = "Vision AI"

@app.post("/browser/notebooklm")
async def browser_notebooklm(body: NotebookBody):
    from browser_tools import notebooklm_create_audio
    return await notebooklm_create_audio(body.script, body.title)

class BrowserOpenBody(BaseModel):
    url: str
    site: str = "default"

@app.post("/browser/open")
async def browser_open(body: BrowserOpenBody):
    from browser_tools import open_and_screenshot
    return await open_and_screenshot(body.url, body.site)

class SessionBody(BaseModel):
    site: str

@app.post("/browser/save-session")
async def save_session_endpoint(body: SessionBody):
    from browser_tools import save_login_session
    return await save_login_session(body.site)


# ── Video pipeline ────────────────────────────────────────────────────────────

class VideoBody(BaseModel):
    script: str
    title: str = "Neesh AI"
    style: str = "branded"
    output_name: Optional[str] = None

@app.post("/video/create")
async def video_create(body: VideoBody):
    from video_tools import create_reel
    return await create_reel(body.script, body.title, body.style, body.output_name)

class UploadBody(BaseModel):
    video_path: str
    caption: str

@app.post("/video/upload-instagram")
async def video_upload(body: UploadBody):
    from video_tools import upload_instagram
    return await upload_instagram(body.video_path, body.caption)


# ── Reddit ────────────────────────────────────────────────────────────────────

class RedditPostBody(BaseModel):
    subreddit: str
    title: str
    content: str
    url: Optional[str] = None

@app.post("/reddit/post")
async def reddit_post_ep(body: RedditPostBody):
    from reddit_tools import submit_post
    return await submit_post(body.subreddit, body.title, body.content, body.url)

class RedditCommentBody(BaseModel):
    post_url: str
    comment: str

@app.post("/reddit/comment")
async def reddit_comment_ep(body: RedditCommentBody):
    from reddit_tools import post_comment
    return await post_comment(body.post_url, body.comment)

class RedditTrendingBody(BaseModel):
    subreddits: list = ["artificial", "MachineLearning", "AIpromptEngineering", "singularity"]
    limit: int = 5

@app.post("/reddit/trending")
async def reddit_trending_ep(body: RedditTrendingBody):
    from reddit_tools import get_trending
    return await get_trending(body.subreddits, body.limit)

@app.post("/reddit/opportunities")
async def reddit_opportunities_ep():
    from reddit_tools import find_opportunities
    return await find_opportunities()


if __name__ == "__main__":
    print("[Vision Host Tools] Starting on http://0.0.0.0:8081")
    print("[Vision Host Tools] Docker calls this via http://host.docker.internal:8081")
    uvicorn.run(app, host="0.0.0.0", port=8081, log_level="info")
