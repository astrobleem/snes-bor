; Actual entity.autokill signed int32. Fresh ordinary births are calloc zero.
; Projectile/dust assignments require their actual constructor services.
; Opt-in B60E owns 128 DWORDs at 43D800..43D9FF; cache capacity becomes 6144.
; Requires cost+movement leases; model installation preserves actor autokill.
; Ready control at 40BF2C is outside the actor-body high rows ending 40BF2B.
SourceAutokillState4086_Ready = $40BF2C
SourceAutokillState4086_End = $40BF2E
SOURCE_ENTITY_AUTOKILL = $43D800
SOURCE_ENTITY_AUTOKILL_STRIDE = 4
SOURCE_ENTITY_AUTOKILL_END = $43DA00
SOURCE_AUTOKILL_ANIMATION_CAPACITY = 6144

; A is a computed animation-cache byte span. Preserve A and all caller state.
SourceAutokillState4086_CheckCacheSpan:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceAutokillState4086_Ready
 beq SourceAutokillState4086_SpanGood
 cmp #$B60E
 bne SourceAutokillState4086_SpanBad
 lda.l SourceAttackCostState4086_Ready
 cmp #$B609
 bne SourceAutokillState4086_SpanBad
 lda.l SourceMovementState4086_Ready
 cmp #$B60B
 bne SourceAutokillState4086_SpanBad
 lda 1,s
 cmp #SOURCE_AUTOKILL_ANIMATION_CAPACITY+1
 bcs SourceAutokillState4086_SpanBad
SourceAutokillState4086_SpanGood:
.a16
.i16
 pla
 plp
 jsl SourceOffscreenState4086_CheckCacheSpan
 rtl
SourceAutokillState4086_SpanBad:
.a16
.i16
 pla
 plp
 sec
 rtl

; A=actual pool slot. Disabled capability is a no-op with no row ownership.
SourceAutokillState4086_PreflightBirth:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceAutokillState4086_Ready
 beq SourceAutokillState4086_BirthGood
 cmp #$B60E
 bne SourceAutokillState4086_BirthBad
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceAutokillState4086_BirthBad
 lda.l VmSourceWorld_Count
 beq SourceAutokillState4086_BirthBad
 cmp #129
 bcs SourceAutokillState4086_BirthBad
 cmp 1,s
 bcc SourceAutokillState4086_BirthBad
 beq SourceAutokillState4086_BirthBad
 lda.l SourceModelAnimationCopy4086_Ready
 cmp #$B4E9
 bne SourceAutokillState4086_BirthBad
 lda.l SourceModelAnimationCopy4086_Bytes
 beq SourceAutokillState4086_BirthBad
 jsl SourceAttackCostState4086_CheckCacheSpan
 bcs SourceAutokillState4086_BirthBad
SourceAutokillState4086_BirthGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceAutokillState4086_BirthBad:
.a16
.i16
 pla
 plp
 sec
 rtl

SourceAutokillState4086_BirthClear:
.a16
.i16
 php
 rep #$38
 phx
 pha
 jsl SourceAutokillState4086_PreflightBirth
 bcs SourceAutokillState4086_ClearBad
 lda.l SourceAutokillState4086_Ready
 beq SourceAutokillState4086_ClearGood
 lda 1,s
 asl a
 asl a
 tax
 lda #0
 sta.l SOURCE_ENTITY_AUTOKILL,x
 sta.l SOURCE_ENTITY_AUTOKILL+2,x
SourceAutokillState4086_ClearGood:
.a16
.i16
 pla
 plx
 plp
 clc
 rtl
SourceAutokillState4086_ClearBad:
.a16
.i16
 pla
 plx
 plp
 sec
 rtl
