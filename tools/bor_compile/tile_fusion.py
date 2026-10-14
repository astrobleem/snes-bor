"""Experimental ASTRA tile-scoped source-row fusion for the bounded MOTU opaque producer.

Targets generated 65816 assembly *after* occupancy/retention transforms. This
module has not been assembled or executed on Mesen. It combines already-proven
per-row mask and pixel formulas into a tile-level routine; do not remove the
scalar renderer or change bitmap/palette authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Sequence

# The existing independent row kernel lives at E000..E0AE (175 bytes). Its
# same operations are copied into the fused routine, which starts at E200.
START = '.org $E200'
END = '.org $F000'


def _blend_body() -> list[str]:
    lines: list[str] = [
        ' ldy #0',
        ' lda $32',
        ' bne AstraTileCheckOpaque',
        ' brl AstraTileCopyBack',
        'AstraTileCheckOpaque:', '.a16', '.i16',
        ' cmp #$FFFF',
        ' bne AstraTileMixed',
        ' brl AstraTileCopySource',
        'AstraTileMixed:', '.a16', '.i16',
    ]
    dests = [0x42D680,0x42D690,0x42D6A0,0x42D6B0,0x42D6C0]
    for kind in ('mixed','back','source'):
        if kind == 'back': lines += [' brl AstraTilePixelDone','AstraTileCopyBack:', '.a16', '.i16']
        elif kind == 'source': lines += [' brl AstraTilePixelDone','AstraTileCopySource:', '.a16', '.i16']
        for i,addr in enumerate(dests):
            if kind == 'mixed':
                lines += [' lda [$3C],y',' eor [$0C],y',' and $32',' eor [$0C],y']
            else:
                lines += [f' lda [${0x0C if kind=="back" else 0x3C:02X}],y']
            lines += [f' sta.l ${addr:06X},x']
            if i != 4: lines += [' iny',' iny']
    lines += ['AstraTilePixelDone:', '.a16', '.i16']
    return lines


def tile_routine() -> list[str]:
    """Fused mask+blend+row-step; reuse OnlineRowPointers once per tile.

    DP: $08..$0A source row record; $0C..$0E backdrop row; $46 source row count;
        $48 original source row stride; $54 foreground screen-row byte offset;
        $56 signed source-local Y. $1E counts output rows.
    Masks preserve SOURCE INDEX 0 transparency, including opaque RGB black.
    """
    lines = [START,
        'AstraOpaqueTile:', '.a16','.i16',
        ' php',' rep #$30',' phx',' phy',
        ' lda #0',' sta $1E',
        'AstraTileNextRow:', '.a16','.i16',
        ' lda #0',' sta $32',
        ' lda $56',' cmp $46',' bcs AstraTileNoSource',
        ' ldx $54',
        ' sep #$20','.a8',
        ' lda.l $F40000,x',
        ' rep #$20','.a16',
        ' and #255',' eor #255',' sta $32',' xba',' ora $32',
        ' ldy #0',' and [$08],y',' sta $32',
        'AstraTileNoSource:', '.a16','.i16',
        ' lda $08',' clc',' adc #2',' sta $3C',
        ' lda $0A',' adc #0',' sta $3E',
        ' lda $1E',' asl a',' tax',
        'AstraTileRow:', '.a16','.i16',
    ]
    lines += _blend_body()
    lines += [
        # Faithfully reproduce OnlineStepRow: for *negative* source y the
        # source pointer must remain clamped to row zero until y reaches zero.
        ' lda $56',' bmi AstraTileNegative',
        ' lda $08',' clc',' adc $48',' sta $08',
        ' lda $0A',' adc #0',' sta $0A',
        'AstraTileNegative:', '.a16','.i16',
        ' inc $56',' inc $54',
        ' lda $0C',' clc',' adc #10',' sta $0C',
        ' lda $0E',' adc #0',' sta $0E',
        ' inc $1E',' lda $1E',' cmp #8',' bcs AstraTileDone',
        ' jmp AstraTileNextRow',
        'AstraTileDone:', '.a16','.i16',
        ' ply',' plx',' plp',' rtl',
    ]
    return lines


class TransformError(ValueError): pass


def fuse(lines: Sequence[str]) -> list[str]:
    """Perform one fail-closed splice on GENERATED native assembler statements.

    Call this *after* m4_occupancy_publisher.apply. It assumes the emitted
    assembly matches 1fb3def's bounded source-row form. No source/ROM writes.
    """
    result = list(lines)
    marker = 'OnlineComposeTile:'
    after = 'OnlineTransfer:'
    if result.count(marker) != 1 or result.count(after) != 1 or result.count(END) != 1:
        raise TransformError('FUSED_TILE_ANCHOR_DRIFT')
    start=result.index(marker)
    stop=result.index(after,start)
    body=result[start:stop]
    mandatory=[' jsr OnlineRowPointers',' jsr OnlineRowMask',' jsl AstraOpaqueRow',' jsr OnlineStepRow','OnlineEncode:']
    for x in mandatory:
        if body.count(x)!=1:raise TransformError('FUSED_TILE_ORIGINAL_ROW_CONTRACT:'+x)
    # Keep previous tile slot selection untouched. Abort if new side effects
    # have been added to the old row region since the audited source version.
    expected_prefix=[
        'OnlineComposeTile:', '.a16','.i16',
        ' lda $18',' asl a',' tax',
        ' lda.l $42C000,x',' sta $2C',
        ' jsr OnlineRowPointers',
    ]
    if body[:len(expected_prefix)]!=expected_prefix:
        raise TransformError('FUSED_TILE_PREFIX_DRIFT')
    if 'AstraOpaqueTile:' in result:raise TransformError('FUSED_TILE_DUPLICATE')
    result[start:stop] = [*expected_prefix,' jsl AstraOpaqueTile','OnlineEncode:', '.a16','.i16']
    # Position E200 deliberately beyond the 175-byte intact row kernel at E000.
    # Keep original row kernel for independent scalar comparisons.
    result[result.index(END):result.index(END)] = tile_routine()
    return result


def row_reference(background:bytes, actor_rows:Sequence[tuple[int,bytes]],
                  foreground:bytes)->bytes:
    """Independent projected-tile reference, 8x5 pair words and source masks.

    actor_rows records must be in screen-row order, with mask duplicated to
    both component-plane bytes, as currently prepared by source phase atlas.
    Foreground contains 8 mask bytes (one per tile row).
    """
    if len(background)!=80 or len(actor_rows)!=8 or len(foreground)!=8:
        raise ValueError('TILE_ROW_REFERENCE_DOMAIN')
    out=bytearray(background)
    for row,(mask,pixels) in enumerate(actor_rows):
        if len(pixels)!=10 or mask<0 or mask>255:raise ValueError('ACTOR_ROW_DOMAIN')
        effective=mask & (~foreground[row]&255)
        expanded=effective*0x101
        for plane in range(5):
            pos=plane*16+row*2
            b=int.from_bytes(background[pos:pos+2],'little')
            a=int.from_bytes(pixels[plane*2:plane*2+2],'little')
            composed = b ^ ((b^a)&expanded)
            out[pos:pos+2]=composed.to_bytes(2,'little')
    return bytes(out)


def source_stream_reference(source_rows:Sequence[tuple[int,bytes]], stride:int,
                            sy0:int, foreground:bytes, background:bytes)->bytes:
    """Check pointer/clipping semantics of OnlineRowPointers/OnlineStepRow.

    This reference intentionally models negative-row pointer clamping and
    bottom clipping, independent of the emitted routine's instruction stream.
    """
    if stride<=0 or len(foreground)!=8:raise ValueError('SOURCE_STREAM_DOMAIN')
    zero=(0,bytes(10));rows=[];pointer=max(0,sy0)
    for i in range(8):
        sy=sy0+i
        rows.append(source_rows[pointer] if 0<=sy<len(source_rows) else zero)
        if sy>=0:pointer+=1
    return row_reference(background,rows,foreground)
