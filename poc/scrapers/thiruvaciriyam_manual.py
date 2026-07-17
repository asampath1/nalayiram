"""Parse manually validated திருவாசிரியம் blocks (POC, PasuramNumber 2578+)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Sequence

from poc.scrapers.thiruvozhukootrirukkai_tidley import PADHAVURAI_LABEL, PattuSection
from poc.scrapers.thiruvirutham_manual import (
    is_separator_line,
    normalize_manual_text,
    parse_manual_padham_rows,
)

PRABANDHAM = "திருவாசிரியம்"
PASURAM_NUMBER_BASE = 2577
ALZWAR = "நம்மாழ்வார்"
PLAIN_PATTU_SUFFIX_RE = re.compile(r"(?:\s+|\.)(\d+)\s*$")
BLOCK_SEPARATOR_RE = re.compile(r"^[-—–\u2014]{6,}\s*$", re.MULTILINE)


def split_manual_blocks(text: str) -> List[str]:
    text = normalize_manual_text(text)
    return [block.strip() for block in BLOCK_SEPARATOR_RE.split(text) if block.strip()]

PRABANDHAM = "திருவாசிரியம்"
PASURAM_NUMBER_BASE = 2577
ALZWAR = "நம்மாழ்வார்"
PLAIN_PATTU_SUFFIX_RE = re.compile(r"(?:\s+|\.)(\d+)\s*$")


def extract_plain_pattu_suffix(line: str) -> tuple[str, int]:
    stripped = line.strip()
    match = PLAIN_PATTU_SUFFIX_RE.search(stripped)
    if not match:
        raise ValueError(f"Plain pattu suffix not found: {stripped[:80]!r}")
    pattu_number = int(match.group(1))
    body = stripped[: match.start()].rstrip()
    return body, pattu_number


def parse_manual_block(block: str) -> PattuSection:
    lines: List[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or is_separator_line(stripped):
            continue
        lines.append(stripped)

    try:
        padhavurai_idx = next(index for index, line in enumerate(lines) if line == PADHAVURAI_LABEL)
    except StopIteration as exc:
        raise ValueError(f"Expected {PADHAVURAI_LABEL!r} in manual block") from exc

    if padhavurai_idx < 1:
        raise ValueError("Pasuram text missing before padhavurai")

    pasuram_lines = lines[:padhavurai_idx]
    last_line, pattu_number = extract_plain_pattu_suffix(pasuram_lines[-1])
    pasuram_lines[-1] = last_line
    pasuram = "\n".join(pasuram_lines)

    padham_rows = parse_manual_padham_rows("\n".join(lines[padhavurai_idx + 1 :]))
    if not padham_rows:
        raise ValueError(f"Pattu {pattu_number}: no padham rows in manual block")

    return PattuSection(
        pattu_number=pattu_number,
        pasuram=pasuram,
        title="",
        padham_rows=padham_rows,
    )


def parse_manual_file(path: Path | str) -> List[PattuSection]:
    text = Path(path).read_text(encoding="utf-8")
    normalized = normalize_manual_text(text)
    sections = [parse_manual_block(block) for block in split_manual_blocks(normalized)]
    sections.sort(key=lambda item: item.pattu_number)
    return sections


def summarize_manual_sections(sections: Sequence[PattuSection]) -> str:
    lines = [f"Manual pattus: {len(sections)}"]
    total_rows = sum(len(section.padham_rows) for section in sections)
    lines.append(f"Padham rows: {total_rows}")
    for section in sections:
        pasuram_number = PASURAM_NUMBER_BASE + section.pattu_number
        lines.append(
            f"  Pattu {section.pattu_number} ({pasuram_number}): "
            f"{len(section.padham_rows)} padhams"
        )
    return "\n".join(lines)
