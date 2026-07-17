"""Scrape பெரிய திருமடல் padham artham from tidley.com (POC, PasuramNumber 2674)."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from poc.scrapers.thiruvozhukootrirukkai_tidley import (
    PADHAVURAI_LABEL,
    PattuSection,
    _parse_table_rows,
    fetch_hentry_elements,
    summarize_sections,
)

TIDLEY_URLS = (
    "https://tidley.com/2022/12/06/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%ae%bf%e0%ae%af-"
    "%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%9f%e0%ae%b2%e0%af%8d-%e0%ae%aa%e0%ae%95%e0%af%81%e0%ae%a4/",
    "https://tidley.com/2022/12/06/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%ae%bf%e0%ae%af-"
    "%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%9f%e0%ae%b2%e0%af%8d-%e0%ae%aa%e0%ae%95%e0%af%81%e0%ae%a4-2/",
)
PRABANDHAM = "பெரிய திருமடல்"
PASURAM_NUMBER = 2674
ALZWAR = "திருமங்கை ஆழ்வார்"
VERSE_TAIL_RE = re.compile(r"[—–\-–\s]+\d+\s*$")


def clean_pasuram_text(text: str) -> str:
    """Strip tidley verse-number suffixes (e.g. ———-1) from pasuram lines."""
    lines: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = VERSE_TAIL_RE.sub("", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _find_padhavurai_indices(elements: Sequence[Any]) -> List[int]:
    indices: List[int] = []
    for index, element in enumerate(elements):
        if element.name == "p" and element.get_text(strip=True) == PADHAVURAI_LABEL:
            indices.append(index)
    return indices


def _pasuram_before_padhavurai(elements: Sequence[Any], padhavurai_index: int) -> str:
    if padhavurai_index <= 0:
        raise RuntimeError(f"No paragraph before {PADHAVURAI_LABEL} at index {padhavurai_index}")
    previous = elements[padhavurai_index - 1]
    if previous.name != "p":
        raise RuntimeError(
            f"Expected paragraph immediately before {PADHAVURAI_LABEL}, got <{previous.name}>"
        )
    return clean_pasuram_text(previous.get_text("\n", strip=True))


def parse_pattu_sections(urls: Sequence[str] | None = None) -> List[PattuSection]:
    source_urls = list(urls or TIDLEY_URLS)
    sections: List[PattuSection] = []
    pattu_number = 0

    for url in source_urls:
        elements = fetch_hentry_elements(url)
        padhavurai_indices = _find_padhavurai_indices(elements)
        if not padhavurai_indices:
            raise RuntimeError(f"No {PADHAVURAI_LABEL} sections found on {url}")

        for padhavurai_index in padhavurai_indices:
            pattu_number += 1
            pasuram = _pasuram_before_padhavurai(elements, padhavurai_index)
            table_index = padhavurai_index + 1
            if table_index >= len(elements) or elements[table_index].name != "table":
                raise RuntimeError(
                    f"Pattu {pattu_number}: expected table immediately after {PADHAVURAI_LABEL}"
                )
            padham_rows = _parse_table_rows(elements[table_index])
            if not padham_rows:
                raise RuntimeError(f"Pattu {pattu_number}: table has no padham rows")

            sections.append(
                PattuSection(
                    pattu_number=pattu_number,
                    pasuram=pasuram,
                    title="",
                    padham_rows=padham_rows,
                )
            )

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
                    "Title": "",
                    "Word": "",
                    "SimilarWords": "",
                    "NithyaanusandhamIndex": None,
                    "PrabandhamTitle": prabandham,
                }
            )
    return records


def scrape_periya_thirumadal(urls: Sequence[str] | None = None) -> List[Dict[str, Any]]:
    sections = parse_pattu_sections(urls)
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
                        len(section.padham_rows),
                    ]
                )
