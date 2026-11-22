"""
Video creation for Instagram Reels.
Pipeline: script text → edge-tts audio → ffmpeg video → Instagram upload.
Requires: ffmpeg in PATH or at C:\ffmpeg\bin\ffmpeg.exe
"""
from __future__ import annotations
import asyncio, json, os, shutil, subprocess, time
from pathlib import Path
from typing import Optional

ROOT = Path(r"C:\Vision")
VIDEO_DIR = ROOT / "data" / "videos"
TEMP_DIR = ROOT / "data" / "video_temp"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE = shutil.which("ffprobe") or r"C:\ffmpeg\bin\ffprobe.exe"


# ── Audio generation ──────────────────────────────────────────────────────

async def _make_audio(text: str, voice: str = "en-GB-RyanNeural",
                      rate: str = "+5%", pitch: str = "+0Hz") -> str:
    import edge_tts
    out = str(TEMP_DIR / f"audio_{int(time.time())}.mp3")
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    with open(out, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
    return out


def _audio_duration(path: str) -> float:
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "json", path],
        capture_output=True, text=True
    )
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 30.0


# ── Video styles ──────────────────────────────────────────────────────────

STYLES = {
    "minimal": {"bg": "0x000d1a", "accent": "00d4ff", "text": "e8f4f8"},
    "branded": {"bg": "0x0a0014", "accent": "9b59b6", "text": "ffffff"},
    "cinematic": {"bg": "0x1a0a00", "accent": "ff6b35", "text": "fff8f0"},
    "dark": {"bg": "0x030303", "accent": "00ff88", "text": "f0f0f0"},
}


def _build_video(audio_path: str, title: str, script: str,
                 output_path: str, style: str = "branded") -> str:
    """Create Instagram Reel (1080x1920) with text overlay + audio."""
    s = STYLES.get(style, STYLES["branded"])
    duration = _audio_duration(audio_path) + 1.0

    # Sanitize text for ffmpeg drawtext (escape special chars)
    def esc(t: str) -> str:
        return (t[:60]
                .replace("'", "")
                .replace(":", "\\:")
                .replace("\\", "/")
                .replace("%", "\\%")
                .replace("[", "")
                .replace("]", ""))

    safe_title = esc(title)
    # Subtitle: first 50 chars of script
    safe_sub = esc(script[:55] + ("..." if len(script) > 55 else ""))

    font_bold = r"C\:/Windows/Fonts/arialbd.ttf"
    font_reg = r"C\:/Windows/Fonts/arial.ttf"

    # Build filter: gradient bg + title + subtitle + branding
    vf = (
        # Background gradient using geq
        f"color=c=black:size=1080x1920:rate=30,"
        f"geq=r='if(lt(Y,960),{int(s[\"bg\"][2:4] or \"00\", 16) if len(s[\"bg\"]) > 4 else 0}+(Y/960)*20,20)'"
        f":g='if(lt(Y,960),{int(s[\"bg\"][4:6] or \"0d\", 16) if len(s[\"bg\"]) > 4 else 13}+(Y/960)*5,5)'"
        f":b='if(lt(Y,960),{int(s[\"bg\"][6:8] or \"1a\", 16) if len(s[\"bg\"]) > 6 else 26}+(Y/960)*10,10)',"
        # Brand bar at top
        f"drawbox=x=0:y=0:w=1080:h=8:color=0x{s['accent']}:t=fill,"
        # Brand bar at bottom
        f"drawbox=x=0:y=1912:w=1080:h=8:color=0x{s['accent']}:t=fill,"
        # Title
        f"drawtext=text='{safe_title}':x=(w-text_w)/2:y=320:"
        f"fontsize=72:fontcolor=0x{s['accent']}:fontfile='{font_bold}':"
        f"shadowcolor=black:shadowx=3:shadowy=3,"
        # Subtitle / hook
        f"drawtext=text='{safe_sub}':x=60:y=460:"
        f"fontsize=44:fontcolor=0x{s['text']}:fontfile='{font_reg}':"
        f"line_spacing=12:shadowcolor=black@0.6:shadowx=2:shadowy=2,"
        # Neesh AI watermark
        f"drawtext=text='Neesh AI':x=(w-text_w)/2:y=h-80:"
        f"fontsize=38:fontcolor=0x{s['accent']}@0.85:fontfile='{font_bold}':"
        f"shadowcolor=black:shadowx=2:shadowy=2"
    )

    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi", "-i", vf,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[:600]}")
    return output_path


# ── Public API ─────────────────────────────────────────────────────────────

async def create_reel(script: str, title: str = "Neesh AI",
                      style: str = "branded",
                      output_name: Optional[str] = None) -> dict:
    if not (shutil.which("ffmpeg") or Path(FFMPEG).exists()):
        return {
            "status": "error",
            "message": (
                "ffmpeg not found. Download from https://ffmpeg.org/download.html "
                "and add it to PATH or place it at C:\\ffmpeg\\bin\\ffmpeg.exe"
            ),
        }
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        audio = await _make_audio(script)
        name = output_name or f"reel_{int(time.time())}.mp4"
        out = str(VIDEO_DIR / name)
        _build_video(audio, title, script, out, style)
        Path(audio).unlink(missing_ok=True)
        size_mb = round(Path(out).stat().st_size / 1024 / 1024, 1)
        return {"status": "ready", "video_path": out, "size_mb": size_mb, "title": title}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def upload_instagram(video_path: str, caption: str) -> dict:
    if not Path(video_path).exists():
        return {"status": "error", "message": f"Video not found: {video_path}"}

    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    user_id = os.environ.get("INSTAGRAM_USER_ID", "")
    r2_base = os.environ.get("CLOUDFLARE_R2_PUBLIC_URL", "").rstrip("/")

    if token and user_id and r2_base:
        # Upload to R2 then use Graph API
        try:
            import httpx, boto3
            bucket = os.environ.get("CLOUDFLARE_R2_BUCKET", "vision-videos")
            account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
            s3 = boto3.client(
                "s3",
                endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=os.environ.get("CLOUDFLARE_R2_ACCESS_KEY", ""),
                aws_secret_access_key=os.environ.get("CLOUDFLARE_R2_SECRET_KEY", ""),
                region_name="auto",
            )
            fname = Path(video_path).name
            s3.upload_file(video_path, bucket, fname, ExtraArgs={"ContentType": "video/mp4"})
            video_url = f"{r2_base}/{fname}"

            async with httpx.AsyncClient(timeout=120) as client:
                # Create container
                r = await client.post(
                    f"https://graph.facebook.com/v18.0/{user_id}/media",
                    params={"media_type": "REELS", "video_url": video_url,
                            "caption": caption, "access_token": token},
                )
                if r.status_code != 200:
                    return {"status": "error", "step": "container", "detail": r.text}
                cid = r.json()["id"]

                # Poll for processing
                for _ in range(30):
                    await asyncio.sleep(10)
                    s = await client.get(
                        f"https://graph.facebook.com/v18.0/{cid}",
                        params={"fields": "status_code", "access_token": token},
                    )
                    sc = s.json().get("status_code", "")
                    if sc == "FINISHED":
                        break
                    if sc == "ERROR":
                        return {"status": "error", "step": "processing"}

                # Publish
                p = await client.post(
                    f"https://graph.facebook.com/v18.0/{user_id}/media_publish",
                    params={"creation_id": cid, "access_token": token},
                )
                if p.status_code == 200:
                    post_id = p.json().get("id", "")
                    return {"status": "published", "post_id": post_id,
                            "url": f"https://www.instagram.com/reel/{post_id}/"}
                return {"status": "error", "step": "publish", "detail": p.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # Fallback: open Instagram for manual upload
    import webbrowser
    webbrowser.open("https://www.instagram.com")
    return {
        "status": "manual",
        "video_path": video_path,
        "caption": caption,
        "message": (
            f"Video ready at {video_path} ({round(Path(video_path).stat().st_size / 1024 / 1024, 1)} MB). "
            "Instagram opened. Upload manually, OR configure CLOUDFLARE_R2 + INSTAGRAM credentials in .env for auto-posting."
        ),
    }
