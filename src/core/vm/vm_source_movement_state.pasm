; Actual entity.destx/destz under ACCEPTED_COMPAT_Q16_16 coordinates.
; Opt-in B60B reserves 1024 bytes, 128 x two DWORDs, at $43DA00..$43DDFF.
; Requires B609 cost storage; combined animation cache capacity is 6656 bytes.
; Birth clears both destination fields; model copies retain them.
SourceMovementState4086_Ready = $43BF7A
SourceMovementState4086_End = $43BF7C
SOURCE_ENTITY_MOVEMENT_DEST = $43DA00
SOURCE_ENTITY_MOVEMENT_DEST_STRIDE = 8
SOURCE_ENTITY_MOVEMENT_DEST_END = $43DE00
SOURCE_MOVEMENT_ANIMATION_CAPACITY = 6656

; A is a computed animation-cache byte span. Preserve A and all caller state.
SourceMovementState4086_CheckCacheSpan:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceMovementState4086_Ready
 beq SourceMovementState4086_SpanGood
 cmp #$B60B
 bne SourceMovementState4086_SpanBad
 lda.l SourceAttackCostState4086_Ready
 cmp #$B609
 bne SourceMovementState4086_SpanBad
 lda 1,s
 cmp #SOURCE_MOVEMENT_ANIMATION_CAPACITY+1
 bcs SourceMovementState4086_SpanBad
SourceMovementState4086_SpanGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceMovementState4086_SpanBad:
.a16
.i16
 pla
 plp
 sec
 rtl

; A=actual pool slot. Disabled capability is a no-op with no row ownership.
SourceMovementState4086_PreflightBirth:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceMovementState4086_Ready
 beq SourceMovementState4086_BirthGood
 cmp #$B60B
 bne SourceMovementState4086_BirthBad
 lda.l SourceAttackCostState4086_Ready
 cmp #$B609
 bne SourceMovementState4086_BirthBad
 lda 1,s
 jsl SourceAttackCostState4086_PreflightBirth
 bcs SourceMovementState4086_BirthBad
SourceMovementState4086_BirthGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceMovementState4086_BirthBad:
.a16
.i16
 pla
 plp
 sec
 rtl

SourceMovementState4086_BirthClear:
.a16
.i16
 php
 rep #$38
 phx
 pha
 jsl SourceMovementState4086_PreflightBirth
 bcs SourceMovementState4086_ClearBad
 lda.l SourceMovementState4086_Ready
 beq SourceMovementState4086_ClearGood
 lda 1,s
 asl a
 asl a
 asl a
 tax
 lda #0
 sta.l SOURCE_ENTITY_MOVEMENT_DEST,x
 sta.l SOURCE_ENTITY_MOVEMENT_DEST+2,x
 sta.l SOURCE_ENTITY_MOVEMENT_DEST+4,x
 sta.l SOURCE_ENTITY_MOVEMENT_DEST+6,x
SourceMovementState4086_ClearGood:
.a16
.i16
 pla
 plx
 plp
 clc
 rtl
SourceMovementState4086_ClearBad:
.a16
.i16
 pla
 plx
 plp
 sec
 rtl
