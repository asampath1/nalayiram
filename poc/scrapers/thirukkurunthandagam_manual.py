"""Parse manually validated திருக்குறுந்தாண்டகம் blocks (POC, PasuramNumber 2032+)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Sequence

from poc.scrapers.thiruvozhukootrirukkai_tidley import PADHAVURAI_LABEL, PattuSection
from poc.scrapers.thiruvirutham_manual import (
    _collect_pasuram_lines,
    _find_pasuram_start,
    _is_padham_or_continuation,
    _non_empty_lines,
    _skip_blank_and_separators,
    _title_from_lines,
    is_separator_line,
    normalize_manual_text,
    parse_manual_padham_rows,
    split_manual_blocks,
)

PRABANDHAM = "திருக்குறுந்தாண்டகம்"
PASURAM_NUMBER_BASE = 2031
ALZWAR = "திருமங்கையாழ்வார்"
PATTU_SUFFIX_RE = re.compile(r"[–—-](\d+)[–—-]?\s*$")


def _is_block_separator(line: str) -> bool:
    stripped = line.strip()
    return stripped in {"—", "–", "-"} or is_separator_line(stripped)


def extract_pattu_suffix(line: str) -> tuple[str, int]:
    stripped = line.strip()
    match = PATTU_SUFFIX_RE.search(stripped)
    if not match:
        raise ValueError(f"Pattu suffix not found: {stripped[:80]!r}")
    pattu_number = int(match.group(1))
    body = stripped[: match.start()].rstrip()
    return body, pattu_number


def parse_manual_block(block: str) -> PattuSection:
    lines = _non_empty_lines(block)
    pasuram_lines, index = _collect_pasuram_lines(lines)
    last_line, pattu_number = extract_pattu_suffix(pasuram_lines[-1])
    pasuram_lines[-1] = last_line
    pasuram = "\n".join(pasuram_lines)

    if index >= len(lines):
        raise ValueError(f"Pattu {pattu_number}: expected padham rows after pasuram")
    label = lines[index].strip()
    if label == PADHAVURAI_LABEL:
        index += 1

    padham_line_chunks: List[str] = []
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            if padham_line_chunks:
                break
            continue
        if stripped.lower() == "title":
            break
        if _is_block_separator(stripped):
            break
        padham_line_chunks.append(stripped)
        index += 1

    padham_rows = parse_manual_padham_rows("\n".join(padham_line_chunks))
    if not padham_rows:
        raise ValueError(f"Pattu {pattu_number}: no padham rows in manual block")

    title_lines: List[str] = []
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.lower() == "title":
            index += 1
            continue
        if _is_block_separator(stripped):
            break
        title_lines.append(stripped)
        index += 1

    title = _title_from_lines(title_lines)
    if not title:
        raise ValueError(f"Pattu {pattu_number}: title block missing in manual input")

    return PattuSection(
        pattu_number=pattu_number,
        pasuram=pasuram,
        title=title,
        padham_rows=padham_rows,
    )


def parse_manual_file(path: Path | str) -> List[PattuSection]:
    text = Path(path).read_text(encoding="utf-8")
    normalized = normalize_manual_text(text)
    lines = normalized.splitlines()
    suffix_indices = [
        index for index, line in enumerate(lines) if line.strip() and PATTU_SUFFIX_RE.search(line)
    ]
    sections: List[PattuSection] = []
    region_start = 0

    for section_index, suffix_idx in enumerate(suffix_indices):
        pasuram_start = _find_pasuram_start(lines, suffix_idx, region_start)
        pasuram_lines = [
            lines[index].strip()
            for index in range(pasuram_start, suffix_idx + 1)
            if lines[index].strip()
        ]
        last_line, pattu_number = extract_pattu_suffix(pasuram_lines[-1])
        pasuram_lines[-1] = last_line
        pasuram = "\n".join(pasuram_lines)

        index = _skip_blank_and_separators(lines, suffix_idx + 1)
        if index < len(lines) and lines[index].strip() == PADHAVURAI_LABEL:
            index += 1

        padham_line_chunks: List[str] = []
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped:
                index += 1
                if padham_line_chunks:
                    break
                continue
            if stripped.lower() == "title":
                break
            if _is_block_separator(stripped):
                break
            if _is_padham_or_continuation(stripped):
                padham_line_chunks.append(stripped)
                index += 1
                continue
            if padham_line_chunks:
                break
            index += 1

        padham_rows = parse_manual_padham_rows("\n".join(padham_line_chunks))
        if not padham_rows:
            raise ValueError(f"Pattu {pattu_number}: no padham rows in manual block")

        next_pasuram_start = (
            _find_pasuram_start(lines, suffix_indices[section_index + 1], suffix_idx + 1)
            if section_index + 1 < len(suffix_indices)
            else len(lines)
        )
        title_lines: List[str] = []
        while index < next_pasuram_start:
            stripped = lines[index].strip()
            if stripped and stripped.lower() != "title" and not _is_block_separator(stripped):
                title_lines.append(stripped)
            index += 1
        title = _title_from_lines(title_lines)
        if not title:
            raise ValueError(f"Pattu {pattu_number}: title block missing in manual input")

        sections.append(
            PattuSection(
                pattu_number=pattu_number,
                pasuram=pasuram,
                title=title,
                padham_rows=padham_rows,
            )
        )
        region_start = next_pasuram_start

    sections.sort(key=lambda section: section.pattu_number)
    return sections


def summarize_manual_sections(sections: Sequence[PattuSection]) -> str:
    lines = [f"Manual pattus: {len(sections)}"]
    total_rows = sum(len(section.padham_rows) for section in sections)
    lines.append(f"Padham rows: {total_rows}")
    for section in sections[:5]:
        pasuram_number = PASURAM_NUMBER_BASE + section.pattu_number
        lines.append(
            f"  Pattu {section.pattu_number} ({pasuram_number}): "
            f"{len(section.padham_rows)} padhams"
        )
    if len(sections) > 5:
        lines.append("  ...")
    return "\n".join(lines)
