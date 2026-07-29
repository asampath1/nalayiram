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

**Template:** `poc/scrapers/ingest_periya_thirumozhi_patthu3.py` → copy for each patthu (`patthu4`, range 1248–1347, `PATHU_NUMBER=4`).

```bash
poc/.venv/bin/python poc/scrapers/ingest_periya_thirumozhi_patthu4.py --config poc/config.ini --dry-run --no-themes
poc/.venv/bin/python poc/scrapers/ingest_periya_thirumozhi_patthu4.py --config poc/config.ini --apply
poc/.venv/bin/python poc/scripts/apply_periya_thirumozhi_patthu4_titles.py --apply
poc/.venv/bin/python poc/scripts/replace_periya_thirumozhi_patthu4_pasuram_from_txt.py --apply
```

- **Dravidaveda only** for Padham/Meaning; flag 404 pasurams, do not backfill from other sites.
- **Titles** from `poc/pasuram.txt` via `apply_periya_thirumozhi_patthu<N>_titles.py` — `(4-N–short) (divyadesam) - (ஸ்ரீ பெரியவாச்சான் பிள்ளை)` + per-verse commentary; pathigam heading in `SimilarWords` for all 10 pasurams.
- **Pasuram readability** — after ingest, replace verse text only from `poc/pasuram.txt` (`replace_periya_thirumozhi_patthu<N>_pasuram_from_txt.py`); keeps padhavurai/Title/SimilarWords.
- Extend `V1_SPECS` end for `periya_thirumozhi` + add pathigam links in `poc/data/release_notes_link_source.html`; extend `classify_entries` end ≤ 1347 in `build_newreleasenote_poc.py`.
- **Release notes:** `build_newreleasenote_poc_v1.py` auto-builds **திவ்யப் பிரபந்தங்கள்** jump-nav box after நித்யாநுஸந்தானம் (`#prab-<key>` anchors).

**Worked example — நான்காம் பத்து:** 1248–1347, 4-1…4-10, Alzwar திருமங்கையாழ்வார்; 97/100 from Dravidaveda (1330–1332 missing); titles + pasuram from `poc/pasuram.txt`; 4-8-1…6 share one title block.

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

Add to `V1_SPECS` in `poc/scripts/build_newreleasenote_poc_v1.py` (`kannadi_index`, `full_width` for 30+ pasurams):

```bash
poc/.venv/bin/python poc/scripts/build_newreleasenote_poc_v1.py --env poc
```

Build `--env test` / `--env prod` only when asked. For pages before manual DB load, use `--config poc/config.ini` so Kannadi openings come from POC data.

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
