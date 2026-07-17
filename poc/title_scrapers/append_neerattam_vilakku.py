#!/usr/bin/env python3
"""Append tidley விளக்க உரை to existing Title for Periyazhvar sections."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config
from poc.title_scrapers.periyazhvar_vilakku_tidley import (
    SECTIONS,
    append_vilakku_to_title,
    scrape_section_vilakku_urai,
)

DEFAULT_CSV_BY_SECTION = {
    "neerattam": ROOT / "lookupsimilarwords" / "reviews" / "neerattam_vilakku_urai_append.csv",
    "poochoodal": ROOT / "lookupsimilarwords" / "reviews" / "poochoodal_vilakku_urai_append.csv",
    "kappidal": ROOT / "lookupsimilarwords" / "reviews" / "kappidal_vilakku_urai_append.csv",
    "senniyongu": ROOT / "lookupsimilarwords" / "reviews" / "senniyongu_vilakku_urai_append.csv",
}


def fetch_existing_titles(
    config_path: str,
    pasuram_numbers: List[int],
) -> Dict[int, str]:
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
    placeholders = ",".join(["%s"] * len(pasuram_numbers))
    cursor.execute(
        f"SELECT PasuramNumber, MAX(Title) FROM `{table}` "
        f"WHERE PasuramNumber IN ({placeholders}) GROUP BY PasuramNumber",
        pasuram_numbers,
    )
    titles = {int(row[0]): (row[1] or "") for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return titles


def apply_appended_titles(
    config_path: str,
    records,
    *,
    section_prefix: str,
    apply: bool,
    csv_path: Path,
) -> int:
    config = load_config(config_path)
    pasuram_numbers = [record.pasuram_number for record in records]
    existing = fetch_existing_titles(config_path, pasuram_numbers)

    rows_out = []
    updated_rows = 0

    conn = mysql.connector.connect(
        host=config.database.host,
        port=config.database.port,
        user=config.database.user,
        password=config.database.password,
        database=config.database.database,
    )
    cursor = conn.cursor()
    table = config.database.table

    for record in records:
        old_title = existing.get(record.pasuram_number, "")
        new_title = append_vilakku_to_title(
            old_title,
            record.vilakku_urai,
            section_prefix=section_prefix,
        )
        rows_out.append(
            {
                "PasuramNumber": record.pasuram_number,
                "PattuNumber": record.pattu_number,
                "ExistingTitle": old_title,
                "VilakkuUrai": record.vilakku_urai,
                "NewTitle": new_title,
            }
        )

        if apply:
            cursor.execute(
                f"UPDATE `{table}` SET Title = %s WHERE PasuramNumber = %s",
                (new_title, record.pasuram_number),
            )
            conn.commit()
            count = cursor.rowcount
            updated_rows += count
            print(
                f"Updated PasuramNumber={record.pasuram_number} "
                f"PattuNumber={record.pattu_number} rows={count}"
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

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "PasuramNumber",
                "PattuNumber",
                "ExistingTitle",
                "VilakkuUrai",
                "NewTitle",
            ],
        )
        writer.writeheader()
        writer.writerows(rows_out)

    return updated_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append Periyazhvar vilakku urai from tidley to existing Title"
    )
    parser.add_argument(
        "--section",
        choices=sorted(SECTIONS.keys()),
        default="neerattam",
        help="Periyazhvar section (default: neerattam)",
    )
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--csv", default=None)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    section = SECTIONS[args.section]
    csv_path = Path(args.csv) if args.csv else DEFAULT_CSV_BY_SECTION[args.section]

    records = scrape_section_vilakku_urai(section)
    pasuram_range = (
        f"{records[0].pasuram_number}-{records[-1].pasuram_number}"
        if records
        else "?"
    )
    print(f"Scraped vilakku urai for {len(records)} pasurams ({pasuram_range}) — {section.label}")
    total = apply_appended_titles(
        args.config,
        records,
        section_prefix=section.title_prefix,
        apply=args.apply,
        csv_path=csv_path,
    )
    table = load_config(args.config).database.table
    mode = "Applied" if args.apply else "Would update"
    print(f"{mode} {total} rows in {table}")
    print(f"Review CSV: {csv_path}")


if __name__ == "__main__":
    main()
