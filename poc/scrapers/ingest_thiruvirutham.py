#!/usr/bin/env python3
"""Scrape Thiruvirutham from tidley/manual/dravidaveda → transliterate → themes → POC JSON/DB."""
from __future__ import annotations

import argparse
import sys
from itertools import groupby
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from poc.config import load_config
from poc.fill_workbook import transliterate_records_from_config
from poc.generate_similar_words import finalize_records
from poc.json_exporter import export_to_json
from poc.load_workbook import delete_pasuram_range
from poc.db_loader import load_json_to_db
from poc.orchestrate_poc import merge_comment_rows
from poc.scraper_adapter import scrape_range
from poc.scrapers.thiruvirutham_manual import (
    parse_manual_file,
    summarize_manual_sections,
)
from poc.scrapers.thiruvirutham_tidley import (
    ALZWAR,
    DEFAULT_PATTU_LIMIT,
    PASURAM_NUMBER_BASE,
    PRABANDHAM,
    TIDLEY_URL,
    PattuSection,
    parse_pattu_sections,
    sections_to_records,
    summarize_sections,
    write_review_csv,
)


DEFAULT_JSON = ROOT / "poc/output/thiruvirutham_poc.json"
DEFAULT_REVIEW_CSV = ROOT / "lookupsimilarwords/reviews/thiruvirutham_tidley.csv"
DEFAULT_DAV_SCRAPED = ROOT / "poc/output/thiruvirutham_dravidaveda_scraped.json"
DEFAULT_MANUAL = ROOT / "poc/input/thiruvirutham_11_20_manual.txt"
DEFAULT_MANUAL_21_40 = ROOT / "poc/input/thiruvirutham_21_40_manual.txt"
DEFAULT_MANUAL_41 = ROOT / "poc/input/thiruvirutham_41_manual.txt"
PRABANDHAM_TITLE = "திருவிருத்தம், Thiruvirutham"
DRAVIDAVEDA_BASE = "https://www.dravidaveda.org"
DRAVIDAVEDA_START = 2519
DRAVIDAVEDA_END = 2577
DRAVIDAVEDA_PATTU_START = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Thiruvirutham (2478+) into POC")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--url", default=TIDLEY_URL)
    parser.add_argument("--pattu-limit", type=int, default=DEFAULT_PATTU_LIMIT)
    parser.add_argument(
        "--manual-file",
        action="append",
        default=[],
        help="Validated manual pasuram text (repeat for multiple files)",
    )
    parser.add_argument("--manual-pattu-start", type=int, default=11)
    parser.add_argument("--manual-pattu-end", type=int, default=41)
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--review-csv", default=str(DEFAULT_REVIEW_CSV))
    parser.add_argument("--dry-run", action="store_true", help="Scrape and process only; no DB write")
    parser.add_argument("--apply", action="store_true", help="Replace pasuram range rows in POC table")
    parser.add_argument("--no-themes", action="store_true")
    parser.add_argument(
        "--tidley-only",
        action="store_true",
        help="Skip manual file even if present (tidley scrape only)",
    )
    parser.add_argument(
        "--skip-dravidaveda",
        action="store_true",
        help="Skip dravidaveda.org scrape (pattu 42–100)",
    )
    parser.add_argument("--dravidaveda-start", type=int, default=DRAVIDAVEDA_START)
    parser.add_argument("--dravidaveda-end", type=int, default=DRAVIDAVEDA_END)
    parser.add_argument("--dravidaveda-pattu-start", type=int, default=DRAVIDAVEDA_PATTU_START)
    parser.add_argument(
        "--dravidaveda-scraped-json",
        default=str(DEFAULT_DAV_SCRAPED),
        help="Intermediate JSON from dravidaveda scrape",
    )
    return parser.parse_args()


def _manual_paths(args: argparse.Namespace) -> list[Path]:
    if args.manual_file:
        return [Path(path) for path in args.manual_file]
    paths: list[Path] = []
    if DEFAULT_MANUAL.exists():
        paths.append(DEFAULT_MANUAL)
    if DEFAULT_MANUAL_21_40.exists():
        paths.append(DEFAULT_MANUAL_21_40)
    if DEFAULT_MANUAL_41.exists():
        paths.append(DEFAULT_MANUAL_41)
    return paths


def load_sections(args: argparse.Namespace) -> list[PattuSection]:
    sections = parse_pattu_sections(url=args.url, pattu_limit=args.pattu_limit)
    print(summarize_sections(sections))

    manual_paths = _manual_paths(args)
    if not args.tidley_only and manual_paths:
        manual_sections: list[PattuSection] = []
        for manual_path in manual_paths:
            if not manual_path.exists():
                raise FileNotFoundError(f"Manual file not found: {manual_path}")
            parsed = parse_manual_file(
                manual_path,
                pattu_start=args.manual_pattu_start,
                pattu_end=args.manual_pattu_end,
            )
            print(f"From {manual_path}:")
            print(summarize_manual_sections(parsed))
            manual_sections.extend(parsed)
        by_pattu = {section.pattu_number: section for section in sections}
        for section in manual_sections:
            by_pattu[section.pattu_number] = section
        sections = [by_pattu[key] for key in sorted(by_pattu)]
        print(f"Combined pattus: {len(sections)}")
    elif args.manual_file:
        raise FileNotFoundError("Manual file(s) not found")

    return sections


def _renumber_padham_rows(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sorted_records = sorted(records, key=lambda row: (row["PasuramNumber"], row.get("PadhamNumber") or 0))
    renumbered: List[Dict[str, Any]] = []
    for _, group in groupby(sorted_records, key=lambda row: row["PasuramNumber"]):
        for padham_number, record in enumerate(group, start=1):
            updated = dict(record)
            updated["PadhamNumber"] = padham_number
            renumbered.append(updated)
    return renumbered


def dravidaveda_rows_to_records(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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


def load_dravidaveda_records(args: argparse.Namespace) -> List[Dict[str, Any]]:
    scraped_json = Path(args.dravidaveda_scraped_json)
    print(
        f"Scraping dravidaveda {args.dravidaveda_start}-{args.dravidaveda_end} "
        f"(pattu {args.dravidaveda_pattu_start}+)"
    )
    raw_rows = scrape_range(
        base_url=DRAVIDAVEDA_BASE,
        start=args.dravidaveda_start,
        end=args.dravidaveda_end,
        prabandham=PRABANDHAM,
        title="",
        alzwar=ALZWAR,
        pattu_number=None,
        pattu_number_start=args.dravidaveda_pattu_start,
        output_path=scraped_json,
    )
    merged_rows = merge_comment_rows(raw_rows)
    records = dravidaveda_rows_to_records(merged_rows)
    pasuram_count = len({record["PasuramNumber"] for record in records})
    print(f"Dravidaveda pasurams: {pasuram_count}, padham rows: {len(records)}")
    expected = set(range(args.dravidaveda_start, args.dravidaveda_end + 1))
    found = {record["PasuramNumber"] for record in records}
    missing = sorted(expected - found)
    if missing:
        print("Dravidaveda pages not found (skipped — add from book manually):")
        for pasuram_number in missing:
            pattu = pasuram_number - (PASURAM_NUMBER_BASE - 1)
            print(f"  PasuramNumber {pasuram_number} (Pattu {pattu}): {DRAVIDAVEDA_BASE}/{pasuram_number}/")
    return records


def main() -> None:
    args = parse_args()
    output_json = Path(args.output_json)
    review_csv = Path(args.review_csv)

    sections = load_sections(args)

    records = sections_to_records(sections)
    for record in records:
        record["PrabandhamTitle"] = PRABANDHAM_TITLE

    if not args.skip_dravidaveda:
        records.extend(load_dravidaveda_records(args))

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

    write_review_csv(sections, review_csv)
    print(f"Wrote {review_csv}")

    start = min(record["PasuramNumber"] for record in records)
    end = max(record["PasuramNumber"] for record in records)

    if args.dry_run and not args.apply:
        print("Dry run complete (no DB changes).")
        return

    if not args.apply:
        print(f"Use --apply to load into POC (range {start}-{end}).")
        return

    config = load_config(args.config)
    db = config.database
    delete_pasuram_range(db, start, end, dry_run=False)
    inserted = load_json_to_db(output_json, db, dry_run=False)
    print(f"Loaded {inserted} rows into {db.table} for {PRABANDHAM} ({start}-{end})")


if __name__ == "__main__":
    main()
