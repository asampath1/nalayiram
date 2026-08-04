#!/usr/bin/env python3
"""Add `{pathigam} {short_name}` search aliases to SimilarWords for PT patthus 2-4.

Used when pasuram.txt no longer contains older patthu commentary blocks but
release-note pathigam links need unambiguous pocindex search prefixes.

  poc/.venv/bin/python poc/scripts/apply_periya_thirumozhi_pathigam_search_aliases.py --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config
from poc.scripts.apply_periya_thirumozhi_patthu4_titles import PATHIGAM_META as PATTHU4_META

PRABANDHAM = "பெரிய திருமொழி"

# (code, start, end, short_name)
PATTHU2: List[Tuple[str, int, int, str]] = [
    ("2-1", 1048, 1057, "வானவர்"),
    ("2-2", 1058, 1067, "காசையாடை"),
    ("2-3", 1068, 1077, "விற்பெருவிழவும்"),
    ("2-4", 1078, 1087, "அன்றாயர்"),
    ("2-5", 1088, 1097, "பாராயது"),
    ("2-6", 1098, 1107, "நண்ணாத"),
    ("2-7", 1108, 1117, "திவளும்"),
    ("2-8", 1118, 1127, "திரிபுரம்"),
    ("2-9", 1128, 1137, "சொல்லுவன்"),
    ("2-10", 1138, 1147, "மஞ்சாடு"),
]

PATTHU3: List[Tuple[str, int, int, str]] = [
    ("3-1", 1148, 1157, "இருந்தண்"),
    ("3-2", 1158, 1167, "ஊன் வாட"),
    ("3-3", 1168, 1177, "வாட மருதிடை"),
    ("3-4", 1178, 1187, "ஒருகுறளாய்"),
    ("3-5", 1188, 1197, "வந்து"),
    ("3-6", 1198, 1207, "தூவிரிய"),
    ("3-7", 1208, 1217, "கள்வன் கொல்"),
    ("3-8", 1218, 1227, "நந்தா விளக்கு"),
    ("3-9", 1228, 1237, "சலங்கொண்ட"),
    ("3-10", 1238, 1247, "திருமடந்தை"),
]


def patthu4_entries() -> List[Tuple[str, int, int, str]]:
    rows: List[Tuple[str, int, int, str]] = []
    for code, info in sorted(PATTHU4_META.items(), key=lambda item: int(item[1]["start"])):
        rows.append((code, int(info["start"]), int(info["end"]), info["short_name"]))
    return rows


def aliases_for_pathigams(
    entries: List[Tuple[str, int, int, str]],
) -> Dict[int, List[str]]:
    by_pasuram: Dict[int, List[str]] = {}
    for code, start, end, short_name in entries:
        alias = f"{code} {short_name}"
        for pasuram_number in range(start, end + 1):
            by_pasuram[pasuram_number] = [alias]
    return by_pasuram


def merge_aliases(similar: str, aliases: List[str]) -> str:
    for alias in aliases:
        if alias and alias not in similar:
            similar = f"{similar},{alias}" if similar else alias
    return similar


def apply_to_db(aliases_by_pasuram: Dict[int, List[str]], config_path: Path) -> int:
    config = load_config(str(config_path))
    db = config.database
    conn = mysql.connector.connect(
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        database=db.database,
    )
    cur = conn.cursor()
    updated = 0
    try:
        for pasuram_number, aliases in sorted(aliases_by_pasuram.items()):
            cur.execute(
                f"SELECT SimilarWords FROM {db.table} "
                f"WHERE PasuramNumber=%s AND Prabandham=%s LIMIT 1",
                (pasuram_number, PRABANDHAM),
            )
            row = cur.fetchone()
            if not row:
                continue
            similar = merge_aliases((row[0] or ""), aliases)
            cur.execute(
                f"UPDATE {db.table} SET SimilarWords=%s "
                f"WHERE PasuramNumber=%s AND Prabandham=%s",
                (similar, pasuram_number, PRABANDHAM),
            )
            updated += cur.rowcount
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return updated


def apply_to_json(
    aliases_by_pasuram: Dict[int, List[str]], json_path: Path
) -> int:
    if not json_path.exists():
        return 0
    records = json.loads(json_path.read_text(encoding="utf-8"))
    updated = 0
    for row in records:
        n = int(row["PasuramNumber"])
        if n not in aliases_by_pasuram:
            continue
        similar = merge_aliases(str(row.get("SimilarWords") or ""), aliases_by_pasuram[n])
        if similar != row.get("SimilarWords"):
            row["SimilarWords"] = similar
            updated += 1
    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    all_aliases: Dict[int, List[str]] = {}
    for entries in (PATTHU2, PATTHU3, patthu4_entries()):
        chunk = aliases_for_pathigams(entries)
        all_aliases.update(chunk)
    print(f"Pathigam search aliases for {len(all_aliases)} pasurams (patthus 2-4)")

    if args.dry_run and not args.apply:
        for code, start, end, name in PATTHU2[:2] + PATTHU3[:1] + patthu4_entries()[:1]:
            print(f"  {code} {name} ({start}-{end}) → alias '{code} {name}'")
        print("Dry run (no DB/JSON changes).")
        return

    if not args.apply:
        print("Use --apply to update POC DB and JSON files.")
        return

    db_rows = apply_to_db(all_aliases, Path(args.config))
    json_rows = 0
    for patthu in (2, 3, 4):
        json_path = ROOT / f"poc/output/periya_thirumozhi_patthu{patthu}_poc.json"
        json_rows += apply_to_json(all_aliases, json_path)
    print(f"DB rows updated: {db_rows}; JSON rows updated: {json_rows}")


if __name__ == "__main__":
    main()
