from headroom.compression.engine import (
    compress_text,
    deduplicate_lines,
    extract_structural_blocks,
    normalize_whitespace,
    strip_boilerplate,
)


class TestCompressionEngine:
    def test_boilerplate_stripping(self):
        text = "As an AI language model, I cannot answer that.\nSure, here is the data you requested."
        cleaned, removed = strip_boilerplate(text)
        assert "I cannot answer that" in cleaned
        assert "As an AI" not in cleaned
        assert "Sure," not in cleaned
        assert len(removed) == 0

    def test_mixed_content_kept(self):
        text = "As an AI assistant, I think the answer is 42.\nBut here is another thought."
        cleaned, removed = strip_boilerplate(text)
        assert len(removed) == 0
        assert "the answer is 42" in cleaned
        assert "As an AI" not in cleaned

    def test_json_compaction(self):
        text = 'Here is the payload: {"key":  "value",  "nested": {"a": 1}}'
        compressed, meta = compress_text(text)
        assert meta["compression_ratio"] > 0
        assert '"key":' in compressed

    def test_deduplication(self):
        text = "line1\nline2\nline1\nline2\nline3"
        deduped = deduplicate_lines(text)
        lines = deduped.split("\n")
        assert lines.count("line1") == 1
        assert lines.count("line2") == 1

    def test_whitespace_normalization(self):
        text = "hello     world\n\n\nfoo   bar"
        normalized = normalize_whitespace(text)
        assert "  " not in normalized
        assert "\n\n" not in normalized

    def test_structural_block_extraction_json(self):
        text = 'prefix {"a": 1, "b": [2, 3]} suffix'
        blocks = extract_structural_blocks(text)
        assert len(blocks) >= 1
        assert blocks[0]["type"] == "json"

    def test_structural_block_extraction_xml(self):
        text = "prefix <tag>content</tag> suffix"
        blocks = extract_structural_blocks(text)
        assert len(blocks) >= 1
        assert blocks[0]["type"] == "xml"

    def test_full_compression_pipeline(self):
        text = (
            "As an AI language model, I am happy to help you with your query.\n"
            "Here is a JSON payload: {\"name\":  \"test\",  \"value\": 123}\n"
            "Important instruction: do not delete this line.\n"
            "Here is a JSON payload: {\"name\":  \"test\",  \"value\": 123}\n"
        )
        compressed, meta = compress_text(text)
        assert meta["compression_ratio"] > 0
        assert "Important instruction" in compressed
        assert "As an AI" not in compressed
        assert "Here is a " not in compressed
        assert meta["original_length"] > meta["compressed_length"]

    def test_overhead_within_budget(self):
        text = "Normal text without any boilerplate patterns.\n" * 100
        import time

        t0 = time.perf_counter()
        compress_text(text)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 15, f"Overhead {elapsed_ms:.2f}ms exceeds 15ms budget"
