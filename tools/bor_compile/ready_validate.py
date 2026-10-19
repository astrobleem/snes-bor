"""One-load-per-entry overlay for the synchronous READY map validator."""
from __future__ import annotations

from collections.abc import Sequence


CODE_START = 0x39A800
CODE_LIMIT = 0x39B000

# Pin the zero initialization too: the overlay starts X at zero and relies on
# this caller-side invariant before entering the replaced validation loop.
ANCHOR = [
    'BatchEpochNormal:', '.a16', '.i16', 'lda #0', 'sta $70',
    'NbValidate:', '.a16', '.i16', 'ldx $70', 'lda.l $42C000,x',
    'and #$8000', 'beq NbGuard2', 'jmp NbAbort',
    'NbGuard2:', '.a16', '.i16', 'lda.l $42C000,x', 'and #$3FFF',
    'cmp #768', 'bcc NbGuard3', 'jmp NbAbort',
    'NbGuard3:', '.a16', '.i16', 'sta.l $42C000,x', 'inc $70',
    'inc $70', 'lda $70', 'cmp #2048', 'bcc NbValidate',
    'lda.l $42D604', 'cmp.l $7FBA90', 'beq NbGuard4',
]

ROUTINE = [
    '.bank 57', '.org $A800', 'RvValidate:', '.a16', '.i16',
    ' ldx #0',
    'RvValidateLoop:', '.a16', '.i16',
    ' lda.l $42C000,x', ' bpl RvUntagged',
    ' lda #$8000', ' stx $70', ' jmp NbAbort',
    'RvUntagged:', '.a16', '.i16',
    ' and #$3FFF', ' cmp #768', ' bcc RvValid',
    ' stx $70', ' jmp NbAbort',
    'RvValid:', '.a16', '.i16',
    ' sta.l $42C000,x', ' inx', ' inx', ' cpx #2048',
    ' bcc RvValidateLoop', ' ldx #2046',
    ' .a16', '.i16',
    ' lda #2048', ' sta $70', ' cmp #2048', ' jmp RvContinue',
    'RvCodeEnd:', '.a16', '.i16',
]


class ReadyValidateContractError(ValueError):
    """Raised when the accepted READY loop cannot be safely overlaid."""


def transform(lines: Sequence[str], enabled: bool = True) -> list[str]:
    """Replace exactly the pinned six-byte loop prefix and append its overlay."""
    result = list(lines)
    if not enabled:
        return result
    normalized = [line.strip() for line in result]
    if any(line.startswith('Rv') and line.endswith(':') for line in normalized):
        raise ReadyValidateContractError('RV_ALREADY_INSTALLED')
    matches = [i for i in range(len(result) - len(ANCHOR) + 1)
               if normalized[i:i + len(ANCHOR)] == ANCHOR]
    if len(matches) != 1 or normalized.count('NbValidate:') != 1:
        raise ReadyValidateContractError('RV_PINNED_VALIDATE_LOOP')
    if normalized.count('NbAbort:') != 1:
        raise ReadyValidateContractError('RV_ABORT_REQUIRED')
    start = matches[0]
    ldx = start + ANCHOR.index('ldx $70')
    result[ldx:ldx + 2] = [' jmp RvValidate', ' nop', ' nop', ' nop']
    # The two replaced source instructions expand to four lines before the
    # continuation, so account for the two-line source growth.
    continuation = start + ANCHOR.index('lda.l $42D604') + 2
    result.insert(continuation, 'RvContinue:')
    return result + ROUTINE
