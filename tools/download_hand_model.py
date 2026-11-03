"""Download Google's versioned Hand Landmarker task bundle."""
import hashlib
import urllib.request
from pathlib import Path

URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / "models" / "hand_landmarker.task"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        temporary = destination.with_suffix(".download")
        with urllib.request.urlopen(URL, timeout=60) as response, temporary.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        if temporary.stat().st_size < 1_000_000:
            temporary.unlink()
            raise SystemExit("Downloaded hand model is unexpectedly small")
        temporary.replace(destination)
    print(f"Hand model ready: {destination}")
    print(f"SHA256: {hashlib.sha256(destination.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
