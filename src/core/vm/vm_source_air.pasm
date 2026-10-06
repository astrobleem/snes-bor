; Pinned inair uses diff(binary32 y, binary32 base) >= double literal 0.1.
; Explicit ACCEPTED_COMPAT_Q16_16 predicate over native coordinates:
; unsigned absolute difference >=6554, including signed subtraction overflow.
; This does not claim exact predicates for arbitrary source binary32 near 0.1.
; Synchronous inputs: model-copy Lo/Hi = y; default-player InvLo/Hi = base.
; No allocation, entity writes, lease changes or pending continuation state.
SourceInAir4086_Q16Compatibility:
.a16
.i16
 php
 rep #$38
 lda.l SourceModelEntityCopy4086_Hi
 eor #$8000
 pha
 lda.l SourceDefaultPlayer4086_InvHi
 eor #$8000
 cmp $01,s
 bcc SourceInAir4086_YHigher
 bne SourceInAir4086_BaseHigher
 pla
 lda.l SourceModelEntityCopy4086_Lo
 cmp.l SourceDefaultPlayer4086_InvLo
 bcs SourceInAir4086_YMinusBase
 bra SourceInAir4086_BaseMinusY
SourceInAir4086_YHigher:
.a16
.i16
 pla
 bra SourceInAir4086_YMinusBase
SourceInAir4086_BaseHigher:
.a16
.i16
 pla
SourceInAir4086_BaseMinusY:
.a16
.i16
 lda.l SourceDefaultPlayer4086_InvLo
 sec
 sbc.l SourceModelEntityCopy4086_Lo
 pha
 lda.l SourceDefaultPlayer4086_InvHi
 sbc.l SourceModelEntityCopy4086_Hi
 bra SourceInAir4086_Compare
SourceInAir4086_YMinusBase:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Lo
 sec
 sbc.l SourceDefaultPlayer4086_InvLo
 pha
 lda.l SourceModelEntityCopy4086_Hi
 sbc.l SourceDefaultPlayer4086_InvHi
SourceInAir4086_Compare:
.a16
.i16
 bne SourceInAir4086_HighDifference
 pla
 cmp #6554
 bcs SourceInAir4086_True
 lda #0
 bra SourceInAir4086_Done
SourceInAir4086_HighDifference:
.a16
.i16
 pla
SourceInAir4086_True:
.a16
.i16
 lda #1
SourceInAir4086_Done:
.a16
.i16
 plp
 clc
 rtl
