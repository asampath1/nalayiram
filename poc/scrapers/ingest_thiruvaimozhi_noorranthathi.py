#!/usr/bin/env python3
"""Ingest திருவாய்மொழி நூற்றந்தாதி from poc/pasuram.txt → POC JSON/DB (no padham)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from poc.acharya_thaniyan_numbers import (
    LEGACY_THANIYAN_PASURAM_NUMBERS,
    THIRUVAIMOZHI_NOORRANTHATHI_THANIYAN_PATTUS,
    UPADESA_THANIYAN_PRABANDHAM,
)
from poc.config import load_config
from poc.db_loader import load_json_to_db
from poc.generate_similar_words import finalize_records
from poc.json_exporter import export_to_json
from poc.load_workbook import delete_pasuram_range
from poc.scrapers.thiruvaimozhi_noorranthathi_manual import (
    EXPECTED_PATTUS,
    LEGACY_THANIYAN_PRABANDHAMS,
    PASURAM_END,
    PASURAM_START,
    PRABANDHAM,
    THANIYAN_PATTUS,
    DEFAULT_SOURCE,
    parse_source,
    sections_to_records,
    summarize_sections,
    thaniyan_prabandham_names,
    write_review_csv,
)

DEFAULT_JSON = ROOT / "poc/output/thiruvaimozhi_noorranthathi_poc.json"
DEFAULT_REVIEW_CSV = ROOT / "lookupsimilarwords/reviews/thiruvaimozhi_noorranthathi_manual.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"Ingest {PRABANDHAM} ({PASURAM_START}-{PASURAM_END}) into POC"
    )
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--review-csv", default=str(DEFAULT_REVIEW_CSV))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-themes", action="store_true")
    return parser.parse_args()


def revert_legacy_thaniyan_pasuram_numbers(db, dry_run: bool) -> int:
    import mysql.connector

    conn = mysql.connector.connect(
        host=db.host, port=db.port, user=db.user, password=db.password, database=db.database
    )
    cur = conn.cursor()
    legacy = list(LEGACY_THANIYAN_PASURAM_NUMBERS)
    placeholders = ", ".join(["%s"] * len(legacy))
    prabandhams = list(thaniyan_prabandham_names()) + [UPADESA_THANIYAN_PRABANDHAM]
    name_placeholders = ", ".join(["%s"] * len(prabandhams))
    where = f"PasuramNumber IN ({placeholders}) AND Prabandham IN ({name_placeholders})"
    params = (*legacy, *prabandhams)
    if dry_run:
        cur.execute(f"SELECT COUNT(*) FROM `{db.table}` WHERE {where}", params)
        count = cur.fetchone()[0]
        print(f"DRY RUN: would revert {count} legacy thaniyan rows to PasuramNumber=0")
        cur.close()
        conn.close()
        return count
    cur.execute(
        f"UPDATE `{db.table}` SET PasuramNumber = 0 WHERE {where}",
        params,
    )
    updated = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if updated:
        print(f"Reverted {updated} legacy thaniyan row(s) to PasuramNumber=0")
    return updated


def delete_thaniyan_rows(db, dry_run: bool) -> int:
    import mysql.connector

    conn = mysql.connector.connect(
        host=db.host, port=db.port, user=db.user, password=db.password, database=db.database
    )
    cur = conn.cursor()
    pattu_placeholders = ", ".join(["%s"] * len(THANIYAN_PATTUS))
    prabandham_names = list(thaniyan_prabandham_names()) + list(LEGACY_THANIYAN_PRABANDHAMS)
    name_placeholders = ", ".join(["%s"] * len(prabandham_names))
    legacy = list(LEGACY_THANIYAN_PASURAM_NUMBERS)
    pn_placeholders = ", ".join(["%s"] * len(legacy))
    where = (
        f"(PattuNumber IN ({pattu_placeholders}) OR PattuNumber IN (1, 2)) "
        f"AND Prabandham IN ({name_placeholders}) "
        f"AND PasuramNumber IN (0, {pn_placeholders})"
    )
    params = (*THANIYAN_PATTUS, *prabandham_names, *legacy)
    if dry_run:
        cur.execute(f"SELECT COUNT(*) FROM `{db.table}` WHERE {where}", params)
        count = cur.fetchone()[0]
        print(f"DRY RUN: would delete {count} thaniyan rows (PattuNumber={THANIYAN_PATTUS})")
        cur.close()
        conn.close()
        return count
    cur.execute(f"DELETE FROM `{db.table}` WHERE {where}", params)
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"Deleted {deleted} thaniyan rows (PattuNumber={THANIYAN_PATTUS})")
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
    delete_pasuram_range(db, PASURAM_START, PASURAM_END, dry_run=False)
    delete_thaniyan_rows(db, dry_run=False)
    revert_legacy_thaniyan_pasuram_numbers(db, dry_run=False)
    inserted = load_json_to_db(output_json, db, dry_run=False)
    print(
        f"Loaded {inserted} rows into {db.table} for {PRABANDHAM} "
        f"({PASURAM_START}-{PASURAM_END} + thaniyans {THANIYAN_PATTUS})"
    )


if __name__ == "__main__":
    main()
