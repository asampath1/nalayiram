"""Backward-compatible wrapper for 2-4 Neerattam vilakku urai."""
from poc.title_scrapers.periyazhvar_vilakku_tidley import (
    NEERATTAM_SECTION,
    VilakkuUraiRecord,
    append_vilakku_to_title,
    scrape_section_vilakku_urai,
)

NEERATTAM_TIDLEY_URL = NEERATTAM_SECTION.url
PASURAM_NUMBER_BASE = NEERATTAM_SECTION.pasuram_number_base
EXPECTED_PATTU_COUNT = NEERATTAM_SECTION.expected_pattu_count


def scrape_neerattam_vilakku_urai(url: str = NEERATTAM_TIDLEY_URL):
    return scrape_section_vilakku_urai(NEERATTAM_SECTION)
