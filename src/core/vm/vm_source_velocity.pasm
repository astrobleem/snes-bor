; Generic source velocity accumulator: full signed 64-bit product / 2^17.
; ACCEPTED_COMPAT_Q16_16. Checked two-axis publication; no position integration.
; Requires outstanding source world tick Pending=1, Phase=10. Does not acknowledge it.
SourceVelocity4086_Ready = $43BC52
SourceVelocity4086_Status = $43BC54
SourceVelocity4086_Aux = $43BC56
SourceVelocity4086_Side = $43BC58
SourceVelocity4086_Sign = $43BC5A
SourceVelocity4086_Axis = $43BC5C
SourceVelocity4086_Left = $43BC5E
SourceVelocity4086_Right = $43BC66
SourceVelocity4086_Product = $43BC6A
SourceVelocity4086_ResultX = $43BC72
SourceVelocity4086_ResultZ = $43BC76
SourceVelocity4086_Accum = $43BC7A
SourceVelocity4086_ScratchEnd = $43BC7E
SourceVelocity4086_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceVelocity4086_Ready
 cmp #$B5DE
 beq SourceVelocity4086_Guard1
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard1:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceVelocity4086_Guard2
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceVelocity4086_Guard3
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard3:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #10
 beq SourceVelocity4086_Guard4
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard4:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceVelocity4086_PendingOk
 jmp SourceVelocity4086_Bad
SourceVelocity4086_PendingOk:
.a16
.i16
 lda.l SourceVelocity4086_Status
 beq SourceVelocity4086_StatusOk
 jmp SourceVelocity4086_Bad
SourceVelocity4086_StatusOk:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 beq SourceVelocity4086_Guard5
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard5:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceVelocity4086_Guard6
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard6:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceVelocity4086_Guard7
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard7:
.a16
.i16
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceVelocity4086_Guard8
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard8:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceVelocity4086_Guard9
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard9:
.a16
.i16
 cmp #129
 bcc SourceVelocity4086_Guard10
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard10:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceVelocity4086_Guard11
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard11:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceVelocity4086_Side
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 sta.l SourceVelocity4086_Aux
 asl a
 asl a
 clc
 adc.l SourceVelocity4086_Aux
 sta.l SourceVelocity4086_Aux
 lda #0
 sta.l SourceVelocity4086_Axis
SourceVelocity4086_AxisLoop:
.a16
.i16
 lda.l SourceVelocity4086_Side
 clc
 adc.l SourceVelocity4086_Axis
 tax
 lda.l SOURCE_WORLD_SIDES+36,x
 sta.l SourceVelocity4086_Left
 lda.l SOURCE_WORLD_SIDES+38,x
 sta.l SourceVelocity4086_Left+2
 lda.l SourceVelocity4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+32,x
 sta.l SourceVelocity4086_Right
 lda.l SOURCE_WORLD_SIDES+34,x
 sta.l SourceVelocity4086_Right+2
 lda #0
 sta.l SourceVelocity4086_Sign
 lda.l SourceVelocity4086_Left+2
 bpl SourceVelocity4086_Positive12
 lda.l SourceVelocity4086_Sign
 eor #1
 sta.l SourceVelocity4086_Sign
 sec
 lda #0
 sbc.l SourceVelocity4086_Left
 sta.l SourceVelocity4086_Left
 lda #0
 sbc.l SourceVelocity4086_Left+2
 sta.l SourceVelocity4086_Left+2
SourceVelocity4086_Positive12:
.a16
.i16
 lda.l SourceVelocity4086_Right+2
 bpl SourceVelocity4086_Positive13
 lda.l SourceVelocity4086_Sign
 eor #1
 sta.l SourceVelocity4086_Sign
 sec
 lda #0
 sbc.l SourceVelocity4086_Right
 sta.l SourceVelocity4086_Right
 lda #0
 sbc.l SourceVelocity4086_Right+2
 sta.l SourceVelocity4086_Right+2
SourceVelocity4086_Positive13:
.a16
.i16
 lda #0
 sta.l SourceVelocity4086_Left+4
 sta.l SourceVelocity4086_Left+6
 sta.l SourceVelocity4086_Product
 sta.l SourceVelocity4086_Product+2
 sta.l SourceVelocity4086_Product+4
 sta.l SourceVelocity4086_Product+6
 ldy #32
SourceVelocity4086_Multiply:
.a16
.i16
 lda.l SourceVelocity4086_Right+2
 lsr a
 sta.l SourceVelocity4086_Right+2
 lda.l SourceVelocity4086_Right
 ror a
 sta.l SourceVelocity4086_Right
 bcc SourceVelocity4086_NoAdd
 clc
 lda.l SourceVelocity4086_Product
 adc.l SourceVelocity4086_Left
 sta.l SourceVelocity4086_Product
 lda.l SourceVelocity4086_Product+2
 adc.l SourceVelocity4086_Left+2
 sta.l SourceVelocity4086_Product+2
 lda.l SourceVelocity4086_Product+4
 adc.l SourceVelocity4086_Left+4
 sta.l SourceVelocity4086_Product+4
 lda.l SourceVelocity4086_Product+6
 adc.l SourceVelocity4086_Left+6
 sta.l SourceVelocity4086_Product+6
SourceVelocity4086_NoAdd:
.a16
.i16
 lda.l SourceVelocity4086_Left
 asl a
 sta.l SourceVelocity4086_Left
 lda.l SourceVelocity4086_Left+2
 rol a
 sta.l SourceVelocity4086_Left+2
 lda.l SourceVelocity4086_Left+4
 rol a
 sta.l SourceVelocity4086_Left+4
 lda.l SourceVelocity4086_Left+6
 rol a
 sta.l SourceVelocity4086_Left+6
 dey
 bne SourceVelocity4086_Multiply
 ldy #17
SourceVelocity4086_Scale:
.a16
.i16
 lda.l SourceVelocity4086_Product+6
 lsr a
 sta.l SourceVelocity4086_Product+6
 lda.l SourceVelocity4086_Product+4
 ror a
 sta.l SourceVelocity4086_Product+4
 lda.l SourceVelocity4086_Product+2
 ror a
 sta.l SourceVelocity4086_Product+2
 lda.l SourceVelocity4086_Product
 ror a
 sta.l SourceVelocity4086_Product
 dey
 bne SourceVelocity4086_Scale
 lda.l SourceVelocity4086_Sign
 beq SourceVelocity4086_Signed
 sec
 lda #0
 sbc.l SourceVelocity4086_Product
 sta.l SourceVelocity4086_Product
 lda #0
 sbc.l SourceVelocity4086_Product+2
 sta.l SourceVelocity4086_Product+2
 lda #0
 sbc.l SourceVelocity4086_Product+4
 sta.l SourceVelocity4086_Product+4
 lda #0
 sbc.l SourceVelocity4086_Product+6
 sta.l SourceVelocity4086_Product+6
SourceVelocity4086_Signed:
.a16
.i16
 lda.l SourceVelocity4086_Aux
 clc
 adc.l SourceVelocity4086_Axis
 tax
 lda.l SOURCE_UPDATE_FRAME_AUX,x
 sta.l SourceVelocity4086_Accum
 lda.l SOURCE_UPDATE_FRAME_AUX+2,x
 sta.l SourceVelocity4086_Accum+2
 clc
 lda.l SourceVelocity4086_Product
 adc.l SourceVelocity4086_Accum
 sta.l SourceVelocity4086_Product
 lda.l SourceVelocity4086_Product+2
 adc.l SourceVelocity4086_Accum+2
 sta.l SourceVelocity4086_Product+2
 lda.l SourceVelocity4086_Accum+2
 bmi SourceVelocity4086_NegAccum
 lda #0
 bra SourceVelocity4086_Extend
SourceVelocity4086_NegAccum:
.a16
.i16
 lda #$FFFF
SourceVelocity4086_Extend:
.a16
.i16
 pha
 adc.l SourceVelocity4086_Product+4
 sta.l SourceVelocity4086_Product+4
 pla
 adc.l SourceVelocity4086_Product+6
 sta.l SourceVelocity4086_Product+6
 lda.l SourceVelocity4086_Product+2
 bmi SourceVelocity4086_NegResult
 lda #0
 bra SourceVelocity4086_CheckUpper
SourceVelocity4086_NegResult:
.a16
.i16
 lda #$FFFF
SourceVelocity4086_CheckUpper:
.a16
.i16
 cmp.l SourceVelocity4086_Product+4
 beq SourceVelocity4086_Guard14
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard14:
.a16
.i16
 cmp.l SourceVelocity4086_Product+6
 beq SourceVelocity4086_Guard15
 jmp SourceVelocity4086_Bad
SourceVelocity4086_Guard15:
.a16
.i16
 lda.l SourceVelocity4086_Axis
 tax
 lda.l SourceVelocity4086_Product
 sta.l SourceVelocity4086_ResultX,x
 lda.l SourceVelocity4086_Product+2
 sta.l SourceVelocity4086_ResultX+2,x
 lda.l SourceVelocity4086_Axis
 bne SourceVelocity4086_Publish
 lda #4
 sta.l SourceVelocity4086_Axis
 jmp SourceVelocity4086_AxisLoop
SourceVelocity4086_Publish:
.a16
.i16
 lda.l SourceVelocity4086_Aux
 tax
 lda.l SourceVelocity4086_ResultX
 sta.l SOURCE_UPDATE_FRAME_AUX,x
 lda.l SourceVelocity4086_ResultX+2
 sta.l SOURCE_UPDATE_FRAME_AUX+2,x
 lda.l SourceVelocity4086_ResultX+4
 sta.l SOURCE_UPDATE_FRAME_AUX+4,x
 lda.l SourceVelocity4086_ResultX+6
 sta.l SOURCE_UPDATE_FRAME_AUX+6,x
 lda #2
 sta.l SourceVelocity4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceVelocity4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceVelocity4086_Status
 ply
 plx
 plp
 sec
 rtl

; Literal arrange_ents tail: clear movex and movez after post-update.
SourceVelocity4086_Clear:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceVelocity4086_Ready
 cmp #$B5DE
 beq SourceVelocity4086_ClearGuard0
 jmp SourceVelocity4086_Bad
SourceVelocity4086_ClearGuard0:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceVelocity4086_ClearGuard1
 jmp SourceVelocity4086_Bad
SourceVelocity4086_ClearGuard1:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceVelocity4086_ClearGuard2
 jmp SourceVelocity4086_Bad
SourceVelocity4086_ClearGuard2:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #12
 beq SourceVelocity4086_ClearGuard3
 jmp SourceVelocity4086_Bad
SourceVelocity4086_ClearGuard3:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceVelocity4086_ClearGuard4
 jmp SourceVelocity4086_Bad
SourceVelocity4086_ClearGuard4:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #3
 beq SourceVelocity4086_ClearGuard5
 jmp SourceVelocity4086_Bad
SourceVelocity4086_ClearGuard5:
.a16
.i16
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceVelocity4086_ClearGuard6
 jmp SourceVelocity4086_Bad
SourceVelocity4086_ClearGuard6:
.a16
.i16
 lda.l SourceVelocity4086_Status
 beq SourceVelocity4086_ClearFresh
 jmp SourceVelocity4086_Bad
SourceVelocity4086_ClearFresh:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne SourceVelocity4086_ClearBad
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 bne SourceVelocity4086_ClearBad
 lda.l VmSourceWorld_Count
 beq SourceVelocity4086_ClearBad
 cmp #129
 bcs SourceVelocity4086_ClearBad
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcs SourceVelocity4086_ClearBad
 asl a
 asl a
 sta.l SourceVelocity4086_Aux
 asl a
 asl a
 clc
 adc.l SourceVelocity4086_Aux
 tax
 lda #0
 sta.l SOURCE_UPDATE_FRAME_AUX,x
 sta.l SOURCE_UPDATE_FRAME_AUX+2,x
 sta.l SOURCE_UPDATE_FRAME_AUX+4,x
 sta.l SOURCE_UPDATE_FRAME_AUX+6,x
 lda #2
 sta.l SourceVelocity4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceVelocity4086_ClearBad:
.a16
.i16
 jmp SourceVelocity4086_Bad
