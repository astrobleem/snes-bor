; Actual common_think check_energy(Which,Role), over the current model cache.
; MP is dynamic entity MP (+76), health is actual typed view health, seal is
; the separately initialized combat scalar, NOT the sealtime timer.
SourceEntityEnergy4086_Ready = $43BE9E
SourceEntityEnergy4086_Status = $43BEA0
SourceEntityEnergy4086_Role = $43BEA2
SourceEntityEnergy4086_Which = $43BEA4
SourceEntityEnergy4086_Result = $43BEA8
SourceEntityEnergy4086_Combat = $43BEAC
SourceEntityEnergy4086_Core = $43BEAE
SourceEntityEnergy4086_Handle = $43BEB0
SourceEntityEnergy4086_End = $43BEB2
SourceEntityEnergy4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceEntityEnergy4086_Ready
 cmp #$B5FD
 beq SourceEntityEnergy4086_Guard1
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard1:
.a16
.i16
 lda.l SourceEntityEnergy4086_Status
 beq SourceEntityEnergy4086_Start
 cmp #2
 beq SourceEntityEnergy4086_Guard2
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard2:
.a16
.i16
SourceEntityEnergy4086_Start:
.a16
.i16
 lda #1
 sta.l SourceEntityEnergy4086_Status
 jsl SourceCommonThink4086_CheckOwner
 bcc SourceEntityEnergy4086_Guard3
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard3:
.a16
.i16
 lda.l SourceEntityEnergy4086_Role
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcc SourceEntityEnergy4086_Guard4
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard4:
.a16
.i16
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 sta.l SourceEntityEnergy4086_Handle
 bne SourceEntityEnergy4086_Present
 jmp SourceEntityEnergy4086_False
SourceEntityEnergy4086_Present:
.a16
.i16
 lda.l SourceCheckEnergy4086_Ready
 cmp #$B5FA
 beq SourceEntityEnergy4086_Guard5
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard5:
.a16
.i16
 lda.l SourceCheckEnergy4086_Status
 beq SourceEntityEnergy4086_NumericIdle
 cmp #2
 beq SourceEntityEnergy4086_Guard6
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard6:
.a16
.i16
SourceEntityEnergy4086_NumericIdle:
.a16
.i16
 lda.l VmSourceEntity_Ready
 cmp #$B5EF
 beq SourceEntityEnergy4086_Guard7
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard7:
.a16
.i16
 lda.l VmSourceEntity_Base
 cmp #$4000
 beq SourceEntityEnergy4086_Guard8
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard8:
.a16
.i16
 lda.l VmSourceEntity_Bank
 cmp #$41
 beq SourceEntityEnergy4086_Guard9
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard9:
.a16
.i16
 lda.l VmSourceEntity_Count
 cmp.l VmSourceWorld_Count
 beq SourceEntityEnergy4086_Guard10
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard10:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceEntityEnergy4086_Guard11
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard11:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceEntityEnergy4086_Guard12
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard12:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410020,x
 cmp #BOR_VT_INTEGER
 beq SourceEntityEnergy4086_Guard13
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard13:
.a16
.i16
 lda.l $410022,x
 beq SourceEntityEnergy4086_Guard14
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard14:
.a16
.i16
 lda.l $410024,x
 sta.l SourceCheckEnergy4086_Health
 lda.l $410026,x
 sta.l SourceCheckEnergy4086_Health+2
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 sta.l SourceEntityEnergy4086_Core
 pla
 lda.l SourceAI4086_Slot
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 sta.l SourceEntityEnergy4086_Combat
 tax
 pla
 lda.l SOURCE_ENTITY_COMBAT+16,x
 cmp #$B5FB
 beq SourceEntityEnergy4086_Guard15
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard15:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT+18,x
 beq SourceEntityEnergy4086_Guard16
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard16:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT+4,x
 sta.l SourceCheckEnergy4086_Seal
 lda.l SOURCE_ENTITY_COMBAT+4+2,x
 sta.l SourceCheckEnergy4086_Seal+2
 lda.l SourceEntityEnergy4086_Core
 tax
 lda.l $40C048,x
 sta.l SourceCheckEnergy4086_Type
 lda.l $40C04A,x
 sta.l SourceCheckEnergy4086_Type+2
 lda.l $40C04C,x
 sta.l SourceCheckEnergy4086_MP
 lda.l $40C04E,x
 sta.l SourceCheckEnergy4086_MP+2
 lda.l SourceEntityEnergy4086_Handle
 jsl SourceAnimationEnergy4086_Query
 bcc SourceEntityEnergy4086_Guard17
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard17:
.a16
.i16
 lda.l SourceEntityEnergy4086_Which
 sta.l SourceCheckEnergy4086_Which
 lda.l SourceEntityEnergy4086_Which+2
 sta.l SourceCheckEnergy4086_Which+2
 lda #1
 sta.l SourceCheckEnergy4086_Present
 jsl SourceCheckEnergy4086_Execute
 bcc SourceEntityEnergy4086_Guard18
 jmp SourceEntityEnergy4086_Bad
SourceEntityEnergy4086_Guard18:
.a16
.i16
 lda.l SourceCheckEnergy4086_Result
 sta.l SourceEntityEnergy4086_Result
 lda.l SourceCheckEnergy4086_Result+2
 sta.l SourceEntityEnergy4086_Result+2
 bra SourceEntityEnergy4086_Done
SourceEntityEnergy4086_False:
.a16
.i16
 lda #0
 sta.l SourceEntityEnergy4086_Result
 sta.l SourceEntityEnergy4086_Result+2
SourceEntityEnergy4086_Done:
.a16
.i16
 lda #2
 sta.l SourceEntityEnergy4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceEntityEnergy4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceEntityEnergy4086_Status
 ply
 plx
 plp
 sec
 rtl
