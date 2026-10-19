"""Fuse the two scratch-to-staging copies in the bounded Q8 staging path.

This transform targets the accepted BYOR MOTU reference publisher.  The source
copy is bank $42:$D680..$D6CF and the destination is bank $00 at the $72 DP
pointer.  The original two-MVN body remains intact as the fallback.
"""
from __future__ import annotations

from collections.abc import Sequence


CODE_START = 0x39AB00
CODE_LIMIT = 0x39B000

# Pin the caller's index-7 bypass and complete staging body.  Only the call to
# Q7SourceFromIndex is redirected; the legacy copy sequence remains byte-for-
# byte present after its newly named entry point.
CALLER_ANCHOR = [
    'lda.l $42D660', 'asl a', 'tax', 'lda $2C',
    'sta.l $42D662,x', 'lda.l $42D660', 'sta $70',
    'lda $70', 'cmp #7', 'bne Q8StageCopy', 'jmp Q8ScratchNoStage',
    'Q8StageCopy:', '.a16', '.i16', 'jsr Q7SourceFromIndex',
    'phb', 'lda #63', 'ldx #$D680', 'ldy $72',
    'mvn $00,$42', 'plb', 'phb', 'lda #15',
    'ldx #$D6C0', 'lda $72', 'clc', 'adc #64', 'tay',
    'lda #15', 'mvn $00,$42', 'plb', 'Q8ScratchNoStage:',
]

SOURCE_ANCHOR = [
    'Q7SourceFromIndex:', '.a16', '.i16', 'lda $70', 'cmp #6',
    'bne Q7NormalSource', 'Q7SpillSource:', '.a16', '.i16',
    'lda #$34B0', 'sta $72', 'rts', 'Q7NormalSource:', '.a16', '.i16',
    'lda $70', 'asl a', 'asl a', 'asl a', 'asl a',
    'sta $74', 'asl a', 'asl a', 'clc', 'adc $74', 'clc',
    'adc #$3500', 'sta $72', 'rts', 'Q7CodeEnd:',
]

ROUTINE = [
    '.bank 57', '.org $AB00', 'PpStart:', '.a16', '.i16',
    ' jsr Q7SourceFromIndex',
    # Read the saved P byte in accumulator-8 mode.  This detects decimal mode
    # without changing D or disturbing the 16-bit X/Y widths.
    ' php', ' sep #$20', '.a8', ' pla', ' and #$08',
    ' beq PpBinary', ' jmp PpFallback8', 'PpBinary:', '.a16', '.i16',
    ' rep #$20', '.a16',
    # The caller bypasses index 7.  The helper still fails closed for any
    # out-of-contract index if entered directly or after future source drift.
    ' lda $70', ' cmp #7', ' bcc PpIndexInRange', ' jmp PpFallback',
    'PpIndexInRange:', '.a16', '.i16', ' cmp #6',
    ' bne PpNormal', ' bra PpSpill',
    'PpNormal:', '.a16', '.i16',
    # Validate the normal D=0 destination from Q7's existing $74 scratch
    # (16*index), without adding a second direct-page write.
    ' lda $74', ' asl a', ' asl a', ' clc', ' adc $74', ' clc',
    ' adc #$3500', ' cmp $72', ' beq PpNormalDestination', ' jmp PpFallback',
    'PpNormalDestination:', '.a16', '.i16', ' bra PpFast',
    'PpSpill:', '.a16', '.i16',
    ' lda $72', ' cmp #$34B0', ' beq PpSpillDestination', ' jmp PpFallback',
    'PpSpillDestination:', '.a16', '.i16',
    'PpFast:', '.a16', '.i16',
    # Compute the original continuation Y and C/V. Both old +64 and
    # replacement +80 are in range for every pinned staging destination.
    ' lda $72', ' clc', ' adc #80', ' tay', ' ldx $72',
    # Keep the caller DBR on stack, then use a symmetric PEA word to set DBR
    # to $42 without changing A/X/Y or C/V.
    ' phb', ' pea $4242', ' plb', ' plb',
    'PpCopyStart:', '.a16', '.i16',
]

# Copy source words from bank $42 scratch to bank $00 staging in ascending
# byte order. Absolute-long indexed stores do not alter X; each LDA/STA pair
# therefore writes exactly the next two bytes at the validated $72 base.
for _offset in range(0, 80, 2):
    ROUTINE.extend((f' lda ${0xD680 + _offset:04X}',
                    f' sta.l ${_offset:06X},x'))

ROUTINE.extend([
    ' lda #$FFFF', ' ldx #$D6D0', ' plb', ' jmp Q8ScratchNoStage',
    'PpFallback8:', '.a16', '.i16', ' rep #$20',
    'PpFallback:', '.a16', '.i16',
    ' jmp PpLegacyAfterSource', 'PpCodeEnd:', '.a16', '.i16',
])


class PreloadPairContractError(ValueError):
    """Raised when the pinned staging copy or scratch producer has drifted."""


def transform(lines: Sequence[str], enabled: bool = True) -> list[str]:
    """Route the pinned staging call through the fused 80-byte copy helper.

    Disabled mode is an exact identity.  Enabled mode is fail-closed on source
    drift, duplicate anchors, prior installation, or duplicate helper labels.
    """
    result = list(lines)
    if not enabled:
        return result
    normalized = [line.strip() for line in result]
    labels = {'PpStart:', 'PpBinary:', 'PpIndexInRange:', 'PpNormal:',
              'PpNormalDestination:', 'PpSpill:', 'PpSpillDestination:',
              'PpFast:', 'PpCopyStart:', 'PpFallback8:', 'PpFallback:',
              'PpCodeEnd:', 'PpLegacyAfterSource:'}
    if any(label in normalized for label in labels):
        raise PreloadPairContractError('PRELOAD_PAIR_ALREADY_INSTALLED')
    if normalized.count('Q8StageCopy:') != 1 or normalized.count('Q8ScratchNoStage:') != 1:
        raise PreloadPairContractError('PRELOAD_PAIR_STAGE_LABELS')
    if normalized.count('Q7SourceFromIndex:') != 1 or normalized.count('Q7CodeEnd:') != 1:
        raise PreloadPairContractError('PRELOAD_PAIR_SOURCE_LABELS')
    callers = [i for i in range(len(result) - len(CALLER_ANCHOR) + 1)
               if normalized[i:i + len(CALLER_ANCHOR)] == CALLER_ANCHOR]
    sources = [i for i in range(len(result) - len(SOURCE_ANCHOR) + 1)
               if normalized[i:i + len(SOURCE_ANCHOR)] == SOURCE_ANCHOR]
    if len(callers) != 1:
        raise PreloadPairContractError('PRELOAD_PAIR_PINNED_CALLER')
    if len(sources) != 1:
        raise PreloadPairContractError('PRELOAD_PAIR_PINNED_SOURCE')
    start = callers[0]
    call = start + CALLER_ANCHOR.index('jsr Q7SourceFromIndex')
    result[call] = ' jmp PpStart'
    # The original two MVNs are preserved as the decimal/out-of-contract path.
    # The helper calls Q7 exactly once, then tail-jumps here when it falls back.
    after_call = call + 1
    result.insert(after_call, 'PpLegacyAfterSource:')
    return result + ROUTINE

