; Source check_lost decision backend. Death/damage requests remain explicit.
; B5E0 context contains source offscreenkill/default/direction/viewport.
; Uses signed 64-bit Q16 intermediates for source coordinate comparisons.
; Scalar positions remain explicit ACCEPTED_COMPAT Q16.16; INTEGER Z=100000
; preserves the source parked-weapon sentinel. No death/damage execution here.
; Status 1 requires an actual death/damage backend; 2 is complete,3 fault.
SourceLost4086_Ready = $43BC90
SourceLost4086_Status = $43BC92
SourceLost4086_Request = $43BC94
SourceLost4086_OffscreenKill = $43BC96
SourceLost4086_DefaultOffscreenKill = $43BC9A
SourceLost4086_Direction = $43BC9E
SourceLost4086_HRes = $43BCA2
SourceLost4086_VRes = $43BCA4
SourceLost4086_View = $43BCA6
SourceLost4086_Side = $43BCA8
SourceLost4086_Life = $43BCAA
SourceLost4086_Core = $43BCAC
SourceLost4086_X = $43BCAE
SourceLost4086_Z = $43BCB2
SourceLost4086_Y = $43BCB6
SourceLost4086_AX = $43BCBA
SourceLost4086_AY = $43BCBE
SourceLost4086_Osk = $43BCC2
SourceLost4086_OpA = $43BCCA
SourceLost4086_OpB = $43BCD2
SourceLost4086_Result = $43BCDA
SourceLost4086_Compare = $43BCE2
SourceLost4086_Vertical = $43BCE4
SourceLost4086_Parked = $43BCE6
SourceLost4086_Countdown = $43BCE8
SourceLost4086_Force = $43BCEC
SourceLost4086_AttackType = $43BCF0
SourceLost4086_Damage = $43BCF2
SourceLost4086_ScratchEnd = $43BCF6
SourceLost4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceLost4086_Ready
 cmp #$B5E0
 bne SourceLost4086_Far1
 jmp SourceLost4086_Guard1
SourceLost4086_Far1:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard1:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 bne SourceLost4086_Far2
 jmp SourceLost4086_Guard2
SourceLost4086_Far2:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard2:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 bne SourceLost4086_Far3
 jmp SourceLost4086_Guard3
SourceLost4086_Far3:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard3:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 bne SourceLost4086_Far4
 jmp SourceLost4086_Guard4
SourceLost4086_Far4:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard4:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #2
 bne SourceLost4086_Far5
 jmp SourceLost4086_Guard5
SourceLost4086_Far5:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard5:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceLost4086_Far6
 jmp SourceLost4086_Guard6
SourceLost4086_Far6:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard6:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne SourceLost4086_Far7
 jmp SourceLost4086_Guard7
SourceLost4086_Far7:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard7:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 bne SourceLost4086_Far8
 jmp SourceLost4086_Guard8
SourceLost4086_Far8:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard8:
.a16
.i16
 lda.l VmSourceWorld_Level
 cmp #1
 bne SourceLost4086_Far9
 jmp SourceLost4086_Guard9
SourceLost4086_Far9:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard9:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 bne SourceLost4086_Far10
 jmp SourceLost4086_Guard10
SourceLost4086_Far10:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard10:
.a16
.i16
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 bne SourceLost4086_Far11
 jmp SourceLost4086_Guard11
SourceLost4086_Far11:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard11:
.a16
.i16
 lda.l SourceLost4086_Status
 bne SourceLost4086_Far12
 jmp SourceLost4086_Guard12
SourceLost4086_Far12:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard12:
.a16
.i16
 lda.l VmSourceWorld_Count
 beq SourceLost4086_Far13
 jmp SourceLost4086_Guard13
SourceLost4086_Far13:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard13:
.a16
.i16
 cmp #129
 bcs SourceLost4086_Far14
 jmp SourceLost4086_Guard14
SourceLost4086_Far14:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard14:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcs SourceLost4086_Far15
 jmp SourceLost4086_Guard15
SourceLost4086_Far15:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard15:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l SourceWorldTick4086_TimeLo
 bne SourceLost4086_Far16
 jmp SourceLost4086_Guard16
SourceLost4086_Far16:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard16:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l SourceWorldTick4086_TimeHi
 bne SourceLost4086_Far17
 jmp SourceLost4086_Guard17
SourceLost4086_Far17:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard17:
.a16
.i16
 lda.l SourceLost4086_HRes
 beq SourceLost4086_Far18
 jmp SourceLost4086_Guard18
SourceLost4086_Far18:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard18:
.a16
.i16
 cmp #$8000
 bcs SourceLost4086_Far19
 jmp SourceLost4086_Guard19
SourceLost4086_Far19:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard19:
.a16
.i16
 lda.l SourceLost4086_VRes
 beq SourceLost4086_Far20
 jmp SourceLost4086_Guard20
SourceLost4086_Far20:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard20:
.a16
.i16
 cmp #$8000
 bcs SourceLost4086_Far21
 jmp SourceLost4086_Guard21
SourceLost4086_Far21:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard21:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceLost4086_Core
 asl a
 sta.l SourceLost4086_Side
 clc
 adc.l SourceLost4086_Core
 sta.l SourceLost4086_Core
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceLost4086_Life
 asl a
 asl a
 clc
 adc.l SourceLost4086_Life
 sta.l SourceLost4086_Life
 sta.l SourceLost4086_View
 tax
 lda.l SOURCE_WORLD_POOL+8,x
 cmp #2
 bne SourceLost4086_Far22
 jmp SourceLost4086_Guard22
SourceLost4086_Far22:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard22:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+10,x
 bne SourceLost4086_Far23
 jmp SourceLost4086_Guard23
SourceLost4086_Far23:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard23:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+12,x
 sta.l SourceLost4086_Y
 lda.l SOURCE_WORLD_POOL+14,x
 sta.l SourceLost4086_Y+2
 lda.l SOURCE_WORLD_POOL+48,x
 cmp #2
 bne SourceLost4086_Far24
 jmp SourceLost4086_Guard24
SourceLost4086_Far24:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard24:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+50,x
 bne SourceLost4086_Far25
 jmp SourceLost4086_Guard25
SourceLost4086_Far25:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard25:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+52,x
 sta.l SourceLost4086_X
 lda.l SOURCE_WORLD_POOL+54,x
 sta.l SourceLost4086_X+2
 lda #0
 sta.l SourceLost4086_Parked
 sta.l SourceLost4086_Vertical
 sta.l SourceLost4086_Request
 sta.l SourceLost4086_AttackType
 sta.l SourceLost4086_Force
 sta.l SourceLost4086_Force+2
 lda.l SOURCE_WORLD_POOL+58,x
 bne SourceLost4086_Far26
 jmp SourceLost4086_Guard26
SourceLost4086_Far26:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard26:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+56,x
 cmp #2
 bne SourceLost4086_Far27
 jmp SourceLost4086_NormalZ
SourceLost4086_Far27:
.a16
.i16
 cmp #1
 bne SourceLost4086_Far28
 jmp SourceLost4086_Guard27
SourceLost4086_Far28:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard27:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+60,x
 cmp #$86A0
 bne SourceLost4086_Far29
 jmp SourceLost4086_Guard28
SourceLost4086_Far29:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard28:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+62,x
 cmp #1
 bne SourceLost4086_Far30
 jmp SourceLost4086_Guard29
SourceLost4086_Far30:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard29:
.a16
.i16
 lda #1
 sta.l SourceLost4086_Parked
 jmp SourceLost4086_ZReadDone
SourceLost4086_NormalZ:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+60,x
 sta.l SourceLost4086_Z
 lda.l SOURCE_WORLD_POOL+62,x
 sta.l SourceLost4086_Z+2
SourceLost4086_ZReadDone:
.a16
.i16
 lda.l VmSourceWorld_AdvanceX
 sta.l SourceLost4086_AX
 lda.l VmSourceWorld_AdvanceX+2
 sta.l SourceLost4086_AX+2
 lda.l VmSourceWorld_AdvanceY
 sta.l SourceLost4086_AY
 lda.l VmSourceWorld_AdvanceY+2
 sta.l SourceLost4086_AY+2
 lda.l SourceLost4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+16,x
 sta.l SourceLost4086_Countdown
 lda.l SOURCE_WORLD_SIDES+18,x
 sta.l SourceLost4086_Countdown+2
 lda.l SourceLost4086_Life
 tax
 lda.l $439004,x
 sta.l SourceLost4086_Damage
 lda.l $439006,x
 sta.l SourceLost4086_Damage+2
 lda.l SourceLost4086_OffscreenKill
 ora.l SourceLost4086_OffscreenKill+2
 bne SourceLost4086_Far31
 jmp SourceLost4086_DefaultOsk
SourceLost4086_Far31:
.a16
.i16
 lda.l SourceLost4086_OffscreenKill
 sta.l SourceLost4086_Osk+2
 lda.l SourceLost4086_OffscreenKill+2
 sta.l SourceLost4086_Osk+2+2
 jmp SourceLost4086_OskReadDone
SourceLost4086_DefaultOsk:
.a16
.i16
 lda.l SourceLost4086_DefaultOffscreenKill
 sta.l SourceLost4086_Osk+2
 lda.l SourceLost4086_DefaultOffscreenKill+2
 sta.l SourceLost4086_Osk+2+2
SourceLost4086_OskReadDone:
.a16
.i16
 lda #0
 sta.l SourceLost4086_Osk
 lda.l SourceLost4086_Osk+4
 bmi SourceLost4086_Far32
 jmp SourceLost4086_PositiveOsk
SourceLost4086_Far32:
.a16
.i16
 lda #$FFFF
 jmp SourceLost4086_SignOsk
SourceLost4086_PositiveOsk:
.a16
.i16
 lda #0
SourceLost4086_SignOsk:
.a16
.i16
 sta.l SourceLost4086_Osk+6
 lda.l SourceLost4086_Y
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Y+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Y+2
 bpl SourceLost4086_Far33
 jmp SourceLost4086_WidenNeg30
SourceLost4086_Far33:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone30
SourceLost4086_WidenNeg30:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone30:
.a16
.i16
 sta.l SourceLost4086_OpA+4
 sta.l SourceLost4086_OpA+6
 lda #$0000
 sta.l SourceLost4086_OpB
 lda #$FE0C
 sta.l SourceLost4086_OpB+2
 lda #$FFFF
 sta.l SourceLost4086_OpB+4
 lda #$FFFF
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_CompareSigned
 bcc SourceLost4086_Far34
 jmp SourceLost4086_Guard31
SourceLost4086_Far34:
.a16
.i16
 jmp SourceLost4086_Outside
SourceLost4086_Guard31:
.a16
.i16
 lda.l SourceLost4086_Parked
 bne SourceLost4086_Far35
 jmp SourceLost4086_Bounds
SourceLost4086_Far35:
.a16
.i16
 jmp SourceLost4086_Pit
SourceLost4086_Bounds:
.a16
.i16
 lda.l SourceLost4086_AX
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_AX+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_AX+2
 bpl SourceLost4086_Far36
 jmp SourceLost4086_WidenNeg32
SourceLost4086_Far36:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone32
SourceLost4086_WidenNeg32:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone32:
.a16
.i16
 sta.l SourceLost4086_OpA+4
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_X
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_X+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_X+2
 bpl SourceLost4086_Far37
 jmp SourceLost4086_WidenNeg33
SourceLost4086_Far37:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone33
SourceLost4086_WidenNeg33:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone33:
.a16
.i16
 sta.l SourceLost4086_OpB+4
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_OpA+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Osk
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Osk+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Osk+4
 sta.l SourceLost4086_OpB+4
 lda.l SourceLost4086_Osk+6
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_CompareSigned
 bcs SourceLost4086_Far38
 jmp SourceLost4086_InBounds34
SourceLost4086_Far38:
.a16
.i16
 bne SourceLost4086_Far39
 jmp SourceLost4086_InBounds34
SourceLost4086_Far39:
.a16
.i16
 jmp SourceLost4086_Outside
SourceLost4086_InBounds34:
.a16
.i16
 lda.l SourceLost4086_X
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_X+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_X+2
 bpl SourceLost4086_Far40
 jmp SourceLost4086_WidenNeg35
SourceLost4086_Far40:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone35
SourceLost4086_WidenNeg35:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone35:
.a16
.i16
 sta.l SourceLost4086_OpA+4
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_AX
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_AX+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_AX+2
 bpl SourceLost4086_Far41
 jmp SourceLost4086_WidenNeg36
SourceLost4086_Far41:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone36
SourceLost4086_WidenNeg36:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone36:
.a16
.i16
 sta.l SourceLost4086_OpB+4
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_OpA+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_OpA+6
 lda #0
 sta.l SourceLost4086_OpB
 sta.l SourceLost4086_OpB+4
 sta.l SourceLost4086_OpB+6
 lda.l SourceLost4086_HRes
 sta.l SourceLost4086_OpB+2
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_OpA+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Osk
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Osk+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Osk+4
 sta.l SourceLost4086_OpB+4
 lda.l SourceLost4086_Osk+6
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_CompareSigned
 bcs SourceLost4086_Far42
 jmp SourceLost4086_InBounds37
SourceLost4086_Far42:
.a16
.i16
 bne SourceLost4086_Far43
 jmp SourceLost4086_InBounds37
SourceLost4086_Far43:
.a16
.i16
 jmp SourceLost4086_Outside
SourceLost4086_InBounds37:
.a16
.i16
 lda.l SourceLost4086_Direction+2
 beq SourceLost4086_Far44
 jmp SourceLost4086_Horizontal
SourceLost4086_Far44:
.a16
.i16
 lda.l SourceLost4086_Direction
 cmp #16
 bne SourceLost4086_Far45
 jmp SourceLost4086_VerticalBounds
SourceLost4086_Far45:
.a16
.i16
 cmp #4
 bne SourceLost4086_Far46
 jmp SourceLost4086_VerticalBounds
SourceLost4086_Far46:
.a16
.i16
SourceLost4086_Horizontal:
.a16
.i16
 lda.l SourceLost4086_AY
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_AY+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_AY+2
 bpl SourceLost4086_Far47
 jmp SourceLost4086_WidenNeg38
SourceLost4086_Far47:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone38
SourceLost4086_WidenNeg38:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone38:
.a16
.i16
 sta.l SourceLost4086_OpA+4
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Z
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Z+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Z+2
 bpl SourceLost4086_Far48
 jmp SourceLost4086_WidenNeg39
SourceLost4086_Far48:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone39
SourceLost4086_WidenNeg39:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone39:
.a16
.i16
 sta.l SourceLost4086_OpB+4
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_OpA+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Y
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Y+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Y+2
 bpl SourceLost4086_Far49
 jmp SourceLost4086_WidenNeg40
SourceLost4086_Far49:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone40
SourceLost4086_WidenNeg40:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone40:
.a16
.i16
 sta.l SourceLost4086_OpB+4
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Add
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_OpA+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Osk
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Osk+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Osk+4
 sta.l SourceLost4086_OpB+4
 lda.l SourceLost4086_Osk+6
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_CompareSigned
 bcs SourceLost4086_Far50
 jmp SourceLost4086_InBounds41
SourceLost4086_Far50:
.a16
.i16
 bne SourceLost4086_Far51
 jmp SourceLost4086_InBounds41
SourceLost4086_Far51:
.a16
.i16
 jmp SourceLost4086_Outside
SourceLost4086_InBounds41:
.a16
.i16
 lda.l SourceLost4086_Z
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Z+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Z+2
 bpl SourceLost4086_Far52
 jmp SourceLost4086_WidenNeg42
SourceLost4086_Far52:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone42
SourceLost4086_WidenNeg42:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone42:
.a16
.i16
 sta.l SourceLost4086_OpA+4
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Y
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Y+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Y+2
 bpl SourceLost4086_Far53
 jmp SourceLost4086_WidenNeg43
SourceLost4086_Far53:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone43
SourceLost4086_WidenNeg43:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone43:
.a16
.i16
 sta.l SourceLost4086_OpB+4
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_OpA+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_AY
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_AY+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_AY+2
 bpl SourceLost4086_Far54
 jmp SourceLost4086_WidenNeg44
SourceLost4086_Far54:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone44
SourceLost4086_WidenNeg44:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone44:
.a16
.i16
 sta.l SourceLost4086_OpB+4
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_OpA+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_OpA+6
 lda #0
 sta.l SourceLost4086_OpB
 sta.l SourceLost4086_OpB+4
 sta.l SourceLost4086_OpB+6
 lda.l SourceLost4086_VRes
 sta.l SourceLost4086_OpB+2
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_OpA+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Osk
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Osk+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Osk+4
 sta.l SourceLost4086_OpB+4
 lda.l SourceLost4086_Osk+6
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_CompareSigned
 bcs SourceLost4086_Far55
 jmp SourceLost4086_InBounds45
SourceLost4086_Far55:
.a16
.i16
 bne SourceLost4086_Far56
 jmp SourceLost4086_InBounds45
SourceLost4086_Far56:
.a16
.i16
 jmp SourceLost4086_Outside
SourceLost4086_InBounds45:
.a16
.i16
 jmp SourceLost4086_Pit
SourceLost4086_VerticalBounds:
.a16
.i16
 lda #$0000
 sta.l SourceLost4086_OpA
 lda #$0000
 sta.l SourceLost4086_OpA+2
 lda #$0000
 sta.l SourceLost4086_OpA+4
 lda #$0000
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Osk
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Osk+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Osk+4
 sta.l SourceLost4086_OpB+4
 lda.l SourceLost4086_Osk+6
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_Osk
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_Osk+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_Osk+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_Osk+6
 lda.l SourceLost4086_Z
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Z+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Z+2
 bpl SourceLost4086_Far57
 jmp SourceLost4086_WidenNeg46
SourceLost4086_Far57:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone46
SourceLost4086_WidenNeg46:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone46:
.a16
.i16
 sta.l SourceLost4086_OpA+4
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Y
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Y+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Y+2
 bpl SourceLost4086_Far58
 jmp SourceLost4086_WidenNeg47
SourceLost4086_Far58:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone47
SourceLost4086_WidenNeg47:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone47:
.a16
.i16
 sta.l SourceLost4086_OpB+4
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_OpA+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Osk
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Osk+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Osk+4
 sta.l SourceLost4086_OpB+4
 lda.l SourceLost4086_Osk+6
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_CompareSigned
 bcc SourceLost4086_Far59
 jmp SourceLost4086_VerticalLowerOk
SourceLost4086_Far59:
.a16
.i16
 jmp SourceLost4086_Outside
SourceLost4086_VerticalLowerOk:
.a16
.i16
 lda #$0000
 sta.l SourceLost4086_OpA
 lda #$0000
 sta.l SourceLost4086_OpA+2
 lda #$0000
 sta.l SourceLost4086_OpA+4
 lda #$0000
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Osk
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Osk+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Osk+4
 sta.l SourceLost4086_OpB+4
 lda.l SourceLost4086_Osk+6
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_Osk
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_Osk+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_Osk+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_Osk+6
 lda #0
 sta.l SourceLost4086_OpA
 sta.l SourceLost4086_OpA+4
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_VRes
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Osk
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Osk+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Osk+4
 sta.l SourceLost4086_OpB+4
 lda.l SourceLost4086_Osk+6
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Add
 ; The source vRes + osk expression is signed int32 before float conversion.
 ; Match the measured pinned compiler's wrap at the int32 limit explicitly.
 lda.l SourceLost4086_Result+4
 bmi SourceLost4086_VerticalWrapNegative
 lda #0
 bra SourceLost4086_VerticalWrapDone
SourceLost4086_VerticalWrapNegative:
.a16
.i16
 lda #$FFFF
SourceLost4086_VerticalWrapDone:
.a16
.i16
 sta.l SourceLost4086_Result+6
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_Osk
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_Osk+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_Osk+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_Osk+6
 lda.l SourceLost4086_Z
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Z+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Z+2
 bpl SourceLost4086_Far60
 jmp SourceLost4086_WidenNeg49
SourceLost4086_Far60:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone49
SourceLost4086_WidenNeg49:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone49:
.a16
.i16
 sta.l SourceLost4086_OpA+4
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Y
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Y+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Y+2
 bpl SourceLost4086_Far61
 jmp SourceLost4086_WidenNeg50
SourceLost4086_Far61:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone50
SourceLost4086_WidenNeg50:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone50:
.a16
.i16
 sta.l SourceLost4086_OpB+4
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_Subtract
 lda.l SourceLost4086_Result
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Result+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Result+4
 sta.l SourceLost4086_OpA+4
 lda.l SourceLost4086_Result+6
 sta.l SourceLost4086_OpA+6
 lda.l SourceLost4086_Osk
 sta.l SourceLost4086_OpB
 lda.l SourceLost4086_Osk+2
 sta.l SourceLost4086_OpB+2
 lda.l SourceLost4086_Osk+4
 sta.l SourceLost4086_OpB+4
 lda.l SourceLost4086_Osk+6
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_CompareSigned
 bcs SourceLost4086_Far62
 jmp SourceLost4086_InBounds51
SourceLost4086_Far62:
.a16
.i16
 bne SourceLost4086_Far63
 jmp SourceLost4086_InBounds51
SourceLost4086_Far63:
.a16
.i16
 jmp SourceLost4086_Outside
SourceLost4086_InBounds51:
.a16
.i16
SourceLost4086_Pit:
.a16
.i16
 lda.l SourceLost4086_Y
 sta.l SourceLost4086_OpA
 lda.l SourceLost4086_Y+2
 sta.l SourceLost4086_OpA+2
 lda.l SourceLost4086_Y+2
 bpl SourceLost4086_Far64
 jmp SourceLost4086_WidenNeg52
SourceLost4086_Far64:
.a16
.i16
 lda #0
 jmp SourceLost4086_WidenDone52
SourceLost4086_WidenNeg52:
.a16
.i16
 lda #$FFFF
SourceLost4086_WidenDone52:
.a16
.i16
 sta.l SourceLost4086_OpA+4
 sta.l SourceLost4086_OpA+6
 lda #$0000
 sta.l SourceLost4086_OpB
 lda #$FF06
 sta.l SourceLost4086_OpB+2
 lda #$FFFF
 sta.l SourceLost4086_OpB+4
 lda #$FFFF
 sta.l SourceLost4086_OpB+6
 jsr SourceLost4086_CompareSigned
 bcc SourceLost4086_Far65
 jmp SourceLost4086_CheckLifespan
SourceLost4086_Far65:
.a16
.i16
 lda #3
 sta.l SourceLost4086_Request
 lda #17
 sta.l SourceLost4086_AttackType
 jmp SourceLost4086_DamageRequest
SourceLost4086_CheckLifespan:
.a16
.i16
 lda.l SourceLost4086_Countdown+2
 bmi SourceLost4086_Far66
 jmp SourceLost4086_CountdownCheck
SourceLost4086_Far66:
.a16
.i16
 lda #4
 sta.l SourceLost4086_Request
 lda #18
 sta.l SourceLost4086_AttackType
 jmp SourceLost4086_DamageRequest
SourceLost4086_CountdownCheck:
.a16
.i16
 jsl SourceFreeze4086_Query
 bcs SourceLost4086_Far67
 jmp SourceLost4086_Guard53
SourceLost4086_Far67:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard53:
.a16
.i16
 ora #0
 beq SourceLost4086_Far68
 jmp SourceLost4086_Complete
SourceLost4086_Far68:
.a16
.i16
 lda.l SourceLost4086_Countdown+2
 cmp #$7FFF
 beq SourceLost4086_Far69
 jmp SourceLost4086_Decrement
SourceLost4086_Far69:
.a16
.i16
 lda.l SourceLost4086_Countdown
 cmp #$FFFF
 bne SourceLost4086_Far70
 jmp SourceLost4086_Complete
SourceLost4086_Far70:
.a16
.i16
SourceLost4086_Decrement:
.a16
.i16
 lda.l SourceLost4086_Side
 tax
 sec
 lda.l SourceLost4086_Countdown
 sbc #1
 sta.l SOURCE_WORLD_SIDES+16,x
 lda.l SourceLost4086_Countdown+2
 sbc #0
 sta.l SOURCE_WORLD_SIDES+18,x
SourceLost4086_Complete:
.a16
.i16
 lda #2
 sta.l SourceLost4086_Status
 jmp SourceLost4086_Ok
SourceLost4086_Outside:
.a16
.i16
 lda.l SourceLost4086_Core
 tax
 lda.l $40C048,x
 and #1
 bne SourceLost4086_Far71
 jmp SourceLost4086_KillRequest
SourceLost4086_Far71:
.a16
.i16
 lda #2
 sta.l SourceLost4086_Request
 jmp SourceLost4086_Pending
SourceLost4086_DamageRequest:
.a16
.i16
 lda.l SourceLost4086_Damage
 ora.l SourceLost4086_Damage+2
 bne SourceLost4086_Far72
 jmp SourceLost4086_KillRequest
SourceLost4086_Far72:
.a16
.i16
 lda.l SourceLost4086_View
 tax
 lda.l SOURCE_WORLD_POOL+32,x
 cmp #1
 bne SourceLost4086_Far73
 jmp SourceLost4086_Guard54
SourceLost4086_Far73:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard54:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+34,x
 bne SourceLost4086_Far74
 jmp SourceLost4086_Guard55
SourceLost4086_Far74:
.a16
.i16
 jmp SourceLost4086_Bad
SourceLost4086_Guard55:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+36,x
 sta.l SourceLost4086_Force
 lda.l SOURCE_WORLD_POOL+38,x
 sta.l SourceLost4086_Force+2
 jmp SourceLost4086_Pending
SourceLost4086_KillRequest:
.a16
.i16
 lda #1
 sta.l SourceLost4086_Request
 lda #0
 sta.l SourceLost4086_AttackType
SourceLost4086_Pending:
.a16
.i16
 lda #1
 sta.l SourceLost4086_Status
SourceLost4086_Ok:
.a16
.i16
 lda.l SourceLost4086_Request
 ply
 plx
 plp
 clc
 rtl
SourceLost4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceLost4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceLost4086_Add:
.a16
.i16
 clc
 lda.l SourceLost4086_OpA
 adc.l SourceLost4086_OpB
 sta.l SourceLost4086_Result
 lda.l SourceLost4086_OpA+2
 adc.l SourceLost4086_OpB+2
 sta.l SourceLost4086_Result+2
 lda.l SourceLost4086_OpA+4
 adc.l SourceLost4086_OpB+4
 sta.l SourceLost4086_Result+4
 lda.l SourceLost4086_OpA+6
 adc.l SourceLost4086_OpB+6
 sta.l SourceLost4086_Result+6
 rts
SourceLost4086_Subtract:
.a16
.i16
 sec
 lda.l SourceLost4086_OpA
 sbc.l SourceLost4086_OpB
 sta.l SourceLost4086_Result
 lda.l SourceLost4086_OpA+2
 sbc.l SourceLost4086_OpB+2
 sta.l SourceLost4086_Result+2
 lda.l SourceLost4086_OpA+4
 sbc.l SourceLost4086_OpB+4
 sta.l SourceLost4086_Result+4
 lda.l SourceLost4086_OpA+6
 sbc.l SourceLost4086_OpB+6
 sta.l SourceLost4086_Result+6
 rts
SourceLost4086_CompareSigned:
.a16
.i16
 lda.l SourceLost4086_OpB+6
 eor #$8000
 sta.l SourceLost4086_Compare
 lda.l SourceLost4086_OpA+6
 eor #$8000
 cmp.l SourceLost4086_Compare
 beq SourceLost4086_Far75
 jmp SourceLost4086_CompareDone
SourceLost4086_Far75:
.a16
.i16
 lda.l SourceLost4086_OpA+4
 cmp.l SourceLost4086_OpB+4
 beq SourceLost4086_Far76
 jmp SourceLost4086_CompareDone
SourceLost4086_Far76:
.a16
.i16
 lda.l SourceLost4086_OpA+2
 cmp.l SourceLost4086_OpB+2
 beq SourceLost4086_Far77
 jmp SourceLost4086_CompareDone
SourceLost4086_Far77:
.a16
.i16
 lda.l SourceLost4086_OpA
 cmp.l SourceLost4086_OpB
 beq SourceLost4086_Far78
 jmp SourceLost4086_CompareDone
SourceLost4086_Far78:
.a16
.i16
SourceLost4086_CompareDone:
.a16
.i16
 rts
