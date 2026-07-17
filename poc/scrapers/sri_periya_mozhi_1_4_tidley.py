"""Scrape பெரிய திருமொழி 1-4 from tidley.com (POC, PasuramNumber 978-987)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

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
    "1-4-%e0%ae%8f%e0%ae%a9%e0%ae%ae%e0%af%8d-%e0%ae%ae%e0%af%81%e0%ae%a9%e0%ae%be/"
)
PATHAM_NUMBER = 1
PATHIGAM_NUMBER = 4
PASURAM_NUMBER_BASE = 977
TITLE_BASE = "(ஏனம் முனாகி) - -(திருவதரியாச்சிராமம் )"
PATHIGAM_NAME_TAMIL = "ஏனம் முனாகி"
PATHIGAM_NAME_ENGLISH = "Enam Munagi"
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
    return _parse_pattu_sections(CONFIG, elements)


def sections_to_records(sections, **kwargs) -> List[Dict[str, Any]]:
    return _sections_to_records(sections, CONFIG, **kwargs)


def write_review_csv(sections, path: Path) -> None:
    _write_review_csv(sections, CONFIG, path)


__all__ = [
    "ALZWAR",
    "CONFIG",
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
