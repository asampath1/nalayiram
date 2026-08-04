#!/usr/bin/env python3
"""Rebuild SuggestedWords for padham autocomplete (autocomplete.php).

Sources tokens from SimilarWords, Padham/Word, and PasuramNumber so users can
find pathigam codes (1-2, 2-4 நீராட்டம்) and pasuram numbers (2048).

Default merges POC + prod pasuram tables into one shared SuggestedWords table.
Satellite projects later: run again with --table only, or a separate suggested table.

  poc/.venv/bin/python poc/scripts/refresh_suggested_words.py --dry-run
  poc/.venv/bin/python poc/scripts/refresh_suggested_words.py --apply
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

SUGGESTED_TABLE = "SuggestedWords"
BATCH_SIZE = 500

# Leading pathigam / verse codes: 1-2, 2-4, 2-8-2, 2048 (if whole segment)
CODE_PREFIX_RE = re.compile(r"^(\d+(?:-\d+)+|\d+)(?:\s+.+)?$")
PURE_NUMBER_RE = re.compile(r"^\d+$")
EMBEDDED_PATHIGAM_RE = re.compile(r"(\d+(?:-\d+)+(?:\s+[^,\d][^,]*)?)")


def normalize_for_dedup(word: str) -> str:
    if word.isascii():
        return word.lower()
    return word


def compact_hyphen_spaces(text: str) -> str:
    return re.sub(r"\s*-\s*", "-", text.strip())


def extract_tokens(similar_words: str) -> set[str]:
    tokens: set[str] = set()
    if not similar_words:
        return tokens
    for raw in similar_words.split(","):
        segment = raw.strip()
        if not segment:
            continue
        tokens.add(segment)
        compact = compact_hyphen_spaces(segment)
        if compact and compact != segment:
            tokens.add(compact)
        match = CODE_PREFIX_RE.match(segment)
        if match:
            code = match.group(1)
            if code:
                tokens.add(code)
        if PURE_NUMBER_RE.match(segment):
            tokens.add(segment)
        for match in EMBEDDED_PATHIGAM_RE.finditer(segment):
            piece = match.group(1).strip()
            if piece:
                tokens.add(piece)
                code_match = CODE_PREFIX_RE.match(piece)
                if code_match:
                    tokens.add(code_match.group(1))
    return tokens


def collect_from_table(cursor, table: str) -> set[str]:
    tokens: set[str] = set()
    cursor.execute(
        f"SELECT DISTINCT SimilarWords, Word, PasuramNumber FROM {table} "
        "WHERE SimilarWords IS NOT NULL OR Word IS NOT NULL OR PasuramNumber IS NOT NULL"
    )
    for similar, word, pasuram_number in cursor.fetchall():
        if pasuram_number is not None and int(pasuram_number) > 0:
            tokens.add(str(int(pasuram_number)))
        if word and str(word).strip():
            w = str(word).strip()
            tokens.add(w)
            tokens |= extract_tokens(w)
        if similar:
            tokens |= extract_tokens(str(similar))
    return tokens


def dedupe_tokens(tokens: set[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if not token or len(token) > 255:
            continue
        key = normalize_for_dedup(token)
        if key in seen:
            continue
        seen.add(key)
        unique.append(token)
    unique.sort(key=lambda w: (normalize_for_dedup(w), w))
    return unique


def write_suggested_words(cursor, words: list[str], truncate: bool) -> int:
    if truncate:
        cursor.execute(f"TRUNCATE TABLE {SUGGESTED_TABLE}")
    inserted = 0
    for offset in range(0, len(words), BATCH_SIZE):
        batch = words[offset : offset + BATCH_SIZE]
        placeholders = ", ".join(["(%s)"] * len(batch))
        cursor.execute(
            f"INSERT INTO {SUGGESTED_TABLE} (Word) VALUES {placeholders}",
            batch,
        )
        inserted += len(batch)
    return inserted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument(
        "--table",
        action="append",
        dest="tables",
        help="Pasuram table(s) to scan (default: POC table + PasuramsArthamTable)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    db = config.database
    tables = args.tables or [db.table, "PasuramsArthamTable"]

    conn = mysql.connector.connect(
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        database=db.database,
    )
    cursor = conn.cursor()
    all_tokens: set[str] = set()
    try:
        for table in tables:
            cursor.execute(f"SHOW TABLES LIKE %s", (table,))
            if not cursor.fetchone():
                print(f"Skip missing table: {table}")
                continue
            chunk = collect_from_table(cursor, table)
            print(f"{table}: contributed {len(chunk)} raw tokens")
            all_tokens |= chunk

        words = dedupe_tokens(all_tokens)
        numeric = sum(1 for w in words if PURE_NUMBER_RE.match(w))
        code_like = sum(1 for w in words if "-" in w and w[0].isdigit())
        print(
            f"Unique suggestions: {len(words)} "
            f"({numeric} pure numbers, {code_like} with hyphen codes)"
        )

        if args.dry_run and not args.apply:
            print("Sample:", words[:20])
            print("Dry run — no DB changes.")
            return

        if not args.apply:
            print("Use --apply to truncate and rebuild SuggestedWords.")
            return

        count = write_suggested_words(cursor, words, truncate=True)
        conn.commit()
        print(f"Wrote {count} rows to {SUGGESTED_TABLE}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
