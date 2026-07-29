"""Scrape இராமாநுச நூற்றந்தாதி padham artham from tidley.com (POC, 3777–3884).

Tidley quirk (page 45–77): verse 75 is mislabeled ``–76-`` (starts with
``செய்த் தலைச் சங்கம்``). Real verse 76 is missing on tidley and is supplied
from ``poc/pasuram.txt``.
"""
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

ROOT = Path(__file__).resolve().parents[2]

TIDLEY_URLS = (
    # 1–7
    "https://tidley.com/2022/07/03/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%b0%e0%ae%be%e0%ae%ae%e0%ae%be%e0%ae%a9%e0%af%81%e0%ae%9c-"
    "%e0%ae%a8%e0%af%82%e0%ae%b1%e0%af%8d%e0%ae%b1%e0%ae%a8%e0%af%8d%e0%ae%a4%e0%ae%be%e0%ae%a4-114/",
    # 8–21
    "https://tidley.com/2022/10/07/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%b0%e0%ae%be%e0%ae%ae%e0%ae%be%e0%ae%a9%e0%af%81%e0%ae%9c-"
    "%e0%ae%a8%e0%af%82%e0%ae%b1%e0%af%8d%e0%ae%b1%e0%ae%a8%e0%af%8d%e0%ae%a4%e0%ae%be%e0%ae%a4-120/",
    # 22–44
    "https://tidley.com/2022/10/08/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%b0%e0%ae%be%e0%ae%ae%e0%ae%be%e0%ae%a9%e0%af%81%e0%ae%9c-"
    "%e0%ae%a8%e0%af%82%e0%ae%b1%e0%af%8d%e0%ae%b1%e0%ae%a8%e0%af%8d%e0%ae%a4%e0%ae%be%e0%ae%a4-121/",
    # 45–77 (75 mislabeled as 76; real 76 missing)
    "https://tidley.com/2022/10/09/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%b0%e0%ae%be%e0%ae%ae%e0%ae%be%e0%ae%a9%e0%af%81%e0%ae%9c-"
    "%e0%ae%a8%e0%af%82%e0%ae%b1%e0%af%8d%e0%ae%b1%e0%ae%a8%e0%af%8d%e0%ae%a4%e0%ae%be%e0%ae%a4-122/",
    # 78–108
    "https://tidley.com/2022/10/09/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%b0%e0%ae%be%e0%ae%ae%e0%ae%be%e0%ae%a9%e0%af%81%e0%ae%9c-"
    "%e0%ae%a8%e0%af%82%e0%ae%b1%e0%af%8d%e0%ae%b1%e0%ae%a8%e0%af%8d%e0%ae%a4%e0%ae%be%e0%ae%a4-123/",
)

PRABANDHAM = "இராமாநுச நூற்றந்தாதி"
PASURAM_NUMBER_BASE = 3776  # local 1 → 3777
ALZWAR = "திருவரங்கத்து அமுதனார்"
EXPECTED_PATTUS = 108
MANUAL_76_PATH = ROOT / "poc" / "pasuram.txt"
MISLABELED_75_PREFIX = "செய்த் தலைச் சங்கம்"

VERSE_TAIL_RE = re.compile(r"[.–—\-–]+\s*\d+\s*[-—–.]*\s*$")
VERSE_NUM_RE = re.compile(r"[.–—\-–]+\s*(\d+)\s*[-—–.]*\s*$")
SEPARATOR_RE = re.compile(r"^[-—–\s]+$")
PADHAM_LINE_RE = re.compile(r"^(.+?)\s*[–—-]\s*(.+)$")


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


def _is_separator(text: str) -> bool:
    stripped = text.strip()
    return bool(SEPARATOR_RE.match(stripped)) and len(stripped.replace(" ", "")) >= 3


def _verse_number(text: str) -> int | None:
    compact = " ".join(line.strip() for line in text.splitlines() if line.strip())
    match = VERSE_NUM_RE.search(compact)
    return int(match.group(1)) if match else None


def _looks_like_unnumbered_verse(text: str) -> bool:
    text = text.strip()
    if not text or len(text) > 320:
        return False
    if text.startswith("***") or "என்றால்" in text or "விவக்ஷி" in text:
        return False
    # Typical antadhi verse: a few lines / commas, not a long prose gloss
    lines = [line for line in text.splitlines() if line.strip()]
    return 1 <= len(lines) <= 6


def _find_verse_before(
    elements: Sequence[Any],
    index: int,
    *,
    used_numbers: set[int],
) -> tuple[str, int]:
    unnumbered_fallback: tuple[str, None] | None = None
    for probe in range(index - 1, -1, -1):
        element = elements[probe]
        if element.name == "table":
            break
        if element.name != "p":
            continue
        text = element.get_text("\n", strip=True)
        if not text:
            continue
        if _is_separator(text):
            if unnumbered_fallback is not None:
                break
            continue
        labeled = _verse_number(text)
        if labeled is not None:
            if labeled not in used_numbers:
                return clean_pasuram_text(text), labeled
            # Already used (e.g. verse 7 missing its number) — prefer closer unnumbered.
            if unnumbered_fallback is not None:
                break
            continue
        if unnumbered_fallback is None and _looks_like_unnumbered_verse(text):
            unnumbered_fallback = (text, None)

    if unnumbered_fallback is not None:
        # Infer next local number after the highest used so far on this page pass.
        inferred = (max(used_numbers) + 1) if used_numbers else 1
        return clean_pasuram_text(unnumbered_fallback[0]), inferred

    raise RuntimeError(f"No numbered verse paragraph found before element index {index}")


def _parse_one_url(url: str) -> List[tuple[int, PattuSection]]:
    """Return (tidley_label, section) pairs in page order."""
    elements = fetch_hentry_elements(url)
    results: List[tuple[int, PattuSection]] = []
    seen_tables: set[int] = set()
    used_numbers: set[int] = set()

    for index, element in enumerate(elements):
        if element.name == "p" and element.get_text(strip=True) == PADHAVURAI_LABEL:
            table_index = index + 1
            if table_index >= len(elements) or elements[table_index].name != "table":
                raise RuntimeError(f"{url}: expected table after {PADHAVURAI_LABEL} at {index}")
            seen_tables.add(table_index)
            pasuram, labeled = _find_verse_before(elements, index, used_numbers=used_numbers)
            padham_rows = _parse_table_rows(elements[table_index])
            if not padham_rows:
                raise RuntimeError(f"{url}: empty padham table after verse label {labeled}")
            used_numbers.add(labeled)
            results.append(
                (
                    labeled,
                    PattuSection(
                        pattu_number=0,  # filled later
                        pasuram=pasuram,
                        title="",
                        padham_rows=padham_rows,
                    ),
                )
            )
            continue

        # Orphan table: verse paragraph immediately before table (no பதவுரை)
        if element.name == "table" and index not in seen_tables:
            prev = elements[index - 1] if index > 0 else None
            if prev is None or prev.name != "p":
                continue
            prev_text = prev.get_text("\n", strip=True)
            if not prev_text or _is_separator(prev_text) or prev_text == PADHAVURAI_LABEL:
                continue
            labeled = _verse_number(prev_text)
            if labeled is None or labeled in used_numbers:
                continue
            padham_rows = _parse_table_rows(element)
            if not padham_rows:
                continue
            seen_tables.add(index)
            used_numbers.add(labeled)
            results.append(
                (
                    labeled,
                    PattuSection(
                        pattu_number=0,
                        pasuram=clean_pasuram_text(prev_text),
                        title="",
                        padham_rows=padham_rows,
                    ),
                )
            )

    return results


def _parse_manual_76(path: Path = MANUAL_76_PATH) -> PattuSection:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError(f"Manual verse 76 file is empty: {path}")

    blocks = re.split(r"\n\s*\n", text)
    if len(blocks) < 2:
        raise RuntimeError(f"Expected verse + padham block in {path}")

    pasuram = clean_pasuram_text(blocks[0])
    padham_rows: List[tuple[str, str]] = []
    for line in "\n".join(blocks[1:]).splitlines():
        line = line.strip()
        if not line:
            continue
        match = PADHAM_LINE_RE.match(line)
        if not match:
            continue
        padham, meaning = match.group(1).strip(), match.group(2).strip()
        if padham and meaning:
            padham_rows.append((padham, meaning))
    if not padham_rows:
        raise RuntimeError(f"No padham rows parsed from {path}")
    return PattuSection(pattu_number=76, pasuram=pasuram, title="", padham_rows=padham_rows)


def _apply_tidley_number_fixes(
    labeled_sections: List[tuple[int, PattuSection]],
) -> Dict[int, PattuSection]:
    """Map local pattu numbers 1–108, fixing tidley 75/76 typo and injecting 76."""
    by_number: Dict[int, PattuSection] = {}

    for labeled, section in labeled_sections:
        number = labeled
        # Tidley marks real 75 as 76
        first_line = section.pasuram.splitlines()[0] if section.pasuram else ""
        if number == 76 and MISLABELED_75_PREFIX[:10] in first_line.replace(" ", ""):
            number = 75
        elif number == 76 and "செய்த்" in first_line and "சங்கம்" in first_line:
            number = 75
        if number in by_number:
            raise RuntimeError(f"Duplicate local number {number}")
        by_number[number] = PattuSection(
            pattu_number=number,
            pasuram=section.pasuram,
            title="",
            padham_rows=section.padham_rows,
        )

    if 75 not in by_number:
        raise RuntimeError("Expected remapped verse 75 from tidley mislabel (செய்த் தலைச் சங்கம்)")

    if 76 not in by_number:
        by_number[76] = _parse_manual_76()

    missing = [n for n in range(1, EXPECTED_PATTUS + 1) if n not in by_number]
    if missing:
        raise RuntimeError(f"Missing local pasurams after fixes: {missing}")

    return by_number


def parse_pattu_sections(urls: Sequence[str] | None = None) -> List[PattuSection]:
    labeled: List[tuple[int, PattuSection]] = []
    for url in urls or TIDLEY_URLS:
        for num, section in _parse_one_url(url):
            labeled.append((num, section))

    by_number = _apply_tidley_number_fixes(labeled)
    return [by_number[n] for n in range(1, EXPECTED_PATTUS + 1)]


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


def scrape_iramanusa_nootranthathi(urls: Sequence[str] | None = None) -> List[Dict[str, Any]]:
    return sections_to_records(parse_pattu_sections(urls))


def write_review_csv(sections: Sequence[PattuSection], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "PasuramNumber",
                "PattuNumber",
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
                        pasuram_number,
                        section.pattu_number,
                        padham_number,
                        padham,
                        meaning,
                        section.pasuram.replace("\n", " / "),
                        len(section.padham_rows),
                    ]
                )


__all__ = [
    "ALZWAR",
    "EXPECTED_PATTUS",
    "PASURAM_NUMBER_BASE",
    "PRABANDHAM",
    "TIDLEY_URLS",
    "parse_pattu_sections",
    "scrape_iramanusa_nootranthathi",
    "sections_to_records",
    "summarize_sections",
    "write_review_csv",
]
