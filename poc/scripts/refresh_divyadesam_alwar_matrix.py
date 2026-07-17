#!/usr/bin/env python3
"""Refresh precomputed DivyaDesam × Alwar matrix counts.

Each cell stores COUNT(DISTINCT PasuramNumber) for that (DivyaDesam, Alzwar)
pair — so single-pasuram prabandhams (e.g. 2672–2674) count as 1.

Table: DivyaDesamAlwarMatrix (Environment = poc | test | prod)

Run after ingesting new prabandhams:
  poc/.venv/bin/python poc/scripts/refresh_divyadesam_alwar_matrix.py --env all --apply
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config

MATRIX_TABLE = "DivyaDesamAlwarMatrix"
DIVYADESAM_TABLE = "DivyaDesamTable"
LEGACY_MATRIX_TABLE = "DivyaDesamAlwarMatrixPOC"

ENV_CONFIGS: dict[str, str] = {
    "poc": "poc/config.ini",
    "test": "poc/config.test.ini",
    "prod": "poc/config.prod.ini",
}

CREATE_MATRIX_SQL = f"""
CREATE TABLE IF NOT EXISTS {MATRIX_TABLE} (
    Environment VARCHAR(10) NOT NULL,
    DivyaDesam VARCHAR(512) NOT NULL,
    Alzwar VARCHAR(255) NOT NULL,
    PasuramCount INT NOT NULL,
    RefreshedAt DATETIME NOT NULL,
    PRIMARY KEY (Environment, DivyaDesam(191), Alzwar(191)),
    KEY idx_matrix_env_alwar (Environment, Alzwar(191)),
    KEY idx_matrix_env_divyadesam (Environment, DivyaDesam(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

AGGREGATE_SQL = """
SELECT
    d.DivyaDesam,
    p.Alzwar,
    COUNT(DISTINCT p.PasuramNumber) AS pasuram_count
FROM {pasuram_table} p
INNER JOIN {divyadesam_table} d
    ON p.PasuramNumber = d.PasuramNumber
WHERE p.Alzwar IS NOT NULL AND TRIM(p.Alzwar) <> ''
  AND d.DivyaDesam IS NOT NULL AND TRIM(d.DivyaDesam) <> ''
GROUP BY d.DivyaDesam, p.Alzwar
ORDER BY d.DivyaDesam, p.Alzwar
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh DivyaDesam × Alwar matrix cache")
    parser.add_argument(
        "--env",
        choices=["poc", "test", "prod", "all"],
        default="poc",
        help="Environment to refresh (default: poc; use all for poc+test+prod)",
    )
    parser.add_argument("--config", default=None, help="Override config path (implies --env poc if set alone)")
    parser.add_argument("--apply", action="store_true", help="Write refreshed counts to DB")
    parser.add_argument("--dry-run", action="store_true", help="Compute only; no DB write")
    return parser.parse_args()


def connect(config_path: Path):
    config = load_config(str(config_path))
    db = config.database
    conn = mysql.connector.connect(
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        database=db.database,
    )
    return conn, db


def fetch_matrix_rows(cursor, pasuram_table: str) -> list[tuple[str, str, int]]:
    started = time.time()
    sql = AGGREGATE_SQL.format(pasuram_table=pasuram_table, divyadesam_table=DIVYADESAM_TABLE)
    cursor.execute(sql)
    rows = [(dd, alwar, int(count)) for dd, alwar, count in cursor.fetchall()]
    elapsed = time.time() - started
    print(f"Aggregated {len(rows)} cells from {pasuram_table} in {elapsed:.2f}s")
    return rows


def migrate_legacy_poc_table(cursor) -> None:
    cursor.execute(f"SHOW TABLES LIKE '{LEGACY_MATRIX_TABLE}'")
    if not cursor.fetchone():
        return
    cursor.execute(f"SELECT COUNT(*) FROM {MATRIX_TABLE} WHERE Environment = 'poc'")
    if cursor.fetchone()[0] > 0:
        return
    cursor.execute(
        f"""
        INSERT INTO {MATRIX_TABLE} (Environment, DivyaDesam, Alzwar, PasuramCount, RefreshedAt)
        SELECT 'poc', DivyaDesam, Alzwar, PasuramCount, RefreshedAt
        FROM {LEGACY_MATRIX_TABLE}
        """
    )
    print(f"Migrated rows from legacy {LEGACY_MATRIX_TABLE} into {MATRIX_TABLE} (poc)")


def refresh_matrix(
    config_path: Path | str | None = None,
    *,
    env: str = "poc",
    dry_run: bool = False,
) -> int:
    """Rebuild DivyaDesamAlwarMatrix for one environment. Returns cells written."""
    if config_path is None:
        config_path = ENV_CONFIGS[env]
    config_path = Path(config_path)
    conn, db = connect(config_path)
    cursor = conn.cursor()

    pasuram_table = db.table
    rows = fetch_matrix_rows(cursor, pasuram_table)
    if not rows:
        print(f"No matrix cells found for {env} — check {pasuram_table} and {DIVYADESAM_TABLE}.")
        conn.close()
        return 0

    total_pasurams_in_cells = sum(count for _dd, _alwar, count in rows)
    print(f"[{env}] Sum of cell counts (matrix footer total): {total_pasurams_in_cells}")

    if dry_run:
        conn.close()
        return len(rows)

    cursor.execute(CREATE_MATRIX_SQL)
    migrate_legacy_poc_table(cursor)

    refreshed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    cursor.execute(
        f"DELETE FROM {MATRIX_TABLE} WHERE Environment = %s",
        (env,),
    )

    insert_sql = f"""
    INSERT INTO {MATRIX_TABLE} (Environment, DivyaDesam, Alzwar, PasuramCount, RefreshedAt)
    VALUES (%s, %s, %s, %s, %s)
    """
    for divyadesam, alwar, count in rows:
        cursor.execute(insert_sql, (env, divyadesam, alwar, count, refreshed_at))
    conn.commit()

    print(
        f"[{env}] Wrote {len(rows)} rows to {MATRIX_TABLE} "
        f"at {refreshed_at.isoformat(sep=' ', timespec='seconds')}"
    )
    conn.close()
    return len(rows)


def main() -> None:
    args = parse_args()
    envs = list(ENV_CONFIGS) if args.env == "all" else [args.env]

    if args.config and args.env == "poc" and len(envs) == 1:
        config_path = Path(args.config)
        if args.dry_run and not args.apply:
            refresh_matrix(config_path, env="poc", dry_run=True)
            return
        if not args.apply:
            refresh_matrix(config_path, env="poc", dry_run=True)
            print(f"Use --apply to write {MATRIX_TABLE}.")
            return
        refresh_matrix(config_path, env="poc", dry_run=False)
        return

    total = 0
    for env in envs:
        if args.dry_run and not args.apply:
            total += refresh_matrix(env=env, dry_run=True)
            continue
        if not args.apply:
            refresh_matrix(env=env, dry_run=True)
            print(f"Use --apply to write {MATRIX_TABLE}.")
            return
        total += refresh_matrix(env=env, dry_run=False)

    if args.apply and len(envs) > 1:
        print(f"Refreshed {total} total cells across {len(envs)} environments.")


if __name__ == "__main__":
    main()
