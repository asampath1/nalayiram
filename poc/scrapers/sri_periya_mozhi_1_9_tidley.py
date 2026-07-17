"""Scrape பெரிய திருமொழி 1-9 from tidley.com (POC, PasuramNumber 1028-1037)."""
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
    "https://tidley.com/2022/11/20/"
    "%e0%ae%b8%e0%af%8d%e0%ae%b0%e0%af%80-%e0%ae%aa%e0%af%86%e0%ae%b0%e0%ae%bf%e0%ae%af-%e0%ae%ae%e0%af%8a%e0%ae%b4%e0%ae%bf-"
    "1-9-%e0%ae%a4%e0%ae%be%e0%ae%af%e0%af%87-%e0%ae%a4%e0%ae%a8%e0%af%8d/"
)
PATHAM_NUMBER = 1
PATHIGAM_NUMBER = 9
PASURAM_NUMBER_BASE = 1027
TITLE_BASE = "(1-9—தாயே தந்தை)(திருவேங்கடம் 2)"
TITLE_PATTU_1 = """(1-9—தாயே தந்தை)(திருவேங்கடம் 2)
(1.“சேலேய்கண்ணியரும் பெருஞ்செல்வமும் நன்மக்களும், மேலாத்தாய் தந்தையுமவரே யினியாவாரே”
2. “தாயாய்த்தந்தையாய் மக்களாய் மற்றுமாய் முற்றுமாய், நீயாய் நீ நின்றவாறு” என்கிறபடியே
உன்னையே ஸகலவிதபந்துக்களுமாகக் கொள்ள வேண்டியிருக்க அது செய்யாதே தாயேயென்றும் தந்தையேயென்றும் தாரமேயென்றும் கிளையேயென்றும் மக்களேயென்றும் ஆபாஸமான புத்ரமித்ராதிகளிடத்திலே ஆசைவைத்து மிகவும் கஷ்டங்கள் பட்டேன்;
அவர்களுக்கு என்னை ரக்ஷிக்க சக்தியுண்டாகிலன்றோ அவர்களால் நான் வாழ்வேன்; உண்மையில் அசக்தர்களான அவர்களை நான் வீணே நம்பிக்கெட்டேன் என்றபடி.)"""
PATHIGAM_NAME_TAMIL = "தாயே தந்தை"
PATHIGAM_NAME_ENGLISH = "Thaye Thanthai"
CONFIG = PathigamIngestConfig(
    tidley_url=TIDLEY_URL,
    patham_number=PATHAM_NUMBER,
    pathigam_number=PATHIGAM_NUMBER,
    pasuram_number_base=PASURAM_NUMBER_BASE,
    title_base=TITLE_BASE,
    title_mode="post_table_context",
    pathigam_name_tamil=PATHIGAM_NAME_TAMIL,
    pathigam_name_english=PATHIGAM_NAME_ENGLISH,
    fixed_titles_by_pattu={1: TITLE_PATTU_1},
)
PASURAM_START = pasuram_start(CONFIG)
PASURAM_END = PASURAM_NUMBER_BASE + 10


def parse_pattu_sections(elements=None) -> List[PattuSection]:
    return _parse_pattu_sections(CONFIG, elements)


def sections_to_records(sections, **kwargs) -> List[Dict[str, Any]]:
    return _sections_to_records(sections, CONFIG, **kwargs)


def write_review_csv(sections, path: Path) -> None:
    _write_review_csv(sections, CONFIG, path)
