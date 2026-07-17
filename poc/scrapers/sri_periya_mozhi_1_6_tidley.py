"""Scrape பெரிய திருமொழி 1-6 from tidley.com + manual (POC, PasuramNumber 998-1007)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from poc.scrapers.periya_thirumozhi_manual import parse_manual_file
from poc.scrapers.periya_thirumozhi_tidley import (
    ALZWAR,
    PRABANDHAM,
    PathigamIngestConfig,
    apply_pathigam_aliases,
    parse_pattu_sections as _parse_pattu_sections,
    pasuram_start,
    sections_to_records as _sections_to_records,
    summarize_sections,
    write_review_csv as _write_review_csv,
)
from poc.scrapers.thiruvozhukootrirukkai_tidley import PattuSection

TIDLEY_URL = (
    "https://tidley.com/2022/11/19/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%ae%bf%e0%ae%af-%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-"
    "1-6-%e0%ae%b5%e0%ae%be%e0%ae%a3%e0%ae%bf%e0%ae%b2-%e0%ae%ae%e0%af%81%e0%ae%b1/"
)
PATHAM_NUMBER = 1
PATHIGAM_NUMBER = 6
PASURAM_NUMBER_BASE = 997
TITLE_BASE = "(வாணில முறுவல்) - -(திரு நைமிசாரண்யம்)"
PATHIGAM_NAME_TAMIL = "வாணில முறுவல்"
PATHIGAM_NAME_ENGLISH = "Vanila Muruval"
MANUAL_998 = (
    Path(__file__).resolve().parent.parent / "input/sri_periya_mozhi_1_6_998_manual.txt"
)
CONFIG = PathigamIngestConfig(
    tidley_url=TIDLEY_URL,
    patham_number=PATHAM_NUMBER,
    pathigam_number=PATHIGAM_NUMBER,
    pasuram_number_base=PASURAM_NUMBER_BASE,
    title_base=TITLE_BASE,
    title_mode="post_table_context",
    pathigam_name_tamil=PATHIGAM_NAME_TAMIL,
    pathigam_name_english=PATHIGAM_NAME_ENGLISH,
)
PASURAM_START = pasuram_start(CONFIG)
PASURAM_END = PASURAM_NUMBER_BASE + 10


def parse_pattu_sections(elements=None) -> List[PattuSection]:
    manual_sections = parse_manual_file(MANUAL_998, CONFIG) if MANUAL_998.exists() else []
    tidley_sections = _parse_pattu_sections(CONFIG, elements)
    by_pattu = {section.pattu_number: section for section in tidley_sections}
    for section in manual_sections:
        by_pattu[section.pattu_number] = section
    return [by_pattu[key] for key in sorted(by_pattu)]


def sections_to_records(sections, **kwargs) -> List[Dict[str, Any]]:
    return _sections_to_records(sections, CONFIG, **kwargs)


def write_review_csv(sections, path: Path) -> None:
    _write_review_csv(sections, CONFIG, path)


__all__ = [
    "ALZWAR",
    "CONFIG",
    "MANUAL_998",
    "PASURAM_END",
    "PASURAM_NUMBER_BASE",
    "PASURAM_START",
    "PATHAM_NUMBER",
    "PATHIGAM_NUMBER",
    "PRABANDHAM",
    "TITLE_BASE",
    "TIDLEY_URL",
    "apply_pathigam_aliases",
    "parse_pattu_sections",
    "sections_to_records",
    "summarize_sections",
    "write_review_csv",
]
