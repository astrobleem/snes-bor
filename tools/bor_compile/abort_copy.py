"""Optional abort-time committed-to-pending map-copy overlay.

The transform replaces only the pinned NbAbort MVN setup and appends a helper
inside the statically reserved bank-$39 gap. It changes source-read/destination-
write interleaving and is intended only under a separately proven exclusive
abort owner; it makes no generic concurrency claim.
"""
from __future__ import annotations

from collections.abc import Sequence

CODE_START = 0x39AE40
CODE_LIMIT = 0x39B000
WORDS_PER_BLOCK = 32
WORD_COUNT = 1024

ANCHOR = [
    'NbAbort:', '.a16', '.i16', 'lda #0', 'sta.l $42D660', 'jsr BhRollback',
    'phb', 'lda #2047', 'ldx #51200', 'ldy #49152', 'mvn $42,$42', 'plb',
    'lda #0', 'sta.l $42D600', 'jmp OnlineReject', 'NbFree:', '.a16', '.i16',
]


class AbortCopyContractError(ValueError):
    """Raised when the pinned abort source has drifted or is duplicated."""


def _routine() -> list[str]:
    rows = [
        '.bank 57', '.org $AE40', 'CaCopy:', '.a16', '.i16',
        ' php', ' lda.l $42D600', ' bne CaPhaseCheck', ' jmp CaFallback',
        'CaPhaseCheck:', '.a16', '.i16', ' cmp #5', ' bcc CaFast',
        ' jmp CaFallback',
        'CaFast:', '.a16', '.i16',
        ' phb', ' pea $4242', ' plb', ' plb', ' cld', ' ldx #0',
        'CaLoop:', '.a16', '.i16',
    ]
    for index in range(WORDS_PER_BLOCK):
        source = f'${0xC800 + 2 * index:04X},x'
        destination = f'${0xC000 + 2 * index:04X},x'
        rows.extend((f' lda {source}', f' sta {destination}'))
    rows.extend((
        ' txa', ' clc', ' adc #64', ' tax', ' cpx #2048',
        ' bcs CaDone', ' jmp CaLoop',
        'CaDone:', '.a16', '.i16',
        ' ldx #53248', ' ldy #51200', ' plb', ' plp', ' lda #0',
        ' jmp CaContinue',
        'CaFallback:', '.a16', '.i16',
        ' plp', ' phb', ' lda #2047', ' jmp CaLegacyCopy',
        'CaCodeEnd:', '.a16', '.i16',
    ))
    return rows


ROUTINE = _routine()


def _size(line: str) -> int:
    line = line.strip()
    if not line or line.endswith(':') or line.startswith('.'):
        return 0
    if line in ('php', 'phb', 'plb', 'plp', 'cld', 'txa', 'tax', 'clc'):
        return 1
    if line == 'pea $4242':
        return 3
    if line == 'lda.l $42D600':
        return 4
    if line.startswith(('ldx #', 'ldy #', 'lda #', 'adc #', 'cmp #', 'cpx #')):
        return 3
    if line.startswith(('lda $', 'sta $')) and line.endswith(',x'):
        return 3
    if line.startswith(('bcs ', 'bcc ', 'beq ', 'bne ')):
        return 2
    if line.startswith('jmp '):
        return 3
    raise AbortCopyContractError('CA_UNKNOWN_INSTRUCTION:' + line)


def estimated_bytes(rows: Sequence[str] = ROUTINE) -> int:
    """Return helper size for the fixed 65816 instruction subset."""
    return sum(_size(line) for line in rows)


def transform(lines: Sequence[str], enabled: bool = True) -> list[str]:
    """Patch only the exact NbAbort copy prefix; disabled mode is identity."""
    result = list(lines)
    if not enabled:
        return result
    normalized = [line.strip() for line in result]
    if any(line.startswith('Ca') and line.endswith(':') for line in normalized):
        raise AbortCopyContractError('CA_ALREADY_INSTALLED')
    matches = [i for i in range(len(normalized) - len(ANCHOR) + 1)
               if normalized[i:i + len(ANCHOR)] == ANCHOR]
    if len(matches) != 1:
        raise AbortCopyContractError('CA_PINNED_SOURCE')
    for label in ('NbAbort:', 'NbFree:', 'CfFuse:', 'CfCodeEnd:'):
        if normalized.count(label) != 1:
            raise AbortCopyContractError('CA_LABEL:' + label)
    start = matches[0]
    prefix = start + ANCHOR.index('phb')
    result[prefix:prefix + 2] = [' jmp CaCopy', ' nop']
    legacy_index = start + ANCHOR.index('ldx #51200')
    result[legacy_index:legacy_index] = ['CaLegacyCopy:', '.a16', '.i16']
    sta_index = start + ANCHOR.index('sta.l $42D600') + 3
    result[sta_index:sta_index] = ['CaContinue:', '.a16', '.i16']
    result.extend(ROUTINE)
    if CODE_START + estimated_bytes() > CODE_LIMIT:
        raise AbortCopyContractError('CA_HELPER_TOO_LARGE')
    return result
