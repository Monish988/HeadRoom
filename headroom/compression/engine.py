import json
import re
from typing import Any

import orjson

STRUCTURAL_PATTERNS = re.compile(
    r"(\{.*?\}|\[.*?\]|<[^>]+>.*?</[^>]+>)", re.DOTALL
)

BOILERPLATE_PATTERNS = [
    re.compile(r"As an AI (language model|assistant),?\s*", re.IGNORECASE),
    re.compile(r"I understand (your request|what you're asking),?\s*", re.IGNORECASE),
    re.compile(r"Certainly!? Here('s| is) (how|my|a)\s*", re.IGNORECASE),
    re.compile(r"(Sure|Of course|Absolutely),?\s+(I|here|let me)\s*", re.IGNORECASE),
    re.compile(r"(Here's|Here is)\s+(a|an|the|my|some)\s*", re.IGNORECASE),
    re.compile(r"Please note that,?\s*", re.IGNORECASE),
    re.compile(r"I'd be happy to\s*", re.IGNORECASE),
]

WHITESPACE_PATTERN = re.compile(r"\s+")


def extract_structural_blocks(text: str) -> list[dict[str, Any]]:
    blocks = []
    for match in STRUCTURAL_PATTERNS.finditer(text):
        raw = match.group(0)
        try:
            parsed = orjson.loads(raw)
            blocks.append({"type": "json", "content": parsed, "raw": raw})
        except (orjson.JSONDecodeError, ValueError):
            if raw.startswith("<"):
                blocks.append({"type": "xml", "content": raw, "raw": raw})
    return blocks


def strip_boilerplate(text: str) -> tuple[str, list[str]]:
    lines = text.split("\n")
    result = []
    removed = []
    for line in lines:
        for pattern in BOILERPLATE_PATTERNS:
            new_line, n = pattern.subn("", line, count=1)
            if n:
                line = new_line
                break
        if line.strip():
            result.append(line)
        else:
            removed.append(line)
    return "\n".join(result), removed


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def deduplicate_lines(text: str) -> str:
    seen: set[str] = set()
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            lines.append(line)
        elif not stripped:
            lines.append(line)
    return "\n".join(lines)


def compress_text(text: str) -> tuple[str, dict[str, Any]]:
    meta: dict[str, Any] = {"original_length": len(text)}

    structural_blocks = extract_structural_blocks(text)
    meta["structural_block_count"] = len(structural_blocks)

    for block in structural_blocks:
        if block["type"] == "json":
            compact = json.dumps(block["content"], separators=(",", ":"))
            text = text.replace(block["raw"], compact, 1)

    text, removed_lines = strip_boilerplate(text)
    meta["boilerplate_lines_removed"] = len(removed_lines)

    text = deduplicate_lines(text)

    text = normalize_whitespace(text)
    meta["compressed_length"] = len(text)

    if meta["original_length"] > 0:
        meta["compression_ratio"] = (
            1 - meta["compressed_length"] / meta["original_length"]
        )
    else:
        meta["compression_ratio"] = 0.0

    return text, meta
