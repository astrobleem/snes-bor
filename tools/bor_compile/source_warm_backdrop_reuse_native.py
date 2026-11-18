"""Reuse a resident canonical backdrop pair by its map provenance.

This optional warm-planner extension keeps the old display's actor-cell bitmap.
An unmarked cell still contains its immutable backdrop, even if that backdrop's
original home was borrowed. Its current paired ID can therefore be shared by
the next map without a new restoration allocation or any PPU write.
"""
from __future__ import annotations

CURRENT_MASK = 0x7E7940
MASK_BYTES = 128
MASK_VALID = CURRENT_MASK + MASK_BYTES
COLD_INIT = 0x2E8800


def initialize(helper_text):
    anchor = 'ldx #0\nWarmMain_CopyCold:'
    if helper_text.count(anchor) != 1:
        raise ValueError('WARM_REUSE_INIT_SHAPE')
    return helper_text.replace(anchor, ' jsl $2E8800\n' + anchor)


def emit(yield_address):
    if not 0x2B8000 <= yield_address < 0x2C0000:
        raise ValueError('WARM_REUSE_YIELD_TARGET')
    # $70 is the byte offset of a map cell. Bit words hold 16 cells each.
    def bit_index():
        return ''' lda $70
 lsr a
 and #15
 asl a
 tax
 lda.l WarmReuse_Bits,x
 sta $78
 lda $70
 lsr a
 lsr a
 lsr a
 lsr a
 and #$FFFE
 tax
'''
    return '''.org $8800
WarmReuse_ColdInit:
.a16
.i16
 php
 rep #$30
 pha
 phx
 phy
 phd
 lda #$3400
 tcd
 ldx #0
 lda #0
WarmReuse_ClearCurrent:
 sta.l $7E7940,x
 inx
 inx
 cpx #128
 bcc WarmReuse_ClearCurrent
 ; Initial map provenance is not inferred from its tile IDs. Reuse becomes
 ; eligible only after this producer has committed a tagged pending map.
 lda #0
 sta.l $7E79C0
 pld
 ply
 plx
 pla
 plp
 rtl
WarmReuse_Find:
.a16
.i16
 lda.l $7E79C0
 cmp #1
 bne WarmReuse_Missing
 lda #0
 sta $70
WarmReuse_FindCell:
 ldx $70
 lda.l $E18000,x
 cmp $30
 bne WarmReuse_FindNext
''' + bit_index() + ''' lda.l $7E7940,x
 and $78
 bne WarmReuse_FindNext
 ldx $70
 lda.l $42C800,x
 cmp #768
 bcs WarmReuse_FindNext
 sta $2C
 asl a
 tax
 lda.l $42D000,x
 and #$3FFF
 beq WarmReuse_FindNext
 clc
 rts
WarmReuse_FindNext:
 lda $70
 clc
 adc #2
 sta $70
 cmp #2048
 bcs WarmReuse_Missing
 and #63
 bne WarmReuse_FindCell
''' + f' jsl ${yield_address:06X}\n' + ''' bra WarmReuse_FindCell
WarmReuse_Missing:
 sec
 rts
WarmReuse_BuildPending:
.a16
.i16
 lda #0
 sta.l $7E79C0
 ldx #0
WarmReuse_ClearPending:
 sta.l $7E7940,x
 inx
 inx
 cpx #128
 bcc WarmReuse_ClearPending
 lda #0
 sta $70
WarmReuse_PendingCell:
 ldx $70
 lda.l $42C000,x
 and #$8000
 beq WarmReuse_PendingNext
''' + bit_index() + ''' lda.l $7E7940,x
 ora $78
 sta.l $7E7940,x
WarmReuse_PendingNext:
 lda $70
 clc
 adc #2
 sta $70
 cmp #2048
 bcc WarmReuse_PendingCell
 rts
WarmReuse_Commit:
.a16
.i16
 php
 rep #$30
 pha
 lda #1
 sta.l $7E79C0
 pla
 plp
 rts
WarmReuse_Bits:
.word ''' + ','.join(str(1 << i) for i in range(16)) + '\n'


def integrate(renderer, yield_address):
    anchors = {
        ' jmp RpResolveRestore\nNbReroute:':
        ' jsr WarmReuse_Find\n bcs WarmReuse_NeedsRestore\n jmp NbReroute\n'
        'WarmReuse_NeedsRestore:\n.a16\n.i16\n jmp RpResolveRestore\nNbReroute:',
        ' bcc NbActorPlan\n lda #2\n sta.l $42D600':
        ' bcc NbActorPlan\n jsr WarmReuse_BuildPending\n lda #2\n sta.l $42D600',
        'NbMapsComplete:\n.a16\n.i16\n':
        'NbMapsComplete:\n.a16\n.i16\n jsr WarmReuse_Commit\n',
        '.org $A000\nNbBegin:': emit(yield_address) + '.org $A000\nNbBegin:',
    }
    for anchor, replacement in anchors.items():
        if renderer.count(anchor) != 1:
            raise ValueError('WARM_REUSE_RENDER_SHAPE:' + anchor.splitlines()[0])
        renderer = renderer.replace(anchor, replacement)
    return renderer
