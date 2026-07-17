#!/usr/bin/env python3
"""Scrape பெருமாள் திருமொழி from tidley (+ dravidaveda 684) → transliterate → themes → POC JSON/DB."""
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
from poc.scrapers.perumal_thirumozhi_tidley import (
    ALZWAR,
    PASURAM_END,
    PASURAM_START,
    PRABANDHAM,
    apply_pattu_aliases,
    parse_all_pathigams,
    sections_to_records,
    summarize_sections,
    write_review_csv,
)

DEFAULT_JSON = ROOT / "poc/output/perumal_thirumozhi_poc.json"
DEFAULT_REVIEW_CSV = ROOT / "lookupsimilarwords/reviews/perumal_thirumozhi_tidley.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Perumal Thirumozhi (647-751) into POC")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--review-csv", default=str(DEFAULT_REVIEW_CSV))
    parser.add_argument("--dry-run", action="store_true", help="Scrape and process only; no DB write")
    parser.add_argument("--apply", action="store_true", help="Replace pasuram range rows in POC table")
    parser.add_argument("--no-themes", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_json = Path(args.output_json)
    review_csv = Path(args.review_csv)

    grouped = parse_all_pathigams()
    sections = [section for item in grouped for section in item.sections]
    print(summarize_sections(sections))
    print(f"Total pasurams: {len(sections)}")

    records = sections_to_records(grouped)
    print(f"Raw padham rows: {len(records)}")

    config_path = Path(args.config)
    records = transliterate_records_from_config(records, config_path)
    records = finalize_records(
        records,
        apply_themes=not args.no_themes,
        themes=None,
        group_by_pasuram_number=False,
    )
    records = apply_pattu_aliases(records)

    export_to_json(records, output_json)
    print(f"Wrote {output_json}")

    write_review_csv(grouped, review_csv)
    print(f"Wrote {review_csv}")

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
    print(
        f"Loaded {inserted} rows into {db.table} for {PRABANDHAM} "
        f"({PASURAM_START}-{PASURAM_END}), Alzwar={ALZWAR}"
    )

    from poc.scripts.refresh_divyadesam_alwar_matrix import refresh_matrix

    print("Refreshing DivyaDesam × Alwar matrix cache...")
    refresh_matrix(args.config, env="poc")


if __name__ == "__main__":
    main()
