from headroom.adapters.openai import OpenAIAdapter
from headroom.adapters.anthropic import AnthropicAdapter
from headroom.adapters.gemini import GeminiAdapter
from headroom.adapters.generic import GenericAdapter
from headroom.adapters.registry import get_adapter, list_providers


class TestOpenAIAdapter:
    adapter = OpenAIAdapter()

    def test_extract_openai_messages(self):
        body = {"model": "gpt-4", "messages": [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]}
        texts = self.adapter.extract_texts(body)
        assert texts == ["hello", "hi"]

    def test_inject_compressed(self):
        body = {"model": "gpt-4", "messages": [{"role": "user", "content": "original hello"}, {"role": "user", "content": "original hi"}]}
        result = self.adapter.inject_texts(body, ["comp hello", "comp hi"])
        assert result["messages"][0]["content"] == "comp hello"
        assert result["messages"][1]["content"] == "comp hi"

    def test_detect(self):
        assert OpenAIAdapter.detect("https://api.openai.com") is True


class TestAnthropicAdapter:
    adapter = AnthropicAdapter()

    def test_extract_anthropic_messages(self):
        body = {"model": "claude-3-opus", "messages": [{"role": "user", "content": "hello"}]}
        texts = self.adapter.extract_texts(body)
        assert texts == ["hello"]

    def test_extract_with_content_blocks(self):
        body = {
            "model": "claude-3",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "block1"}, {"type": "text", "text": "block2"}]}],
        }
        texts = self.adapter.extract_texts(body)
        assert texts == ["block1 block2"]

    def test_inject_string_content(self):
        body = {"model": "claude-3", "messages": [{"role": "user", "content": "original"}]}
        result = self.adapter.inject_texts(body, ["compressed"])
        assert result["messages"][0]["content"] == "compressed"

    def test_detect(self):
        assert AnthropicAdapter.detect("https://api.anthropic.com") is True
        assert AnthropicAdapter.detect("https://api.openai.com") is False


class TestGeminiAdapter:
    adapter = GeminiAdapter()

    def test_extract_contents(self):
        body = {"contents": [{"parts": [{"text": "hello"}, {"text": "world"}]}, {"parts": [{"text": "foo"}]}]}
        texts = self.adapter.extract_texts(body)
        assert texts == ["hello", "world", "foo"]

    def test_inject_parts(self):
        body = {"contents": [{"parts": [{"text": "a"}, {"text": "b"}]}]}
        result = self.adapter.inject_texts(body, ["x", "y"])
        assert result["contents"][0]["parts"][0]["text"] == "x"
        assert result["contents"][0]["parts"][1]["text"] == "y"

    def test_detect(self):
        assert GeminiAdapter.detect("https://generativelanguage.googleapis.com") is True
        assert GeminiAdapter.detect("https://api.openai.com") is False
        assert GeminiAdapter.detect("https://api.openai.com") is False

    def test_endpoint_path(self):
        assert self.adapter.endpoint_path() == "/v1/models/{model}:generateContent"


class TestGenericAdapter:
    adapter = GenericAdapter()

    def test_extract_known_keys(self):
        body = {"prompt": "hello", "query": "world", "irrelevant": 42}
        texts = self.adapter.extract_texts(body)
        assert "hello" in texts
        assert "world" in texts

    def test_nested_extraction(self):
        body = {"input": {"content": "nested", "meta": {"text": "deep"}}}
        texts = self.adapter.extract_texts(body)
        assert "nested" in texts
        assert "deep" in texts

    def test_inject_preserves_structure(self):
        body = {"prompt": "old1", "nested": {"text": "old2"}}
        result = self.adapter.inject_texts(body, ["new1", "new2"])
        assert result["prompt"] == "new1"
        assert result["nested"]["text"] == "new2"


class TestRegistry:
    def test_get_openai_adapter(self):
        adapter = get_adapter("https://api.openai.com")
        assert type(adapter).__name__ == "OpenAIAdapter"

    def test_get_anthropic_adapter(self):
        adapter = get_adapter("https://api.anthropic.com")
        assert type(adapter).__name__ == "AnthropicAdapter"

    def test_get_gemini_adapter(self):
        adapter = get_adapter("https://generativelanguage.googleapis.com")
        assert type(adapter).__name__ == "GeminiAdapter"

    def test_get_generic_fallback(self):
        adapter = get_adapter("https://custom.example.com")
        assert type(adapter).__name__ == "GenericAdapter"

    def test_provider_override(self):
        adapter = get_adapter("https://api.openai.com", override="anthropic")
        assert type(adapter).__name__ == "AnthropicAdapter"

    def test_list_providers(self):
        providers = list_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "gemini" in providers
        assert "generic" in providers
