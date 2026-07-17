#!/usr/bin/env python3
"""Scrape பெரிய திருமொழி இரண்டாம் பத்து (1048-1147) from dravidaveda → POC JSON/DB."""
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

PRABANDHAM = "பெரிய திருமொழி"
PRABANDHAM_TITLE = "பெரிய திருமொழி, Periya Thirumozhi"
ALZWAR = "திருமங்கையாழ்வார்"
PATHU_NUMBER = 2
PASURAM_START = 1048
PASURAM_END = 1147
DRAVIDAVEDA_BASE = "https://www.dravidaveda.org"
DEFAULT_JSON = ROOT / "poc/output/periya_thirumozhi_patthu2_poc.json"
DEFAULT_SCRAPED = ROOT / "poc/output/periya_thirumozhi_patthu2_dravidaveda_scraped.json"


def pattu_number_for_pasuram(pasuram_number: int) -> int:
    """Verse index within pathigam (1-10), matching tidley ingest convention."""
    return ((pasuram_number - PASURAM_START) % 10) + 1


def pathigam_within_pathu(pasuram_number: int) -> int:
    """Pathigam index within the second patthu (1–10), matching UI 2-1-1 style."""
    return (pasuram_number - PASURAM_START) // 10 + 1


def pathigam_suffix(pasuram_number: int) -> str:
    return (
        f"{PATHU_NUMBER}-{pathigam_within_pathu(pasuram_number)}"
        f"-{pattu_number_for_pasuram(pasuram_number)}"
    )


def pathigam_search_aliases(pasuram_number: int) -> List[str]:
    pathigam = pathigam_within_pathu(pasuram_number)
    pattu = pattu_number_for_pasuram(pasuram_number)
    a, b, c = PATHU_NUMBER, pathigam, pattu
    return [f"{a}.{b}.{c}", f"{a}-{b}-{c}", f"{a} {b} {c}"]


def append_pasuram_suffix(pasuram_text: str, suffix: str) -> str:
    lines = [line.rstrip() for line in str(pasuram_text or "").splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return pasuram_text
    last = lines[-1].rstrip()
    if suffix in last:
        return pasuram_text
    lines[-1] = f"{last} –{suffix}"
    return "\n".join(lines)


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
        pasuram_number = int(row["PasuramNumber"])
        suffix = pathigam_suffix(pasuram_number)
        pasuram_text = append_pasuram_suffix(row.get("Pasuram", ""), suffix)
        records.append(
            {
                "Prabandham": PRABANDHAM,
                "PasuramNumber": pasuram_number,
                "Pasuram": pasuram_text,
                "PattuNumber": pattu_number_for_pasuram(pasuram_number),
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


def apply_pathigam_aliases(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    updated: List[Dict[str, Any]] = []
    for record in records:
        row = dict(record)
        aliases = ",".join(pathigam_search_aliases(int(row["PasuramNumber"])))
        similar = str(row.get("SimilarWords", "") or "").strip()
        if aliases:
            similar = f"{similar},{aliases}" if similar else aliases
        row["SimilarWords"] = similar
        updated.append(row)
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest Periya Thirumozhi 2nd patthu (1048-1147) into POC"
    )
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--scraped-json", default=str(DEFAULT_SCRAPED))
    parser.add_argument("--start", type=int, default=PASURAM_START)
    parser.add_argument("--end", type=int, default=PASURAM_END)
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
        print(f"Scraping dravidaveda {args.start}-{args.end} (இரண்டாம் பத்து)")
        raw_rows = scrape_range(
            base_url=DRAVIDAVEDA_BASE,
            start=args.start,
            end=args.end,
            prabandham=PRABANDHAM,
            title="",
            alzwar=ALZWAR,
            pattu_number=None,
            pattu_number_start=None,
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
            print(
                f"  PasuramNumber {pasuram_number} "
                f"({pathigam_suffix(pasuram_number)}): "
                f"{DRAVIDAVEDA_BASE}/{pasuram_number}/"
            )
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
    records = apply_pathigam_aliases(records)

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
    print(
        f"Loaded {inserted} rows into {db.table} for {PRABANDHAM} "
        f"({args.start}-{args.end})"
    )

    from poc.scripts.refresh_divyadesam_alwar_matrix import refresh_matrix

    refresh_matrix(args.config, env="poc", dry_run=False)
    print("Refreshed DivyaDesamAlwarMatrix (poc).")


if __name__ == "__main__":
    main()
