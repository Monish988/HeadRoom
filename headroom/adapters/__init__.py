from abc import ABC, abstractmethod
from typing import Any, Optional
from urllib.parse import urlparse


class BaseAdapter(ABC):
    @staticmethod
    @abstractmethod
    def detect(url: str) -> bool: ...

    @abstractmethod
    def extract_texts(self, body: dict[str, Any]) -> list[str]: ...

    @abstractmethod
    def inject_texts(
        self, body: dict[str, Any], compressed: list[str]
    ) -> dict[str, Any]: ...

    @abstractmethod
    def model_key(self) -> str: ...

    @abstractmethod
    def endpoint_path(self) -> str: ...

    def is_stream_supported(self) -> bool:
        return True


def detect_provider(upstream_base_url: str, override: Optional[str] = None) -> str:
    if override:
        return override.lower()
    host = urlparse(upstream_base_url).hostname or ""
    if "openrouter" in host:
        return "openai"
    if "anthropic" in host:
        return "anthropic"
    if "googleapis" in host or "generativelanguage" in host:
        return "gemini"
    if "cohere" in host:
        return "cohere"
    if "mistral" in host:
        return "openai"
    if "groq" in host:
        return "openai"
    if "together" in host:
        return "openai"
    if "deepseek" in host:
        return "openai"
    if "fireworks" in host:
        return "openai"
    if "api.openai" in host:
        return "openai"
    return "generic"
