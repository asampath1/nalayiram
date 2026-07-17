"""Shared types and helpers for prabandham-specific title scrapers."""
from __future__ import annotations

import re
from dataclasses import dataclass


SEPARATOR_RE = re.compile(r"^[-—–\s]+$")
PATTU_SUFFIX_RE = re.compile(r"[–\-—]\s*(\d+)\s*[–\-—]?\s*$")

SKIP_PARAGRAPH_MARKERS = (
    "This entry was posted",
    "Leave a Reply",
    "Powered by WordPress",
    "Share this:",
)


@dataclass(frozen=True)
class PasuramTitleRecord:
    pattu_number: int
    pasuram_number: int
    pasuram: str
    title: str
    prabandham: str = ""


def is_separator(text: str) -> bool:
    stripped = text.strip()
    return bool(SEPARATOR_RE.match(stripped)) and len(stripped.replace(" ", "")) >= 6


def is_pasuram_paragraph(text: str) -> bool:
    lines = [line for line in text.strip().split("\n") if line.strip()]
    if not lines:
        return False
    return bool(PATTU_SUFFIX_RE.search(lines[-1]))


def extract_pattu_number(text: str) -> int:
    lines = [line for line in text.strip().split("\n") if line.strip()]
    match = PATTU_SUFFIX_RE.search(lines[-1])
    if not match:
        raise ValueError(f"Pasuram suffix not found in paragraph: {text[:80]!r}")
    return int(match.group(1))


def join_title_blocks(blocks: list[str]) -> str:
    parts: list[str] = []
    for block in blocks:
        flattened = " ".join(line.strip() for line in block.split("\n") if line.strip())
        if flattened:
            parts.append(flattened)
    return " ".join(parts)
