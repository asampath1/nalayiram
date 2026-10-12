#!/usr/bin/env python3
"""Build public_html/sitemap.xml: home + hub pages + prabandham search URLs only.

Does not include individual pasuram / pathigam URLs.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "public_html" / "divyaprabandham_counts_seed.json"
OUT = ROOT / "public_html" / "sitemap.xml"
BASE = "https://nalayiram.in"


def url_entry(loc: str, lastmod: str, priority: str) -> str:
    return (
        "<url>\n"
        f"<loc>{loc}</loc>\n"
        f"<lastmod>{lastmod}</lastmod>\n"
        f"<priority>{priority}</priority>\n"
        "</url>"
    )


def main() -> None:
    lastmod = f"{date.today().isoformat()}T00:00:00+00:00"
    rows = json.loads(SEED.read_text(encoding="utf-8"))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        url_entry(f"{BASE}/", lastmod, "1.00"),
        url_entry(f"{BASE}/newreleasenotes.html", lastmod, "0.90"),
        url_entry(f"{BASE}/divyaprabandham_counts.php?env=prod", lastmod, "0.80"),
        url_entry(f"{BASE}/divyadesam_alwar_matrix.php?env=prod", lastmod, "0.80"),
    ]
    for row in rows:
        name = str(row.get("padham_prefix") or row.get("prabandham") or "").strip()
        if not name:
            continue
        loc = f"{BASE}/index.php?padhamPrefix={quote(name, safe='')}"
        parts.append(url_entry(loc, lastmod, "0.70"))
    parts.append("</urlset>")
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(rows)} prabandham URLs + hubs)")


if __name__ == "__main__":
    main()
