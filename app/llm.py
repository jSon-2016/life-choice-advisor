"""共享 LLM 实例。"""

from langchain_community.chat_models import ChatTongyi

from app.config import LLM_MODEL


def create_llm(*, temperature: float = 0.3) -> ChatTongyi:
    return ChatTongyi(model=LLM_MODEL, temperature=temperature)
