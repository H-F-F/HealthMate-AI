import os

from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi

load_dotenv()


def _get_api_key() -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("缺少 DASHSCOPE_API_KEY，请先在 .env 中配置。")
    return api_key


def get_chat_model():
    model_name = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
    return ChatTongyi(
        model=model_name,
        dashscope_api_key=_get_api_key(),
    )
