import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
CAPTURE_WIDTH_RATIO = float(os.getenv("CAPTURE_WIDTH_RATIO", "0.42"))
CAPTURE_INTERVAL = float(os.getenv("CAPTURE_INTERVAL", "2.0"))
CHANGE_THRESHOLD = int(os.getenv("CHANGE_THRESHOLD", "10"))