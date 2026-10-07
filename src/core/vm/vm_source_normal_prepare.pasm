; Source normal_prepare prefix and weighted normal attacks, with actual
; animation frame-zero continuation. Special, held weapon, chain and TURN
; branches remain explicit until executable.
; Callback 16 is a stable engine function identity, not an OAM/model name.
SourceNormalPrepare4086_Ready = $43BF42
SourceNormalPrepare4086_Status = $43BF44
SourceNormalPrepare4086_PreDirection = $43BF46
SourceNormalPrepare4086_Direction = $43BF4A
SourceNormalPrepare4086_TargetView = $43BF4E
SourceNormalPrepare4086_Index = $43BF50
SourceNormalPrepare4086_Role = $43BF52
SourceNormalPrepare4086_TurnID = $43BF54
SourceNormalPrepare4086_Options = $43BF56
SourceNormalPrepare4086_Total = $43BF58
SourceNormalPrepare4086_Dividend = $43BF5A
SourceNormalPrepare4086_Remainder = $43BF5C
SourceNormalPrepare4086_Count = $43BF5E
SourceNormalPrepare4086_End = $43BF60
SourceNormalPrepare4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceNormalPrepare4086_Ready
 cmp #$B606
 beq SourceNormalPrepare4086_Guard1
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard1:
.a16
.i16
 lda.l SourceNormalPrepare4086_Status
 beq SourceNormalPrepare4086_Start
 cmp #2
 beq SourceNormalPrepare4086_Guard2
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard2:
.a16
.i16
SourceNormalPrepare4086_Start:
.a16
.i16
 lda #1
 sta.l SourceNormalPrepare4086_Status
 jsl SourceAI4086_CheckOwner
 bcc SourceNormalPrepare4086_Guard3
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard3:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #1
 beq SourceNormalPrepare4086_Guard4
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard4:
.a16
.i16
 lda.l SourceAI4086_Callback
 cmp #16
 beq SourceNormalPrepare4086_Guard5
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard5:
.a16
.i16
 lda.l SourceAI4086_Callback+2
 beq SourceNormalPrepare4086_Guard6
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard6:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $43900C,x
 cmp #16
 beq SourceNormalPrepare4086_Guard7
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard7:
.a16
.i16
 lda.l $43900E,x
 beq SourceNormalPrepare4086_Guard8
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard8:
.a16
.i16
 jsl SourceAITarget4086_ActionUnbounded
 bcc SourceNormalPrepare4086_Guard9
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard9:
.a16
.i16
 lda.l SourceAI4086_Side
 tax
 lda #0
 sta.l $416824,x
 sta.l $416826,x
 sta.l $416828,x
 sta.l $41682A,x
 lda.l SourceAITarget4086_Result
 ora.l SourceAITarget4086_Result+2
 bne SourceNormalPrepare4086_Target
 jmp SourceNormalPrepare4086_NoAttack
SourceNormalPrepare4086_Target:
.a16
.i16
 lda.l SourceAI4086_Model
 tax
 lda.l SourceAI4086_Slot
 jsl SourceAttackBody4086_ReadEntity
 bcc SourceNormalPrepare4086_Guard10
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard10:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410018,x
 cmp #1
 beq SourceNormalPrepare4086_Guard11
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard11:
.a16
.i16
 lda.l $41001A,x
 beq SourceNormalPrepare4086_Guard12
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard12:
.a16
.i16
 lda.l $41001C,x
 sta.l SourceNormalPrepare4086_PreDirection
 sta.l SourceNormalPrepare4086_Direction
 lda.l $41001E,x
 sta.l SourceNormalPrepare4086_PreDirection+2
 sta.l SourceNormalPrepare4086_Direction+2
 lda.l SourceAttackBody4086_NoFlip
 ora.l SourceAttackBody4086_NoFlip+2
 bne SourceNormalPrepare4086_TurnCheck
 lda.l SourceAITarget4086_Selected
 asl a
 asl a
 asl a
 asl a
 sta.l SourceNormalPrepare4086_TargetView
 asl a
 asl a
 clc
 adc.l SourceNormalPrepare4086_TargetView
 clc
 adc #$4000
 sta.l SourceNormalPrepare4086_TargetView
 tay
 tya
 tax
 lda.l $410030,x
 cmp #2
 beq SourceNormalPrepare4086_TargetCoordinate
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_TargetCoordinate:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410034,x
 pha
 lda.l $410036,x
 pha
 tya
 tax
 lda 1,s
 eor #$8000
 sta.l SourceNormalPrepare4086_Direction
 lda.l $410036,x
 eor #$8000
 cmp.l SourceNormalPrepare4086_Direction
 beq SourceNormalPrepare4086_CompareLow
 bcc SourceNormalPrepare4086_DirectionFalse
 bra SourceNormalPrepare4086_DirectionTrue
SourceNormalPrepare4086_CompareLow:
.a16
.i16
 lda.l $410034,x
 cmp 3,s
 beq SourceNormalPrepare4086_DirectionFalse
 bcc SourceNormalPrepare4086_DirectionFalse
SourceNormalPrepare4086_DirectionTrue:
.a16
.i16
 pla
 pla
 lda #1
 bra SourceNormalPrepare4086_DirectionStore
SourceNormalPrepare4086_DirectionFalse:
.a16
.i16
 pla
 pla
 lda #0
SourceNormalPrepare4086_DirectionStore:
.a16
.i16
 sta.l SourceNormalPrepare4086_Direction
 lda #0
 sta.l SourceNormalPrepare4086_Direction+2
SourceNormalPrepare4086_TurnCheck:
.a16
.i16
 lda.l SourceNormalPrepare4086_Direction
 cmp.l SourceNormalPrepare4086_PreDirection
 bne SourceNormalPrepare4086_ChangedDirection
 lda.l SourceNormalPrepare4086_Direction+2
 cmp.l SourceNormalPrepare4086_PreDirection+2
 beq SourceNormalPrepare4086_DirectionReady
SourceNormalPrepare4086_ChangedDirection:
.a16
.i16
 lda.l SourceNormalPrepare4086_TurnID
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcc SourceNormalPrepare4086_Guard14
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard14:
.a16
.i16
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 beq SourceNormalPrepare4086_Guard15
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard15:
.a16
.i16
SourceNormalPrepare4086_DirectionReady:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l SourceNormalPrepare4086_Direction
 sta.l $41001C,x
 lda.l SourceNormalPrepare4086_Direction+2
 sta.l $41001E,x
 lda.l SourceAI4086_Freeze
 tax
 lda.l VmSourceWorld_Time+2
 cmp.l $42E00A,x
 bcs SourceNormalPrepare4086_TimerHigh
 jmp SourceNormalPrepare4086_Done
SourceNormalPrepare4086_TimerHigh:
.a16
.i16
 bne SourceNormalPrepare4086_Attack
 lda.l VmSourceWorld_Time
 cmp.l $42E008,x
 bcs SourceNormalPrepare4086_Attack
 jmp SourceNormalPrepare4086_Done
SourceNormalPrepare4086_Attack:
.a16
.i16
 lda.l SourceAI4086_Flags
 tax
 lda.l $43EB1C,x
 ora.l $43EB1E,x
 beq SourceNormalPrepare4086_Guard16
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard16:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Ready
 cmp #$B5FE
 beq SourceNormalPrepare4086_Guard17
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard17:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Status
 cmp #2
 beq SourceNormalPrepare4086_Guard18
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard18:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Maximum
 cmp.l SourceModelAnimationCopy4086_Maximum
 beq SourceNormalPrepare4086_Guard19
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard19:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Normals
 sta.l SourceNormalPrepare4086_Index
SourceNormalPrepare4086_SpecialLoop:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Normals
 clc
 adc.l SourceAttackChoiceProfile4086_Specials
 cmp.l SourceNormalPrepare4086_Index
 beq SourceNormalPrepare4086_Random
 jsr SourceNormalPrepare4086_MissingRole
 bcc SourceNormalPrepare4086_NextSpecial
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_NextSpecial:
.a16
.i16
 lda.l SourceNormalPrepare4086_Index
 inc a
 sta.l SourceNormalPrepare4086_Index
 bra SourceNormalPrepare4086_SpecialLoop
SourceNormalPrepare4086_Random:
.a16
.i16
 lda.l VmNativeVariant_Result+0
 pha
 lda.l VmNativeVariant_Result+2
 pha
 lda.l VmNativeVariant_Result+4
 pha
 lda.l VmNativeVariant_Result+6
 pha
 jsl SourceRandom4086_Next
 bcc SourceNormalPrepare4086_RandomGood
 pla
 sta.l VmNativeVariant_Result+6
 pla
 sta.l VmNativeVariant_Result+4
 pla
 sta.l VmNativeVariant_Result+2
 pla
 sta.l VmNativeVariant_Result+0
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_RandomGood:
.a16
.i16
 pla
 sta.l VmNativeVariant_Result+6
 pla
 sta.l VmNativeVariant_Result+4
 pla
 sta.l VmNativeVariant_Result+2
 pla
 sta.l VmNativeVariant_Result+0
 lda.l SourceAttackBody4086_Chain+4
 lsr a
 lsr a
 lsr a
 lsr a
 and #15
 cmp #2
 bcc SourceNormalPrepare4086_Guard20
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Guard20:
.a16
.i16
 lda #0
 sta.l SourceNormalPrepare4086_Index
 sta.l SourceNormalPrepare4086_Options
 sta.l SourceNormalPrepare4086_Total
SourceNormalPrepare4086_NormalLoop:
.a16
.i16
 lda.l SourceNormalPrepare4086_Index
 cmp.l SourceAttackChoiceProfile4086_Normals
 bne SourceNormalPrepare4086_NormalCandidate
 jmp SourceNormalPrepare4086_Select
SourceNormalPrepare4086_NormalCandidate:
.a16
.i16
 jsr SourceNormalPrepare4086_ResolveRole
 bcc SourceNormalPrepare4086_NormalResolved
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_NormalResolved:
.a16
.i16
 ora #0
 beq SourceNormalPrepare4086_NextNormal
 lda.l SourceNormalPrepare4086_Role
 tax
 lda.l SourceAITarget4086_Selected
 jsl SourceEntityRange4086_Execute
 bcc SourceNormalPrepare4086_NormalRange
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_NormalRange:
.a16
.i16
 lda.l SourceEntityRange4086_Result
 ora.l SourceEntityRange4086_Result+2
 beq SourceNormalPrepare4086_NextNormal
 lda.l SourceNormalPrepare4086_Options
 cmp #64
 bcc SourceNormalPrepare4086_Append
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Append:
.a16
.i16
 asl a
 asl a
 tax
 lda.l SourceNormalPrepare4086_Role
 sta.l SOURCE_ATTACK_CHOICES,x
 lda.l SourceNormalPrepare4086_Index
 cmp #6
 bcs SourceNormalPrepare4086_UnitWeight
 lda #6
 sec
 sbc.l SourceNormalPrepare4086_Index
 bra SourceNormalPrepare4086_StoreWeight
SourceNormalPrepare4086_UnitWeight:
.a16
.i16
 lda #1
SourceNormalPrepare4086_StoreWeight:
.a16
.i16
 sta.l SOURCE_ATTACK_CHOICES+2,x
 clc
 adc.l SourceNormalPrepare4086_Total
 sta.l SourceNormalPrepare4086_Total
 lda.l SourceNormalPrepare4086_Options
 inc a
 sta.l SourceNormalPrepare4086_Options
SourceNormalPrepare4086_NextNormal:
.a16
.i16
 lda.l SourceNormalPrepare4086_Index
 inc a
 sta.l SourceNormalPrepare4086_Index
 jmp SourceNormalPrepare4086_NormalLoop
SourceNormalPrepare4086_Select:
.a16
.i16
 lda.l SourceNormalPrepare4086_Total
 bne SourceNormalPrepare4086_ChoiceRandom
 jmp SourceNormalPrepare4086_NoAttack
SourceNormalPrepare4086_ChoiceRandom:
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
 bcc SourceNormalPrepare4086_ChoiceRandomGood
 pla
 sta.l VmNativeVariant_Result+6
 pla
 sta.l VmNativeVariant_Result+4
 pla
 sta.l VmNativeVariant_Result+2
 pla
 sta.l VmNativeVariant_Result
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_ChoiceRandomGood:
.a16
.i16
 lda.l VmNativeVariant_Result+4
 sta.l SourceNormalPrepare4086_Dividend
 pla
 sta.l VmNativeVariant_Result+6
 pla
 sta.l VmNativeVariant_Result+4
 pla
 sta.l VmNativeVariant_Result+2
 pla
 sta.l VmNativeVariant_Result
 lda #0
 sta.l SourceNormalPrepare4086_Remainder
 lda #16
 sta.l SourceNormalPrepare4086_Count
SourceNormalPrepare4086_Modulo:
.a16
.i16
 lda.l SourceNormalPrepare4086_Dividend
 asl a
 sta.l SourceNormalPrepare4086_Dividend
 lda.l SourceNormalPrepare4086_Remainder
 rol a
 cmp.l SourceNormalPrepare4086_Total
 bcc SourceNormalPrepare4086_ModuloStore
 sec
 sbc.l SourceNormalPrepare4086_Total
SourceNormalPrepare4086_ModuloStore:
.a16
.i16
 sta.l SourceNormalPrepare4086_Remainder
 lda.l SourceNormalPrepare4086_Count
 dec a
 sta.l SourceNormalPrepare4086_Count
 bne SourceNormalPrepare4086_Modulo
 lda #0
 sta.l SourceNormalPrepare4086_Index
SourceNormalPrepare4086_ChoiceLoop:
.a16
.i16
 lda.l SourceNormalPrepare4086_Index
 cmp.l SourceNormalPrepare4086_Options
 bcc SourceNormalPrepare4086_ChoiceBounded
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_ChoiceBounded:
.a16
.i16
 asl a
 asl a
 tax
 lda.l SourceNormalPrepare4086_Remainder
 cmp.l SOURCE_ATTACK_CHOICES+2,x
 bcc SourceNormalPrepare4086_Chosen
 sec
 sbc.l SOURCE_ATTACK_CHOICES+2,x
 sta.l SourceNormalPrepare4086_Remainder
 lda.l SourceNormalPrepare4086_Index
 inc a
 sta.l SourceNormalPrepare4086_Index
 bra SourceNormalPrepare4086_ChoiceLoop
SourceNormalPrepare4086_Chosen:
.a16
.i16
 lda.l SOURCE_ATTACK_CHOICES,x
 sta.l SourceAnimationInit4086_Number
 lda.l SourceAI4086_Life
 tax
 lda #17
 sta.l $43900C,x
 lda #0
 sta.l $43900E,x
 lda.l SourceAI4086_Flags
 tax
 lda #0
 sta.l $43EB00,x
 sta.l $43EB02,x
 lda.l SourceAI4086_Flags
 asl a
 clc
 adc.l SourceAI4086_Flags
 tax
 lda #1
 sta.l $40C058,x
 lda #0
 sta.l $40C05A,x
 lda.l SourceAI4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda #0
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Begin
 bcc SourceNormalPrepare4086_AnimationStarted
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_AnimationStarted:
.a16
.i16
 lda.l SourceAnimationInit4086_State
 cmp #2
 bne SourceNormalPrepare4086_AnimationPending
 jmp SourceNormalPrepare4086_Done
SourceNormalPrepare4086_AnimationPending:
.a16
.i16
 cmp #1
 beq SourceNormalPrepare4086_Pending
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_Pending:
.a16
.i16
 lda #1
 ply
 plx
 plp
 clc
 rtl
SourceNormalPrepare4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceNormalPrepare4086_Ready
 cmp #$B606
 beq SourceNormalPrepare4086_ContinueReady
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_ContinueReady:
.a16
.i16
 lda.l SourceNormalPrepare4086_Status
 cmp #1
 beq SourceNormalPrepare4086_ContinuePending
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_ContinuePending:
.a16
.i16
 jsl SourceAI4086_CheckOwner
 bcc SourceNormalPrepare4086_ContinueOwner
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_ContinueOwner:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #1
 beq SourceNormalPrepare4086_ContinueAction
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_ContinueAction:
.a16
.i16
 lda.l SourceAI4086_Slot
 cmp.l SourceAnimationInit4086_Slot
 beq SourceNormalPrepare4086_ContinueSlot
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_ContinueSlot:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceNormalPrepare4086_ContinueFrame
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_ContinueFrame:
.a16
.i16
 jsl SourceAnimationInit4086_Ack
 bcc SourceNormalPrepare4086_Done
 jmp SourceNormalPrepare4086_Bad
SourceNormalPrepare4086_NoAttack:
.a16
.i16
 lda.l SourceAI4086_Flags
 tax
 lda #1
 sta.l $43EB00,x
 lda #0
 sta.l $43EB02,x
 lda.l SourceAI4086_Life
 tax
 lda #0
 sta.l $43900C,x
 sta.l $43900E,x
SourceNormalPrepare4086_Done:
.a16
.i16
 lda #2
 sta.l SourceNormalPrepare4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceNormalPrepare4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceNormalPrepare4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceNormalPrepare4086_MissingRole:
.a16
.i16
 lda.l SourceNormalPrepare4086_Index
 asl a
 tax
 lda.l SOURCE_ATTACK_CHOICE_ROLES,x
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcs SourceNormalPrepare4086_RoleBad
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 bne SourceNormalPrepare4086_RoleBad
 clc
 rts
SourceNormalPrepare4086_RoleBad:
.a16
.i16
 sec
 rts
SourceNormalPrepare4086_ResolveRole:
.a16
.i16
 lda.l SourceNormalPrepare4086_Index
 asl a
 tax
 lda.l SOURCE_ATTACK_CHOICE_ROLES,x
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcs SourceNormalPrepare4086_ResolveBad
 sta.l SourceNormalPrepare4086_Role
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 clc
 rts
SourceNormalPrepare4086_ResolveBad:
.a16
.i16
 sec
 rts
