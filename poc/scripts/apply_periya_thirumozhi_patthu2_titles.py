#!/usr/bin/env python3
"""Apply Titles for பெரிய திருமொழி இரண்டாம் பத்து (1048-1147) from poc/pasuram.txt → POC only."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config

PASURAM_TXT = ROOT / "poc" / "pasuram.txt"
POC_JSON = ROOT / "poc" / "output" / "periya_thirumozhi_patthu2_poc.json"
TITLES_JSON = ROOT / "poc" / "output" / "periya_thirumozhi_patthu2_titles.json"

HEADER_RE = re.compile(
    r"Title\s*:\s*For Pasuram Number Range\s+(\d+)\s+to\s+(\d+)\s+"
    r"\((2-\d+)–([^)]+)\)\s+\(([^)]+)\)",
    re.UNICODE,
)
ORDINAL_MARKERS = [
    ("முதல்", 1),
    ("இரண்டாம்", 2),
    ("மூன்றாம்", 3),
    ("நாலாம்", 4),
    ("நான்காம்", 4),
    ("ஐந்தாம்", 5),
    ("ஆறாம்", 6),
    ("ஏழாம்", 7),
    ("எட்டாம்", 8),
    ("ஒன்பதாம்", 9),
    ("பத்தாம்", 10),
]
MARKER_RE = re.compile(
    r"(?:என்கிறார்\s*[–\-—]?\s*)?("
    + "|".join(re.escape(name) for name, _ in ORDINAL_MARKERS)
    + r")\s+பாசுரத்தில்",
    re.UNICODE,
)
ORDINAL_TO_INDEX = {name: idx for name, idx in ORDINAL_MARKERS}
VERSE_PREFIX_RE = re.compile(r"^நண்ணாத\s+வாளவுணர்.*?2-6-1-?\s*", re.DOTALL)
RESPECTIVE_PREFIX_RE = re.compile(
    r"^[-–—\s]*\(respective title for 10 pasurams given below\)\s*",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    text = text.replace("\u2028", "\n").replace("\u2029", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text.split("\n")]
    parts = [line for line in lines if line]
    return " ".join(parts).strip(" –-\t")


def clean_body_prefix(body: str, start: int) -> str:
    body = RESPECTIVE_PREFIX_RE.sub("", body).strip()
    if start == 1098:
        body = VERSE_PREFIX_RE.sub("", body).strip()
    return body


def split_pathigam_bodies(raw: str) -> List[Tuple[re.Match[str], str]]:
    matches = list(HEADER_RE.finditer(raw))
    # Keep the last header per range so the instructional example is skipped.
    by_range: dict[tuple[int, int], re.Match[str]] = {}
    for match in matches:
        key = (int(match.group(1)), int(match.group(2)))
        by_range[key] = match
    matches = sorted(by_range.values(), key=lambda m: m.start())
    if len(matches) != 10:
        raise RuntimeError(f"Expected 10 pathigam headers, found {len(matches)}")
    sections: List[Tuple[re.Match[str], str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        body = raw[start:end]
        body = re.split(r"—{5,}|-{5,}", body, maxsplit=1)[0]
        sections.append((match, body.strip()))
    return sections


def split_commentaries(body: str, start: int, end: int) -> Dict[int, str]:
    body = normalize_text(body)
    body = clean_body_prefix(body, start)

    expected = list(range(start, end + 1))
    by_index: Dict[int, str] = {}
    matches = list(MARKER_RE.finditer(body))
    if not matches:
        raise RuntimeError(f"No ordinal markers in range {start}-{end}")

    cursor = 0
    for match in matches:
        ordinal = match.group(1)
        idx = ORDINAL_TO_INDEX[ordinal]
        chunk = body[cursor : match.end()].strip(" –-\t")
        if not chunk:
            raise RuntimeError(f"Empty commentary for pasuram index {idx} in {start}-{end}")
        by_index[idx] = chunk
        cursor = match.end()

    trailing = body[cursor:].strip(" –-\t")
    if 10 not in by_index:
        if not trailing:
            raise RuntimeError(f"Missing 10th commentary for {start}-{end}")
        by_index[10] = trailing
        trailing = ""
    elif trailing:
        # 2-9 summary paragraph after பத்தாம்
        by_index[10] = f"{by_index[10]} {trailing}".strip()

    if set(by_index) != set(range(1, 11)):
        raise RuntimeError(
            f"Incomplete commentaries for {start}-{end}: got {sorted(by_index)}"
        )

    return {
        pasuram_number: by_index[index]
        for index, pasuram_number in enumerate(expected, start=1)
    }


def build_title(pathigam_code: str, short_name: str, divyadesam: str, commentary: str) -> str:
    header = f"({pathigam_code}–{short_name.strip()}) ({divyadesam.strip()})"
    body = commentary.strip()
    if not (body.startswith("(") and body.endswith(")")):
        body = f"({body})"
    return f"{header}\n{body}"


def parse_titles(path: Path) -> Dict[int, Dict[str, str]]:
    raw = path.read_text(encoding="utf-8")
    titles: Dict[int, Dict[str, str]] = {}
    for match, body in split_pathigam_bodies(raw):
        start = int(match.group(1))
        end = int(match.group(2))
        code = match.group(3)
        short_name = match.group(4).strip()
        divyadesam = match.group(5).strip()
        commentaries = split_commentaries(body, start, end)
        for pasuram_number, commentary in commentaries.items():
            titles[pasuram_number] = {
                "pathigam_code": code,
                "short_name": short_name,
                "divyadesam": divyadesam,
                "commentary": commentary,
                "title": build_title(code, short_name, divyadesam, commentary),
            }
    if len(titles) != 100:
        raise RuntimeError(f"Expected 100 titles, got {len(titles)}")
    missing = [n for n in range(1048, 1148) if n not in titles]
    if missing:
        raise RuntimeError(f"Missing pasurams: {missing}")
    return titles


def apply_to_json(titles: Dict[int, Dict[str, str]], json_path: Path) -> int:
    records = json.loads(json_path.read_text(encoding="utf-8"))
    heading_aliases = build_heading_aliases(titles)
    updated = 0
    for row in records:
        pasuram_number = int(row["PasuramNumber"])
        info = titles.get(pasuram_number)
        if not info:
            continue
        row["Title"] = info["title"]
        similar = str(row.get("SimilarWords") or "")
        for alias in heading_aliases.get(pasuram_number, []):
            if alias and alias not in similar:
                similar = f"{similar},{alias}" if similar else alias
        row["SimilarWords"] = similar
        updated += 1
    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return updated


def apply_to_db(titles: Dict[int, Dict[str, str]], config_path: Path) -> int:
    config = load_config(str(config_path))
    db = config.database
    heading_aliases = build_heading_aliases(titles)
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
        for pasuram_number, info in sorted(titles.items()):
            title = info["title"]
            aliases = heading_aliases.get(pasuram_number, [])
            cur.execute(
                f"""
                SELECT SimilarWords FROM {db.table}
                WHERE PasuramNumber=%s AND Prabandham='பெரிய திருமொழி' LIMIT 1
                """,
                (pasuram_number,),
            )
            row = cur.fetchone()
            similar = (row[0] if row else "") or ""
            for alias in aliases:
                if alias and alias not in similar:
                    similar = f"{similar},{alias}" if similar else alias
            cur.execute(
                f"""
                UPDATE {db.table}
                SET Title=%s, SimilarWords=%s
                WHERE PasuramNumber=%s AND Prabandham='பெரிய திருமொழி'
                """,
                (title, similar, pasuram_number),
            )
            updated += cur.rowcount
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return updated


def build_heading_aliases(titles: Dict[int, Dict[str, str]]) -> Dict[int, List[str]]:
    """Tamil+English pathigam headings for SimilarWords, e.g. 2-3–விற்பெருவிழவும், 2-3-Virperuvizhavum."""
    import re

    from poc.transliterate_gpt_adapter import transliterate_with_public_html_script

    pathigams: Dict[str, Dict[str, Any]] = {}
    for pasuram_number, info in titles.items():
        code = info["pathigam_code"]
        bucket = pathigams.setdefault(
            code,
            {"short_name": info["short_name"], "numbers": []},
        )
        bucket["numbers"].append(pasuram_number)

    short_names = [meta["short_name"] for meta in pathigams.values()]
    translations = transliterate_with_public_html_script(
        short_names,
        ROOT / "public_html" / "transliterateGPT.py",
        Path("poc/cache/transliterate_gpt_dict.json"),
        Path("poc/output/transliterate_pathigam_headings.xlsx"),
    )
    name_to_eng = dict(zip(short_names, translations))

    aliases_by_pasuram: Dict[int, List[str]] = {}
    for code, meta in pathigams.items():
        tamil = meta["short_name"]
        eng = name_to_eng[tamil]
        eng_compact = re.sub(r"\s+", "", eng)
        if eng_compact and eng_compact[0].islower():
            eng_compact = eng_compact[0].upper() + eng_compact[1:]
        aliases = [
            f"{code}–{tamil}",
            f"{code}-{eng_compact}",
            tamil,
            eng,
        ]
        for pasuram_number in meta["numbers"]:
            aliases_by_pasuram[pasuram_number] = aliases
    return aliases_by_pasuram


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--pasuram-txt", default=str(PASURAM_TXT))
    parser.add_argument("--poc-json", default=str(POC_JSON))
    parser.add_argument("--titles-json", default=str(TITLES_JSON))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    titles = parse_titles(Path(args.pasuram_txt))
    Path(args.titles_json).write_text(
        json.dumps(titles, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Parsed {len(titles)} titles → {args.titles_json}")
    for n in (1048, 1077, 1098, 1137):
        preview = titles[n]["title"][:140].replace("\n", " | ")
        print(f"{n}: {preview}")

    if args.dry_run and not args.apply:
        print("Dry run only (no DB/JSON updates).")
        return
    if not args.apply:
        print("Use --apply to update POC JSON + DB.")
        return

    json_updated = apply_to_json(titles, Path(args.poc_json))
    print(f"Updated {json_updated} rows in {args.poc_json}")
    db_updated = apply_to_db(titles, Path(args.config))
    print(f"Updated {db_updated} rows in POC DB")


if __name__ == "__main__":
    main()
