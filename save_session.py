"""
Save browser login sessions for Vision's automation tools.
Run this script ONCE per service from the Windows host (not inside Docker).

Usage:
  python save_session.py <site>

Supported sites:
  google       — saves session for NotebookLM and other Google services
  whatsapp     — saves WhatsApp Web session (scan QR once)
  instagram    — saves Instagram session
  claude       — saves Claude.ai session
  reddit       — saves Reddit session
  chatgpt      — saves ChatGPT session

Example:
  python save_session.py google
  python save_session.py whatsapp
"""
import asyncio
import sys
from pathlib import Path

# Add host_tools to path
sys.path.insert(0, str(Path(__file__).parent / "host_tools"))


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    site = sys.argv[1].lower()
    from browser_tools import save_login_session

    print(f"\n[Vision] Opening browser for {site} login...")
    result = await save_login_session(site)

    if result.get("status") == "saved":
        print(f"[Vision] Session saved to: {result['file']}")
        print(f"[Vision] Done! Vision will now use this session for {site} automation.")
    else:
        print(f"[Vision] Error: {result}")


if __name__ == "__main__":
    asyncio.run(main())
