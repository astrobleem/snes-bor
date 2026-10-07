; Camera role bounds in the admitted Q16 coordinate domain.
; Source role pointers alone determine participation, independent of exists/dead/type.
; Maxplayers 1..4 and cameratype 0/1. Altitude subtraction faults on Q16 overflow.
SourceCameraBounds4086_Ready = $43BBC2
SourceCameraBounds4086_Status = $43BBC4
SourceCameraBounds4086_MaxPlayers = $43BBC6
SourceCameraBounds4086_CameraType = $43BBC8
SourceCameraBounds4086_Count = $43BBCA
SourceCameraBounds4086_RM = $43BBCC
SourceCameraBounds4086_LM = $43BBD0
SourceCameraBounds4086_BM = $43BBD4
SourceCameraBounds4086_TM = $43BBD8
SourceCameraBounds4086_Cursor = $43BBDC
SourceCameraBounds4086_Low = $43BBDE
SourceCameraBounds4086_View = $43BBE0
SourceCameraBounds4086_Value = $43BBE2
SourceCameraBounds4086_Compare = $43BBE6
SourceCameraBounds4086_End = $43BBE8
SourceCameraBounds4086_Collect:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCameraBounds4086_Ready
 cmp #$B5DA
 beq SourceCameraBounds4086_G1
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G1:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceCameraBounds4086_G2
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G2:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceCameraBounds4086_G3
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G3:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceCameraBounds4086_G4
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G4:
.a16
.i16
 cmp #129
 bcc SourceCameraBounds4086_G5
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G5:
.a16
.i16
 lda.l SourceCameraBounds4086_MaxPlayers
 bne SourceCameraBounds4086_G6
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G6:
.a16
.i16
 cmp #5
 bcc SourceCameraBounds4086_G7
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G7:
.a16
.i16
 lda.l SourceCameraBounds4086_CameraType
 cmp #2
 bcc SourceCameraBounds4086_G8
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G8:
.a16
.i16
 lda #0
 sta.l SourceCameraBounds4086_Count
 sta.l SourceCameraBounds4086_Cursor
 sta.l SourceCameraBounds4086_RM
 sta.l SourceCameraBounds4086_BM
 lda #$D8F1
 sta.l SourceCameraBounds4086_RM+2
 sta.l SourceCameraBounds4086_BM+2
 lda #$FFFF
 sta.l SourceCameraBounds4086_LM
 sta.l SourceCameraBounds4086_TM
 lda #$7FFF
 sta.l SourceCameraBounds4086_LM+2
 sta.l SourceCameraBounds4086_TM+2
SourceCameraBounds4086_RoleLoop:
.a16
.i16
 lda.l SourceCameraBounds4086_Cursor
 asl a
 asl a
 tax
 lda.l $43FD84,x
 sta.l SourceCameraBounds4086_Low
 ora.l $43FD86,x
 bne SourceCameraBounds4086_NonNull
 jmp SourceCameraBounds4086_NextRole
SourceCameraBounds4086_NonNull:
.a16
.i16
 lda.l $43FD86,x
 cmp #$41
 beq SourceCameraBounds4086_G9
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G9:
.a16
.i16
 lda.l SourceCameraBounds4086_Low
 cmp #$4000
 bcs SourceCameraBounds4086_G10
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G10:
.a16
.i16
 cmp #$6800
 bcc SourceCameraBounds4086_G11
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G11:
.a16
.i16
 sec
 sbc #$4000
 sta.l SourceCameraBounds4086_View
 ldx #0
SourceCameraBounds4086_Divide:
.a16
.i16
 cmp #80
 bcc SourceCameraBounds4086_Remainder
 sec
 sbc #80
 inx
 bra SourceCameraBounds4086_Divide
SourceCameraBounds4086_Remainder:
.a16
.i16
 ora #0
 beq SourceCameraBounds4086_G12
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G12:
.a16
.i16
 txa
 cmp.l VmSourceWorld_Count
 bcc SourceCameraBounds4086_G13
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G13:
.a16
.i16
 lda.l SourceCameraBounds4086_View
 tax
 lda.l $414000,x
 cmp.l SourceCameraBounds4086_Low
 beq SourceCameraBounds4086_G14
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G14:
.a16
.i16
 lda.l $414002,x
 cmp #$41
 beq SourceCameraBounds4086_G15
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G15:
.a16
.i16
 lda.l $414030,x
 cmp #2
 beq SourceCameraBounds4086_G16
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G16:
.a16
.i16
 lda.l $414038,x
 cmp #2
 beq SourceCameraBounds4086_G17
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G17:
.a16
.i16
 lda.l SourceCameraBounds4086_Count
 inc a
 sta.l SourceCameraBounds4086_Count
 lda.l $414034,x
 sta.l SourceCameraBounds4086_Value
 lda.l $414036,x
 sta.l SourceCameraBounds4086_Value+2
 lda.l SourceCameraBounds4086_RM+2
 eor #$8000
 sta.l SourceCameraBounds4086_Compare
 lda.l SourceCameraBounds4086_Value+2
 eor #$8000
 cmp.l SourceCameraBounds4086_Compare
 bcc SourceCameraBounds4086_RMKeep
 bne SourceCameraBounds4086_RMUpdate
 lda.l SourceCameraBounds4086_Value
 cmp.l SourceCameraBounds4086_RM
 bcc SourceCameraBounds4086_RMKeep
SourceCameraBounds4086_RMUpdate:
.a16
.i16
 lda.l SourceCameraBounds4086_Value
 sta.l SourceCameraBounds4086_RM
 lda.l SourceCameraBounds4086_Value+2
 sta.l SourceCameraBounds4086_RM+2
SourceCameraBounds4086_RMKeep:
.a16
.i16
 lda.l SourceCameraBounds4086_LM+2
 eor #$8000
 sta.l SourceCameraBounds4086_Compare
 lda.l SourceCameraBounds4086_Value+2
 eor #$8000
 cmp.l SourceCameraBounds4086_Compare
 bcc SourceCameraBounds4086_LMUpdate
 bne SourceCameraBounds4086_LMKeep
 lda.l SourceCameraBounds4086_Value
 cmp.l SourceCameraBounds4086_LM
 bcs SourceCameraBounds4086_LMKeep
SourceCameraBounds4086_LMUpdate:
.a16
.i16
 lda.l SourceCameraBounds4086_Value
 sta.l SourceCameraBounds4086_LM
 lda.l SourceCameraBounds4086_Value+2
 sta.l SourceCameraBounds4086_LM+2
SourceCameraBounds4086_LMKeep:
.a16
.i16
 lda.l $41403C,x
 sta.l SourceCameraBounds4086_Value
 lda.l $41403E,x
 sta.l SourceCameraBounds4086_Value+2
 lda.l SourceCameraBounds4086_CameraType
 beq SourceCameraBounds4086_DepthReady
 lda.l $414008,x
 cmp #2
 beq SourceCameraBounds4086_G18
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G18:
.a16
.i16
 lda.l SourceCameraBounds4086_Value
 sec
 sbc.l $41400C,x
 sta.l SourceCameraBounds4086_Value
 lda.l SourceCameraBounds4086_Value+2
 sbc.l $41400E,x

 bvc SourceCameraBounds4086_G19
 jmp SourceCameraBounds4086_Bad
SourceCameraBounds4086_G19:
.a16
.i16
 sta.l SourceCameraBounds4086_Value+2
SourceCameraBounds4086_DepthReady:
.a16
.i16
 lda.l SourceCameraBounds4086_BM+2
 eor #$8000
 sta.l SourceCameraBounds4086_Compare
 lda.l SourceCameraBounds4086_Value+2
 eor #$8000
 cmp.l SourceCameraBounds4086_Compare
 bcc SourceCameraBounds4086_BMKeep
 bne SourceCameraBounds4086_BMUpdate
 lda.l SourceCameraBounds4086_Value
 cmp.l SourceCameraBounds4086_BM
 bcc SourceCameraBounds4086_BMKeep
SourceCameraBounds4086_BMUpdate:
.a16
.i16
 lda.l SourceCameraBounds4086_Value
 sta.l SourceCameraBounds4086_BM
 lda.l SourceCameraBounds4086_Value+2
 sta.l SourceCameraBounds4086_BM+2
SourceCameraBounds4086_BMKeep:
.a16
.i16
 lda.l SourceCameraBounds4086_TM+2
 eor #$8000
 sta.l SourceCameraBounds4086_Compare
 lda.l SourceCameraBounds4086_Value+2
 eor #$8000
 cmp.l SourceCameraBounds4086_Compare
 bcc SourceCameraBounds4086_TMUpdate
 bne SourceCameraBounds4086_TMKeep
 lda.l SourceCameraBounds4086_Value
 cmp.l SourceCameraBounds4086_TM
 bcs SourceCameraBounds4086_TMKeep
SourceCameraBounds4086_TMUpdate:
.a16
.i16
 lda.l SourceCameraBounds4086_Value
 sta.l SourceCameraBounds4086_TM
 lda.l SourceCameraBounds4086_Value+2
 sta.l SourceCameraBounds4086_TM+2
SourceCameraBounds4086_TMKeep:
.a16
.i16
SourceCameraBounds4086_NextRole:
.a16
.i16
 lda.l SourceCameraBounds4086_Cursor
 inc a
 sta.l SourceCameraBounds4086_Cursor
 cmp.l SourceCameraBounds4086_MaxPlayers
 bcs SourceCameraBounds4086_Done
 jmp SourceCameraBounds4086_RoleLoop
SourceCameraBounds4086_Done:
.a16
.i16
 lda #2
 sta.l SourceCameraBounds4086_Status
 lda.l SourceCameraBounds4086_Count
 ply
 plx
 plp
 clc
 rtl
SourceCameraBounds4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCameraBounds4086_Status
 ply
 plx
 plp
 sec
 rtl
