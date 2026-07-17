#!/usr/bin/env python3
"""Scrape பெரிய திருவந்தாதி from dravidaveda → transliterate → themes → POC JSON/DB."""
from __future__ import annotations

import argparse
import sys
from itertools import groupby
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from poc.config import load_config
from poc.db_loader import load_json_to_db
from poc.fill_workbook import transliterate_records_from_config
from poc.generate_similar_words import finalize_records
from poc.json_exporter import export_to_json
from poc.load_workbook import delete_pasuram_range
from poc.orchestrate_poc import merge_comment_rows
from poc.scraper_adapter import scrape_range

PRABANDHAM = "பெரிய திருவந்தாதி"
PRABANDHAM_TITLE = "பெரிய திருவந்தாதி, Periya Thiruvandhathi"
ALZWAR = "நம்மாழ்வார்"
PASURAM_NUMBER_BASE = 2584
PASURAM_START = PASURAM_NUMBER_BASE + 1
PASURAM_END = PASURAM_NUMBER_BASE + 87
PATTU_START = 1
DRAVIDAVEDA_BASE = "https://www.dravidaveda.org"
DEFAULT_JSON = ROOT / "poc/output/periya_thiruvandhathi_poc.json"
DEFAULT_SCRAPED = ROOT / "poc/output/periya_thiruvandhathi_dravidaveda_scraped.json"


def _renumber_padham_rows(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    renumbered: List[Dict[str, Any]] = []
    for _, group in groupby(records, key=lambda row: row["PasuramNumber"]):
        for padham_number, row in enumerate(group, start=1):
            updated = dict(row)
            updated["PadhamNumber"] = padham_number
            renumbered.append(updated)
    return renumbered


def rows_to_records(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for row in rows:
        padham = str(row.get("Padham", "")).strip()
        if not padham or padham.upper() == "NOTE":
            continue
        records.append(
            {
                "Prabandham": PRABANDHAM,
                "PasuramNumber": int(row["PasuramNumber"]),
                "Pasuram": row.get("Pasuram", ""),
                "PattuNumber": row.get("PattuNumber"),
                "Padham": padham,
                "Meaning": row.get("Meaning", ""),
                "Alzwar": row.get("Alzwar") or ALZWAR,
                "PadhamNumber": row.get("PadhamNumber"),
                "Title": "",
                "Word": "",
                "SimilarWords": "",
                "NithyaanusandhamIndex": None,
                "PrabandhamTitle": PRABANDHAM_TITLE,
            }
        )
    return _renumber_padham_rows(records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest Periya Thiruvandhathi (2585-2671) into POC"
    )
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--scraped-json", default=str(DEFAULT_SCRAPED))
    parser.add_argument("--start", type=int, default=PASURAM_START)
    parser.add_argument("--end", type=int, default=PASURAM_END)
    parser.add_argument("--pattu-start", type=int, default=PATTU_START)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-themes", action="store_true")
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Use existing scraped JSON only",
    )
    return parser.parse_args()


def load_scraped_records(args: argparse.Namespace) -> List[Dict[str, Any]]:
    scraped_json = Path(args.scraped_json)
    if not args.skip_scrape:
        print(
            f"Scraping dravidaveda {args.start}-{args.end} "
            f"(pattu {args.pattu_start}+)"
        )
        raw_rows = scrape_range(
            base_url=DRAVIDAVEDA_BASE,
            start=args.start,
            end=args.end,
            prabandham=PRABANDHAM,
            title="",
            alzwar=ALZWAR,
            pattu_number=None,
            pattu_number_start=args.pattu_start,
            output_path=scraped_json,
        )
    else:
        import json

        with open(scraped_json, encoding="utf-8") as fh:
            raw_rows = json.load(fh)

    merged_rows = merge_comment_rows(raw_rows)
    records = rows_to_records(merged_rows)
    pasuram_count = len({record["PasuramNumber"] for record in records})
    print(f"Pasurams: {pasuram_count}, padham rows: {len(records)}")

    expected = set(range(args.start, args.end + 1))
    found = {record["PasuramNumber"] for record in records}
    missing = sorted(expected - found)
    if missing:
        print("Dravidaveda pages not found (skipped):")
        for pasuram_number in missing:
            pattu = pasuram_number - PASURAM_NUMBER_BASE
            print(f"  PasuramNumber {pasuram_number} (Pattu {pattu}): {DRAVIDAVEDA_BASE}/{pasuram_number}/")
    return records


def main() -> None:
    args = parse_args()
    output_json = Path(args.output_json)

    records = load_scraped_records(args)
    print(f"Raw padham rows: {len(records)}")

    config_path = Path(args.config)
    records = transliterate_records_from_config(records, config_path)
    records = finalize_records(
        records,
        apply_themes=not args.no_themes,
        themes=None,
        group_by_pasuram_number=False,
    )

    export_to_json(records, output_json)
    print(f"Wrote {output_json}")

    if args.dry_run and not args.apply:
        print("Dry run complete (no DB changes).")
        return

    if not args.apply:
        print(f"Use --apply to load into POC (range {args.start}-{args.end}).")
        return

    config = load_config(args.config)
    db = config.database
    delete_pasuram_range(db, args.start, args.end, dry_run=False)
    inserted = load_json_to_db(output_json, db, dry_run=False)
    print(f"Loaded {inserted} rows into {db.table} for {PRABANDHAM} ({args.start}-{args.end})")


if __name__ == "__main__":
    main()
