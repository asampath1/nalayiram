"""Scrape திருவெழுகூற்றிருக்கை padham artham from tidley.com (POC, PasuramNumber 2672)."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

import requests
from bs4 import BeautifulSoup

from poc.title_scrapers.base import join_title_blocks

TIDLEY_URL = (
    "https://tidley.com/2022/12/05/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%b5%e0%af%86%e0%ae%b4%e0%af%81-"
    "%e0%ae%95%e0%af%82%e0%ae%b1%e0%af%8d%e0%ae%b1%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%95-2/"
)
PRABANDHAM = "திருவெழுகூற்றிருக்கை"
PASURAM_NUMBER = 2672
ALZWAR = "திருமங்கையாழ்வார்"
START_MARKER = "ஒருபே ருந்தி யிருமலர்த் தவிசில்"
PADHAVURAI_LABEL = "பதவுரை"

SEPARATOR_RE = re.compile(r"^[-—–\s]+$")
COMMENTARY_STARTS = (
    "கீழ்",
    "அம்பாலே",
    "இந்த",
    "தேவ",
    "உலக",
    "***",
    "தேவதை",
    "நானிலம்",
    "“",
    '"',
)


@dataclass(frozen=True)
class PattuSection:
    pattu_number: int
    pasuram: str
    title: str
    padham_rows: List[tuple[str, str]]


def _is_separator(text: str) -> bool:
    stripped = text.strip()
    return bool(SEPARATOR_RE.match(stripped)) and len(stripped.replace(" ", "")) >= 3


def _is_likely_verse(text: str) -> bool:
    text = text.strip()
    if not text or len(text) > 220:
        return False
    if text == PADHAVURAI_LABEL:
        return False
    if any(text.startswith(prefix) for prefix in COMMENTARY_STARTS):
        return False
    if "என்றார்" in text or "என்கைக்காக" in text or "என்க." in text:
        return False
    if "," in text:
        return True
    return len(text) < 120


def format_pasuram_comma_lines(text: str) -> str:
    """Split pasuram on commas into separate lines (comma kept at end of each clause)."""
    text = text.strip()
    if not text:
        return text
    if "\n" in text:
        return "\n".join(
            format_pasuram_comma_lines(line) for line in text.split("\n") if line.strip()
        )

    parts = re.split(r",", text)
    lines: List[str] = []
    trailing_comma = text.rstrip().endswith(",")
    for index, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if index < len(parts) - 1 or trailing_comma:
            lines.append(f"{part},")
        else:
            lines.append(part)
    return "\n".join(lines)


def _split_title_pasuram(block: Sequence[str]) -> tuple[str, str]:
    if not block:
        return "", ""
    lines = list(block)
    verses: List[str] = []
    while lines and _is_likely_verse(lines[-1]):
        verses.insert(0, lines.pop())
    if not verses and lines:
        verses = [lines.pop()]
    title = join_title_blocks(lines)
    pasuram = format_pasuram_comma_lines("\n".join(verses))
    return title, pasuram


def _parse_table_rows(table) -> List[tuple[str, str]]:
    rows: List[tuple[str, str]] = []
    for tr in table.find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in tr.find_all(["td", "th"])]
        cells = [c for c in cells if c and c != "–" and c != "-"]
        if len(cells) < 2:
            continue
        padham = cells[0]
        meaning = cells[-1]
        if not padham or not meaning:
            continue
        if padham == PADHAVURAI_LABEL or meaning == PADHAVURAI_LABEL:
            continue
        rows.append((padham, meaning))
    return rows


def fetch_hentry_elements(url: str = TIDLEY_URL, timeout: int = 30) -> List[Any]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    hentry = soup.select_one(".hentry")
    if hentry is None:
        raise RuntimeError(f"Could not find .hentry on tidley page: {url}")

    elements: List[Any] = []
    for element in hentry.find_all(["p", "table"]):
        if element.name != "table" and element.find_parent("table"):
            continue
        elements.append(element)
    return elements


def find_start_index(elements: Sequence[Any]) -> int:
    candidates: List[int] = []
    for index, element in enumerate(elements):
        if element.name != "p":
            continue
        text = element.get_text(strip=True)
        if text.startswith(START_MARKER) and "அயனை" in text:
            candidates.append(index)

    for index in reversed(candidates):
        probe = index + 1
        while probe < len(elements) and elements[probe].name == "p" and not elements[probe].get_text(strip=True):
            probe += 1
        if probe < len(elements) and elements[probe].name == "p":
            if elements[probe].get_text(strip=True) == PADHAVURAI_LABEL:
                return index

    if not candidates:
        raise RuntimeError(f"Start marker not found: {START_MARKER}")
    return candidates[-1]


def _paragraphs_between(
    elements: Sequence[Any],
    start_index: int,
    end_index: int,
    *,
    inclusive_start: bool = False,
) -> List[str]:
    chunk: List[str] = []
    begin = start_index if inclusive_start else start_index + 1
    for index in range(begin, end_index):
        element = elements[index]
        if element.name != "p":
            continue
        text = element.get_text(strip=True)
        if text and text != PADHAVURAI_LABEL:
            chunk.append(text)
    return chunk


def _last_block_after_separator(paragraphs: Sequence[str]) -> List[str]:
    blocks: List[List[str]] = [[]]
    for text in paragraphs:
        if _is_separator(text):
            blocks.append([])
        else:
            blocks[-1].append(text)
    non_empty = [block for block in blocks if block]
    return non_empty[-1] if non_empty else []


def parse_pattu_sections(elements: Sequence[Any] | None = None) -> List[PattuSection]:
    if elements is None:
        elements = fetch_hentry_elements()

    start_index = find_start_index(elements)
    table_indices = [i for i, element in enumerate(elements) if element.name == "table" and i > start_index]
    if not table_indices:
        raise RuntimeError("No padham tables found after start marker")

    sections: List[PattuSection] = []
    previous_table_index = start_index

    for pattu_number, table_index in enumerate(table_indices, start=1):
        if pattu_number == 1:
            between = _paragraphs_between(
                elements, start_index, table_index, inclusive_start=True
            )
        else:
            between = _paragraphs_between(elements, previous_table_index, table_index)
        last_block = _last_block_after_separator(between)
        title, pasuram = _split_title_pasuram(last_block)
        padham_rows = _parse_table_rows(elements[table_index])
        if not padham_rows:
            raise RuntimeError(f"Pattu {pattu_number}: table has no padham rows")

        sections.append(
            PattuSection(
                pattu_number=pattu_number,
                pasuram=pasuram,
                title=title,
                padham_rows=padham_rows,
            )
        )
        previous_table_index = table_index

    return sections


def sections_to_records(
    sections: Sequence[PattuSection],
    *,
    prabandham: str = PRABANDHAM,
    pasuram_number: int = PASURAM_NUMBER,
    alzwar: str = ALZWAR,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for section in sections:
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


def scrape_thiruvozhukootrirukkai(url: str = TIDLEY_URL) -> List[Dict[str, Any]]:
    elements = fetch_hentry_elements(url)
    sections = parse_pattu_sections(elements)
    return sections_to_records(sections)


def write_review_csv(sections: Sequence[PattuSection], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "PattuNumber",
                "PadhamNumber",
                "Padham",
                "Meaning",
                "Pasuram",
                "Title",
                "padham_count",
            ]
        )
        for section in sections:
            for padham_number, (padham, meaning) in enumerate(section.padham_rows, start=1):
                writer.writerow(
                    [
                        section.pattu_number,
                        padham_number,
                        padham,
                        meaning,
                        section.pasuram.replace("\n", " / "),
                        section.title,
                        len(section.padham_rows),
                    ]
                )


def summarize_sections(sections: Sequence[PattuSection]) -> str:
    lines = [f"Pattus: {len(sections)}"]
    total_rows = sum(len(section.padham_rows) for section in sections)
    lines.append(f"Padham rows: {total_rows}")
    for section in sections[:3]:
        lines.append(
            f"  Pattu {section.pattu_number}: {len(section.padham_rows)} padhams, "
            f"title_len={len(section.title)}, pasuram={section.pasuram[:50]!r}..."
        )
    return "\n".join(lines)
