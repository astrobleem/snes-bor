"""Optional 32-word block-unroll for the accepted READY validator.

The original RvValidate code and symbols remain untouched. Only its pinned
six-byte dispatch slot is redirected; this offline prototype fits in the
reserved $39AB00..$39B000 bank-local gap. Native performance is unmeasured.
"""
from __future__ import annotations

from collections.abc import Sequence

import ready_validate as accepted


CODE_START = 0x39AB00
CODE_LIMIT = 0x39B000
WORDS_PER_BLOCK = 32
WORDS_TOTAL = 1024
DISPATCH = [
    'NbValidate:', '.a16', '.i16', 'jmp RvValidate', 'nop', 'nop', 'nop',
]


class ReadyUnrollContractError(ValueError):
    """Raised when the accepted validator or its dispatch has drifted."""


def _routine() -> list[str]:
    rows = [
        '.bank 57', '.org $AB00', 'RuValidate:', '.a16', '.i16',
        # Preserve entry status and DBR, select map bank $42, use binary math.
        ' php', ' phb', ' pea $4242', ' plb', ' plb', ' cld', ' ldx #0',
        'RuBlockLoop:', '.a16', '.i16',
    ]
    for index in range(WORDS_PER_BLOCK):
        operand = f'${0xC000 + 2 * index:04X},x'
        rows.extend((
            f' lda {operand}',
            ' and #$BFFF',
            ' cmp #768',
            f' bcc RuValid{index:02d}',
            f' jmp RuReject{index:02d}',
            f'RuValid{index:02d}:',
            f' sta {operand}',
        ))
    rows.extend((
        ' txa', ' clc', ' adc #64', ' tax', ' cpx #2048',
        ' bcs RuSuccess', ' jmp RuBlockLoop',
        'RuSuccess:',
        ' plb', ' plp', ' ldx #2046', ' lda #2048', ' sta $70',
        ' cmp #2048', ' jmp RvContinue',
    ))
    # The fast path sends either tagged words or untagged out-of-range values
    # here. Cold fixups reconstruct exact X and re-read the original word to
    # distinguish tag errors from slot errors without adding hot-path state.
    for index in range(WORDS_PER_BLOCK):
        offset = 2 * index
        rows.extend((
            f'RuReject{index:02d}:',
            ' txa', ' clc', f' adc #{offset}', ' tax', ' jmp RuReject',
        ))
    rows.extend((
        'RuReject:',
        ' lda $C000,x', ' bpl RuSlotReload', ' jmp RuTaggedBad',
        'RuSlotReload:',
        ' and #$3FFF', ' jmp RuSlotFail',
        'RuTaggedBad:',
        ' plb', ' plp', ' txa', ' beq RuTaggedCarry', ' clc',
        'RuTaggedCarry:',
        ' lda #$8000', ' stx $70', ' jmp NbAbort',
        'RuSlotFail:',
        ' plb', ' plp', ' cmp #768', ' stx $70', ' jmp NbAbort',
        'RuCodeEnd:', '.a16', '.i16',
    ))
    return rows


ROUTINE = _routine()


def _size(line: str) -> int:
    line = line.strip()
    if not line or line.endswith(':') or line.startswith('.'):
        return 0
    if line in ('phb', 'plb', 'php', 'plp', 'cld', 'txa', 'tax', 'clc'):
        return 1
    if line == 'pea $4242':
        return 3
    if line.startswith(('lda #', 'adc #', 'and #', 'cmp #', 'cpx #', 'ldx #')):
        return 3
    if line.startswith(('lda $', 'sta $')) and line.endswith(',x'):
        return 3
    if line in ('sta $70', 'stx $70'):
        return 2
    if line.startswith(('bcc ', 'bcs ', 'bpl ', 'beq ')):
        return 2
    if line.startswith('jmp '):
        return 3
    raise ReadyUnrollContractError('RU_UNKNOWN_INSTRUCTION:' + line)


def estimated_bytes(rows: Sequence[str] = ROUTINE) -> int:
    """Return the literal size of the fixed helper's 65816 instruction set."""
    return sum(_size(line) for line in rows)


def transform(lines: Sequence[str], enabled: bool = True) -> list[str]:
    """Redirect the pinned dispatch; disabled mode is an exact identity."""
    result = list(lines)
    if not enabled:
        return result
    normalized = [line.strip() for line in result]
    if any(line.startswith('Ru') and line.endswith(':') for line in normalized):
        raise ReadyUnrollContractError('RU_ALREADY_INSTALLED')
    dispatches = [i for i in range(len(result) - len(DISPATCH) + 1)
                  if normalized[i:i + len(DISPATCH)] == DISPATCH]
    if len(dispatches) != 1 or normalized.count('RvValidate:') != 1:
        raise ReadyUnrollContractError('RU_PINNED_DISPATCH')
    original = [line.strip() for line in accepted.ROUTINE]
    starts = [i for i in range(len(normalized) - len(original) + 1)
              if normalized[i:i + len(original)] == original]
    if len(starts) != 1:
        raise ReadyUnrollContractError('RU_ORIGINAL_ROUTINE')
    if normalized.count('RvContinue:') != 1 or normalized.count('NbAbort:') != 1:
        raise ReadyUnrollContractError('RU_CONTINUATIONS')
    start = dispatches[0]
    result[start + 3:start + 7] = ['jmp RuValidate', ' nop', ' nop', ' nop']
    result.extend(ROUTINE)
    if CODE_START + estimated_bytes() >= CODE_LIMIT:
        raise ReadyUnrollContractError('RU_HELPER_TOO_LARGE')
    return result
