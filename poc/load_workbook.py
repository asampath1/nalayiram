#!/usr/bin/env python3
"""Load filled workbook JSON into PasuramsArthamTablePOC (POC only)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from poc.config import load_config
from poc.db_loader import _load_records, load_json_to_db


def delete_pasuram_range(config, start: int, end: int, dry_run: bool) -> int:
    conn = mysql.connector.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
    )
    cursor = conn.cursor()
    query = (
        f"DELETE FROM `{config.table}` "
        f"WHERE PasuramNumber >= %s AND PasuramNumber <= %s"
    )
    if dry_run:
        cursor.execute(
            f"SELECT COUNT(*) FROM `{config.table}` WHERE PasuramNumber >= %s AND PasuramNumber <= %s",
            (start, end),
        )
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"DRY RUN: would delete {count} rows in pasuram range {start}-{end}")
        return count

    cursor.execute(query, (start, end))
    deleted = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Deleted {deleted} existing rows for pasuram range {start}-{end}")
    return deleted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load filled JSON into PasuramsArthamTablePOC")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--input-json", default="poc/output/thiruvandhathi_filled.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--replace-range",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="Delete existing POC rows in pasuram range before insert (e.g. 2182 2381)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    json_path = Path(args.input_json)
    if not json_path.exists():
        raise FileNotFoundError(json_path)

    records = _load_records(json_path)
    if not records:
        print("No records to load.")
        return

    pasuram_nums = [r.get("PasuramNumber") for r in records if r.get("PasuramNumber") is not None]
    start = min(pasuram_nums)
    end = max(pasuram_nums)
    print(f"JSON has {len(records)} rows, pasuram range {start}-{end}")

    if args.replace_range:
        r_start, r_end = args.replace_range
        delete_pasuram_range(config.database, r_start, r_end, args.dry_run)
    elif not args.dry_run:
        print(
            f"Warning: not replacing existing rows. Use --replace-range {start} {end} "
            "to delete before insert."
        )

    inserted = load_json_to_db(json_path, config.database, dry_run=args.dry_run)
    print(f"{'Would insert' if args.dry_run else 'Inserted'} {inserted} rows into {config.database.table}")


if __name__ == "__main__":
    main()
