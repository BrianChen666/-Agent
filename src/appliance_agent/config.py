from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_embedding_model: str = "text-embedding-v4"
    qwen_embedding_dimensions: int = 1024
    qwen_rerank_model: str = "qwen3-rerank"
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    temperature: float = 0.1

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY") or None,
            dashscope_base_url=os.getenv("DASHSCOPE_BASE_URL", cls.dashscope_base_url),
            qwen_embedding_model=os.getenv("QWEN_EMBEDDING_MODEL", cls.qwen_embedding_model),
            qwen_embedding_dimensions=int(os.getenv("QWEN_EMBEDDING_DIMENSIONS", "1024")),
            qwen_rerank_model=os.getenv("QWEN_RERANK_MODEL", cls.qwen_rerank_model),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY") or None,
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", cls.deepseek_base_url),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", cls.deepseek_model),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
        )
