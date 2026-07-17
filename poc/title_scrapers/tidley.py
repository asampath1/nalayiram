"""Shared tidley.com HTML fetch and paragraph parsing."""
from __future__ import annotations

from typing import Iterable, List

import requests
from bs4 import BeautifulSoup

from poc.title_scrapers.base import (
    SKIP_PARAGRAPH_MARKERS,
    PasuramTitleRecord,
    extract_pattu_number,
    is_pasuram_paragraph,
    is_separator,
    join_title_blocks,
)


def _should_skip_paragraph(text: str) -> bool:
    return any(marker in text for marker in SKIP_PARAGRAPH_MARKERS)


def fetch_paragraphs(url: str, timeout: int = 30) -> List[str]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    hentry = soup.select_one(".hentry")
    if hentry is None:
        raise RuntimeError(f"Could not find .hentry on tidley page: {url}")

    paragraphs = [
        paragraph.get_text("\n", strip=True)
        for paragraph in hentry.find_all("p")
        if paragraph.get_text(strip=True)
    ]
    return [paragraph for paragraph in paragraphs if not _should_skip_paragraph(paragraph)]


def parse_tidley_paragraphs(
    paragraphs: Iterable[str],
    *,
    pasuram_number_base: int,
    expected_pattu_count: int | None = None,
) -> List[PasuramTitleRecord]:
    """Parse tidley paragraphs into pasuram records with multi-paragraph titles."""
    title_blocks: list[str] = []
    records: list[PasuramTitleRecord] = []

    for paragraph in paragraphs:
        if is_separator(paragraph):
            if records:
                title_blocks = []
            continue

        if is_pasuram_paragraph(paragraph):
            pattu_number = extract_pattu_number(paragraph)
            records.append(
                PasuramTitleRecord(
                    pattu_number=pattu_number,
                    pasuram_number=pasuram_number_base + pattu_number,
                    pasuram=paragraph.strip(),
                    title=join_title_blocks(title_blocks),
                )
            )
            title_blocks = []
            if expected_pattu_count is not None and pattu_number == expected_pattu_count:
                break
            continue

        title_blocks.append(paragraph)

    return records


def scrape_tidley_titles(
    url: str,
    *,
    pasuram_number_base: int,
    expected_pattu_count: int,
) -> List[PasuramTitleRecord]:
    paragraphs = fetch_paragraphs(url)
    records = parse_tidley_paragraphs(
        paragraphs,
        pasuram_number_base=pasuram_number_base,
        expected_pattu_count=expected_pattu_count,
    )
    if len(records) != expected_pattu_count:
        raise RuntimeError(
            f"Expected {expected_pattu_count} pasurams, parsed {len(records)} from tidley"
        )

    pattu_numbers = [record.pattu_number for record in records]
    expected = list(range(1, expected_pattu_count + 1))
    if sorted(pattu_numbers) != expected:
        raise RuntimeError(f"Unexpected pattu sequence: {pattu_numbers[:5]} ... {pattu_numbers[-5:]}")

    return records
