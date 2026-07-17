"""Fetch Periyazhvar vilakku urai from tidley and append to existing Title."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List

from poc.title_scrapers.base import join_title_blocks
from poc.title_scrapers.tidley import fetch_paragraphs

SEPARATOR_RE = re.compile(r"^[-—–\s]+$")
VILAKKU_HEADER = "விளக்க உரை"
PADHAVURAI_HEADER = "பதவுரை"


@dataclass(frozen=True)
class PeriyazhvarSectionConfig:
    section_id: str
    label: str
    title_prefix: str
    url: str
    pasuram_number_base: int
    expected_pattu_count: int
    pattu_suffix_pattern: str


@dataclass(frozen=True)
class VilakkuUraiRecord:
    pattu_number: int
    pasuram_number: int
    vilakku_urai: str


NEERATTAM_SECTION = PeriyazhvarSectionConfig(
    section_id="neerattam",
    label="2-4 Neerattam (152-161)",
    title_prefix="2-4 நீராட்டம்",
    url=(
        "https://tidley.com/2021/04/28/"
        "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%ae%bf%e0%ae%af%e0%ae%be%e0%ae%b4%e0%af%8d"
        "%e0%ae%b5%e0%ae%be%e0%ae%b0%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81-%e0%ae%ae-13/"
    ),
    pasuram_number_base=151,
    expected_pattu_count=10,
    pattu_suffix_pattern=r"2-4-(\d+)-?\s*$",
)

POOCHOODAL_SECTION = PeriyazhvarSectionConfig(
    section_id="poochoodal",
    label="2-7 Poochoodal (182-191)",
    title_prefix="2-7 பூச்சூடல்",
    url=(
        "https://tidley.com/2021/04/29/"
        "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%ae%bf%e0%ae%af%e0%ae%be%e0%ae%b4%e0%af%8d"
        "%e0%ae%b5%e0%ae%be%e0%ae%b0%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81-%e0%ae%ae-16/"
    ),
    pasuram_number_base=181,
    expected_pattu_count=10,
    pattu_suffix_pattern=r"2-7-(\d+)-?\s*$",
)

KAPPIDAL_SECTION = PeriyazhvarSectionConfig(
    section_id="kappidal",
    label="2-8 Kappidal (192-201)",
    title_prefix="2-8 காப்பிடல்",
    url=(
        "https://tidley.com/2021/04/29/"
        "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%ae%bf%e0%ae%af%e0%ae%be%e0%ae%b4%e0%af%8d"
        "%e0%ae%b5%e0%ae%be%e0%ae%b0%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81-%e0%ae%ae-17/"
    ),
    pasuram_number_base=191,
    expected_pattu_count=10,
    pattu_suffix_pattern=r"2-8-(\d+)-?\s*$",
)

SENNIYONGU_SECTION = PeriyazhvarSectionConfig(
    section_id="senniyongu",
    label="5-4 Senniyongu (463-473)",
    title_prefix="5-4 சென்னியோங்கு",
    url=(
        "https://tidley.com/2021/05/06/"
        "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%ae%bf%e0%ae%af%e0%ae%be%e0%ae%b4%e0%af%8d"
        "%e0%ae%b5%e0%ae%be%e0%ae%b0%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81-%e0%ae%ae-42/"
    ),
    pasuram_number_base=462,
    expected_pattu_count=11,
    pattu_suffix_pattern=r"5-4-(\d+)-?\s*$",
)

SECTIONS = {
    "neerattam": NEERATTAM_SECTION,
    "poochoodal": POOCHOODAL_SECTION,
    "kappidal": KAPPIDAL_SECTION,
    "senniyongu": SENNIYONGU_SECTION,
}


def _is_separator(text: str) -> bool:
    stripped = text.strip()
    # Tidley uses 3–19 dash chars; some sections use only 3–4 (e.g. 2-7 between pasurams).
    return bool(SEPARATOR_RE.match(stripped)) and len(stripped.replace(" ", "")) >= 3


def _extract_pattu_number(text: str, pattu_suffix_re: re.Pattern[str]) -> int | None:
    lines = [line for line in text.split("\n") if line.strip()]
    for line in reversed(lines):
        match = pattu_suffix_re.search(line.strip())
        if match:
            return int(match.group(1))
    match = pattu_suffix_re.search(text)
    return int(match.group(1)) if match else None


def parse_vilakku_paragraphs(
    paragraphs: Iterable[str],
    *,
    pasuram_number_base: int,
    pattu_suffix_re: re.Pattern[str],
) -> List[VilakkuUraiRecord]:
    records: list[VilakkuUraiRecord] = []
    paras = list(paragraphs)
    index = 0

    while index < len(paras):
        pattu_number = _extract_pattu_number(paras[index], pattu_suffix_re)
        if pattu_number is None:
            index += 1
            continue

        vilakku_blocks: list[str] = []
        scan = index + 1
        while scan < len(paras):
            if _is_separator(paras[scan]):
                break
            if paras[scan].strip() == VILAKKU_HEADER:
                scan += 1
                while scan < len(paras) and not _is_separator(paras[scan]):
                    block = paras[scan].strip()
                    if block in (VILAKKU_HEADER, PADHAVURAI_HEADER):
                        break
                    if _extract_pattu_number(paras[scan], pattu_suffix_re) is not None:
                        break
                    vilakku_blocks.append(paras[scan])
                    scan += 1
                break
            scan += 1

        records.append(
            VilakkuUraiRecord(
                pattu_number=pattu_number,
                pasuram_number=pasuram_number_base + pattu_number,
                vilakku_urai=join_title_blocks(vilakku_blocks),
            )
        )
        while scan < len(paras) and not _is_separator(paras[scan]):
            scan += 1
        index = scan + 1 if scan < len(paras) else len(paras)

    return records


def scrape_section_vilakku_urai(section: PeriyazhvarSectionConfig) -> List[VilakkuUraiRecord]:
    pattu_suffix_re = re.compile(section.pattu_suffix_pattern)
    paragraphs = fetch_paragraphs(section.url)
    records = parse_vilakku_paragraphs(
        paragraphs,
        pasuram_number_base=section.pasuram_number_base,
        pattu_suffix_re=pattu_suffix_re,
    )
    if len(records) != section.expected_pattu_count:
        raise RuntimeError(
            f"Expected {section.expected_pattu_count} pasurams, parsed {len(records)} from tidley"
        )

    pattu_numbers = [record.pattu_number for record in records]
    expected = list(range(1, section.expected_pattu_count + 1))
    if sorted(pattu_numbers) != expected:
        raise RuntimeError(f"Unexpected pattu sequence: {pattu_numbers}")

    return records


def build_vilakku_title(section_prefix: str, vilakku_urai: str) -> str:
    prefix = (section_prefix or "").strip()
    appendix = (vilakku_urai or "").strip()
    if not prefix and not appendix:
        return ""
    if not appendix:
        return f"({prefix})"
    if not prefix:
        return appendix
    return f"({prefix}) - {appendix}"


def append_vilakku_to_title(
    existing_title: str,
    vilakku_urai: str,
    *,
    section_prefix: str | None = None,
) -> str:
    if section_prefix:
        return build_vilakku_title(section_prefix, vilakku_urai)

    base = (existing_title or "").strip()
    appendix = vilakku_urai.strip()
    if not appendix:
        return base
    if appendix in base:
        return base
    if not base:
        return appendix
    return f"{base} {appendix}"
