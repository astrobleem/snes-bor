; Actual entity.tocost int32, independent of cached-model installation.
; Opt-in B609 reserves the last 512 bytes of the animation-cache arena.
; Active cache capacity is 7680 bytes; disabled retains the original 8192.
; Fresh and old-NONE births clear this field before publication. Model copies
; retain it. No per-frame cost response or guessed zero replaces this field.
SourceAttackCostState4086_Ready = $43BF70
SourceAttackCostState4086_End = $43BF72
SOURCE_ENTITY_ATTACK_COST = $43DE00
SOURCE_ENTITY_ATTACK_COST_STRIDE = 4
SOURCE_ENTITY_ATTACK_COST_END = $43E000
SOURCE_ATTACK_COST_ANIMATION_CAPACITY = 7680

; A is a computed animation-cache byte span. Preserve A and all caller state.
SourceAttackCostState4086_CheckCacheSpan:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceAttackCostState4086_Ready
 beq SourceAttackCostState4086_SpanGood
 cmp #$B609
 bne SourceAttackCostState4086_SpanBad
 lda 1,s
 cmp #SOURCE_ATTACK_COST_ANIMATION_CAPACITY+1
 bcs SourceAttackCostState4086_SpanBad
SourceAttackCostState4086_SpanGood:
.a16
.i16
 lda 1,s
 jsl SourceMovementState4086_CheckCacheSpan
 bcs SourceAttackCostState4086_SpanBad
 pla
 plp
 clc
 rtl
SourceAttackCostState4086_SpanBad:
.a16
.i16
 pla
 plp
 sec
 rtl

; A=actual pool slot. Disabled capability is a no-op with no row ownership.
SourceAttackCostState4086_PreflightBirth:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceAttackCostState4086_Ready
 beq SourceAttackCostState4086_BirthGood
 cmp #$B609
 bne SourceAttackCostState4086_BirthBad
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceAttackCostState4086_BirthBad
 lda.l VmSourceWorld_Count
 beq SourceAttackCostState4086_BirthBad
 cmp #129
 bcs SourceAttackCostState4086_BirthBad
 cmp 1,s
 bcc SourceAttackCostState4086_BirthBad
 beq SourceAttackCostState4086_BirthBad
 lda.l SourceModelAnimationCopy4086_Ready
 cmp #$B4E9
 bne SourceAttackCostState4086_BirthBad
 lda.l SourceModelAnimationCopy4086_Bytes
 beq SourceAttackCostState4086_BirthBad
 jsl SourceAttackCostState4086_CheckCacheSpan
 bcs SourceAttackCostState4086_BirthBad
SourceAttackCostState4086_BirthGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceAttackCostState4086_BirthBad:
.a16
.i16
 pla
 plp
 sec
 rtl

SourceAttackCostState4086_BirthClear:
.a16
.i16
 php
 rep #$38
 phx
 pha
 jsl SourceAttackCostState4086_PreflightBirth
 bcs SourceAttackCostState4086_ClearBad
 lda.l SourceAttackCostState4086_Ready
 beq SourceAttackCostState4086_ClearGood
 lda 1,s
 asl a
 asl a
 tax
 lda #0
 sta.l SOURCE_ENTITY_ATTACK_COST,x
 sta.l SOURCE_ENTITY_ATTACK_COST+2,x
SourceAttackCostState4086_ClearGood:
.a16
.i16
 pla
 plx
 plp
 clc
 rtl
SourceAttackCostState4086_ClearBad:
.a16
.i16
 pla
 plx
 plp
 sec
 rtl
