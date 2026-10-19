"""Bounded fast lookup for the accepted borrowed-home invalidation scan."""
from __future__ import annotations

from collections.abc import Sequence


CODE_START = 0x39AB00
CODE_LIMIT = 0x39B000

# Pin the complete admission guards, original lookup loop, and mutation/return
# continuations. The overlay changes only the original LDX dispatch.
ANCHOR = [
    'BhInvalidate:', '.a16', '.i16', 'lda $2C', 'cmp #596',
    'bcc BhBranch28', 'jmp BhInvalidateOK',
    'BhBranch28:', '.a16', '.i16', 'lda.l $42D70C', 'cmp #1',
    'beq BhBranch29', 'jmp BhInvalidateBad',
    'BhBranch29:', '.a16', '.i16', 'ldx #0',
    'BhInvalidateFind:', '.a16', '.i16', 'txa', 'lsr a',
    'cmp.l $42D704', 'bcc BhBranch30', 'jmp BhInvalidateBad',
    'BhBranch30:', '.a16', '.i16', 'lda.l $42D710,x',
    'and #$3FFF', 'cmp $2C', 'bne BhBranch31',
    'jmp BhInvalidateFound',
    'BhBranch31:', '.a16', '.i16', 'inx', 'inx',
    'jmp BhInvalidateFind',
    'BhInvalidateFound:', '.a16', '.i16', 'phx', 'lda $2C',
    'asl a', 'tax', 'lda.l $42D000,x', 'and #$3FFF',
    'bne BhBranch32', 'jmp BhInvalidateUnreferenced',
    'BhBranch32:', '.a16', '.i16', 'plx', 'sec', 'rts',
    'BhInvalidateUnreferenced:', '.a16', '.i16', 'plx',
    'lda.l $42D710,x', 'ora #$4000', 'sta.l $42D710,x',
    'lda $2C', 'asl a', 'tax', 'lda.l $42D000,x',
    'ora #$8000', 'sta.l $42D000,x',
    'BhInvalidateOK:', '.a16', '.i16', 'clc', 'rts',
    'BhInvalidateBad:', '.a16', '.i16', 'sec', 'rts',
]

ROUTINE = [
    '.bank 57', '.org $AB00', 'IvFind:', '.a16', '.i16',
    ' phy', ' phb', ' pea $4242', ' plb', ' plb',
    ' lda $D704', ' cmp #597', ' bcs IvFallback',
    ' ldx #0', ' tay', ' beq IvMiss',
    'IvLoop:', '.a16', '.i16', ' lda $D710,x',
    ' and #$3FFF', ' cmp $2C', ' beq IvFound',
    ' inx', ' inx', ' dey', ' bne IvLoop', ' jmp IvMiss',
    'IvFound:', '.a16', '.i16', ' plb', ' ply',
    ' jmp BhInvalidateFound',
    'IvMiss:', '.a16', '.i16', ' plb', ' ply',
    ' txa', ' lsr a', ' cmp.l $42D704', ' jmp BhInvalidateBad',
    'IvFallback:', '.a16', '.i16', ' plb', ' ply',
    ' ldx #0', ' jmp BhInvalidateFind',
    'IvCodeEnd:', '.a16', '.i16',
]


class BorrowInvalidateContractError(ValueError):
    """Raised when the pinned original invalidation code has drifted."""


def transform(lines: Sequence[str], enabled: bool = True) -> list[str]:
    """Patch only the original scan entry and append the bank-local helper."""
    result = list(lines)
    if not enabled:
        return result
    normalized = [line.strip() for line in result]
    helper_labels = {
        'IvFind:', 'IvLoop:', 'IvFound:',
        'IvMiss:', 'IvFallback:',
        'IvCodeEnd:',
    }
    if any(line in helper_labels for line in normalized):
        raise BorrowInvalidateContractError('BORROW_INVALIDATE_ALREADY_INSTALLED')
    matches = [i for i in range(len(result) - len(ANCHOR) + 1)
               if normalized[i:i + len(ANCHOR)] == ANCHOR]
    for label in ('BhInvalidate:', 'BhInvalidateFind:', 'BhInvalidateFound:',
                  'BhInvalidateUnreferenced:', 'BhInvalidateOK:',
                  'BhInvalidateBad:'):
        if normalized.count(label) != 1:
            raise BorrowInvalidateContractError('BORROW_INVALIDATE_LABEL:' + label)
    if len(matches) != 1:
        raise BorrowInvalidateContractError('BORROW_INVALIDATE_PINNED_SOURCE')
    start = matches[0]
    dispatch = start + ANCHOR.index('ldx #0')
    result[dispatch] = ' jmp IvFind'
    return result + ROUTINE


