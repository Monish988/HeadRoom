from typing import Any

from headroom.adapters import BaseAdapter


class AnthropicAdapter(BaseAdapter):
    @staticmethod
    def detect(url: str) -> bool:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        return "anthropic" in host

    def extract_texts(self, body: dict[str, Any]) -> list[str]:
        texts = []
        for msg in body.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, str):
                texts.append(content)
            elif isinstance(content, list):
                combined = " ".join(
                    b.get("text", "") for b in content if b.get("type") == "text"
                )
                texts.append(combined)
        return texts

    def inject_texts(
        self, body: dict[str, Any], compressed: list[str]
    ) -> dict[str, Any]:
        idx = 0
        for msg in body.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, str) and idx < len(compressed):
                msg["content"] = compressed[idx]
                idx += 1
            elif isinstance(content, list) and idx < len(compressed):
                for block in content:
                    if block.get("type") == "text":
                        block["text"] = compressed[idx]
                        idx += 1
        return body

    def model_key(self) -> str:
        return "model"

    def endpoint_path(self) -> str:
        return "/v1/messages"

    def is_stream_supported(self) -> bool:
        return True
