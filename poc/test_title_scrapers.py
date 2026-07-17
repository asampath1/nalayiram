"""Tests for tidley title parsing (multi-paragraph commentary)."""
from __future__ import annotations

from poc.title_scrapers.base import join_title_blocks
from poc.title_scrapers.tidley import parse_tidley_paragraphs


def test_join_title_blocks_preserves_multiple_internal_lines():
    block = (
        "ப்ரஹ்மாதிகளும் அறிய ஒண்ணாத படி இருக்கிற ஸ்ரீ சர்வேஸ்வரன் என்னுடைய ஹிருதயத்திலே வந்து புகுந்தான் –\n"
        "இது போலே இருக்கும் நன்மை யுண்டோ -என்கிறார்-\n"
        "செவ்விப் பூக்களை கொண்டு ஏத்துகிற ருத்ரனும் சதுர்முகனும்-வாய் விட்டு ஏத்த மாட்டாத-\n"
        "ஸ்ரீ சர்வாதிகன் என் உள்ளத்தைக் கலந்தான் -அவ்வழகையும் மேன்மையும் உடையவன் என்கை-"
    )
    title = join_title_blocks([block])
    assert "ஸ்ரீ சர்வாதிகன் என் உள்ளத்தைக் கலந்தான்" in title
    assert "ப்ரஹ்மாதிகளும் அறிய ஒண்ணாத" in title


def test_first_pasuram_uses_intro_commentary_as_title():
    paragraphs = [
        "intro block one",
        "intro block two",
        "நான்முகனை நாராயணன் படைத்தான்\nசிந்தாமல் கொண்மினீர் தேர்ந்து–1-",
        "——————-",
        "commentary for pasuram 2",
        "line two\nof pasuram two\nthird line\nfourth –2-",
    ]
    records = parse_tidley_paragraphs(paragraphs, pasuram_number_base=2381)
    assert records[0].pattu_number == 1
    assert records[0].pasuram_number == 2382
    assert records[0].title == "intro block one intro block two"
    assert records[1].title == "commentary for pasuram 2"


def test_irandam_title_override_for_2182():
    from poc.title_scrapers.base import PasuramTitleRecord
    from poc.title_scrapers.overrides import apply_title_overrides

    records = [
        PasuramTitleRecord(
            pattu_number=1,
            pasuram_number=2182,
            pasuram="pasuram text",
            title="long scraped intro",
        )
    ]
    override = "ப்ராப்த விஷயத்தில் பிறந்த பிரேம பரம்பரைகளாலே"
    updated = apply_title_overrides(records, {2182: override})
    assert updated[0].title == override
    assert "long scraped intro" not in updated[0].title


def test_moondram_prefix_applied_from_2283():
    from poc.title_scrapers.base import PasuramTitleRecord
    from poc.title_scrapers.moondram_tidley import COMMENTARY_PREFIX
    from poc.title_scrapers.overrides import apply_title_prefix

    records = [
        PasuramTitleRecord(1, 2282, "p1", COMMENTARY_PREFIX + " intro commentary"),
        PasuramTitleRecord(2, 2283, "p2", "per-pattu commentary"),
    ]
    updated = apply_title_prefix(records, COMMENTARY_PREFIX, from_pasuram_number=2283)
    assert updated[0].title.count("நம்பிள்ளை") == 1
    assert updated[1].title.startswith(COMMENTARY_PREFIX)
    assert "per-pattu commentary" in updated[1].title
