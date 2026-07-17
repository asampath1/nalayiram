#!/usr/bin/env python3
"""Tests for pasuram context (NOTE) row merging."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from poc.orchestrate_poc import merge_comment_rows


def test_leading_note_merges_to_first_padham():
    records = [
        {"PasuramNumber": 2384, "Padham": "NOTE", "Meaning": "(எம்பெருமான்)"},
        {"PasuramNumber": 2384, "Padham": "பாலில்", "Meaning": "திருப்பாற்கடலில்"},
    ]
    out = merge_comment_rows(records)
    assert len(out) == 1
    assert out[0]["Padham"] == "பாலில்"
    assert out[0]["Meaning"] == "திருப்பாற்கடலில் (- (எம்பெருமான்))"


def test_mid_pasuram_note_merges_to_first_padham():
    records = [
        {"PasuramNumber": 2383, "Padham": "தேருங்கால்", "Meaning": "“ஆராயுமிடத்து."},
        {"PasuramNumber": 2383, "Padham": "NOTE", "Meaning": "எத்தவம் செய்தார்க்கும் (context)"},
        {"PasuramNumber": 2383, "Padham": "முடிவது", "Meaning": "முடிவில் பலனையளிப்பது"},
    ]
    out = merge_comment_rows(records)
    assert len(out) == 2
    assert "(- எத்தவம்" in out[0]["Meaning"]
    assert out[1]["Padham"] == "முடிவது"


if __name__ == "__main__":
    test_leading_note_merges_to_first_padham()
    test_mid_pasuram_note_merges_to_first_padham()
    print("OK")
