"""Optional fused committed-map copy and accepted REF rebuild overlay.

This prototype replaces only the four-byte PHB/LDA-count prefix at the pinned
NbMapsComplete anchor with JMP/NOP and appends a helper in $39:AB00..$39:B000.
The helper deliberately changes cross-resource write interleaving and therefore
depends on the fixture's exclusive publication owner; it makes no production
concurrency claim.
"""
from __future__ import annotations

from collections.abc import Sequence

import ref_rebuild as accepted


CODE_START = 0x39AB00
CODE_LIMIT = 0x39B000
REF_WORDS = 768
MAP_WORDS = 1024
WORDS_PER_BLOCK = 32

# Pin the original copy and both accepted rebuild loops through the original
# continuation. The two original loops and every original symbol remain in
# place; only PHB + LDA #2047 are replaced by a same-size JMP + NOP.
ANCHOR = [
    'NbMapsComplete:', '.a16', '.i16', 'phb', 'lda #2047',
    'ldx #49152', 'ldy #51200', 'mvn $42,$42', 'plb', 'jmp RfRebuild',
    'NbClearRefs:', '.a16', '.i16', 'lda.l $42D000,x', 'and #$8000',
    'sta.l $42D000,x', 'inx', 'inx', 'cpx #1536', 'bcc NbClearRefs',
    'ldy #0', 'NbPublishRefs:', '.a16', '.i16', 'tya', 'tax',
    'lda.l $42C000,x', 'asl a', 'tax', 'lda.l $42D000,x', 'inc a',
    'sta.l $42D000,x', 'iny', 'iny', 'cpy #2048', 'bcc NbPublishRefs',
    'RfContinue:', 'lda $10',
]


class CommitRebuildFuseContractError(ValueError):
    """Raised when the accepted source anchor has drifted or is duplicated."""


def _routine() -> list[str]:
    rows = [
        '.bank 57', '.org $AB00', 'CfFuse:', '.a16', '.i16',
        ' php', ' phb', ' pea $4242', ' plb', ' plb', ' cld', ' ldx #0',
        'CfClearLoop:', '.a16', '.i16',
    ]
    for index in range(WORDS_PER_BLOCK):
        operand = f'${0xD000 + 2 * index:04X},x'
        rows.extend((f' lda {operand}', ' and #$8000', f' sta {operand}'))
    rows.extend((
        ' txa', ' clc', ' adc #64', ' tax', ' cpx #1536',
        ' bcs CfClearDone', ' jmp CfClearLoop',
        'CfClearDone:', '.a16', '.i16', ' ldx #0',
        'CfCountLoop:', '.a16', '.i16',
    ))
    for index in range(WORDS_PER_BLOCK):
        source = f'${0xC000 + 2 * index:04X},x'
        destination = f'${0xC800 + 2 * index:04X},x'
        rows.extend((
            f' lda {source}', f' sta {destination}', ' asl a', ' tay',
            ' lda $D000,y', ' inc a', ' sta $D000,y',
        ))
    rows.extend((
        ' txa', ' clc', ' adc #64', ' tax', ' cpx #2048',
        ' bcs CfCountDone', ' jmp CfCountLoop',
        'CfCountDone:', '.a16', '.i16',
        ' lda $D000,y', ' tyx', ' ldy #2048', ' plb', ' plp',
        ' cpy #2048', ' jmp RfContinue',
        'CfCodeEnd:', '.a16', '.i16',
    ))
    return rows


ROUTINE = _routine()


def _size(line: str) -> int:
    line = line.strip()
    if not line or line.endswith(':') or line.startswith('.'):
        return 0
    if line in ('php', 'phb', 'plb', 'plp', 'cld', 'txa', 'tax', 'tyx',
                'tay', 'asl a', 'inc a', 'clc'):
        return 1
    if line == 'pea $4242':
        return 3
    if line.startswith(('ldx #', 'ldy #', 'lda #', 'adc #', 'and #', 'cpx #', 'cpy #')):
        return 3
    if line.startswith(('lda $', 'sta $')) and line.endswith((',x', ',y')):
        return 3
    if line.startswith(('bcs ', 'bcc ', 'beq ', 'bne ')):
        return 2
    if line.startswith('jmp '):
        return 3
    raise CommitRebuildFuseContractError('CF_UNKNOWN_INSTRUCTION:' + line)


def estimated_bytes(rows: Sequence[str] = ROUTINE) -> int:
    """Return literal helper size for the fixed 65816 instruction subset."""
    return sum(_size(line) for line in rows)


def transform(lines: Sequence[str], enabled: bool = True) -> list[str]:
    """Redirect only the accepted copy prefix; disabled mode is exact identity."""
    result = list(lines)
    if not enabled:
        return result
    normalized = [line.strip() for line in result]
    if any(line.startswith('Cf') and line.endswith(':') for line in normalized):
        raise CommitRebuildFuseContractError('CF_ALREADY_INSTALLED')
    matches = [i for i in range(len(result) - len(ANCHOR) + 1)
               if normalized[i:i + len(ANCHOR)] == ANCHOR]
    if len(matches) != 1:
        raise CommitRebuildFuseContractError('CF_PINNED_SOURCE')
    original_rebuild = [line.strip() for line in accepted.ROUTINE]
    rebuild_matches = [i for i in range(len(normalized) - len(original_rebuild) + 1)
                       if normalized[i:i + len(original_rebuild)] == original_rebuild]
    if len(rebuild_matches) != 1:
        raise CommitRebuildFuseContractError('CF_ORIGINAL_REBUILD')
    for label in ('NbMapsComplete:', 'NbClearRefs:', 'NbPublishRefs:', 'RfRebuild:', 'RfContinue:'):
        if normalized.count(label) != 1:
            raise CommitRebuildFuseContractError('CF_LABEL:' + label)
    start = matches[0]
    patch = start + ANCHOR.index('phb')
    result[patch:patch + 2] = [' jmp CfFuse', ' nop']
    result.extend(ROUTINE)
    if CODE_START + estimated_bytes() >= CODE_LIMIT:
        raise CommitRebuildFuseContractError('CF_HELPER_TOO_LARGE')
    return result
