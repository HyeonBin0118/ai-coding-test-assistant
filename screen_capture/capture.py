import os
import mss
from PIL import Image


def capture_left_half() -> Image.Image:
    ratio = float(os.getenv("CAPTURE_WIDTH_RATIO", "0.42"))
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        region = {
            "left": monitor["left"],
            "top": monitor["top"],
            "width": int(monitor["width"] * ratio),
            "height": monitor["height"],
        }
        screenshot = sct.grab(region)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")