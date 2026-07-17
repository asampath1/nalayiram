"""Fetch Mudhal Thiruvandhathi pasuram titles from tidley.com (Pattu 36–100)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from poc.title_scrapers.base import SKIP_PARAGRAPH_MARKERS, is_separator
from poc.title_scrapers.tidley import fetch_paragraphs

BASE_URL = "https://tidley.com/2014/06/28/"
SLUG_TEMPLATE = (
    "%e0%ae%ae%e0%af%81%e0%ae%a4%e0%ae%b2%e0%af%8d-%e0%ae%a4%e0%ae%bf%e0%ae%b0%e0%af%81"
    "%e0%ae%b5%e0%ae%a8%e0%af%8d%e0%ae%a4%e0%ae%be%e0%ae%a4%e0%ae%bf-%e0%ae%aa%e0%ae%be%e0%ae%9a%e0%af%81%e0%ae%b0-{slug}/"
)
PASURAM_NUMBER_BASE = 2081
DIRECT_URL_PATTU_MAX = 43  # Pattu 36–43 via 2014/06/28 slug = pattu - 1
AVATHARIKAI_PREFIX = "(ஸ்ரீ நம்பிள்ளை படி அவதாரிகை)"
HEADING_PATTU_RE = re.compile(r"பாசுரம்\s*[-–—]?\s*(\d+)")


@dataclass(frozen=True)
class MudalTitleRecord:
    pattu_number: int
    pasuram_number: int
    title: str
    url: str


def slug_for_pattu(pattu_number: int) -> int:
    return pattu_number - 1


def direct_url_for_pattu(pattu_number: int) -> str:
    return urljoin(BASE_URL, SLUG_TEMPLATE.format(slug=slug_for_pattu(pattu_number)))


def _should_skip_paragraph(text: str) -> bool:
    return any(marker in text for marker in SKIP_PARAGRAPH_MARKERS)


def _fetch_soup(url: str, timeout: int = 30) -> BeautifulSoup:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


def extract_pattu_from_page(soup: BeautifulSoup) -> Optional[int]:
    for selector in (".entry-title", "h1", "h2", "h3"):
        for tag in soup.select(selector):
            match = HEADING_PATTU_RE.search(tag.get_text(" ", strip=True))
            if match:
                return int(match.group(1))
    hentry = soup.select_one(".hentry")
    if hentry:
        for tag in hentry.find_all(["h1", "h2", "h3", "strong", "b", "p"], limit=12):
            match = HEADING_PATTU_RE.search(tag.get_text(" ", strip=True))
            if match:
                return int(match.group(1))
    return None


def extract_avatharikai_title(paragraphs: Iterable[str]) -> str:
    """Title = prefix + text between அவதாரிகை – and separator above pasuram."""
    blocks: list[str] = []
    collecting = False
    for paragraph in paragraphs:
        text = paragraph.strip()
        if not text or _should_skip_paragraph(text):
            continue
        if not collecting:
            if "அவதாரிகை" in text:
                collecting = True
                remainder = re.sub(r"^.*?அவதாரிகை\s*[–\-—]\s*", "", text).strip()
                if remainder:
                    blocks.append(remainder)
            continue
        if is_separator(text):
            break
        if text in {"பதவுரை", "வியாக்யானம் –", "வியாக்யானம் -", "வியாக்யானம்"}:
            break
        blocks.append(text)
    if not blocks:
        return AVATHARIKAI_PREFIX
    body = "\n".join(blocks)
    return f"{AVATHARIKAI_PREFIX}\n{body}"


def scrape_title_from_url(url: str) -> tuple[Optional[int], str]:
    soup = _fetch_soup(url)
    pattu_number = extract_pattu_from_page(soup)
    paragraphs = fetch_paragraphs(url)
    title = extract_avatharikai_title(paragraphs)
    return pattu_number, title


def scrape_direct_pattu(pattu_number: int, *, pause_s: float = 0.2) -> MudalTitleRecord:
    url = direct_url_for_pattu(pattu_number)
    found_pattu, title = scrape_title_from_url(url)
    if found_pattu is not None and found_pattu != pattu_number:
        raise RuntimeError(
            f"Pattu mismatch on {url}: expected {pattu_number}, page shows {found_pattu}"
        )
    time.sleep(pause_s)
    return MudalTitleRecord(
        pattu_number=pattu_number,
        pasuram_number=PASURAM_NUMBER_BASE + pattu_number,
        title=title,
        url=url,
    )


def scrape_via_next_chain(
    start_url: str,
    *,
    pattu_end: int = 100,
    pause_s: float = 0.25,
    max_hops: int = 120,
) -> list[MudalTitleRecord]:
    records: list[MudalTitleRecord] = []
    url: Optional[str] = start_url
    seen_pattus: set[int] = set()
    hops = 0
    while url and hops < max_hops:
        hops += 1
        found_pattu, title = scrape_title_from_url(url)
        if found_pattu is None:
            raise RuntimeError(f"Could not parse pattu number from page: {url}")
        if found_pattu not in seen_pattus:
            seen_pattus.add(found_pattu)
            records.append(
                MudalTitleRecord(
                    pattu_number=found_pattu,
                    pasuram_number=PASURAM_NUMBER_BASE + found_pattu,
                    title=title,
                    url=url,
                )
            )
        if found_pattu >= pattu_end:
            break
        soup = _fetch_soup(url)
        next_link = soup.select_one('a[rel="next"]')
        url = next_link["href"] if next_link and next_link.get("href") else None
        time.sleep(pause_s)
    return records


def scrape_mudal_titles(
    pattu_start: int = 36,
    pattu_end: int = 100,
    *,
    pause_s: float = 0.2,
) -> list[MudalTitleRecord]:
    records: list[MudalTitleRecord] = []
    direct_end = min(pattu_end, DIRECT_URL_PATTU_MAX)
    for pattu_number in range(pattu_start, direct_end + 1):
        records.append(scrape_direct_pattu(pattu_number, pause_s=pause_s))

    if pattu_end <= DIRECT_URL_PATTU_MAX:
        return records

    last_direct = records[-1]
    soup = _fetch_soup(last_direct.url)
    next_link = soup.select_one('a[rel="next"]')
    if not next_link or not next_link.get("href"):
        raise RuntimeError(f"No rel=next link after pattu {DIRECT_URL_PATTU_MAX}")

    chain_records = scrape_via_next_chain(
        next_link["href"],
        pattu_end=pattu_end,
        pause_s=pause_s,
    )
    records.extend(chain_records)
    return records


def titles_by_pasuram_number(records: Iterable[MudalTitleRecord]) -> Dict[int, str]:
    return {record.pasuram_number: record.title for record in records}
