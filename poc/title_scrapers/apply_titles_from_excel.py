#!/usr/bin/env python3
"""Load per-pasuram Title commentary from Excel and apply to DB."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from poc.config import load_config
from poc.title_scrapers.apply_titles import apply_titles_to_db, write_csv, write_json
from poc.title_scrapers.base import PasuramTitleRecord, join_title_blocks


def load_titles_from_excel(
    path: Path,
    *,
    sheet_name: str | int | None = 0,
) -> List[PasuramTitleRecord]:
    df = pd.read_excel(path, sheet_name=sheet_name)
    required = {"PattuNumber", "PasuramNumber", "Title"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Excel missing columns {sorted(missing)}: {path}")

    has_prabandham = "Prabandham" in df.columns
    records: List[PasuramTitleRecord] = []
    for _, row in df.iterrows():
        excel_pattu = int(row["PattuNumber"])
        excel_pasuram = int(row["PasuramNumber"])
        prabandham = ""
        if has_prabandham and not pd.isna(row["Prabandham"]):
            prabandham = str(row["Prabandham"]).strip()

        # Thaniyan rows in workbook use PattuNumber=0 and Pattu index in PasuramNumber.
        if excel_pattu == 0 and prabandham and "தனியன்" in prabandham:
            pasuram_number = 0
            pattu_number = excel_pasuram
        else:
            pasuram_number = excel_pasuram
            pattu_number = excel_pattu

        title_raw = row["Title"]
        if pd.isna(title_raw):
            title = ""
        else:
            title = join_title_blocks([str(title_raw)])

        records.append(
            PasuramTitleRecord(
                pattu_number=pattu_number,
                pasuram_number=pasuram_number,
                pasuram="",
                title=title,
                prabandham=prabandham,
            )
        )

    records.sort(key=lambda r: (r.pasuram_number, r.pattu_number))
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply Title column from Excel workbook to DB")
    parser.add_argument("--xlsx", required=True, help="Workbook with PattuNumber, PasuramNumber, Title")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: first sheet)")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument(
        "--csv",
        default=None,
        help="Optional CSV export path (default: poc/output/{stem}_titles.csv)",
    )
    parser.add_argument(
        "--json",
        default=None,
        help="Optional JSON export path (default: poc/output/{stem}_titles.json)",
    )
    parser.add_argument("--apply", action="store_true", help="Write titles to DB")
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip CSV/JSON export",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    xlsx_path = Path(args.xlsx)
    if not xlsx_path.exists():
        raise FileNotFoundError(xlsx_path)

    sheet: str | int = args.sheet
    if isinstance(sheet, str) and sheet.isdigit():
        sheet = int(sheet)

    records = load_titles_from_excel(xlsx_path, sheet_name=sheet)
    stem = xlsx_path.stem

    if not args.skip_export:
        csv_path = Path(args.csv or ROOT / "poc" / "output" / f"{stem}_titles.csv")
        json_path = Path(args.json or ROOT / "poc" / "output" / f"{stem}_titles.json")
        write_csv(records, csv_path)
        write_json(records, json_path)
        print(f"Wrote {len(records)} pasurams to {csv_path}")
        print(f"Wrote {len(records)} pasurams to {json_path}")

    if args.apply:
        total = apply_titles_to_db(records, args.config, apply=True)
        print(f"Applied titles to {total} rows in {load_config(args.config).database.table}")
    else:
        total = apply_titles_to_db(records, args.config, apply=False)
        print(f"DRY RUN: would update {total} rows")


if __name__ == "__main__":
    main()
