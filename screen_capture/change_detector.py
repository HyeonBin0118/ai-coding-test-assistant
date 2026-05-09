import asyncio
import imagehash
from PIL import Image
from .capture import capture_left_half


async def start_monitor(on_change, interval: float = 2.0, threshold: int = 10):
    prev_hash = None

    # 시작하자마자 한 번 즉시 캡처
    try:
        img = capture_left_half()
        await on_change(img)
    except Exception as e:
        print(f"initial capture error: {e}")

    while True:
        try:
            img = capture_left_half()
            current_hash = imagehash.phash(img)

            if prev_hash is not None:
                diff = current_hash - prev_hash
                if diff >= threshold:
                    await on_change(img)
                    await asyncio.sleep(3.0)
                    prev_hash = None
                    continue

            prev_hash = current_hash

        except Exception as e:
            print(f"monitor error: {e}")

        await asyncio.sleep(interval)