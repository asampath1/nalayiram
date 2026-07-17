#!/usr/bin/env python3
"""Export POC records to JSON in the desired format."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def export_to_json(records: List[Dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
    print(f"Exported {len(records)} records to {output_path}")
