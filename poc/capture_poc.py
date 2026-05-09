import os
import time
from pathlib import Path

import mss
import imagehash
from PIL import Image
from dotenv import load_dotenv

load_dotenv()


def capture_left_half() -> Image.Image:
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        ratio = float(os.getenv("CAPTURE_WIDTH_RATIO", "0.42"))
        region = {
            "left": monitor["left"],
            "top": monitor["top"],
            "width": int(monitor["width"] * ratio),
            "height": monitor["height"],
        }
        screenshot = sct.grab(region)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")


def get_hash(img: Image.Image) -> imagehash.ImageHash:
    return imagehash.phash(img)


def monitor_changes(interval: float = 2.0, threshold: int = 10):
    print(f"start — interval={interval}s  threshold={threshold}  (Ctrl+C to stop)")

    prev_hash = None
    change_count = 0

    try:
        while True:
            img = capture_left_half()
            current_hash = get_hash(img)

            if prev_hash is not None:
                diff = current_hash - prev_hash

                if diff >= threshold:
                    change_count += 1
                    print(f"\nchange detected  diff={diff}  count={change_count}")
                    Path("poc/output").mkdir(parents=True, exist_ok=True)
                    img.save(f"poc/output/change_{change_count}.png")
                    time.sleep(3.0)
                    prev_hash = None
                    continue
                else:
                    print(f"  diff={diff:>3}", end="\r")

            prev_hash = current_hash
            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\nstopped — {change_count} changes detected")


if __name__ == "__main__":
    interval = float(os.getenv("CAPTURE_INTERVAL", "2.0"))
    threshold = int(os.getenv("CHANGE_THRESHOLD", "10"))
    monitor_changes(interval=interval, threshold=threshold)