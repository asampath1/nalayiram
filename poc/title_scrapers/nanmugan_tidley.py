"""Fetch Nanmugan Thiruvandhathi pasuram titles from tidley.com."""
from __future__ import annotations

from typing import List

from poc.title_scrapers.base import PasuramTitleRecord
from poc.title_scrapers.tidley import parse_tidley_paragraphs, scrape_tidley_titles

NANMUGAN_TIDLEY_URL = (
    "https://tidley.com/2019/04/12/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%a8%e0%ae%be%e0%ae%a9%e0%af%8d"
    "%e0%ae%ae%e0%af%81%e0%ae%95%e0%ae%a9%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%b5%e0%ae%a8%e0%af%8d%e0%ae%a4/"
)
PASURAM_NUMBER_BASE = 2381
EXPECTED_PATTU_COUNT = 96


def scrape_nanmugan_titles(
    url: str = NANMUGAN_TIDLEY_URL,
    *,
    pasuram_number_base: int = PASURAM_NUMBER_BASE,
) -> List[PasuramTitleRecord]:
    return scrape_tidley_titles(
        url,
        pasuram_number_base=pasuram_number_base,
        expected_pattu_count=EXPECTED_PATTU_COUNT,
    )


__all__ = [
    "NANMUGAN_TIDLEY_URL",
    "PASURAM_NUMBER_BASE",
    "EXPECTED_PATTU_COUNT",
    "parse_tidley_paragraphs",
    "scrape_nanmugan_titles",
]
