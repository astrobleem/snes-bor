"""Exact boolean coverage at the Q8 mark callsite, with row early exit.

OnlineRowMask remains the authority for clipping, alignment, transparency and
fixed foreground occlusion. Only NbMarkTest consumes coverage as a boolean.
The original full-mask OnlineCoverage routine remains available unchanged.
All early-exit state is caller scratch, reinitialized by OnlineRowPointers at
the next cell. No cached coverage, memory lease or allocation policy is added.
"""
from __future__ import annotations
from collections.abc import Sequence

CODE_START = 0x39A700
CODE_LIMIT = 0x39B000
ANCHOR = [
    'NbMarkTest:', '.a16', '.i16', 'lda.l $42D674',
    'beq NbUseSourcePresence', 'jsr OnlineCoverage',
    'bra NbPresenceChecked', 'NbUseSourcePresence:', '.a16', '.i16',
    'jsr WarmSourcePresence', 'NbPresenceChecked:', '.a16', '.i16', 'cmp #0',
    'beq NbMarkNext',
]
ROUTINE = [
    '.bank 57', '.org $A700', 'EcCoverage:', '.a16', '.i16',
    ' jsr OnlineRowPointers', ' lda #0', ' sta $58',
    'EcCoverageRow:', '.a16', '.i16', ' jsr OnlineRowMask', ' inc $58',
    ' lda $32', ' bne EcHit', ' jsr OnlineStepRow', ' lda $58',
    ' cmp #8', ' bcc EcCoverageRow', ' lda #0',
    'EcHit:', '.a16', '.i16', ' rts', 'EcCodeEnd:', '.a16', '.i16',
]


class ExactCoverageContractError(ValueError):
    pass


def fast_coverage(row_masks: Sequence[int]) -> tuple[bool, int]:
    """Reference boolean reduction of eight already exact u16 row masks."""
    if len(row_masks) != 8 or any(type(x) is not int or not 0 <= x <= 65535
                                  for x in row_masks):
        raise ValueError('EC_EIGHT_U16_ROWS_REQUIRED')
    for visited, mask in enumerate(row_masks, 1):
        if mask:
            return True, visited
    return False, 8


def transform(lines: Sequence[str], enabled: bool = True) -> list[str]:
    """Replace one pinned boolean call; keep every original instruction fixed."""
    result = list(lines)
    if not enabled:
        return result
    normalized = [x.strip() for x in result]
    if any(x.startswith('Ec') and x.endswith(':') for x in normalized):
        raise ExactCoverageContractError('EC_ALREADY_INSTALLED')
    hits = [i for i in range(len(result) - len(ANCHOR) + 1)
            if normalized[i:i + len(ANCHOR)] == ANCHOR]
    if len(hits) != 1 or normalized.count('NbMarkTest:') != 1:
        raise ExactCoverageContractError('EC_PINNED_BOOLEAN_CALLSITE')
    if normalized.count('OnlineCoverage:') != 1:
        raise ExactCoverageContractError('EC_ORIGINAL_COVERAGE_REQUIRED')
    index = hits[0] + ANCHOR.index('jsr OnlineCoverage')
    result[index] = result[index].replace('jsr OnlineCoverage', 'jsr EcCoverage')
    return result + ROUTINE
