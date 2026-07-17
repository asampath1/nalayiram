"""Parse manually validated பெரிய திருமொழி pasuram blocks (POC)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

from poc.scrapers.periya_thirumozhi_tidley import (
    PathigamIngestConfig,
    _clean_verse_text,
    pattu_number_from_verse,
)
from poc.scrapers.thiruvozhukootrirukkai_tidley import PADHAVURAI_LABEL, PattuSection
from poc.scrapers.thiruvirutham_manual import (
    _collect_pasuram_lines,
    _non_empty_lines,
    _title_from_lines,
    is_separator_line,
    normalize_manual_text,
    parse_manual_padham_rows,
    split_manual_blocks,
)


def parse_manual_block(block: str, config: PathigamIngestConfig) -> PattuSection:
    lines = _non_empty_lines(block)
    pasuram_lines, index = _collect_pasuram_lines(lines)
    raw_pasuram = "\n".join(pasuram_lines)
    pattu_number = pattu_number_from_verse(raw_pasuram, config)
    pasuram = _clean_verse_text(raw_pasuram, config, pattu_number)

    if index >= len(lines):
        raise ValueError(f"Pattu {pattu_number}: expected {PADHAVURAI_LABEL!r} after pasuram")
    label = lines[index].strip()
    if label != PADHAVURAI_LABEL:
        raise ValueError(
            f"Pattu {pattu_number}: expected {PADHAVURAI_LABEL!r}, got {label[:40]!r}"
        )
    index += 1

    padham_line_chunks: List[str] = []
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            if padham_line_chunks:
                break
            continue
        if stripped.lower() == "title.":
            break
        if is_separator_line(stripped):
            break
        if stripped.startswith("(") and padham_line_chunks:
            break
        padham_line_chunks.append(stripped)
        index += 1

    padham_rows = parse_manual_padham_rows("\n".join(padham_line_chunks))
    if not padham_rows:
        raise ValueError(f"Pattu {pattu_number}: no padham rows in manual block")

    title_lines: List[str] = []
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.lower() == "title.":
            index += 1
            continue
        if is_separator_line(stripped):
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


def parse_manual_file(
    path: Path | str,
    config: PathigamIngestConfig,
) -> List[PattuSection]:
    text = Path(path).read_text(encoding="utf-8")
    normalized = normalize_manual_text(text)
    sections = [
        parse_manual_block(block, config) for block in split_manual_blocks(normalized)
    ]
    sections.sort(key=lambda section: section.pattu_number)
    return sections


def summarize_manual_sections(sections: Sequence[PattuSection]) -> str:
    from poc.scrapers.thiruvozhukootrirukkai_tidley import summarize_sections

    return summarize_sections(sections)
