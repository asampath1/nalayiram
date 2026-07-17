# Nalayiram Prompts — prabandham-ingest

Prompt examples for the `/prabandham-ingest` skill (`.cursor/skills/prabandham-ingest/SKILL.md`).
Use in Agent mode. The skill auto-loads on ingest/scrape/load requests, or type `/prabandham-ingest` to attach it explicitly.

## Prompt templates

### Start a new ingest

> Ingest <prabandham name> from tidley.
> URLs: <url1>, <url2>, …
> Range <START>–<END>, PattuNumber 1–<N>, Alzwar <name>, Title empty, no Divyadesam.
> Thaniyan already in DB — do not touch.

### Report a source quirk

> Verse <n> is mislabeled on tidley (starts with "<first words>"). Verse <m> is missing;
> I have put its text and padham/meaning lines in poc/input/<prabandham>_<verse>_manual.txt.

### Apply after dry-run looks good

> Dry-run counts look right. Apply to POC with themes and verify.

### Counts + release notes (POC)

> Update the counts table and rebuild the POC release notes for the new prabandham.

### UAT/Prod release notes before manual DB load

> Update UAT and Prod release notes as well. I will do the manual DB update.

### Verify

> Spot-check pasurams <first>, <last>, and <quirky ones> in the POC DB and on
> pocindex.php?padhamPrefix=<prabandham name>.

## What each prompt triggers

| You say | Agent behavior (from the skill) |
|---------|-------------------------------|
| "Ingest [prabandham] from tidley, range X–Y" | Asks you to confirm range/Alzwar/Title/source if missing, copies the `iramanusa_nootranthathi_tidley.py` template, dry-runs with `--no-themes`, shows you counts before any `--apply` |
| "Verse 75 is mislabeled on tidley, 76 is missing" | Handles it as a known tidley quirk — remaps/injects from a manual text file, reports the anomaly instead of guessing |
| "Apply it to POC" | Runs `--apply` (delete range + reinsert), then verifies distinct pasuram count, Alzwar, thaniyan rows untouched, duplicate-check SQL |
| "Update the counts and release notes" | Edits `divyaprabandham_counts_seed.json` + reseeds, adds `V1_SPECS` entry, rebuilds `newreleasenotespoc.html` |
| "Update UAT and prod release notes too, I'll do the DB manually" | Builds `--env test` / `--env prod` with `--config poc/config.ini` so openings render from POC data; links resolve after the manual DB load |

## Worked example (இராமாநுச நூற்றந்தாதி, July 2026)

- Range 3777–3884, PattuNumber 1–108, Alzwar திருவரங்கத்து அமுதனார், Title empty, no Divyadesam.
- Source: 5 tidley URLs (1–7, 8–21, 22–44, 45–77, 78–108).
- Quirks: verse 75 mislabeled `–76-` on tidley; real 76 missing, supplied via `poc/input/iramanusa_76_manual.txt`; verse 7 unnumbered; verse 59 orphan பதவுரை table.
- Result: 108 pasurams, 1264 padham rows in POC; counts row 25 (அமுதனார், 108); Kannadi section in all three release-notes files.
