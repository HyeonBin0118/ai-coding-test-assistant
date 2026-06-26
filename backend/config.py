import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CAPTURE_WIDTH_RATIO = float(os.getenv("CAPTURE_WIDTH_RATIO", "0.42"))
CAPTURE_INTERVAL = float(os.getenv("CAPTURE_INTERVAL", "2.0"))
CHANGE_THRESHOLD = int(os.getenv("CHANGE_THRESHOLD", "10"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:8001/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen-coder-v5")