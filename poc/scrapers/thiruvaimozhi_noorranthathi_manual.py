#!/usr/bin/env python3
"""Parse திருவாய்மொழி நூற்றந்தாதி from poc/pasuram.txt (Title / Pasuram / Meaning)."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
import sys

sys.path.insert(0, str(ROOT))

from poc.acharya_thaniyan_numbers import (
    LEGACY_THANIYAN_PASURAM_NUMBERS,
    THIRUVAIMOZHI_NOORRANTHATHI_THANIYAN_PATTUS,
    THIRUVAIMOZHI_NOORRANTHATHI_THANIYAN_PRABANDHAMS,
    thiruvaimozhi_thaniyan_pattu,
)

PRABANDHAM = "திருவாய்மொழி நூற்றந்தாதி"
ALZWAR = "ஸ்ரீ மணவாள மாமுனிகள்"
ALZWAR_THANIYAN = ""
PASURAM_START = 3958
PASURAM_END = 4057
EXPECTED_PATTUS = 100
THANIYAN_PATTUS = THIRUVAIMOZHI_NOORRANTHATHI_THANIYAN_PATTUS
LEGACY_THANIYAN_PRABANDHAMS = (
    "தனியன்",
    "திருவாய்மொழி நூற்றந்தாதி - தனியன்",
    "திருவாய்மொழி நூற்றந்தாதி - தனியன்-51",
    "திருவாய்மொழி நூற்றந்தாதி - தனியன்-52",
)
DEFAULT_SOURCE = ROOT / "poc" / "pasuram.txt"


def thaniyan_prabandham(header_index: int) -> str:
    return THIRUVAIMOZHI_NOORRANTHATHI_THANIYAN_PRABANDHAMS[header_index - 1]


def thaniyan_prabandham_names() -> tuple[str, ...]:
    return THIRUVAIMOZHI_NOORRANTHATHI_THANIYAN_PRABANDHAMS

TITLE_LINE_RE = re.compile(r"^(.+? பாசுரம்\.)(.*)$", re.UNICODE)
THANIYAN_HEADER_RE = re.compile(
    r"திருவாய்மொழி நூற்றந்தாதி\s*-\s*தனியன்-(\d+)\s*$"
)
THANIYAN_BLOCK_STOP_RE = re.compile(
    r"^(?:Pasuram Starts|Format\s*$|<(?:Example|Before Pasuram|Pasuram>|/Example)>|முதல் பாசுரம்\.)",
    re.I,
)
BODY_START_RE = re.compile(r"^-{5,}\s*$", re.M)
SKIP_LINE_RE = re.compile(
    r"^(?:<Example>|Title$|Pasuram$|Meaning|Format|Continue|Prabhandham|Alwar|No divyadesam|No Themes|No Padavurai|Pasuram Number|Pasuram Starts|POC Only|Update ReleaseNotes|like this till)",
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


def _pasuram_number_for_pattu(pattu: int) -> int:
    if not (1 <= pattu <= EXPECTED_PATTUS):
        raise ValueError(f"Unexpected pattu {pattu}")
    return PASURAM_START + pattu - 1


def _ordinal_to_pattu(ordinal: str) -> int | None:
    ordinal = ordinal.strip()
    if ordinal == "முதல்":
        return 1
    if ordinal == "நூறாம்":
        return 100

    tens_words = {
        "இருபது": 20,
        "முப்பது": 30,
        "நாற்பது": 40,
        "ஐம்பது": 50,
        "அறுபது": 60,
        "எழுபது": 70,
        "எண்பது": 80,
        "தொண்ணூறு": 90,
    }
    unit_words = {
        "ஒன்று": 1,
        "இரண்டு": 2,
        "மூன்று": 3,
        "நான்கு": 4,
        "ஐந்து": 5,
        "ஆறு": 6,
        "ஏழு": 7,
        "எட்டு": 8,
        "ஒன்பது": 9,
    }
    unit_ordinals = {
        "இரண்டாம்": 2,
        "மூன்றாம்": 3,
        "நான்காம்": 4,
        "நாலாம்": 4,
        "ஐந்தாம்": 5,
        "ஆறாம்": 6,
        "ஏழாம்": 7,
        "எட்டாம்": 8,
        "ஒன்பதாம்": 9,
        "பத்தாம்": 10,
        "பதினொன்றாம்": 11,
        "பன்னிரண்டாம்": 12,
        "பதிமூன்றாம்": 13,
        "பதினான்காம்": 14,
        "பதினைந்தாம்": 15,
        "பதினாறாம்": 16,
        "பதினேழாம்": 17,
        "பதினெட்டாம்": 18,
        "பத்தொன்பதாம்": 19,
        "இருபத்தொன்பதாம்": 29,
        "முப்பத்தொன்பதாம்": 39,
        "நாற்பத்தொன்பதாம்": 49,
        "ஐம்பத்தொன்பதாம்": 59,
        "அறுபத்தொன்பதாம்": 69,
        "எழுபத்தொன்பதாம்": 79,
        "எண்பத்தொன்பதாம்": 89,
        "தொண்ணூற்றொன்பதாம்": 99,
    }
    typo_aliases = {
        "இருபத்தஆறாம்": 26,
        "இருப்பத்தெட்டாம்": 28,
        "எண்பத்தோறாம்": 81,
    }
    if ordinal in typo_aliases:
        return typo_aliases[ordinal]
    if ordinal in unit_ordinals:
        return unit_ordinals[ordinal]
    for tens_word, tens_val in tens_words.items():
        if ordinal == f"{tens_word}தாம்":
            return tens_val
        if tens_word.endswith("து") and ordinal == f"{tens_word[:-1]}ாம்":
            return tens_val
    if ordinal.endswith("தாம்"):
        stem = ordinal[: -len("தாம்")]
        for tens_word, tens_val in tens_words.items():
            if stem == tens_word:
                return tens_val
            prefix = tens_word + "த்து"
            if stem.startswith(prefix):
                unit_part = stem[len(prefix) :]
                if unit_part in unit_words:
                    return tens_val + unit_words[unit_part]
            prefix2 = tens_word + "ற்று"
            if stem.startswith(prefix2):
                unit_part = stem[len(prefix2) :]
                if unit_part in unit_words:
                    return tens_val + unit_words[unit_part]
            prefix3 = tens_word + "ற்ற"
            if stem.startswith(prefix3):
                unit_part = stem[len(prefix3) :]
                if unit_part in unit_words:
                    return tens_val + unit_words[unit_part]
    return None


def _pattu_from_title_line(line: str) -> int | None:
    m = TITLE_LINE_RE.match(line.strip())
    if not m:
        return None
    ordinal = m.group(1).replace(" பாசுரம்.", "").strip()
    return _ordinal_to_pattu(ordinal)


def _parse_thaniyan_block(lines: list[str], pattu: int, header_index: int) -> Section:
    pasuram_lines: list[str] = []
    meaning_lines: list[str] = []
    phase = "pasuram"
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            if pasuram_lines and phase == "pasuram":
                phase = "meaning"
            continue
        if stripped.lower() == "meaning":
            phase = "meaning"
            continue
        if phase == "meaning" and THANIYAN_BLOCK_STOP_RE.match(stripped):
            break
        if phase == "pasuram":
            pasuram_lines.append(stripped.rstrip(" –—-"))
        else:
            meaning_lines.append(stripped)
    if not pasuram_lines:
        raise RuntimeError(f"Thaniyan {pattu}: missing pasuram text")
    if not meaning_lines:
        raise RuntimeError(f"Thaniyan {pattu}: missing meaning text")
    return Section(
        pattu_number=pattu,
        pasuram_number=0,
        pasuram="\n".join(pasuram_lines),
        title="",
        meaning="\n".join(meaning_lines),
        alzwar=ALZWAR_THANIYAN,
        prabandham=thaniyan_prabandham(header_index),
        is_thaniyan=True,
    )


def _parse_thaniyans(text: str) -> list[Section]:
    lines = _clean_lines(text)
    thaniyans: list[Section] = []
    i = 0
    while i < len(lines):
        m = THANIYAN_HEADER_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        header_index = int(m.group(1))
        pattu = thiruvaimozhi_thaniyan_pattu(header_index)
        block: list[str] = []
        i += 1
        while i < len(lines):
            if THANIYAN_HEADER_RE.match(lines[i].strip()):
                break
            if BODY_START_RE.match(lines[i]):
                break
            if THANIYAN_BLOCK_STOP_RE.match(lines[i].strip()):
                break
            if TITLE_LINE_RE.match(lines[i].strip()) and "தனியன்" not in lines[i]:
                break
            block.append(lines[i])
            i += 1
        thaniyans.append(_parse_thaniyan_block(block, pattu, header_index))
    thaniyans.sort(key=lambda s: s.pattu_number)
    expected = list(THANIYAN_PATTUS)
    got = [s.pattu_number for s in thaniyans]
    if got != expected:
        raise RuntimeError(f"Expected thaniyans {expected}, got {got}")
    return thaniyans


def _split_main_blocks(body_lines: list[str]) -> list[tuple[int, str, list[str]]]:
    """Return (pattu, title_line, content_lines_after_title) in file order."""
    blocks: list[tuple[int, str, list[str]]] = []
    i = 0
    while i < len(body_lines):
        line = body_lines[i].strip()
        if not line or SKIP_LINE_RE.match(line):
            i += 1
            continue
        m = TITLE_LINE_RE.match(line)
        if not m:
            i += 1
            continue
        pattu = len(blocks) + 1
        parsed = _pattu_from_title_line(line)
        if parsed is not None and parsed != pattu:
            raise RuntimeError(
                f"Title ordinal {parsed} != expected sequential {pattu}: {line[:80]!r}"
            )
        content: list[str] = []
        i += 1
        while i < len(body_lines):
            nxt = body_lines[i].strip()
            if TITLE_LINE_RE.match(nxt):
                break
            content.append(body_lines[i])
            i += 1
        blocks.append((pattu, line, content))
    return blocks


def _parse_verse_block(pattu: int, title: str, content_lines: list[str]) -> Section:
    lines = [ln.strip() for ln in content_lines if ln.strip()]
    if len(lines) < 5:
        raise RuntimeError(
            f"Pattu {pattu}: expected at least 4 pasuram lines + meaning, got {len(lines)}"
        )
    pasuram = "\n".join(lines[:4])
    meaning = "\n".join(lines[4:])
    return Section(
        pattu_number=pattu,
        pasuram_number=_pasuram_number_for_pattu(pattu),
        pasuram=pasuram,
        title=title,
        meaning=meaning,
        alzwar=ALZWAR,
        prabandham=PRABANDHAM,
    )


def parse_source(path: Path = DEFAULT_SOURCE) -> list[Section]:
    text = path.read_text(encoding="utf-8")
    thaniyans = _parse_thaniyans(text)

    body_start = None
    for m in BODY_START_RE.finditer(text):
        body_start = m.end()
    if body_start is None:
        raise RuntimeError("Could not locate main body separator (----------)")

    body_lines = _clean_lines(text[body_start:])
    blocks = _split_main_blocks(body_lines)
    if len(blocks) != EXPECTED_PATTUS:
        raise RuntimeError(f"Expected {EXPECTED_PATTUS} verses, got {len(blocks)}")

    by_pattu: dict[int, Section] = {}
    for pattu, title, content in blocks:
        if pattu in by_pattu:
            raise RuntimeError(f"Duplicate pattu {pattu}")
        by_pattu[pattu] = _parse_verse_block(pattu, title, content)

    missing = [n for n in range(1, EXPECTED_PATTUS + 1) if n not in by_pattu]
    if missing:
        raise RuntimeError(f"Missing pattu numbers: {missing[:10]}{'...' if len(missing) > 10 else ''}")

    main = [by_pattu[n] for n in range(1, EXPECTED_PATTUS + 1)]
    return thaniyans + main


def sections_to_records(sections: list[Section]) -> list[dict]:
    records: list[dict] = []
    prabandham_title = f"{PRABANDHAM}, Thiruvaimozhi Noorranthathi"
    for sec in sections:
        title_for_similar = (
            f"திருவாய்மொழி நூற்றந்தாதி, Thiruvaimozhi Noorranthathi, {sec.prabandham}, Thiruvaimozhi Noorranthathi Thaniyan"
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
    thaniyans = [s for s in sections if s.is_thaniyan]
    main = [s for s in sections if not s.is_thaniyan]
    with_title = sum(1 for s in main if s.title)
    with_meaning = sum(1 for s in main if s.meaning)
    lines = [
        f"Sections: {len(sections)} ({len(thaniyans)} thaniyans + {len(main)} verses)",
        f"With Title: {with_title}/{len(main)}; with Meaning: {with_meaning}/{len(main)}",
        f"PasuramNumbers: {PASURAM_START}-{PASURAM_END}",
        f"Thaniyan PattuNumbers: {[s.pattu_number for s in thaniyans]}",
    ]
    for s in sections[:4]:
        lines.append(
            f"  Pattu {s.pattu_number} PN={s.pasuram_number} thaniyan={s.is_thaniyan}: "
            f"title_len={len(s.title)} meaning_len={len(s.meaning)} "
            f"pasuram={s.pasuram.splitlines()[0][:50]!r}..."
        )
    s100 = main[-1]
    lines.append(
        f"  Pattu 100 PN={s100.pasuram_number}: title={s100.title[:60]!r}..."
    )
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
