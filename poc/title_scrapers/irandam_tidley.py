"""Fetch Irandam Thiruvandhathi pasuram titles from tidley.com."""
from __future__ import annotations

from pathlib import Path
from typing import List

from poc.title_scrapers.base import PasuramTitleRecord
from poc.title_scrapers.overrides import apply_overrides_from_file
from poc.title_scrapers.tidley import scrape_tidley_titles

IRANDAM_TIDLEY_URL = (
    "https://tidley.com/2019/04/21/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%87%e0%ae%b0%e0%ae%a3%e0%af%8d"
    "%e0%ae%9f%e0%ae%be%e0%ae%ae%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%b5%e0%ae%a8%e0%af%8d%e0%ae%a4%e0%ae%be/"
)
PASURAM_NUMBER_BASE = 2181
EXPECTED_PATTU_COUNT = 100
TITLE_OVERRIDES_PATH = Path(__file__).resolve().parent.parent / "input" / "irandam_title_overrides.json"


def scrape_irandam_titles(
    url: str = IRANDAM_TIDLEY_URL,
    *,
    pasuram_number_base: int = PASURAM_NUMBER_BASE,
) -> List[PasuramTitleRecord]:
    records = scrape_tidley_titles(
        url,
        pasuram_number_base=pasuram_number_base,
        expected_pattu_count=EXPECTED_PATTU_COUNT,
    )
    return apply_overrides_from_file(records, TITLE_OVERRIDES_PATH)


__all__ = [
    "IRANDAM_TIDLEY_URL",
    "PASURAM_NUMBER_BASE",
    "EXPECTED_PATTU_COUNT",
    "scrape_irandam_titles",
]
