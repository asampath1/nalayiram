#!/usr/bin/env python3
"""Backfill பெரிய திருமொழி 1330-1332 (4-9-3…4-9-5) into POC from poc/pasuram.txt.

Dravidaveda still 404s on /1330/, /1331/ and /1332/, so verse, padhavurai and
Title are taken from the manually supplied block in poc/pasuram.txt instead.

Block shape per pasuram:

    1330
    <verse lines, last ends with the 4-9-N marker>
    பதவுரை
    <padham> - <meaning>          (one per line)
    Title: (4-9–நும்மைத் தொழுதோம்) (திருவிந்தளூர்) - (ஸ்ரீ பெரியவாச்சான் பிள்ளை)
    (<commentary>)

  poc/.venv/bin/python poc/scrapers/ingest_periya_thirumozhi_1330_1332.py --dry-run
  poc/.venv/bin/python poc/scrapers/ingest_periya_thirumozhi_1330_1332.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from poc.config import load_config
from poc.db_loader import load_json_to_db
from poc.fill_workbook import transliterate_records_from_config
from poc.generate_similar_words import finalize_records
from poc.json_exporter import export_to_json
from poc.load_workbook import delete_pasuram_range

PRABANDHAM = "பெரிய திருமொழி"
PRABANDHAM_TITLE = "பெரிய திருமொழி, Periya Thirumozhi"
ALZWAR = "திருமங்கையாழ்வார்"
PATHIGAM_CODE = "4-9"
PATHIGAM_SHORT = "நும்மைத் தொழுதோம்"
PATHIGAM_SHORT_ENG = "Nummaith Thozhudhom"
PASURAM_NUMBERS = (1330, 1331, 1332)
PATHIGAM_START = 1328

PASURAM_TXT = ROOT / "poc" / "pasuram.txt"
DEFAULT_JSON = ROOT / "poc/output/periya_thirumozhi_1330_1332_poc.json"
COVERAGE_REPORT = ROOT / "lookupsimilarwords/reviews/periya_thirumozhi_1330_1332_padhavurai_coverage.txt"

MARKER_RE = re.compile(r"[\s—–\-−]*4[-–]9[-–]([345])[\s—–\-−]*$")
SEP_LINE_RE = re.compile(r"^[—–\-−_]{4,}\s*$")


def verse_index(pasuram_number: int) -> int:
    """Verse position within the pathigam (1-10) → PattuNumber."""
    return pasuram_number - PATHIGAM_START + 1


def pathigam_aliases(pasuram_number: int) -> List[str]:
    """Search aliases in the same order as the already-loaded 1328."""
    v = verse_index(pasuram_number)
    eng_compact = PATHIGAM_SHORT_ENG.replace(" ", "")
    return [
        f"{PATHIGAM_CODE.replace('-', '.')}.{v}",
        f"{PATHIGAM_CODE}-{v}",
        f"{PATHIGAM_CODE.replace('-', ' ')} {v}",
        f"{PATHIGAM_CODE}–{PATHIGAM_SHORT}",
        f"{PATHIGAM_CODE}-{eng_compact}",
        PATHIGAM_SHORT_ENG,
        f"{PATHIGAM_CODE} {PATHIGAM_SHORT}",
    ]


def normalize_verse(lines: List[str], pasuram_number: int) -> str:
    """Keep the supplied line structure; normalise only the trailing marker."""
    kept = [" ".join(line.split()) for line in lines if line.strip()]
    if not kept:
        raise RuntimeError(f"No verse text for {pasuram_number}")
    kept[-1] = MARKER_RE.sub("", kept[-1]).rstrip(" —–-−")
    kept[-1] = f"{kept[-1]} –{PATHIGAM_CODE}-{verse_index(pasuram_number)}"
    return "\n".join(kept)


def parse_blocks(path: Path) -> Dict[int, Dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    lines = [line.rstrip() for line in raw.replace("\r\n", "\n").split("\n")]

    starts: Dict[int, int] = {}
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.isdigit() and int(stripped) in PASURAM_NUMBERS:
            starts.setdefault(int(stripped), index)
    missing = [n for n in PASURAM_NUMBERS if n not in starts]
    if missing:
        raise RuntimeError(f"No block header found for: {missing}")

    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    blocks: Dict[int, Dict[str, Any]] = {}
    for position, (pasuram_number, start) in enumerate(ordered):
        end = ordered[position + 1][1] if position + 1 < len(ordered) else len(lines)
        body = lines[start + 1 : end]

        verse_lines: List[str] = []
        padhams: List[Dict[str, str]] = []
        title_parts: List[str] = []
        section = "verse"
        for line in body:
            stripped = line.strip()
            if SEP_LINE_RE.match(stripped):
                continue
            if stripped == "பதவுரை":
                section = "padhavurai"
                continue
            if stripped.startswith("Title:"):
                section = "title"
                header = stripped[len("Title:") :].strip()
                if header:
                    title_parts.append(header)
                continue
            if section == "verse":
                verse_lines.append(line)
            elif section == "padhavurai":
                if not stripped:
                    continue
                if " - " not in stripped:
                    raise RuntimeError(
                        f"{pasuram_number}: padhavurai line missing ' - ' separator: {stripped!r}"
                    )
                padham, meaning = stripped.split(" - ", 1)
                padhams.append(
                    {"padham": padham.strip(), "meaning": meaning.strip()}
                )
            elif section == "title" and stripped:
                title_parts.append(stripped)

        if not padhams:
            raise RuntimeError(f"{pasuram_number}: no padhavurai lines found")
        if len(title_parts) < 2:
            raise RuntimeError(f"{pasuram_number}: Title header + commentary expected")

        commentary = " ".join(title_parts[1:])
        commentary = re.sub(r"\s+\)", ")", commentary)
        commentary = re.sub(r"\(\s+", "(", commentary)
        blocks[pasuram_number] = {
            "pasuram": normalize_verse(verse_lines, pasuram_number),
            "padhams": padhams,
            "title": f"{title_parts[0]}\n{commentary}",
        }
    return blocks


def blocks_to_records(blocks: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for pasuram_number in PASURAM_NUMBERS:
        block = blocks[pasuram_number]
        for padham_number, pair in enumerate(block["padhams"], start=1):
            records.append(
                {
                    "Prabandham": PRABANDHAM,
                    "PasuramNumber": pasuram_number,
                    "Pasuram": block["pasuram"],
                    "PattuNumber": verse_index(pasuram_number),
                    "Padham": pair["padham"],
                    "Meaning": pair["meaning"],
                    "Alzwar": ALZWAR,
                    "PadhamNumber": padham_number,
                    "Title": block["title"],
                    "Word": "",
                    "SimilarWords": "",
                    "NithyaanusandhamIndex": None,
                    "PrabandhamTitle": PRABANDHAM_TITLE,
                }
            )
    return records


def apply_aliases(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    updated: List[Dict[str, Any]] = []
    for record in records:
        row = dict(record)
        similar = str(row.get("SimilarWords", "") or "").strip()
        for alias in pathigam_aliases(int(row["PasuramNumber"])):
            if alias and alias not in similar:
                similar = f"{similar},{alias}" if similar else alias
        row["SimilarWords"] = similar
        updated.append(row)
    return updated


def write_coverage_report(blocks: Dict[int, Dict[str, Any]]) -> None:
    """Padhavurai here is partial; record which verse words have no padham row."""
    lines = [
        "பெரிய திருமொழி 1330-1332 (4-9-3…4-9-5) — padhavurai coverage",
        "Source: poc/pasuram.txt (manual; Dravidaveda still 404s on these pages).",
        "",
    ]
    for pasuram_number in PASURAM_NUMBERS:
        block = blocks[pasuram_number]
        covered = " ".join(p["padham"] for p in block["padhams"])
        covered_words = {w.strip(".,;:!?()") for w in covered.split() if w.strip()}
        verse = re.sub(r"–4-9-\d+$", "", block["pasuram"]).replace("\n", " ")
        uncovered = [
            w
            for w in verse.split()
            if w.strip(".,;:!?()—–-") and w.strip(".,;:!?()—–-") not in covered_words
        ]
        lines.append(
            f"{pasuram_number} ({PATHIGAM_CODE}-{verse_index(pasuram_number)}): "
            f"{len(block['padhams'])} padham rows"
        )
        lines.append(f"  no padham row for: {' '.join(uncovered)}")
        lines.append("")
    COVERAGE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--pasuram-txt", default=str(PASURAM_TXT))
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-themes", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    blocks = parse_blocks(Path(args.pasuram_txt))
    write_coverage_report(blocks)

    for pasuram_number in PASURAM_NUMBERS:
        block = blocks[pasuram_number]
        print(f"===== {pasuram_number} ({PATHIGAM_CODE}-{verse_index(pasuram_number)}) =====")
        print(block["pasuram"])
        print(f"  padham rows: {len(block['padhams'])}")
        print(f"  Title: {block['title'].splitlines()[0]}")
        print()

    records = blocks_to_records(blocks)
    print(f"Padham rows total: {len(records)}")

    records = transliterate_records_from_config(records, Path(args.config))
    records = finalize_records(
        records,
        apply_themes=not args.no_themes,
        themes=None,
        group_by_pasuram_number=False,
    )
    records = apply_aliases(records)

    output_json = Path(args.output_json)
    export_to_json(records, output_json)
    print(f"Wrote {output_json}")
    print(f"Coverage report → {COVERAGE_REPORT}")

    if args.dry_run and not args.apply:
        print("Dry run complete (no DB changes).")
        return
    if not args.apply:
        print("Use --apply to load into POC.")
        return

    config = load_config(args.config)
    db = config.database
    delete_pasuram_range(db, min(PASURAM_NUMBERS), max(PASURAM_NUMBERS), dry_run=False)
    inserted = load_json_to_db(output_json, db, dry_run=False)
    print(f"Loaded {inserted} rows into {db.table} for {PRABANDHAM} (1330-1332)")


if __name__ == "__main__":
    main()
