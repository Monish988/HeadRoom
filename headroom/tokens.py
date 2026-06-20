"""Token counting with tiktoken (OpenAI) and heuristic fallback."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

_tiktoken_encoders: dict[str, object] = {}


def _get_tiktoken_encoder(model: str = "gpt-4") -> object | None:
    try:
        import tiktoken  # type: ignore[import-untyped]

        if model not in _tiktoken_encoders:
            try:
                _tiktoken_encoders[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                _tiktoken_encoders[model] = tiktoken.get_encoding("cl100k_base")
        return _tiktoken_encoders[model]
    except ImportError:
        return None


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Return the number of tokens in *text*.

    Uses tiktoken when available (OpenAI models), otherwise falls back to
    ``ceil(len(text) / 4)`` which is a rough industry heuristic for English
    text encoded with cl100k/merge-based tokenizers.
    """
    encoder = _get_tiktoken_encoder(model)
    if encoder is not None:
        return len(encoder.encode(text))  # type: ignore[union-attr]

    # Heuristic fallback: ~4 chars per token
    return (len(text) + 3) // 4
