"""Lớp gọi LLM: OpenRouter nếu có cấu hình, ngược lại dùng mock LLM.

Chọn provider bằng biến môi trường (12-Factor), không sửa code:
  - ``OPENROUTER_API_KEY`` có giá trị → gọi OpenRouter (model ``OPENROUTER_MODEL``)
  - không có → ``utils.mock_llm`` (test/CI chạy offline, tất định, không tốn tiền)

Trả về cùng một dạng dict với mock: answer, tokens_in, tokens_out, cost_usd.
"""

from __future__ import annotations

import httpx

from utils import mock_llm

from .config import get_settings
from .logging_utils import log_event

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 30.0
# Đủ chỗ cho model suy luận (reasoning token cũng tính vào max_tokens)
MAX_OUTPUT_TOKENS = 1024
SYSTEM_PROMPT = (
    "Bạn là trợ lý kỹ thuật về cloud và deployment. "
    "Trả lời ngắn gọn, chính xác, bằng ngôn ngữ của người hỏi."
)


def _ask_openrouter(question: str, history: list[dict], api_key: str, model: str) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": t["role"], "content": t["content"]} for t in history]
    messages.append({"role": "user", "content": question})

    response = httpx.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": messages,
            "max_tokens": MAX_OUTPUT_TOKENS,
            # model suy luận: nghĩ ít, và không trả phần suy nghĩ vào câu trả lời
            "reasoning": {"effort": "low", "exclude": True},
            # yêu cầu OpenRouter trả luôn chi phí thật của lượt gọi
            "usage": {"include": True},
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()

    usage = data.get("usage") or {}
    tokens_in = int(usage.get("prompt_tokens", 0))
    tokens_out = int(usage.get("completion_tokens", 0))
    cost = usage.get("cost")
    if cost is None:
        # Không có giá thật → ước lượng theo bảng giá của mock (thang gpt-4o-mini)
        cost = (
            tokens_in / 1000 * mock_llm.PRICE_INPUT_PER_1K
            + tokens_out / 1000 * mock_llm.PRICE_OUTPUT_PER_1K
        )

    return {
        "answer": data["choices"][0]["message"]["content"].strip(),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(float(cost), 8),
    }


def ask_llm(question: str, history: list[dict] | None = None) -> dict:
    history = history or []
    settings = get_settings()
    if not settings.openrouter_api_key:
        return mock_llm.ask_llm(question, history)

    try:
        return _ask_openrouter(
            question, history, settings.openrouter_api_key, settings.openrouter_model
        )
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as err:
        # Provider lỗi thì service vẫn trả lời được (bằng mock) thay vì 500,
        # và log lại để thấy ngay trên dashboard
        log_event(
            "llm_fallback",
            level="warning",
            provider="openrouter",
            error=f"{type(err).__name__}: {err}",
        )
        return mock_llm.ask_llm(question, history)
