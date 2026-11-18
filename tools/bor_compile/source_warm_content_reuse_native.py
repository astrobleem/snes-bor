"""Opt-in exact resident-pair sharing before warm allocation preflight.

The hash and bucket lists are hints only. Every hit compares all 64 HIGH and
16 LOW bytes in resident VRAM during a fresh blank. Referenced IDs cannot be
allocated by either NbFree or BhEligible. New hashes are written only for IDs
the existing producer owns; lookups ignore them until committed refs are >0.
"""
from __future__ import annotations

import struct

from source_warm_presentation_native import _relax

HASHES = 0x430000
HEADS = 0x430600
LINKS = 0x430800
LEASE_END = 0x430E00
ENTRY = 0x2E9000
SEED = 0x9E37


def fingerprint(pair):
    if len(pair) != 80:
        raise ValueError('WARM_CONTENT_PAIR_EXTENT')
    value = SEED
    for word in struct.unpack('<40H', pair):
        value = ((((value << 1) | (value >> 15)) & 0xFFFF) ^ word)
        value = (value + SEED) & 0xFFFF
    return value or 1


def backdrop_hashes(rom):
    # These are the exact immutable sources of WarmCopyBackdrop, not a new
    # picture or future-position table. The ROM writer still checks all bytes.
    if len(rom) <= 0x210000 + 596 * 16:
        raise ValueError('WARM_CONTENT_ROM_EXTENT')
    return [fingerprint(rom[0x200000 + i * 64:0x200000 + (i + 1) * 64]
                        + rom[0x210000 + i * 16:0x210000 + (i + 1) * 16])
            for i in range(596)]


def initialize(helper):
    anchor = 'ldx #0\nWarmMain_CopyCold:'
    if helper.count(anchor) != 1:
        raise ValueError('WARM_CONTENT_INIT_SHAPE')
    return helper.replace(anchor,
        ' jsl $2E9000\n bcs WarmMain_Fault\n' + anchor)


def emit(hashes, scan_yield):
    if len(hashes) != 596 or any(not 1 <= value <= 65535 for value in hashes):
        raise ValueError('WARM_CONTENT_HASH_TABLE')
    if not 0x2B8000 <= scan_yield < 0x2C0000:
        raise ValueError('WARM_CONTENT_YIELD_TARGET')
    text = '''.org $9000
WarmContent_Init:
.a16
.i16
 php
 rep #$38
 pha
 phx
 phd
 lda #$3400
 tcd
 lda.l $7FFB88
 cmp #$B6D0
 bne WarmContent_InitBad
 lda.l $7E7700
 cmp #$B6D0
 bne WarmContent_InitBad
 lda #0
 ldx #0
WarmContent_Clear:
 sta.l $430000,x
 inx
 inx
 cpx #3584
 bcc WarmContent_Clear
 ldx #0
WarmContent_InitHome:
 ; A cold actor may have overwritten an original home. Its invalid-home bit
 ; disqualifies the immutable hash; unknown cold actor content remains zero.
 lda.l $42D000,x
 and #$8000
 bne WarmContent_InitNext
 lda.l WarmContent_BackdropHashes,x
 sta.l $430000,x
WarmContent_InitNext:
 inx
 inx
 cpx #1192
 bcc WarmContent_InitHome
 pld
 plx
 pla
 plp
 clc
 rtl
WarmContent_InitBad:
 pld
 plx
 pla
 plp
 sec
 rtl
WarmContent_Hash:
.a16
.i16
 lda #$9E37
 ldx #0
WarmContent_HashWord:
 asl a
 bcc WarmContent_NoRotateCarry
 inc a
WarmContent_NoRotateCarry:
 eor.l $42D680,x
 clc
 adc #$9E37
 inx
 inx
 cpx #80
 bcc WarmContent_HashWord
 cmp #0
 bne WarmContent_HashDone
 inc a
WarmContent_HashDone:
 rts
WarmContent_Remember:
.a16
.i16
 jsr WarmContent_Hash
 pha
 lda $2C
 asl a
 tax
 pla
 sta.l $430000,x
 rts
WarmContent_Index:
.a16
.i16
 lda #$FFFF
 ldx #0
WarmContent_ClearHeads:
 sta.l $430600,x
 inx
 inx
 cpx #512
 bcc WarmContent_ClearHeads
 lda #0
 sta $70
WarmContent_IndexId:
 ldx $70
 lda.l $42D000,x
 and #$3FFF
 beq WarmContent_IndexNext
 lda.l $430000,x
 beq WarmContent_IndexNext
 and #255
 asl a
 tax
 lda.l $430600,x
 sta $72
 lda $70
 sta.l $430600,x
 tax
 lda $72
 sta.l $430800,x
WarmContent_IndexNext:
 lda $70
 clc
 adc #2
 sta $70
 cmp #1536
 bcc WarmContent_IndexId
 rts
WarmContent_Find:
.a16
.i16
 jsr WarmContent_Hash
 sta $7E
 and #255
 asl a
 tax
 lda.l $430600,x
 sta $70
WarmContent_Candidate:
 lda $70
 cmp #1536
 bcs WarmContent_Missing
 tax
 lda.l $430000,x
 cmp $7E
 bne WarmContent_NextCandidate
 ; The index contains only committed positive-ref IDs and is immutable until
 ; planning ends. Both allocators require refcount zero before any overwrite.
 lda $70
 lsr a
 sta $2C
 jsr NbFreshVblank
 sep #$20
.a8
 lda #$80
 sta.l $002115
 rep #$20
.a16
WarmContent_CompareBegin:
 jsr WarmCompare
WarmContent_CompareComplete:
 bcc WarmContent_Found
WarmContent_NextCandidate:
 ldx $70
 lda.l $430800,x
 sta $70
 jmp WarmContent_Candidate
WarmContent_Found:
 clc
 rts
WarmContent_Missing:
 sec
 rts
WarmContent_Plan:
.a16
.i16
 lda.l $42D674
 beq WarmContent_PlanDone
 jsr WarmContent_Index
 lda #0
 sta $18
WarmContent_PlanCell:
 lda $18
 asl a
 tax
 lda.l $42C000,x
 cmp #$FFFF
 bne WarmContent_PlanNext
 jsr OnlineColorPointers
 jsl AstraOpaqueTile
 jsr WarmContent_Find
 bcs WarmContent_PlanNext
 lda $18
 asl a
 tax
 lda $2C
 ora #$C000
 sta.l $42C000,x
WarmContent_PlanNext:
'''
    text += f' jsl ${scan_yield:06X}\n'
    text += ''' inc $18
 lda $18
 cmp #896
 bcc WarmContent_PlanCell
WarmContent_PlanDone:
 rts
WarmContent_BackdropHashes:
.word ''' + ','.join(str(value) for value in hashes) + '\n'
    return _relax(text, 'WarmContent')


def integrate(renderer, hashes, scan_yield):
    anchors = {
        'NbActorPlanStart:\n.a16\n.i16\n jsr BhPrepare\n bcc BhActorPlanAdmitted\n jmp NbAbort\nBhActorPlanAdmitted:':
        '''NbActorPlanStart:
.a16
.i16
 jsr BhPrepare
 bcc BhActorPlanAdmitted
 ; Ordinary admission performs no color scan or VRAM reads. Only a failed
 ; exact preflight pays for sharing; clear its provisional borrow list before
 ; replanning, without changing restores, refs, maps or the allocation cursor.
 jsr BhBegin
 jsr WarmContent_Plan
 jsr BhPrepare
 bcc BhActorPlanAdmitted
 jmp NbAbort
BhActorPlanAdmitted:''',
        ' lda $64\n sta $2C\n jsr NbPreloadPair':
        ' lda $64\n sta $2C\n jsr WarmContent_Remember\n jsr NbPreloadPair',
        'BhActorPairSafe:\n.a16\n.i16\n jsr NbPreloadPair':
        'BhActorPairSafe:\n.a16\n.i16\n jsr WarmContent_Remember\n jsr NbPreloadPair',
        'NbActorProduce:\n.a16\n.i16\n lda $18\n asl a\n tax\n lda.l $42C000,x\n and #$8000':
        '''NbActorProduce:
.a16
.i16
 lda $18
 asl a
 tax
 lda.l $42C000,x
 and #$C000
 cmp #$C000
 bne WarmContent_ProduceOrdinary
 ; Keep the actor tag through BuildPending, then skip the resident pair's
 ; upload and leave the existing bit14 route for ordinary RvValidate to strip.
 lda.l $42C000,x
 and #$7FFF
 sta.l $42C000,x
 jmp NbActorProduceNext
WarmContent_ProduceOrdinary:
.a16
.i16
 and #$8000''',
        '.org $A000\nNbBegin:': emit(hashes, scan_yield) + '.org $A000\nNbBegin:',
    }
    for anchor, replacement in anchors.items():
        if renderer.count(anchor) != 1:
            raise ValueError('WARM_CONTENT_RENDER_SHAPE:' + anchor.splitlines()[0])
        renderer = renderer.replace(anchor, replacement)
    return renderer
