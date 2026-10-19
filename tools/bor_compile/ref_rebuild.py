"""Single-pass fixed overlay for the accepted reference-table rebuild."""
from __future__ import annotations

from collections.abc import Sequence


CODE_START = 0x39A900
CODE_LIMIT = 0x39B000

# Pin the completed map copy, both original loops, and the continuation. The
# overlay depends on the copy having populated bank $42 and keeps the old loop
# labels/bodies in place for symbol and guard stability.
ANCHOR = [
    'NbMapsComplete:', '.a16', '.i16', 'phb', 'lda #2047', 'ldx #49152',
    'ldy #51200', 'mvn $42,$42', 'plb', 'ldx #0',
    'NbClearRefs:', '.a16', '.i16', 'lda.l $42D000,x', 'and #$8000',
    'sta.l $42D000,x', 'inx', 'inx', 'cpx #1536', 'bcc NbClearRefs',
    'ldy #0', 'NbPublishRefs:', '.a16', '.i16', 'tya', 'tax',
    'lda.l $42C000,x', 'asl a', 'tax', 'lda.l $42D000,x', 'inc a',
    'sta.l $42D000,x', 'iny', 'iny', 'cpy #2048', 'bcc NbPublishRefs',
    'lda $10',
]


_CLEAR_WORD = [
    ' lda $D000,x', ' and #$8000', ' sta $D000,x', ' inx', ' inx',
]
_PUBLISH_WORD = [
    ' lda $C000,y', ' asl a', ' tax', ' lda $D000,x', ' inc a',
    ' sta $D000,x', ' iny', ' iny',
]

ROUTINE = [
    '.bank 57', '.org $A900', 'RfRebuild:', '.a16', '.i16',
    ' phb', ' pea $4242', ' plb', ' plb',
    ' ldx #0',
    'RfClearLoop:', '.a16', '.i16',
    *_CLEAR_WORD, *_CLEAR_WORD, *_CLEAR_WORD, *_CLEAR_WORD,
    *_CLEAR_WORD, *_CLEAR_WORD, *_CLEAR_WORD, *_CLEAR_WORD,
    *_CLEAR_WORD, *_CLEAR_WORD, *_CLEAR_WORD, *_CLEAR_WORD,
    *_CLEAR_WORD, *_CLEAR_WORD, *_CLEAR_WORD, *_CLEAR_WORD,
    ' cpx #1536', ' bcs RfClearDone', ' brl RfClearLoop',
    'RfClearDone:', '.a16', '.i16',
    ' ldy #0',
    'RfPublishLoop:', '.a16', '.i16',
    *_PUBLISH_WORD, *_PUBLISH_WORD, *_PUBLISH_WORD, *_PUBLISH_WORD,
    *_PUBLISH_WORD, *_PUBLISH_WORD, *_PUBLISH_WORD, *_PUBLISH_WORD,
    *_PUBLISH_WORD, *_PUBLISH_WORD, *_PUBLISH_WORD, *_PUBLISH_WORD,
    *_PUBLISH_WORD, *_PUBLISH_WORD, *_PUBLISH_WORD, *_PUBLISH_WORD,
    ' cpy #2048', ' bcs RfPublishDone', ' brl RfPublishLoop',
    'RfPublishDone:', '.a16', '.i16',
    ' plb', ' cpy #2048', ' jmp RfContinue',
    'RfCodeEnd:', '.a16', '.i16',
]


class RefRebuildContractError(ValueError):
    """Raised when the accepted reference-rebuild anchor has drifted."""


def transform(lines: Sequence[str], enabled: bool = True) -> list[str]:
    """Replace exactly the pinned entry instruction and append the overlay."""
    result = list(lines)
    if not enabled:
        return result
    normalized = [line.strip() for line in result]
    if any(line.startswith('Rf') and line.endswith(':') for line in normalized):
        raise RefRebuildContractError('REF_REBUILD_ALREADY_INSTALLED')
    matches = [i for i in range(len(result) - len(ANCHOR) + 1)
               if normalized[i:i + len(ANCHOR)] == ANCHOR]
    for label in ('NbMapsComplete:', 'NbClearRefs:', 'NbPublishRefs:'):
        if normalized.count(label) != 1:
            raise RefRebuildContractError('REF_REBUILD_LABEL:' + label)
    if len(matches) != 1:
        raise RefRebuildContractError('REF_REBUILD_PINNED_SOURCE')
    start = matches[0]
    dispatch = start + ANCHOR.index('ldx #0')
    result[dispatch] = ' jmp RfRebuild'
    continuation = start + ANCHOR.index('lda $10')
    result.insert(continuation, 'RfContinue:')
    return result + ROUTINE
