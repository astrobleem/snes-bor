; Closed constructor body prelude. Caller has selected a free pool slot and
; completed named/script cleanup and independent factor copying. B5CI identity
; and immutable name/table CRC must be checked before Ready is granted.
; Clear transient entity state, preserve token/sort/resources, publish exists/count
; before shared script binding. Finish follows model install/bind, before default-init.
; Body/name/map identity rows $433800..$4357FF: name48, mapH, palette ownerH,
; draw flag32, boss32, spawntypeH, leaseH. Reset clears post-spawn fields.
; This does not execute drawmethod or palette uploads.
SourceCtorState4086_Ready = $43B848
SourceCtorState4086_Status = $43B84A
SourceCtorState4086_Base = $43B84C
SourceCtorState4086_Bank = $43B84E
SourceCtorState4086_Bytes = $43B850
SourceCtorState4086_Models = $43B852
SourceCtorState4086_X = $43B854
SourceCtorState4086_Z = $43B858
SourceCtorState4086_A = $43B85C
SourceCtorState4086_Direction = $43B860
SourceCtorState4086_Time = $43B864
SourceCtorState4086_Player = $43B868
SourceCtorState4086_NoHit = $43B86C
SourceCtorState4086_SavedMode = $43B86E
SourceCtorState4086_Row = $43B870
SourceCtorState4086_Value = $43B872
SourceCtorState4086_View = $43B874
SourceCtorState4086_Side = $43B876
SourceCtorState4086_Relation = $43B878
SourceCtorState4086_Name = $43B87A
SourceCtorState4086_Index = $43B87C
SourceCtorState4086_Count = $43B87E
SourceCtorState4086_End = $43B880

SourceCtorState4086_Reset:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceScriptClone4086_Status
 cmp #2
 beq SourceCtorState4086_CleanupDone
 jmp SourceCtorState4086_Bad
SourceCtorState4086_CleanupDone:
.a16
.i16
 jsl SourceScriptClone4086_CheckModelProgram
 bcc SourceCtorState4086_ProgramValid
 jmp SourceCtorState4086_Bad
SourceCtorState4086_ProgramValid:
.a16
.i16
 jsl SourceCtorModel4086_Preflight
 bcc SourceCtorState4086_Guard_1
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_1:
.a16
.i16
 lda.l SourceScriptClone4086_Status
 cmp #2
 beq SourceCtorState4086_Guard_2
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_2:
.a16
.i16
 lda.l SourceCtorState4086_Ready
 cmp #$B5C2
 beq SourceCtorState4086_Guard_3
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_3:
.a16
.i16
 lda.l SourceCtorState4086_Status
 beq SourceCtorState4086_Guard_4
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_4:
.a16
.i16
 lda.l SourceCtorState4086_Models
 cmp.l SourceScriptClone4086_Models
 beq SourceCtorState4086_Guard_5
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_5:
.a16
.i16
 lda.l SourceCtorState4086_Base
 cmp #$8000
 bcs SourceCtorState4086_Guard_6
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_6:
.a16
.i16
 lda.l SourceCtorState4086_Bank
 bne SourceCtorState4086_Guard_7
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_7:
.a16
.i16
 cmp #64
 bcc SourceCtorState4086_Guard_8
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_8:
.a16
.i16
 lda.l SourceCtorState4086_Models
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 cmp.l SourceCtorState4086_Bytes
 beq SourceCtorState4086_Guard_9
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_9:
.a16
.i16
 dec a
 clc
 adc.l SourceCtorState4086_Base
 bcc SourceCtorState4086_Guard_10
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_10:
.a16
.i16
 lda.l SourceCtorState4086_NoHit
 cmp #2
 bcc SourceCtorState4086_Guard_11
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_11:
.a16
.i16
 lda.l SourceCtorState4086_SavedMode
 cmp #2
 bcc SourceCtorState4086_Guard_12
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_12:
.a16
.i16
 lda.l VmSourceWorld_Level
 cmp #2
 bcc SourceCtorState4086_Guard_13
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_13:
.a16
.i16
 lda.l SourceCtorState4086_Player+2
 beq SourceCtorState4086_Guard_14
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_14:
.a16
.i16
 lda.l SourceCtorState4086_Player
 cmp #4
 bcc SourceCtorState4086_Guard_15
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_15:
.a16
.i16
 lda.l SourceCtorModel4086_View
 sta.l SourceCtorState4086_View
 tax
 lda.l $414004,x
 ora.l $414006,x
 beq SourceCtorState4086_Guard_16
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_16:
.a16
.i16
 lda.l SourceCtorModel4086_Side
 sta.l SourceCtorState4086_Side
 sta.l SourceCtorState4086_Relation
 sta.l SourceCtorState4086_Name
 ldx #0
 jsr SourceCtorState4086_Read
 cmp #$3542
 beq SourceCtorState4086_Guard_17
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_17:
.a16
.i16
 ldx #2
 jsr SourceCtorState4086_Read
 cmp #$4943
 beq SourceCtorState4086_Guard_18
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_18:
.a16
.i16
 ldx #4
 jsr SourceCtorState4086_Read
 cmp #1
 beq SourceCtorState4086_Guard_19
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_19:
.a16
.i16
 ldx #6
 jsr SourceCtorState4086_Read
 cmp #64
 beq SourceCtorState4086_Guard_20
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_20:
.a16
.i16
 ldx #8
 jsr SourceCtorState4086_Read
 cmp.l SourceCtorState4086_Models
 beq SourceCtorState4086_Guard_21
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_21:
.a16
.i16
 ldx #10
 jsr SourceCtorState4086_Read
 beq SourceCtorState4086_Guard_22
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_22:
.a16
.i16
 ldx #12
 jsr SourceCtorState4086_Read
 clc
 adc #24
 cmp.l SourceCtorState4086_Bytes
 beq SourceCtorState4086_Guard_23
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_23:
.a16
.i16
 ldx #14
 jsr SourceCtorState4086_Read
 beq SourceCtorState4086_Guard_24
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_24:
.a16
.i16
 ldx #20
 jsr SourceCtorState4086_Read
 beq SourceCtorState4086_Guard_25
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_25:
.a16
.i16
 ldx #22
 jsr SourceCtorState4086_Read
 beq SourceCtorState4086_Guard_26
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_26:
.a16
.i16
 lda.l SourceScriptClone4086_Model
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 sta.l SourceCtorState4086_Row
 tax
 jsr SourceCtorState4086_Read
 cmp.l SourceScriptClone4086_Model
 beq SourceCtorState4086_Guard_27
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_27:
.a16
.i16
 inx
 inx
 jsr SourceCtorState4086_Read
 beq SourceCtorState4086_Guard_28
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_28:
.a16
.i16
 lda.l SourceCtorState4086_Row
 clc
 adc #12
 tax
 jsr SourceCtorState4086_Read
 cmp #7
 bcc SourceCtorState4086_Guard_29
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_29:
.a16
.i16
 inx
 inx
 jsr SourceCtorState4086_Read
 bne SourceCtorState4086_Guard_30
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_30:
.a16
.i16
 cmp #48
 bcc SourceCtorState4086_Guard_31
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_31:
.a16
.i16
 ; Existing source roles must match the actual pool before publishing a birth.
 lda #0
 sta.l SourceCtorState4086_Count
 sta.l SourceCtorState4086_Index
 ldx #0
SourceCtorState4086_CountLoop:
.a16
.i16
 lda.l $414006,x
 beq SourceCtorState4086_Guard_32
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_32:
.a16
.i16
 lda.l $414004,x
 cmp #2
 bcc SourceCtorState4086_Guard_33
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_33:
.a16
.i16
 clc
 adc.l SourceCtorState4086_Count
 sta.l SourceCtorState4086_Count
 txa
 clc
 adc #80
 tax
 lda.l SourceCtorState4086_Index
 inc a
 sta.l SourceCtorState4086_Index
 cmp.l VmSourceWorld_Count
 bcs SourceCtorState4086_Guard_34
 jmp SourceCtorState4086_CountLoop
SourceCtorState4086_Guard_34:
.a16
.i16
 lda.l $43FD82
 beq SourceCtorState4086_Guard_35
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_35:
.a16
.i16
 lda.l SourceCtorState4086_Count
 cmp.l $43FD80
 beq SourceCtorState4086_Guard_36
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_36:
.a16
.i16
 lda.l SourceWorldTick4086_Maximum
 cmp.l VmSourceWorld_Count
 bcs SourceCtorState4086_Guard_37
 jmp SourceCtorState4086_MaximumValid
SourceCtorState4086_Guard_37:
.a16
.i16
 bne SourceCtorState4086_Guard_38
 jmp SourceCtorState4086_MaximumValid
SourceCtorState4086_Guard_38:
.a16
.i16
 jmp SourceCtorState4086_Bad
SourceCtorState4086_MaximumValid:
.a16
.i16
 jsl SourceFreeze4086_PreflightBirth
 bcc SourceCtorState4086_FreezePreflightOk
 jmp SourceCtorState4086_Bad
SourceCtorState4086_FreezePreflightOk:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 jsl SourceAttackCostState4086_PreflightBirth
 bcc SourceCtorState4086_CostPreflightOk
 jmp SourceCtorState4086_Bad
SourceCtorState4086_CostPreflightOk:
.a16
.i16
 jsl SourceMovementState4086_PreflightBirth
 bcc SourceCtorState4086_MovementPreflightOk
 jmp SourceCtorState4086_Bad
SourceCtorState4086_MovementPreflightOk:
.a16
.i16
 jsl SourceAutokillState4086_PreflightBirth
 bcc SourceCtorState4086_AutokillMovementPreflightOk
 jmp SourceCtorState4086_Bad
SourceCtorState4086_AutokillMovementPreflightOk:
.a16
.i16
 jsl SourceOffscreenState4086_PreflightBirth
 bcc SourceCtorState4086_OffscreenAutokillMovementPreflightOk
 jmp SourceCtorState4086_Bad
SourceCtorState4086_OffscreenAutokillMovementPreflightOk:
.a16
.i16
 ; All external domains validated; no callback occurs during the reset.
 lda.l SourceCtorState4086_View
 clc
 adc #4
 tax
 ldy #38
 lda #0
SourceCtorState4086_ClearView:
.a16
.i16
 sta.l $414000,x
 inx
 inx
 dey
 beq SourceCtorState4086_Guard_39
 jmp SourceCtorState4086_ClearView
SourceCtorState4086_Guard_39:
.a16
.i16
 lda.l SourceCtorState4086_Side
 clc
 adc #0
 tax
 ldy #32
 lda #0
SourceCtorState4086_ClearSide:
.a16
.i16
 sta.l $416800,x
 inx
 inx
 dey
 beq SourceCtorState4086_Guard_40
 jmp SourceCtorState4086_ClearSide
SourceCtorState4086_Guard_40:
.a16
.i16
 lda.l SourceCtorState4086_Relation
 clc
 adc #0
 tax
 ldy #32
 lda #0
SourceCtorState4086_ClearRelation:
.a16
.i16
 sta.l $409000,x
 inx
 inx
 dey
 beq SourceCtorState4086_Guard_41
 jmp SourceCtorState4086_ClearRelation
SourceCtorState4086_Guard_41:
.a16
.i16
 lda.l SourceCtorState4086_Name
 clc
 adc #0
 tax
 ldy #32
 lda #0
SourceCtorState4086_ClearName:
.a16
.i16
 sta.l $433800,x
 inx
 inx
 dey
 beq SourceCtorState4086_Guard_42
 jmp SourceCtorState4086_ClearName
SourceCtorState4086_Guard_42:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 ldy #16
 lda #0
SourceCtorState4086_ClearFlags:
.a16
.i16
 sta.l $43EB00,x
 inx
 inx
 dey
 beq SourceCtorState4086_Guard_43
 jmp SourceCtorState4086_ClearFlags
SourceCtorState4086_Guard_43:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 asl a
 asl a
 sta.l SourceCtorState4086_Value
 asl a
 asl a
 clc
 adc.l SourceCtorState4086_Value
 tax
 ldy #10
 lda #0
SourceCtorState4086_ClearAux:
.a16
.i16
 sta.l $41F500,x
 inx
 inx
 dey
 beq SourceCtorState4086_Guard_44
 jmp SourceCtorState4086_ClearAux
SourceCtorState4086_Guard_44:
.a16
.i16
 jsl SourceFreeze4086_InitializeBirth
 bcc SourceCtorState4086_FreezeBirthDone
 jmp SourceCtorState4086_Bad
SourceCtorState4086_FreezeBirthDone:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 jsl SourceCombatState4086_BirthClear
 lda.l SourceScriptClone4086_Slot
 jsl SourceAttackCostState4086_BirthClear
 bcc SourceCtorState4086_CostBirthDone
 jmp SourceCtorState4086_Bad
SourceCtorState4086_CostBirthDone:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 jsl SourceMovementState4086_BirthClear
 bcc SourceCtorState4086_MovementBirthDone
 jmp SourceCtorState4086_Bad
SourceCtorState4086_MovementBirthDone:
.a16
.i16
 jsl SourceAutokillState4086_BirthClear
 bcc SourceCtorState4086_AutokillMovementBirthDone
 jmp SourceCtorState4086_Bad
SourceCtorState4086_AutokillMovementBirthDone:
.a16
.i16
 jsl SourceOffscreenState4086_BirthClear
 bcc SourceCtorState4086_OffscreenAutokillMovementBirthDone
 jmp SourceCtorState4086_Bad
SourceCtorState4086_OffscreenAutokillMovementBirthDone:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 jsl SourceAIState4086_InitializeBirth
 bcc SourceCtorState4086_AIStateBirthDone
 jmp SourceCtorState4086_Bad
SourceCtorState4086_AIStateBirthDone:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 jsl SourcePhysicsState4086_InitializeBirth
 bcc SourceCtorState4086_PhysicsStateBirthDone
 jmp SourceCtorState4086_Bad
SourceCtorState4086_PhysicsStateBirthDone:
.a16
.i16
 lda.l SourceCtorState4086_View
 tax
 lda #1
 sta.l $414004,x
 lda #2
 sta.l $414008,x
 lda #1
 sta.l $414010,x
 lda #1
 sta.l $414018,x
 lda #1
 sta.l $414020,x
 lda #1
 sta.l $414028,x
 lda #2
 sta.l $414030,x
 lda #2
 sta.l $414038,x
 lda #1
 sta.l $414040,x
 lda.l SourceCtorState4086_A
 sta.l $41400C,x
 lda.l SourceCtorState4086_A+2
 sta.l $41400E,x
 lda.l SourceCtorState4086_Direction
 sta.l $41401C,x
 lda.l SourceCtorState4086_Direction+2
 sta.l $41401E,x
 lda.l SourceCtorState4086_X
 sta.l $414034,x
 lda.l SourceCtorState4086_X+2
 sta.l $414036,x
 lda.l SourceCtorState4086_Z
 sta.l $41403C,x
 lda.l SourceCtorState4086_Z+2
 sta.l $41403E,x
 lda.l SourceCtorState4086_Side
 tax
 lda.l SourceCtorState4086_Time
 sta.l $41680C,x
 lda.l SourceCtorState4086_Time+2
 sta.l $41680E,x
 lda.l SourceCtorState4086_Time
 clc
 adc #1
 sta.l $416814,x
 sta.l $416818,x
 lda.l SourceCtorState4086_Time+2
 adc #0
 sta.l $416816,x
 sta.l $41681A,x
 lda #1
 sta.l $416822,x
 ; Source lifespan and alpha, distinct from the presentation capability.
 lda.l SourceCtorState4086_Row
 clc
 adc #4
 tax
 jsr SourceCtorState4086_Read
 pha
 inx
 inx
 jsr SourceCtorState4086_Read
 pha
 lda.l SourceCtorState4086_Side
 tax
 pla
 sta.l $416812,x
 pla
 sta.l $416810,x
 lda.l SourceCtorState4086_Row
 clc
 adc #12
 tax
 jsr SourceCtorState4086_Read
 pha
 lda.l SourceCtorState4086_Side
 tax
 pla
 sta.l $41681E,x
 ; Source display name, full 48-byte zero-terminated storage.
 lda #0
 sta.l SourceCtorState4086_Index
SourceCtorState4086_NameLoop:
.a16
.i16
 lda.l SourceCtorState4086_Row
 clc
 adc #16
 clc
 adc.l SourceCtorState4086_Index
 tax
 jsr SourceCtorState4086_Read
 sta.l SourceCtorState4086_Value
 lda.l SourceCtorState4086_Name
 clc
 adc.l SourceCtorState4086_Index
 tax
 lda.l SourceCtorState4086_Value
 sta.l $433800,x
 lda.l SourceCtorState4086_Index
 inc a
 inc a
 sta.l SourceCtorState4086_Index
 cmp #48
 bcs SourceCtorState4086_Guard_45
 jmp SourceCtorState4086_NameLoop
SourceCtorState4086_Guard_45:
.a16
.i16
 lda.l SourceCtorState4086_Count
 inc a
 sta.l SourceCtorState4086_Count
 sta.l $43FD80
 cmp.l SourceWorldTick4086_Maximum
 bcs SourceCtorState4086_Guard_46
 jmp SourceCtorState4086_MaximumDone
SourceCtorState4086_Guard_46:
.a16
.i16
 sta.l SourceWorldTick4086_Maximum
SourceCtorState4086_MaximumDone:
.a16
.i16
 lda #1
 sta.l SourceCtorState4086_Status
 jmp SourceCtorState4086_Good

SourceCtorState4086_Finish:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCtorState4086_Ready
 cmp #$B5C2
 beq SourceCtorState4086_Guard_47
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_47:
.a16
.i16
 lda.l SourceCtorState4086_Status
 cmp #1
 beq SourceCtorState4086_Guard_48
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_48:
.a16
.i16
 lda.l SourceCtorModel4086_Status
 cmp #2
 beq SourceCtorState4086_Guard_49
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_49:
.a16
.i16
 jsr SourceScriptClone4086_Preflight
 bcc SourceCtorState4086_Guard_50
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_50:
.a16
.i16
 lda.l SourceScriptClone4086_Status
 cmp #2
 beq SourceCtorState4086_Guard_51
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_51:
.a16
.i16
 lda.l SourceCtorState4086_Side
 cmp.l SourceScriptClone4086_Relation
 beq SourceCtorState4086_Guard_52
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_52:
.a16
.i16
 tax
 lda.l $416800,x
 cmp.l SourceScriptClone4086_Model
 beq SourceCtorState4086_Guard_53
 jmp SourceCtorState4086_Bad
SourceCtorState4086_Guard_53:
.a16
.i16
 lda.l SourceCtorState4086_Row
 tax
 jsr SourceCtorState4086_Read
 cmp.l SourceScriptClone4086_Model
 beq SourceCtorState4086_FinishModelPaired
 jmp SourceCtorState4086_Bad
SourceCtorState4086_FinishModelPaired:
.a16
.i16
 lda.l SourceCtorState4086_View
 cmp.l SourceCtorModel4086_View
 beq SourceCtorState4086_FinishViewPaired
 jmp SourceCtorState4086_Bad
SourceCtorState4086_FinishViewPaired:
.a16
.i16
 lda.l SourceCtorState4086_Row
 clc
 adc #8
 tax
 jsr SourceCtorState4086_Read
 pha
 inx
 inx
 jsr SourceCtorState4086_Read
 pha
 lda.l SourceCtorState4086_Relation
 tax
 pla
 sta.l $409026,x
 pla
 sta.l $409024,x
 lda.l SourceCtorModel4086_Core
 tax
 lda.l $40C048,x
 and #1
 bne SourceCtorState4086_Guard_54
 jmp SourceCtorState4086_NotPlayer
SourceCtorState4086_Guard_54:
.a16
.i16
 lda.l SourceCtorState4086_View
 tax
 lda.l SourceCtorState4086_Player
 sta.l $41402C,x
 lda.l SourceCtorState4086_Player+2
 sta.l $41402E,x
 lda.l SourceCtorState4086_SavedMode
 beq SourceCtorState4086_Guard_55
 jmp SourceCtorState4086_MaskPlayer
SourceCtorState4086_Guard_55:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceCtorState4086_Guard_56
 jmp SourceCtorState4086_NotPlayer
SourceCtorState4086_Guard_56:
.a16
.i16
 lda.l SourceCtorState4086_NoHit
 bne SourceCtorState4086_Guard_57
 jmp SourceCtorState4086_NotPlayer
SourceCtorState4086_Guard_57:
.a16
.i16
SourceCtorState4086_MaskPlayer:
.a16
.i16
 lda.l SourceCtorModel4086_Core
 tax
 lda.l $40C028,x
 and #$FFFE
 sta.l $40C028,x
 lda.l $40C02C,x
 and #$FFFE
 sta.l $40C02C,x
SourceCtorState4086_NotPlayer:
.a16
.i16
 lda.l SourceCtorModel4086_Core
 tax
 lda.l $40C048,x
 and #128
 beq SourceCtorState4086_NoTextbox
 lda.l SourceScriptClone4086_Token
 sta.l $43FD98
 lda #$41
 sta.l $43FD9A
SourceCtorState4086_NoTextbox:
.a16
.i16
 lda.l SourceCtorState4086_Name
 tax
 lda.l SourceScriptClone4086_Model
 sta.l $433832,x
 lda #$B5C2
 sta.l $43383E,x
 lda #2
 sta.l SourceCtorState4086_Status
SourceCtorState4086_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceCtorState4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCtorState4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceCtorState4086_Read:
.a16
.i16
 phb
 phx
 txa
 clc
 adc.l SourceCtorState4086_Base
 tax
 sep #$20
.a8
 lda.l SourceCtorState4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plx
 plb
 ora #0
 rts

; Synchronous pre-default-init body owner. Cleanup and factor copy precede this
; call. It never runs callbacks; the caller next enters DefaultInit Begin/Continue.
SourceCtorState4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceFactors4086_Ready
 cmp #$B5F1
 beq SourceCtorState4086_BeginGuard_1
 jmp SourceCtorState4086_BeginBad
SourceCtorState4086_BeginGuard_1:
.a16
.i16
 lda.l SourceFactors4086_Status
 cmp #2
 beq SourceCtorState4086_BeginGuard_2
 jmp SourceCtorState4086_BeginBad
SourceCtorState4086_BeginGuard_2:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceCtorState4086_BeginGuard_3
 jmp SourceCtorState4086_BeginBad
SourceCtorState4086_BeginGuard_3:
.a16
.i16
 asl a
 asl a
 tax
 lda.l $43B900,x
 cmp.l SourceScriptClone4086_Model
 beq SourceCtorState4086_BeginGuard_4
 jmp SourceCtorState4086_BeginBad
SourceCtorState4086_BeginGuard_4:
.a16
.i16
 lda.l $43B902,x
 cmp #$B5F1
 beq SourceCtorState4086_BeginGuard_5
 jmp SourceCtorState4086_BeginBad
SourceCtorState4086_BeginGuard_5:
.a16
.i16
 jsl SourceCtorState4086_Reset
 bcc SourceCtorState4086_BeginGuard_6
 jmp SourceCtorState4086_BeginBad
SourceCtorState4086_BeginGuard_6:
.a16
.i16
 jsl SourceCtorModel4086_Apply
 bcc SourceCtorState4086_BeginGuard_7
 jmp SourceCtorState4086_BeginBad
SourceCtorState4086_BeginGuard_7:
.a16
.i16
 ; Source spawn copies model knockdowncount after exists and model assignment.
 ; Bind no script and run no default callback until this fresh copy completes.
 lda.l SourceScriptClone4086_Slot
 jsl SourceDamageState4086_InitializeBirth
 bcc SourceCtorState4086_DamageStateBirthDone
 jmp SourceCtorState4086_BeginBad
SourceCtorState4086_DamageStateBirthDone:
.a16
.i16
 jsl SourceScriptClone4086_Bind
 bcc SourceCtorState4086_BeginGuard_8
 jmp SourceCtorState4086_BeginBad
SourceCtorState4086_BeginGuard_8:
.a16
.i16
 jsl SourceCtorState4086_Finish
 bcc SourceCtorState4086_BeginGuard_9
 jmp SourceCtorState4086_BeginBad
SourceCtorState4086_BeginGuard_9:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceCtorState4086_BeginBad:
.a16
.i16
 lda #3
 sta.l SourceCtorState4086_Status
 ply
 plx
 plp
 sec
 rtl
