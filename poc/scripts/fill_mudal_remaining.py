#!/usr/bin/env python3
"""Fill Mudhal Thiruvandhathi remaining Excel with tidley titles → themes → POC JSON."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from poc.fill_workbook import excel_to_records, transliterate_records_from_config
from poc.generate_similar_words import finalize_records
from poc.json_exporter import export_to_json
from poc.title_scrapers.mudal_tidley import scrape_mudal_titles, titles_by_pasuram_number

DEFAULT_INPUT = ROOT / "Mudhalthiruvandhathi-remaining.xlsx"
DEFAULT_JSON = ROOT / "poc/output/mudal_thiruvandhathi_remaining_poc.json"
DEFAULT_TITLES_JSON = ROOT / "poc/output/mudal_remaining_titles_tidley.json"
DEFAULT_REVIEW_CSV = ROOT / "lookupsimilarwords/reviews/mudal_remaining_titles_tidley.csv"


def apply_titles_to_records(
    records: list[dict],
    titles: dict[int, str],
) -> tuple[list[dict], list[int]]:
    missing_pasurams: list[int] = []
    updated: list[dict] = []
    for record in records:
        pasuram_number = record.get("PasuramNumber")
        title = titles.get(pasuram_number, "")
        if not title:
            missing_pasurams.append(pasuram_number)
        updated.append({**record, "Title": title})
    return updated, sorted(set(missing_pasurams))


def write_title_review_csv(records: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["pattu_number", "pasuram_number", "url", "title_preview"],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "pattu_number": record.pattu_number,
                    "pasuram_number": record.pasuram_number,
                    "url": record.url,
                    "title_preview": record.title[:120].replace("\n", " "),
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--config", default=str(ROOT / "poc/config.ini"))
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--titles-json", default=str(DEFAULT_TITLES_JSON))
    parser.add_argument("--review-csv", default=str(DEFAULT_REVIEW_CSV))
    parser.add_argument("--pattu-start", type=int, default=36)
    parser.add_argument("--pattu-end", type=int, default=100)
    parser.add_argument("--skip-scrape", action="store_true", help="Reuse --titles-json")
    parser.add_argument("--themes", default="all")
    parser.add_argument("--no-themes", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    df = pd.read_excel(input_path)
    records = excel_to_records(df)

    if args.skip_scrape:
        title_rows = json.loads(Path(args.titles_json).read_text(encoding="utf-8"))
        titles = {row["pasuram_number"]: row["title"] for row in title_rows}
    else:
        scraped = scrape_mudal_titles(args.pattu_start, args.pattu_end)
        Path(args.titles_json).write_text(
            json.dumps([r.__dict__ for r in scraped], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        write_title_review_csv(scraped, Path(args.review_csv))
        titles = titles_by_pasuram_number(scraped)

    records, missing = apply_titles_to_records(records, titles)
    if missing:
        print(f"WARNING: missing tidley titles for pasurams: {missing}")

    records = transliterate_records_from_config(records, Path(args.config))

    from lookupsimilarwords.theme_registry import resolve_theme_ids

    theme_ids = None if args.themes == "all" else resolve_theme_ids(args.themes)
    records = finalize_records(
        records,
        apply_themes=not args.no_themes,
        themes=theme_ids,
    )

    export_to_json(records, Path(args.output_json))
    themed = sum(1 for r in records if len((r.get("SimilarWords") or "").split(",")) > 4)
    print(f"Wrote {len(records)} records to {args.output_json}")
    print(f"Rows with theme tags: {themed}")
    if missing:
        print("Provide manual titles for:", missing)


if __name__ == "__main__":
    main()
