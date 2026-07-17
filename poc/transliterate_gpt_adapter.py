#!/usr/bin/env python3
"""Adapter to call the existing public_html/transliterateGPT.py script from the POC pipeline."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from typing import List

import pandas as pd


def _load_transliterate_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("transliterate_gpt", str(script_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def transliterate_with_public_html_script(texts: List[str], script_path: Path, dict_path: Path, output_path: Path) -> List[str]:
    script_path = script_path.resolve()
    module = _load_transliterate_module(script_path)

    input_path = output_path.with_suffix(".input.xlsx")
    df = pd.DataFrame({"Padam": texts})
    df.to_excel(input_path, index=False)

    # Monkey patch the module constants used by the existing script
    setattr(module, "INPUT_XLSX", str(input_path))
    setattr(module, "OUTPUT_XLSX", str(output_path))
    setattr(module, "DICT_PATH", str(dict_path))

    # Run the loaded main() function
    asyncio.run(module.main())

    if not output_path.exists():
        raise RuntimeError(f"Expected output file not created: {output_path}")

    output_df = pd.read_excel(output_path)
    if "Word" not in output_df.columns:
        raise RuntimeError("Transliteration output file missing 'Word' column")

    return output_df["Word"].astype(str).tolist()
