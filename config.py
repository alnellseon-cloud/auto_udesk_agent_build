import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("UAGENT_BASE_URL", "").strip().rstrip("/")
TOKEN = os.environ.get("UAGENT_TOKEN", "")

# 自动登录凭据（用于 token 过期时自动刷新，可选）
UC_BASE_URL = os.environ.get("UC_BASE_URL", "").strip().rstrip("/")
UC_EMAIL = os.environ.get("UAGENT_EMAIL", "")
UC_PASSWORD_MD5 = os.environ.get("UAGENT_PASSWORD_MD5", "")

DEFAULT_MODEL = "doubao-seed-1.6"
DEFAULT_MODEL_PROVIDER = "langgenius/openai_api_compatible/openai_api_compatible"

AVAILABLE_MODELS = [
    "doubao-seed-1.6",
    "doubao-seed-1.8",
    "doubao-lite-4k",
    "hs-doubao-1.5",
    "DeepSeek-V3",
    "GLM-4-Flash",
]
