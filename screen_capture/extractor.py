import os
import re
import json
import base64
from io import BytesIO
from PIL import Image
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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


def _image_to_base64(img: Image.Image) -> str:
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


async def extract_problem(img: Image.Image) -> dict:
    img_b64 = _image_to_base64(img)

    response = await client.chat.completions.create(
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