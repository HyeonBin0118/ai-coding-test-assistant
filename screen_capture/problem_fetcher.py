import re
from playwright.async_api import async_playwright
from pywinauto import Desktop
import asyncio
from playwright.sync_api import sync_playwright


def get_programmers_window():
    try:
        desktop = Desktop(backend="uia")
        for w in desktop.windows():
            try:
                title = w.window_text()
                if "프로그래머스" in title:
                    return w
            except Exception:
                continue
        # 활성 탭에 없으면 모든 크롬 창에서 주소창 뒤지기
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
    try:
        win = get_programmers_window()
        if not win:
            return ""
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
    try:
        win = get_programmers_window()
        if not win:
            return ""
        title = win.window_text()
        parts = [p.strip() for p in re.split(r"\s[-|]\s", title)]
        parts = [p for p in parts if p
                 and "프로그래머스" not in p
                 and "Chrome" not in p
                 and "코딩테스트" not in p
                 and "Programmers" not in p]
        return parts[0] if parts else ""
    except Exception:
        return ""


def extract_lesson_id(url: str) -> str:
    match = re.search(r"/lessons/(\d+)", url)
    return match.group(1) if match else ""


async def fetch_problem_by_url() -> dict:
    # 방법 1: 주소창에서 URL 직접 읽기
    url = get_browser_url()
    
    # 방법 2: 탭 제목에서 문제 제목으로 검색 (주소창 실패 시)
    if not url:
        title = get_title_from_window()
        if not title:
            return {}
        # 제목으로 프로그래머스 검색해서 lesson_id 찾기
        search_url = f"https://school.programmers.co.kr/learn/challenges?order=recent&search={title}"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
            # 첫 번째 검색 결과 링크
            link = await page.query_selector("a.challenge-title")
            if link:
                href = await link.get_attribute("href")
                url = "https://school.programmers.co.kr" + href
            await browser.close()

    if not url:
        return {}
    if not url.startswith("http"):
        url = "https://" + url
    if not extract_lesson_id(url):
        return {}

    return await fetch_problem(url)


def _fetch_problem_sync(url: str) -> dict:
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
                rows = el.query_selector_all("table tbody tr")
                for row in rows:
                    cols = row.query_selector_all("td")
                    col_texts = [c.inner_text() for c in cols]
                    if len(col_texts) >= 2:
                        examples.append({
                            "input": col_texts[0].strip(),
                            "output": col_texts[1].strip(),
                            "explanation": col_texts[2].strip() if len(col_texts) > 2 else ""
                        })

        browser.close()

    return {
        "title": title,
        "description": description,
        "constraints": constraints,
        "examples": examples,
        "is_coding_problem": bool(title),
    }


async def fetch_problem(url: str) -> dict:
    return await asyncio.to_thread(_fetch_problem_sync, url)


async def fetch_problem_by_url() -> dict:
    url = get_browser_url()
    if not url:
        return {}
    if not url.startswith("http"):
        url = "https://" + url
    if not extract_lesson_id(url):
        return {}
    return await fetch_problem(url)