import os
import re
import json
import base64
from io import BytesIO
from pathlib import Path

import httpx
from openai import OpenAI
import mss
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CAPTURE_WIDTH_RATIO = float(os.getenv("CAPTURE_WIDTH_RATIO", "0.42"))

client = OpenAI(api_key=OPENAI_API_KEY)

EXTRACT_PROMPT = """이 화면은 프로그래머스 코딩 테스트 문제 페이지의 좌측 영역입니다.
화면에서 코딩 문제를 추출해서 아래 JSON 형식으로만 반환하세요.
다른 텍스트나 마크다운 코드블록 없이 JSON만 반환하세요.

{
    "title": "문제 제목",
    "description": "문제 설명 전문",
    "constraints": "제한 사항",
    "examples": [
        {
            "input": "입력 예시",
            "output": "출력 예시",
            "explanation": "설명 (없으면 빈 문자열)"
        }
    ],
    "is_coding_problem": true
}

코딩 문제 화면이 아니면 is_coding_problem을 false로 설정하세요."""


def capture_left_half() -> Image.Image:
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        region = {
            "left": monitor["left"],
            "top": monitor["top"],
            "width": int(monitor["width"] * CAPTURE_WIDTH_RATIO),
            "height": monitor["height"],
        }
        screenshot = sct.grab(region)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")


def image_to_base64(img: Image.Image) -> str:
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def call_vision(img: Image.Image) -> dict:
    img_b64 = image_to_base64(img)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACT_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    },
                ],
            }
        ],
        max_tokens=4096,
        temperature=0.1,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
    raw = re.sub(r"\n?```\s*$", "", raw).strip()
    return json.loads(raw)


def main():
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY not set")
        return

    img = capture_left_half()
    Path("poc/output").mkdir(parents=True, exist_ok=True)
    img.save("poc/output/screenshot.png")

    result = call_vision(img)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    with open("poc/output/extracted_problem.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()