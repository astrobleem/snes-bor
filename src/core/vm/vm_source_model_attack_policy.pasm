; Modeldata subset: nopassiveblock32, blockodds32, stealth.detect32/hide32.
; No set_model_ex fallback applies: copy all four values, including negatives.
; B5F0 leases sixteen mutable 16-byte cache rows at $40BC00..$40BCFF.
; Entity destination is AI-state +8..+23; noaicontrol/running stay independent.
SourceModelAttackPolicy4086_Ready = $43BD98
SourceModelAttackPolicy4086_Models = $43BD9A
SourceModelAttackPolicy4086_Slot = $43BD9C
SourceModelAttackPolicy4086_Model = $43BD9E
SourceModelAttackPolicy4086_Status = $43BDA0
SourceModelAttackPolicy4086_Cache = $43BDA2
SourceModelAttackPolicy4086_Entity = $43BDA4
SourceModelAttackPolicy4086_End = $43BDA6
SOURCE_MODEL_ATTACK_POLICY_CACHE = $40BC00
SourceModelAttackPolicy4086_Check:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceModelAttackPolicy4086_Ready
 cmp #$B5F0
 beq SourceModelAttackPolicy4086_Guard0
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard0:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceModelAttackPolicy4086_Guard1
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard1:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceModelAttackPolicy4086_Guard2
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard2:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceModelAttackPolicy4086_Guard3
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard3:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceModelAttackPolicy4086_Guard4
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard4:
.a16
.i16
 lda.l VmSourceWorld_Count
 cmp #129
 bcc SourceModelAttackPolicy4086_Guard5
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard5:
.a16
.i16
 cmp.l SourceModelEntityCopy4086_Entities
 beq SourceModelAttackPolicy4086_Guard6
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard6:
.a16
.i16
 cmp.l SourceModelAttackPolicy4086_Slot
 bne SourceModelAttackPolicy4086_Guard7
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard7:
.a16
.i16
 cmp.l SourceModelAttackPolicy4086_Slot
 bcs SourceModelAttackPolicy4086_Guard8
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard8:
.a16
.i16
 lda.l SourceModelAttackPolicy4086_Models
 bne SourceModelAttackPolicy4086_Guard9
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard9:
.a16
.i16
 cmp #17
 bcc SourceModelAttackPolicy4086_Guard10
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard10:
.a16
.i16
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceModelAttackPolicy4086_Guard11
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard11:
.a16
.i16
 cmp.l SourceModelAttackPolicy4086_Model
 bne SourceModelAttackPolicy4086_Guard12
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard12:
.a16
.i16
 cmp.l SourceModelAttackPolicy4086_Model
 bcs SourceModelAttackPolicy4086_Guard13
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Guard13:
.a16
.i16
 lda.l SourceModelAttackPolicy4086_Model
 asl a
 asl a
 asl a
 asl a
 sta.l SourceModelAttackPolicy4086_Cache
 lda.l SourceModelAttackPolicy4086_Slot
 asl a
 asl a
 asl a
 sta.l SourceModelAttackPolicy4086_Entity
 asl a
 clc
 adc.l SourceModelAttackPolicy4086_Entity
 clc
 adc #8
 sta.l SourceModelAttackPolicy4086_Entity
 lda #1
 sta.l SourceModelAttackPolicy4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceModelAttackPolicy4086_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceModelAttackPolicy4086_Check
 bcc SourceModelAttackPolicy4086_Copy
 jmp SourceModelAttackPolicy4086_Bad
SourceModelAttackPolicy4086_Copy:
.a16
.i16
 ldy #0
SourceModelAttackPolicy4086_Loop:
.a16
.i16
 tya
 clc
 adc.l SourceModelAttackPolicy4086_Cache
 tax
 lda.l SOURCE_MODEL_ATTACK_POLICY_CACHE,x
 pha
 tya
 clc
 adc.l SourceModelAttackPolicy4086_Entity
 tax
 pla
 sta.l SOURCE_ENTITY_AI_STATE,x
 iny
 iny
 cpy #16
 bcc SourceModelAttackPolicy4086_Loop
 lda #2
 sta.l SourceModelAttackPolicy4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceModelAttackPolicy4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceModelAttackPolicy4086_Status
 ply
 plx
 plp
 sec
 rtl
