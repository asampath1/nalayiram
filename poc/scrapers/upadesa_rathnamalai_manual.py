#!/usr/bin/env python3
"""Parse உபதேச ரத்னமாலை from poc/pasuram.txt (Title / Pasuram / Simple Explanation)."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
import sys

sys.path.insert(0, str(ROOT))

from poc.acharya_thaniyan_numbers import UPADESA_THANIYAN_PATTU

PRABANDHAM = "உபதேச ரத்னமாலை"
PRABANDHAM_THANIYAN = "உபதேச ரத்னமாலை - தனியன்"
ALZWAR = "ஸ்ரீ மணவாள மாமுனிகள்"
ALZWAR_THANIYAN = "ஸ்ரீ கோயில் கந்தானை அண்ணன்"
ALZWAR_74 = "ஸ்ரீ எறும்பி அப்பா"
PASURAM_START = 3885  # pattu 1
PASURAM_SHARED_73_74 = 3957
EXPECTED_PATTUS = 74
THANIYAN_PATTU = 50
DEFAULT_SOURCE = ROOT / "poc" / "pasuram.txt"

SEP_RE = re.compile(r"^[\s—–\-−_]{10,}\s*$")
VERSE_TAIL_RE = re.compile(r"[.—–\-−—]+\s*(\d+)\s*[-—–.]*\s*$")
TAG_RE = re.compile(r"^<(?:Title|pasuram|Simple Explanation)>\s*$", re.I)
INSTRUCTION_RE = re.compile(
    r"Continue like above|Format below|Note: Not always|Prabhandham name|Written by|Rendered by",
    re.I,
)


@dataclass
class Section:
    pattu_number: int
    pasuram_number: int
    pasuram: str
    title: str
    meaning: str
    alzwar: str
    prabandham: str
    is_thaniyan: bool = False


def _clean_lines(text: str) -> list[str]:
    return [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]


def _strip_tags_and_noise(lines: list[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        if TAG_RE.match(ln.strip()):
            continue
        if INSTRUCTION_RE.search(ln) and "உபதேச" not in ln[:20]:
            # keep Tamil content; drop English instruction lines
            if re.search(r"[A-Za-z]{4,}", ln) and not re.search(r"[\u0b80-\u0bff]", ln):
                continue
        out.append(ln)
    return out


def _split_sep_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    cur: list[str] = []
    for ln in lines:
        if SEP_RE.match(ln):
            if any(x.strip() for x in cur):
                blocks.append(cur)
            cur = []
            continue
        cur.append(ln)
    if any(x.strip() for x in cur):
        blocks.append(cur)
    return blocks


def _pasuram_number_for_pattu(pattu: int) -> int:
    if pattu <= 72:
        return PASURAM_START + pattu - 1
    if pattu in (73, 74):
        return PASURAM_SHARED_73_74
    raise ValueError(f"Unexpected pattu {pattu}")


def _parse_numbered_block(lines: list[str]) -> Section | None:
    lines = _strip_tags_and_noise(lines)
    verse_idx = None
    verse_num = None
    for i, ln in enumerate(lines):
        m = VERSE_TAIL_RE.search(ln.strip())
        if m:
            verse_idx = i
            verse_num = int(m.group(1))
    if verse_idx is None or verse_num is None:
        return None
    if not (1 <= verse_num <= 73):
        return None

    start = verse_idx
    while start > 0 and lines[start - 1].strip():
        start -= 1

    pasuram_lines = list(lines[start : verse_idx + 1])
    pasuram_lines[-1] = VERSE_TAIL_RE.sub("", pasuram_lines[-1]).rstrip(" -—–−.")
    pasuram = "\n".join(p.strip() for p in pasuram_lines if p.strip()).strip()

    title = "\n".join(ln.strip() for ln in lines[:start] if ln.strip()).strip()
    # Drop leftover English scaffolding in title
    if title.lower().startswith("example"):
        title = ""
    meaning = "\n".join(ln.strip() for ln in lines[verse_idx + 1 :] if ln.strip()).strip()

    return Section(
        pattu_number=verse_num,
        pasuram_number=_pasuram_number_for_pattu(verse_num),
        pasuram=pasuram,
        title=title,
        meaning=meaning,
        alzwar=ALZWAR,
        prabandham=PRABANDHAM,
    )


def _parse_thaniyan(text: str) -> Section:
    # From "தனியன்" header through its explanation, before main prabandham header.
    m = re.search(
        r"ரத்னமாலை\s*[–—\-]\s*தனியன்\s*(.*?)\n\s*Prabhandham name\s*-\s*உபதேச ரத்னமாலை\s*$",
        text,
        re.S | re.M,
    )
    if not m:
        raise RuntimeError("Could not locate thaniyan block in pasuram.txt")
    block = m.group(1)
    # Drop "Rendered by ..." line
    lines = []
    for ln in _clean_lines(block):
        if ln.strip().startswith("Rendered by"):
            continue
        if SEP_RE.match(ln):
            continue
        lines.append(ln)
    # First non-empty run = pasuram (until blank after verse), rest = meaning
    non_empty_runs: list[list[str]] = []
    cur: list[str] = []
    for ln in lines:
        if ln.strip():
            cur.append(ln.strip())
        elif cur:
            non_empty_runs.append(cur)
            cur = []
    if cur:
        non_empty_runs.append(cur)
    if len(non_empty_runs) < 2:
        raise RuntimeError(f"Thaniyan expected verse + meaning, got {len(non_empty_runs)} runs")
    pasuram = "\n".join(non_empty_runs[0]).rstrip(" –—-")
    meaning = "\n".join(x for run in non_empty_runs[1:] for x in run)
    return Section(
        pattu_number=THANIYAN_PATTU,
        pasuram_number=0,
        pasuram=pasuram,
        title="",
        meaning=meaning,
        alzwar=ALZWAR_THANIYAN,
        prabandham=PRABANDHAM_THANIYAN,
        is_thaniyan=True,
    )


def _parse_verse_74(text: str) -> Section:
    m = re.search(
        r"எறும்பி அப்பா அருளிச் செய்தது\s*(.*)\Z",
        text,
        re.S,
    )
    if not m:
        raise RuntimeError("Could not locate verse 74 (எறும்பி அப்பா) block")
    lines = [ln.strip() for ln in _clean_lines(m.group(1)) if not SEP_RE.match(ln)]
    # Pasuram until blank or line starting with "74 "
    pasuram_lines: list[str] = []
    meaning_lines: list[str] = []
    in_meaning = False
    for ln in lines:
        if not ln:
            if pasuram_lines:
                in_meaning = True
            continue
        if re.match(r"^74\b", ln) or in_meaning:
            in_meaning = True
            meaning_lines.append(ln)
            continue
        pasuram_lines.append(ln.rstrip(" –—-"))
    if not pasuram_lines:
        raise RuntimeError("Verse 74 pasuram text missing")
    return Section(
        pattu_number=74,
        pasuram_number=PASURAM_SHARED_73_74,
        pasuram="\n".join(pasuram_lines),
        title="எறும்பி அப்பா அருளிச் செய்தது",
        meaning="\n".join(meaning_lines),
        alzwar=ALZWAR_74,
        prabandham=PRABANDHAM,
    )


def parse_source(path: Path = DEFAULT_SOURCE) -> list[Section]:
    text = path.read_text(encoding="utf-8")
    thaniyan = _parse_thaniyan(text)

    # Main body: from a line that is exactly <Title> (not the format mention) through verse 73.
    body_m = re.search(
        r"(?m)^<Title>\s*\n(.*?)(?=எறும்பி அப்பா அருளிச் செய்தது)",
        text,
        re.S,
    )
    if not body_m:
        raise RuntimeError("Could not locate main verse body starting at <Title>")
    body_lines = _clean_lines(body_m.group(1))
    filtered: list[str] = []
    for ln in body_lines:
        if ln.strip().startswith("Continue like above"):
            continue
        filtered.append(ln)

    sections_by_pattu: dict[int, Section] = {}
    for block in _split_sep_blocks(filtered):
        sec = _parse_numbered_block(block)
        if sec is None:
            continue
        sections_by_pattu[sec.pattu_number] = sec

    missing = [n for n in range(1, 74) if n not in sections_by_pattu]
    if missing:
        raise RuntimeError(f"Missing numbered verses: {missing}")

    verse74 = _parse_verse_74(text)
    ordered = [thaniyan] + [sections_by_pattu[n] for n in range(1, 74)] + [verse74]
    return ordered


def sections_to_records(sections: list[Section]) -> list[dict]:
    records: list[dict] = []
    prabandham_title = f"{PRABANDHAM}, Upadesa Rathnamalai"
    for sec in sections:
        title_for_similar = (
            f"{PRABANDHAM_THANIYAN}, Upadesa Rathnamalai Thaniyan"
            if sec.is_thaniyan
            else prabandham_title
        )
        records.append(
            {
                "Prabandham": sec.prabandham,
                "PasuramNumber": sec.pasuram_number,
                "Pasuram": sec.pasuram,
                "PattuNumber": sec.pattu_number,
                "Word": "",
                "Meaning": sec.meaning,
                "Padham": "",
                "PadhamNumber": 1,
                "Alzwar": sec.alzwar,
                "Title": sec.title,
                "NithyaanusandhamIndex": None,
                "PrabandhamTitle": title_for_similar,
            }
        )
    return records


def summarize_sections(sections: list[Section]) -> str:
    main = [s for s in sections if not s.is_thaniyan]
    with_title = sum(1 for s in main if s.title)
    with_meaning = sum(1 for s in main if s.meaning)
    lines = [
        f"Sections: {len(sections)} (1 thaniyan + {len(main)} verses)",
        f"With Title: {with_title}/{len(main)}; with Meaning: {with_meaning}/{len(main)}",
        f"PasuramNumbers: {PASURAM_START}-{PASURAM_SHARED_73_74} "
        f"(73+74 share {PASURAM_SHARED_73_74})",
    ]
    for s in sections[:3]:
        lines.append(
            f"  Pattu {s.pattu_number} PN={s.pasuram_number}: "
            f"title_len={len(s.title)} meaning_len={len(s.meaning)} "
            f"pasuram={s.pasuram.splitlines()[0][:50]!r}..."
        )
    s73 = next(s for s in sections if s.pattu_number == 73)
    s74 = next(s for s in sections if s.pattu_number == 74)
    lines.append(f"  Pattu 73 PN={s73.pasuram_number} alzwar={s73.alzwar}")
    lines.append(f"  Pattu 74 PN={s74.pasuram_number} alzwar={s74.alzwar} title={s74.title!r}")
    return "\n".join(lines)


def write_review_csv(sections: list[Section], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["PattuNumber", "PasuramNumber", "Alzwar", "Title", "Pasuram", "Meaning"]
        )
        for s in sections:
            w.writerow(
                [
                    s.pattu_number,
                    s.pasuram_number,
                    s.alzwar,
                    s.title,
                    s.pasuram,
                    s.meaning,
                ]
            )


if __name__ == "__main__":
    secs = parse_source()
    print(summarize_sections(secs))
