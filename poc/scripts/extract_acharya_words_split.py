#!/usr/bin/env python3
"""Extract recitation-split verses from an acharya.org Tamil PDF.

Older pathigams are TAB-encoded (pdftotext + tab2unicode). Later ones embed
Nirmala UI with a swapped ToUnicode cmap; those are decoded from TTF glyph
ids, then Tamil prefix vowels (ெ ே ை) are moved from visual to logical order.

Writes a numbered block file for apply_thirupallandu_words_split.py.
Leading PDF ** becomes ● (recite twice). Mid-verse * is kept.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tamil.txt2unicode import tab2unicode  # type: ignore

CIRCLE = "● "
PREFIX_VOWELS = {0xBC6, 0xBC7, 0xBC8}  # ெ ே ை
TAMIL_CONSONANTS = set(range(0xB95, 0xBB6))


def looks_tab(line: str) -> bool:
    if re.search(r"[\u0b80-\u0bff]", line) and not re.search(
        r"[îðñõöùúûüýþª«¬¯°±²³´µ¶·¸¹º»¼½¾¿À-ÿ]", line
    ):
        return False
    return bool(re.search(r"[îðñõöùúûüýþª«¬¯°±²³´µ¶·¸¹º»¼½¾¿À-ÿ¢]", line))


def pdf_to_unicode(pdf: Path) -> str:
    raw = subprocess.check_output(
        ["pdftotext", "-raw", str(pdf), "-"], text=True, encoding="utf-8"
    )
    if any(looks_tab(line) for line in raw.splitlines()):
        lines = [tab2unicode(line) if looks_tab(line) else line for line in raw.splitlines()]
        text = "\n".join(lines).replace("௬", "கூ")
        # tab2unicode leftover pulli ¤: ªî÷¤ → தெளி (1-4 verse 58)
        text = text.replace("தௌ¤வுறா", "தெளிவுறா")
        leftover = [ln for ln in text.splitlines() if "¤" in ln]
        if leftover:
            raise SystemExit("TAB leftover ¤ after convert:\n" + "\n".join(leftover[:8]))
        return text
    return nirmala_pdf_to_unicode(pdf)


def _font_gid2u(doc, xref: int) -> dict[int, int]:
    import pymupdf

    data = doc.extract_font(xref)[3]
    font = pymupdf.Font(fontbuffer=data)
    try:
        cps = list(font.valid_codepoints() or [])
    except Exception:
        cps = []
    if not cps:
        cps = list(range(32, 256)) + list(range(0xB80, 0xC00))
    gid2u: dict[int, int] = {}
    for u in cps:
        g = font.has_glyph(u)
        if g and g not in gid2u:
            gid2u[g] = u
    return gid2u


def _visual_to_logical(s: str) -> str:
    chars = list(s)
    out: list[str] = []
    i = 0
    while i < len(chars):
        o = ord(chars[i])
        if (
            o in PREFIX_VOWELS
            and i + 1 < len(chars)
            and ord(chars[i + 1]) in TAMIL_CONSONANTS
        ):
            out.append(chars[i + 1])
            out.append(chars[i])
            i += 2
            continue
        out.append(chars[i])
        i += 1
    return unicodedata.normalize("NFC", "".join(out))


def nirmala_pdf_to_unicode(pdf: Path) -> str:
    """Decode Nirmala-embedded Acharya PDFs via TTF cmap (ToUnicode is swapped)."""
    import pymupdf

    doc = pymupdf.open(pdf)
    maps: dict[str, dict[int, int]] = {}
    for page in doc:
        for fontinfo in page.get_fonts():
            xref, _ext, typ, name = fontinfo[0], fontinfo[1], fontinfo[2], fontinfo[3]
            if "Nirmala" not in name or typ != "Type0":
                continue
            short = name.split("+")[-1]
            key = "NirmalaUI-Bold" if "Bold" in short else "NirmalaUI"
            if key not in maps:
                maps[key] = _font_gid2u(doc, xref)

    lines: list[str] = []
    for page in doc:
        spans: list[tuple[float, float, float, str]] = []
        for item in page.get_texttrace():
            font = item["font"]
            gid2u = maps.get(font)
            if gid2u is None and "Nirmala" not in font:
                continue
            if gid2u is None:
                gid2u = {}
            chars: list[str] = []
            for c in item.get("chars") or []:
                ucs, gid = c[0], c[1]
                u = gid2u.get(gid, ucs if gid < 0 else ucs)
                if u >= 32:
                    chars.append(chr(u))
            text = "".join(chars)
            if not text.strip():
                continue
            x0, y0, x1, _y1 = item["bbox"]
            spans.append((y0, x0, x1, text))
        spans.sort(key=lambda s: (round(s[0], 1), s[1]))
        buf: list[str] = []
        cur_y: float | None = None
        prev_x1 = 0.0
        for y0, x0, x1, text in spans:
            if cur_y is None or abs(y0 - cur_y) > 3:
                if buf:
                    lines.append(_visual_to_logical("".join(buf)).strip())
                buf = [text]
                cur_y = y0
            else:
                if buf and x0 > prev_x1 + 1.2 and not buf[-1].endswith(" ") and not text.startswith(" "):
                    buf.append(" ")
                buf.append(text)
            prev_x1 = x1
        if buf:
            lines.append(_visual_to_logical("".join(buf)).strip())
    doc.close()
    return "\n".join(ln for ln in lines if ln)


def strip_page_furniture(text: str) -> str:
    text = re.sub(r"நாலாயிர திவ்யப்ரபந்தம்.*", "", text)
    text = re.sub(r"ஸ்ரீமதத இராமாநுஜாய நம:", "", text)
    text = re.sub(r"ஸ்ரீமதே இராமாநுஜாய நம:", "", text)
    text = re.sub(r"ஆழ்வார் எம்பபருமானார்.*", "", text)
    text = re.sub(r"ஆழ்வார் எம்பெருமானார்.*", "", text)
    text = re.sub(r"http://acharya\.org", "", text)
    return text


def clean_verse(chunk: str, leading_double_star: bool) -> str:
    chunk = chunk.strip()
    had_lead = bool(re.match(r"^\*\*\s*", chunk)) or leading_double_star
    chunk = re.sub(r"^\*\*\s*", "", chunk)
    chunk = re.sub(r"\*\*", "\n", chunk)
    out = []
    for line in chunk.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            out.append(line)
    text = "\n".join(out)
    if had_lead and not text.startswith(CIRCLE.strip()):
        text = CIRCLE + text
    return text


def split_numbered_verses(body: str, pdf_count: int) -> dict[int, str]:
    """Split on a trailing 1..pdf_count at end of a line."""
    pattern = r"(?m)\s+(" + "|".join(str(n) for n in range(pdf_count, 0, -1)) + r")\s*$"
    # longer numbers first so 10 is not eaten as 1 + 0
    pattern = r"(?m)[ \t]+(" + "|".join(
        str(n) for n in range(pdf_count, 0, -1)
    ) + r")\s*$"
    parts = re.split(pattern, body)
    verses: dict[int, str] = {}
    i = 0
    while i + 1 < len(parts):
        chunk, num_s = parts[i], parts[i + 1]
        n = int(num_s)
        leading = bool(re.match(r"(?s)^\s*\*\*", chunk))
        verses[n] = clean_verse(chunk, leading)
        i += 2
    return verses


def write_keyed(path: Path, verses: dict[int, str], pasuram_start: int, count: int) -> None:
    expected = set(range(1, count + 1))
    if set(verses) != expected:
        raise SystemExit(f"PDF verse keys {sorted(verses)} != {sorted(expected)}")
    blocks = []
    for i in range(count):
        pn = pasuram_start + i
        blocks.append(f"{pn}\n{verses[i + 1]}")
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"wrote {path} pasuram {pasuram_start}–{pasuram_start + count - 1}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--start-marker", required=True, help="Substring where pasuram body begins")
    p.add_argument("--end-marker", default="அடிவரவு")
    p.add_argument("--pdf-count", type=int, required=True)
    p.add_argument("--pasuram-start", type=int, required=True)
    args = p.parse_args()

    text = strip_page_furniture(pdf_to_unicode(Path(args.pdf)))
    start = text.find(args.start_marker)
    if start < 0:
        raise SystemExit(f"start marker not found: {args.start_marker!r}")
    star = text.rfind("**", max(0, start - 12), start)
    if star >= 0:
        start = star
    end = text.find(args.end_marker, start)
    if end < 0:
        for alt in ("பெரியாழ்வார் திருவடிகளே", "திருவடிகளே சரணம்", "திருவடிகளே"):
            end = text.find(alt, start + len(args.start_marker))
            if end >= 0:
                break
    if end < 0:
        raise SystemExit("end marker not found")
    body = text[start:end]
    verses = split_numbered_verses(body, args.pdf_count)
    write_keyed(Path(args.out), verses, args.pasuram_start, args.pdf_count)
    for n in range(1, args.pdf_count + 1):
        first = verses[n].splitlines()[0]
        print(f"  pdf {n} -> {args.pasuram_start + n - 1}: {first}")


if __name__ == "__main__":
    main()
