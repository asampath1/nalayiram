#!/usr/bin/env python3
"""Build Mahabharata detector — thin wrapper around build_theme_detector.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from lookupsimilarwords.build_theme_detector import build_theme
from lookupsimilarwords.config import load_db_config
from lookupsimilarwords.theme_registry import DEFAULT_DETECTORS_DIR


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build MB detector from POC")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--table", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_DETECTORS_DIR))
    args = parser.parse_args()

    db_config = load_db_config(Path(args.config))
    if args.table:
        db_config["table"] = args.table
    build_theme("mahabharatham", db_config, Path(args.output_dir))


if __name__ == "__main__":
    main()
