---
name: prabandham-ingest
description: End-to-end workflow for adding a new prabandham or pasuram range to the Nalayira Divya Prabandham site - scrape (tidley/dravidaveda/Excel), manual text ingest, transliterate, themes, load POC DB, update counts, rebuild Kannadi release notes, promote POC UI to UAT. Use when the user asks to ingest, scrape, add, or load a prabandham, pasuram range, padhaartham, thaniyan, promote test1.php, or to update release notes or counts after a data load.
---

# Prabandham Ingest Pipeline

Adds pasuram rows to the site DB and regenerates derived pages.
Full path-by-path reference: [docs/PASURAM_INGESTION_PIPELINE.md](../../../docs/PASURAM_INGESTION_PIPELINE.md).

## Ground rules

- **POC-first**: apply only to the POC table (`poc/config.ini` → `PasuramsArthamTablePOC`) unless the user explicitly asks for UAT/prod. Production DB loads are always manual (user's process).
- **Dry-run first**: never `--apply` before a dry-run whose counts match user expectations.
- **Never touch thaniyans** on replace: thaniyan rows are `PasuramNumber = 0` (PattuNumber = thaniyan index). Pasuram-range deletes must not include 0.
- Run everything from the repo root with `poc/.venv/bin/python`.
- Confirm before starting: prabandham name, PasuramNumber range, PattuNumber mapping, Alzwar, Title convention, source, Divyadesam (if any).

## Environments

| Env | Config | Table | Search UI | Kannadi release notes |
|-----|--------|-------|-----------|----------------------|
| POC | `poc/config.ini` | `PasuramsArthamTablePOC` | `pocindex.php` | `public_html/newreleasenotespoc.html` |
| UAT | `poc/config.test.ini` | `PasuramsArthamTableTest` | `test1.php` | `public_html/newreleasenotestest.html` |
| Prod | `poc/config.prod.ini` | `PasuramsArthamTable` | `index.php` | `public_html/newreleasenotes.html` |

## Workflow

```
Progress:
- [ ] 1. Scraper / parser module (or reuse existing path)
- [ ] 2. Ingest dry-run + spot-check
- [ ] 3. Apply to POC DB + verify
- [ ] 4. Counts seed + reseed
- [ ] 5. V1_SPECS + rebuild release notes
- [ ] 5b. Pathigam search aliases (if pathigam-box prabandham)
- [ ] 6. (Optional) Promote POC UI → UAT
```

### Step 1 — Source module

| Source | Template |
|--------|----------|
| Tidley table-padham | `iramanusa_nootranthathi_tidley.py` + `ingest_iramanusa_nootranthathi.py` |
| Manual text (`poc/pasuram.txt`) | `upadesa_rathnamalai_manual.py` + `ingest_upadesa_rathnamalai.py` |
| Dravidaveda / Excel | See [docs/PASURAM_INGESTION_PIPELINE.md](../../../docs/PASURAM_INGESTION_PIPELINE.md) paths A–E |
| Dravidaveda பெரிய திருமொழி patthu | `ingest_periya_thirumozhi_patthu<N>.py` (copy patthu 3) |

Tidley quirks: mislabeled verse numbers, missing verses, unnumbered verses, orphan பதவுரை tables — surface to the user; inject fixes from `poc/pasuram.txt` when needed.

### Path G — Manual text (no padham)

For prabandhams with **Title + Pasuram + Simple Explanation** only (no பதவுரை lines).

**One DB row per pattu:** `Pasuram` = verse, `Title` = optional heading, `Meaning` = simple explanation, `Word`/`Padham` empty, `PadhamNumber` = 1.

**UI:** `pocindex.php` shows `Meaning` in the PadhaArtham column (no leading ` - ` when `Word` is empty).

**Template:** `poc/scrapers/upadesa_rathnamalai_manual.py`, `poc/scrapers/ingest_upadesa_rathnamalai.py`.

```bash
poc/.venv/bin/python poc/scrapers/ingest_upadesa_rathnamalai.py --config poc/config.ini --dry-run --no-themes
poc/.venv/bin/python poc/scrapers/ingest_upadesa_rathnamalai.py --config poc/config.ini --apply --no-themes
```

- Deletes `PasuramNumber` range + replaces thaniyan by `PattuNumber` + `Prabandham LIKE` (does not use `--no-themes` for themes unless user wants none).
- Thaniyan: separate block in source file → `PasuramNumber=0`, next free `PattuNumber`.
- Shared `PasuramNumber` for multiple pattus is OK (e.g. pattu 73+74 → same number); verify with `(PasuramNumber, PattuNumber)` not padham duplicates.

**Worked example — உபதேச ரத்னமாலை:** 3885–3957, pattu 1–72 sequential, 73+74 → 3957, thaniyan pattu 50, Alzwar மாமுனிகள் (74 → எறும்பி அப்பா), 74 rows in counts, no themes, POC release notes only.

### Path H — Dravidaveda பெரிய திருமொழி patthu (padham + titles)

**Template:** `poc/scrapers/ingest_periya_thirumozhi_patthu10.py` (numeric-only, explicit `PATHIGAMS` ranges) or `patthu7` (category crawl). Copy per patthu with new range + `PATHU_NUMBER`. Do **not** derive pathigam bounds with modulo-10 from the first pasuram.

**Pick the source path first:** `curl -sI https://www.dravidaveda.org/<first_pasuram>/`. If the page
serves padhavurai (patthus 8–11 did), copy patthu 10 and skip the crawler entirely; if not
(patthus 6–7), copy patthu 7's category crawl.

**Pre-flight on `poc/pasuram.txt` before writing scripts** — cheap and catches most surprises:
count the `N-p-v` verse markers (not always 100 — patthu 10 is 104, 11 is 80), confirm every
marker has a non-empty commentary block, check for duplicate blocks, and check short names
against `build_pathigam_catalog()` for collisions.

```bash
poc/.venv/bin/python poc/scrapers/ingest_periya_thirumozhi_patthu10.py --config poc/config.ini --dry-run
poc/.venv/bin/python poc/scrapers/ingest_periya_thirumozhi_patthu10.py --config poc/config.ini --apply --skip-scrape
poc/.venv/bin/python poc/scripts/apply_periya_thirumozhi_patthu10_titles.py --apply
poc/.venv/bin/python poc/scripts/replace_periya_thirumozhi_patthu10_pasuram_from_txt.py --apply
```

`--skip-scrape` on apply reuses the dry-run's scraped JSON — a 100-page crawl takes ~8 minutes, so never scrape twice.

- **Dravidaveda only** for Padham/Meaning; flag 404/empty pages, do not backfill from other sites (crawler warns and continues; ingest injects pasuram-only stubs).
- **Titles** from `poc/pasuram.txt` via `apply_periya_thirumozhi_patthu<N>_titles.py` — `(10-N–short) (divyadesam) - (ஸ்ரீ பெரியவாச்சான் பிள்ளை)` + per-verse commentary; pathigam heading in `SimilarWords` for every verse in the pathigam. Numbered DD suffixes (e.g. திரு நறையூர் 8) are pathigam ordinals at the same Divyadesam. Keep Title-section short names as written even when the verse spelling differs (10-4 `சந்தமலர் க்குழல்`, 11-1 `குன்றமொன்`).
- **Don't assume one Divyadesam per patthu.** Patthus 6–8 were single-DD with ordinals 1…10; patthu 9 spans eight DDs. Patthus 10–11 are **sparse** in `DivyaDesamTable` — do not invent DD rows; omit the Title DD bracket when `pasuram.txt` has none; keep non-DD second-brackets as written.
- **Context bracket is per pathigam, not per patthu** — include the extra bracket only where `pasuram.txt` supplies one.
- **Pasuram readability** — after ingest, replace verse text only from `poc/pasuram.txt` (`replace_periya_thirumozhi_patthu<N>_pasuram_from_txt.py`); keeps padhavurai/Title/SimilarWords. If the source file duplicates a patthu (patthu 11), use the first copy and cut at the next block's `verse_block_start` plus `Title :`. Anchor verse-suffix regex at EOL so mid-line quotes (e.g. `திருவாய்மொழி -10-8-2-`) are ignored.
- Extend `V1_SPECS` end for `periya_thirumozhi` + add pathigam links in `poc/data/release_notes_link_source.html`; extend `classify_entries` end ≤ **2031** in `build_newreleasenote_poc.py`.
- **Counts seed:** bump the `பெரிய திருமொழி` `total_count` **and** the திருமங்கையாழ்வார் `alwar_subtotal` (subtotal = sum of that Āzhvār's rows; the page recomputes it for display, so a stale value is cosmetic only).
- **Release notes:** `build_newreleasenote_poc_v1.py` auto-builds **திவ்யப் பிரபந்தங்கள்** jump-nav box after நித்யாநுஸந்தானம் (`#prab-<key>` anchors). Rebuild UAT/Prod only after user verifies POC.
- **Duplicate short names across patthus are fine** (8-5 and 7-5 are both `தந்தை காலில்`): the alias catalog is keyed by pasuram range, so prefixed aliases stay unique. Only the bare Tamil alias becomes ambiguous — confirm with the user.

**Worked example — பத்தாம் + பதினொன்றாம் பத்து:** 1848–1951 (10-1…10-10, **104** verses; 10-7 = 14) and 1952–2031 (11-1…11-8, **80** verses); Alzwar திருமங்கையாழ்வார்; **184/184** from Dravidaveda via direct `/{n}/`; 1374 + 1121 padham rows; no stubs; sparse DD (13/104 and 14/80 already mapped); Title short names as written; counts 900 → **1084**, alwar_subtotal 953 → **1137**, footer **4058**. Prabandham complete in POC (948–2031).

**Earlier example — ஒன்பதாம் பத்து:** 1748–1847, 9-1…9-10, Alzwar திருமங்கையாழ்வார்; **100/100** from Dravidaveda via direct `/{n}/` (no crawler); 1567 padham rows; eight Divyadesams (கண்ணங்குடி, நாகை, புல்லாணி 1–2, குறுங்குடி 1–2, வல்லவாழ், மாலிருஞ்சோலை 1–2, கோட்டியூர்); context bracket only for 9-2…9-5 and 9-9; counts 797 → **897**, alwar_subtotal 850 → **950**.

**Earlier example — எட்டாம் பத்து:** 1648–1747, 8-1…8-10; **100/100** from Dravidaveda via direct `/{n}/`; 1508 padham rows; all pathigams திரு கண்ணபுரம் 1…10; context bracket in Title only for 8-1…8-4.

**Earlier example — ஏழாம் பத்து:** 1548–1647, 7-1…7-10; **100/100** from Dravidaveda (7-1…7-9 category crawl; 7-10 numeric `/{n}/`); titles + pasuram from `poc/pasuram.txt`.

**Earlier example — ஆறாம் பத்து:** 1448–1547, 6-1…6-10; 99/100 from Dravidaveda at ingest; **1485** (6-4-8) padhavurai backfilled in POC later (17 padham rows).

### Step 2 — Dry-run (padham prabandhams)

```bash
poc/.venv/bin/python poc/scrapers/ingest_<name>.py --config poc/config.ini --dry-run --no-themes
```

Check: section count, padham rows, first/last/quirky verses. Review `poc/output/<name>_poc.json`, `lookupsimilarwords/reviews/<name>_*.csv`.

### Step 3 — Apply + verify

```bash
poc/.venv/bin/python poc/scrapers/ingest_<name>.py --config poc/config.ini --apply
```

Verify: distinct PasuramNumbers, Alzwar/Prabandham, thaniyans untouched. Duplicate check (padham prabandhams):

```sql
SELECT PasuramNumber, PadhamNumber, COUNT(*) FROM PasuramsArthamTablePOC
WHERE PasuramNumber BETWEEN <START> AND <END>
GROUP BY PasuramNumber, PadhamNumber HAVING COUNT(*) > 1;
```

For no-padham prabandhams with shared PasuramNumber, also check `(PasuramNumber, PattuNumber, PadhamNumber)`.

### Step 4 — Counts

Edit `public_html/divyaprabandham_counts_seed.json`, then:

```bash
poc/.venv/bin/python poc/scripts/seed_divyaprabandham_counts.py --config poc/config.ini --apply
```

### Step 5 — Release notes

Add to `V1_SPECS` in `poc/scripts/build_newreleasenote_poc_v1.py` (`kannadi_index`, `full_width` for 30+ pasurams).

Pathigam links live in `poc/data/release_notes_link_source.html` (parsed by `build_newreleasenote_poc.py`).

```bash
poc/.venv/bin/python poc/scripts/build_newreleasenote_poc_v1.py --env poc
```

Build `--env test` / `--env prod` only when asked. For pages before manual DB load, use `--config poc/config.ini` so Kannadi openings come from POC data.

### Step 5b — Pathigam search aliases (pathigam-box prabandhams)

Release-note pathigam links must search an **unambiguous** prefixed term, not a bare short name that appears in many pasurams.

**Applies to:** பெரியாழ்வார் திருமொழி, நாச்சியார் திருமொழி, பெருமாள் திருமொழி, பெரிய திருமொழி, திருவாய்மொழி.

**Alias formats:**
- Patthu–pathigam: `{P}-{N} {short}` — e.g. `2-1 வானவர்`, `1-3 முற்ற மூத்து`
- நாச்சியார் / பெருமாள்: `{N}-{short}` — e.g. `1-தையொரு திங்களும்`, `4-ஊனேறு`

**What the script does:**
1. Builds catalog from `release_notes_link_source.html` (+ `RANGE_OVERRIDES` in `pathigam_search_aliases.py`)
2. Merges alias into `SimilarWords` for every pasuram in the pathigam range
3. Rewrites `padhamPrefix` in link source to the prefixed form
4. Optionally rebuilds POC release notes

```bash
poc/.venv/bin/python poc/scripts/apply_pathigam_search_aliases.py --dry-run
poc/.venv/bin/python poc/scripts/apply_pathigam_search_aliases.py --apply --rebuild-release-notes
```

**User-validated overrides** (`RANGE_OVERRIDES`): பெரியாழ்வார் 2-4/2-7/2-8 use pathigam names; 1-9 `வட்டு நடுவே`; PT 1-1 `வாடினேன் வாடி`; PT 1-3 `முற்ற மூத்து`.

After adding new pathigam rows to link source, re-run `--apply --rebuild-release-notes`. Spot-check: `pocindex.php?padhamPrefix=5-3+வென்றி` → exactly that pathigam's pasuram count.

### Step 5c — SuggestedWords (padham autocomplete)

`autocomplete.php` reads table `SuggestedWords` (not live `SimilarWords`). Rebuild after ingest or pathigam alias updates so users see new terms, pasuram numbers (e.g. `2048`), and pathigam codes (e.g. `1-2`, `2-4 நீராட்டம்`).

```bash
poc/.venv/bin/python poc/scripts/refresh_suggested_words.py --dry-run
poc/.venv/bin/python poc/scripts/refresh_suggested_words.py --apply
```

Merges POC + prod pasuram tables by default. **Satellite projects** (separate tables/pages): run with `--table YourSatelliteTable` only, or add a dedicated `SuggestedWords*` table + matching `autocomplete` endpoint — same token logic, different source.

Legacy PHP: `public_html/update_suggested_words.php` (same logic, slower on server).

### Step 6 — Promote POC UI → UAT

When `pocindex.php` UI changes should match on UAT, copy and rewire (do **not** point UAT at the POC table):

```bash
cd public_html
cp pocindex.php test1.php
sed -i '' \
  -e 's/pocindex\.php/test1.php/g' \
  -e 's/PasuramsArthamTablePOC/PasuramsArthamTableTest/g' \
  -e 's/newreleasenotespoc\.html/newreleasenotestest.html/g' \
  -e 's/env=poc/env=test/g' \
  -e 's/poc_build_search_conditions/build_search_conditions/g' \
  test1.php
```

Upload `test1.php`. UAT data still requires a separate load into `PasuramsArthamTableTest`.

## Verify in UI

- POC: `pocindex.php?padhamPrefix=<prabandham or number>`
- UAT: `test1.php?padhamPrefix=<prabandham or number>`

Green **Title** when non-empty; red **PattuNumber**; thaniyan shows Acharyar from `Alzwar`; search uses `SimilarWords LIKE`.
