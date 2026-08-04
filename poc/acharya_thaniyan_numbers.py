"""Thaniyan PattuNumber slots for மாமுனிகள் prabandhams (PasuramNumber=0 in DB/UI)."""
from __future__ import annotations

UPADESA_THANIYAN_PATTU = 50
UPADESA_THANIYAN_PRABANDHAM = "உபதேச ரத்னமாலை - தனியன்"

THIRUVAIMOZHI_NOORRANTHATHI_THANIYAN_PRABANDHAMS = (
    "திருவாய்மொழி நூற்றந்தாதி - தனியன்-1",
    "திருவாய்மொழி நூற்றந்தாதி - தனியன்-2",
)
THIRUVAIMOZHI_NOORRANTHATHI_THANIYAN_PATTUS = (51, 52)

# Legacy PasuramNumbers from an earlier ingest attempt — clean up on re-apply.
LEGACY_THANIYAN_PASURAM_NUMBERS = (4058, 4059, 4060)


def thiruvaimozhi_thaniyan_pattu(header_index: int) -> int:
    """Map source header தனியன்-1 / தனியன்-2 → PattuNumber 51 / 52."""
    if header_index not in (1, 2):
        raise ValueError(f"Unexpected thaniyan header index {header_index}")
    return UPADESA_THANIYAN_PATTU + header_index
