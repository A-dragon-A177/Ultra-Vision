"""Vision TTS — Microsoft Edge Neural TTS (free, no API key).

Voices per agent:
  vision   → en-GB-RyanNeural        (British male, deep/authoritative)
  jarvis   → en-GB-ThomasNeural      (British male, warmer)
  ultron   → en-US-ChristopherNeural (American male, cold/commanding)
  zola     → en-US-EricNeural        (American male, different cadence)
  jim      → en-AU-WilliamNeural     (Australian male)
  friday   → en-US-AriaNeural        (US female, natural)
  edith    → en-GB-SoniaNeural       (British female, authoritative)
  veronica → en-US-JennyNeural       (US female, warm)
  jocasta  → en-AU-NatashaNeural     (Australian female)
  herbie   → en-US-AnaNeural         (lighter/faster, bot-like)
  Tamil    → ta-IN-ValluvarNeural    (auto-detected from Unicode U+0B80-U+0BFF)
"""
import io
import os
import re

import edge_tts

AGENT_VOICES = {
    "vision":   {"voice": "en-GB-RyanNeural",        "rate": "-12%", "pitch": "-4Hz"},
    "jarvis":   {"voice": "en-GB-ThomasNeural",       "rate": "-8%",  "pitch": "-2Hz"},
    "ultron":   {"voice": "en-US-ChristopherNeural",  "rate": "-8%",  "pitch": "-6Hz"},
    "zola":     {"voice": "en-US-EricNeural",         "rate": "+3%",  "pitch": "+3Hz"},
    "jim":      {"voice": "en-AU-WilliamNeural",      "rate": "-5%",  "pitch": "0Hz"},
    "friday":   {"voice": "en-US-AriaNeural",         "rate": "-5%",  "pitch": "+2Hz"},
    "edith":    {"voice": "en-GB-SoniaNeural",        "rate": "-8%",  "pitch": "+2Hz"},
    "veronica": {"voice": "en-US-JennyNeural",        "rate": "-5%",  "pitch": "+2Hz"},
    "jocasta":  {"voice": "en-AU-NatashaNeural",      "rate": "-5%",  "pitch": "+2Hz"},
    "herbie":   {"voice": "en-US-GuyNeural",           "rate": "+35%", "pitch": "+18Hz"},
}

_DEFAULT_VOICE = AGENT_VOICES["vision"]
_TAMIL_VOICE   = "ta-IN-ValluvarNeural"
_TAMIL_RE      = re.compile(r"[஀-௿]")


def _is_tamil(text: str) -> bool:
    return bool(_TAMIL_RE.search(text))


def _clean_for_tts(text: str) -> str:
    """Strip markdown and symbols that TTS reads literally (hashtag, asterisk, etc.)."""
    # Bold / italic / strikethrough
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text, flags=re.S)
    text = re.sub(r'_{1,2}(.+?)_{1,2}', r'\1', text, flags=re.S)
    text = re.sub(r'~~(.+?)~~', r'\1', text, flags=re.S)
    # Inline code
    text = re.sub(r'`+(.+?)`+', r'\1', text, flags=re.S)
    # Markdown headers  (#, ##, ###…)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.M)
    # Horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.M)
    # URLs → "link"
    text = re.sub(r'https?://\S+', 'link', text)
    # Markdown links → keep anchor text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # List markers (-, *, +, •)
    text = re.sub(r'^[\s]*[-*+•]\s+', '', text, flags=re.M)
    # Leftover lone special chars that TTS vocalises
    text = re.sub(r'[*#_~`\\]', '', text)
    # Normalise whitespace
    text = re.sub(r'\n{2,}', '. ', text)
    text = re.sub(r'\n', ', ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


async def synthesize(text: str, agent: str = "vision") -> bytes:
    if _is_tamil(text):
        voice = os.environ.get("TTS_VOICE_TAMIL", _TAMIL_VOICE).strip() or _TAMIL_VOICE
        rate  = "+0%"
        pitch = "+0Hz"
    else:
        cfg   = AGENT_VOICES.get(agent.lower(), _DEFAULT_VOICE)
        voice = cfg["voice"]
        rate  = cfg["rate"]
        pitch = cfg["pitch"]
        # allow .env overrides only for the default "vision" agent
        if agent.lower() == "vision":
            voice = os.environ.get("TTS_VOICE", voice).strip() or voice
            rate  = os.environ.get("TTS_RATE",  rate).strip()  or rate
            pitch = os.environ.get("TTS_PITCH", pitch).strip() or pitch

    communicate = edge_tts.Communicate(_clean_for_tts(text), voice, rate=rate, pitch=pitch)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


def tts_available() -> bool:
    return True
