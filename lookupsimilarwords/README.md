# Similar Words Lookup

Extract padham-level intelligence from the database for vetting and POC automation.

**Full ingestion pipeline (scrape, load, deploy):** [docs/PASURAM_INGESTION_PIPELINE.md](../docs/PASURAM_INGESTION_PIPELINE.md) — this README covers **theme detectors and vetting** only.

## Theme registry (Rules 1–9)

All themes are defined in [`theme_registry.json`](theme_registry.json). Each theme has:

- **query_concepts** — searched in `SimilarWords` when mining POC
- **aliases** — appended to every padham row when the pasuram triggers
- **meaning_keyword_seeds** / **padham_substring_seeds** — strong signal detectors

| Theme ID | Aliases appended |
|----------|------------------|
| `mahabharatham` | மகாபாரதம், mahabharatham |
| `sivan` | சிவன், sivan |
| `gajendran` | Gajendran, கஜேந்திரன் |
| `sangu` | sangu, சங்கு |
| `chakkaram` | chakaram, சக்கரம், நேமி, nemi, ஆழி, Aazhi |
| `ramayana` | Ramayanam, இராமாயணம், Raman, இராமன், காகுத்தன், Kaguthan |
| `vamanan` | வாமனன், திருவிக்ரமன், vamanan, thiruvikraman |
| `narasimha` | நரசிம்ம, நரசிம்மா, நரசிங்கா, narsimaa, narsimha, narasimha, Narasinga, narasimhan, narasimhar, நரசிம்மன், நரசிம்ஹன், நரசிம்ஹர், நரஸிம்ம |
| `garudan` | கருடன், Garudan, பெரிய திருவடி, Periya Thiruvadi |

**Multi-theme pasurams:** each theme is evaluated independently. If a pasuram triggers MB and Ramayana, **all aliases from both themes** are unioned onto every row in that pasuram.

## Workflow per theme

### 1. Extract tagged rows for vetting (training corpus from `SimilarWords`)

```bash
poc/.venv/bin/python lookupsimilarwords/extract_concept_lookup.py \
  --config poc/config.ini \
  --theme ramayana
```

Writes `lookupsimilarwords/extracts/{theme}_lookup.json` and `.csv`.

### 1c. Full POC scan from training (Padham + Meaning on all ~29K rows)

After `build_theme_detector.py`, scan which pasurams would receive theme aliases:

```bash
poc/.venv/bin/python lookupsimilarwords/scan_poc_theme_from_training.py --theme narasimha
```

Writes `lookupsimilarwords/reviews/{theme}_poc_full_scan.json` and `.csv`.

Apply aliases to approved pasurams in POC (dry-run default; use `--apply` to write):

```bash
poc/.venv/bin/python lookupsimilarwords/apply_poc_theme_from_scan.py --theme narasimha
poc/.venv/bin/python lookupsimilarwords/apply_poc_theme_from_scan.py --theme narasimha --apply
poc/.venv/bin/python lookupsimilarwords/apply_poc_theme_from_scan.py --theme garudan --exclude 2244 --apply
```

### 1b. Review candidate signals (before tuning seeds)

```bash
poc/.venv/bin/python lookupsimilarwords/review_theme_signals.py --theme ramayana
```

Writes `lookupsimilarwords/reviews/{theme}_candidate_signals.csv`, `{theme}_strong_lines_review.csv`, `{theme}_signal_review.json`. For Ramayana, filters to the **76 pasurams** where `SimilarWords` contains `Ramayanam`.

### 2. Build detector from POC

Mines strong signals from rows already tagged in `PasuramsArthamTablePOC`:

```bash
poc/.venv/bin/python lookupsimilarwords/build_theme_detector.py --theme ramayana
poc/.venv/bin/python lookupsimilarwords/build_theme_detector.py --all
```

Output: `lookupsimilarwords/detectors/{theme}_detector.json`

Legacy MB wrapper still works:

```bash
poc/.venv/bin/python lookupsimilarwords/build_mahabharatham_detector.py --config poc/config.ini
```

### 3. Validate (POC + Excel)

```bash
poc/.venv/bin/python lookupsimilarwords/validate_theme_detectors.py --theme all
poc/.venv/bin/python lookupsimilarwords/validate_mb_detector.py   # MB only
```

Writes per theme: `{theme}_validation_poc.json`, `thiruvandhathi_{theme}_report.json/.csv`, and `all_themes_validation_summary.json`.

### 4. Scan workbook

```bash
poc/.venv/bin/python lookupsimilarwords/scan_workbook_themes.py --theme all
poc/.venv/bin/python lookupsimilarwords/scan_workbook_mb.py        # MB only (legacy)
```

Combined report: `thiruvandhathi_all_themes_report.json` (lists `themes_triggered` per pasuram).

### 5. Fill workbook + load POC

```bash
poc/.venv/bin/python poc/fill_workbook.py --input Thiruvandhathi2and3.xlsx --themes all
poc/.venv/bin/python poc/load_workbook.py --input-json poc/output/thiruvandhathi_filled.json \
  --replace-range 2182 2381
```

Use `--no-themes` to skip pasuram-wide tagging. All writes go to **`PasuramsArthamTablePOC` only** (override table with `--config` / `--table`).

## Apply themes to a pasuram range (in-place SimilarWords update)

Use when padham rows **already exist** in the DB and you want to refresh theme aliases without reloading JSON. Evaluates **all** registered themes (or a subset) on `Padham` + `Meaning` per pasuram.

**Early prabandham blocks** (one command for all):

| Range | Content |
|-------|---------|
| 1–12 | திருப்பல்லாண்டு |
| 152–161 | பெரியாழ்வார் 2-4 நீராட்டம் |
| 182–201 | 2-7 பூச்சூடல், 2-8 காப்பிடல் |
| 463–503 | Thiruppavai + Periyazhvar 5-4 |
| 917–947 | திருப்பள்ளியெழுச்சி, அமலனாதிபிரான், கண்ணிநுண்சிறுத்தாம்பு |

```bash
# Dry-run on POC
poc/.venv/bin/python lookupsimilarwords/apply_themes_to_range.py \
  --config poc/config.ini --early-prabandhams

# Apply on Test (UAT)
poc/.venv/bin/python lookupsimilarwords/apply_themes_to_range.py \
  --config poc/config.test.ini --early-prabandhams --apply

# Custom range
poc/.venv/bin/python lookupsimilarwords/apply_themes_to_range.py \
  --config poc/config.ini --start 474 --end 503 --apply
```

Review CSV: `lookupsimilarwords/reviews/early_prabandhams_{start}_{end}_theme_apply.csv` (or per-range when using `--start`/`--end`).

**Notable hits after early apply:** `vamanan` on Thiruppavai **476, 490, 497**; Narasimha does not auto-trigger in Thiruppavai except manual override on **496** (see below).

### Manual pasuram theme overrides

When detector rules miss a pasuram (e.g. `சீரிய சிங்கம்` = Narasinga on pasuram **496**):

```bash
poc/.venv/bin/python lookupsimilarwords/apply_theme_overrides.py \
  --config poc/config.ini --apply
```

Edit [`theme_pasuram_overrides.json`](theme_pasuram_overrides.json) before running.

## Detection rules

- **Pasuram-wide tagging:** if any padham line in a pasuram matches → append theme aliases to **every** row in that pasuram
- **Strong signals only:** `padham_substring_signals` on Padham OR `meaning_keywords` on Meaning
- **No global padham-exact lists** (avoids false positives on generic words like அன்று)
- MB uses parenthesis normalization: `(பாரத) யுத்த` → matches `பாரத யுத்த`

## Tests

```bash
poc/.venv/bin/python lookupsimilarwords/test_pasuram_themes.py
```

## Legacy

[`extract_lookup.py`](extract_lookup.py) and [`similar_word_lookup.json`](similar_word_lookup.json) are deprecated — do not use for new theme work.

## Configuration

DB settings from `poc/config.ini` `[db]`. Override table with `--table`.
