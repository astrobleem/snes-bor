"""Experimental 27-byte WFR1 run-loop specialization.

This module emits only the measured run-within-width block; it does not change
the generic decoder's validation, row traversal, failure exits, or leases.
Use ``patch_decoder`` only on a decoder containing the exact original block.
"""
from __future__ import annotations

import hashlib


RUN_BLOCK_BYTES = 27
RUN_WRITE_OFFSET = 15
GENERIC_BLOCK = """WarmRle_RunWithinWidth:
WarmRle_RunWrite:
 lda $1C
 beq WarmRle_RunDone
 lda $18
 clc
 adc $1A
 tax
 sep #$20
 lda $1E
 sta.l $7E8400,x
 rep #$20
 inc $1A
 dec $1C
 jmp WarmRle_RunWrite
"""

SPECIALIZED_BLOCK = """WarmRle_RunWithinWidth:
 sta $1A
 sec
 sbc $1C
 clc
 adc $18
 tax
 ldy $1C
 sep #$20
 lda $1E
WarmRle_RunWrite:
 sta.l $7E8400,x
 inx
 dey
 bne WarmRle_RunWrite
 rep #$20
 stz $1C
"""


def emit() -> str:
    """Return the replacement body, retaining the original continuation label."""
    return SPECIALIZED_BLOCK


def patch_decoder(code: str) -> str:
    """Replace the exact generic run block once; reject any other decoder shape."""
    if not isinstance(code, str):
        raise ValueError("WARM_RLE_RUN_CODE_TYPE")
    if code.count(GENERIC_BLOCK) != 1:
        raise ValueError("WARM_RLE_RUN_GENERIC_BLOCK_CARDINALITY")
    updated = code.replace(GENERIC_BLOCK, emit(), 1)
    if updated.count("WarmRle_RunDone:") != 1:
        raise ValueError("WARM_RLE_RUN_CONTINUATION_CARDINALITY")
    return updated


def evidence() -> dict[str, object]:
    snippet = emit()
    return {
        "schema": "BYOR_WARM_RLE_RUN_NATIVE_EXPERIMENT_V3",
        "block_bytes": RUN_BLOCK_BYTES,
        "run_write_offset": RUN_WRITE_OFFSET,
        "assembly_sha256": hashlib.sha256(snippet.encode("utf-8")).hexdigest(),
        "generic_block_sha256": hashlib.sha256(GENERIC_BLOCK.encode("utf-8")).hexdigest(),
        "preserves": ["A at end-column value until stored", "X/Y restored by outer decoder epilogue",
                      "caller P/DP/DBR/stack by outer decoder epilogue"],
        "additional_stack_use": 0,
        "run_count_storage": "$1C is cleared to zero with a 16-bit STZ after each successfully emitted run, matching the generic decoder's completed-run state; the unchanged validation and failure paths are retained.",
        "status": "experimental block only; no native or build acceptance claim",
    }

