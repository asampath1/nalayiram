"""Scrape சிறிய திருமடல் padham artham from tidley.com (POC, PasuramNumber 2673)."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from poc.scrapers.thiruvozhukootrirukkai_tidley import (
    PADHAVURAI_LABEL,
    PattuSection,
    _parse_table_rows,
    fetch_hentry_elements,
    summarize_sections,
)

TIDLEY_URL = (
    "https://tidley.com/2022/12/06/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%9a%e0%ae%bf%e0%ae%b1%e0%ae%bf%e0%ae%af-"
    "%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%9f%e0%ae%b2%e0%af%8d-%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-2/"
)
DEFAULT_PATTU_FILE = (
    Path(__file__).resolve().parent.parent / "input" / "siriya_thirumadal_pattus.txt"
)
PRABANDHAM = "சிறிய திருமடல்"
PASURAM_NUMBER = 2673
ALZWAR = "திருமங்கையாழ்வார்"


def load_pattu_pasurams(path: Path) -> List[Tuple[int, str]]:
    """Parse pattu file: numbered blocks (1, 2, …) each followed by pasuram lines."""
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^\s*(\d+)\s*$", text)
    pattus: List[Tuple[int, str]] = []
    index = 1
    while index < len(blocks):
        pattu_number = int(blocks[index])
        body = blocks[index + 1].strip() if index + 1 < len(blocks) else ""
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        pasuram = "\n".join(lines)
        pattus.append((pattu_number, pasuram))
        index += 2
    if not pattus:
        raise RuntimeError(f"No pattu blocks found in {path}")
    return pattus


def _find_padhavurai_indices(elements: Sequence[Any]) -> List[int]:
    indices: List[int] = []
    for index, element in enumerate(elements):
        if element.name == "p" and element.get_text(strip=True) == PADHAVURAI_LABEL:
            indices.append(index)
    return indices


def parse_pattu_sections(
    elements: Sequence[Any] | None = None,
    *,
    pattu_pasurams: Sequence[Tuple[int, str]] | None = None,
    pattu_file: Path | None = None,
) -> List[PattuSection]:
    if elements is None:
        elements = fetch_hentry_elements(TIDLEY_URL)

    if pattu_pasurams is None:
        source = pattu_file or DEFAULT_PATTU_FILE
        pattu_pasurams = load_pattu_pasurams(source)

    padhavurai_indices = _find_padhavurai_indices(elements)
    if not padhavurai_indices:
        raise RuntimeError(f"No {PADHAVURAI_LABEL} sections found on page")
    if len(padhavurai_indices) != len(pattu_pasurams):
        raise RuntimeError(
            f"Pattu count mismatch: tidley has {len(padhavurai_indices)} tables, "
            f"file has {len(pattu_pasurams)} pattus"
        )

    sections: List[PattuSection] = []
    for (pattu_number, pasuram), padhavurai_index in zip(pattu_pasurams, padhavurai_indices):
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


def scrape_siriya_thirumadal(
    url: str = TIDLEY_URL,
    *,
    pattu_file: Path | None = None,
) -> List[Dict[str, Any]]:
    elements = fetch_hentry_elements(url)
    sections = parse_pattu_sections(elements, pattu_file=pattu_file)
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
