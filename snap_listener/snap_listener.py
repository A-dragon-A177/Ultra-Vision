"""
Vision Snap Listener
Runs on Windows (NOT inside Docker).

Listens to the microphone for a sharp finger snap.
When a snap is detected → opens http://localhost:8080/speak in your browser.

Install once:
    pip install sounddevice numpy

Run:
    python snap_listener.py
"""
import sys
import time
import webbrowser

VISION_URL = "http://localhost:8080/speak"
SNAP_THRESHOLD = 0.30     # Minimum volume (0.0–1.0) — lower = more sensitive
SNAP_RATIO = 7            # Must be this many times louder than background
COOLDOWN_SEC = 2.5        # Seconds to wait before triggering again

try:
    import numpy as np
    import sounddevice as sd
except ImportError:
    print("Missing packages. Run:  pip install sounddevice numpy")
    sys.exit(1)

SAMPLE_RATE = 44100
FRAME_SIZE = 1024

last_trigger = 0.0
background_rms = 0.01     # running estimate of ambient noise level


def _callback(indata, frames, time_info, status):
    global last_trigger, background_rms

    volume = float(np.sqrt(np.mean(indata ** 2)))

    # Slowly track background level (low-pass filter)
    background_rms = 0.97 * background_rms + 0.03 * volume

    # Snap = sudden loud spike well above background
    is_snap = (
        volume > SNAP_THRESHOLD
        and volume > background_rms * SNAP_RATIO
    )

    if is_snap:
        now = time.time()
        if now - last_trigger > COOLDOWN_SEC:
            last_trigger = now
            print(f"  Snap! (vol={volume:.3f} bg={background_rms:.3f})  → Opening Vision…")
            webbrowser.open(VISION_URL)


def main():
    print("═" * 56)
    print("  Vision Snap Listener")
    print(f"  Snap your fingers → {VISION_URL}")
    print(f"  Threshold: {SNAP_THRESHOLD}  Ratio: ×{SNAP_RATIO}  Cooldown: {COOLDOWN_SEC}s")
    print("  Press Ctrl+C to stop.")
    print("═" * 56)

    try:
        with sd.InputStream(
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SIZE,
            callback=_callback,
            dtype="float32",
        ):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nSnap listener stopped.")
    except sd.PortAudioError as e:
        print(f"\nMicrophone error: {e}")
        print("Make sure a microphone is connected and not in use by another app.")
        sys.exit(1)


if __name__ == "__main__":
    main()
