"""Parse manually validated Thiruvirutham pasuram blocks (POC)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Sequence

from poc.scrapers.thiruvozhukootrirukkai_tidley import PADHAVURAI_LABEL, PattuSection
from poc.scrapers.thiruvirutham_tidley import (
    PASURAM_NUMBER_BASE,
    _extract_title,
    clean_pasuram_text,
)
from poc.title_scrapers.base import PATTU_SUFFIX_RE, join_title_blocks

BLOCK_SEPARATOR_RE = re.compile(r"^——+\s*$", re.MULTILINE)
LINE_BREAK_RE = re.compile(r"[\u2028\u2029]")
SEP_LINE_RE = re.compile(r"^[-—–\u2014\s]{6,}$")
SHORT_SECTION_SEPARATOR_RE = re.compile(r"^——{1,6}\s*$")
TITLE_INTRO_MARKERS = (
    "பாசுரம்",
    "துறை",
    "அவதாரிகை",
    "இப்பாட்ட",
    "சொல்வது",
)


def normalize_manual_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = LINE_BREAK_RE.sub("\n", text)
    return text.strip()


def split_manual_blocks(text: str) -> List[str]:
    text = normalize_manual_text(text)
    blocks = [block.strip() for block in BLOCK_SEPARATOR_RE.split(text) if block.strip()]
    return blocks


def _non_empty_lines(block: str) -> List[str]:
    return [line.strip() for line in block.splitlines() if line.strip()]


def is_separator_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if SHORT_SECTION_SEPARATOR_RE.match(stripped):
        return True
    if SEP_LINE_RE.match(stripped):
        return True
    chars = stripped.replace(" ", "")
    return len(chars) >= 6 and all(ch in "-—–\u2014" for ch in chars)


def _looks_like_title_block(lines: Sequence[str]) -> bool:
    text = " ".join(lines)
    return any(marker in text for marker in TITLE_INTRO_MARKERS)


def _collect_immediate_pre_title(lines: Sequence[str], pasuram_start: int) -> List[str]:
    index = pasuram_start - 1
    while index >= 0 and not lines[index].strip():
        index -= 1
    if index < 0:
        return []

    collected: List[str] = []
    while index >= 0:
        stripped = lines[index].strip()
        if not stripped or is_separator_line(stripped) or stripped == PADHAVURAI_LABEL:
            break
        collected.insert(0, stripped)
        index -= 1
    return collected


def _collect_pre_title_before_pasuram(
    lines: Sequence[str],
    pasuram_start: int,
) -> List[str]:
    return _collect_immediate_pre_title(lines, pasuram_start)


def find_pasuram_suffix_indices(lines: Sequence[str]) -> List[int]:
    indices: List[int] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped and PATTU_SUFFIX_RE.search(stripped):
            indices.append(index)
    return indices


def _find_pasuram_start(lines: Sequence[str], suffix_idx: int, min_idx: int = 0) -> int:
    """Walk back from the suffix line through verse lines; stop at blank or separator."""
    start = suffix_idx
    while start > min_idx:
        previous = lines[start - 1].strip()
        if not previous or is_separator_line(previous):
            break
        start -= 1
    return start


def _skip_blank_and_separators(lines: Sequence[str], index: int) -> int:
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or is_separator_line(stripped):
            index += 1
            continue
        break
    return index


def _extract_pattu_number(pasuram_line: str) -> int:
    match = PATTU_SUFFIX_RE.search(pasuram_line)
    if not match:
        raise ValueError(f"Pasuram suffix not found: {pasuram_line[:80]!r}")
    return int(match.group(1))


def _collect_pasuram_lines(lines: Sequence[str]) -> tuple[List[str], int]:
    pasuram_lines: List[str] = []
    index = 0
    while index < len(lines):
        pasuram_lines.append(lines[index])
        if PATTU_SUFFIX_RE.search(lines[index]):
            index += 1
            break
        index += 1
    if not pasuram_lines or not PATTU_SUFFIX_RE.search(pasuram_lines[-1]):
        raise ValueError("Pasuram text with suffix not found in manual block")
    return pasuram_lines, index


def _first_title_paragraph(lines: Sequence[str]) -> str:
    groups: List[List[str]] = [[]]
    for line in lines:
        if not line.strip():
            if groups[-1]:
                groups.append([])
            continue
        groups[-1].append(line.strip())
    non_empty = [group for group in groups if group]
    if not non_empty:
        return ""
    return join_title_blocks(["\n".join(non_empty[0])])


PADHAM_LINE_RE = re.compile(r"^(.+?)[–—-](.*)$")
PAREN_ONLY_RE = re.compile(r"^\(.+\)$")
TITLE_LINE_MARKERS = (
    "துறை பாசுரம்",
    "அவதாரிகை",
    "அவதாரிகை-",
)


def _normalize_padham_line(line: str) -> str:
    stripped = line.strip()
    if re.search(r"[–—-]", stripped):
        return stripped
    if stripped.endswith("இது;"):
        return f"{stripped[:-4].strip()}–இது"
    return stripped


def parse_manual_padham_rows(text: str) -> List[tuple[str, str]]:
    rows: List[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = _normalize_padham_line(raw_line)
        if not line:
            continue
        if PAREN_ONLY_RE.match(line):
            if rows:
                padham, meaning = rows[-1]
                rows[-1] = (padham, f"{meaning} {line}")
            continue
        match = PADHAM_LINE_RE.match(line)
        if not match:
            continue
        padham = match.group(1).strip()
        meaning = match.group(2).strip()
        if not padham:
            continue
        if not meaning:
            meaning = padham
        rows.append((padham, meaning))
    return rows


def _is_title_line(line: str) -> bool:
    stripped = line.strip()
    if any(marker in stripped for marker in TITLE_LINE_MARKERS):
        return True
    return False


def _is_padham_or_continuation(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped in {"—", "-"}:
        return False
    if stripped.startswith("("):
        return True
    if _is_title_line(stripped):
        return False
    normalized = _normalize_padham_line(stripped)
    return bool(PADHAM_LINE_RE.match(normalized))


def _collect_pre_title_lines(
    lines: Sequence[str],
    start_idx: int,
    pasuram_start: int,
) -> List[str]:
    pre_title: List[str] = []
    for index in range(start_idx, pasuram_start):
        stripped = lines[index].strip()
        if stripped and not is_separator_line(stripped):
            pre_title.append(stripped)
    return pre_title


def _collect_post_title_lines(
    lines: Sequence[str],
    start_idx: int,
    end_idx: int,
) -> List[str]:
    post_title: List[str] = []
    for index in range(start_idx, end_idx):
        stripped = lines[index].strip()
        if stripped and not is_separator_line(stripped):
            post_title.append(stripped)
    return post_title


def _title_from_lines(lines: Sequence[str]) -> str:
    cleaned = [line.strip() for line in lines if line.strip() and not is_separator_line(line)]
    if not cleaned:
        return ""
    return join_title_blocks(["\n".join(cleaned)])


def _title_before_pasuram_layout(lines: Sequence[str], suffix_indices: Sequence[int]) -> bool:
    first_suffix = suffix_indices[0]
    first_pasuram_start = _find_pasuram_start(lines, first_suffix, 0)
    pre_title = _collect_pre_title_lines(lines, 0, first_pasuram_start)
    return bool(pre_title)


def parse_manual_stream(text: str) -> List[PattuSection]:
    normalized = normalize_manual_text(text)
    lines = normalized.splitlines()
    suffix_indices = find_pasuram_suffix_indices(lines)
    if not suffix_indices:
        return []

    title_before_pasuram = _title_before_pasuram_layout(lines, suffix_indices)
    sections: List[PattuSection] = []
    region_start = 0

    for section_index, suffix_idx in enumerate(suffix_indices):
        pasuram_start = _find_pasuram_start(lines, suffix_idx, region_start)

        pasuram_lines = [
            lines[index].strip()
            for index in range(pasuram_start, suffix_idx + 1)
            if lines[index].strip()
        ]
        pattu_number = _extract_pattu_number(pasuram_lines[-1])
        pasuram = clean_pasuram_text("\n".join(pasuram_lines))

        index = _skip_blank_and_separators(lines, suffix_idx + 1)
        if index >= len(lines):
            raise ValueError(f"Pattu {pattu_number}: expected {PADHAVURAI_LABEL!r} after pasuram")
        label = lines[index].strip()
        if label != PADHAVURAI_LABEL:
            raise ValueError(
                f"Pattu {pattu_number}: expected {PADHAVURAI_LABEL!r} after pasuram, got {label[:40]!r}"
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
            if is_separator_line(stripped):
                break
            if _is_padham_or_continuation(stripped):
                padham_line_chunks.append(stripped)
                index += 1
                continue
            if padham_line_chunks:
                padham_line_chunks[-1] += stripped
                index += 1
                continue
            break

        padham_rows = parse_manual_padham_rows("\n".join(padham_line_chunks))
        if not padham_rows:
            raise ValueError(f"Pattu {pattu_number}: no padham rows in manual block")

        padham_end = index
        if section_index + 1 < len(suffix_indices):
            next_suffix_idx = suffix_indices[section_index + 1]
            next_pasuram_start = _find_pasuram_start(lines, next_suffix_idx, suffix_idx + 1)
        else:
            next_pasuram_start = len(lines)

        if title_before_pasuram:
            title = _title_from_lines(
                _collect_pre_title_before_pasuram(lines, pasuram_start)
            )
            region_start = padham_end
        else:
            post_title = _collect_post_title_lines(lines, padham_end, next_pasuram_start)
            title = _title_from_lines(post_title)
            region_start = next_pasuram_start

        sections.append(
            PattuSection(
                pattu_number=pattu_number,
                pasuram=pasuram,
                title=title,
                padham_rows=padham_rows,
            )
        )

    return sections


def parse_manual_block(block: str) -> PattuSection:
    lines = _non_empty_lines(block)
    pasuram_lines, index = _collect_pasuram_lines(lines)
    pattu_number = _extract_pattu_number(pasuram_lines[-1])
    pasuram = clean_pasuram_text("\n".join(pasuram_lines))

    if index >= len(lines) or lines[index] != PADHAVURAI_LABEL:
        raise ValueError(f"Pattu {pattu_number}: expected {PADHAVURAI_LABEL!r} after pasuram")
    index += 1

    padham_line_chunks: List[str] = []
    while index < len(lines):
        line = lines[index]
        if _is_padham_or_continuation(line):
            padham_line_chunks.append(line)
        elif padham_line_chunks:
            padham_line_chunks[-1] += line
        else:
            break
        index += 1

    padham_rows = parse_manual_padham_rows("\n".join(padham_line_chunks))
    if not padham_rows:
        raise ValueError(f"Pattu {pattu_number}: no padham rows in manual block")

    title = _first_title_paragraph(lines[index:])
    if not title:
        title = _extract_title(lines[index:])

    return PattuSection(
        pattu_number=pattu_number,
        pasuram=pasuram,
        title=title,
        padham_rows=padham_rows,
    )


def parse_manual_file(
    path: Path | str,
    *,
    pattu_start: int | None = None,
    pattu_end: int | None = None,
) -> List[PattuSection]:
    text = Path(path).read_text(encoding="utf-8")
    normalized = normalize_manual_text(text)
    suffix_count = len(find_pasuram_suffix_indices(normalized.splitlines()))

    if suffix_count >= 2:
        sections = parse_manual_stream(normalized)
    else:
        sections = [parse_manual_block(block) for block in split_manual_blocks(normalized)]

    if pattu_start is not None:
        sections = [section for section in sections if section.pattu_number >= pattu_start]
    if pattu_end is not None:
        sections = [section for section in sections if section.pattu_number <= pattu_end]
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
            f"{len(section.padham_rows)} padhams, title_len={len(section.title)}"
        )
    return "\n".join(lines)
