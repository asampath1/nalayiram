#!/usr/bin/env python3
"""Replace Pasuram verse text for ஆறாம் பத்து (1448-1547) from poc/pasuram.txt.

Keeps Dravidaveda Padham/Meaning/Title/SimilarWords unchanged.
Only updates the shared Pasuram column (readability / spacing from txt).

  poc/.venv/bin/python poc/scripts/replace_periya_thirumozhi_patthu6_pasuram_from_txt.py --dry-run
  poc/.venv/bin/python poc/scripts/replace_periya_thirumozhi_patthu6_pasuram_from_txt.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config

PASURAM_TXT = ROOT / "poc" / "pasuram.txt"
POC_JSON = ROOT / "poc" / "output" / "periya_thirumozhi_patthu6_poc.json"
EXTRACT_JSON = ROOT / "poc" / "output" / "periya_thirumozhi_patthu6_verses_from_txt.json"
PASURAM_START = 1448
PASURAM_END = 1547

SUFFIX_FIND_RE = re.compile(
    r"(?<![0-9])(6-(?:10|[1-9])-(?:10|[1-9]))\s*[-–—]?",
    re.UNICODE,
)
SEP_LINE_RE = re.compile(r"^[—–\-−_]{4,}\s*$", re.MULTILINE)


def pasuram_for_suffix(suffix: str) -> int:
    _, pathigam_s, pattu_s = suffix.split("-")
    return PASURAM_START + (int(pathigam_s) - 1) * 10 + (int(pattu_s) - 1)


def normalize_verse(text: str, suffix: str) -> str:
    text = text.replace("\u2028", "\n").replace("\u2029", "\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line and not SEP_LINE_RE.match(line)]
    dash_only = re.compile(r"^[—–\-−_]+$", re.UNICODE)
    lines = [line for line in lines if not dash_only.match(line)]
    suffix_only = re.compile(
        r"^[–\-—\s]*" + re.escape(suffix) + r"\s*-?\s*$", re.UNICODE
    )
    lines = [line for line in lines if not suffix_only.match(line)]
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    canon = f"–{suffix}"
    last = lines[-1]
    last = re.sub(
        r"[–\-—\s]*" + re.escape(suffix) + r"\s*-?\s*$",
        "",
        last,
    ).rstrip()
    last = re.sub(r"\s+" + re.escape(suffix) + r"\s*-?\s*$", "", last).rstrip()
    last = re.sub(r"[–\-—]+\s*$", "", last).rstrip()
    lines[-1] = f"{last} {canon}" if last else canon
    return "\n".join(lines)


def verse_block_start(raw: str, match: re.Match[str]) -> int:
    """Start of multi-line verse stanza ending with suffix marker at match."""
    line_start = raw.rfind("\n", 0, match.start()) + 1
    pos = line_start
    while pos > 0:
        prev_nl = raw.rfind("\n", 0, pos - 1)
        if prev_nl < 0:
            break
        prev_line = raw[prev_nl + 1 : pos].strip()
        if not prev_line or SEP_LINE_RE.match(prev_line):
            break
        if SUFFIX_FIND_RE.search(prev_line):
            break
        if prev_line.startswith(("Prabhadham", "If No", "Title :", "Example")):
            break
        if "dravidaveda" in prev_line.lower():
            break
        pos = prev_nl + 1
    return pos


def extract_verses(path: Path) -> Dict[int, str]:
    raw = path.read_text(encoding="utf-8")
    first = None
    for match in SUFFIX_FIND_RE.finditer(raw):
        if match.group(1) != "6-1-1":
            continue
        probe = raw[max(0, match.start() - 8) : match.start()]
        if any("\u0b80" <= ch <= "\u0bff" for ch in probe):
            first = match
            break
    if first is None:
        raise RuntimeError("Could not find verse marker 6-1-1")

    ordered: List[re.Match[str]] = []
    seen: set[str] = set()
    for match in SUFFIX_FIND_RE.finditer(raw):
        if match.start() < first.start():
            continue
        suffix = match.group(1)
        if suffix in seen:
            continue
        seen.add(suffix)
        ordered.append(match)

    verses: Dict[int, str] = {}
    for index, match in enumerate(ordered):
        suffix = match.group(1)
        if index == 0:
            start = verse_block_start(raw, match)
        else:
            prev = ordered[index - 1]
            mid = raw[prev.end() : match.start()]
            sep = SEP_LINE_RE.search(mid)
            if sep:
                start = prev.end() + sep.end()
            else:
                start = verse_block_start(raw, match)
        end = match.start() + len(suffix)
        verse_text = raw[start:end]
        pasuram_number = pasuram_for_suffix(suffix)
        verses[pasuram_number] = normalize_verse(verse_text, suffix)

    missing = [n for n in range(PASURAM_START, PASURAM_END + 1) if n not in verses]
    if missing:
        raise RuntimeError(f"Missing verses for: {missing}")
    empty = [n for n, text in verses.items() if not text.strip()]
    if empty:
        raise RuntimeError(f"Empty verses for: {empty}")
    leak_markers = ("ஷட்பத", "என்கிறார்", "ஸ்வாபதேசம்", "Title :")
    leaked = [
        n
        for n, text in verses.items()
        if any(marker in text for marker in leak_markers)
    ]
    if leaked:
        raise RuntimeError(f"Commentary leak suspected in verses: {leaked}")
    return verses


def apply_to_db(verses: Dict[int, str], config_path: Path, dry_run: bool) -> tuple[int, int]:
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
    changed_pasurams = 0
    changed_rows = 0
    try:
        for pasuram_number, new_text in sorted(verses.items()):
            cur.execute(
                f"""
                SELECT Pasuram FROM {db.table}
                WHERE PasuramNumber=%s AND Prabandham='பெரிய திருமொழி'
                LIMIT 1
                """,
                (pasuram_number,),
            )
            row = cur.fetchone()
            if not row:
                print(f"WARNING: no DB rows for {pasuram_number} (skipped)")
                continue
            old = row[0] or ""
            if old == new_text:
                continue
            changed_pasurams += 1
            if dry_run:
                continue
            cur.execute(
                f"""
                UPDATE {db.table}
                SET Pasuram=%s
                WHERE PasuramNumber=%s AND Prabandham='பெரிய திருமொழி'
                """,
                (new_text, pasuram_number),
            )
            changed_rows += cur.rowcount
        if not dry_run:
            conn.commit()
    finally:
        cur.close()
        conn.close()
    return changed_pasurams, changed_rows


def apply_to_json(verses: Dict[int, str], json_path: Path) -> int:
    if not json_path.exists():
        return 0
    records = json.loads(json_path.read_text(encoding="utf-8"))
    updated = 0
    for row in records:
        n = int(row["PasuramNumber"])
        if n in verses and row.get("Pasuram") != verses[n]:
            row["Pasuram"] = verses[n]
            updated += 1
    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--pasuram-txt", default=str(PASURAM_TXT))
    parser.add_argument("--poc-json", default=str(POC_JSON))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    verses = extract_verses(Path(args.pasuram_txt))
    EXTRACT_JSON.write_text(
        json.dumps({str(k): v for k, v in verses.items()}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Extracted {len(verses)} verses → {EXTRACT_JSON}")
    for n in (1448, 1449, 1458, 1547):
        print(f"--- {n} ---")
        print(verses[n])

    if args.dry_run and not args.apply:
        changed, _ = apply_to_db(verses, Path(args.config), dry_run=True)
        print(f"Dry run: {changed} pasurams differ from DB (no writes).")
        return
    if not args.apply:
        print("Use --apply to update POC DB + JSON.")
        return

    changed_pasurams, changed_rows = apply_to_db(
        verses, Path(args.config), dry_run=False
    )
    json_updated = apply_to_json(verses, Path(args.poc_json))
    print(
        f"Updated Pasuram text for {changed_pasurams} pasurams "
        f"({changed_rows} padham rows); JSON rows {json_updated}"
    )


if __name__ == "__main__":
    main()
