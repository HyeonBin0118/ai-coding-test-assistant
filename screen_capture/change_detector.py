import asyncio
from .title_reader import read_title


async def start_monitor(on_change, on_title_change, interval: float = 2.0, threshold: int = 10):
    prev_title = ""

    # 시작 시 즉시 로드
    try:
        await on_change()
    except Exception as e:
        print(f"initial fetch error: {e}")

    while True:
        try:
            title = read_title()
            if title and title != prev_title:
                prev_title = title
                await on_title_change(title)
        except Exception as e:
            print(f"monitor error: {e}")

        await asyncio.sleep(0.5)