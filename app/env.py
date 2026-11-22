"""Load settings from .env when Vision runs without Docker (for example, straight on a laptop)."""
import os
from pathlib import Path

_f = Path(__file__).resolve().parent.parent / ".env"
if _f.exists():
    for line in _f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
