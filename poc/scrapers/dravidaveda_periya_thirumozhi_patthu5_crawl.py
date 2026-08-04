#!/usr/bin/env python3
"""Crawl Dravidaveda category pages for பெரிய திருமொழி ஐந்தாம் பத்து padhavurai.

Dravidaveda no longer serves padhavurai at /{pasuram_number}/. Instead:
  patthu category → pathigam listing → விளக்க உரை → padhavurai page (opaque slug).

  poc/.venv/bin/python poc/scrapers/dravidaveda_periya_thirumozhi_patthu5_crawl.py --dry-run
  poc/.venv/bin/python poc/scrapers/dravidaveda_periya_thirumozhi_patthu5_crawl.py --pathigam 1
  poc/.venv/bin/python poc/scrapers/dravidaveda_periya_thirumozhi_patthu5_crawl.py --pathigam-start 1 --pathigam-end 10
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from poc.scraper_adapter import SCRAPER_PATH, load_scraper_module, normalize_scraped_row

PATTHU5_CATEGORY_URL = (
    "https://www.dravidaveda.org/category/"
    "இரண்டாமாயிரம்/பெரிய-திருமொழி/பெரிய-திருமொழி-ஐந்தாம்பத்து/"
    "?post_type=enhancedcategory"
)
DRAVIDAVEDA_BASE = "https://www.dravidaveda.org"
PASURAM_START = 1348
PASURAM_END = 1447
PRABANDHAM = "பெரிய திருமொழி"
ALZWAR = "திருமங்கையாழ்வார்"
DEFAULT_OUTPUT = ROOT / "poc/output/periya_thirumozhi_patthu5_dravidaveda_scraped.json"

PATHIGAM_LINK_RE = re.compile(
    r"5\s*[–\-]\s*(\d{1,2})\s",
    re.UNICODE,
)
PATHIGAM_URL_RE = re.compile(
    r"திருமொழி-(\d{1,2})-1",
    re.UNICODE,
)
PASURAM_NUM_RE = re.compile(r"\((\d{4})\)")
VILAKKA_LABEL = "விளக்க உரை"
ANNOUNCEMENT_POST_IDS = {"531", "556", "551"}


@dataclass
class PathigamLink:
    pathigam_number: int
    label: str
    url: str


@dataclass
class PadhavuraiLink:
    vilakka_url: str
    final_url: Optional[str] = None
    pasuram_number: Optional[int] = None


def fetch_html(url: str, session: requests.Session) -> str:
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.text


def discover_pathigam_urls(html: str, base_url: str = DRAVIDAVEDA_BASE) -> List[PathigamLink]:
    soup = BeautifulSoup(html, "html.parser")
    found: Dict[int, PathigamLink] = {}
    for anchor in soup.find_all("a", href=True):
        text = anchor.get_text(" ", strip=True)
        href = anchor["href"].strip()
        if not href or "category" not in href:
            continue
        pathigam_number: Optional[int] = None
        url_match = PATHIGAM_URL_RE.search(href)
        if url_match:
            pathigam_number = int(url_match.group(1))
        else:
            text_match = PATHIGAM_LINK_RE.match(text)
            if text_match:
                pathigam_number = int(text_match.group(1))
        if pathigam_number is None or not (1 <= pathigam_number <= 10):
            continue
        full_url = urljoin(base_url, href)
        if pathigam_number not in found:
            found[pathigam_number] = PathigamLink(pathigam_number, text, full_url)
    if len(found) != 10:
        missing = sorted(set(range(1, 11)) - set(found))
        raise RuntimeError(
            f"Expected 10 pathigam links on category page, found {len(found)}; missing={missing}"
        )
    return [found[n] for n in sorted(found)]


def discover_padhavurai_links(html: str, base_url: str = DRAVIDAVEDA_BASE) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        text = anchor.get_text(" ", strip=True)
        if text != VILAKKA_LABEL:
            continue
        href = urljoin(base_url, anchor["href"].strip())
        post_id = ""
        if "?p=" in href:
            post_id = href.split("?p=", 1)[-1].split("&", 1)[0]
        if post_id in ANNOUNCEMENT_POST_IDS:
            continue
        if href in seen:
            continue
        seen.add(href)
        links.append(href)
    return links


def resolve_final_url(url: str, session: requests.Session) -> str:
    response = session.get(url, allow_redirects=True, timeout=60)
    response.raise_for_status()
    return response.url.rstrip("/") + "/"


def pasuram_number_from_html(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title:
        match = PASURAM_NUM_RE.search(soup.title.get_text())
        if match:
            return int(match.group(1))
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
        match = PASURAM_NUM_RE.search(tag.get_text())
        if match:
            return int(match.group(1))
    match = PASURAM_NUM_RE.search(soup.get_text(" ", strip=True))
    if match:
        return int(match.group(1))
    raise RuntimeError("Could not find pasuram number (NNNN) on padhavurai page")


def expected_pasuram_range(pathigam_number: int) -> Tuple[int, int]:
    start = PASURAM_START + (pathigam_number - 1) * 10
    return start, start + 9


def pattu_number_for_pasuram(pasuram_number: int) -> int:
    return ((pasuram_number - PASURAM_START) % 10) + 1


def scrape_pathigam(
    pathigam: PathigamLink,
    session: requests.Session,
    scrape_pasuram_page,
    dry_run: bool,
) -> List[Dict[str, Any]]:
    print(f"Pathigam 5-{pathigam.pathigam_number} ({pathigam.label}): {pathigam.url}")
    pathigam_html = fetch_html(pathigam.url, session)
    vilakka_urls = discover_padhavurai_links(pathigam_html)
    exp_start, exp_end = expected_pasuram_range(pathigam.pathigam_number)
    if len(vilakka_urls) != 10:
        raise RuntimeError(
            f"Pathigam 5-{pathigam.pathigam_number}: expected 10 விளக்க உரை links, "
            f"found {len(vilakka_urls)}"
        )

    results: List[Dict[str, Any]] = []
    for index, vilakka_url in enumerate(vilakka_urls, start=1):
        final_url = resolve_final_url(vilakka_url, session)
        padhavurai_html = fetch_html(final_url, session)
        pasuram_number = pasuram_number_from_html(padhavurai_html)
        if not (exp_start <= pasuram_number <= exp_end):
            raise RuntimeError(
                f"Pathigam 5-{pathigam.pathigam_number} link #{index}: "
                f"pasuram {pasuram_number} outside expected {exp_start}-{exp_end}"
            )
        print(f"  [{index}/10] PasuramNumber {pasuram_number} ← {final_url}")
        if dry_run:
            continue
        raw_rows = scrape_pasuram_page(final_url)
        if not raw_rows:
            raise RuntimeError(f"No padham rows scraped from {final_url}")
        pattu_number = pattu_number_for_pasuram(pasuram_number)
        for raw in raw_rows:
            canonical = dict(raw)
            canonical["PasuramNo"] = pasuram_number
            normalized = normalize_scraped_row(
                canonical,
                prabandham=PRABANDHAM,
                title="",
                alzwar=ALZWAR,
                pattu_number=pattu_number,
            )
            results.append(normalized)
    return results


def scrape_patthu5(
    pathigam_start: int = 1,
    pathigam_end: int = 10,
    output_path: Path = DEFAULT_OUTPUT,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; NalayiramPOC/1.0; +https://nalayiram.in)"
            )
        }
    )

    category_html = fetch_html(PATTHU5_CATEGORY_URL, session)
    pathigams = discover_pathigam_urls(category_html)
    selected = [p for p in pathigams if pathigam_start <= p.pathigam_number <= pathigam_end]
    if not selected:
        raise RuntimeError(f"No pathigams in range {pathigam_start}-{pathigam_end}")

    scrape_pasuram_page = getattr(load_scraper_module(SCRAPER_PATH), "scrape_pasuram_page")
    all_rows: List[Dict[str, Any]] = []
    for pathigam in selected:
        rows = scrape_pathigam(pathigam, session, scrape_pasuram_page, dry_run=dry_run)
        all_rows.extend(rows)

    if dry_run:
        print(f"Dry run: would scrape {len(selected)} pathigams ({pathigam_start}-{pathigam_end})")
        return all_rows

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    pasuram_count = len({row["PasuramNumber"] for row in all_rows})
    print(f"Saved {len(all_rows)} padham rows for {pasuram_count} pasurams → {output_path}")
    return all_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dry-run", action="store_true", help="Print URL map only; no scrape/save")
    parser.add_argument("--pathigam", type=int, default=None, help="Single pathigam 1-10 (e.g. 1 for 5-1)")
    parser.add_argument("--pathigam-start", type=int, default=1)
    parser.add_argument("--pathigam-end", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.pathigam is not None:
        pathigam_start = pathigam_end = args.pathigam
    else:
        pathigam_start = args.pathigam_start
        pathigam_end = args.pathigam_end
    scrape_patthu5(
        pathigam_start=pathigam_start,
        pathigam_end=pathigam_end,
        output_path=Path(args.output),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
