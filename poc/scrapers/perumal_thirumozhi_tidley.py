"""Scrape பெருமாள் திருமொழி padham artham from tidley.com (POC, PasuramNumber 647–751)."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
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
from poc.title_scrapers.base import is_separator

PRABANDHAM = "பெருமாள் திருமொழி"
ALZWAR = "குலசேகர ஆழ்வார்"
PRABANDHAM_TITLE = "பெருமாள் திருமொழி, Perumal ThiruMozhi"
DRAVIDAVEDA_684_URL = "https://www.dravidaveda.org/684/"

PATHIGAM_SUFFIX_RE = re.compile(
    r"[–\-—\s.]*(\d+)\s*[-–—.]+\s*(\d+)\s*[-–—.]*\s*$"
)
VERSE_TAIL_RE = re.compile(r"[—–\-–\s]+\d+\s*[-—–]?\s*$")


@dataclass(frozen=True)
class PathigamSpec:
    pathigam_number: int
    pasuram_start: int
    pasuram_end: int
    pattu_name_tamil: str
    pattu_name_english: str
    title: str
    tidley_url: str


PATHIGAM_SPECS: Tuple[PathigamSpec, ...] = (
    PathigamSpec(
        1,
        647,
        657,
        "இருள் இரிய",
        "Irul Iriya",
        "(இருள் இரிய) - இருள் இரிய திருவரங்கப் பெருமானை கண்டு என்றுகொல் மகிழ்வேன் எனல்",
        "https://tidley.com/2021/08/06/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%be%e0%ae%b3%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-1-%e0%ae%b8/",
    ),
    PathigamSpec(
        2,
        658,
        667,
        "தேட்டரும் திறல்",
        "Thettarum Thiral",
        "(தேட்டரும் திறல்) - அரங்கன் அடியாரது அடிமைத்திறத்தில் ஈடுபடுதல்",
        "https://tidley.com/2021/08/06/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%be%e0%ae%b3%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-2-%e0%ae%b8/",
    ),
    PathigamSpec(
        3,
        668,
        676,
        "மெய்யில் வாழ்க்கையை",
        "Meyyil Vazhkkaiyai",
        "(மெய்யில் வாழ்க்கையை) - அழகிய மணவாளன்பால் மயல் விஞ்சிய நிலையில் எழுந்த மாற்றம்.",
        "https://tidley.com/2021/08/06/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%be%e0%ae%b3%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-3-%e0%ae%b8/",
    ),
    PathigamSpec(
        4,
        677,
        687,
        "ஊனேறு",
        "Ooneru",
        "(ஊனேறு) - திருவேங்கட மலைத் தொடர்பு வேண்டல்",
        "https://tidley.com/2021/08/07/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%be%e0%ae%b3%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-4-%e0%ae%b8/",
    ),
    PathigamSpec(
        5,
        688,
        697,
        "தரு துயரம் தடாயேல்",
        "Tharu Thuyaram Thadaayel",
        "(தரு துயரம் தடாயேல்) - திருவித்துவக் கோட்டம்மானையே வேண்டி நிற்றல்",
        "https://tidley.com/2021/08/07/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%be%e0%ae%b3%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-5-%e0%ae%b8/",
    ),
    PathigamSpec(
        6,
        698,
        707,
        "ஏர் மலர் பூம் குழல்",
        "Er Malar Poom Kuzhal",
        "(ஏர் மலர் பூம் குழல்) - ஆய்ச்சியர் ஊடி அமலனை எள் கல்",
        "https://tidley.com/2021/08/07/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%be%e0%ae%b3%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-6-%e0%ae%b8/",
    ),
    PathigamSpec(
        7,
        708,
        718,
        "ஆலை நீள் கரும்பு",
        "Aalai Neel Karumbu",
        "(ஆலை நீள் கரும்பு) - சேய் வளர் காட்சியின் சீரை யசோதை போல் தாய் தேவகி பெறாத் தாழ் வெண்ணிப் புலம்பல்",
        "https://tidley.com/2021/08/07/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%be%e0%ae%b3%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-7-%e0%ae%b8/",
    ),
    PathigamSpec(
        8,
        719,
        729,
        "மன்னு புகழ்",
        "Mannu Pugazh",
        "(மன்னு புகழ்) - கணபுரத்தொளிர் காகுத்தன் தாலாட்டு",
        "https://tidley.com/2021/08/07/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%be%e0%ae%b3%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-8-%e0%ae%b8/",
    ),
    PathigamSpec(
        9,
        730,
        740,
        "வன் தாள் இணை",
        "Van Thaal Inai",
        "(வன் தாள் இணை) - தனயன் கான் புகத் தசரதன் புலம்பல்",
        "https://tidley.com/2021/08/07/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%be%e0%ae%b3%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-9-%e0%ae%b8/",
    ),
    PathigamSpec(
        10,
        741,
        751,
        "அம் கண் நெடு மதிள்",
        "Am Kan Nedu Madhil",
        "(அம் கண் நெடு மதிள்)- தில்லைநகர் திருச்சித்திர கூடத்தில் தொல்லிராமனாய்த் தோன்றிய கதைமுறை",
        "https://tidley.com/2021/08/08/%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%af%81%e0%ae%ae%e0%ae%be%e0%ae%b3%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-10-%e0%ae%b8/",
    ),
)

PASURAM_START = 647
PASURAM_END = 751


def _paragraph_text(element: Any) -> str:
    return element.get_text("\n", strip=True)


def _suffix_match(text: str, pathigam_number: int) -> re.Match[str] | None:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    match = PATHIGAM_SUFFIX_RE.search(lines[-1])
    if not match:
        return None
    if int(match.group(1)) != pathigam_number:
        return None
    return match


def _is_pasuram_paragraph(text: str, pathigam_number: int) -> bool:
    return _suffix_match(text, pathigam_number) is not None


def _pattu_from_suffix(text: str, pathigam_number: int) -> int:
    match = _suffix_match(text, pathigam_number)
    if not match:
        raise ValueError(f"Could not parse pathigam suffix from: {text[:80]!r}")
    return int(match.group(2))


def clean_pasuram_text(text: str, pathigam_number: int) -> str:
    lines: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = PATHIGAM_SUFFIX_RE.sub("", line)
        line = VERSE_TAIL_RE.sub("", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _paragraph_texts_between(
    elements: Sequence[Any],
    start_index: int,
    end_index: int,
    *,
    skip_padhavurai_label: bool = True,
) -> List[str]:
    texts: List[str] = []
    for index in range(start_index + 1, end_index):
        element = elements[index]
        if element.name == "table":
            continue
        if element.name != "p":
            continue
        text = _paragraph_text(element).strip()
        if not text:
            continue
        if skip_padhavurai_label and text == PADHAVURAI_LABEL:
            continue
        if is_separator(text) or _is_separator(text):
            continue
        if PATHIGAM_SUFFIX_RE.search(text.splitlines()[-1] if text.splitlines() else ""):
            continue
        texts.append(text)
    return texts


def _padham_rows_from_block(
    elements: Sequence[Any],
    pasuram_index: int,
    end_index: int,
    pasuram: str,
) -> List[Tuple[str, str]]:
    padhavurai_index: int | None = None
    for index in range(pasuram_index + 1, end_index):
        element = elements[index]
        if element.name == "table":
            rows = _parse_table_rows(element)
            if rows:
                return rows
        if element.name == "p" and element.get_text(strip=True) == PADHAVURAI_LABEL:
            padhavurai_index = index
            break

    start = padhavurai_index if padhavurai_index is not None else pasuram_index
    paragraphs = _paragraph_texts_between(
        elements,
        start,
        end_index,
        skip_padhavurai_label=padhavurai_index is not None,
    )
    rows: List[Tuple[str, str]] = []
    for paragraph in paragraphs:
        rows.extend(parse_padham_rows(paragraph))
    if rows:
        return rows
    return _fallback_rows_from_pasuram(pasuram)


def _fallback_rows_from_pasuram(pasuram: str) -> List[Tuple[str, str]]:
    lines = [line.strip() for line in pasuram.splitlines() if line.strip()]
    if not lines:
        return [("", "")]
    return [(line, "") for line in lines]


def scrape_dravidaveda_pasuram(url: str = DRAVIDAVEDA_684_URL) -> Tuple[str, List[Tuple[str, str]]]:
    from poc.scraper_adapter import load_scraper_module, SCRAPER_PATH

    scrape_pasuram_page = getattr(load_scraper_module(SCRAPER_PATH), "scrape_pasuram_page")
    raw_rows = scrape_pasuram_page(url)
    if not raw_rows:
        raise RuntimeError(f"No rows scraped from {url}")
    pasuram = str(raw_rows[0].get("Pasuram", "") or "").strip()
    rows: List[Tuple[str, str]] = []
    for raw in raw_rows:
        padham = str(raw.get("Padham", "") or "").strip()
        meaning = str(raw.get("Meaning", "") or "").strip()
        if padham and padham != "NOTE" and meaning:
            rows.append((padham, meaning))
    if not pasuram or not rows:
        raise RuntimeError(f"Incomplete dravidaveda scrape from {url}")
    return pasuram, rows


@dataclass
class PathigamSections:
    spec: PathigamSpec
    sections: List[PattuSection]


def parse_pathigam_page(spec: PathigamSpec, elements: Sequence[Any] | None = None) -> List[PattuSection]:
    if elements is None:
        elements = fetch_hentry_elements(spec.tidley_url)

    pasuram_indices: List[int] = []
    for index, element in enumerate(elements):
        if element.name != "p":
            continue
        text = _paragraph_text(element)
        if _is_pasuram_paragraph(text, spec.pathigam_number):
            pasuram_indices.append(index)

    sections: List[PattuSection] = []
    for position, pasuram_index in enumerate(pasuram_indices):
        end_index = pasuram_indices[position + 1] if position + 1 < len(pasuram_indices) else len(elements)
        raw_pasuram = _paragraph_text(elements[pasuram_index])
        pattu_number = _pattu_from_suffix(raw_pasuram, spec.pathigam_number)
        pasuram = clean_pasuram_text(raw_pasuram, spec.pathigam_number)
        padham_rows = _padham_rows_from_block(elements, pasuram_index, end_index, pasuram)
        sections.append(
            PattuSection(
                pattu_number=pattu_number,
                pasuram=pasuram,
                title=spec.title,
                padham_rows=padham_rows,
            )
        )

    expected_count = spec.pasuram_end - spec.pasuram_start + 1
    if spec.pathigam_number == 4 and len(sections) == expected_count - 1:
        missing_pattu = 8
        insert_at = next(
            (idx for idx, section in enumerate(sections) if section.pattu_number > missing_pattu),
            len(sections),
        )
        pasuram_text, padham_rows = scrape_dravidaveda_pasuram()
        pasuram_text = clean_pasuram_text(
            f"{pasuram_text}\n–{spec.pathigam_number}-{missing_pattu}–",
            spec.pathigam_number,
        )
        sections.insert(
            insert_at,
            PattuSection(
                pattu_number=missing_pattu,
                pasuram=pasuram_text,
                title=spec.title,
                padham_rows=padham_rows,
            ),
        )

    if len(sections) != expected_count:
        suffixes = [section.pattu_number for section in sections]
        raise RuntimeError(
            f"Pathigam {spec.pathigam_number}: expected {expected_count} pasurams "
            f"({spec.pasuram_start}-{spec.pasuram_end}), found {len(sections)} {suffixes}"
        )

    sections.sort(key=lambda section: section.pattu_number)
    return sections


def parse_all_pathigams(specs: Sequence[PathigamSpec] | None = None) -> List[PathigamSections]:
    return [
        PathigamSections(spec=spec, sections=parse_pathigam_page(spec))
        for spec in (specs or PATHIGAM_SPECS)
    ]


def parse_all_sections(specs: Sequence[PathigamSpec] | None = None) -> List[PattuSection]:
    sections: List[PattuSection] = []
    for group in parse_all_pathigams(specs):
        sections.extend(group.sections)
    return sections


def pattu_aliases(spec: PathigamSpec) -> str:
    return f"({spec.pattu_name_tamil}), ({spec.pattu_name_english})"


def sections_to_records(
    grouped: Sequence[PathigamSections] | None = None,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for item in grouped or parse_all_pathigams():
        spec = item.spec
        aliases = pattu_aliases(spec)
        for position, section in enumerate(sorted(item.sections, key=lambda s: s.pattu_number)):
            pasuram_number = spec.pasuram_start + position
            pattu_number = position + 1
            for padham_number, (padham, meaning) in enumerate(section.padham_rows, start=1):
                records.append(
                    {
                        "Prabandham": PRABANDHAM,
                        "PasuramNumber": pasuram_number,
                        "Pasuram": section.pasuram,
                        "PattuNumber": pattu_number,
                        "Padham": padham,
                        "Meaning": meaning,
                        "Alzwar": ALZWAR,
                        "PadhamNumber": padham_number,
                        "Title": spec.title,
                        "Word": "",
                        "SimilarWords": "",
                        "NithyaanusandhamIndex": None,
                        "PrabandhamTitle": PRABANDHAM_TITLE,
                        "PattuAliases": aliases,
                    }
                )
    return records


def apply_pattu_aliases(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    updated: List[Dict[str, Any]] = []
    for record in records:
        row = dict(record)
        aliases = row.pop("PattuAliases", "")
        similar = str(row.get("SimilarWords", "") or "").strip()
        if aliases:
            similar = f"{similar},{aliases}" if similar else aliases
        row["SimilarWords"] = similar
        row.pop("PathigamNumber", None)
        updated.append(row)
    return updated


def write_review_csv(grouped: Sequence[PathigamSections], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "PathigamNumber",
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
        for item in grouped:
            spec = item.spec
            spec_sections = sorted(item.sections, key=lambda section: section.pattu_number)
            for position, section in enumerate(spec_sections):
                current_pasuram = spec.pasuram_start + position
                for padham_number, (padham, meaning) in enumerate(section.padham_rows, start=1):
                    writer.writerow(
                        [
                            spec.pathigam_number,
                            position + 1,
                            current_pasuram,
                            padham_number,
                            padham,
                            meaning,
                            section.pasuram.replace("\n", " / "),
                            section.title.replace("\n", " / "),
                            len(section.padham_rows),
                        ]
                    )
