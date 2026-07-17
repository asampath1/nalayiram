#!/usr/bin/env python3
"""Append theme aliases to SimilarWords for pasurams listed in a full-scan CSV.

Used after scan_poc_theme_from_training.py (choice B: approved pasuram list, not a range reload).
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lookupsimilarwords.config import load_db_config
from lookupsimilarwords.pasuram_themes import append_theme_aliases, normalize_text
from lookupsimilarwords.theme_registry import get_theme


def load_pasuram_numbers_from_csv(csv_path: Path) -> List[int]:
    numbers: List[int] = []
    with csv_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if "pasuram_number" not in (reader.fieldnames or []):
            raise ValueError(f"CSV must have pasuram_number column: {csv_path}")
        for row in reader:
            raw = (row.get("pasuram_number") or "").strip()
            if raw:
                numbers.append(int(raw))
    return numbers


def fetch_rows_for_pasurams(
    db_config: Dict[str, Any],
    pasuram_numbers: List[int],
) -> List[Dict[str, Any]]:
    import mysql.connector

    if not pasuram_numbers:
        return []

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
    placeholders = ",".join(["%s"] * len(pasuram_numbers))
    query = (
        f"SELECT Sno, PasuramNumber, PadhamNumber, SimilarWords "
        f"FROM `{table}` "
        f"WHERE PasuramNumber IN ({placeholders}) "
        f"ORDER BY PasuramNumber, PadhamNumber"
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, pasuram_numbers)
    rows = list(cursor.fetchall())
    cursor.close()
    conn.close()
    return rows


def apply_aliases(
    db_config: Dict[str, Any],
    pasuram_numbers: List[int],
    aliases: List[str],
    dry_run: bool,
) -> Dict[str, Any]:
    import mysql.connector

    rows = fetch_rows_for_pasurams(db_config, pasuram_numbers)
    found_pasurams: Set[int] = {int(r["PasuramNumber"]) for r in rows}

    updates: List[Dict[str, Any]] = []
    for row in rows:
        old_sw = row.get("SimilarWords") or ""
        new_sw = append_theme_aliases(old_sw, aliases)
        if normalize_text(new_sw) != normalize_text(old_sw):
            updates.append(
                {
                    "sno": row["Sno"],
                    "pasuram_number": row["PasuramNumber"],
                    "padham_number": row.get("PadhamNumber"),
                    "old_similar_words": old_sw,
                    "new_similar_words": new_sw,
                }
            )

    missing = sorted(set(pasuram_numbers) - found_pasurams)

    if dry_run:
        by_pasuram: Dict[int, int] = {}
        for u in updates:
            pn = int(u["pasuram_number"])
            by_pasuram[pn] = by_pasuram.get(pn, 0) + 1
        return {
            "dry_run": True,
            "pasurams_requested": len(pasuram_numbers),
            "pasurams_with_rows": len(found_pasurams),
            "rows_fetched": len(rows),
            "rows_would_update": len(updates),
            "pasurams_would_update": len(by_pasuram),
            "missing_pasurams": missing,
            "sample_updates": updates[:5],
        }

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
    updated = 0
    for item in updates:
        cursor.execute(
            f"UPDATE `{table}` SET SimilarWords = %s WHERE Sno = %s",
            (item["new_similar_words"], item["sno"]),
        )
        updated += 1
    conn.commit()
    cursor.close()
    conn.close()

    return {
        "dry_run": False,
        "pasurams_requested": len(pasuram_numbers),
        "pasurams_with_rows": len(found_pasurams),
        "rows_fetched": len(rows),
        "rows_updated": updated,
        "missing_pasurams": missing,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append theme aliases to SimilarWords for pasurams in a scan CSV"
    )
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--theme", required=True, help="e.g. narasimha, garudan")
    parser.add_argument(
        "--csv",
        default=None,
        help="Scan CSV (default: lookupsimilarwords/reviews/{theme}_poc_full_scan.csv)",
    )
    parser.add_argument(
        "--exclude",
        type=int,
        nargs="*",
        default=[],
        help="Pasuram numbers to skip (e.g. 2244 for garudan FP)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write updates to DB (default: dry-run only)",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    theme_id = args.theme
    theme = get_theme(theme_id)
    aliases = theme.get("aliases", [])
    if not aliases:
        raise ValueError(f"No aliases for theme {theme_id!r}")

    csv_path = Path(args.csv) if args.csv else Path(f"lookupsimilarwords/reviews/{theme_id}_poc_full_scan.csv")
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Scan CSV not found: {csv_path}. Run scan_poc_theme_from_training.py --theme {theme_id} first."
        )

    pasuram_numbers = load_pasuram_numbers_from_csv(csv_path)
    exclude = set(args.exclude or [])
    if exclude:
        pasuram_numbers = [p for p in pasuram_numbers if p not in exclude]

    db_config = load_db_config(Path(args.config))
    print(f"Theme: {theme_id}")
    print(f"Table: {db_config['table']}")
    print(f"CSV: {csv_path} ({len(pasuram_numbers)} pasurams)")
    if exclude:
        print(f"Excluded: {sorted(exclude)}")
    print(f"Aliases ({len(aliases)}): {', '.join(aliases[:6])}{'...' if len(aliases) > 6 else ''}")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")

    summary = apply_aliases(db_config, pasuram_numbers, aliases, dry_run=dry_run)

    if dry_run:
        print(f"Rows fetched: {summary['rows_fetched']}")
        print(f"Rows that would change: {summary['rows_would_update']}")
        print(f"Pasurams with at least one change: {summary['pasurams_would_update']}")
        if summary.get("missing_pasurams"):
            print(f"WARNING: no rows for pasurams: {summary['missing_pasurams']}")
        for sample in summary.get("sample_updates", []):
            print(
                f"  sample pasuram {sample['pasuram_number']} padham {sample['padham_number']}: "
                f"+{len(sample['new_similar_words']) - len(sample['old_similar_words'])} chars"
            )
        print("Re-run with --apply to write to the database.")
    else:
        print(f"Rows updated: {summary['rows_updated']}")
        if summary.get("missing_pasurams"):
            print(f"WARNING: no rows for pasurams: {summary['missing_pasurams']}")


if __name__ == "__main__":
    main()
