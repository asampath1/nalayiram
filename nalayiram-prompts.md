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
| "Ingest பெரிய திருமொழி patthu from Dravidaveda" | `ingest_periya_thirumozhi_patthu<N>.py` + titles + optional pasuram replace |
| "Fix pathigam search / pathigam links" | `apply_pathigam_search_aliases.py --apply --rebuild-release-notes` |
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
- Titles: `apply_periya_thirumozhi_patthu4_titles.py`; Pasuram spacing: `replace_periya_thirumozhi_patthu4_pasuram_from_txt.py`.
- Release notes: `periya_thirumozhi` V1_SPECS to 1347; jump-nav **திவ்யப் பிரபந்தங்கள்** box (POC/UAT/Prod).

### Pathigam search aliases (216 pathigams, 5 prabandhams)

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
