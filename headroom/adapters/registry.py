from typing import Any

from headroom.adapters import BaseAdapter, detect_provider
from headroom.adapters.openai import OpenAIAdapter
from headroom.adapters.anthropic import AnthropicAdapter
from headroom.adapters.gemini import GeminiAdapter
from headroom.adapters.generic import GenericAdapter

ADAPTERS: dict[str, type[BaseAdapter]] = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "gemini": GeminiAdapter,
    "generic": GenericAdapter,
}


def get_adapter(upstream_base_url: str, override: Any = None) -> BaseAdapter:
    provider = detect_provider(upstream_base_url, override)
    cls = ADAPTERS.get(provider, GenericAdapter)
    return cls()


def list_providers() -> list[str]:
    return list(ADAPTERS.keys())
