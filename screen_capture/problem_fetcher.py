import re
import asyncio
from playwright.sync_api import sync_playwright
from pywinauto import Desktop


def get_programmers_window():
    try:
        desktop = Desktop(backend="uia")
        for w in desktop.windows():
            try:
                if "프로그래머스" in w.window_text():
                    return w
            except Exception:
                continue
        # 활성 탭에 없으면 모든 크롬 창의 주소창 검색
        for w in desktop.windows():
            try:
                if "Chrome" not in w.window_text():
                    continue
                for ctrl in w.descendants(control_type="Edit"):
                    try:
                        val = ctrl.get_value()
                        if val and "programmers.co.kr" in val:
                            return w
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass
    return None


def get_browser_url() -> str:
    win = get_programmers_window()
    if not win:
        return ""
    try:
        for ctrl in win.descendants(control_type="Edit"):
            try:
                val = ctrl.get_value()
                if val and "programmers.co.kr" in val:
                    return val
            except Exception:
                continue
    except Exception:
        pass
    return ""


def get_title_from_window() -> str:
    win = get_programmers_window()
    if not win:
        return ""
    try:
        title = win.window_text()
        parts = [p.strip() for p in re.split(r"\s[-|]\s", title)]
        skip = {"프로그래머스", "Chrome", "코딩테스트", "Programmers"}
        parts = [p for p in parts if p and not any(s in p for s in skip)]
        return parts[0] if parts else ""
    except Exception:
        return ""


def extract_lesson_id(url: str) -> str:
    match = re.search(r"/lessons/(\d+)", url)
    return match.group(1) if match else ""


def _parse_examples(el) -> list:
    examples = []
    for row in el.query_selector_all("table tbody tr"):
        cols = [c.inner_text() for c in row.query_selector_all("td")]
        if len(cols) >= 2:
            examples.append({
                "input": cols[0].strip(),
                "output": cols[1].strip(),
                "explanation": cols[2].strip() if len(cols) > 2 else ""
            })
    return examples


def _fetch_sync(url: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)

        title = ""
        if page.locator("li.active").count() > 0:
            title = page.locator("li.active").first.inner_text().strip()

        sections = page.query_selector_all("div.lesson-content div.markdown")
        description = ""
        constraints = ""
        examples = []

        for i, el in enumerate(sections):
            text = el.inner_text()
            if i == 0:
                description = text.strip()
            elif "제한" in text:
                constraints = text.strip()
            elif "입출력 예" in text:
                examples = _parse_examples(el)

        browser.close()

    return {
        "title": title,
        "description": description,
        "constraints": constraints,
        "examples": examples,
        "is_coding_problem": bool(title),
    }


async def fetch_problem(url: str) -> dict:
    return await asyncio.to_thread(_fetch_sync, url)


async def fetch_problem_by_url() -> dict:
    url = get_browser_url()
    if not url:
        return {}
    if not url.startswith("http"):
        url = "https://" + url
    if not extract_lesson_id(url):
        return {}
    return await fetch_problem(url)