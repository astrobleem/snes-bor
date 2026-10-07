; common_try_block(NULL): source nopassiveblock32, full32 rand32 mask,
; and current ANI_BLOCK presence. Target/range/block mutation body is unbound.
; Preserve typed VM return scratch while consuming the real engine RNG stream.
SourceTryBlock4086_Ready = $43BDA6
SourceTryBlock4086_Status = $43BDA8
SourceTryBlock4086_Entity = $43BDAA
SourceTryBlock4086_Mask = $43BDAC
SourceTryBlock4086_End = $43BDB0
SourceTryBlock4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceTryBlock4086_Ready
 cmp #$B5F1
 beq SourceTryBlock4086_Guard0
 jmp SourceTryBlock4086_Bad
SourceTryBlock4086_Guard0:
.a16
.i16
 lda.l SourceTryBlock4086_Status
 beq SourceTryBlock4086_Guard1
 jmp SourceTryBlock4086_Bad
SourceTryBlock4086_Guard1:
.a16
.i16
 jsl SourceNormalAttack4086_CheckOwner
 bcc SourceTryBlock4086_Guard2
 jmp SourceTryBlock4086_Bad
SourceTryBlock4086_Guard2:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 cmp #3
 beq SourceTryBlock4086_Guard3
 jmp SourceTryBlock4086_Bad
SourceTryBlock4086_Guard3:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceModelAttackPolicy4086_Slot
 lda.l SourceAI4086_Model
 sta.l SourceModelAttackPolicy4086_Model
 jsl SourceModelAttackPolicy4086_Check
 bcc SourceTryBlock4086_Policy
 jmp SourceTryBlock4086_Bad
SourceTryBlock4086_Policy:
.a16
.i16
 lda.l SourceModelAttackPolicy4086_Entity
 sec
 sbc #8
 sta.l SourceTryBlock4086_Entity
 tax
 lda.l SOURCE_ENTITY_AI_STATE+8,x
 ora.l SOURCE_ENTITY_AI_STATE+10,x
 bne SourceTryBlock4086_Random
 jmp SourceTryBlock4086_False
SourceTryBlock4086_Random:
.a16
.i16
 lda.l VmNativeVariant_Result
 pha
 lda.l VmNativeVariant_Result+2
 pha
 lda.l VmNativeVariant_Result+4
 pha
 lda.l VmNativeVariant_Result+6
 pha
 jsl SourceRandom4086_Next
 bcc SourceTryBlock4086_Masked
 jmp SourceTryBlock4086_RandomBad
SourceTryBlock4086_Masked:
.a16
.i16
 lda.l VmNativeVariant_Result+4
 and.l SOURCE_ENTITY_AI_STATE+12,x
 sta.l SourceTryBlock4086_Mask
 lda.l VmNativeVariant_Result+6
 and.l SOURCE_ENTITY_AI_STATE+14,x
 sta.l SourceTryBlock4086_Mask+2
 pla
 sta.l VmNativeVariant_Result+6
 pla
 sta.l VmNativeVariant_Result+4
 pla
 sta.l VmNativeVariant_Result+2
 pla
 sta.l VmNativeVariant_Result
 lda.l SourceTryBlock4086_Mask
 cmp #1
 beq SourceTryBlock4086_LowOne
 jmp SourceTryBlock4086_False
SourceTryBlock4086_LowOne:
.a16
.i16
 lda.l SourceTryBlock4086_Mask+2
 beq SourceTryBlock4086_HighZero
 jmp SourceTryBlock4086_False
SourceTryBlock4086_HighZero:
.a16
.i16
 lda.l SourceModelAnimationCopy4086_Maximum
 cmp #14
 bcs SourceTryBlock4086_AnimationBound
 jmp SourceTryBlock4086_Bad
SourceTryBlock4086_AnimationBound:
.a16
.i16
 lda.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE+26,x ; ANI_BLOCK=13
 beq SourceTryBlock4086_False
 jmp SourceTryBlock4086_Bad
SourceTryBlock4086_RandomBad:
.a16
.i16
 pla
 sta.l VmNativeVariant_Result+6
 pla
 sta.l VmNativeVariant_Result+4
 pla
 sta.l VmNativeVariant_Result+2
 pla
 sta.l VmNativeVariant_Result
 jmp SourceTryBlock4086_Bad
SourceTryBlock4086_False:
.a16
.i16
 lda #0
 sta.l SourceNormalAttack4086_Response
 sta.l SourceNormalAttack4086_Response+2
 lda #2
 sta.l SourceTryBlock4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceTryBlock4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceTryBlock4086_Status
 ply
 plx
 plp
 sec
 rtl
