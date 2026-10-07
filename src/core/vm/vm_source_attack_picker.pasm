; Literal pick_random_attack over actual current cache/entities/energy/ranges.
; Store compact (role,weight) pairs rather than expanding repeated choices.
; SOURCE_ATTACK_CHOICES owns $435800..$4358FF (64 x 4 bytes).
SourceAttackPicker4086_Ready = $43BEC6
SourceAttackPicker4086_Status = $43BEC8
SourceAttackPicker4086_Target = $43BECA
SourceAttackPicker4086_TestOnly = $43BECC
SourceAttackPicker4086_Result = $43BED0
SourceAttackPicker4086_Index = $43BED4
SourceAttackPicker4086_Role = $43BED6
SourceAttackPicker4086_Weight = $43BED8
SourceAttackPicker4086_Options = $43BEDA
SourceAttackPicker4086_Total = $43BEDC
SourceAttackPicker4086_Boundary = $43BEDE
SourceAttackPicker4086_WeaponOffset = $43BEE0
SourceAttackPicker4086_WeaponSlot = $43BEE2
SourceAttackPicker4086_Random = $43BEE4
SourceAttackPicker4086_Dividend = $43BEE6
SourceAttackPicker4086_Remainder = $43BEE8
SourceAttackPicker4086_Count = $43BEEA
SourceAttackPicker4086_End = $43BEEC
SOURCE_ATTACK_CHOICES = $435800
SourceAttackPicker4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAttackPicker4086_Ready
 cmp #$B5FF
 beq SourceAttackPicker4086_Guard1
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard1:
.a16
.i16
 lda.l SourceAttackPicker4086_Status
 beq SourceAttackPicker4086_Start
 cmp #2
 beq SourceAttackPicker4086_Guard2
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard2:
.a16
.i16
SourceAttackPicker4086_Start:
.a16
.i16
 lda #1
 sta.l SourceAttackPicker4086_Status
 jsl SourceCommonThink4086_CheckOwner
 bcc SourceAttackPicker4086_Guard3
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard3:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Ready
 cmp #$B5FE
 beq SourceAttackPicker4086_Guard4
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard4:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Status
 cmp #2
 beq SourceAttackPicker4086_Guard5
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard5:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Maximum
 cmp.l SourceModelAnimationCopy4086_Maximum
 beq SourceAttackPicker4086_Guard6
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard6:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Normals
 clc
 adc.l SourceAttackChoiceProfile4086_Specials
 sta.l SourceAttackPicker4086_Boundary
 lda #0
 sta.l SourceAttackPicker4086_Index
 sta.l SourceAttackPicker4086_Options
 sta.l SourceAttackPicker4086_Total
SourceAttackPicker4086_Loop:
.a16
.i16
 lda.l SourceAttackPicker4086_Index
 cmp.l SourceAttackChoiceProfile4086_Total
 bcc SourceAttackPicker4086_Entry
 jmp SourceAttackPicker4086_Select
SourceAttackPicker4086_Entry:
.a16
.i16
 cmp.l SourceAttackPicker4086_Boundary
 bcc SourceAttackPicker4086_ReadRole
 beq SourceAttackPicker4086_ReadRole
 lda.l SourceAttackPicker4086_TestOnly
 ora.l SourceAttackPicker4086_TestOnly+2
 beq SourceAttackPicker4086_ReadRole
 jmp SourceAttackPicker4086_Select
SourceAttackPicker4086_ReadRole:
.a16
.i16
 lda.l SourceAttackPicker4086_Index
 asl a
 tax
 lda.l SOURCE_ATTACK_CHOICE_ROLES,x
 sta.l SourceAttackPicker4086_Role
 jsr SourceAttackPicker4086_Valid
 bcc SourceAttackPicker4086_Guard7
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard7:
.a16
.i16
 ora #0
 bne SourceAttackPicker4086_Present
 jmp SourceAttackPicker4086_Next
SourceAttackPicker4086_Present:
.a16
.i16
 lda #1
 sta.l SourceAttackPicker4086_Weight
 lda.l SourceAttackPicker4086_Index
 cmp.l SourceAttackChoiceProfile4086_Normals
 bcs SourceAttackPicker4086_NotNormal
 cmp #5
 bcc SourceAttackPicker4086_RangeJump1
 jmp SourceAttackPicker4086_Range
SourceAttackPicker4086_RangeJump1:
.a16
.i16
 asl a
 tax
 lda.l SourceAttackPicker4086_Weights,x
 sta.l SourceAttackPicker4086_Weight
 jmp SourceAttackPicker4086_Range
SourceAttackPicker4086_NotNormal:
.a16
.i16
 cmp.l SourceAttackPicker4086_Boundary
 bcs SourceAttackPicker4086_NotSpecial
 lda.l SourceAttackPicker4086_Role
 sta.l SourceEntityEnergy4086_Role
 lda #1
 sta.l SourceEntityEnergy4086_Which
 lda #0
 sta.l SourceEntityEnergy4086_Which+2
 jsl SourceEntityEnergy4086_Execute
 bcc SourceAttackPicker4086_Guard8
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard8:
.a16
.i16
 lda.l SourceEntityEnergy4086_Result
 ora.l SourceEntityEnergy4086_Result+2
 beq SourceAttackPicker4086_RangeJump2
 jmp SourceAttackPicker4086_Range
SourceAttackPicker4086_RangeJump2:
.a16
.i16
 lda #0
 sta.l SourceEntityEnergy4086_Which
 jsl SourceEntityEnergy4086_Execute
 bcc SourceAttackPicker4086_Guard9
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard9:
.a16
.i16
 lda.l SourceEntityEnergy4086_Result
 ora.l SourceEntityEnergy4086_Result+2
 beq SourceAttackPicker4086_RangeJump3
 jmp SourceAttackPicker4086_Range
SourceAttackPicker4086_RangeJump3:
.a16
.i16
 jmp SourceAttackPicker4086_Next
SourceAttackPicker4086_NotSpecial:
.a16
.i16
 beq SourceAttackPicker4086_Throw
 jmp SourceAttackPicker4086_Range
SourceAttackPicker4086_Throw:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $43904C,x
 cmp #$B508
 beq SourceAttackPicker4086_Guard10
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard10:
.a16
.i16
 lda.l SourceAI4086_Flags
 tax
 lda.l $43EB1C,x
 ora.l $43EB1E,x
 bne SourceAttackPicker4086_WeaponPresent
 jmp SourceAttackPicker4086_Next
SourceAttackPicker4086_WeaponPresent:
.a16
.i16
 lda.l $43EB1E,x
 cmp #$41
 beq SourceAttackPicker4086_Guard11
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard11:
.a16
.i16
 lda.l $43EB1C,x
 cmp #$4000
 bcs SourceAttackPicker4086_Guard12
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard12:
.a16
.i16
 cmp #$6800
 bcc SourceAttackPicker4086_Guard13
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard13:
.a16
.i16
 sec
 sbc #$4000
 sta.l SourceAttackPicker4086_WeaponOffset
 lda #0
 sta.l SourceAttackPicker4086_WeaponSlot
SourceAttackPicker4086_WeaponLocate:
.a16
.i16
 lda.l SourceAttackPicker4086_WeaponOffset
 beq SourceAttackPicker4086_WeaponLocated
 cmp #80
 bcs SourceAttackPicker4086_Guard14
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard14:
.a16
.i16
 sec
 sbc #80
 sta.l SourceAttackPicker4086_WeaponOffset
 lda.l SourceAttackPicker4086_WeaponSlot
 inc a
 sta.l SourceAttackPicker4086_WeaponSlot
 bra SourceAttackPicker4086_WeaponLocate
SourceAttackPicker4086_WeaponLocated:
.a16
.i16
 lda.l SourceAttackPicker4086_WeaponSlot
 cmp.l VmSourceWorld_Count
 bcc SourceAttackPicker4086_Guard15
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard15:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 sta.l SourceAttackPicker4086_WeaponOffset
 clc
 adc #$4000
 tax
 pla
 txa
 cmp.l $410000,x
 beq SourceAttackPicker4086_Guard16
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard16:
.a16
.i16
 lda.l $410002,x
 cmp #$41
 beq SourceAttackPicker4086_Guard17
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard17:
.a16
.i16
 lda.l SourceAttackPicker4086_WeaponOffset
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceAttackPicker4086_Guard18
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard18:
.a16
.i16
 lda.l $439032,x
 beq SourceAttackPicker4086_WeaponSubtypeLow
 jmp SourceAttackPicker4086_Next
SourceAttackPicker4086_WeaponSubtypeLow:
.a16
.i16
 lda.l $439030,x
 cmp #9
 beq SourceAttackPicker4086_Range
 jmp SourceAttackPicker4086_Next
SourceAttackPicker4086_Range:
.a16
.i16
 lda.l SourceAttackPicker4086_Target
 cmp #$FFFF
 beq SourceAttackPicker4086_Append
 lda.l SourceAttackPicker4086_Role
 tax
 lda.l SourceAttackPicker4086_Target
 jsl SourceEntityRange4086_Execute
 bcc SourceAttackPicker4086_Guard19
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard19:
.a16
.i16
 lda.l SourceEntityRange4086_Result
 ora.l SourceEntityRange4086_Result+2
 bne SourceAttackPicker4086_Append
 jmp SourceAttackPicker4086_Next
SourceAttackPicker4086_Append:
.a16
.i16
 lda.l SourceAttackPicker4086_Options
 cmp #64
 bcc SourceAttackPicker4086_Guard20
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard20:
.a16
.i16
 asl a
 asl a
 tax
 lda.l SourceAttackPicker4086_Role
 sta.l SOURCE_ATTACK_CHOICES,x
 lda.l SourceAttackPicker4086_Weight
 sta.l SOURCE_ATTACK_CHOICES+2,x
 clc
 adc.l SourceAttackPicker4086_Total
 sta.l SourceAttackPicker4086_Total
 lda.l SourceAttackPicker4086_Options
 inc a
 sta.l SourceAttackPicker4086_Options
SourceAttackPicker4086_Next:
.a16
.i16
 lda.l SourceAttackPicker4086_Index
 inc a
 sta.l SourceAttackPicker4086_Index
 jmp SourceAttackPicker4086_Loop
SourceAttackPicker4086_Select:
.a16
.i16
 lda.l SourceAttackPicker4086_Total
 bne SourceAttackPicker4086_RandomCall
 lda #$FFFF
 sta.l SourceAttackPicker4086_Result
 sta.l SourceAttackPicker4086_Result+2
 jmp SourceAttackPicker4086_Done
SourceAttackPicker4086_RandomCall:
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
 bcc SourceAttackPicker4086_RandomGood
 jmp SourceAttackPicker4086_RandomBad
SourceAttackPicker4086_RandomGood:
.a16
.i16
 lda.l VmNativeVariant_Result+4
 sta.l SourceAttackPicker4086_Dividend
 pla
 sta.l VmNativeVariant_Result+6
 pla
 sta.l VmNativeVariant_Result+4
 pla
 sta.l VmNativeVariant_Result+2
 pla
 sta.l VmNativeVariant_Result
 lda #0
 sta.l SourceAttackPicker4086_Remainder
 lda #16
 sta.l SourceAttackPicker4086_Count
SourceAttackPicker4086_Modulo:
.a16
.i16
 lda.l SourceAttackPicker4086_Dividend
 asl a
 sta.l SourceAttackPicker4086_Dividend
 lda.l SourceAttackPicker4086_Remainder
 rol a
 cmp.l SourceAttackPicker4086_Total
 bcc SourceAttackPicker4086_ModuloStore
 sec
 sbc.l SourceAttackPicker4086_Total
SourceAttackPicker4086_ModuloStore:
.a16
.i16
 sta.l SourceAttackPicker4086_Remainder
 lda.l SourceAttackPicker4086_Count
 dec a
 sta.l SourceAttackPicker4086_Count
 bne SourceAttackPicker4086_Modulo
 lda #0
 sta.l SourceAttackPicker4086_Index
SourceAttackPicker4086_SelectOption:
.a16
.i16
 lda.l SourceAttackPicker4086_Index
 cmp.l SourceAttackPicker4086_Options
 bcc SourceAttackPicker4086_Guard21
 jmp SourceAttackPicker4086_Bad
SourceAttackPicker4086_Guard21:
.a16
.i16
 asl a
 asl a
 tax
 lda.l SourceAttackPicker4086_Remainder
 cmp.l SOURCE_ATTACK_CHOICES+2,x
 bcc SourceAttackPicker4086_Chosen
 sec
 sbc.l SOURCE_ATTACK_CHOICES+2,x
 sta.l SourceAttackPicker4086_Remainder
 lda.l SourceAttackPicker4086_Index
 inc a
 sta.l SourceAttackPicker4086_Index
 bra SourceAttackPicker4086_SelectOption
SourceAttackPicker4086_Chosen:
.a16
.i16
 lda.l SOURCE_ATTACK_CHOICES,x
 sta.l SourceAttackPicker4086_Result
 lda #0
 sta.l SourceAttackPicker4086_Result+2
SourceAttackPicker4086_Done:
.a16
.i16
 lda #2
 sta.l SourceAttackPicker4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceAttackPicker4086_RandomBad:
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
SourceAttackPicker4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAttackPicker4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceAttackPicker4086_Valid:
.a16
.i16
 lda.l SourceAttackPicker4086_Role
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcs SourceAttackPicker4086_ValidBad
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 beq SourceAttackPicker4086_ValidGood
 cmp.l SourceAttackChoiceProfile4086_Frames
 bcc SourceAttackPicker4086_ValidGood
 beq SourceAttackPicker4086_ValidGood
SourceAttackPicker4086_ValidBad:
.a16
.i16
 sec
 rts
SourceAttackPicker4086_ValidGood:
.a16
.i16
 clc
 rts
SourceAttackPicker4086_Weights:
.dw 16,13,10,7,4
