import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from headroom.adapters.registry import get_adapter
from headroom.cache.redis_cache import RedisCache
from headroom.compression.engine import compress_text
from headroom.config import settings
from headroom.proxy import LLMProxy
from headroom.tokens import count_tokens

cache = RedisCache()
proxy = LLMProxy()
adapter = get_adapter(settings.upstream_base_url, settings.provider)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.connect()
    yield
    await cache.disconnect()
    await proxy.close()


app = FastAPI(title="HeadRoom", version="0.2.0", lifespan=lifespan)


@app.get("/health")
async def health():
    stats = await cache.get_stats()
    return {
        "status": "ok",
        "cache": stats,
        "adapter": type(adapter).__module__.split(".")[-1].replace("_adapter", ""),
    }


def _is_dry_run(request: Request) -> bool:
    """Return True if dry-run is active via config or per-request header."""
    if settings.dry_run:
        return True
    header = request.headers.get("x-headroom-dry-run", "").lower()
    return header in ("true", "1", "yes")


def _is_no_compress(request: Request) -> bool:
    """Return True if the request carries the no-compress escape hatch."""
    header = request.headers.get("x-headroom-no-compress", "").lower()
    return header in ("true", "1", "yes")


def _detect_model(body: dict[str, Any]) -> str:
    """Best-effort extraction of the model name for token counting."""
    return body.get("model", "gpt-4")


@app.api_route("/{path:path}", methods=["POST"])
async def proxy_request(request: Request, path: str):
    start = time.perf_counter()

    body: dict[str, Any] = await request.json()
    dry_run = _is_dry_run(request)
    no_compress = _is_no_compress(request)
    model = _detect_model(body)

    texts = adapter.extract_texts(body)
    compressed_texts = []
    total_original = 0
    total_compressed = 0
    total_original_tokens = 0
    total_compressed_tokens = 0
    total_overhead_ms = 0.0
    exempt_count = 0

    for text in texts:
        if no_compress:
            compressed_texts.append(text)
            total_original += len(text)
            total_compressed += len(text)
            tok = count_tokens(text, model)
            total_original_tokens += tok
            total_compressed_tokens += tok
            exempt_count += 1
            continue

        cached = await cache.get_cached(text)
        if cached is not None:
            compressed_texts.append(cached)
            total_original += len(text)
            total_compressed += len(cached)
            tok = count_tokens(text, model)
            total_original_tokens += tok
            total_compressed_tokens += count_tokens(cached, model)
            continue

        t0 = time.perf_counter()
        compressed, meta = compress_text(text, model)
        overhead_ms = (time.perf_counter() - t0) * 1000
        total_overhead_ms += overhead_ms

        if meta.get("exempt"):
            exempt_count += 1

        if dry_run:
            compressed_texts.append(text)
        else:
            await cache.set_cached(text, compressed)
            compressed_texts.append(compressed)

        total_original += meta.get("original_length", 0)
        total_compressed += meta.get("compressed_length", 0)
        total_original_tokens += meta.get("original_tokens", 0)
        total_compressed_tokens += meta.get("compressed_tokens", 0)

    if compressed_texts:
        body = adapter.inject_texts(body, compressed_texts)

    stream = body.get("stream", False)
    upstream_headers = {k: v for k, v in request.headers.items()}

    try:
        if stream and adapter.is_stream_supported():
            return StreamingResponse(
                proxy.forward_stream(body, upstream_headers, adapter.endpoint_path()),
                media_type="text/event-stream",
            )
        result = await proxy.forward_request(
            body, upstream_headers, adapter.endpoint_path()
        )
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"error": f"Upstream request failed: {e}"},
        )

    elapsed = (time.perf_counter() - start) * 1000

    result["_headroom"] = {
        "proxy_overhead_ms": round(elapsed, 2),
        "parse_overhead_ms": round(total_overhead_ms, 2),
        "original_chars": total_original,
        "compressed_chars": total_compressed,
        "original_tokens": total_original_tokens,
        "compressed_tokens": total_compressed_tokens,
        "texts_compressed": len(compressed_texts),
        "exempt_blocks": exempt_count,
        "dry_run": dry_run,
        "adapter": type(adapter).__name__.replace("Adapter", "").lower(),
    }

    return result
