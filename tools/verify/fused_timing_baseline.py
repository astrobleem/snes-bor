"""Digest-pinned loader for the accepted fused-coverage timing receipt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


RECEIPT_SHA256 = 'fc1a9f5a77ceba0e8d945addb044306d1327308b547a0f4c54d87c89564b2221'
BASE_ROM_SHA256 = '0ad890b7390e83e593596e456469fece2ab37ab9378ac733c80b581a56841edd'
DEFAULT_RECEIPT = (Path(__file__).resolve().parents[2] / 'docs' / 'receipts'
                   / 'byor-motu-exact-coverage.json')


class TimingBaselineContractError(ValueError):
    """Raised when the pinned baseline receipt is missing or inconsistent."""


def load_timing_baseline(path: str | Path = DEFAULT_RECEIPT) -> dict[str, Any]:
    """Read once, verify the exact receipt bytes, then parse those same bytes."""
    try:
        raw = Path(path).read_bytes()
    except (OSError, TypeError, ValueError) as exc:
        raise TimingBaselineContractError('FTB_RECEIPT_UNREADABLE') from exc

    actual = hashlib.sha256(raw).hexdigest()
    if actual != RECEIPT_SHA256:
        raise TimingBaselineContractError('FTB_RECEIPT_SHA256')

    try:
        receipt = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TimingBaselineContractError('FTB_RECEIPT_JSON') from exc
    if not isinstance(receipt, dict):
        raise TimingBaselineContractError('FTB_RECEIPT_OBJECT')
    if receipt.get('candidate_rom_sha256') != BASE_ROM_SHA256:
        raise TimingBaselineContractError('FTB_BASE_ROM_IDENTITY')
    return receipt
