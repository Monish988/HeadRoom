# HeadRoom

A local-first AI Proxy Gateway that compresses LLM input prompts transparently. Sits between your application and any LLM provider — just change the `base_url` and get 30–50% token reduction with ≤15ms overhead.

## Quick start

```bash
pip install -r requirements.txt
python -m headroom
```

Or with Docker:

```bash
docker compose up -d
```

## Usage

Point your LLM client at `http://localhost:8000`:

```bash
HEADROOM_UPSTREAM_BASE_URL=https://openrouter.ai/api python -m headroom
```

Provider is auto-detected from the upstream URL. Override with `HEADROOM_PROVIDER`:

```bash
HEADROOM_PROVIDER=anthropic HEADROOM_UPSTREAM_BASE_URL=https://api.anthropic.com python -m headroom
HEADROOM_PROVIDER=gemini HEADROOM_UPSTREAM_BASE_URL=https://generativelanguage.googleapis.com python -m headroom
HEADROOM_PROVIDER=openai HEADROOM_UPSTREAM_BASE_URL=https://api.openai.com python -m headroom
```

Responses include a `_headroom` key with compression stats.

## Supported providers

| Provider | Endpoint | Auto-detected |
|----------|----------|---------------|
| OpenAI / OpenRouter / Groq / Together / DeepSeek / Mistral / Fireworks | `/v1/chat/completions` | `api.openai`, `openrouter`, `groq`, `together`, `deepseek`, `mistral`, `fireworks` |
| Anthropic | `/v1/messages` | `anthropic` |
| Google Gemini | `/v1/models/{model}:generateContent` | `googleapis`, `generativelanguage` |
| Any other provider | best-effort | fallback (walks `content`/`text`/`prompt` keys) |

## Tests

```bash
python -m pytest tests/ -v
```

## How it works

1. Request hits catch-all `POST /{path:path}`
2. Adapter extracts text content from provider-specific format
3. Compression engine: compacts JSON/XML blocks → strips boilerplate substrings → deduplicates → normalizes whitespace
4. Redis cache (SHA-256 keyed, graceful no-op if unavailable)
5. Original request body with compressed text forwarded to upstream

## Configuration

All via `HEADROOM_` env prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Listen port |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `UPSTREAM_BASE_URL` | `https://api.openai.com` | LLM provider base URL |
| `LOG_LEVEL` | `info` | Logging level |
| `PROVIDER` | auto-detect | Force provider (`openai`, `anthropic`, `gemini`) |

## Docker

Build and run with Redis:

```bash
docker compose up -d
```

Set the upstream provider via `.env`:

```bash
echo HEADROOM_UPSTREAM_BASE_URL=https://api.anthropic.com >> .env
docker compose up -d
```

Or run standalone without Redis:

```bash
docker build -t headroom .
docker run -p 8000:8000 \
  -e HEADROOM_UPSTREAM_BASE_URL=https://openrouter.ai/api \
  headroom
```
