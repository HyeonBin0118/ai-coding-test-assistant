import re
import pygetwindow as gw


def read_title() -> str:
    windows = gw.getWindowsWithTitle("프로그래머스")
    if not windows:
        windows = gw.getWindowsWithTitle("Programmers")
    if not windows:
        return ""

    title = windows[0].title
    parts = [p.strip() for p in re.split(r"\s[-|–—]\s", title)]
    parts = [p for p in parts if p and "프로그래머스" not in p and "Programmers" not in p and "Chrome" not in p and "코딩테스트" not in p]
    return parts[0] if parts else ""