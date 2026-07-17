#!/usr/bin/env python3
"""Seed DivyaPrabandhamCounts from public_html/divyaprabandham_counts_seed.json.

Manual inventory of completed prabandhams (not auto-computed from pasuram tables).

  poc/.venv/bin/python poc/scripts/seed_divyaprabandham_counts.py --dry-run
  poc/.venv/bin/python poc/scripts/seed_divyaprabandham_counts.py --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config

TABLE = "DivyaPrabandhamCounts"
SEED_JSON = ROOT / "public_html" / "divyaprabandham_counts_seed.json"

CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    SortOrder INT NOT NULL,
    AlwarOrder INT NOT NULL,
    Alwar VARCHAR(255) NULL,
    AlwarSubtotal INT NULL,
    DivyaPrabhandham VARCHAR(255) NOT NULL,
    PadhamPrefix VARCHAR(255) NOT NULL,
    TotalCount INT NOT NULL,
    UpdatedAt DATETIME NOT NULL,
    PRIMARY KEY (SortOrder),
    KEY idx_counts_alwar_order (AlwarOrder)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

INSERT_SQL = f"""
INSERT INTO {TABLE}
    (SortOrder, AlwarOrder, Alwar, AlwarSubtotal, DivyaPrabhandham, PadhamPrefix, TotalCount, UpdatedAt)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed DivyaPrabandhamCounts table")
    parser.add_argument("--config", default="poc/config.ini", help="DB config path")
    parser.add_argument("--apply", action="store_true", help="Write to database")
    parser.add_argument("--dry-run", action="store_true", help="Print summary only")
    return parser.parse_args()


def load_rows() -> list[dict]:
    data = json.loads(SEED_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Seed JSON must be a list of row objects")
    return data


def main() -> None:
    args = parse_args()
    rows = load_rows()
    total = sum(int(r["total_count"]) for r in rows)
    print(f"Loaded {len(rows)} rows from {SEED_JSON.name}; footer total {total}")

    if args.dry_run and not args.apply:
        for row in rows:
            alwar = row.get("alwar") or "—"
            sub = f" ({row['alwar_subtotal']})" if row.get("alwar_subtotal") else ""
            print(f"  {row['sort_order']:2d}. [{row['alwar_order']}] {alwar}{sub} | {row['prabandham']} | {row['total_count']}")
        print("Use --apply to write to DB.")
        return

    if not args.apply:
        print("Use --apply to write to DB.")
        return

    config = load_config(args.config)
    db = config.database
    conn = mysql.connector.connect(
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        database=db.database,
    )
    cursor = conn.cursor()
    try:
        cursor.execute(CREATE_SQL)
        cursor.execute(f"DELETE FROM {TABLE}")
        updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        for row in rows:
            cursor.execute(
                INSERT_SQL,
                (
                    int(row["sort_order"]),
                    int(row["alwar_order"]),
                    row.get("alwar"),
                    row.get("alwar_subtotal"),
                    row["prabandham"],
                    row["padham_prefix"],
                    int(row["total_count"]),
                    updated_at,
                ),
            )
        conn.commit()
        print(f"Wrote {len(rows)} rows to {TABLE} at {updated_at.isoformat(sep=' ', timespec='seconds')}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
