# UAT: Test table loads and verification

**Full pipeline:** [docs/PASURAM_INGESTION_PIPELINE.md](../docs/PASURAM_INGESTION_PIPELINE.md)

**UI:** `public_html/test1.php` (queries `PasuramsArthamTableTest`)

**Config:** [poc/config.test.ini](config.test.ini) → table `PasuramsArthamTableTest`

Swap `--config poc/config.test.ini` for any POC command to target UAT.

---

## Thiruvandhathi padham load (2182–2381)

```bash
# 1. Regenerate JSON if Excel/themes changed
poc/.venv/bin/python poc/fill_workbook.py --input Thiruvandhathi2and3.xlsx --themes all

# 2. Dry-run delete + insert into Test
poc/.venv/bin/python poc/load_workbook.py \
  --config poc/config.test.ini \
  --input-json poc/output/thiruvandhathi_filled.json \
  --replace-range 2182 2381 \
  --dry-run

# 3. Apply to Test
poc/.venv/bin/python poc/load_workbook.py \
  --config poc/config.test.ini \
  --input-json poc/output/thiruvandhathi_filled.json \
  --replace-range 2182 2381
```

**Duplicate check (Test DB):**

```sql
SELECT PasuramNumber, PadhamNumber, COUNT(*) AS cnt
FROM PasuramsArthamTableTest
WHERE PasuramNumber BETWEEN 2182 AND 2381
GROUP BY PasuramNumber, PadhamNumber
HAVING COUNT(*) > 1;
```

Expect **zero rows**.

---

## Commentary titles (Excel → Test)

```bash
poc/.venv/bin/python poc/title_scrapers/apply_titles_from_excel.py \
  --xlsx thiruppavai-commentary.xlsx \
  --config poc/config.test.ini --apply --skip-export

poc/.venv/bin/python poc/title_scrapers/apply_titles_from_excel.py \
  --xlsx thirupalliyezhuchi-commentary.xlsx \
  --config poc/config.test.ini --apply --skip-export

poc/.venv/bin/python poc/title_scrapers/apply_titles_from_excel.py \
  --xlsx Amalanadipiran-commentary.xlsx \
  --config poc/config.test.ini --apply --skip-export
```

| Workbook | Pasurams | Spot-check on test1.php |
|----------|----------|-------------------------|
| `thiruppavai-commentary.xlsx` | 474–503 | 474, 496, 503 |
| `thirupalliyezhuchi-commentary.xlsx` | 917–926, thaniyans 19/20 | 917, thaniyan Pattu 19 |
| `Amalanadipiran-commentary.xlsx` | 927–947 | 927, 947 |
| `thiruppallandu-commentary.xlsx` | 1–12 | 1, 12 |

---

## Periyazhvar vilakku urai (tidley → Test)

Title format: `(section) - vilakku text`

```bash
for s in neerattam poochoodal kappidal senniyongu; do
  poc/.venv/bin/python poc/title_scrapers/append_neerattam_vilakku.py \
    --section "$s" --config poc/config.test.ini --apply
done
```

| Section | Pasurams |
|---------|----------|
| `neerattam` | 152–161 |
| `poochoodal` | 182–191 |
| `kappidal` | 192–201 |
| `senniyongu` | 463–473 |

Spot-check **152** — should start with `(2-4 நீராட்டம்) -`.

---

## Early-prabandham themes (SimilarWords → Test)

```bash
poc/.venv/bin/python lookupsimilarwords/apply_themes_to_range.py \
  --config poc/config.test.ini --early-prabandhams --apply

poc/.venv/bin/python lookupsimilarwords/apply_theme_overrides.py \
  --config poc/config.test.ini --apply
```

Theme search spot-checks on `test1.php`:

| Search | Expect (examples) |
|--------|-------------------|
| `vamanan` / வாமனன் | Thiruppavai 476, 490, 497 |
| `narasimha` | Pasuram 496 (manual override) |
| `Gajendran` | Thiruppalliyezhuchi 917+ |

---

## Thiruvandhathi UAT checklist (`test1.php`)

### Setup

- [ ] Open UAT site: `test1.php` (not `pocindex.php` / not production `index.php`).
- [ ] Confirm load completed (~2346 rows for pasurams 2182–2381).

### Display (per pasuram row)

- [ ] **PasuramNumber** link works (e.g. `?padhamPrefix=2213`).
- [ ] **Prabandham** is `இரண்டாம் திருவந்தாதி` (2182–2281) or `மூன்றாம் திருவந்தாதி` (2282–2381).
- [ ] **PattuNumber** (red): 2182→1 … 2281→100; 2282→1 … 2381→100.
- [ ] **Title** (green): only when pasuram has commentary; empty for most padham-only lines.
- [ ] **Padham column**: red `Word` (`padham, Transliteration`) — blue `Meaning`.

### Theme search (`SimilarWords` aliases)

| Search term | Expect (examples) | Avoid false positives |
|-------------|-------------------|------------------------|
| Ramayana theme alias | 2233 (Ramayana only) | 2213 not Ramayana-only noise |
| Mahabharatham | 2309 | — |
| Sangu / Chakkaram | 2213 | — |
| Sivan | 2198, 2244, 2277 | not சிவந்த-only |
| Vamanan | 2272, 2242, 2364, 2270 | not 2212 |
| Gajendran | 2194, 2256 | not 2310 |
| Narasimha (`narasimha`, `நரசிங்கம்`) | 2199, 2228, 2265, 2312, 2323 | not 2226 (அரிய) |
| Garudan (`Garudan`, `Periya Thiruvadi`) | 2273, 2277, 2338 | not 2244 (Rudra) |

### Regression (blocked stems)

- [ ] `?padhamPrefix=2213` — sangu/chakkaram themes, not spurious Ramayana from substring.
- [ ] Pasuram **2196** / **2197** — theme tags present if report says so.
- [ ] Spot-check **2281** (last of Irandam) and **2381** (last of Moonraam): PattuNumber = 100.

### Compare to POC (optional)

- [ ] Same pasuram on `pocindex.php` vs `test1.php` — same PattuNumber, Word, Meaning, theme search behavior after Test load.

### Sign-off

- [ ] No duplicate `(PasuramNumber, PadhamNumber)` in Test for loaded ranges.
- [ ] Stakeholder OK → promote to `PasuramsArthamTable` only when ready (separate process).
