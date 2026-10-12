# Nalayiram Prompts — prabandham-ingest

Prompt examples for the `/prabandham-ingest` skill (`.cursor/skills/prabandham-ingest/SKILL.md`).
Use in Agent mode. The skill auto-loads on ingest/scrape/load requests, or type `/prabandham-ingest` to attach it explicitly.

## Prompt templates

### Start a new ingest (tidley)

> Ingest <prabandham name> from tidley.
> URLs: <url1>, <url2>, …
> Range <START>–<END>, PattuNumber 1–<N>, Alzwar <name>, Title empty, no Divyadesam.
> Thaniyan already in DB — do not touch.

### Start a new ingest (manual text, no padham)

> Ingest <prabandham name> from poc/pasuram.txt.
> Range <START>–<END>, PattuNumber 1–<N>, Alzwar <name>.
> No padhavurai — Title + Pasuram + Simple Explanation in Meaning column.
> Thaniyan in file → load as PasuramNumber=0, PattuNumber=<N>.
> POC only; no themes; no Divyadesam.

### Replace Pasuram text from pasuram.txt (readability)

> Replace Pasuram verse text for பெரிய திருமொழி patthu <N> from poc/pasuram.txt. Keep padhavurai and titles unchanged.

### Start a new ingest (Dravidaveda பெரிய திருமொழி patthu)

> Ingest பெரிய திருமொழி <ordinal> பத்து from Dravidaveda.
> Range <START>–<END>, pathigams <P>-1 to <P>-10, Alzwar திருமங்கையாழ்வார்.
> Titles from poc/pasuram.txt; apply all themes; pathigam headings in SimilarWords.
> Flag missing Dravidaveda pages; then replace Pasuram text from pasuram.txt.
> POC only.

The short form works too once `poc/pasuram.txt` holds the patthu — the agent probes
`dravidaveda.org/{first}/`, runs the pre-flight checks, and reports before applying:

> Ready for the next in sequence is <ordinal> பத்து (<START>–<END>). poc/pasuram.txt

### Report a source quirk

> Verse <n> is mislabeled on tidley (starts with "<first words>"). Verse <m> is missing;
> I have put its text and padham/meaning lines in poc/pasuram.txt.

### Apply after dry-run looks good

> Dry-run counts look right. Apply to POC and verify.

### Counts + release notes (POC)

> Update the counts table and rebuild the POC release notes for the new prabandham.

### UAT/Prod release notes before manual DB load

> Update UAT and Prod release notes as well. I will do the manual DB update.

### Promote POC UI to UAT

> Upgrade POC UI changes to Test (UAT) — copy pocindex.php to test1.php with UAT table/URLs.

### Verify

> Spot-check pasurams <first>, <last>, and <quirky ones> in the POC DB and on
> pocindex.php?padhamPrefix=<prabandham name>.

### Apply திருவாய்மொழி Titles from a tidley விளக்க உரை page

> Apply Titles for திருவாய்மொழி <N-M shortname> (<START>–<END>) from this tidley URL.
> Format `(N-M–shortname) - (commentary)`. POC only; do not change SimilarWords, padham, or verse text.
> Mode: before-verse / after-padhavurai / hybrid (combination of 4-10 and 5-8).

### Divya Desam matrix order (region-wise, POC)

> Order the Divya Desam × Alwar matrix by the LIFCO region list. POC only. Do not change counts.

### சாற்றுமுறை SimilarWords (POC)

> Add `சாற்றுமுறை,satrumurai` to SimilarWords on these PasuramNumbers. POC only. Dry-run first; skip if already tagged.

### Pathigam search aliases (release-note links)

> Fix pathigam links so pocindex search returns only that pathigam's pasurams.
> Add prefixed aliases to SimilarWords and update release-note padhamPrefix URLs.

> Apply pathigam search aliases for all pathigam prabandhams and rebuild POC release notes.

## What each prompt triggers

| You say | Agent behavior (from the skill) |
|---------|-------------------------------|
| "Ingest [prabandham] from tidley, range X–Y" | Confirms specs, uses `iramanusa_nootranthathi_tidley.py` template, dry-run, apply POC |
| "Ingest from poc/pasuram.txt" | Uses `upadesa_rathnamalai_manual.py` template; one row per pattu; `--no-themes` unless asked |
| "Verse 75 mislabeled on tidley, 76 is missing" | Remaps/injects from `poc/pasuram.txt`; reports anomaly |
| "Apply it to POC" | `--apply`, verify counts, thaniyans untouched, duplicate SQL |
| "Update the counts and release notes" | `divyaprabandham_counts_seed.json` + reseed + `V1_SPECS` + rebuild POC release notes |
| "Update UAT and prod release notes too, I'll do the DB manually" | `--env test`/`prod` with `--config poc/config.ini` for Kannadi from POC data |
| "Upgrade POC UI to UAT" | `cp pocindex.php test1.php` + sed swaps for table, URLs, `env=test` |
| "Replace Pasuram from pasuram.txt" | `replace_periya_thirumozhi_patthu<N>_pasuram_from_txt.py --apply` |
| "Ingest பெரிய திருமொழி patthu from Dravidaveda" | Probes `/{n}/` for a direct source, pre-flights `pasuram.txt`, then `ingest_periya_thirumozhi_patthu<N>.py` + titles + pasuram replace |
| "Fix pathigam search / pathigam links" | `apply_pathigam_search_aliases.py --apply --rebuild-release-notes` |
| "Apply திருவாய்மொழி Titles from tidley" | `apply_thiruvaimozhi_tidley_titles.py --mode before-verse\|after-padhavurai\|hybrid --apply` |
| "Order Divya Desams by region / LIFCO" | `includes/divyadesam_regions_poc.php`; matrix `?env=poc` + `divyadesamautocomplete.php?env=poc` |
| "Add சாற்றுமுறை,satrumurai on these PNs" | CONCAT SimilarWords on all padham rows of those PasuramNumbers; skip if already tagged |
| "Refresh autocomplete / suggested words" | `refresh_suggested_words.py --apply` (after ingest or alias updates) |

## Worked examples

### இராமாநுச நூற்றந்தாதி (tidley)

- Range 3777–3884, PattuNumber 1–108, Alzwar திருவரங்கத்து அமுதனார், Title empty.
- Source: 5 tidley URLs; quirks: verse 75 mislabeled, 76 from `poc/pasuram.txt`.
- Result: 108 pasurams, 1264 padham rows; counts row 25; Kannadi in all three release-notes files.

### உபதேச ரத்னமாலை (manual text)

- Range 3885–3957; pattu 1–72 sequential; **73 and 74 both → 3957**.
- Alzwar ஸ்ரீ மணவாள மாமுனிகள் (pattu 74 → ஸ்ரீ எறும்பி அப்பா); thaniyan pattu 50.
- Source: `poc/pasuram.txt` (Title / Pasuram / Simple Explanation); no padham, no themes.
- Scripts: `upadesa_rathnamalai_manual.py`, `ingest_upadesa_rathnamalai.py`.
- Result: 75 DB rows (74 verses + thaniyan); counts sort 26 (74); POC release notes only.

### POC UI → UAT

- Copied `pocindex.php` → `test1.php` with `PasuramsArthamTableTest`, `test1.php` links, `env=test`, `newreleasenotestest.html`.
- Mobile layout, thaniyan display, PadhaArtham Show/Hide, `prabandhamPrefix` search, **Clear** / **Top** links — parity with POC.

### பெரிய திருமொழி நான்காம் பத்து (Dravidaveda + pasuram.txt)

- Range 1248–1347, pathigams 4-1…4-10, Alzwar திருமங்கையாழ்வார், themes on.
- Dravidaveda padhavurai; **97/100** loaded (1330–1332 404 on Dravidaveda).
- **Gap closed 2026-08-17** — 1330–1332 backfilled from a manual `poc/pasuram.txt` block via `ingest_periya_thirumozhi_1330_1332.py`; padhavurai partial, coverage logged to `lookupsimilarwords/reviews/`.
- Titles: `apply_periya_thirumozhi_patthu4_titles.py`; Pasuram spacing: `replace_periya_thirumozhi_patthu4_pasuram_from_txt.py`.
- Release notes: `periya_thirumozhi` V1_SPECS to 1347; jump-nav **திவ்யப் பிரபந்தங்கள்** box (POC/UAT/Prod).

### பெரிய திருமொழி ஐந்தாம் பத்து (Dravidaveda + pasuram.txt)

- Range 1348–1447, pathigams 5-1…5-10, Alzwar திருமங்கையாழ்வார், themes on.
- Dravidaveda category crawl; **100/100** padhavurai loaded.
- Titles: `apply_periya_thirumozhi_patthu5_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu5_pasuram_from_txt.py`.
- **Flag:** 5-9-1…5 (1428–1432) — empty Title (no commentary in `pasuram.txt`).
- Release notes: `periya_thirumozhi` V1_SPECS to 1447.

### பெரிய திருமொழி ஆறாம் பத்து (Dravidaveda + pasuram.txt)

- Range 1448–1547, pathigams 6-1…6-10, Alzwar திருமங்கையாழ்வார், themes on.
- Dravidaveda category crawl; **99/100** padhavurai at ingest. **1485** / 6-4-8 later backfilled in POC (17 padham rows).
- Titles: `apply_periya_thirumozhi_patthu6_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu6_pasuram_from_txt.py`.
- Pathigam 6-1 short name **வண்டுணும்** (exceptional; verse line uses `வண்டுண்`).
- Release notes: `periya_thirumozhi` V1_SPECS to **1547**; POC counts **597** for பெரிய திருமொழி.

### பெரிய திருமொழி ஏழாம் பத்து (Dravidaveda + pasuram.txt)

- Range 1548–1647, pathigams 7-1…7-10, Alzwar திருமங்கையாழ்வார், themes on.
- 7-1…7-9 category crawl; 7-10 numeric `/{n}/`; **100/100** padhavurai.
- Titles: `apply_periya_thirumozhi_patthu7_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu7_pasuram_from_txt.py`.
- திரு நறையூர் 8/9/10 = pathigam ordinals at the same Divyadesam.
- Release notes: `periya_thirumozhi` V1_SPECS to **1647**; POC counts **697**; UAT/Prod after POC verify.

### பெரிய திருமொழி எட்டாம் பத்து (Dravidaveda numeric + pasuram.txt)

- Range 1648–1747, pathigams 8-1…8-10, Alzwar திருமங்கையாழ்வார், themes on.
- **No crawler** — `dravidaveda.org/{n}/` served padhavurai for all 100; **100/100**, 1508 padham rows.
- Titles: `apply_periya_thirumozhi_patthu8_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu8_pasuram_from_txt.py`.
- All ten pathigams are திரு கண்ணபுரம் 1…10 (ordinals at one Divyadesam); context bracket only for 8-1…8-4.
- 8-5 short name `தந்தை காலில்` duplicates 7-5 — accepted; bare-term search returns both pathigams.
- Release notes: V1_SPECS to **1747**; POC counts **797**, alwar_subtotal **850**.

### பெரிய திருமொழி ஒன்பதாம் பத்து (Dravidaveda numeric + pasuram.txt)

- Range 1748–1847, pathigams 9-1…9-10, Alzwar திருமங்கையாழ்வார், themes on.
- **No crawler** — direct `/{n}/` again; **100/100**, 1567 padham rows, nothing flagged.
- Titles: `apply_periya_thirumozhi_patthu9_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu9_pasuram_from_txt.py`.
- **First multi-Divyadesam patthu** — eight DDs (கண்ணங்குடி, நாகை, புல்லாணி 1–2, குறுங்குடி 1–2, வல்லவாழ், மாலிருஞ்சோலை 1–2, கோட்டியூர்); the trailing 1/2 are still pathigam ordinals at one DD.
- Context bracket only for 9-2…9-5 and 9-9.
- Common-word short names (`எங்கள்`, `முந்துற`, `மூவரில்`, `காவார்`) — no catalog collision, but search with the prefixed alias.
- Release notes: V1_SPECS to **1847**; POC counts **897**, alwar_subtotal **950**, footer total **3871**.

### பெரிய திருமொழி பத்தாம் பத்து (Dravidaveda numeric + pasuram.txt)

- Range **1848–1951**, pathigams 10-1…10-10, **104** pasurams (not 100). Alzwar திருமங்கையாழ்வார், themes on.
- **10-7 மானமுடைத்து is 14 verses (1908–1921)** — accepted. Use explicit `PATHIGAMS`; do not modulo-10 from 1848. `PattuNumber` 1–14. Kannadi box lists all 14 openings.
- **No crawler** — direct `/{n}/`; **104/104**, 1374 padham rows, nothing flagged.
- Titles: `apply_periya_thirumozhi_patthu10_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu10_pasuram_from_txt.py`.
- Short name **10-4 `சந்தமலர் க்குழல்`** as in Title section (not verse `சந்த மலர்க் குழல்`).
- Sparse DD: only 13/104 already in `DivyaDesamTable` (10-1 has the 18 DDs for பதினெண் திருப்பதிகள்). Omit DD Title bracket when Title section has none. Keep non-DD second-brackets as written.

### பெரிய திருமொழி பதினொன்றாம் பத்து (Dravidaveda numeric + pasuram.txt)

- Range **1952–2031**, pathigams 11-1…11-8 only (**80** pasurams; no 11-9/11-10). Completes பெரிய திருமொழி (948–2031).
- **No crawler** — direct `/{n}/`; **80/80**, 1121 padham rows, nothing flagged.
- Titles: `apply_periya_thirumozhi_patthu11_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu11_pasuram_from_txt.py`.
- Short name **11-1 `குன்றமொன்`** as in Title section (not verse `குன்றம் ஓன்று`).
- `poc/pasuram.txt` duplicates this whole patthu — parsers use the first copy.
- Sparse DD: 14/80 already mapped. Context bracket only where Title section supplies one (11-5 திருச்சாழல்).
- Release notes: V1_SPECS / `classify_entries` to **2031**; POC counts **1084**, alwar_subtotal **1137**, footer total **4058**.

### Pathigam search aliases (பெரிய திருமொழி now 108 pathigams; 5 prabandhams)

Unambiguous pocindex search from Kannadi release-note pathigam links.

**Prabandhams:** பெரியாழ்வார் திருமொழி, நாச்சியார் திருமொழி, பெருமாள் திருமொழி, பெரிய திருமொழி, திருவாய்மொழி.

**Alias format:**
- Patthu–pathigam: `2-1 வானவர்`, `1-3 முற்ற மூத்து` (space after code)
- நாச்சியார் / பெருமாள்: `1-தையொரு திங்களும்`, `4-ஊனேறு` (hyphen, no space)

**Rule:** `padhamPrefix` in `poc/data/release_notes_link_source.html` must match the visible pathigam heading (e.g. `2-4+நீராட்டம்`, not bare `நீராட்டம்`).

**Overrides** (in `poc/scripts/pathigam_search_aliases.py` → `RANGE_OVERRIDES`):
- பெரியாழ்வார் 2-4/2-7/2-8 → pathigam name (நீராட்டம், பூச்சூடல், காப்பிடல்), not opening line
- பெரியாழ்வார் 1-9 → `1-9 வட்டு நடுவே` (+ extra `1-9 வட்டநடுவே`)
- பெரிய திருமொழி 1-1 → `1-1 வாடினேன் வாடி`; 1-3 → `1-3 முற்ற மூத்து`

```bash
poc/.venv/bin/python poc/scripts/apply_pathigam_search_aliases.py --dry-run
poc/.venv/bin/python poc/scripts/apply_pathigam_search_aliases.py --apply --rebuild-release-notes
```

Validation output (optional): `poc/output/pathigam_search_alias_validation.txt` / `.csv`.

**Verify:** `pocindex.php?padhamPrefix=2-4+நீராட்டம்` → 10 pasurams; bare `வென்றி` may still hit many — prefixed `5-3+வென்றி` → 10 only.

### திருவாய்மொழி Titles from tidley (POC)

Missed pathigam Titles, format `(N-M–shortname) - (commentary)`. Wrap `((விளி.) …)` when commentary already starts with `(`. Script: `poc/scripts/apply_thiruvaimozhi_tidley_titles.py`. Does **not** touch SimilarWords / padham / verse.

| Pathigam | Range | Mode | Notes |
|----------|-------|------|-------|
| 3-3 ஒழிவில் | 2919–2929 | `before-verse` | `***` before pasuram |
| 4-10 ஒன்றும் தேவும் | 3106–3116 | `before-verse` | same |
| 5-8 ஆரா அமுதே | 3194–3204 | `after-padhavurai` | first `***` para after padhavurai table |
| 6-10 உலகம் உண்ட பெருவாயா | 3326–3336 | `hybrid` | mix of before-verse and after-table |
| 7-2 கங்குலும் பகலும் | 3348–3358 | `hybrid` | |
| 7-4 ஆழி எழ | 3370–3380 | `hybrid` | 7-4-9 after-table `(அன்றுமண்ணீர்)` |

8-10, 9-10, 10-9, 10-10 already had Titles from earlier ingest — left as-is.

```bash
poc/.venv/bin/python poc/scripts/apply_thiruvaimozhi_tidley_titles.py \
  --source poc/input/thiruvaimozhi_7_4_tidley.md \
  --code 7-4 --short-name 'ஆழி எழ' --start 3370 --end 3380 --mode hybrid --apply
```

### Divya Desam region order (POC matrix + autocomplete)

LIFCO பொருளடக்கம்: 7 regions (சோழ 40, நடு 2, தொண்டை 22, வட 11, மலை 13, பாண்டிய 18, நில உலகில் இல்லாதவை 2). Names stay the existing bilingual strings from `divyadesamautocomplete.php` — PDF is order only; counts do not change.

- List: `public_html/includes/divyadesam_regions_poc.php`
- Matrix `?env=poc`: region heading rows (centered); `?env=test|prod` stay Tamil A→Z
- `pocindex.php` autocomplete: `divyadesamautocomplete.php?env=poc`
- Hostinger: create `public_html/includes/` and upload `divyadesam_regions_poc.php` (do not upload unused files)
- POC home header: மாமுனிகள் in the source line; drop redundant header **அடைவு** (nav still has the Kannadi link); example `1-1 வாடினேன் வாடி`
- Kannadi POC header: தேடல் முகப்பு + `divyadesam_alwar_matrix.php?env=poc`

### சாற்றுமுறை SimilarWords (POC, 2026-08-19)

Append `,சாற்றுமுறை,satrumurai` on all padham rows of the listed PasuramNumbers; skip if already tagged. Did **not** retouch tags through திருவாய்மொழி **3776**.

**Rule:** last of each pathigam for பெரிய / பெருமாள் திருமொழி (plus last-two where marked). For andhathis, thandagams, திருச்சந்த, இராமாநுச, உபதேச, நூற்றந்தாதி: last 2–3 of the **whole** work (not every decade). Numbers live in the satrumurai plan; உபதேச typo `33956` → **3956**.

- Applied **148** new PNs (2019 padham rows); **2081** already tagged; **149/149** on the list now searchable via `pocindex.php?padhamPrefix=சாற்றுமுறை`.

