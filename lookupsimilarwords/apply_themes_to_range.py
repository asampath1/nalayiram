#!/usr/bin/env python3
"""Apply all theme detectors to SimilarWords for pasurams in a number range."""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lookupsimilarwords.config import load_db_config
from lookupsimilarwords.pasuram_themes import (
    apply_all_themes_to_records,
    load_detectors_for_themes,
    normalize_text,
)
from lookupsimilarwords.theme_registry import resolve_theme_ids

EARLY_PRABANDHAM_RANGES: Tuple[Tuple[int, int], ...] = (
    (1, 12),
    (152, 161),
    (182, 201),
    (463, 503),
    (917, 947),
)
REVIEWS_DIR = Path(__file__).resolve().parent / "reviews"


def fetch_rows_for_range(
    db_config: Dict[str, Any],
    start: int,
    end: int,
) -> List[Dict[str, Any]]:
    import mysql.connector

    ssl_options = {} if not db_config.get("use_ssl") else {"ssl_disabled": False}
    conn = mysql.connector.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        **ssl_options,
    )
    table = db_config["table"]
    query = (
        f"SELECT Sno, PasuramNumber, PattuNumber, PadhamNumber, Padham, Meaning, "
        f"Prabandham, SimilarWords "
        f"FROM `{table}` "
        f"WHERE PasuramNumber >= %s AND PasuramNumber <= %s "
        f"AND Padham IS NOT NULL AND TRIM(Padham) != '' "
        f"AND UPPER(TRIM(Padham)) != 'NOTE' "
        f"ORDER BY PasuramNumber, PadhamNumber"
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (start, end))
    rows = list(cursor.fetchall())
    cursor.close()
    conn.close()
    return rows


def _themes_added(old_sw: str, new_sw: str) -> List[str]:
    old_parts = {normalize_text(p).lower() for p in old_sw.split(",") if normalize_text(p)}
    new_parts = [normalize_text(p) for p in new_sw.split(",") if normalize_text(p)]
    added: List[str] = []
    for part in new_parts:
        if part.lower() not in old_parts:
            added.append(part)
    return added


def apply_range(
    db_config: Dict[str, Any],
    start: int,
    end: int,
    theme_ids: Sequence[str],
    *,
    dry_run: bool,
) -> Dict[str, Any]:
    rows = fetch_rows_for_range(db_config, start, end)
    if not rows:
        return {
            "start": start,
            "end": end,
            "rows_fetched": 0,
            "rows_updated": 0,
            "pasuram_summaries": [],
        }

    detectors = load_detectors_for_themes(list(theme_ids))
    updated_records = apply_all_themes_to_records(rows, detectors)

    updates: List[Dict[str, Any]] = []
    pasuram_meta: Dict[int, Dict[str, Any]] = defaultdict(
        lambda: {"themes_added": set(), "rows_updated": 0, "prabandham": ""}
    )

    for old_row, new_row in zip(rows, updated_records):
        old_sw = old_row.get("SimilarWords") or ""
        new_sw = new_row.get("SimilarWords") or ""
        if normalize_text(new_sw) == normalize_text(old_sw):
            continue

        pasuram_number = int(old_row["PasuramNumber"])
        added = _themes_added(old_sw, new_sw)
        pasuram_meta[pasuram_number]["rows_updated"] += 1
        pasuram_meta[pasuram_number]["prabandham"] = old_row.get("Prabandham") or ""
        pasuram_meta[pasuram_number]["themes_added"].update(added)

        updates.append(
            {
                "sno": old_row["Sno"],
                "pasuram_number": pasuram_number,
                "padham_number": old_row.get("PadhamNumber"),
                "old_similar_words": old_sw,
                "new_similar_words": new_sw,
                "added_aliases": ", ".join(added),
            }
        )

    pasuram_summaries = [
        {
            "pasuram_number": pn,
            "prabandham": meta["prabandham"],
            "themes_added": ", ".join(sorted(meta["themes_added"])),
            "rows_updated": meta["rows_updated"],
        }
        for pn, meta in sorted(pasuram_meta.items())
    ]

    if not dry_run and updates:
        import mysql.connector

        ssl_options = {} if not db_config.get("use_ssl") else {"ssl_disabled": False}
        conn = mysql.connector.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            **ssl_options,
        )
        table = db_config["table"]
        cursor = conn.cursor()
        for item in updates:
            cursor.execute(
                f"UPDATE `{table}` SET SimilarWords = %s WHERE Sno = %s",
                (item["new_similar_words"], item["sno"]),
            )
        conn.commit()
        cursor.close()
        conn.close()

    return {
        "start": start,
        "end": end,
        "rows_fetched": len(rows),
        "rows_updated": len(updates),
        "pasurams_updated": len(pasuram_summaries),
        "pasuram_summaries": pasuram_summaries,
        "updates": updates,
    }


def write_review_csv(path: Path, summaries: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["PasuramNumber", "Prabandham", "themes_added", "rows_updated"],
        )
        writer.writeheader()
        for item in summaries:
            writer.writerow(
                {
                    "PasuramNumber": item["pasuram_number"],
                    "Prabandham": item["prabandham"],
                    "themes_added": item["themes_added"],
                    "rows_updated": item["rows_updated"],
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply theme detectors to SimilarWords for a pasuram number range"
    )
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--start", type=int, help="First pasuram number (inclusive)")
    parser.add_argument("--end", type=int, help="Last pasuram number (inclusive)")
    parser.add_argument(
        "--early-prabandhams",
        action="store_true",
        help="Apply to early blocks: 1-12, 152-161, 182-201, 463-503, 917-947",
    )
    parser.add_argument(
        "--themes",
        default="all",
        help="Comma-separated theme ids or 'all' (default: all)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write updates to DB (default: dry-run only)",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Review CSV path (default: lookupsimilarwords/reviews/early_prabandhams_{start}_{end}_theme_apply.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = not args.apply

    if args.early_prabandhams:
        ranges = EARLY_PRABANDHAM_RANGES
    elif args.start is not None and args.end is not None:
        ranges = ((args.start, args.end),)
    else:
        raise SystemExit("Provide --start/--end or --early-prabandhams")

    theme_ids = resolve_theme_ids(args.themes)
    db_config = load_db_config(Path(args.config))

    print(f"Table: {db_config['table']}")
    print(f"Themes: {', '.join(theme_ids)}")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")
    print(f"Ranges: {', '.join(f'{a}-{b}' for a, b in ranges)}")

    total_fetched = 0
    total_updated = 0
    all_summaries: List[Dict[str, Any]] = []

    for start, end in ranges:
        result = apply_range(db_config, start, end, theme_ids, dry_run=dry_run)
        total_fetched += result["rows_fetched"]
        total_updated += result["rows_updated"]
        all_summaries.extend(result["pasuram_summaries"])

        print(
            f"  {start}-{end}: fetched {result['rows_fetched']} rows, "
            f"{'would update' if dry_run else 'updated'} {result['rows_updated']} rows "
            f"across {result['pasurams_updated']} pasurams"
        )

        csv_path = (
            Path(args.csv)
            if args.csv
            else REVIEWS_DIR / f"early_prabandhams_{start}_{end}_theme_apply.csv"
        )
        write_review_csv(csv_path, result["pasuram_summaries"])
        print(f"  Wrote review CSV: {csv_path}")

    print(
        f"Total: fetched {total_fetched} rows, "
        f"{'would update' if dry_run else 'updated'} {total_updated} rows "
        f"across {len(all_summaries)} pasurams"
    )
    if dry_run:
        print("Re-run with --apply to write to the database.")


if __name__ == "__main__":
    main()
