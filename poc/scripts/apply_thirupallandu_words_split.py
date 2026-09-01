#!/usr/bin/env python3
"""Load recitation-split verses into PasuramWordsSplit (UAT Test table).

Does not write Pasuram or any other column. Skips thaniyans (PasuramNumber 0).

  poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --dry-run
  poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply
  poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
      --prabandham 'பெரியாழ்வார் திருமொழி' \
      --split-txt poc/input/periyazhwar_tm_1_1_pasuram_words_split.txt \
      --start 13 --end 22
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config

DEFAULT_PRABANDHAM = "திருப்பல்லாண்டு"
DEFAULT_SPLIT_TXT = ROOT / "poc" / "input" / "thirupallandu_pasuram_words_split.txt"
DEFAULT_CONFIG = ROOT / "poc" / "config.test.ini"
TABLE = "PasuramsArthamTableTest"


def parse_split_txt(path: Path, start: int, end: int) -> dict[int, str]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise SystemExit(f"empty split file: {path}")
    verses: dict[int, str] = {}
    for block in re.split(r"\n\s*\n", raw):
        lines = [ln.rstrip() for ln in block.splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            continue
        if not lines[0].strip().isdigit():
            raise SystemExit(f"expected verse number as first line, got: {lines[0]!r}")
        n = int(lines[0].strip())
        text = "\n".join(lines[1:]).strip()
        if not text:
            raise SystemExit(f"empty verse text for {n}")
        verses[n] = text
    expected = set(range(start, end + 1))
    if set(verses) != expected:
        raise SystemExit(f"split file keys {sorted(verses)} != {sorted(expected)}")
    return verses


def connect(config_path: Path):
    cfg = load_config(str(config_path))
    db = cfg.database
    if db.table != TABLE:
        raise SystemExit(f"refusing config table {db.table!r}; expected {TABLE}")
    return mysql.connector.connect(
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        database=db.database,
    )


def ensure_column(cur) -> None:
    cur.execute(f"SHOW COLUMNS FROM {TABLE} LIKE 'PasuramWordsSplit'")
    if cur.fetchone():
        return
    cur.execute(
        f"ALTER TABLE {TABLE} ADD COLUMN PasuramWordsSplit TEXT NULL AFTER Pasuram"
    )
    print(f"added {TABLE}.PasuramWordsSplit")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--prabandham", default=DEFAULT_PRABANDHAM)
    parser.add_argument("--split-txt", default=str(DEFAULT_SPLIT_TXT))
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=12)
    args = parser.parse_args()
    if args.dry_run == args.apply:
        raise SystemExit("pass exactly one of --dry-run or --apply")
    if args.start < 1 or args.end < args.start:
        raise SystemExit("invalid --start/--end")

    verses = parse_split_txt(Path(args.split_txt), args.start, args.end)
    conn = connect(Path(args.config))
    cur = conn.cursor()

    if args.apply:
        ensure_column(cur)
        conn.commit()

    cur.execute(f"SHOW COLUMNS FROM {TABLE} LIKE 'PasuramWordsSplit'")
    if not cur.fetchone() and args.dry_run:
        print(f"DRY RUN: would ADD COLUMN PasuramWordsSplit TEXT NULL AFTER Pasuram on {TABLE}")

    total_rows = 0
    for n in range(args.start, args.end + 1):
        cur.execute(
            f"""
            SELECT COUNT(*) FROM {TABLE}
            WHERE Prabandham = %s AND PasuramNumber = %s AND PasuramNumber <> 0
            """,
            (args.prabandham, n),
        )
        count = cur.fetchone()[0]
        text = verses[n]
        first = text.splitlines()[0]
        last = text.splitlines()[-1]
        print(f"PasuramNumber={n} rows={count} first={first!r} last={last!r}")
        if count == 0:
            raise SystemExit(f"no Test rows for {args.prabandham} #{n}")
        if args.apply:
            cur.execute(
                f"""
                UPDATE {TABLE}
                SET PasuramWordsSplit = %s
                WHERE Prabandham = %s AND PasuramNumber = %s AND PasuramNumber <> 0
                """,
                (text, args.prabandham, n),
            )
            if cur.rowcount != count:
                print(f"  warning: rowcount={cur.rowcount} expected={count}")
        total_rows += count

    if args.apply:
        conn.commit()
        print(
            f"applied PasuramWordsSplit for {args.prabandham} "
            f"{args.start}–{args.end} ({total_rows} rows). Pasuram unchanged."
        )
    else:
        print(f"DRY RUN: would UPDATE PasuramWordsSplit only, {total_rows} rows. Pasuram unchanged.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
