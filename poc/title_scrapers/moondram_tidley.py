"""Fetch Moondram Thiruvandhathi pasuram titles from tidley.com."""
from __future__ import annotations

from typing import List

from poc.title_scrapers.base import PasuramTitleRecord, join_title_blocks
from poc.title_scrapers.overrides import apply_title_prefix
from poc.title_scrapers.tidley import scrape_tidley_titles

MOONDRAM_TIDLEY_URL = (
    "https://tidley.com/2019/04/23/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%ae%e0%af%82%e0%ae%a9%e0%af%8d"
    "%e0%ae%b1%e0%ae%be%e0%ae%ae%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81%e0%ae%b5%e0%ae%a8%e0%af%8d%e0%ae%a4%e0%ae%be/"
)
PASURAM_NUMBER_BASE = 2281
EXPECTED_PATTU_COUNT = 100
FIRST_PASURAM_NUMBER = PASURAM_NUMBER_BASE + 1
PREFIX_FROM_PASURAM_NUMBER = FIRST_PASURAM_NUMBER + 1  # 2283 onward
COMMENTARY_PREFIX = join_title_blocks(
    [
        "ஸ்ரீ நம்பிள்ளை படி வியாக்யானம் –",
        "ஸ்ரீ பெரியவாச்சான் பிள்ளை வியாக்யானம் -ஸ்ரீ அப்பிள்ளை ஸ்வாமிகள் உரையுடன் –",
    ]
)


def scrape_moondram_titles(
    url: str = MOONDRAM_TIDLEY_URL,
    *,
    pasuram_number_base: int = PASURAM_NUMBER_BASE,
) -> List[PasuramTitleRecord]:
    records = scrape_tidley_titles(
        url,
        pasuram_number_base=pasuram_number_base,
        expected_pattu_count=EXPECTED_PATTU_COUNT,
    )
    return apply_title_prefix(
        records,
        COMMENTARY_PREFIX,
        from_pasuram_number=PREFIX_FROM_PASURAM_NUMBER,
    )


__all__ = [
    "MOONDRAM_TIDLEY_URL",
    "PASURAM_NUMBER_BASE",
    "EXPECTED_PATTU_COUNT",
    "COMMENTARY_PREFIX",
    "scrape_moondram_titles",
]
