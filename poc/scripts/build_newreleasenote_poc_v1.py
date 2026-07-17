#!/usr/bin/env python3
"""Build Kannadi pasuram-number order POC release notes (v1).

Keeps நித்யாநுஸந்தானம் unchanged, then boxes the rest by prabandham name
in Divya Prabandha Kannadi order (starting with திருப்பல்லாண்டு 1–12).

பெரியாழ்வார் / பெரிய திருமொழி / திருவாய்மொழி use detailed pasuram-number
indexes per patthu (same style as நாச்சியார்), with header linking to the
first pathigam of that patthu.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from poc.scripts.build_newreleasenote_poc import (  # noqa: E402
    ENV_PRESETS,
    NITHYA_JSON,
    SOURCE_HTML,
    LinkEntry,
    apply_range_corrections,
    build_html,
    classify_entries,
    column_layout_for_rows,
    index_links,
    load_kannadi_index,
    load_nachiyar_patthu_indexes,
    load_pasuram_set,
    parse_links,
    pick_link,
    PERUMAL_PATTU_ROW_GROUPS,
    render_kannadi_index,
    render_nachiyar_patthu_boxes,
    render_nithya_v2,
    render_patthu_pasuram_boxes,
    rewrite_search_script,
)

OUTPUT_HTML = ROOT / "public_html" / "newreleasenotespoc.html"

# (key, title, mode, layout, start, end, padham_prefix, opts)
# Ordered by Kannadi pasuram number (DivyaPrabandhaKannadi-PBA.pdf).
V1_SPECS: list[tuple] = [
    ("thirupallandu", "திருப்பல்லாண்டு", "kannadi_index", None, 1, 12, "திருப்பல்லாண்டு", {"layout": "even2"}),
    ("periyazhwar", "பெரியாழ்வார் திருமொழி", "patthu_pasuram", None, 13, 473, "பெரியாழ்வார்+திருமொழி", {}),
    ("thiruppavai", "திருப்பாவை", "kannadi_index", None, 474, 503, "திருப்பாவை", {"layout": "even4", "full_width": True}),
    ("nachiyar", "ஸ்ரீ நாச்சியார் திருமொழி", "nachiyar_patthu", None, 504, 646, None, {"row_break": True}),
    (
        "perumal_thirumozhi",
        "பெருமாள் திருமொழி",
        "nachiyar_patthu",
        None,
        647,
        751,
        None,
        {"row_break": True},
    ),
    (
        "thiruchanda",
        "ஸ்ரீ திருச்சந்த விருத்தம்",
        "kannadi_index",
        None,
        752,
        871,
        "ஸ்ரீ+திருச்சந்த+விருத்தம்",
        {"full_width": True},
    ),
    ("thirumalai", "திருமாலை", "kannadi_index", None, 872, 916, "திருமாலை", {}),
    # even2 keeps one-line readability when three small boxes share a row
    ("thiruppalliyezhuchi", "திருப்பள்ளியெழுச்சி", "kannadi_index", None, 917, 926, "திருப்பள்ளியெழுச்சி", {"layout": "even2"}),
    ("amalanadipiran", "அமலனாதிபிரான்", "kannadi_index", None, 927, 936, "அமலனாதிபிரான்", {"layout": "even2"}),
    ("kanninunsiruthambu", "கண்ணிநுண்சிறுத்தாம்பு", "kannadi_index", None, 937, 947, "கண்ணிநுண்சிறுத்தாம்பு", {"layout": "even2"}),
    ("periya_thirumozhi", "பெரிய திருமொழி", "patthu_pasuram", None, 948, 1247, None, {}),
    ("thirukkurunthandagam", "திருக்குறுந்தாண்டகம்", "kannadi_index", None, 2032, 2051, "திருக்குறுந்தாண்டகம்", {"row_break": True, "layout": "even4"}),
    ("nedum_thandagam", "திரு நெடும் தாண்டகம்", "kannadi_index", None, 2052, 2081, "திரு+நெடும்+தாண்டகம்", {"layout": "even4"}),
    ("mudal_thiruvandhathi", "முதல் திருவந்தாதி", "kannadi_index", None, 2082, 2181, "முதல்+திருவந்தாதி", {"full_width": True}),
    ("irandam_thiruvandhathi", "இரண்டாம் திருவந்தாதி", "kannadi_index", None, 2182, 2281, "இரண்டாம்+திருவந்தாதி", {"full_width": True}),
    ("moonram_thiruvandhathi", "மூன்றாம் திருவந்தாதி", "kannadi_index", None, 2282, 2381, "மூன்றாம்+திருவந்தாதி", {"full_width": True}),
    ("nanmugan_thiruvandhathi", "நான்முகன் திருவந்தாதி", "kannadi_index", None, 2382, 2477, "நான்முகன்+திருவந்தாதி", {"full_width": True}),
    ("thiruviruttam", "திருவிருத்தம்", "kannadi_index", None, 2478, 2577, "திருவிருத்தம்", {"full_width": True}),
    ("thiruvachiriyam", "திருவாசிரியம்", "kannadi_index", None, 2578, 2584, "திருவாசிரியம்", {"layout": "even2"}),
    ("periya_thiruvandhathi", "பெரிய திருவந்தாதி", "kannadi_index", None, 2585, 2671, "பெரிய+திருவந்தாதி", {"full_width": True}),
    ("thiruvozhukootrirukkai", "திருவெழுகூற்றிருக்கை", "kannadi_index", None, 2672, 2672, "திருவெழுகூற்றிருக்கை", {"layout": "even2"}),
    ("siriya_thirumadal", "சிறிய திருமடல்", "kannadi_index", None, 2673, 2673, "சிறிய+திருமடல்", {"layout": "even2"}),
    ("periya_thirumadal", "பெரிய திருமடல்", "kannadi_index", None, 2674, 2674, "பெரிய+திருமடல்", {"layout": "even2"}),
    ("thiruvaimozhi", "திருவாய்மொழி", "patthu_pasuram", None, 2675, 3776, None, {}),
    (
        "iramanusa_nootranthathi",
        "இராமாநுச நூற்றந்தாதி",
        "kannadi_index",
        None,
        3777,
        3884,
        "இராமாநுச நூற்றந்தாதி",
        {"full_width": True},
    ),
]


def resolve_entry(
    by_prefix: dict[str, list[LinkEntry]],
    groups: dict[str, list[LinkEntry]],
    key: str,
    padham_prefix: str | None,
    start: int,
    end: int,
    title: str,
) -> LinkEntry | None:
    if key in groups and groups[key]:
        return apply_range_corrections(groups[key][0])
    if padham_prefix:
        entry = pick_link(by_prefix, padham_prefix)
        if entry:
            return apply_range_corrections(entry)
        entry = pick_link(by_prefix, padham_prefix.replace("+", " "))
        if entry:
            return apply_range_corrections(entry)
    href = (
        f"https://nalayiram.in/pocindex.php?padhamPrefix="
        f"{(padham_prefix or title).replace(' ', '+')}"
    )
    return LinkEntry(
        href=href,
        label=f"{title}({start}-{end})",
        padham_prefix=padham_prefix or title,
        start=start,
        end=end,
    )


def build_body_v1(
    groups: dict[str, list[LinkEntry]],
    by_prefix: dict[str, list[LinkEntry]],
    nithya_html: str,
    pasurams: set[int],
    kannadi_indexes: dict[str, list],
    nachiyar_patthu_indexes: dict[int, list],
    perumal_patthu_indexes: dict[int, list],
    config_path: Path,
) -> str:
    parts = [nithya_html]

    for key, title, mode, _layout, start, end, padham_prefix, opts in V1_SPECS:
        row_break = bool(opts.get("row_break"))
        entry = resolve_entry(by_prefix, groups, key, padham_prefix, start, end, title)
        items = groups.get(key) or ([entry] if entry else [])

        if mode == "kannadi_index":
            rows = kannadi_indexes.get(key, [])
            if not rows:
                continue
            href = entry.href if entry else f"https://nalayiram.in/pocindex.php?padhamPrefix={start}"
            range_label = f"({start}-{end})" if start != end else f"({start})"
            col_layout = opts.get("layout") or column_layout_for_rows(rows, group_key=key)
            full_width = bool(opts.get("full_width")) or len(rows) >= 30
            parts.append(
                render_kannadi_index(
                    title,
                    href,
                    range_label,
                    rows,
                    pasurams,
                    layout=col_layout,
                    full_width=full_width,
                    row_break=row_break,
                )
            )
        elif mode == "nachiyar_patthu":
            if not items:
                continue
            patthu_indexes = (
                perumal_patthu_indexes if key == "perumal_thirumozhi" else nachiyar_patthu_indexes
            )
            row_groups = (
                PERUMAL_PATTU_ROW_GROUPS if key == "perumal_thirumozhi" else None
            )
            parts.append(
                render_nachiyar_patthu_boxes(
                    title,
                    items,
                    pasurams,
                    patthu_indexes,
                    row_break=row_break,
                    patthu_row_groups=row_groups,
                )
            )
        elif mode == "patthu_pasuram":
            if not items:
                continue
            parts.append(
                render_patthu_pasuram_boxes(
                    title,
                    items,
                    pasurams,
                    config_path,
                    row_break=row_break,
                )
            )

    return "\n".join(parts)


def load_v1_indexes(config_path: Path) -> dict[str, list]:
    indexes: dict[str, list] = {}
    for key, _title, mode, _layout, start, end, _prefix, _opts in V1_SPECS:
        if mode != "kannadi_index":
            continue
        indexes[key] = load_kannadi_index(config_path, start, end)
    return indexes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env",
        choices=sorted(ENV_PRESETS),
        default="poc",
        help="Target environment (sets config, source, search script, output)",
    )
    parser.add_argument("--config", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--search-script",
        default=None,
        help="Search PHP script: pocindex.php | test1.php | index.php",
    )
    args = parser.parse_args()

    preset = ENV_PRESETS[args.env]
    config_path = Path(args.config or preset["config"])
    source_path = Path(args.source or preset["source"])
    output_path = Path(args.output or preset["output"])
    search_script = args.search_script or preset["search_script"]

    source_html = source_path.read_text(encoding="utf-8")
    nithya = json.loads(NITHYA_JSON.read_text(encoding="utf-8"))
    entries = parse_links(source_html)
    by_prefix = index_links(entries)
    pasurams = load_pasuram_set(config_path)
    groups = classify_entries(entries)

    kannadi_indexes = load_v1_indexes(config_path)
    nachiyar_patthu_indexes = load_nachiyar_patthu_indexes(config_path, groups["nachiyar"])
    perumal_patthu_indexes = load_nachiyar_patthu_indexes(
        config_path, groups.get("perumal_thirumozhi", [])
    )

    nithya_html = render_nithya_v2(nithya, by_prefix, pasurams)
    body = build_body_v1(
        groups,
        by_prefix,
        nithya_html,
        pasurams,
        kannadi_indexes,
        nachiyar_patthu_indexes,
        perumal_patthu_indexes,
        config_path,
    )
    output = rewrite_search_script(build_html(source_html, body), search_script)
    output_path.write_text(output, encoding="utf-8")
    print(f"Wrote {output_path} ({args.env}, {search_script})")


if __name__ == "__main__":
    main()
