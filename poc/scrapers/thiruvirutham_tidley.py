"""Scrape திருவிருத்தம் padham artham from tidley.com (POC, PasuramNumber 2478+)."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

from poc.scrapers.thiruvozhukootrirukkai_tidley import (
    PADHAVURAI_LABEL,
    PattuSection,
    fetch_hentry_elements,
    summarize_sections,
)
from poc.title_scrapers.base import PATTU_SUFFIX_RE, is_separator, join_title_blocks

# Slug uses தனியன் (not தனியான்) — the latter URL returns 404 on tidley.
TIDLEY_URL = (
    "https://tidley.com/2016/11/26/"
    "%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81-%e0%ae%b5%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%a4%e0%af%8d"
    "%e0%ae%a4%e0%ae%ae%e0%af%8d-%e0%ae%a4%e0%ae%a9%e0%ae%bf%e0%ae%af%e0%ae%a9%e0%af%8d-%e0%ae%aa%e0%ae%be/"
)
PRABANDHAM = "திருவிருத்தம்"
PASURAM_NUMBER_BASE = 2477
ALZWAR = "நம்மாழ்வார்"
START_MARKER = "பொய் நின்ற ஞானமும்"
DEFAULT_PATTU_LIMIT = 10

VERSE_TAIL_RE = re.compile(r"[—–\-–\s]+\d+\s*[-—–]?\s*$")
PADHAM_LINE_RE = re.compile(r"^(.+?)[–—-](.+)$")
PAREN_ONLY_RE = re.compile(r"^\(.+\)$")


def clean_pasuram_text(text: str) -> str:
    lines: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = VERSE_TAIL_RE.sub("", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _paragraph_text(element: Any) -> str:
    return element.get_text("\n", strip=True)


def _is_pasuram_paragraph(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    return bool(PATTU_SUFFIX_RE.search(lines[-1]))


def _strip_padhavurai_label(text: str) -> str:
    text = text.strip()
    if text == PADHAVURAI_LABEL:
        return ""
    if text.startswith(PADHAVURAI_LABEL):
        remainder = text[len(PADHAVURAI_LABEL) :].strip()
        return remainder
    return text


def _is_padham_line(line: str) -> bool:
    line = line.strip()
    if not line or line == "—" or line == "-":
        return False
    if PAREN_ONLY_RE.match(line):
        return False
    match = PADHAM_LINE_RE.match(line)
    if not match:
        return False
    padham, meaning = match.group(1).strip(), match.group(2).strip()
    return bool(padham and meaning)


def _paragraph_is_padham_block(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    substantive = [line for line in lines if not PAREN_ONLY_RE.match(line)]
    if not substantive:
        return False
    return all(_is_padham_line(line) for line in substantive)


def parse_padham_rows(text: str) -> List[tuple[str, str]]:
    text = _strip_padhavurai_label(text)
    rows: List[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
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
        if padham and meaning:
            rows.append((padham, meaning))
    return rows


def fetch_hentry_elements_with_retry(url: str = TIDLEY_URL, timeout: int = 30, attempts: int = 3) -> List[Any]:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return fetch_hentry_elements(url, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - retry transient tidley failures
            last_error = exc
    raise RuntimeError(f"Could not fetch tidley page after {attempts} attempts: {url}") from last_error


def find_start_index(elements: Sequence[Any]) -> int:
    for index, element in enumerate(elements):
        if element.name != "p":
            continue
        text = _paragraph_text(element)
        if text.startswith(START_MARKER) and _is_pasuram_paragraph(text):
            return index
    raise RuntimeError(f"Start marker not found: {START_MARKER}")


def _has_padhavurai_after(elements: Sequence[Any], pasuram_index: int) -> bool:
    """Ignore citation paragraphs that end with a verse-like suffix but have no பதவுரை."""
    for probe in range(pasuram_index + 1, min(pasuram_index + 4, len(elements))):
        element = elements[probe]
        if element.name != "p":
            continue
        text = _paragraph_text(element).strip()
        if is_separator(text):
            return False
        if text == PADHAVURAI_LABEL or text.startswith(PADHAVURAI_LABEL):
            return True
        if _is_pasuram_paragraph(text):
            return False
    return False


def _find_pasuram_indices(elements: Sequence[Any], start_index: int) -> List[int]:
    indices: List[int] = []
    for index in range(start_index, len(elements)):
        element = elements[index]
        if element.name != "p":
            continue
        text = _paragraph_text(element)
        if _is_pasuram_paragraph(text) and _has_padhavurai_after(elements, index):
            indices.append(index)
    return indices


def _section_end_index(elements: Sequence[Any], start_index: int) -> int:
    for index in range(start_index + 1, len(elements)):
        element = elements[index]
        if element.name != "p":
            continue
        text = _paragraph_text(element)
        if is_separator(text):
            return index
        if _is_pasuram_paragraph(text):
            return index
    return len(elements)


def _extract_title(paragraphs: Sequence[str]) -> str:
    if not paragraphs:
        return ""
    return join_title_blocks([paragraphs[0]])


def parse_pattu_section(
    elements: Sequence[Any],
    pasuram_index: int,
    *,
    pattu_number: int,
) -> PattuSection:
    pasuram = clean_pasuram_text(_paragraph_text(elements[pasuram_index]))
    end_index = _section_end_index(elements, pasuram_index)

    cursor = pasuram_index + 1
    if cursor < end_index and _paragraph_text(elements[cursor]).strip() == PADHAVURAI_LABEL:
        cursor += 1

    padham_paragraphs: List[str] = []
    title_paragraphs: List[str] = []

    while cursor < end_index:
        element = elements[cursor]
        if element.name != "p":
            cursor += 1
            continue
        text = _paragraph_text(element)
        if not text or text.strip() == PADHAVURAI_LABEL:
            cursor += 1
            continue

        stripped = _strip_padhavurai_label(text)
        if not title_paragraphs and (
            _paragraph_is_padham_block(stripped) or (not padham_paragraphs and parse_padham_rows(stripped))
        ):
            padham_paragraphs.append(stripped)
            cursor += 1
            continue

        title_paragraphs.append(text)
        cursor += 1

    padham_text = "\n".join(padham_paragraphs)
    padham_rows = parse_padham_rows(padham_text)
    if not padham_rows:
        raise RuntimeError(f"Pattu {pattu_number}: no padham rows parsed")

    return PattuSection(
        pattu_number=pattu_number,
        pasuram=pasuram,
        title=_extract_title(title_paragraphs),
        padham_rows=padham_rows,
    )


def parse_pattu_sections(
    elements: Sequence[Any] | None = None,
    *,
    url: str = TIDLEY_URL,
    pattu_limit: int | None = DEFAULT_PATTU_LIMIT,
) -> List[PattuSection]:
    if elements is None:
        elements = fetch_hentry_elements_with_retry(url)

    start_index = find_start_index(elements)
    pasuram_indices = _find_pasuram_indices(elements, start_index)
    if not pasuram_indices:
        raise RuntimeError("No pasuram paragraphs found after start marker")

    if pattu_limit is not None:
        pasuram_indices = pasuram_indices[:pattu_limit]

    sections: List[PattuSection] = []
    for pattu_number, pasuram_index in enumerate(pasuram_indices, start=1):
        sections.append(
            parse_pattu_section(
                elements,
                pasuram_index,
                pattu_number=pattu_number,
            )
        )
    return sections


def sections_to_records(
    sections: Sequence[PattuSection],
    *,
    prabandham: str = PRABANDHAM,
    pasuram_number_base: int = PASURAM_NUMBER_BASE,
    alzwar: str = ALZWAR,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for section in sections:
        pasuram_number = pasuram_number_base + section.pattu_number
        for padham_number, (padham, meaning) in enumerate(section.padham_rows, start=1):
            records.append(
                {
                    "Prabandham": prabandham,
                    "PasuramNumber": pasuram_number,
                    "Pasuram": section.pasuram,
                    "PattuNumber": section.pattu_number,
                    "Padham": padham,
                    "Meaning": meaning,
                    "Alzwar": alzwar,
                    "PadhamNumber": padham_number,
                    "Title": section.title,
                    "Word": "",
                    "SimilarWords": "",
                    "NithyaanusandhamIndex": None,
                    "PrabandhamTitle": prabandham,
                }
            )
    return records


def scrape_thiruvirutham(
    url: str = TIDLEY_URL,
    *,
    pattu_limit: int | None = DEFAULT_PATTU_LIMIT,
) -> List[Dict[str, Any]]:
    sections = parse_pattu_sections(url=url, pattu_limit=pattu_limit)
    return sections_to_records(sections)


def write_review_csv(sections: Sequence[PattuSection], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "PattuNumber",
                "PasuramNumber",
                "PadhamNumber",
                "Padham",
                "Meaning",
                "Pasuram",
                "Title",
                "padham_count",
            ]
        )
        for section in sections:
            pasuram_number = PASURAM_NUMBER_BASE + section.pattu_number
            for padham_number, (padham, meaning) in enumerate(section.padham_rows, start=1):
                writer.writerow(
                    [
                        section.pattu_number,
                        pasuram_number,
                        padham_number,
                        padham,
                        meaning,
                        section.pasuram.replace("\n", " / "),
                        section.title,
                        len(section.padham_rows),
                    ]
                )
