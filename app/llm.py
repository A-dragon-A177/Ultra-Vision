"""Model access for Vision.

Priority order:
  1. Groq (groq.com) — primary brain, rotates across up to 3 keys
     Default model: llama-3.3-70b-versatile (free tier, very fast)
  2. Gemini Flash (Google) — free fallback, also handles voice transcription + web search
  3. Ollama — offline fallback

Set GROK_API_KEY_1 (and optionally _2, _3) in .env to activate Groq.
Gemini is still recommended as a fallback even if you use Groq — it is free.
"""
import asyncio
import base64
import os
import re

import httpx

# ── Grok (xAI) ────────────────────────────────────────────────────────────────

_grok_key_idx = 0


def _grok_keys():
    return [
        k for k in [
            os.environ.get("GROK_API_KEY_1", "").strip(),
            os.environ.get("GROK_API_KEY_2", "").strip(),
            os.environ.get("GROK_API_KEY_3", "").strip(),
        ] if k
    ]


def _next_grok_key():
    global _grok_key_idx
    keys = _grok_keys()
    if not keys:
        return None
    key = keys[_grok_key_idx % len(keys)]
    _grok_key_idx = (_grok_key_idx + 1) % len(keys)
    return key


async def _grok(system, messages):
    """Groq API (OpenAI-compatible). Rotates across up to 3 keys to spread rate limits."""
    key = _next_grok_key()
    if not key:
        raise RuntimeError("No GROK_API_KEY_1 set")
    model = os.environ.get("GROK_MODEL", "llama-3.3-70b-versatile")
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    body = {"model": model, "messages": msgs}
    async with httpx.AsyncClient(timeout=120) as client:
        for attempt in range(len(_grok_keys()) or 1):
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code == 429:
                # This key is rate-limited — rotate to the next one and retry
                key = _next_grok_key() or key
                await asyncio.sleep(2)
                continue
            if r.status_code in (500, 503) and attempt < 2:
                await asyncio.sleep(5)
                continue
            r.raise_for_status()
            break
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()


# ── Gemini (Google) ───────────────────────────────────────────────────────────

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_picked_model = None


def _gemini_key():
    return os.environ.get("GEMINI_API_KEY", "").strip()


async def _pick_gemini_model(client):
    global _picked_model
    if os.environ.get("GEMINI_MODEL", "").strip():
        return os.environ["GEMINI_MODEL"].strip()
    if _picked_model:
        return _picked_model
    r = await client.get(f"{GEMINI_BASE}/models", headers={"x-goog-api-key": _gemini_key()},
                         params={"pageSize": 200})
    r.raise_for_status()
    best = None
    for m in r.json().get("models", []):
        name = m.get("name", "").split("/")[-1]
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        if not re.fullmatch(r"gemini-\d+(\.\d+)?-flash", name):
            continue
        version = float(re.search(r"gemini-(\d+(?:\.\d+)?)", name).group(1))
        if best is None or version > best[0]:
            best = (version, name)
    if not best:
        raise RuntimeError("No Gemini Flash model found. Set GEMINI_MODEL in .env.")
    _picked_model = best[1]
    return _picked_model


async def _gemini(system, contents, search=False):
    async with httpx.AsyncClient(timeout=180) as client:
        model = await _pick_gemini_model(client)
        body = {"contents": contents}
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}
        if search:
            body["tools"] = [{"google_search": {}}]
        for attempt in range(3):
            r = await client.post(
                f"{GEMINI_BASE}/models/{model}:generateContent",
                headers={"x-goog-api-key": _gemini_key()},
                json=body,
            )
            if r.status_code in (429, 500, 503) and attempt < 2:
                await asyncio.sleep(8 * (attempt + 1))
                continue
            if r.status_code == 400 and search:
                text = await _gemini(system, contents, search=False)
                return text + "\n\n(Note: live web search was not available.)"
            r.raise_for_status()
            break
    data = r.json()
    try:
        cand = data["candidates"][0]
        parts = cand["content"]["parts"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Gemini returned no answer: {str(data)[:300]}")
    text = "".join(p.get("text", "") for p in parts).strip()
    seen, links = set(), []
    for ch in (cand.get("groundingMetadata") or {}).get("groundingChunks", []):
        web = ch.get("web") or {}
        if web.get("uri") and web["uri"] not in seen:
            seen.add(web["uri"])
            links.append(f"- {web.get('title', 'source')}: {web['uri']}")
    if links:
        text += "\n\nSources:\n" + "\n".join(links[:8])
    return text


# ── Ollama (offline) ──────────────────────────────────────────────────────────

async def _ollama(system, messages):
    url = os.environ["OLLAMA_URL"].rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    async with httpx.AsyncClient(timeout=600) as client:
        r = await client.post(f"{url}/api/chat", json={"model": model, "messages": msgs, "stream": False})
        r.raise_for_status()
        return r.json()["message"]["content"].strip()


# ── Main entry point ──────────────────────────────────────────────────────────

async def chat(system, messages, search=False, quality=False):
    """Route a chat request through available models.

    Priority: Grok → Gemini (supports live web search) → Ollama.
    search=True: uses Gemini's grounded search even if Grok is available.
    quality=True: prefers Grok (already the default) — kept for compatibility.
    """
    errors = []

    # Web search requests go to Gemini (has Google grounding built in)
    if search and _gemini_key():
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ]
        try:
            return await _gemini(system, contents, search=True)
        except Exception as e:
            errors.append(f"Gemini search: {e}")
            # Fall through to Grok without search

    # Grok — primary brain
    if _grok_keys():
        try:
            return await _grok(system, messages)
        except Exception as e:
            errors.append(f"Grok: {e}")

    # Gemini — free fallback
    if _gemini_key():
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ]
        try:
            return await _gemini(system, contents)
        except Exception as e:
            errors.append(f"Gemini: {e}")

    # Ollama — offline fallback
    if os.environ.get("OLLAMA_URL", "").strip():
        try:
            return await _ollama(system, messages)
        except Exception as e:
            errors.append(f"Ollama: {e}")

    raise RuntimeError("No brain available. " + " | ".join(errors))


# ── Voice transcription ───────────────────────────────────────────────────────

async def transcribe(audio_bytes, mime_type="audio/ogg"):
    """Voice note → text. Uses Gemini (supports Tamil, English, Hindi natively)."""
    if not _gemini_key():
        raise RuntimeError("Voice notes need GEMINI_API_KEY (free at aistudio.google.com).")
    contents = [{
        "role": "user",
        "parts": [
            {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(audio_bytes).decode()}},
            {"text": "Transcribe this voice note exactly as spoken, in the language(s) spoken "
                     "(English, Tamil, Hindi or a mix). Output only the transcript."},
        ],
    }]
    return await _gemini("", contents)


# ── Phone alert ───────────────────────────────────────────────────────────────

async def call_founder():
    """Ring via CallMeBot when an agent needs a decision. Set CALLMEBOT_USER in .env."""
    user = os.environ.get("CALLMEBOT_USER", "").strip()
    if not user:
        return False
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.get("https://api.callmebot.com/start.php", params={
                "user": user, "text": "Vision needs your decision. Please check Telegram.",
                "lang": "en-GB-Standard-B", "rpt": 2})
        return True
    except Exception:
        return False
