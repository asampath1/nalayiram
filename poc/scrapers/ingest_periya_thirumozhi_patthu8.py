#!/usr/bin/env python3
"""Scrape பெரிய திருமொழி எட்டாம் பத்து (1648-1747) from dravidaveda → POC JSON/DB.

Unlike patthu 6/7, dravidaveda serves this patthu's padhavurai directly at
/{pasuram_number}/, so no category crawl is needed. Pages that 404 or return no
padham rows are flagged and skipped (pasuram-only stub injected from pasuram.txt).
"""
from __future__ import annotations

import argparse
import json
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
from poc.scraper_adapter import SCRAPER_PATH, load_scraper_module, normalize_scraped_row

PRABANDHAM = "பெரிய திருமொழி"
PRABANDHAM_TITLE = "பெரிய திருமொழி, Periya Thirumozhi"
ALZWAR = "திருமங்கையாழ்வார்"
PATHU_NUMBER = 8
PASURAM_START = 1648
PASURAM_END = 1747
DRAVIDAVEDA_BASE = "https://www.dravidaveda.org"
DEFAULT_JSON = ROOT / "poc/output/periya_thirumozhi_patthu8_poc.json"
DEFAULT_SCRAPED = ROOT / "poc/output/periya_thirumozhi_patthu8_dravidaveda_scraped.json"
MISSING_REPORT = ROOT / "lookupsimilarwords/reviews/periya_thirumozhi_patthu8_dravidaveda_missing.txt"


def pattu_number_for_pasuram(pasuram_number: int) -> int:
    """Verse index within pathigam (1-10), matching tidley ingest convention."""
    return ((pasuram_number - PASURAM_START) % 10) + 1


def pathigam_within_pathu(pasuram_number: int) -> int:
    """Pathigam index within the eighth patthu (1–10), matching UI 8-1-1 style."""
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


def scrape_numeric_range(start: int, end: int, output_path: Path) -> List[Dict[str, Any]]:
    """Scrape /{n}/ pages one by one; warn and continue on failure."""
    scrape_pasuram_page = getattr(load_scraper_module(SCRAPER_PATH), "scrape_pasuram_page")
    results: List[Dict[str, Any]] = []
    for pasuram_number in range(start, end + 1):
        url = f"{DRAVIDAVEDA_BASE}/{pasuram_number}/"
        print(f"Scraping {url} ({pathigam_suffix(pasuram_number)})")
        try:
            raw_rows = scrape_pasuram_page(url)
        except Exception as exc:
            print(f"  WARNING: scrape failed for {pasuram_number}: {exc}")
            continue
        if not raw_rows:
            print(f"  WARNING: no padham rows for {pasuram_number}")
            continue
        pattu_number = pattu_number_for_pasuram(pasuram_number)
        for raw in raw_rows:
            canonical = dict(raw)
            canonical["PasuramNo"] = pasuram_number
            results.append(
                normalize_scraped_row(
                    canonical,
                    prabandham=PRABANDHAM,
                    title="",
                    alzwar=ALZWAR,
                    pattu_number=pattu_number,
                )
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    pasuram_count = len({row["PasuramNumber"] for row in results})
    print(f"Saved {len(results)} padham rows for {pasuram_count} pasurams → {output_path}")
    return results


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


def inject_pasuram_only_stubs(missing: List[int]) -> List[Dict[str, Any]]:
    """One padham-less row per missing pasuram, Pasuram text from poc/pasuram.txt."""
    from poc.scripts.replace_periya_thirumozhi_patthu8_pasuram_from_txt import (
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


def load_scraped_records(args: argparse.Namespace) -> List[Dict[str, Any]]:
    scraped_json = Path(args.scraped_json)
    if not args.skip_scrape:
        raw_rows = scrape_numeric_range(args.start, args.end, scraped_json)
    else:
        raw_rows = json.loads(scraped_json.read_text(encoding="utf-8"))

    merged_rows = merge_comment_rows(raw_rows)
    records = rows_to_records(merged_rows)
    pasuram_count = len({record["PasuramNumber"] for record in records})
    print(f"Pasurams: {pasuram_count}, padham rows: {len(records)}")

    expected = set(range(args.start, args.end + 1))
    found = {record["PasuramNumber"] for record in records}
    missing = sorted(expected - found)
    if missing:
        lines = [
            f"PasuramNumber {n} ({pathigam_suffix(n)}): {DRAVIDAVEDA_BASE}/{n}/"
            for n in missing
        ]
        print("Dravidaveda padhavurai not found (pasuram-only stub used):")
        for line in lines:
            print(f"  {line}")
        MISSING_REPORT.parent.mkdir(parents=True, exist_ok=True)
        MISSING_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        records.extend(inject_pasuram_only_stubs(missing))
        print(
            f"Injected {len(missing)} pasuram-only stub row(s) from poc/pasuram.txt "
            f"→ {MISSING_REPORT}"
        )
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest Periya Thirumozhi 8th patthu (1648-1747) into POC"
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
