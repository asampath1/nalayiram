#!/usr/bin/env python3
"""Validate MB detector — thin wrapper around validate_theme_detectors.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lookupsimilarwords.validate_theme_detectors import main as validate_main


if __name__ == "__main__":
    if "--theme" not in sys.argv:
        sys.argv.extend(["--theme", "mahabharatham"])
    validate_main()
