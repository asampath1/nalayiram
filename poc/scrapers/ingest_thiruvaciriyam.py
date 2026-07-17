#!/usr/bin/env python3
"""Ingest திருவாசிரியம் from manual book text → transliterate → themes → POC JSON/DB."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from poc.config import load_config
from poc.db_loader import load_json_to_db
from poc.fill_workbook import transliterate_records_from_config
from poc.generate_similar_words import finalize_records
from poc.json_exporter import export_to_json
from poc.load_workbook import delete_pasuram_range
from poc.scrapers.thiruvirutham_tidley import sections_to_records
from poc.scrapers.thiruvaciriyam_manual import (
    ALZWAR,
    PASURAM_NUMBER_BASE,
    PRABANDHAM,
    parse_manual_file,
    summarize_manual_sections,
)

DEFAULT_JSON = ROOT / "poc/output/thiruvaciriyam_poc.json"
DEFAULT_MANUAL = ROOT / "poc/திருவாசிரியம்.txt"
PASURAM_START = PASURAM_NUMBER_BASE + 1
PASURAM_END = PASURAM_NUMBER_BASE + 7
PRABANDHAM_TITLE = "திருவாசிரியம், Thiruvaciriyam"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Thiruvaciriyam (2578-2584) into POC")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--manual-file", default=str(DEFAULT_MANUAL))
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--dry-run", action="store_true", help="Process only; no DB write")
    parser.add_argument("--apply", action="store_true", help="Replace pasuram range rows in POC table")
    parser.add_argument("--no-themes", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manual_path = Path(args.manual_file)
    output_json = Path(args.output_json)

    sections = parse_manual_file(manual_path)
    print(summarize_manual_sections(sections))

    records = sections_to_records(
        sections,
        prabandham=PRABANDHAM,
        pasuram_number_base=PASURAM_NUMBER_BASE,
        alzwar=ALZWAR,
    )
    for record in records:
        record["PrabandhamTitle"] = PRABANDHAM_TITLE
        record["Title"] = ""

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
        print(f"Use --apply to load into POC (range {PASURAM_START}-{PASURAM_END}).")
        return

    config = load_config(args.config)
    db = config.database
    delete_pasuram_range(db, PASURAM_START, PASURAM_END, dry_run=False)
    inserted = load_json_to_db(output_json, db, dry_run=False)
    print(f"Loaded {inserted} rows into {db.table} for {PRABANDHAM} ({PASURAM_START}-{PASURAM_END})")


if __name__ == "__main__":
    main()
