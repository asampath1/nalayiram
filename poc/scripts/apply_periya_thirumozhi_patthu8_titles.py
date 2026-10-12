#!/usr/bin/env python3
"""Apply Titles for பெரிய திருமொழி எட்டாம் பத்து (1648-1747) from poc/pasuram.txt → POC.

Title format when commentary exists:
  (8-1–சிலையிலங்கு) (திரு கண்ணபுரம் 1) - (context) - (ஸ்ரீ பெரியவாச்சான் பிள்ளை)
  (commentary)

pasuram.txt supplies a pathigam context only for 8-1..8-4; the remaining pathigams
use the patthu 7 header shape without a context bracket.
திரு கண்ணபுரம் 1..10 are pathigam ordinals at the same Divyadesam, not distinct DDs.
If no commentary after pasuram in pasuram.txt → empty Title.
Pathigam heading aliases still added to SimilarWords for all 10 pasurams.
"""
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
from poc.transliterate_gpt_adapter import transliterate_with_public_html_script

PASURAM_TXT = ROOT / "poc" / "pasuram.txt"
POC_JSON = ROOT / "poc" / "output" / "periya_thirumozhi_patthu8_poc.json"
TITLES_JSON = ROOT / "poc" / "output" / "periya_thirumozhi_patthu8_titles.json"
AUTHOR = "ஸ்ரீ பெரியவாச்சான் பிள்ளை"
PASURAM_START = 1648
PASURAM_END = 1747

PATHIGAM_META: Dict[str, Dict[str, str]] = {
    "8-1": {
        "start": "1648",
        "end": "1657",
        "short_name": "சிலையிலங்கு",
        "divyadesam": "திரு கண்ணபுரம் 1",
        "context": "தலைமகன்பால் ஈடுபட்ட தலைமகளது செய்லகளை வினவ வந்தாருக்குத் தாய் கூறுதல்",
    },
    "8-2": {
        "start": "1658",
        "end": "1667",
        "short_name": "தெள்ளியீர்",
        "divyadesam": "திரு கண்ணபுரம் 2",
        "context": "தலைவியின் நிலை கண்ட தாய் தலைமகளை இயற்பழித்தும் தலைமகளது இளமைக்கு இறங்கியும் கூறுதல்",
    },
    "8-3": {
        "start": "1668",
        "end": "1677",
        "short_name": "கரையெடுத்த",
        "divyadesam": "திரு கண்ணபுரம் 3",
        "context": "தலைமகளைப் பிரிந்த தலைமகள் இரங்கிக் கூறுதல்",
    },
    "8-4": {
        "start": "1678",
        "end": "1687",
        "short_name": "விண்ணவர் தங்கள்",
        "divyadesam": "திரு கண்ணபுரம் 4",
        "context": "கோல்தும்பி",
    },
    "8-5": {
        "start": "1688",
        "end": "1697",
        "short_name": "தந்தை காலில்",
        "divyadesam": "திரு கண்ணபுரம் 5",
        "context": "",
    },
    "8-6": {
        "start": "1698",
        "end": "1707",
        "short_name": "தொண்டீர்",
        "divyadesam": "திரு கண்ணபுரம் 6",
        "context": "",
    },
    "8-7": {
        "start": "1708",
        "end": "1717",
        "short_name": "வியமுடை",
        "divyadesam": "திரு கண்ணபுரம் 7",
        "context": "",
    },
    "8-8": {
        "start": "1718",
        "end": "1727",
        "short_name": "வானோர் அளவும்",
        "divyadesam": "திரு கண்ணபுரம் 8",
        "context": "",
    },
    "8-9": {
        "start": "1728",
        "end": "1737",
        "short_name": "கைம்மான",
        "divyadesam": "திரு கண்ணபுரம் 9",
        "context": "",
    },
    "8-10": {
        "start": "1738",
        "end": "1747",
        "short_name": "வண்டார்",
        "divyadesam": "திரு கண்ணபுரம் 10",
        "context": "",
    },
}

SUFFIX_FIND_RE = re.compile(
    r"(?<![0-9])(8[-–](?:10|[1-9])[-–](?:10|[1-9]))\s*[-–—]?",
    re.UNICODE,
)
SEP_LINE_RE = re.compile(r"^[—–\-−_]{4,}\s*$", re.MULTILINE)


def canonicalize_suffix(suffix: str) -> str:
    return suffix.replace("–", "-").replace("—", "-")


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


def normalize_ws(text: str) -> str:
    text = text.replace("\u2028", "\n").replace("\u2029", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return " ".join(line for line in lines if line).strip(" –-\t")


def code_for_pasuram(pasuram_number: int) -> str:
    return f"8-{(pasuram_number - PASURAM_START) // 10 + 1}"


def extract_blocks(raw: str) -> List[Tuple[str, str]]:
    first = None
    for match in SUFFIX_FIND_RE.finditer(raw):
        if canonicalize_suffix(match.group(1)) != "8-1-1":
            continue
        probe = raw[max(0, match.start() - 8) : match.start()]
        if any("\u0b80" <= ch <= "\u0bff" for ch in probe):
            first = match
            break
    if first is None:
        raise RuntimeError("Could not find verse marker 8-1-1")

    ordered: List[re.Match[str]] = []
    seen: set[str] = set()
    for match in SUFFIX_FIND_RE.finditer(raw):
        if match.start() < first.start():
            continue
        suffix = canonicalize_suffix(match.group(1))
        if suffix in seen:
            continue
        _, a, b = suffix.split("-")
        if not (1 <= int(a) <= 10 and 1 <= int(b) <= 10):
            continue
        seen.add(suffix)
        ordered.append(match)

    blocks: List[Tuple[str, str]] = []
    for index, match in enumerate(ordered):
        content_start = match.end()
        content_end = ordered[index + 1].start() if index + 1 < len(ordered) else len(raw)
        chunk = raw[content_start:content_end]
        if index + 1 < len(ordered):
            next_match = ordered[index + 1]
            verse_start = verse_block_start(raw, next_match)
            chunk = raw[content_start:verse_start]
        sep = SEP_LINE_RE.search(chunk)
        if sep:
            chunk = chunk[: sep.start()]
        commentary = normalize_ws(chunk)
        blocks.append((canonicalize_suffix(match.group(1)), commentary))
    return blocks


def build_title_for(
    code: str, short_name: str, divyadesam: str, context: str, commentary: str
) -> str:
    header = f"({code}–{short_name}) ({divyadesam})"
    if context.strip():
        header = f"{header} - ({context.strip()})"
    header = f"{header} - ({AUTHOR})"
    body = commentary.strip()
    if body and not (body.startswith("(") and body.endswith(")")):
        body = f"({body})"
    elif not body:
        body = "()"
    return f"{header}\n{body}"


def parse_titles(path: Path) -> Dict[int, Dict[str, str]]:
    raw = path.read_text(encoding="utf-8")
    blocks = {suffix: commentary for suffix, commentary in extract_blocks(raw)}
    titles: Dict[int, Dict[str, str]] = {}

    for code, info in PATHIGAM_META.items():
        start_n = int(info["start"])
        end_n = int(info["end"])
        for pasuram_number in range(start_n, end_n + 1):
            pathigam_idx = (pasuram_number - PASURAM_START) // 10 + 1
            pattu_idx = (pasuram_number - PASURAM_START) % 10 + 1
            suffix = f"8-{pathigam_idx}-{pattu_idx}"
            commentary = blocks.get(suffix, "")

            if not commentary.strip():
                title = ""
            else:
                title = build_title_for(
                    code,
                    info["short_name"],
                    info["divyadesam"],
                    info.get("context", ""),
                    commentary,
                )

            titles[pasuram_number] = {
                "pathigam_code": code,
                "short_name": info["short_name"],
                "divyadesam": info["divyadesam"],
                "context": info.get("context", ""),
                "commentary": commentary,
                "title": title,
                "suffix": suffix,
            }

    missing = [n for n in range(PASURAM_START, PASURAM_END + 1) if n not in titles]
    empty: List[int] = []
    for n, info in titles.items():
        if not info["commentary"].strip("()"):
            empty.append(n)
    if missing:
        print(f"WARNING: missing title blocks for: {missing}")
    if empty:
        print(f"WARNING: empty commentary for: {sorted(empty)}")
    if len(titles) != 100:
        raise RuntimeError(f"Expected 100 titles, got {len(titles)}; missing={missing}")
    return titles


def build_heading_aliases(titles: Dict[int, Dict[str, str]]) -> Dict[int, List[str]]:
    pathigams: Dict[str, Dict[str, Any]] = {}
    for pasuram_number, info in titles.items():
        code = info["pathigam_code"]
        bucket = pathigams.setdefault(code, {"short_name": info["short_name"], "numbers": []})
        bucket["numbers"].append(pasuram_number)
    short_names = [meta["short_name"] for meta in pathigams.values()]
    translations = transliterate_with_public_html_script(
        short_names,
        ROOT / "public_html" / "transliterateGPT.py",
        Path("poc/cache/transliterate_gpt_dict.json"),
        Path("poc/output/transliterate_pathigam_headings_patthu8.xlsx"),
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
            f"{code} {tamil}",
            f"{code}–{tamil}",
            f"{code}-{eng_compact}",
            tamil,
            eng,
        ]
        print(f"{code}: {aliases[0]} | {aliases[1]}")
        for n in meta["numbers"]:
            aliases_by_pasuram[n] = aliases
    return aliases_by_pasuram


def apply_to_json(titles: Dict[int, Dict[str, str]], json_path: Path) -> int:
    if not json_path.exists():
        print(f"JSON not found yet: {json_path}")
        return 0
    records = json.loads(json_path.read_text(encoding="utf-8"))
    aliases = build_heading_aliases(titles)
    updated = 0
    for row in records:
        n = int(row["PasuramNumber"])
        info = titles.get(n)
        if not info:
            continue
        row["Title"] = info["title"]
        similar = str(row.get("SimilarWords") or "")
        for alias in aliases.get(n, []):
            if alias and alias not in similar:
                similar = f"{similar},{alias}" if similar else alias
        row["SimilarWords"] = similar
        updated += 1
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return updated


def apply_to_db(titles: Dict[int, Dict[str, str]], config_path: Path) -> int:
    config = load_config(str(config_path))
    db = config.database
    aliases = build_heading_aliases(titles)
    conn = mysql.connector.connect(
        host=db.host, port=db.port, user=db.user, password=db.password, database=db.database
    )
    cur = conn.cursor()
    updated = 0
    try:
        for n, info in sorted(titles.items()):
            cur.execute(
                f"SELECT SimilarWords FROM {db.table} "
                f"WHERE PasuramNumber=%s AND Prabandham='பெரிய திருமொழி' LIMIT 1",
                (n,),
            )
            row = cur.fetchone()
            similar = (row[0] if row else "") or ""
            for alias in aliases.get(n, []):
                if alias and alias not in similar:
                    similar = f"{similar},{alias}" if similar else alias
            cur.execute(
                f"""
                UPDATE {db.table}
                SET Title=%s, SimilarWords=%s
                WHERE PasuramNumber=%s AND Prabandham='பெரிய திருமொழி'
                """,
                (info["title"], similar, n),
            )
            updated += cur.rowcount
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return updated


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
        json.dumps({str(k): v for k, v in titles.items()}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Parsed {len(titles)} titles → {args.titles_json}")
    for n in (1648, 1649, 1658, 1688, 1747):
        preview = titles[n]["title"][:200].replace("\n", " | ") if titles[n]["title"] else "(empty)"
        print(n, preview)
    if args.dry_run and not args.apply:
        print("Dry run only.")
        return
    if not args.apply:
        print("Use --apply to update POC JSON + DB.")
        return
    print(f"JSON rows updated: {apply_to_json(titles, Path(args.poc_json))}")
    print(f"DB rows updated: {apply_to_db(titles, Path(args.config))}")


if __name__ == "__main__":
    main()
