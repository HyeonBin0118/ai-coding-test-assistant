import asyncio
from .problem_fetcher import get_title_from_window


async def start_monitor(on_change, on_title_change, interval: float = 2.0, threshold: int = 10):
    prev_title = ""

    try:
        await on_change()
    except Exception as e:
        print(f"initial fetch error: {e}")

    while True:
        try:
            title = get_title_from_window()
            if title and title != prev_title:
                prev_title = title
                await on_title_change(title)
        except Exception as e:
            print(f"monitor error: {e}")

        await asyncio.sleep(0.5)