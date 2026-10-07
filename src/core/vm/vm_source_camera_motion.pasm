; Generic admitted rightward horizontal camera, with optional SCROLL_BACK.
; Source-sized viewport is an input independent of the cropped SNES presentation.
; Compute into scratch and publish only after checked Q16 arithmetic completes.
; Q16 arithmetic/mean overflow or nonrepresentable half quantum rejects explicitly.
; Ready grants validated immutable source descriptor. A=1 moved, A=0 no roles; C=fault.
SourceCameraMotion4086_Ready = $43BBE8
SourceCameraMotion4086_Status = $43BBEA
SourceCameraMotion4086_Direction = $43BBEC
SourceCameraMotion4086_Width = $43BBEE
SourceCameraMotion4086_Height = $43BBF0
SourceCameraMotion4086_HRes = $43BBF2
SourceCameraMotion4086_VRes = $43BBF4
SourceCameraMotion4086_Rocking = $43BBF6
SourceCameraMotion4086_Speed = $43BBF8
SourceCameraMotion4086_OffsetX = $43BBFC
SourceCameraMotion4086_OffsetZ = $43BC00
SourceCameraMotion4086_MinX = $43BC04
SourceCameraMotion4086_MaxX = $43BC08
SourceCameraMotion4086_MinZ = $43BC0C
SourceCameraMotion4086_MaxZ = $43BC10
SourceCameraMotion4086_Blockade = $43BC14
SourceCameraMotion4086_To = $43BC18
SourceCameraMotion4086_OpA = $43BC1C
SourceCameraMotion4086_OpB = $43BC20
SourceCameraMotion4086_Result = $43BC24
SourceCameraMotion4086_Compare = $43BC28
SourceCameraMotion4086_X = $43BC2C
SourceCameraMotion4086_Y = $43BC30
SourceCameraMotion4086_TX = $43BC34
SourceCameraMotion4086_TY = $43BC38
SourceCameraMotion4086_Position = $43BC3C
SourceCameraMotion4086_EndFlag = $43BC40
SourceCameraMotion4086_DX = $43BC42
SourceCameraMotion4086_DY = $43BC46
SourceCameraMotion4086_End = $43BC4A
SourceCameraMotion4086_Move:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCameraMotion4086_Ready
 cmp #$B5DB
 beq SourceCameraMotion4086_Guard1
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard1:
.a16
.i16
 lda.l SourceCameraBounds4086_Ready
 cmp #$B5DA
 beq SourceCameraMotion4086_Guard2
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard2:
.a16
.i16
 lda.l SourceWait4086_Ready
 cmp #$B5D9
 beq SourceCameraMotion4086_Guard3
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard3:
.a16
.i16
 lda.l SourceScrollerPrefix4086_Ready
 cmp #$B5D7
 beq SourceCameraMotion4086_Guard4
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard4:
.a16
.i16
 lda.l SourceStageProducer4086_Ready
 cmp #$B5D6
 beq SourceCameraMotion4086_Guard5
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard5:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceCameraMotion4086_Guard6
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard6:
.a16
.i16
 lda.l SourceCameraBounds4086_Status
 cmp #2
 beq SourceCameraMotion4086_Guard7
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard7:
.a16
.i16
 lda.l SourceWait4086_Status
 cmp #2
 beq SourceCameraMotion4086_Guard8
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard8:
.a16
.i16
 lda.l SourceScrollerPrefix4086_State
 cmp #2
 beq SourceCameraMotion4086_Guard9
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard9:
.a16
.i16
 lda.l SourceStageProducer4086_State
 cmp #4
 beq SourceCameraMotion4086_Guard10
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard10:
.a16
.i16
 lda.l VmSourceWorld_ScrollAxis
 beq SourceCameraMotion4086_Guard11
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard11:
.a16
.i16
 lda.l SourceCameraMotion4086_Direction
 cmp #2
 beq SourceCameraMotion4086_DirectionOK
 cmp #3

 beq SourceCameraMotion4086_Guard12
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard12:
.a16
.i16
SourceCameraMotion4086_DirectionOK:
.a16
.i16
 lda.l SourceCameraMotion4086_Width
 bne SourceCameraMotion4086_Guard13
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard13:
.a16
.i16
 cmp #$8000
 bcc SourceCameraMotion4086_Guard14
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard14:
.a16
.i16
 lda.l SourceCameraMotion4086_Height
 bne SourceCameraMotion4086_Guard15
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard15:
.a16
.i16
 cmp #$8000
 bcc SourceCameraMotion4086_Guard16
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard16:
.a16
.i16
 lda.l SourceCameraMotion4086_HRes
 bne SourceCameraMotion4086_Guard17
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard17:
.a16
.i16
 cmp #$8000
 bcc SourceCameraMotion4086_Guard18
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard18:
.a16
.i16
 lda.l SourceCameraMotion4086_VRes
 bne SourceCameraMotion4086_Guard19
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard19:
.a16
.i16
 cmp #$8000
 bcc SourceCameraMotion4086_Guard20
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard20:
.a16
.i16
 lda.l SourceCameraMotion4086_Width
 cmp.l SourceCameraMotion4086_HRes
 bcs SourceCameraMotion4086_Guard21
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard21:
.a16
.i16
 lda.l SourceCameraMotion4086_Speed+2
 bpl SourceCameraMotion4086_Guard22
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard22:
.a16
.i16
 lda.l VmSourceWorld_AdvanceX
 sta.l SourceCameraMotion4086_X
 lda.l VmSourceWorld_AdvanceX+2
 sta.l SourceCameraMotion4086_X+2
 lda.l VmSourceWorld_AdvanceY
 sta.l SourceCameraMotion4086_Y
 lda.l VmSourceWorld_AdvanceY+2
 sta.l SourceCameraMotion4086_Y+2
 lda.l SourceCameraMotion4086_X
 sta.l SourceCameraMotion4086_TX
 lda.l SourceCameraMotion4086_X+2
 sta.l SourceCameraMotion4086_TX+2
 lda.l SourceCameraMotion4086_Y
 sta.l SourceCameraMotion4086_TY
 lda.l SourceCameraMotion4086_Y+2
 sta.l SourceCameraMotion4086_TY+2
 lda.l SourceStageProducer4086_Position
 sta.l SourceCameraMotion4086_Position
 lda.l SourceStageProducer4086_Position+2
 sta.l SourceCameraMotion4086_Position+2
 lda.l SourceCameraBounds4086_Count
 bne SourceCameraMotion4086_Branch23
 jmp SourceCameraMotion4086_NoRoles
SourceCameraMotion4086_Branch23:
.a16
.i16
 lda.l SourceStageProducer4086_Waiting
 beq SourceCameraMotion4086_Branch24
 jmp SourceCameraMotion4086_Depth
SourceCameraMotion4086_Branch24:
.a16
.i16
 lda #0
 sta.l SourceCameraMotion4086_EndFlag
 lda #0
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_HRes
 sta.l SourceCameraMotion4086_OpB+2
 lda #0
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_Width
 sta.l SourceCameraMotion4086_OpA+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard25
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard25:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_To
 ora.l SourceCameraMotion4086_To+2
 bne SourceCameraMotion4086_WidthLong
 lda #1
 sta.l SourceCameraMotion4086_EndFlag
SourceCameraMotion4086_WidthLong:
.a16
.i16
 lda.l SourceCameraBounds4086_RM
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraBounds4086_RM+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraBounds4086_LM
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraBounds4086_LM+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard26
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard26:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda #0
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_HRes
 sta.l SourceCameraMotion4086_OpB+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 jsr SourceCameraMotion4086_CompareSigned
 bcs SourceCameraMotion4086_Branch27
 jmp SourceCameraMotion4086_MeanX
SourceCameraMotion4086_Branch27:
.a16
.i16
 lda.l SourceCameraMotion4086_OpA
 cmp.l SourceCameraMotion4086_OpB
 bne SourceCameraMotion4086_HoldX
 lda.l SourceCameraMotion4086_OpA+2
 cmp.l SourceCameraMotion4086_OpB+2
 bne SourceCameraMotion4086_Branch28
 jmp SourceCameraMotion4086_MeanX
SourceCameraMotion4086_Branch28:
.a16
.i16
SourceCameraMotion4086_HoldX:
.a16
.i16
 lda.l SourceCameraMotion4086_X
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_X+2
 sta.l SourceCameraMotion4086_To+2
 jmp SourceCameraMotion4086_TargetX
SourceCameraMotion4086_MeanX:
.a16
.i16
 lda.l SourceCameraBounds4086_LM
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraBounds4086_LM+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraBounds4086_RM
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraBounds4086_RM+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Add

 bcc SourceCameraMotion4086_Guard29
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard29:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_To
 and #1
 beq SourceCameraMotion4086_Guard30
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard30:
.a16
.i16
 lda.l SourceCameraMotion4086_To+2
 cmp #$8000
 ror a
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_To
 ror a
 sta.l SourceCameraMotion4086_To
 lda #0
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_HRes
 lsr a
 sta.l SourceCameraMotion4086_OpB+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard31
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard31:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_OffsetX
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_OffsetX+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Add

 bcc SourceCameraMotion4086_Guard32
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard32:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_TargetX:
.a16
.i16
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_MinX
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_MinX+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcs SourceCameraMotion4086_MinKeep33
 lda.l SourceCameraMotion4086_MinX
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_MinX+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_MinKeep33:
.a16
.i16
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_MaxX
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_MaxX+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcc SourceCameraMotion4086_MaxKeep34
 lda.l SourceCameraMotion4086_MaxX
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_MaxX+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_MaxKeep34:
.a16
.i16
 lda.l SourceCameraMotion4086_Direction
 and #1
 beq SourceCameraMotion4086_ForwardTarget
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_Blockade
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_Blockade+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcs SourceCameraMotion4086_MinKeep35
 lda.l SourceCameraMotion4086_Blockade
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Blockade+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_MinKeep35:
.a16
.i16
SourceCameraMotion4086_ForwardTarget:
.a16
.i16
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_X
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_X+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcs SourceCameraMotion4086_Branch36
 jmp SourceCameraMotion4086_BackwardX
SourceCameraMotion4086_Branch36:
.a16
.i16
 lda.l SourceCameraMotion4086_X
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_X+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_Speed
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_Speed+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Add

 bcc SourceCameraMotion4086_Guard37
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard37:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_Result
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_Result+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcc SourceCameraMotion4086_MaxKeep38
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_MaxKeep38:
.a16
.i16
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_X
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_X+2
 jmp SourceCameraMotion4086_ClampX
SourceCameraMotion4086_BackwardX:
.a16
.i16
 lda.l SourceCameraMotion4086_Direction
 and #1
 bne SourceCameraMotion4086_Branch39
 jmp SourceCameraMotion4086_ClampX
SourceCameraMotion4086_Branch39:
.a16
.i16
 lda.l SourceCameraMotion4086_X
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_X+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_Speed
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_Speed+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard40
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard40:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_Result
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_Result+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcs SourceCameraMotion4086_MinKeep41
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_MinKeep41:
.a16
.i16
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_X
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_X+2
SourceCameraMotion4086_ClampX:
.a16
.i16
 lda.l SourceCameraMotion4086_X+2
 bpl SourceCameraMotion4086_XNonnegative
 lda #0
 sta.l SourceCameraMotion4086_X
 sta.l SourceCameraMotion4086_X+2
SourceCameraMotion4086_XNonnegative:
.a16
.i16
 lda #0
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_Width
 sta.l SourceCameraMotion4086_OpA+2
 lda #0
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_HRes
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard42
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard42:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_X
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_X+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcc SourceCameraMotion4086_XBeforeEnd
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_X
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_X+2
 lda #1
 sta.l SourceCameraMotion4086_EndFlag
SourceCameraMotion4086_XBeforeEnd:
.a16
.i16
 lda.l SourceCameraMotion4086_EndFlag
 beq SourceCameraMotion4086_PositionFromX
 lda.l SourceCameraMotion4086_Position
 clc
 adc #1
 sta.l SourceCameraMotion4086_Position
 lda.l SourceCameraMotion4086_Position+2
 adc #0

 bvc SourceCameraMotion4086_Guard43
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard43:
.a16
.i16
 sta.l SourceCameraMotion4086_Position+2
 jmp SourceCameraMotion4086_Depth
SourceCameraMotion4086_PositionFromX:
.a16
.i16
 lda.l SourceCameraMotion4086_X+2
 sta.l SourceCameraMotion4086_Position
 lda #0
 sta.l SourceCameraMotion4086_Position+2
SourceCameraMotion4086_Depth:
.a16
.i16
 lda.l SourceCameraBounds4086_BM
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraBounds4086_BM+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraBounds4086_TM
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraBounds4086_TM+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard44
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard44:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda #0
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_VRes
 sta.l SourceCameraMotion4086_OpB+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 jsr SourceCameraMotion4086_CompareSigned
 bcs SourceCameraMotion4086_Branch45
 jmp SourceCameraMotion4086_MeanY
SourceCameraMotion4086_Branch45:
.a16
.i16
 lda.l SourceCameraMotion4086_OpA
 cmp.l SourceCameraMotion4086_OpB
 bne SourceCameraMotion4086_HoldY
 lda.l SourceCameraMotion4086_OpA+2
 cmp.l SourceCameraMotion4086_OpB+2
 bne SourceCameraMotion4086_Branch46
 jmp SourceCameraMotion4086_MeanY
SourceCameraMotion4086_Branch46:
.a16
.i16
SourceCameraMotion4086_HoldY:
.a16
.i16
 lda.l SourceCameraMotion4086_Y
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Y+2
 sta.l SourceCameraMotion4086_To+2
 jmp SourceCameraMotion4086_TargetY
SourceCameraMotion4086_MeanY:
.a16
.i16
 lda.l SourceCameraBounds4086_BM
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraBounds4086_BM+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraBounds4086_TM
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraBounds4086_TM+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Add

 bcc SourceCameraMotion4086_Guard47
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard47:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_To
 and #1
 beq SourceCameraMotion4086_Guard48
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard48:
.a16
.i16
 lda.l SourceCameraMotion4086_To+2
 cmp #$8000
 ror a
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_To
 ror a
 sta.l SourceCameraMotion4086_To
 lda #0
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_VRes
 lsr a
 sta.l SourceCameraMotion4086_OpB+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard49
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard49:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_OffsetZ
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_OffsetZ+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Add

 bcc SourceCameraMotion4086_Guard50
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard50:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_TargetY:
.a16
.i16
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_MaxZ
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_MaxZ+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcc SourceCameraMotion4086_MaxKeep51
 lda.l SourceCameraMotion4086_MaxZ
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_MaxZ+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_MaxKeep51:
.a16
.i16
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_MinZ
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_MinZ+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcs SourceCameraMotion4086_MinKeep52
 lda.l SourceCameraMotion4086_MinZ
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_MinZ+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_MinKeep52:
.a16
.i16
 lda.l SourceCameraMotion4086_Y
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_Y+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_Speed
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_Speed+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Add

 bcc SourceCameraMotion4086_Guard53
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard53:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_Result
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_Result+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcc SourceCameraMotion4086_MaxKeep54
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_MaxKeep54:
.a16
.i16
 lda.l SourceCameraMotion4086_Y
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_Y+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_Speed
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_Speed+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard55
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard55:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_Result
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_Result+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcs SourceCameraMotion4086_MinKeep56
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
SourceCameraMotion4086_MinKeep56:
.a16
.i16
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_Y
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_Y+2
 lda #0
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_Height
 sta.l SourceCameraMotion4086_OpA+2
 lda #0
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_VRes
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard57
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard57:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda #0
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_Rocking
 bne SourceCameraMotion4086_RockingInset
 lda #12
 bra SourceCameraMotion4086_DepthInset
SourceCameraMotion4086_RockingInset:
.a16
.i16
 lda #16
SourceCameraMotion4086_DepthInset:
.a16
.i16
 sta.l SourceCameraMotion4086_OpB+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpA+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard58
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard58:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_Y
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_Y+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_CompareSigned
 bcc SourceCameraMotion4086_MaxKeep59
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_Y
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_Y+2
SourceCameraMotion4086_MaxKeep59:
.a16
.i16
 lda.l SourceCameraMotion4086_Y+2
 bpl SourceCameraMotion4086_YNonnegative
 lda #0
 sta.l SourceCameraMotion4086_Y
 sta.l SourceCameraMotion4086_Y+2
SourceCameraMotion4086_YNonnegative:
.a16
.i16
 lda.l SourceCameraMotion4086_X
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_X+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_TX
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_TX+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard60
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard60:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_DX
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_DX+2
 lda.l SourceCameraMotion4086_Y
 sta.l SourceCameraMotion4086_OpA
 lda.l SourceCameraMotion4086_Y+2
 sta.l SourceCameraMotion4086_OpA+2
 lda.l SourceCameraMotion4086_TY
 sta.l SourceCameraMotion4086_OpB
 lda.l SourceCameraMotion4086_TY+2
 sta.l SourceCameraMotion4086_OpB+2
 jsr SourceCameraMotion4086_Subtract

 bcc SourceCameraMotion4086_Guard61
 jmp SourceCameraMotion4086_Bad
SourceCameraMotion4086_Guard61:
.a16
.i16
 lda.l SourceCameraMotion4086_Result
 sta.l SourceCameraMotion4086_To
 lda.l SourceCameraMotion4086_Result+2
 sta.l SourceCameraMotion4086_To+2
 lda.l SourceCameraMotion4086_To
 sta.l SourceCameraMotion4086_DY
 lda.l SourceCameraMotion4086_To+2
 sta.l SourceCameraMotion4086_DY+2
 lda.l SourceCameraMotion4086_DX
 sta.l SourceScrollerPrefix4086_ScrollDX
 lda.l SourceCameraMotion4086_DX+2
 sta.l SourceScrollerPrefix4086_ScrollDX+2
 lda.l SourceCameraMotion4086_DY
 sta.l SourceScrollerPrefix4086_ScrollDY
 lda.l SourceCameraMotion4086_DY+2
 sta.l SourceScrollerPrefix4086_ScrollDY+2
 lda.l SourceCameraMotion4086_X
 sta.l VmSourceWorld_AdvanceX
 lda.l SourceCameraMotion4086_X+2
 sta.l VmSourceWorld_AdvanceX+2
 lda.l SourceCameraMotion4086_Y
 sta.l VmSourceWorld_AdvanceY
 lda.l SourceCameraMotion4086_Y+2
 sta.l VmSourceWorld_AdvanceY+2
 lda.l SourceCameraMotion4086_Position
 sta.l SourceStageProducer4086_Position
 lda.l SourceCameraMotion4086_Position+2
 sta.l SourceStageProducer4086_Position+2
 lda #1
 beq SourceCameraMotion4086_Branch62
 jmp SourceCameraMotion4086_Done
SourceCameraMotion4086_Branch62:
.a16
.i16
SourceCameraMotion4086_NoRoles:
.a16
.i16
 lda #0
SourceCameraMotion4086_Done:
.a16
.i16
 pha
 lda #2
 sta.l SourceCameraMotion4086_Status
 pla
 ply
 plx
 plp
 clc
 rtl
SourceCameraMotion4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCameraMotion4086_Status
 sta.l SourceStageProducer4086_State
 ply
 plx
 plp
 sec
 rtl
SourceCameraMotion4086_Add:
.a16
.i16
 lda.l SourceCameraMotion4086_OpA
 clc
 adc.l SourceCameraMotion4086_OpB
 sta.l SourceCameraMotion4086_Result
 lda.l SourceCameraMotion4086_OpA+2
 adc.l SourceCameraMotion4086_OpB+2
 bvs SourceCameraMotion4086_ArithmeticBad
 sta.l SourceCameraMotion4086_Result+2
 clc
 rts
SourceCameraMotion4086_Subtract:
.a16
.i16
 lda.l SourceCameraMotion4086_OpA
 sec
 sbc.l SourceCameraMotion4086_OpB
 sta.l SourceCameraMotion4086_Result
 lda.l SourceCameraMotion4086_OpA+2
 sbc.l SourceCameraMotion4086_OpB+2
 bvs SourceCameraMotion4086_ArithmeticBad
 sta.l SourceCameraMotion4086_Result+2
 clc
 rts
SourceCameraMotion4086_ArithmeticBad:
.a16
.i16
 sec
 rts
SourceCameraMotion4086_CompareSigned:
.a16
.i16
 lda.l SourceCameraMotion4086_OpB+2
 eor #$8000
 sta.l SourceCameraMotion4086_Compare
 lda.l SourceCameraMotion4086_OpA+2
 eor #$8000
 cmp.l SourceCameraMotion4086_Compare
 bne SourceCameraMotion4086_CompareDone
 lda.l SourceCameraMotion4086_OpA
 cmp.l SourceCameraMotion4086_OpB
SourceCameraMotion4086_CompareDone:
.a16
.i16
 rts
