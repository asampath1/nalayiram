"""Legacy bulk extractor: all padhams with mined SimilarWords aliases.

Prefer extract_concept_lookup.py for themed concepts (e.g. மகாபாரதம்).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import mysql.connector

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from lookupsimilarwords.config import load_db_config


IGNORE_PATTERNS = [
    re.compile(r"சாற்றுமுறை", re.IGNORECASE),
    re.compile(r"satrumurai", re.IGNORECASE),
]


def normalize_token(token: str) -> str:
    token = str(token or "").strip()
    token = re.sub(r"^\s+|\s+$", "", token)
    token = re.sub(r"[\s\u00A0]+", " ", token)
    token = token.strip(",; ")
    return token


def split_similar_words(similar_words: str) -> List[str]:
    if not similar_words:
        return []

    tokens = re.split(r"[,;]+", similar_words)
    stripped = [normalize_token(token) for token in tokens]
    return [token for token in stripped if token]


def should_ignore_token(token: str, ignore_patterns: List[re.Pattern]) -> bool:
    for pattern in ignore_patterns:
        if pattern.search(token):
            return True
    return False


def row_tokens_to_keep(similar_words: str, word: str, title: str) -> List[str]:
    tokens = split_similar_words(similar_words)
    exclusion_values = set(split_similar_words(word) + split_similar_words(title))
    kept: List[str] = []

    for token in tokens:
        normalized = normalize_token(token)
        if not normalized:
            continue

        if should_ignore_token(normalized, IGNORE_PATTERNS):
            continue

        if re.search(r"\d", normalized):
            continue

        if normalized in exclusion_values:
            continue

        exclusion_lower = {val.lower() for val in exclusion_values}
        if normalized.lower() in exclusion_lower:
            continue

        kept.append(normalized)

    return list(dict.fromkeys(kept))


def build_lookup_map(rows: Iterable[Dict[str, Optional[str]]]) -> Dict[str, List[str]]:
    lookup: Dict[str, List[str]] = {}

    for row in rows:
        padham = normalize_token(row.get("Padham", ""))
        if not padham:
            continue

        similar_words = row.get("SimilarWords", "") or ""
        word = row.get("Word", "") or ""
        title = row.get("Title", "") or ""

        alias_tokens = row_tokens_to_keep(similar_words, word, title)
        if not alias_tokens:
            continue

        existing = lookup.setdefault(padham, [])
        for token in alias_tokens:
            if token not in existing:
                existing.append(token)

    return lookup


def query_poc_table(db_config: Dict[str, str], batch_size: int = 5000) -> Iterable[Dict[str, Optional[str]]]:
    ssl_options = {} if not db_config.get("use_ssl") else {"ssl_disabled": False}
    connection = mysql.connector.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        **ssl_options,
    )

    cursor = connection.cursor(dictionary=True)
    table = db_config["table"]
    query = (
        f"SELECT Padham, SimilarWords, Word, Title "
        f"FROM `{table}` "
        f"WHERE SimilarWords IS NOT NULL AND SimilarWords != ''"
    )
    cursor.execute(query)
    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        for row in batch:
            yield row

    cursor.close()
    connection.close()


def save_lookup(lookup: Dict[str, List[str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(lookup, fh, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = ArgumentParser(description="Build a SimilarWords lookup JSON from PasuramsArthamTablePOC")
    parser.add_argument(
        "--config",
        default="poc/config.ini",
        help="Path to the INI config file containing DB connection info",
    )
    parser.add_argument(
        "--output",
        default="lookupsimilarwords/similar_word_lookup.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Number of rows to fetch from the DB per batch",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    db_config = load_db_config(config_path)
    rows = query_poc_table(db_config, batch_size=args.batch_size)
    lookup = build_lookup_map(rows)
    save_lookup(lookup, Path(args.output))
    print(f"Wrote {len(lookup)} lookup entries to {args.output}")


if __name__ == "__main__":
    main()
