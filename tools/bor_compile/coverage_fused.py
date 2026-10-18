"""Fused exact boolean coverage scanner for the NbMarkTest callsite.

The overlay keeps OnlineRowPointers as the single authority for initial
projection/clipping and reproduces OnlineRowMask and OnlineStepRow inline.
The planar $0C/$0E step state is intentionally unused by this boolean path.
"""
from __future__ import annotations

from collections.abc import Sequence


CODE_START = 0x39A740
CODE_LIMIT = 0x39B000

ANCHOR = [
    'NbMarkTest:', '.a16', '.i16', 'lda.l $42D674',
    'beq NbUseSourcePresence', 'jsr EcCoverage',
    'bra NbPresenceChecked', 'NbUseSourcePresence:', '.a16', '.i16',
    'jsr WarmSourcePresence', 'NbPresenceChecked:', '.a16', '.i16',
    'cmp #0', 'beq NbMarkNext',
]

ROUTINE = [
    '.bank 57', '.org $A740', 'FcCoverage:', '.a16', '.i16',
    ' jsr OnlineRowPointers',
    ' lda #0', ' sta $58',
    'FcCoverageRow:', '.a16', '.i16',
    ' lda #0', ' sta $32',
    ' lda $56', ' cmp $46', ' bcs FcMaskDone',
    ' ldx $54', ' sep #$20', '.a8',
    ' lda.l $F40000,x', ' rep #$20', '.a16',
    ' and #255', ' eor #255', ' sta $32',
    ' xba', ' ora $32', ' ldy #0',
    ' and [$08],y', ' sta $32',
    'FcMaskDone:', '.a16', '.i16',
    ' inc $58', ' lda $32', ' bne FcCovered',
    ' lda $56', ' bmi FcStepNegative',
    ' lda $08', ' clc', ' adc $48', ' sta $08',
    ' lda $0A', ' adc #0', ' sta $0A',
    'FcStepNegative:', '.a16', '.i16',
    ' inc $56', ' inc $54',
    ' lda $58', ' cmp #8', ' bcc FcCoverageRow',
    ' lda #0', ' bra FcHit',
    'FcCovered:', '.a16', '.i16', ' lda #1',
    'FcHit:', '.a16', '.i16', ' rts',
    'FcCodeEnd:', '.a16', '.i16',
]


class CoverageFusedContractError(ValueError):
    """Raised when the source cannot be safely overlaid at the pinned site."""


def transform(lines: Sequence[str], enabled: bool = True) -> list[str]:
    """Retarget exactly the pinned boolean call and append the fixed overlay."""
    result = list(lines)
    if not enabled:
        return result
    normalized = [line.strip() for line in result]
    if any(line.startswith('Fc') and line.endswith(':') for line in normalized):
        raise CoverageFusedContractError('FC_ALREADY_INSTALLED')
    matches = [i for i in range(len(result) - len(ANCHOR) + 1)
               if normalized[i:i + len(ANCHOR)] == ANCHOR]
    if len(matches) != 1 or normalized.count('NbMarkTest:') != 1:
        raise CoverageFusedContractError('FC_PINNED_BOOLEAN_CALLSITE')
    if normalized.count('EcCoverage:') != 1:
        raise CoverageFusedContractError('FC_ORIGINAL_EC_REQUIRED')
    if normalized.count('OnlineCoverage:') != 1:
        raise CoverageFusedContractError('FC_ORIGINAL_COVERAGE_REQUIRED')
    call = matches[0] + ANCHOR.index('jsr EcCoverage')
    result[call] = result[call].replace('jsr EcCoverage', 'jsr FcCoverage')
    return result + ROUTINE
