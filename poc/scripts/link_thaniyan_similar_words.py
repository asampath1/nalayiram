#!/usr/bin/env python3
"""Append parent prabandham names to thaniyan SimilarWords for prabandham-wide search."""
from __future__ import annotations

import argparse
import configparser
from pathlib import Path

import mysql.connector

# Parent prabandham (Tamil, English) → thaniyan Prabandham prefix in DB.
THANIYAN_PARENTS: list[tuple[str, str, str]] = [
    ("சிறிய திருமடல்", "Siriya Thirumadal", "சிறிய திருமடல்"),
    ("பெரிய திருமடல்", "Periya Thirumadal", "பெரிய திருமடல்"),
    ("திருவெழுகூற்றிருக்கை", "Thiruvozhukootrirukkai", "திருவெழுகூற்றிருக்கை"),
    ("திரு நெடும் தாண்டகம்", "Thiru Nedum Thandagam", "திரு நெடும் தாண்டகம்"),
    ("திருவிருத்தம்", "Thiruvirutham", "திருவிருத்தம்"),
]


def load_db_config(config_path: Path) -> dict:
    cfg = configparser.ConfigParser()
    cfg.read(config_path)
    section = cfg["db"]
    return {
        "host": section["host"],
        "port": int(section.get("port", 3306)),
        "user": section["user"],
        "password": section["password"],
        "database": section["database"],
    }


def link_thaniyan_similar_words(config_path: Path, dry_run: bool = False) -> int:
    db_cfg = load_db_config(config_path)
    table = configparser.ConfigParser()
    table.read(config_path)
    table_name = table["db"]["table"]

    conn = mysql.connector.connect(**db_cfg)
    cursor = conn.cursor()
    updated = 0

    for tamil, english, prefix in THANIYAN_PARENTS:
        like_prefix = f"{prefix}%"
        cursor.execute(
            f"""
            SELECT Sno, Prabandham, SimilarWords
            FROM {table_name}
            WHERE Prabandham LIKE %s
              AND Prabandham LIKE %s
              AND SimilarWords NOT LIKE %s
            """,
            (like_prefix, "%தனியன%", f"%{english}%"),
        )
        rows = cursor.fetchall()
        aliases = f",{tamil},{english}"
        for sno, prabandham, similar in rows:
            new_similar = f"{similar or ''}{aliases}"
            if dry_run:
                print(f"DRY RUN Sno={sno} {prabandham!r} += {aliases}")
            else:
                cursor.execute(
                    f"UPDATE {table_name} SET SimilarWords = %s WHERE Sno = %s",
                    (new_similar, sno),
                )
            updated += 1

    if not dry_run:
        conn.commit()
    cursor.close()
    conn.close()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent.parent / "config.ini"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    count = link_thaniyan_similar_words(Path(args.config), dry_run=args.dry_run)
    print(f"{'Would update' if args.dry_run else 'Updated'} {count} thaniyan row(s).")


if __name__ == "__main__":
    main()
