#!/usr/bin/env python3
"""Scrape பெரிய திருமொழி ஏழாம் பத்து (1548-1647) from dravidaveda → POC JSON/DB."""
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
from poc.scrapers.dravidaveda_periya_thirumozhi_patthu7_crawl import scrape_patthu7

PRABANDHAM = "பெரிய திருமொழி"
PRABANDHAM_TITLE = "பெரிய திருமொழி, Periya Thirumozhi"
ALZWAR = "திருமங்கையாழ்வார்"
PATHU_NUMBER = 7
PASURAM_START = 1548
PASURAM_END = 1647
NUMERIC_START = 1638
DRAVIDAVEDA_BASE = "https://www.dravidaveda.org"
DEFAULT_JSON = ROOT / "poc/output/periya_thirumozhi_patthu7_poc.json"
DEFAULT_SCRAPED = ROOT / "poc/output/periya_thirumozhi_patthu7_dravidaveda_scraped.json"


def pattu_number_for_pasuram(pasuram_number: int) -> int:
    """Verse index within pathigam (1-10), matching tidley ingest convention."""
    return ((pasuram_number - PASURAM_START) % 10) + 1


def pathigam_within_pathu(pasuram_number: int) -> int:
    """Pathigam index within the seventh patthu (1–10), matching UI 7-1-1 style."""
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
        description="Ingest Periya Thirumozhi 7th patthu (1548-1647) into POC"
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


def pathigam_range_for_pasurams(start: int, end: int) -> tuple[int, int]:
    pathigam_start = (start - PASURAM_START) // 10 + 1
    pathigam_end = (end - PASURAM_START) // 10 + 1
    return pathigam_start, pathigam_end


def load_scraped_records(args: argparse.Namespace) -> List[Dict[str, Any]]:
    scraped_json = Path(args.scraped_json)
    if not args.skip_scrape:
        import json

        pathigam_start, pathigam_end = pathigam_range_for_pasurams(args.start, args.end)
        raw_rows: List[Dict[str, Any]] = []
        crawl_end = min(pathigam_end, 9)
        if pathigam_start <= 9:
            print(
                f"Crawling dravidaveda pathigams 7-{pathigam_start}..7-{crawl_end} "
                f"(pasurams {args.start}-{min(args.end, NUMERIC_START - 1)})"
            )
            raw_rows.extend(
                scrape_patthu7(
                    pathigam_start=max(pathigam_start, 1),
                    pathigam_end=crawl_end,
                    output_path=scraped_json,
                    dry_run=False,
                )
            )
        if pathigam_end >= 10 and args.end >= NUMERIC_START:
            numeric_start = max(args.start, NUMERIC_START)
            numeric_end = min(args.end, PASURAM_END)
            numeric_json = scraped_json.with_name(
                scraped_json.stem + "_numeric1638.json"
            )
            print(
                f"Numeric scrape 7-10: {DRAVIDAVEDA_BASE}/{{n}}/ "
                f"(pasurams {numeric_start}-{numeric_end})"
            )
            raw_rows.extend(
                scrape_range(
                    base_url=DRAVIDAVEDA_BASE,
                    start=numeric_start,
                    end=numeric_end,
                    prabandham=PRABANDHAM,
                    title="",
                    alzwar=ALZWAR,
                    pattu_number=None,
                    pattu_number_start=pattu_number_for_pasuram(numeric_start),
                    output_path=numeric_json,
                )
            )
        scraped_json.parent.mkdir(parents=True, exist_ok=True)
        scraped_json.write_text(
            json.dumps(raw_rows, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
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
        records.extend(inject_pasuram_only_stubs(missing))
        print(
            f"Injected {len(missing)} pasuram-only stub row(s) from poc/pasuram.txt "
            f"(no Dravidaveda padhavurai)."
        )
    return records


def inject_pasuram_only_stubs(missing: List[int]) -> List[Dict[str, Any]]:
    """One padham-less row per missing pasuram, Pasuram text from poc/pasuram.txt."""
    from poc.scripts.replace_periya_thirumozhi_patthu7_pasuram_from_txt import (
        PASURAM_TXT,
        extract_verses,
    )

    verses = extract_verses(PASURAM_TXT)
    stubs: List[Dict[str, Any]] = []
    for pasuram_number in missing:
        pasuram_text = verses.get(pasuram_number, "")
        if not pasuram_text:
            raise RuntimeError(
                f"Missing pasuram text in poc/pasuram.txt for {pasuram_number}"
            )
        stubs.append(
            {
                "Prabandham": PRABANDHAM,
                "PasuramNumber": pasuram_number,
                "Pasuram": pasuram_text,
                "PattuNumber": pattu_number_for_pasuram(pasuram_number),
                "Padham": "",
                "Meaning": "",
                "Alzwar": ALZWAR,
                "PadhamNumber": 1,
                "Title": "",
                "Word": "",
                "SimilarWords": "",
                "NithyaanusandhamIndex": None,
                "PrabandhamTitle": PRABANDHAM_TITLE,
            }
        )
    return stubs


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
