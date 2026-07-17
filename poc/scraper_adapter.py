#!/usr/bin/env python3
"""Adapter to normalize pasuram scraping output into a reusable JSON format."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

ROOT = Path(__file__).resolve().parent.parent
SCRAPER_PATH = ROOT / "public_html" / "scrape_pasuram.py"


def load_scraper_module(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Scraper module not found at {path}")

    spec = importlib.util.spec_from_file_location("scrape_pasuram", str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_scraped_row(raw: Dict[str, Any], prabandham: str, title: str, alzwar: Optional[str], pattu_number: Optional[int]) -> Dict[str, Any]:
    return {
        "Prabandham": prabandham,
        "PasuramNumber": int(raw.get("PasuramNo", 0) or 0),
        "Pasuram": raw.get("Pasuram", ""),
        "PattuNumber": pattu_number,
        "Word": None,
        "Meaning": raw.get("Meaning", ""),
        "Alzwar": alzwar,
        "PadhamNumber": raw.get("PadhamNo"),
        "Padham": raw.get("Padham", ""),
        "Title": title,
        "SimilarWords": None,
        "NithyaanusandhamIndex": None,
    }


def scrape_range(
    base_url: str,
    start: int,
    end: int,
    prabandham: str,
    title: str,
    alzwar: Optional[str],
    pattu_number: Optional[int],
    pattu_number_start: Optional[int],
    output_path: Path,
    sleep_delay: Optional[float] = None,
    url_overrides: Optional[Mapping[int, int]] = None,
) -> List[Dict[str, Any]]:
    module = load_scraper_module(SCRAPER_PATH)
    if not hasattr(module, "scrape_pasuram_page"):
        raise AttributeError("Loaded scraper does not define scrape_pasuram_page()")

    scrape_pasuram_page = getattr(module, "scrape_pasuram_page")
    results: List[Dict[str, Any]] = []

    overrides = url_overrides or {}

    for pasuram_number in range(start, end + 1):
        url_slug = overrides.get(pasuram_number, pasuram_number)
        url = f"{base_url.rstrip('/')}/{url_slug}/"
        print(f"Scraping {url}" + (f" (PasuramNumber {pasuram_number})" if url_slug != pasuram_number else ""))
        raw_rows = scrape_pasuram_page(url)
        if not raw_rows:
            print(f"Warning: no rows returned for {url}")
            continue

        if pattu_number_start is not None:
            current_pattu = pattu_number_start + (pasuram_number - start)
        else:
            current_pattu = pattu_number

        for raw in raw_rows:
            canonical = dict(raw)
            canonical["PasuramNo"] = pasuram_number
            normalized = normalize_scraped_row(
                canonical,
                prabandham=prabandham,
                title=title,
                alzwar=alzwar,
                pattu_number=current_pattu,
            )
            results.append(normalized)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)

    print(f"Saved {len(results)} normalized records to {output_path}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize scraped pasuram data into JSON for POC consumption")
    parser.add_argument("--base-url", default="https://www.dravidaveda.org", help="Base URL for pasuram pages")
    parser.add_argument("--start", type=int, required=True, help="Starting pasuram number")
    parser.add_argument("--end", type=int, required=True, help="Ending pasuram number")
    parser.add_argument("--prabandham", required=True, help="Prabandham name for the selected pasuram range")
    parser.add_argument("--title", required=True, help="English title for the selected prabandham")
    parser.add_argument("--alzwar", default="", help="Alzwar name, if available")
    parser.add_argument("--pattu-number", type=int, default=None, help="Pattu number for this prabandham")
    parser.add_argument("--pattu-number-start", type=int, default=None, help="Starting pattu number for the first scraped pasuram")
    parser.add_argument("--output", default="poc/output/scraped_pasurams.json", help="Output JSON path")
    args = parser.parse_args()

    scrape_range(
        base_url=args.base_url,
        start=args.start,
        end=args.end,
        prabandham=args.prabandham,
        title=args.title,
        alzwar=args.alzwar or None,
        pattu_number=args.pattu_number,
        pattu_number_start=args.pattu_number_start,
        output_path=Path(args.output),
    )


if __name__ == "__main__":
    main()
