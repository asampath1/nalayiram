#!/usr/bin/env python3
"""Build Kannadi-ordered POC release notes HTML from releasenotespoc.html."""

from __future__ import annotations

import argparse
import configparser
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote_plus

import mysql.connector

ROOT = Path(__file__).resolve().parents[2]
# Link catalog for pathigam/prabandham entries (not a public page)
SOURCE_HTML = ROOT / "poc" / "data" / "release_notes_link_source.html"
NITHYA_JSON = ROOT / "poc" / "data" / "nithya_anusandhanam_order.json"
RELEASE_NOTES_PAGE_TITLE = "Nalayira Divya Prabhandham list"

# Environment presets for Kannadi release notes (search script + DB config + outputs)
ENV_PRESETS: dict[str, dict[str, str]] = {
    "poc": {
        "config": str(ROOT / "poc" / "config.ini"),
        "source": str(SOURCE_HTML),
        "search_script": "pocindex.php",
        "output": str(ROOT / "public_html" / "newreleasenotespoc.html"),
    },
    "test": {
        "config": str(ROOT / "poc" / "config.test.ini"),
        "source": str(SOURCE_HTML),
        "search_script": "test1.php",
        "output": str(ROOT / "public_html" / "newreleasenotestest.html"),
    },
    "prod": {
        "config": str(ROOT / "poc" / "config.prod.ini"),
        "source": str(SOURCE_HTML),
        "search_script": "index.php",
        "output": str(ROOT / "public_html" / "newreleasenotes.html"),
    },
}


def rewrite_search_script(html_text: str, search_script: str) -> str:
    """Point all padham search links at the target environment script."""
    for script in ("pocindex.php", "test1.php", "index.php"):
        if script == search_script:
            continue
        html_text = html_text.replace(
            f"https://nalayiram.in/{script}",
            f"https://nalayiram.in/{search_script}",
        )
        html_text = html_text.replace(f'href="{script}', f'href="{search_script}')
    return html_text

LINK_RE = re.compile(
    r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
RANGE_RE = re.compile(r"\((\d+)(?:-(\d+))?\)")
PATHIGAM_RE = re.compile(r"(?:^|\s)(\d+)-(\d+)\s")
PATTU_TITLES = {
    1: "முதல் பத்து",
    2: "இரண்டாம் பத்து",
    3: "மூன்றாம் பத்து",
    4: "நான்காம் பத்து",
    5: "ஐந்தாம் பத்து",
    6: "ஆறாம் பத்து",
    7: "ஏழாம் பத்து",
    8: "எட்டாம் பத்து",
    9: "ஒன்பதாம் பத்து",
    10: "பத்தாம் பத்து",
    11: "பதினொன்றாம் பத்து",
    12: "பன்னிரெண்டாம் பத்து",
    13: "பதிமூன்றாம் பத்து",
    14: "பதினான்காம் பத்து",
}
# HTML label ranges that differ from POC DB (Kannadi vs ingested span)
RANGE_CORRECTIONS: dict[str, tuple[int, int]] = {
    "முதல் திருவந்தாதி": (2082, 2181),
    "இரண்டாம் திருவந்தாதி": (2182, 2281),
}
# Prefixes confirmed loaded even when strict range count differs
LOADED_PREFIX_OVERRIDES = (
    "இரண்டாம் திருவந்தாதி",
    "நண்ணாதார் முறுவலிப்ப",
)


@dataclass(frozen=True)
class LinkEntry:
    href: str
    label: str
    padham_prefix: str
    start: int | None
    end: int | None

    @property
    def sort_key(self) -> tuple[int, str]:
        return (self.start or 99999, self.label)


def pathigam_hundred(label: str) -> int | None:
    match = PATHIGAM_RE.search(label)
    if match:
        return int(match.group(1))
    return None


def pathigam_leading_num(label: str) -> int | None:
    """Pathigam index for நாச்சியார்-style labels: 1-தையொரு … 14-பட்டி."""
    match = re.match(r"^(\d+)-", label.strip())
    if not match:
        return None
    rest = label.strip()[len(match.group(0)) :]
    if rest and rest[0].isdigit():
        return None
    return int(match.group(1))


def patthu_number(label: str) -> int | None:
    hundred = pathigam_hundred(label)
    if hundred is not None:
        return hundred
    leading = pathigam_leading_num(label)
    if leading is not None:
        return (leading - 1) // 10 + 1
    return None


def pathigam_seq(label: str, index: int) -> int:
    leading = pathigam_leading_num(label)
    if leading is not None:
        return leading
    _, unit = pathigam_parts(label)
    return unit if unit is not None else (index + 1)


def apply_range_corrections(entry: LinkEntry) -> LinkEntry:
    for key, (start, end) in RANGE_CORRECTIONS.items():
        if key in entry.padham_prefix or key in entry.label:
            new_label = RANGE_RE.sub(f"({start}-{end})", entry.label, count=1)
            return LinkEntry(
                href=entry.href,
                label=new_label,
                padham_prefix=entry.padham_prefix,
                start=start,
                end=end,
            )
    return entry


def prefix_is_loaded_override(entry: LinkEntry) -> bool:
    haystack = f"{entry.padham_prefix} {entry.label}"
    return any(term in haystack for term in LOADED_PREFIX_OVERRIDES)


def parse_range(label: str) -> tuple[int | None, int | None]:
    match = RANGE_RE.search(label)
    if not match:
        return None, None
    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else start
    return start, end


def extract_padham_prefix(href: str) -> str:
    match = re.search(r"[?&]padhamPrefix=([^&\"]+)", href)
    if not match:
        return ""
    return unquote_plus(match.group(1).replace("+", " "))


def parse_links(source_html: str) -> list[LinkEntry]:
    entries: list[LinkEntry] = []
    seen: set[tuple[str, str]] = set()
    for href, raw_label in LINK_RE.findall(source_html):
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", raw_label))).strip()
        prefix = extract_padham_prefix(href)
        start, end = parse_range(label)
        key = (href, label)
        if key in seen:
            continue
        seen.add(key)
        entries.append(LinkEntry(href=href, label=label, padham_prefix=prefix, start=start, end=end))
    return entries


def index_links(entries: list[LinkEntry]) -> dict[str, list[LinkEntry]]:
    by_prefix: dict[str, list[LinkEntry]] = {}
    for entry in entries:
        by_prefix.setdefault(entry.padham_prefix, []).append(entry)
    return by_prefix


def prefix_keys(prefix: str) -> list[str]:
    decoded = unquote_plus(prefix)
    return list(dict.fromkeys([prefix, decoded, decoded.replace(" ", "+"), decoded.replace("+", " ")]))


def pick_link(
    by_prefix: dict[str, list[LinkEntry]],
    prefix: str,
    start: int | None = None,
    end: int | None = None,
    label: str | None = None,
) -> LinkEntry | None:
    candidates: list[LinkEntry] = []
    for key in prefix_keys(prefix):
        candidates.extend(by_prefix.get(key, []))
    if start is not None:
        for entry in candidates:
            if entry.start == start and (end is None or entry.end == end):
                return entry
    if candidates:
        return candidates[0]
    if label and start is not None and end is not None:
        href = f"https://nalayiram.in/pocindex.php?padhamPrefix={prefix}"
        return LinkEntry(href=href, label=label, padham_prefix=prefix, start=start, end=end)
    return None


def load_pasuram_set(config_path: Path) -> set[int]:
    cfg = configparser.ConfigParser()
    cfg.read(config_path)
    db = cfg["db"]
    conn = mysql.connector.connect(
        host=db["host"],
        port=int(db["port"]),
        user=db["user"],
        password=db["password"],
        database=db["database"],
    )
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT DISTINCT PasuramNumber FROM {db['table']} "
            "WHERE PasuramNumber IS NOT NULL AND PasuramNumber > 0"
        )
        return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


@dataclass(frozen=True)
class KannadiIndexRow:
    pasuram_number: int
    pattu_number: int
    opening: str


def opening_snippet(pasuram_text: str, max_len: int = 12) -> str:
    """Return a short opening label for Kannadi index lines.

    Prefer the first whitespace-separated word. Join Tamil sandhi fragments
    ending in hard consonant + pulli (``க்/ச்/ட்/த்/ப்/ற்``).

    Some DB verses have no spaces on the first line (run-on Tamil). In that
    case fall back to a ``max_len`` character prefix so labels stay readable
    instead of dumping the whole line (e.g. உய்யவுலகு 65–74).
    """
    text = (pasuram_text or "").strip()
    # Skip leading separator-only lines (e.g. "—" above some pasurams)
    for line in text.splitlines():
        line = line.strip()
        if not line or re.fullmatch(r"[-—–\s]+", line):
            continue
        # Period / danda act as soft word breaks for index labels
        line_for_words = re.sub(r"[.|।॥]+", " ", line)
        parts = [p for p in re.split(r"\s+", line_for_words) if p]
        if not parts:
            continue
        first = parts[0]
        # Sandhi orthography only (vallinam + pulli), not every consonant-final word
        if len(parts) > 1 and re.search(r"[கசடதபற]்$", first):
            first = first + parts[1]
        first = re.sub(r"[.,;:!?\-—–|]+$", "", first)
        if not first:
            continue
        # Space-less / run-on first line → short prefix for the index
        if len(first) > max_len:
            return first[:max_len]
        return first
    return ""


def load_kannadi_index(config_path: Path, start: int, end: int) -> list[KannadiIndexRow]:
    cfg = configparser.ConfigParser()
    cfg.read(config_path)
    db = cfg["db"]
    conn = mysql.connector.connect(
        host=db["host"],
        port=int(db["port"]),
        user=db["user"],
        password=db["password"],
        database=db["database"],
    )
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT PasuramNumber, MIN(PattuNumber), MIN(Pasuram)
            FROM {db['table']}
            WHERE PasuramNumber BETWEEN %s AND %s
            GROUP BY PasuramNumber
            ORDER BY PasuramNumber
            """,
            (start, end),
        )
        by_number: dict[int, tuple[int, str]] = {}
        for pasuram_number, pattu_number, pasuram_text in cur.fetchall():
            by_number[int(pasuram_number)] = (
                int(pattu_number or 0),
                opening_snippet(pasuram_text or ""),
            )
        rows: list[KannadiIndexRow] = []
        for pasuram_number in range(start, end + 1):
            pattu_number, opening = by_number.get(pasuram_number, (pasuram_number - start + 1, ""))
            rows.append(
                KannadiIndexRow(
                    pasuram_number=pasuram_number,
                    pattu_number=pattu_number,
                    opening=opening or "…",
                )
            )
        return rows
    finally:
        conn.close()


def pathigam_parts(label: str) -> tuple[int | None, int | None]:
    match = PATHIGAM_RE.search(label)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def pathigam_id(label: str) -> str:
    match = re.match(r"^(\d+-\d+)\s", label.strip())
    if match:
        return match.group(1)
    match = PATHIGAM_RE.search(label)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    match = re.match(r"^(\d+)-", label.strip())
    if match:
        return f"{match.group(1)}-"
    return ""


def load_openings_map(config_path: Path, pasuram_numbers: list[int]) -> dict[int, str]:
    numbers = sorted(set(pasuram_numbers))
    if not numbers:
        return {}
    cfg = configparser.ConfigParser()
    cfg.read(config_path)
    db = cfg["db"]
    conn = mysql.connector.connect(
        host=db["host"],
        port=int(db["port"]),
        user=db["user"],
        password=db["password"],
        database=db["database"],
    )
    try:
        cur = conn.cursor()
        placeholders = ",".join(["%s"] * len(numbers))
        cur.execute(
            f"""
            SELECT PasuramNumber, MIN(Pasuram)
            FROM {db['table']}
            WHERE PasuramNumber IN ({placeholders})
            GROUP BY PasuramNumber
            """,
            tuple(numbers),
        )
        return {
            int(pasuram_number): opening_snippet(pasuram_text or "")
            for pasuram_number, pasuram_text in cur.fetchall()
        }
    finally:
        conn.close()


def collect_pathigam_starts(groups: dict[str, list[LinkEntry]], keys: tuple[str, ...]) -> list[int]:
    starts: list[int] = []
    for key in keys:
        for entry in groups[key]:
            entry = apply_range_corrections(entry)
            if entry.start is not None:
                starts.append(entry.start)
    return starts


def even_column_chunks(items: list, num_cols: int = 4) -> list[list]:
    """Distribute items evenly across columns (avoids a bloated last column)."""
    if not items:
        return [[] for _ in range(num_cols)]
    base, remainder = divmod(len(items), num_cols)
    columns: list[list] = []
    index = 0
    for col in range(num_cols):
        size = base + (1 if col < remainder else 0)
        columns.append(items[index : index + size])
        index += size
    return columns


def thirumalai_column_chunks(rows: list) -> list[list]:
    """45 pasurams: 11 + 11 + 11 + 12."""
    sizes = [11, 11, 11, 12]
    columns: list[list] = []
    index = 0
    for size in sizes:
        columns.append(rows[index : index + size])
        index += size
    return columns


def split_kannadi_columns(rows: list, layout: str) -> list[list]:
    if layout == "thirumalai":
        return thirumalai_column_chunks(rows)
    if layout == "even1":
        return [list(rows)]
    if layout == "even2":
        return even_column_chunks(rows, 2)
    return even_column_chunks(rows, 4)


def column_layout_for_rows(rows: list[KannadiIndexRow], *, group_key: str = "") -> str:
    if group_key == "thirumalai" or len(rows) == 45:
        return "thirumalai"
    if len(rows) <= 14:
        return "even2"
    return "even4"


def column_major_chunks(rows: list[KannadiIndexRow], num_cols: int = 4, rows_per_col: int = 8) -> list[list[KannadiIndexRow]]:
    return even_column_chunks(rows, num_cols)


def render_kannadi_columns(
    rows: list[KannadiIndexRow],
    pasurams: set[int],
    *,
    layout: str = "even4",
) -> str:
    if not rows:
        return '            <p class="kannadi-empty">(விரைவில்)</p>'
    columns_html: list[str] = []
    for column in split_kannadi_columns(rows, layout):
        lines: list[str] = []
        for row in column:
            loaded = row.pasuram_number in pasurams
            css = "release-loaded" if loaded else "release-pending"
            href = f"https://nalayiram.in/pocindex.php?padhamPrefix={row.pasuram_number}"
            seq = row.pattu_number if row.pattu_number else (
                row.pasuram_number - rows[0].pasuram_number + 1
            )
            lines.append(
                f'                    <div class="kannadi-line">'
                f'<a class="{css}" href="{html.escape(href, quote=True)}">'
                f"{row.pasuram_number} {html.escape(row.opening)} "
                f'<span class="k-seq">{seq}</span></a></div>'
            )
        columns_html.append("                <div class=\"kannadi-col\">\n" + "\n".join(lines) + "\n                </div>")
    if layout == "even1":
        col_class = "kannadi-index cols-1"
    elif layout == "even2":
        col_class = "kannadi-index cols-2"
    else:
        col_class = "kannadi-index cols-4"
    return f"""            <div class="{col_class}">
{chr(10).join(columns_html)}
            </div>"""


def entry_range_label(entries: list[LinkEntry]) -> str:
    starts = [entry.start for entry in entries if entry.start is not None]
    ends = [entry.end for entry in entries if entry.end is not None]
    if starts and ends:
        return f" ({min(starts)}-{max(ends)})"
    return ""


def kannadi_header_loaded(
    title: str,
    href: str,
    rows: list[KannadiIndexRow],
    pasurams: set[int],
) -> bool:
    probe = LinkEntry(href=href, label=title, padham_prefix=title, start=None, end=None)
    if prefix_is_loaded_override(probe):
        return True
    return all(row.pasuram_number in pasurams for row in rows) if rows else False


def kannadi_header_link(
    title: str,
    prabandham_href: str,
    range_label: str,
    rows: list[KannadiIndexRow],
    pasurams: set[int],
    *,
    heading: str = "h3",
) -> str:
    header_loaded = kannadi_header_loaded(title, prabandham_href, rows, pasurams)
    header_css = "release-loaded" if header_loaded else "release-pending"
    header_suffix = "" if header_loaded else ' <span class="pending-tag">(விரைவில்)</span>'
    return (
        f"<{heading}>"
        f'<a class="{header_css}" href="{html.escape(prabandham_href, quote=True)}">'
        f"{html.escape(title)}{html.escape(range_label)}</a>{header_suffix}"
        f"</{heading}>"
    )


def render_kannadi_index(
    title: str,
    prabandham_href: str,
    range_label: str,
    rows: list[KannadiIndexRow],
    pasurams: set[int],
    *,
    layout: str = "even4",
    full_width: bool = False,
    row_break: bool = False,
) -> str:
    header = kannadi_header_link(title, prabandham_href, range_label, rows, pasurams)
    width_cls = " kannadi-full-width" if full_width else ""
    row_cls = " row-break" if row_break else ""
    return f"""        <div class="static-list kannadi-prabandham{width_cls}{row_cls}">
            {header}
{render_kannadi_columns(rows, pasurams, layout=layout)}
        </div>"""


def render_pathigam_kannadi_columns(
    entries: list[LinkEntry],
    pasurams: set[int],
    openings: dict[int, str],
    *,
    num_cols: int | None = None,
) -> str:
    if not entries:
        return '            <p class="kannadi-empty">(விரைவில்)</p>'

    lines_for_cols: list[tuple[str, str, str, int, LinkEntry]] = []
    for index, raw_entry in enumerate(entries):
        entry = apply_range_corrections(raw_entry)
        seq = pathigam_seq(entry.label, index)
        start = entry.start or 0
        pid = pathigam_id(entry.label)
        opening = openings.get(start, "")
        lines_for_cols.append((pid, opening, entry.href, seq, entry))

    # Column layout: 2 cols for ≤10 pathigams (or forced), else 4 cols — evenly split
    if num_cols is None:
        num_cols = 2 if len(lines_for_cols) <= 10 else 4
    columns = even_column_chunks(lines_for_cols, num_cols)

    columns_html: list[str] = []
    for column in columns:
        lines: list[str] = []
        for pid, opening, href, seq, entry in column:
            loaded = is_loaded(pasurams, entry.start, entry.end, entry)
            css = "release-loaded" if loaded else "release-pending"
            suffix = "" if loaded else ' <span class="pending-tag">(விரைவில்)</span>'
            display = f"{pid} {opening}" if pid else f"{entry.start} {opening}"
            lines.append(
                f'                    <div class="kannadi-line">'
                f'<a class="{css}" href="{html.escape(href, quote=True)}">'
                f"{html.escape(display)} "
                f'<span class="k-seq">{seq}</span></a>{suffix}</div>'
            )
        columns_html.append("                <div class=\"kannadi-col\">\n" + "\n".join(lines) + "\n                </div>")
    col_class = "kannadi-index kannadi-pathigam-index cols-2" if num_cols == 2 else "kannadi-index kannadi-pathigam-index cols-4"
    return f"""            <div class="{col_class}">
{chr(10).join(columns_html)}
            </div>"""


def render_pathigam_kannadi_box(
    title: str,
    entries: list[LinkEntry],
    pasurams: set[int],
    openings: dict[int, str],
    *,
    row_break: bool = False,
    pathigam_cols: int | None = None,
) -> str:
    row_cls = " row-break" if row_break else ""
    return f"""        <div class="static-list kannadi-prabandham kannadi-pathigam-box{row_cls}">
            <h3>{html.escape(title)}</h3>
{render_pathigam_kannadi_columns(entries, pasurams, openings, num_cols=pathigam_cols)}
        </div>"""


def patthu_title(patthu_num: int) -> str:
    return PATTU_TITLES.get(patthu_num, f"{patthu_num}-ம் பத்து")


# Nachiyar patthu boxes per grid row (groups of 3; last row 13–14)
NACHIYAR_PATTU_ROW_GROUPS: tuple[tuple[int, ...], ...] = (
    (1, 2, 3),
    (4, 5, 6),
    (7, 8, 9),
    (10, 11, 12),
    (13, 14),
)

PERUMAL_PATTU_ROW_GROUPS: tuple[tuple[int, ...], ...] = (
    (1, 2, 3),
    (4, 5, 6),
    (7, 8, 9),
    (10,),
)


def patthu_display_name(patthu_num: int, entry: LinkEntry) -> str:
    label = entry.label.split("(")[0].strip()
    match = re.match(r"^(\d+)-(.+)$", label)
    if match:
        return match.group(2).strip()
    return patthu_title(patthu_num)

def group_nachiyar_patthus(entries: list[LinkEntry]) -> list[tuple[int, LinkEntry]]:
    """Each நாச்சியார் pathigam (1–14) is its own Kannadi patthu."""
    grouped: list[tuple[int, LinkEntry]] = []
    for entry in sorted(entries, key=lambda e: e.sort_key):
        patthu_num = pathigam_leading_num(entry.label)
        if patthu_num is None:
            continue
        grouped.append((patthu_num, apply_range_corrections(entry)))
    return grouped


def render_nachiyar_patthu_box(
    base_title: str,
    patthu_num: int,
    entry: LinkEntry,
    rows: list[KannadiIndexRow],
    pasurams: set[int],
) -> str:
    patthu_name = patthu_display_name(patthu_num, entry)
    range_label = entry_range_label([entry])
    display_title = f"{base_title} - {patthu_name}"
    col_layout = column_layout_for_rows(rows)
    header = kannadi_header_link(display_title, entry.href, range_label, rows, pasurams)
    return f"""            <div class="static-list kannadi-prabandham nachiyar-patthu-box">
                {header}
{render_kannadi_columns(rows, pasurams, layout=col_layout)}
            </div>"""


def render_nachiyar_patthu_boxes(
    base_title: str,
    entries: list[LinkEntry],
    pasurams: set[int],
    patthu_indexes: dict[int, list[KannadiIndexRow]],
    *,
    row_break: bool = False,
    patthu_row_groups: tuple[tuple[int, ...], ...] | None = None,
) -> str:
    by_patthu = dict(group_nachiyar_patthus(entries))
    row_groups = patthu_row_groups or NACHIYAR_PATTU_ROW_GROUPS
    row_blocks: list[str] = []
    for row_index, patthu_nums in enumerate(row_groups):
        boxes = [
            render_nachiyar_patthu_box(
                base_title,
                num,
                by_patthu[num],
                patthu_indexes.get(num, []),
                pasurams,
            )
            for num in patthu_nums
            if num in by_patthu
        ]
        if not boxes:
            continue
        # Always 3 columns so a partial last row (13–14) keeps box width
        # and leaves the third slot empty, matching பெரியாழ்வார் layout.
        row_cls = " row-break" if row_break and row_index == 0 else ""
        row_blocks.append(
            f"""        <div class="nachiyar-patthu-row{row_cls}">
            <div class="nachiyar-patthu-grid cols-3">
{chr(10).join(boxes)}
            </div>
        </div>"""
        )
    return "\n".join(row_blocks)


def pathigam_box_title(entry: LinkEntry) -> str:
    """Pathigam label without range, e.g. '1-1 வண்ண மாடங்கள்'."""
    return RANGE_RE.sub("", entry.label).strip()


def render_pathigam_pasuram_box(
    entry: LinkEntry,
    rows: list[KannadiIndexRow],
    pasurams: set[int],
) -> str:
    entry = apply_range_corrections(entry)
    start = entry.start or 0
    end = entry.end if entry.end is not None else start
    range_label = f" ({start}-{end})" if start != end else f" ({start})"
    header = kannadi_header_link(
        pathigam_box_title(entry),
        entry.href,
        range_label,
        rows,
        pasurams,
    )
    # Always 2 cols: pathigam boxes sit in a 3-wide grid (narrow cells).
    return f"""            <div class="static-list kannadi-prabandham nachiyar-patthu-box">
                {header}
{render_kannadi_columns(rows, pasurams, layout="even2")}
            </div>"""


def render_patthu_pasuram_boxes(
    base_title: str,
    entries: list[LinkEntry],
    pasurams: set[int],
    config_path: Path,
    *,
    row_break: bool = False,
    pathigams_per_row: int = 3,
) -> str:
    """One box per pathigam (pasuram-level index), grouped under each patthu.

    Matches நாச்சியார் style: pathigam header links to that pathigam; body lists
    every pasuram. Pathigam boxes sit in a 3-column grid (third slot empty when
    a row has fewer than 3).
    """
    sections: list[str] = []
    for patthu_index, (hundred, items) in enumerate(group_by_patthu(entries)):
        if hundred == 0:
            continue
        items = [apply_range_corrections(entry) for entry in items]
        items = [entry for entry in items if entry.start is not None]
        if not items:
            continue
        patthu_start = min(entry.start for entry in items if entry.start is not None)
        patthu_end = max(
            (entry.end if entry.end is not None else entry.start) for entry in items
        )
        section_title = (
            f"{base_title} - {patthu_title(hundred)} ({patthu_start}-{patthu_end})"
        )
        row_cls = " row-break" if row_break and patthu_index == 0 else ""
        row_blocks: list[str] = []
        for chunk_start in range(0, len(items), pathigams_per_row):
            chunk = items[chunk_start : chunk_start + pathigams_per_row]
            boxes: list[str] = []
            for entry in chunk:
                end = entry.end if entry.end is not None else entry.start
                assert entry.start is not None and end is not None
                rows = [
                    KannadiIndexRow(row.pasuram_number, index + 1, row.opening)
                    for index, row in enumerate(
                        load_kannadi_index(config_path, entry.start, end)
                    )
                ]
                boxes.append(render_pathigam_pasuram_box(entry, rows, pasurams))
            row_blocks.append(
                f"""            <div class="nachiyar-patthu-grid cols-3">
{chr(10).join(boxes)}
            </div>"""
            )
        sections.append(
            f"""        <div class="patthu-pasuram-section{row_cls}">
            <h3 class="patthu-section-title">{html.escape(section_title)}</h3>
{chr(10).join(row_blocks)}
        </div>"""
        )
    return "\n".join(sections)


def render_pathigam_patthu_boxes(
    base_title: str,
    entries: list[LinkEntry],
    pasurams: set[int],
    openings: dict[int, str],
    layout: str,
    *,
    row_break: bool = False,
    pathigam_cols: int | None = None,
) -> str:
    """Emit separate static-list boxes per patthu, matching releasenotespoc.html."""
    boxes: list[str] = []
    if layout == "single":
        box_title = f"{base_title}{entry_range_label(entries)}"
        boxes.append(
            render_pathigam_kannadi_box(
                box_title,
                entries,
                pasurams,
                openings,
                row_break=row_break,
                pathigam_cols=pathigam_cols or 2,
            )
        )
        return "\n".join(boxes)

    grouped = group_by_patthu(entries)
    patthu_groups = [(hundred, items) for hundred, items in grouped if hundred != 0]
    ungrouped = next((items for hundred, items in grouped if hundred == 0), [])

    if ungrouped:
        boxes.append(
            render_pathigam_kannadi_box(
                f"{base_title}{entry_range_label(ungrouped)}",
                ungrouped,
                pasurams,
                openings,
                row_break=row_break,
                pathigam_cols=pathigam_cols,
            )
        )

    for index, (hundred, items) in enumerate(patthu_groups):
        if layout in {"patthu_suffix", "repeat_title"}:
            patthu_title_text = patthu_title(hundred)
            box_title = f"{base_title} - {patthu_title_text}{entry_range_label(items)}"
        else:
            box_title = f"{base_title}{entry_range_label(items)}"
        boxes.append(
            render_pathigam_kannadi_box(
                box_title,
                items,
                pasurams,
                openings,
                row_break=row_break and index == 0,
                pathigam_cols=pathigam_cols,
            )
        )
    return "\n".join(boxes)


def render_madal_box(
    blocks: list[tuple[str, str, str, list[KannadiIndexRow]]],
    pasurams: set[int],
) -> str:
    """Three madal prabandhams in one box (no மடல்கள் group heading)."""
    lines: list[str] = []
    for title, href, range_label, rows in blocks:
        label = f"{title} {range_label}".strip()
        start = rows[0].pasuram_number if rows else None
        end = rows[-1].pasuram_number if rows else None
        entry = LinkEntry(href=href, label=label, padham_prefix=title, start=start, end=end)
        lines.append(f"            <h3>{link_html(entry, pasurams)}</h3>")
    return f"""        <div class="static-list row-break">
{chr(10).join(lines)}
        </div>"""


def render_kannadi_multi(
    section_title: str,
    blocks: list[tuple[str, str, str, list[KannadiIndexRow]]],
    pasurams: set[int],
) -> str:
    """Render a section with multiple Kannadi index blocks (e.g. திருவந்தாதி)."""
    parts: list[str] = []
    for title, href, range_label, rows in blocks:
        header = kannadi_header_link(title, href, range_label, rows, pasurams, heading="h4")
        layout = column_layout_for_rows(rows)
        parts.append(
            f"""            <div class="kannadi-sub-block">
                {header}
{render_kannadi_columns(rows, pasurams, layout=layout)}
            </div>"""
        )
    return f"""        <div class="static-list kannadi-prabandham kannadi-multi kannadi-full-width">
            <h3>{html.escape(section_title)}</h3>
{chr(10).join(parts)}
        </div>"""


def is_loaded(pasurams: set[int], start: int | None, end: int | None, entry: LinkEntry | None = None) -> bool:
    if entry is not None and prefix_is_loaded_override(entry):
        return True
    if start is None or end is None:
        return False
    expected = end - start + 1
    actual = sum(1 for n in range(start, end + 1) if n in pasurams)
    return actual == expected


def link_html(entry: LinkEntry, pasurams: set[int]) -> str:
    entry = apply_range_corrections(entry)
    if entry.start is None:
        css = "release-loaded"
        suffix = ""
    else:
        loaded = is_loaded(pasurams, entry.start, entry.end, entry)
        css = "release-loaded" if loaded else "release-pending"
        suffix = "" if loaded else ' <span class="pending-tag">(விரைவில்)</span>'
    return (
        f'<a class="{css}" href="{html.escape(entry.href, quote=True)}">'
        f"{html.escape(entry.label)}</a>{suffix}"
    )


def render_list(entries: list[LinkEntry], pasurams: set[int]) -> str:
    items = "\n".join(
        f"                <li>{link_html(entry, pasurams)}</li>" for entry in entries
    )
    return f"            <ul>\n{items}\n            </ul>"


def group_by_patthu(entries: list[LinkEntry]) -> list[tuple[int, list[LinkEntry]]]:
    buckets: dict[int, list[LinkEntry]] = {}
    ungrouped: list[LinkEntry] = []
    for entry in entries:
        hundred = patthu_number(entry.label)
        if hundred is None:
            ungrouped.append(entry)
            continue
        buckets.setdefault(hundred, []).append(entry)
    groups: list[tuple[int, list[LinkEntry]]] = []
    if ungrouped:
        groups.append((0, ungrouped))
    for hundred in sorted(buckets):
        groups.append((hundred, sorted(buckets[hundred], key=lambda e: e.sort_key)))
    return groups


def render_patthu_group(title: str, entries: list[LinkEntry], pasurams: set[int]) -> str:
    patthu_blocks: list[str] = []
    for hundred, items in group_by_patthu(entries):
        if hundred == 0:
            patthu_blocks.append(render_list(items, pasurams))
            continue
        patthu_title_text = patthu_title(hundred)
        patthu_blocks.append(f"""            <div class="static-list patthu-box">
                <h4>{html.escape(patthu_title_text)}</h4>
{render_list(items, pasurams)}
            </div>""")
    inner = "\n".join(patthu_blocks)
    return f"""        <div class="patthu-group">
            <h3>{html.escape(title)}</h3>
            <div class="patthu-grid">
{inner}
            </div>
        </div>"""


def render_nithya_v2(nithya: dict, by_prefix: dict[str, list[LinkEntry]], pasurams: set[int]) -> str:
    """Render நித்யாநுஸந்தானம் with structure matching the release-notes image."""
    thaniya_blocks: list[str] = []
    sub_ul: list[str] = []

    for spec in nithya["thaniyangal"]:
        if spec.get("type") == "heading":
            if sub_ul:
                thaniya_blocks.append("            <ul>\n" + "\n".join(sub_ul) + "\n            </ul>")
                sub_ul = []
            entry = pick_link(by_prefix, spec["padhamPrefix"])
            label = spec.get("label", entry.label if entry else spec["padhamPrefix"])
            href = entry.href if entry else (
                f"https://nalayiram.in/pocindex.php?padhamPrefix={spec['padhamPrefix']}"
            )
            heading_entry = LinkEntry(
                href=href, label=label, padham_prefix=spec["padhamPrefix"], start=None, end=None
            )
            thaniya_blocks.append(f"            <h4>{link_html(heading_entry, pasurams)}</h4>")
            continue

        entry = pick_link(by_prefix, spec["padhamPrefix"], spec["start"], spec["end"])
        if entry is None:
            href = f"https://nalayiram.in/pocindex.php?padhamPrefix={spec['padhamPrefix']}"
            label = f"{spec['padhamPrefix']}({spec['start']}-{spec['end']})"
            entry = LinkEntry(
                href=href, label=label, padham_prefix=spec["padhamPrefix"],
                start=spec["start"], end=spec["end"],
            )

        line = f"                <li>{link_html(entry, pasurams)}</li>"
        if spec["padhamPrefix"] in {"நீராட்டம்", "பூச்சூடல்", "காப்பிடல்", "சென்னியோங்கு"}:
            sub_ul.append(line)
        else:
            if sub_ul:
                thaniya_blocks.append("            <ul>\n" + "\n".join(sub_ul) + "\n            </ul>")
                sub_ul = []
            thaniya_blocks.append(f"            <h4>{link_html(entry, pasurams)}</h4>")

    if sub_ul:
        thaniya_blocks.append("            <ul>\n" + "\n".join(sub_ul) + "\n            </ul>")

    koil_items: list[str] = []
    for spec in nithya["koil_thiruvaimozhi"]:
        entry = pick_link(by_prefix, spec["padhamPrefix"], spec["start"], spec["end"])
        if entry and spec.get("label"):
            entry = LinkEntry(
                href=entry.href,
                label=spec["label"],
                padham_prefix=entry.padham_prefix,
                start=entry.start,
                end=entry.end,
            )
        if entry is None:
            href = f"https://nalayiram.in/pocindex.php?padhamPrefix={spec['padhamPrefix']}"
            label = spec.get("label", f"({spec['start']}-{spec['end']})")
            entry = LinkEntry(
                href=href, label=label, padham_prefix=spec["padhamPrefix"],
                start=spec["start"], end=spec["end"],
            )
        koil_items.append(f"                <li>{link_html(entry, pasurams)}</li>")

    search_href = html.escape(nithya["search_link"], quote=True)
    return f"""        <div class="group-box nithya-group">
            <h2 class="group-title"><a href="{search_href}">{html.escape(nithya["title"])}</a></h2>
            <div class="nithya-columns">
                <div class="static-list">
                    <h3>தனியன்கள்</h3>
{chr(10).join(thaniya_blocks)}
                </div>
                <div class="static-list">
                    <h3>கோயில் திருவாய்மொழி</h3>
                    <ul>
{chr(10).join(koil_items)}
                    </ul>
                </div>
            </div>
        </div>"""


def classify_entries(entries: list[LinkEntry]) -> dict[str, list[LinkEntry]]:
    groups: dict[str, list[LinkEntry]] = {
        "periyazhwar": [],
        "nachiyar": [],
        "perumal_thirumozhi": [],
        "thirumalai": [],
        "periya_thirumozhi": [],
        "thirukkurunthandagam": [],
        "nedum_thandagam": [],
        "thiruvandhathi": [],
        "thiruviruttam": [],
        "thiruvachiriyam": [],
        "madal": [],
        "thiruvaimozhi": [],
    }
    seen_in_group: dict[str, set[str]] = {k: set() for k in groups}

    for entry in entries:
        if entry.start is None:
            continue
        prefix = entry.padham_prefix

        def add(group: str) -> None:
            key = entry.href
            if key in seen_in_group[group]:
                return
            seen_in_group[group].add(key)
            groups[group].append(entry)

        if "திருக்குறுந்தாண்டகம்" in prefix or entry.start == 2032:
            add("thirukkurunthandagam")
        elif "நெடும்+தாண்டகம்" in prefix or "நெடும் தாண்டகம்" in entry.label or entry.start == 2052:
            add("nedum_thandagam")
        elif entry.start == 2082 or (
            entry.start is not None
            and entry.end is not None
            and entry.start >= 2082
            and entry.end <= 2671
            and any(
                term in entry.label or term in entry.padham_prefix
                for term in ("திருவந்தாதி", "Thiruvandhathi")
            )
        ):
            add("thiruvandhathi")
        elif "திருவிருத்தம்" in prefix or entry.start == 2478:
            add("thiruviruttam")
        elif "திருவாசிரியம்" in prefix or entry.start == 2578:
            add("thiruvachiriyam")
        elif entry.start in {2672, 2673, 2674}:
            add("madal")
        elif entry.start >= 2675 and entry.end is not None and entry.end <= 3776:
            add("thiruvaimozhi")
        elif entry.start >= 948 and entry.end is not None and entry.end <= 1347:
            add("periya_thirumozhi")
        elif entry.start == 872 or (entry.start >= 872 and entry.end is not None and entry.end <= 916):
            add("thirumalai")
        elif entry.start >= 504 and entry.end is not None and entry.end <= 646:
            add("nachiyar")
        elif entry.start >= 647 and entry.end is not None and entry.end <= 751:
            add("perumal_thirumozhi")
        elif entry.start >= 13 and entry.end is not None and entry.end <= 473:
            add("periyazhwar")

    for group in groups:
        if group == "thiruvaimozhi":
            by_range: dict[tuple[int, int], LinkEntry] = {}
            for entry in groups[group]:
                if entry.start is None or entry.end is None:
                    continue
                key = (entry.start, entry.end)
                existing = by_range.get(key)
                if existing is None or len(entry.label) > len(existing.label):
                    by_range[key] = entry
            groups[group] = sorted(by_range.values(), key=lambda e: e.sort_key)
        else:
            groups[group].sort(key=lambda e: e.sort_key)
    return groups


def build_body(
    groups: dict[str, list[LinkEntry]],
    nithya_html: str,
    pasurams: set[int],
    kannadi_indexes: dict[str, list[KannadiIndexRow]] | None = None,
    kannadi_multi_blocks: dict[str, list[tuple[str, str, str, list[KannadiIndexRow]]]] | None = None,
    pathigam_openings: dict[int, str] | None = None,
    nachiyar_patthu_indexes: dict[int, list[KannadiIndexRow]] | None = None,
) -> str:
    parts = [nithya_html]
    kannadi_indexes = kannadi_indexes or {}
    kannadi_multi_blocks = kannadi_multi_blocks or {}
    pathigam_openings = pathigam_openings or {}
    nachiyar_patthu_indexes = nachiyar_patthu_indexes or {}

    group_specs = [
        ("periyazhwar", "பெரியாழ்வார் திருமொழி", "kannadi_pathigam", "patthu_suffix", {}),
        ("nachiyar", "ஸ்ரீ நாச்சியார் திருமொழி", "nachiyar_patthu", None, {"row_break": True}),
        ("thirumalai", "திருமாலை", "kannadi_index", None, {}),
        ("periya_thirumozhi", "பெரிய திருமொழி", "kannadi_pathigam", "patthu_suffix", {}),
        ("thirukkurunthandagam", "திருக்குறுந்தாண்டகம்", "kannadi_index", None, {"row_break": True}),
        ("nedum_thandagam", "திரு நெடும் தாண்டகம்", "kannadi_index", None, {}),
        ("thiruvandhathi", "திருவந்தாதி", "kannadi_multi", None, {}),
        ("thiruviruttam", "திருவிருத்தம்", "kannadi_index", None, {}),
        ("thiruvachiriyam", "திருவாசிரியம்", "kannadi_index", None, {}),
        ("madal", "", "madal_box", None, {}),
        ("thiruvaimozhi", "திருவாய்மொழி", "kannadi_pathigam", "patthu_suffix", {}),
    ]

    for key, title, mode, layout, opts in group_specs:
        items = groups[key]
        row_break = bool(opts.get("row_break"))
        pathigam_cols = opts.get("pathigam_cols")
        if mode == "kannadi_index":
            index_rows = kannadi_indexes.get(key, [])
            if not index_rows and not items:
                continue
            href = items[0].href if items else f"https://nalayiram.in/pocindex.php?padhamPrefix={key}"
            range_label = ""
            if items and items[0].start is not None and items[0].end is not None:
                if len(items) == 1:
                    range_label = f"({items[0].start}-{items[0].end})"
                else:
                    starts = [entry.start for entry in items if entry.start is not None]
                    ends = [entry.end for entry in items if entry.end is not None]
                    if starts and ends:
                        range_label = f"({min(starts)}-{max(ends)})"
            display_title = title or (items[0].label.split("(")[0].strip() if items else key)
            layout = column_layout_for_rows(index_rows, group_key=key)
            full_width = len(index_rows) >= 30 or key in {"thiruviruttam", "thirumalai"}
            parts.append(
                render_kannadi_index(
                    display_title,
                    href,
                    range_label,
                    index_rows,
                    pasurams,
                    layout=layout,
                    full_width=full_width,
                    row_break=row_break,
                )
            )
            continue
        if mode == "madal_box":
            blocks = kannadi_multi_blocks.get(key, [])
            if not blocks:
                continue
            parts.append(render_madal_box(blocks, pasurams))
            continue
        if mode == "kannadi_multi":
            blocks = kannadi_multi_blocks.get(key, [])
            if not blocks:
                continue
            parts.append(render_kannadi_multi(title, blocks, pasurams))
            continue
        if not items:
            continue
        if mode == "nachiyar_patthu":
            parts.append(
                render_nachiyar_patthu_boxes(
                    title,
                    items,
                    pasurams,
                    nachiyar_patthu_indexes,
                    row_break=row_break,
                )
            )
        elif mode == "kannadi_pathigam":
            parts.append(
                render_pathigam_patthu_boxes(
                    title,
                    items,
                    pasurams,
                    pathigam_openings,
                    layout or "single",
                    row_break=row_break,
                    pathigam_cols=pathigam_cols,
                )
            )
        elif mode == "patthu":
            parts.append(render_patthu_group(title, items, pasurams))
        elif mode == "list":
            parts.append(f"""        <div class="static-list">
            <h3>{html.escape(title)}</h3>
{render_list(items, pasurams)}
        </div>""")
        elif mode == "single":
            entry = items[0]
            parts.append(f"""        <div class="static-list">
            <h3>{link_html(entry, pasurams)}</h3>
        </div>""")
        elif mode == "madal":
            lines = "\n".join(
                f"            <h3>{link_html(entry, pasurams)}</h3>" for entry in items
            )
            parts.append(f"""        <div class="static-list">
{lines}
        </div>""")

    return "\n".join(parts)


def build_html(source_html: str, body: str) -> str:
    head_match = re.search(r"(.*?<div class=\"container\">)", source_html, re.DOTALL)
    tail_match = re.search(r"</div>\s*</body>", source_html, re.DOTALL)
    if not head_match or not tail_match:
        raise RuntimeError("Could not parse source HTML structure")

    head = head_match.group(1)
    head = re.sub(
        r"<title>[^<]*</title>",
        f"<title>{RELEASE_NOTES_PAGE_TITLE}</title>",
        head,
        count=1,
    )

    extra_css = """
        body {
            overflow-x: hidden;
            max-width: 100vw;
        }

        .container {
            max-width: min(1200px, 100%);
            width: 100%;
            box-sizing: border-box;
        }

        .static-list {
            min-width: 0;
            overflow: visible;
            box-sizing: border-box;
        }

        .static-list h3 {
            font-size: calc(1.17em - 1pt);
            line-height: 1.22;
        }

        .static-list h4,
        .group-title {
            font-size: calc(1em - 1pt);
            line-height: 1.22;
        }

        .kannadi-full-width {
            grid-column: 1 / -1;
        }

        .row-break {
            grid-column: 1 / -1;
        }

        .nachiyar-patthu-row {
            grid-column: 1 / -1;
            min-width: 0;
        }

        .nachiyar-patthu-grid {
            display: grid;
            gap: 10px;
            min-width: 0;
        }

        .nachiyar-patthu-grid.cols-1 {
            grid-template-columns: minmax(0, 1fr);
        }

        .nachiyar-patthu-grid.cols-2 {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .nachiyar-patthu-grid.cols-3 {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .nachiyar-patthu-box {
            min-width: 0;
            padding: 8px;
        }

        .patthu-pasuram-section {
            grid-column: 1 / -1;
            min-width: 0;
            margin-bottom: 8px;
        }

        .patthu-pasuram-section .nachiyar-patthu-grid {
            margin-bottom: 10px;
        }

        .patthu-section-title {
            margin: 0 0 10px 0;
            color: #0066CC;
            font-size: calc(1.17em - 1pt);
            line-height: 1.22;
        }

        @media (max-width: 900px) {
            .nachiyar-patthu-grid.cols-2,
            .nachiyar-patthu-grid.cols-3 {
                grid-template-columns: 1fr;
            }
        }

        .group-box {
            border: 2px solid #0066CC;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            background-color: #f8fcff;
            grid-column: 1 / -1;
        }

        .group-title {
            text-align: center;
            color: #0066CC;
            margin: 0 0 15px 0;
        }

        .nithya-columns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        .prabandham-nav-list {
            columns: 3;
            column-gap: 1.5rem;
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .prabandham-nav-list li {
            break-inside: avoid;
            margin-bottom: 0.35rem;
        }

        .prabandham-nav-list a {
            color: #0066CC;
            font-weight: 600;
            text-decoration: none;
        }

        .prabandham-nav-list a:hover,
        .prabandham-nav-list a:focus {
            text-decoration: underline;
        }

        [id^="prab-"] {
            scroll-margin-top: 0.75rem;
        }

        .release-pending {
            color: #888888;
        }

        .release-loaded {
            color: #0066CC;
        }

        .pending-tag {
            font-size: 0.85em;
            color: #aa6600;
        }

        .patthu-group {
            border: 1px solid #ccc;
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 10px;
        }

        .patthu-group > h3 {
            margin-top: 0;
            color: #0066CC;
            font-size: calc(1.17em - 1pt);
            line-height: 1.22;
        }

        .patthu-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }

        .patthu-box h4 {
            margin: 0 0 8px 0;
            color: #0066CC;
            font-size: calc(1em - 1pt);
            line-height: 1.22;
        }

        .nachiyar-patthu-box h3 {
            font-size: calc(1.17em - 1pt);
            line-height: 1.2;
            margin-bottom: 0.25em;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        .nachiyar-patthu-box h3 a {
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        @media (max-width: 900px) {
            .patthu-grid {
                grid-template-columns: 1fr;
            }
        }

        .kannadi-prabandham .kannadi-index,
        .kannadi-multi .kannadi-index {
            display: grid;
            gap: 4px 10px;
            margin-top: 10px;
            font-size: 0.88em;
            line-height: 1.45;
            min-width: 0;
        }

        .kannadi-index.cols-4 {
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .kannadi-index.cols-1 {
            grid-template-columns: minmax(0, 1fr);
        }

        .kannadi-index.cols-2 {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .kannadi-col {
            min-width: 0;
        }

        .kannadi-line {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* Short prabandhams (2-col): show full opening snippet without "..." */
        .kannadi-index.cols-2 .kannadi-line {
            white-space: normal;
            overflow: visible;
            text-overflow: clip;
            overflow-wrap: anywhere;
        }

        .kannadi-line a {
            text-decoration: underline;
        }

        .kannadi-line .k-seq {
            color: #555555;
            font-size: 0.9em;
        }

        @media (max-width: 900px) {
            .kannadi-index.cols-4 {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 600px) {
            .kannadi-index.cols-4,
            .kannadi-index.cols-2 {
                grid-template-columns: 1fr;
            }
        }

        .kannadi-pathigam-index {
            margin-top: 8px;
        }

        .kannadi-pathigam-box h3 {
            margin-top: 0;
            font-size: calc(1.17em - 1pt);
            line-height: 1.22;
        }

        @media (max-width: 768px) {
            .nithya-columns {
                grid-template-columns: 1fr;
            }

            .prabandham-nav-list {
                columns: 2;
            }
        }

        /* Phone / narrow: stack prabandham boxes full-width (avoid 3-col squeeze) */
        @media (max-width: 900px) {
            .container {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 14px;
                padding: 14px;
            }

            header img {
                width: 140px;
            }
        }

        @media (max-width: 600px) {
            .container {
                grid-template-columns: minmax(0, 1fr);
                gap: 12px;
                padding: 12px;
            }

            .prabandham-nav-list {
                columns: 1;
            }

            header img {
                width: 120px;
            }

            .kannadi-line {
                white-space: normal;
                overflow: visible;
                text-overflow: clip;
                overflow-wrap: anywhere;
            }

            .static-list h3,
            .patthu-section-title,
            .group-title {
                overflow-wrap: anywhere;
                word-break: break-word;
            }
        }

        .kannadi-multi .kannadi-sub-block {
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid #ddeeff;
        }

        .kannadi-multi .kannadi-sub-block:first-of-type {
            border-top: none;
            padding-top: 0;
            margin-top: 8px;
        }

        .kannadi-multi h4 {
            margin: 0 0 6px 0;
            font-size: calc(1em - 1pt);
            line-height: 1.22;
        }

        .kannadi-empty {
            color: #888888;
            font-style: italic;
            margin: 0;
        }
"""

    head = head.replace("</style>", extra_css + "\n    </style>")
    # Drop the release-notes subtitle line (Kannadi / loaded-vs-pending note).
    head = re.sub(
        r'\s*<h5 style="color:\s*white;">[^<]*</h5>',
        "",
        head,
        count=1,
    )

    return f"{head}\n{body}\n    </div>\n</body>\n</html>\n"


def load_nachiyar_patthu_indexes(
    config_path: Path,
    entries: list[LinkEntry],
) -> dict[int, list[KannadiIndexRow]]:
    indexes: dict[int, list[KannadiIndexRow]] = {}
    for patthu_num, entry in group_nachiyar_patthus(entries):
        if entry.start is None or entry.end is None:
            continue
        indexes[patthu_num] = load_kannadi_index(config_path, entry.start, entry.end)
    return indexes


def load_kannadi_data(
    config_path: Path,
    groups: dict[str, list[LinkEntry]],
) -> tuple[
    dict[str, list[KannadiIndexRow]],
    dict[str, list[tuple[str, str, str, list[KannadiIndexRow]]]],
]:
    kannadi_indexes: dict[str, list[KannadiIndexRow]] = {}
    kannadi_multi_blocks: dict[str, list[tuple[str, str, str, list[KannadiIndexRow]]]] = {}

    single_ranges = {
        "thirumalai": (872, 916),
        "thirukkurunthandagam": (2032, 2051),
        "nedum_thandagam": (2052, 2081),
        "thiruviruttam": (2478, 2577),
        "thiruvachiriyam": (2578, 2584),
    }
    for key, (start, end) in single_ranges.items():
        kannadi_indexes[key] = load_kannadi_index(config_path, start, end)

    for multi_key in ("thiruvandhathi", "madal"):
        blocks: list[tuple[str, str, str, list[KannadiIndexRow]]] = []
        for entry in sorted(groups[multi_key], key=lambda e: e.sort_key):
            entry = apply_range_corrections(entry)
            if entry.start is None:
                continue
            end = entry.end if entry.end is not None else entry.start
            title = entry.label.split("(")[0].strip()
            rows = load_kannadi_index(config_path, entry.start, end)
            range_label = f"({entry.start}-{end})"
            blocks.append((title, entry.href, range_label, rows))
        kannadi_multi_blocks[multi_key] = blocks

    return kannadi_indexes, kannadi_multi_blocks


def main() -> None:
    """Canonical builder: pathigam-detail Kannadi layout (former v1)."""
    import runpy

    v1_path = Path(__file__).resolve().parent / "build_newreleasenote_poc_v1.py"
    runpy.run_path(str(v1_path), run_name="__main__")


if __name__ == "__main__":
    main()
