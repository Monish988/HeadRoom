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

cache = RedisCache()
proxy = LLMProxy()
adapter = get_adapter(settings.upstream_base_url, settings.provider)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.connect()
    yield
    await cache.disconnect()
    await proxy.close()


app = FastAPI(title="HeadRoom", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    stats = await cache.get_stats()
    return {
        "status": "ok",
        "cache": stats,
        "adapter": type(adapter).__module__.split(".")[-1].replace("_adapter", ""),
    }


@app.api_route("/{path:path}", methods=["POST"])
async def proxy_request(request: Request, path: str):
    start = time.perf_counter()

    body: dict[str, Any] = await request.json()
    texts = adapter.extract_texts(body)
    compressed_texts = []
    total_original = 0
    total_compressed = 0
    total_overhead_ms = 0.0

    for text in texts:
        cached = await cache.get_cached(text)
        if cached is not None:
            compressed_texts.append(cached)
            continue

        t0 = time.perf_counter()
        compressed, meta = compress_text(text)
        overhead_ms = (time.perf_counter() - t0) * 1000
        total_overhead_ms += overhead_ms

        await cache.set_cached(text, compressed)
        compressed_texts.append(compressed)
        total_original += meta.get("original_length", 0)
        total_compressed += meta.get("compressed_length", 0)

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
        "texts_compressed": len(compressed_texts),
        "adapter": type(adapter).__name__.replace("Adapter", "").lower(),
    }

    return result
