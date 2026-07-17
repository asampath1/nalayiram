#!/usr/bin/env python3
"""Extract concept-tagged padhams from the DB for vetting and slim automation lookup.

Queries rows where SimilarWords contains a given concept (e.g. மகாபாரதம்), outputs
full Padham–Meaning records plus a padham_lookup map with fixed aliases only.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import mysql.connector

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from lookupsimilarwords.config import load_db_config


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", str(text or ""))
    text = re.sub(r"[\s\u00A0]+", " ", text).strip()
    return text


def normalize_padham(padham: str) -> str:
    return normalize_text(padham)


def query_concept_rows(
    db_config: Dict[str, Any],
    concept: str | List[str],
    batch_size: int = 5000,
) -> List[Dict[str, Any]]:
    if isinstance(concept, str):
        concepts = [concept]
    else:
        concepts = [normalize_text(c) for c in concept if normalize_text(c)]
    if not concepts:
        return []

    ssl_options = {} if not db_config.get("use_ssl") else {"ssl_disabled": False}
    connection = mysql.connector.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        **ssl_options,
    )

    table = db_config["table"]
    like_clauses = " OR ".join(["SimilarWords LIKE %s"] * len(concepts))
    query = (
        f"SELECT PasuramNumber, PattuNumber, PadhamNumber, Padham, Meaning, Word, "
        f"Prabandham, Title, SimilarWords "
        f"FROM `{table}` "
        f"WHERE ({like_clauses}) "
        f"AND Padham IS NOT NULL AND TRIM(Padham) != '' "
        f"AND UPPER(TRIM(Padham)) != 'NOTE' "
        f"ORDER BY PasuramNumber, PattuNumber, PadhamNumber"
    )
    patterns = [f"%{c}%" for c in concepts]

    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, patterns)

    rows: List[Dict[str, Any]] = []
    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        rows.extend(batch)

    cursor.close()
    connection.close()
    return rows


def build_record(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    padham = normalize_padham(row.get("Padham", ""))
    if not padham or padham.upper() == "NOTE":
        return None

    meaning = normalize_text(row.get("Meaning", ""))
    return {
        "PasuramNumber": row.get("PasuramNumber"),
        "PattuNumber": row.get("PattuNumber"),
        "PadhamNumber": row.get("PadhamNumber"),
        "Padham": padham,
        "Meaning": meaning,
        "Word": normalize_text(row.get("Word", "")),
        "Prabandham": normalize_text(row.get("Prabandham", "")),
        "Title": normalize_text(row.get("Title", "")),
    }


def build_padham_lookup(
    records: List[Dict[str, Any]],
    aliases: List[str],
) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}

    for record in records:
        padham = record["Padham"]
        entry = lookup.setdefault(
            padham,
            {
                "aliases": list(aliases),
                "meanings": [],
                "pasuram_numbers": [],
            },
        )

        meaning = record.get("Meaning", "")
        if meaning and meaning not in entry["meanings"]:
            entry["meanings"].append(meaning)

        pasuram_num = record.get("PasuramNumber")
        if pasuram_num is not None and pasuram_num not in entry["pasuram_numbers"]:
            entry["pasuram_numbers"].append(pasuram_num)

    for entry in lookup.values():
        entry["pasuram_numbers"].sort(
            key=lambda x: (isinstance(x, str), x),
        )

    return dict(sorted(lookup.items(), key=lambda item: item[0]))


def build_output(
    raw_rows: List[Dict[str, Any]],
    concept: str,
    concept_english: str,
    source_table: str,
) -> Dict[str, Any]:
    aliases = [concept]
    if concept_english and concept_english not in aliases:
        aliases.append(concept_english)

    records: List[Dict[str, Any]] = []
    for row in raw_rows:
        record = build_record(row)
        if record:
            records.append(record)

    padham_lookup = build_padham_lookup(records, aliases)

    return {
        "concept": concept,
        "aliases": aliases,
        "source_table": source_table,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "distinct_padham_count": len(padham_lookup),
        "records": records,
        "padham_lookup": padham_lookup,
    }


def save_json(data: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def save_csv(records: List[Dict[str, Any]], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "PasuramNumber",
        "PattuNumber",
        "PadhamNumber",
        "Padham",
        "Meaning",
        "Word",
        "Prabandham",
        "Title",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def print_summary(data: Dict[str, Any]) -> None:
    print(f"Concept: {data['concept']}")
    print(f"Source table: {data['source_table']}")
    print(f"Records: {data['record_count']}")
    print(f"Distinct padhams: {data['distinct_padham_count']}")

    if not data["records"]:
        print("No rows matched. Check concept spelling and table contents.")
        return

    counts = Counter(r["Padham"] for r in data["records"])
    print("\nTop padhams by occurrence:")
    for padham, count in counts.most_common(15):
        print(f"  {count:4d}  {padham}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract concept-tagged padhams (Padham–Meaning) for vetting and slim lookup",
    )
    parser.add_argument(
        "--config",
        default="poc/config.ini",
        help="Path to INI config with [db] section",
    )
    parser.add_argument(
        "--table",
        default=None,
        help="Override table name from config (e.g. PasuramsArthamTable)",
    )
    parser.add_argument(
        "--theme",
        default=None,
        help="Theme id from theme_registry.json (sets concept, aliases, output paths)",
    )
    parser.add_argument(
        "--concept",
        default="மகாபாரதம்",
        help="Tamil concept token to find in SimilarWords",
    )
    parser.add_argument(
        "--concept-english",
        default="mahabharatham",
        help="English alias to attach in padham_lookup (fixed, not mined)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: lookupsimilarwords/extracts/{theme}_lookup.json)",
    )
    parser.add_argument(
        "--csv",
        default=None,
        metavar="PATH",
        help="Optional CSV path for Padham–Meaning review (records only)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="DB fetch batch size",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_config = load_db_config(Path(args.config))
    if args.table:
        db_config["table"] = args.table

    if not db_config.get("table"):
        raise ValueError("Database table not configured; set [db] table or pass --table")

    concept = normalize_text(args.concept)
    concept_english = normalize_text(args.concept_english)
    query_concepts = [concept]
    aliases = [concept]
    if concept_english and concept_english not in aliases:
        aliases.append(concept_english)

    if args.theme:
        from lookupsimilarwords.theme_registry import get_theme

        theme = get_theme(args.theme)
        concept = normalize_text(theme.get("concept", args.theme))
        query_concepts = theme.get("query_concepts", [concept])
        aliases = list(theme.get("aliases", [concept]))
        if concept_english and len(aliases) <= 1:
            concept_english = normalize_text(args.concept_english)

    print(f"Querying `{db_config['table']}` for SimilarWords containing any of: {query_concepts}")
    raw_rows = query_concept_rows(db_config, query_concepts, batch_size=args.batch_size)

    if args.theme:
        data = {
            "theme_id": args.theme,
            "concept": concept,
            "aliases": aliases,
            "source_table": db_config["table"],
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "record_count": 0,
            "distinct_padham_count": 0,
            "records": [],
            "padham_lookup": {},
        }
        records: List[Dict[str, Any]] = []
        for row in raw_rows:
            record = build_record(row)
            if record:
                records.append(record)
        data["records"] = records
        data["record_count"] = len(records)
        data["padham_lookup"] = build_padham_lookup(records, aliases)
        data["distinct_padham_count"] = len(data["padham_lookup"])
    else:
        data = build_output(
            raw_rows,
            concept=concept,
            concept_english=concept_english,
            source_table=db_config["table"],
        )

    if args.output:
        output_path = Path(args.output)
    elif args.theme:
        output_path = Path(f"lookupsimilarwords/extracts/{args.theme}_lookup.json")
    else:
        output_path = Path("lookupsimilarwords/mahabharatham_lookup.json")
    save_json(data, output_path)
    print(f"\nWrote JSON to {output_path}")

    if args.csv:
        csv_path = Path(args.csv)
    elif args.theme:
        csv_path = Path(f"lookupsimilarwords/extracts/{args.theme}_lookup.csv")
    else:
        csv_path = None

    if csv_path is not None:
        save_csv(data["records"], csv_path)
        print(f"Wrote CSV to {csv_path}")

    print()
    print_summary(data)


if __name__ == "__main__":
    main()
