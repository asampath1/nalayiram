#!/usr/bin/env python3
"""Apply திருவாய்மொழி Titles from a tidley விளக்க உரை page → POC.

Title format:
  (5-8–ஆரா அமுதே) - (first *** paragraph)

Modes:
  before-verse      *** text before the pasuram (3-3 / 4-10)
  after-padhavurai  first *** para after the padhavurai table (5-8)

POC only. Does not touch SimilarWords, padham, or verse text.
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

STAR_RE = re.compile(r"(?:\\?\*){3}-\s*")
STAR_LINE_RE = re.compile(r"(?m)^\s*\*{3}\s*[-–—]?\s*")
SUFFIX_RE = re.compile(
    r"[–—-]\s*(\d+)-(\d+)-(\d+)\s*[–—-]?",
)
NBSP_RE = re.compile(r"[\u00a0\u2007\u202f]")
LEAD_DASH_RE = re.compile(r"^[–—\-]+\s*")
VERSE_LINES = 4
PRABANDHAM = "திருவாய்மொழி"


def normalize_ws_line(line: str) -> str:
    line = NBSP_RE.sub(" ", line)
    return re.sub(r"[ \t]+", " ", line).strip()


def commentary_text(raw: str) -> str:
    raw = STAR_RE.sub("", raw, count=1) if STAR_RE.match(raw.lstrip()) else raw
    lines = [normalize_ws_line(ln) for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return ""
    text = "\n".join(lines)
    text = LEAD_DASH_RE.sub("", text).strip()
    return text


def extract_commentaries(raw: str, patthu: int, pathigam: int) -> Dict[int, str]:
    raw = raw.replace("\\*", "*")
    parts = STAR_RE.split(raw)
    found: Dict[int, str] = {}
    for chunk in parts[1:]:
        match = SUFFIX_RE.search(chunk)
        if not match:
            continue
        if int(match.group(1)) != patthu or int(match.group(2)) != pathigam:
            continue
        verse_idx = int(match.group(3))
        before_suffix = chunk[: match.start()]
        paragraphs = [
            "\n".join(
                ln for ln in (normalize_ws_line(x) for x in para.splitlines()) if ln
            )
            for para in re.split(r"\n\s*\n", before_suffix)
        ]
        paragraphs = [p for p in paragraphs if p]
        if len(paragraphs) >= 2:
            body = commentary_text("\n".join(paragraphs[:-1]))
        else:
            lines = [normalize_ws_line(ln) for ln in before_suffix.splitlines()]
            lines = [ln for ln in lines if ln]
            if len(lines) <= VERSE_LINES:
                continue
            body = commentary_text("\n".join(lines[:-VERSE_LINES]))
        if verse_idx not in found:
            found[verse_idx] = body
    return found


def _first_paragraph(text: str) -> str:
    text = LEAD_DASH_RE.sub("", text.strip())
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        return ""
    lines = [normalize_ws_line(ln) for ln in paras[0].splitlines()]
    return "\n".join(ln for ln in lines if ln).strip()


def extract_after_padhavurai(raw: str, patthu: int, pathigam: int) -> Dict[int, str]:
    """First *** paragraph after each padhavurai.

    A leftover *** sitting immediately before the next verse is assigned to
    that next verse (tidley 5-8 layout for 7, 9, 10, 11).
    """
    raw = raw.replace("\\*", "*")
    suffixes = [
        m
        for m in SUFFIX_RE.finditer(raw)
        if int(m.group(1)) == patthu and int(m.group(2)) == pathigam
    ]
    found: Dict[int, str] = {}
    for index, match in enumerate(suffixes):
        verse_idx = int(match.group(3))
        end = suffixes[index + 1].start() if index + 1 < len(suffixes) else len(raw)
        gap = raw[match.end() : end]
        stars = list(STAR_LINE_RE.finditer(gap))
        if not stars:
            continue
        owned: List[re.Match[str]] = []
        leftover: List[re.Match[str]] = []
        has_next = index + 1 < len(suffixes)
        for star in stars:
            rest = gap[star.end() :]
            paras = [p for p in re.split(r"\n\s*\n", rest) if p.strip()]
            commentary_paras = paras[:-1] if has_next and paras else paras
            if has_next and len(commentary_paras) <= 2:
                leftover.append(star)
            else:
                owned.append(star)
        if owned and verse_idx not in found:
            found[verse_idx] = _first_paragraph(gap[owned[0].end() :])
        if leftover and index + 1 < len(suffixes):
            next_idx = int(suffixes[index + 1].group(3))
            if next_idx not in found:
                found[next_idx] = _first_paragraph(gap[leftover[-1].end() :])
    return found


def _paras(text: str) -> List[str]:
    out: List[str] = []
    for para in re.split(r"\n\s*\n", text):
        lines = [normalize_ws_line(ln) for ln in para.splitlines()]
        joined = "\n".join(ln for ln in lines if ln).strip()
        if joined:
            out.append(joined)
    return out


def _before_verse_body(text: str) -> str:
    """All commentary paragraphs; last paragraph is the pasuram."""
    paras = _paras(text)
    if len(paras) >= 2:
        return commentary_text("\n\n".join(paras[:-1]))
    return ""


AVATH_START_RE = re.compile(r"^\([^)\n]{1,80}\)")


def _bare_avatharikai(gap: str, *, allow_two_para: bool = False) -> str:
    """`(விளி)` paragraph immediately before the verse when *** is missing."""
    paras = _paras(gap)
    if len(paras) < 2:
        return ""
    if paras[-2].startswith("("):
        return commentary_text(paras[-2])
    if allow_two_para and len(paras) >= 3 and paras[-3].startswith("("):
        return commentary_text("\n\n".join(paras[-3:-1]))
    return ""


def _after_table_first_para(gap: str) -> str:
    """First prose paragraph after the padhavurai table, before the next ***."""
    star = STAR_LINE_RE.search(gap)
    region = gap[: star.start()] if star else gap
    past_table = False
    collected: List[str] = []
    for line in region.splitlines():
        stripped = normalize_ws_line(line)
        if stripped.startswith("பதவுரை"):
            past_table = False
            continue
        if stripped.startswith("|"):
            past_table = True
            continue
        if stripped.startswith("—") or stripped.startswith("---"):
            if collected:
                break
            continue
        if past_table and stripped:
            collected.append(line)
    if not collected:
        return ""
    return _first_paragraph("\n".join(collected))


def extract_hybrid(raw: str, patthu: int, pathigam: int) -> Dict[int, str]:
    """Mix of 4-10 (*** before verse, all paras) and 5-8 (*** after table, first para)."""
    raw = raw.replace("\\*", "*")
    suffixes = [
        m
        for m in SUFFIX_RE.finditer(raw)
        if int(m.group(1)) == patthu and int(m.group(2)) == pathigam
    ]
    found: Dict[int, str] = {}

    if suffixes:
        pre = raw[: suffixes[0].start()]
        first_idx = int(suffixes[0].group(3))
        stars = list(STAR_LINE_RE.finditer(pre))
        if stars:
            found[first_idx] = _before_verse_body(pre[stars[-1].end() :])
        else:
            body = _bare_avatharikai(pre, allow_two_para=True)
            if body:
                found[first_idx] = body

    for index, match in enumerate(suffixes):
        verse_idx = int(match.group(3))
        has_next = index + 1 < len(suffixes)
        end = suffixes[index + 1].start() if has_next else len(raw)
        gap = raw[match.end() : end]
        stars = list(STAR_LINE_RE.finditer(gap))
        owned: List[re.Match[str]] = []
        leftover: List[re.Match[str]] = []
        for star in stars:
            rest = gap[star.end() :]
            paras = _paras(rest)
            commentary_paras = paras[:-1] if has_next and paras else paras
            if has_next and len(commentary_paras) <= 5:
                leftover.append(star)
            else:
                owned.append(star)
        if owned and verse_idx not in found:
            found[verse_idx] = _first_paragraph(gap[owned[0].end() :])
            extra = owned[1:] + leftover
        else:
            extra = owned + leftover
        if extra and has_next:
            next_idx = int(suffixes[index + 1].group(3))
            if next_idx not in found:
                found[next_idx] = _before_verse_body(gap[extra[-1].end() :])
        if verse_idx not in found:
            body = _after_table_first_para(gap)
            if body:
                found[verse_idx] = body
        if has_next:
            next_idx = int(suffixes[index + 1].group(3))
            if next_idx not in found:
                body = _bare_avatharikai(gap)
                if body:
                    found[next_idx] = body
    return found


def build_title(code: str, short_name: str, commentary: str) -> str:
    body = commentary.strip()
    if body and not (body.startswith("(") and body.endswith(")")):
        body = f"({body})"
    elif not body:
        body = "()"
    return f"({code}–{short_name}) - {body}"


def parse_titles(
    source: Path,
    *,
    code: str,
    short_name: str,
    start: int,
    end: int,
    mode: str = "before-verse",
) -> Dict[int, Dict[str, str]]:
    patthu, pathigam = (int(x) for x in code.split("-"))
    expected = end - start + 1
    raw = source.read_text(encoding="utf-8")
    if mode == "after-padhavurai":
        commentaries = extract_after_padhavurai(raw, patthu, pathigam)
    elif mode == "hybrid":
        commentaries = extract_hybrid(raw, patthu, pathigam)
    else:
        commentaries = extract_commentaries(raw, patthu, pathigam)
    titles: Dict[int, Dict[str, str]] = {}
    missing: List[int] = []
    for offset, pasuram_number in enumerate(range(start, end + 1)):
        verse_idx = offset + 1
        commentary = commentaries.get(verse_idx, "")
        if not commentary:
            missing.append(pasuram_number)
        titles[pasuram_number] = {
            "pathigam_code": code,
            "short_name": short_name,
            "suffix": f"{code}-{verse_idx}",
            "commentary": commentary,
            "title": build_title(code, short_name, commentary),
        }
    if missing:
        raise RuntimeError(
            f"Missing *** commentary for {code}: {missing}; "
            f"found verses {sorted(commentaries)}"
        )
    if len(titles) != expected:
        raise RuntimeError(f"Expected {expected} titles, got {len(titles)}")
    return titles


def apply_to_db(titles: Dict[int, Dict[str, str]], config_path: Path) -> int:
    config = load_config(str(config_path))
    db = config.database
    conn = mysql.connector.connect(
        host=db.host, port=db.port, user=db.user, password=db.password, database=db.database
    )
    cur = conn.cursor()
    updated = 0
    try:
        for n, info in sorted(titles.items()):
            cur.execute(
                f"""
                UPDATE {db.table}
                SET Title=%s
                WHERE PasuramNumber=%s AND Prabandham=%s
                """,
                (info["title"], n, PRABANDHAM),
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
    parser.add_argument("--source", required=True)
    parser.add_argument("--code", required=True, help="Pathigam code, e.g. 5-8")
    parser.add_argument("--short-name", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--titles-json", default="")
    parser.add_argument(
        "--mode",
        choices=("before-verse", "after-padhavurai", "hybrid"),
        default="before-verse",
        help="before-verse: *** text before the pasuram (3-3/4-10). "
        "after-padhavurai: first *** para after the padhavurai table (5-8). "
        "hybrid: both layouts in one page (6-10 / 7-2 / 7-4).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    titles = parse_titles(
        Path(args.source),
        code=args.code,
        short_name=args.short_name,
        start=args.start,
        end=args.end,
        mode=args.mode,
    )
    out = Path(args.titles_json) if args.titles_json else (
        ROOT / "poc" / "output" / f"thiruvaimozhi_{args.code.replace('-', '_')}_titles.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({str(k): v for k, v in titles.items()}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Parsed {len(titles)} titles → {out}")
    for n, info in sorted(titles.items()):
        preview = info["title"].replace("\n", " | ")
        print(f"{n} {info['suffix']}: {preview[:240]}")
    if args.dry_run and not args.apply:
        print("Dry run only.")
        return
    if not args.apply:
        print("Use --apply to update POC DB.")
        return
    print(f"DB rows updated: {apply_to_db(titles, Path(args.config))}")


if __name__ == "__main__":
    main()
