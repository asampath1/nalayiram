"""Scrape ஸ்ரீ திருச்சந்த விருத்தம் padham artham from tidley.com (POC, PasuramNumber 752–871)."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from poc.scrapers.thiruvozhukootrirukkai_tidley import (
    PADHAVURAI_LABEL,
    PattuSection,
    _is_separator,
    _parse_table_rows,
    fetch_hentry_elements,
    summarize_sections,
)
from poc.scrapers.thiruvirutham_tidley import parse_padham_rows
from poc.title_scrapers.base import PATTU_SUFFIX_RE, extract_pattu_number, is_separator

PRABANDHAM = "ஸ்ரீ திருச்சந்த விருத்தம்"
PASURAM_NUMBER_BASE = 751
ALZWAR = "திருமழிசையாழ்வார்"
MANUAL_PADHAM_JSON = Path(__file__).resolve().parent.parent / "input" / "thiruchanda_manual_padham.json"

TIDLEY_BATCH_URLS: List[Tuple[int, int, str]] = [
    (
        1,
        20,
        "https://tidley.com/2020/02/09/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%9a%e0%af%8d%e0%ae%9a%e0%ae%a8%e0%af%8d%e0%ae%a4-%e0%ae%b5%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%a4%e0%af%8d%e0%ae%a4%e0%ae%ae/",
    ),
    (
        21,
        40,
        "https://tidley.com/2020/02/09/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%9a%e0%af%8d%e0%ae%9a%e0%ae%a8%e0%af%8d%e0%ae%a4-%e0%ae%b5%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%a4%e0%af%8d%e0%ae%a4-2/",
    ),
    (
        41,
        60,
        "https://tidley.com/2020/02/09/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%9a%e0%af%8d%e0%ae%9a%e0%ae%a8%e0%af%8d%e0%ae%a4-%e0%ae%b5%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%a4%e0%af%8d%e0%ae%a4-3/",
    ),
    (
        61,
        80,
        "https://tidley.com/2020/02/10/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%9a%e0%af%8d%e0%ae%9a%e0%ae%a8%e0%af%8d%e0%ae%a4-%e0%ae%b5%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%a4%e0%af%8d%e0%ae%a4-6/",
    ),
    (
        81,
        100,
        "https://tidley.com/2020/02/09/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%9a%e0%af%8d%e0%ae%9a%e0%ae%a8%e0%af%8d%e0%ae%a4-%e0%ae%b5%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%a4%e0%af%8d%e0%ae%a4-4/",
    ),
    (
        101,
        120,
        "https://tidley.com/2020/02/10/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%9a%e0%af%8d%e0%ae%9a%e0%ae%a8%e0%af%8d%e0%ae%a4-%e0%ae%b5%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%a4%e0%af%8d%e0%ae%a4-5/",
    ),
]

VERSE_TAIL_RE = re.compile(r"[—–\-–\s]+\d+\s*[-—–]?\s*$")


def load_manual_padham_rows(path: Path = MANUAL_PADHAM_JSON) -> Dict[int, List[Tuple[str, str]]]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {int(key): [(padham, meaning) for padham, meaning in rows] for key, rows in raw.items()}


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


def _find_pasuram_indices(elements: Sequence[Any]) -> List[int]:
    indices: List[int] = []
    for index, element in enumerate(elements):
        if element.name != "p":
            continue
        text = _paragraph_text(element)
        if _is_pasuram_paragraph(text):
            indices.append(index)
    return indices


def _first_table_index(elements: Sequence[Any], start_index: int, end_index: int) -> int | None:
    for index in range(start_index + 1, end_index):
        if elements[index].name == "table":
            return index
    return None


def _paragraph_texts_between(elements: Sequence[Any], start_index: int, end_index: int) -> List[str]:
    texts: List[str] = []
    for index in range(start_index + 1, end_index):
        element = elements[index]
        if element.name != "p":
            continue
        text = _paragraph_text(element).strip()
        if not text or text == PADHAVURAI_LABEL or is_separator(text) or _is_separator(text):
            continue
        texts.append(text)
    return texts


def _padham_rows_from_paragraphs(paragraphs: Sequence[str]) -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    for paragraph in paragraphs:
        rows.extend(parse_padham_rows(paragraph))
    return rows


def _fallback_rows_from_pasuram(pasuram: str) -> List[Tuple[str, str]]:
    lines = [line.strip() for line in pasuram.splitlines() if line.strip()]
    if not lines:
        return [("", "")]
    return [(line, "") for line in lines]


def parse_pattu_section(
    elements: Sequence[Any],
    pasuram_index: int,
    end_index: int,
    *,
    pattu_number: int,
    manual_rows: Dict[int, List[Tuple[str, str]]],
) -> PattuSection:
    pasuram = clean_pasuram_text(_paragraph_text(elements[pasuram_index]))

    if pattu_number in manual_rows:
        padham_rows = list(manual_rows[pattu_number])
    else:
        padham_rows: List[Tuple[str, str]] = []
        table_index = _first_table_index(elements, pasuram_index, end_index)
        if table_index is not None:
            padham_rows = _parse_table_rows(elements[table_index])
        if not padham_rows:
            padham_rows = _padham_rows_from_paragraphs(
                _paragraph_texts_between(elements, pasuram_index, end_index)
            )
        if not padham_rows:
            padham_rows = _fallback_rows_from_pasuram(pasuram)

    if not padham_rows:
        raise RuntimeError(f"Pattu {pattu_number}: no padham rows parsed")

    return PattuSection(
        pattu_number=pattu_number,
        pasuram=pasuram,
        title="",
        padham_rows=padham_rows,
    )


def parse_page_sections(
    elements: Sequence[Any],
    *,
    pattu_start: int,
    pattu_end: int,
    manual_rows: Dict[int, List[Tuple[str, str]]],
) -> List[PattuSection]:
    pasuram_indices = _find_pasuram_indices(elements)
    if not pasuram_indices:
        raise RuntimeError("No pasuram paragraphs found on page")

    sections: List[PattuSection] = []
    for position, pasuram_index in enumerate(pasuram_indices):
        end_index = pasuram_indices[position + 1] if position + 1 < len(pasuram_indices) else len(elements)
        suffix_line = _paragraph_text(elements[pasuram_index]).splitlines()[-1]
        pattu_number = extract_pattu_number(suffix_line)
        if pattu_number < pattu_start or pattu_number > pattu_end:
            raise RuntimeError(
                f"Unexpected pattu {pattu_number} on page (expected {pattu_start}-{pattu_end})"
            )
        sections.append(
            parse_pattu_section(
                elements,
                pasuram_index,
                end_index,
                pattu_number=pattu_number,
                manual_rows=manual_rows,
            )
        )

    expected = pattu_end - pattu_start + 1
    if len(sections) != expected:
        raise RuntimeError(
            f"Expected {expected} pattus ({pattu_start}-{pattu_end}), found {len(sections)}"
        )
    return sections


def parse_all_sections(
    urls: Sequence[Tuple[int, int, str]] | None = None,
    *,
    manual_rows: Dict[int, List[Tuple[str, str]]] | None = None,
) -> List[PattuSection]:
    manual_rows = manual_rows if manual_rows is not None else load_manual_padham_rows()
    sections: List[PattuSection] = []
    for pattu_start, pattu_end, url in urls or TIDLEY_BATCH_URLS:
        elements = fetch_hentry_elements(url)
        sections.extend(
            parse_page_sections(
                elements,
                pattu_start=pattu_start,
                pattu_end=pattu_end,
                manual_rows=manual_rows,
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
                    "Title": "",
                    "Word": "",
                    "SimilarWords": "",
                    "NithyaanusandhamIndex": None,
                    "PrabandhamTitle": prabandham,
                }
            )
    return records


def scrape_thiruchanda() -> List[Dict[str, Any]]:
    sections = parse_all_sections()
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
                        len(section.padham_rows),
                    ]
                )
