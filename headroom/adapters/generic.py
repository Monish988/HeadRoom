from typing import Any

from headroom.adapters import BaseAdapter

TEXT_KEYS = {"content", "text", "message", "prompt", "input", "query"}


class GenericAdapter(BaseAdapter):
    @staticmethod
    def detect(url: str) -> bool:
        return True

    def extract_texts(self, body: dict[str, Any]) -> list[str]:
        texts = []
        self._walk_extract(body, texts)
        return texts

    def inject_texts(
        self, body: dict[str, Any], compressed: list[str]
    ) -> dict[str, Any]:
        idx = 0
        self._walk_inject(body, compressed, idx)
        return body

    def _walk_extract(self, node: Any, texts: list[str]) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                if isinstance(val, str) and key.lower() in TEXT_KEYS:
                    texts.append(val)
                else:
                    self._walk_extract(val, texts)
        elif isinstance(node, list):
            for item in node:
                self._walk_extract(item, texts)

    def _walk_inject(
        self, node: Any, compressed: list[str], idx: int
    ) -> int:
        if isinstance(node, dict):
            for key, val in list(node.items()):
                if isinstance(val, str) and key.lower() in TEXT_KEYS:
                    if idx < len(compressed):
                        node[key] = compressed[idx]
                        idx += 1
                else:
                    idx = self._walk_inject(val, compressed, idx)
        elif isinstance(node, list):
            for item in node:
                idx = self._walk_inject(item, compressed, idx)
        return idx

    def model_key(self) -> str:
        return "model"

    def endpoint_path(self) -> str:
        return "/v1/chat/completions"

    def is_stream_supported(self) -> bool:
        return False
