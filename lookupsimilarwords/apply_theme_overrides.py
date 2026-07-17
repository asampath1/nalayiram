#!/usr/bin/env python3
"""Apply manual pasuram-level theme tags from theme_pasuram_overrides.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lookupsimilarwords.config import load_db_config
from lookupsimilarwords.pasuram_themes import append_theme_aliases, normalize_text
from lookupsimilarwords.theme_registry import get_theme

DEFAULT_OVERRIDES = Path(__file__).resolve().parent / "theme_pasuram_overrides.json"


def load_overrides(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def fetch_rows_for_pasurams(db_config: Dict[str, Any], pasuram_numbers: List[int]) -> List[Dict[str, Any]]:
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
        f"FROM `{table}` WHERE PasuramNumber IN ({placeholders}) "
        f"ORDER BY PasuramNumber, PadhamNumber"
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, pasuram_numbers)
    rows = list(cursor.fetchall())
    cursor.close()
    conn.close()
    return rows


def apply_overrides(
    db_config: Dict[str, Any],
    overrides: Dict[str, List[Dict[str, Any]]],
    *,
    dry_run: bool,
) -> int:
    import mysql.connector

    updates: List[Dict[str, Any]] = []
    for theme_id, entries in overrides.items():
        theme = get_theme(theme_id)
        aliases = theme.get("aliases", [])
        if not aliases:
            raise ValueError(f"No aliases configured for theme {theme_id!r}")

        for entry in entries:
            pasuram_number = int(entry["pasuram_number"])
            rows = fetch_rows_for_pasurams(db_config, [pasuram_number])
            for row in rows:
                old_sw = row.get("SimilarWords") or ""
                new_sw = append_theme_aliases(old_sw, aliases)
                if normalize_text(new_sw) == normalize_text(old_sw):
                    continue
                updates.append(
                    {
                        "sno": row["Sno"],
                        "pasuram_number": pasuram_number,
                        "theme_id": theme_id,
                        "note": entry.get("note", ""),
                        "new_similar_words": new_sw,
                    }
                )

    if dry_run:
        for item in updates:
            print(
                f"DRY RUN: PasuramNumber={item['pasuram_number']} theme={item['theme_id']} "
                f"Sno={item['sno']}"
            )
            if item["note"]:
                print(f"  note: {item['note']}")
        print(f"Would update {len(updates)} rows")
        return len(updates)

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
        print(
            f"Updated PasuramNumber={item['pasuram_number']} theme={item['theme_id']} Sno={item['sno']}"
        )
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Updated {len(updates)} rows")
    return len(updates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply manual theme tags from overrides JSON")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--overrides", default=str(DEFAULT_OVERRIDES))
    parser.add_argument("--apply", action="store_true", help="Write to DB (default: dry-run)")
    args = parser.parse_args()

    overrides = load_overrides(Path(args.overrides))
    db_config = load_db_config(Path(args.config))
    print(f"Table: {db_config['table']}")
    print(f"Overrides: {args.overrides}")
    apply_overrides(db_config, overrides, dry_run=not args.apply)


if __name__ == "__main__":
    main()
