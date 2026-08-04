#!/usr/bin/env python3
"""Ingest உபதேச ரத்னமாலை from poc/pasuram.txt → POC JSON/DB (no padham)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from poc.config import load_config
from poc.db_loader import load_json_to_db
from poc.generate_similar_words import finalize_records
from poc.json_exporter import export_to_json
from poc.load_workbook import delete_pasuram_range
from poc.acharya_thaniyan_numbers import UPADESA_THANIYAN_PATTU
from poc.scrapers.upadesa_rathnamalai_manual import (
    PRABANDHAM_THANIYAN,
    EXPECTED_PATTUS,
    PASURAM_SHARED_73_74,
    PASURAM_START,
    PRABANDHAM,
    THANIYAN_PATTU,
    DEFAULT_SOURCE,
    parse_source,
    sections_to_records,
    summarize_sections,
    write_review_csv,
)

DEFAULT_JSON = ROOT / "poc/output/upadesa_rathnamalai_poc.json"
DEFAULT_REVIEW_CSV = ROOT / "lookupsimilarwords/reviews/upadesa_rathnamalai_manual.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"Ingest {PRABANDHAM} ({PASURAM_START}-{PASURAM_SHARED_73_74}) into POC"
    )
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--review-csv", default=str(DEFAULT_REVIEW_CSV))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-themes", action="store_true")
    return parser.parse_args()


def delete_thaniyan_pattu(db, pattu: int, prabandham_stem: str, dry_run: bool) -> int:
    import mysql.connector

    conn = mysql.connector.connect(
        host=db.host, port=db.port, user=db.user, password=db.password, database=db.database
    )
    cur = conn.cursor()
    where = (
        "PattuNumber = %s AND Prabandham = %s AND PasuramNumber IN (0, 4058)"
    )
    if dry_run:
        cur.execute(
            f"SELECT COUNT(*) FROM `{db.table}` WHERE {where}",
            (pattu, PRABANDHAM_THANIYAN),
        )
        count = cur.fetchone()[0]
        print(f"DRY RUN: would delete {count} thaniyan rows (PattuNumber={pattu})")
        cur.close()
        conn.close()
        return count
    cur.execute(
        f"DELETE FROM `{db.table}` WHERE {where}",
        (pattu, PRABANDHAM_THANIYAN),
    )
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"Deleted {deleted} thaniyan rows (PattuNumber={pattu})")
    return deleted


def main() -> None:
    args = parse_args()
    sections = parse_source(Path(args.source))
    print(summarize_sections(sections))
    main_verses = [s for s in sections if not s.is_thaniyan]
    if len(main_verses) != EXPECTED_PATTUS:
        raise SystemExit(f"Expected {EXPECTED_PATTUS} verses, got {len(main_verses)}")

    records = sections_to_records(sections)
    records = finalize_records(
        records,
        apply_themes=not args.no_themes,
        themes=None,
        group_by_pasuram_number=False,
    )
    output_json = Path(args.output_json)
    export_to_json(records, output_json)
    print(f"Wrote {output_json} ({len(records)} rows)")
    review_csv = Path(args.review_csv)
    write_review_csv(sections, review_csv)
    print(f"Wrote {review_csv}")

    if args.dry_run and not args.apply:
        print("Dry run complete (no DB changes).")
        return
    if not args.apply:
        print("Use --apply to load into POC.")
        return

    config = load_config(args.config)
    db = config.database
    delete_pasuram_range(db, PASURAM_START, PASURAM_SHARED_73_74, dry_run=False)
    delete_thaniyan_pattu(db, THANIYAN_PATTU, "உபதேச ரத்னமாலை", dry_run=False)
    inserted = load_json_to_db(output_json, db, dry_run=False)
    print(
        f"Loaded {inserted} rows into {db.table} for {PRABANDHAM} "
        f"({PASURAM_START}-{PASURAM_SHARED_73_74} + thaniyan {THANIYAN_PATTU})"
    )


if __name__ == "__main__":
    main()
