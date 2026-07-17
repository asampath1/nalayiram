"""Prabandham-specific scrapers for per-pasuram Title (commentary) text."""
from poc.title_scrapers.base import PasuramTitleRecord
from poc.title_scrapers.irandam_tidley import scrape_irandam_titles
from poc.title_scrapers.moondram_tidley import scrape_moondram_titles
from poc.title_scrapers.nanmugan_tidley import scrape_nanmugan_titles

__all__ = [
    "PasuramTitleRecord",
    "scrape_irandam_titles",
    "scrape_moondram_titles",
    "scrape_nanmugan_titles",
]
