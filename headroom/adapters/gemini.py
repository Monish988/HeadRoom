from typing import Any

from headroom.adapters import BaseAdapter


class GeminiAdapter(BaseAdapter):
    @staticmethod
    def detect(url: str) -> bool:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        return "googleapis" in host or "generativelanguage" in host

    def extract_texts(self, body: dict[str, Any]) -> list[str]:
        texts = []
        for content in body.get("contents", []):
            for part in content.get("parts", []):
                if "text" in part:
                    texts.append(part["text"])
        return texts

    def inject_texts(
        self, body: dict[str, Any], compressed: list[str]
    ) -> dict[str, Any]:
        idx = 0
        for content in body.get("contents", []):
            for part in content.get("parts", []):
                if "text" in part and idx < len(compressed):
                    part["text"] = compressed[idx]
                    idx += 1
        return body

    def model_key(self) -> str:
        return "model"

    def endpoint_path(self) -> str:
        return "/v1/models/{model}:generateContent"

    def is_stream_supported(self) -> bool:
        return True
