from typing import Any, AsyncGenerator

import httpx

from headroom.config import settings


class LLMProxy:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.upstream_base_url)

    async def forward_request(
        self, body: dict[str, Any], headers: dict[str, str], path: str = "/v1/chat/completions"
    ) -> dict[str, Any]:
        upstream_headers = self._filter_headers(headers)
        response = await self._client.post(
            path,
            json=body,
            headers=upstream_headers,
        )
        response.raise_for_status()
        return response.json()

    async def forward_stream(
        self, body: dict[str, Any], headers: dict[str, str], path: str = "/v1/chat/completions"
    ) -> AsyncGenerator[bytes, None]:
        upstream_headers = self._filter_headers(headers)
        async with self._client.stream(
            "POST",
            path,
            json=body,
            headers=upstream_headers,
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk

    def _filter_headers(self, headers: dict[str, str]) -> dict[str, str]:
        hop_by_hop = {
            "host", "connection", "transfer-encoding", "te",
            "keep-alive", "proxy-authorization", "proxy-authenticate",
            "upgrade", "content-length", "content-encoding",
        }
        result: dict[str, str] = {}
        for key, value in headers.items():
            lower = key.lower()
            if lower in hop_by_hop or lower.startswith("x-headroom"):
                continue
            result[key] = value
        if "host" not in result:
            result["host"] = self._client.base_url.host
        return result

    async def close(self) -> None:
        await self._client.aclose()
