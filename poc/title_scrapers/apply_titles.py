#!/usr/bin/env python3
"""Scrape tidley titles and optionally apply them to POC/Test DB rows."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Callable, Iterable, List

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config
from poc.title_scrapers.base import PasuramTitleRecord
from poc.title_scrapers.irandam_tidley import scrape_irandam_titles
from poc.title_scrapers.moondram_tidley import scrape_moondram_titles
from poc.title_scrapers.nanmugan_tidley import scrape_nanmugan_titles

PRABANDHAM_CHOICES = {
    "nanmugan": {
        "label": "Nanmugan Thiruvandhathi (2382-2477)",
        "scrape": scrape_nanmugan_titles,
        "csv": ROOT / "lookupsimilarwords" / "reviews" / "nanmugan_titles_tidley.csv",
        "json": ROOT / "poc" / "output" / "nanmugan_titles_tidley.json",
    },
    "irandam": {
        "label": "Irandam Thiruvandhathi (2182-2281)",
        "scrape": scrape_irandam_titles,
        "csv": ROOT / "lookupsimilarwords" / "reviews" / "irandam_titles_tidley.csv",
        "json": ROOT / "poc" / "output" / "irandam_titles_tidley.json",
    },
    "moondram": {
        "label": "Moondram Thiruvandhathi (2282-2381)",
        "scrape": scrape_moondram_titles,
        "csv": ROOT / "lookupsimilarwords" / "reviews" / "moondram_titles_tidley.csv",
        "json": ROOT / "poc" / "output" / "moondram_titles_tidley.json",
    },
}


def write_csv(records: Iterable[PasuramTitleRecord], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["PasuramNumber", "Pasuram", "PattuNumber", "Title"],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "PasuramNumber": record.pasuram_number,
                    "Pasuram": record.pasuram,
                    "PattuNumber": record.pattu_number,
                    "Title": record.title,
                }
            )


def write_json(records: Iterable[PasuramTitleRecord], json_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "PasuramNumber": record.pasuram_number,
            "Pasuram": record.pasuram,
            "PattuNumber": record.pattu_number,
            "Title": record.title,
        }
        for record in records
    ]
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def apply_titles_to_db(
    records: List[PasuramTitleRecord],
    config_path: str,
    *,
    apply: bool,
) -> int:
    config = load_config(config_path)
    conn = mysql.connector.connect(
        host=config.database.host,
        port=config.database.port,
        user=config.database.user,
        password=config.database.password,
        database=config.database.database,
    )
    cursor = conn.cursor()
    table = config.database.table
    updated_rows = 0

    for record in records:
        if record.pasuram_number == 0 and record.pattu_number > 0:
            prabandham_like = f"%{record.prabandham.split('-')[0].strip()}%"
            where_sql = (
                f"PasuramNumber = 0 AND PattuNumber = %s AND Prabandham LIKE %s"
            )
            where_args = (record.pattu_number, prabandham_like)
        else:
            where_sql = "PasuramNumber = %s"
            where_args = (record.pasuram_number,)

        if apply:
            cursor.execute(
                f"UPDATE `{table}` SET Title = %s WHERE {where_sql}",
                (record.title, *where_args),
            )
            conn.commit()
            updated_rows += cursor.rowcount
            print(
                f"Updated PasuramNumber={record.pasuram_number} "
                f"PattuNumber={record.pattu_number} rows={cursor.rowcount}"
            )
        else:
            if record.pasuram_number == 0 and record.pattu_number > 0:
                prabandham_like = f"%{record.prabandham.split('-')[0].strip()}%"
                cursor.execute(
                    f"SELECT COUNT(*) FROM `{table}` "
                    f"WHERE PasuramNumber = 0 AND PattuNumber = %s AND Prabandham LIKE %s",
                    (record.pattu_number, prabandham_like),
                )
            else:
                cursor.execute(
                    f"SELECT COUNT(*) FROM `{table}` WHERE PasuramNumber = %s",
                    (record.pasuram_number,),
                )
            count = cursor.fetchone()[0]
            updated_rows += count
            print(
                f"DRY RUN: PasuramNumber={record.pasuram_number} "
                f"PattuNumber={record.pattu_number} rows={count}"
            )

    cursor.close()
    conn.close()
    return updated_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape tidley titles for Thiruvandhathi prabandhams")
    parser.add_argument(
        "--prabandham",
        choices=sorted(PRABANDHAM_CHOICES),
        default="nanmugan",
        help="Which prabandham to scrape/apply (default: nanmugan)",
    )
    parser.add_argument("--config", default="poc/config.ini", help="POC config for DB apply")
    parser.add_argument("--csv", help="CSV output path for vetting (default per prabandham)")
    parser.add_argument("--json", help="JSON output path (default per prabandham)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply scraped titles to DB (default is scrape/export only)",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip CSV/JSON export (use with --apply after vetting)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prabandham_cfg = PRABANDHAM_CHOICES[args.prabandham]
    scrape_fn: Callable[[], List[PasuramTitleRecord]] = prabandham_cfg["scrape"]
    records = scrape_fn()

    if not args.skip_export:
        csv_path = Path(args.csv or prabandham_cfg["csv"])
        json_path = Path(args.json or prabandham_cfg["json"])
        write_csv(records, csv_path)
        write_json(records, json_path)
        print(f"Wrote {len(records)} pasurams to {csv_path}")
        print(f"Wrote {len(records)} pasurams to {json_path}")

    if args.apply:
        total = apply_titles_to_db(records, args.config, apply=True)
        print(f"Applied titles to {total} rows in {load_config(args.config).database.table}")
    elif args.skip_export:
        total = apply_titles_to_db(records, args.config, apply=False)
        print(f"DRY RUN: would update {total} rows")


if __name__ == "__main__":
    main()
