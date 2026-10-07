; Generic single-series NPC runoff and adjust_walk_animation service.
; Ready B60C is published only with derived single WALK/UP/DOWN/BACKWALK
; arrays and absent directional-series pointers. RUN remains source-derived.
; Parent is the captured callback17 SourceCommonAttackFinish owner.
; Q16.16 numeric policy is explicit; intermediate coordinate overflow faults.
SourceAttackRunoff4086_Ready = $43BF7C
SourceAttackRunoff4086_Status = $43BF7E
SourceAttackRunoff4086_Mode = $43BF80 ; 0 idle,1 gate needs RNG,2 selected runoff
SourceAttackRunoff4086_Running = $43BF82
SourceAttackRunoff4086_Target = $43BF84
SourceAttackRunoff4086_Right = $43BF86
SourceAttackRunoff4086_SelfX = $43BF88
SourceAttackRunoff4086_TargetX = $43BF8C
SourceAttackRunoff4086_DestX = $43BF90
SourceAttackRunoff4086_DestZ = $43BF94
SourceAttackRunoff4086_VelX = $43BF98
SourceAttackRunoff4086_WalkID = $43BF9C
SourceAttackRunoff4086_UpID = $43BF9E
SourceAttackRunoff4086_DownID = $43BFA0
SourceAttackRunoff4086_BackID = $43BFA2
SourceAttackRunoff4086_RunID = $43BFA4
SourceAttackRunoff4086_Temp = $43BFA6
SourceAttackRunoff4086_Handle = $43BFA8
SourceAttackRunoff4086_End = $43BFAA

SourceAttackRunoff4086_Preflight:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAttackRunoff4086_Ready
 cmp #$B60C
 beq SourceAttackRunoff4086_Branch1
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch1:
.a16
.i16
 lda.l SourceAttackRunoff4086_Status
 bne SourceAttackRunoff4086_Branch2
 jmp SourceAttackRunoff4086_PreflightStart
SourceAttackRunoff4086_Branch2:
.a16
.i16
 cmp #2
 beq SourceAttackRunoff4086_Branch3
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch3:
.a16
.i16
SourceAttackRunoff4086_PreflightStart:
.a16
.i16
 lda #0
 sta.l SourceAttackRunoff4086_Mode
 lda.l SourceAI4086_Side
 tax
 lda.l $40900C,x
 sta.l SourceRetirement4086_ArgLo
 lda.l $40900E,x
 sta.l SourceRetirement4086_ArgHi
 jsl SourceRetirement4086_ResolvePointer
 bcc SourceAttackRunoff4086_Branch4
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch4:
.a16
.i16
 cmp #$FFFF
 bne SourceAttackRunoff4086_Branch5
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch5:
.a16
.i16
 ; Slot -> physical view token, independent of exists (literal pointer rules).
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 clc
 adc #$4000
 sta.l SourceAttackRunoff4086_Target
 pla
 lda.l SourceAI4086_View
 tax
 lda.l $410030,x
 cmp #BOR_VT_DECIMAL
 beq SourceAttackRunoff4086_Branch6
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch6:
.a16
.i16
 lda.l $410032,x
 beq SourceAttackRunoff4086_Branch7
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch7:
.a16
.i16
 lda.l $410034,x
 sta.l SourceAttackRunoff4086_SelfX
 lda.l $410036,x
 sta.l SourceAttackRunoff4086_SelfX+2
 lda.l SourceAttackRunoff4086_Target
 tax
 lda.l $410030,x
 cmp #BOR_VT_DECIMAL
 beq SourceAttackRunoff4086_Branch8
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch8:
.a16
.i16
 lda.l $410032,x
 beq SourceAttackRunoff4086_Branch9
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch9:
.a16
.i16
 lda.l $410034,x
 sta.l SourceAttackRunoff4086_TargetX
 lda.l $410036,x
 sta.l SourceAttackRunoff4086_TargetX+2
 eor #$8000
 sta.l SourceAttackRunoff4086_Temp
 lda.l SourceAttackRunoff4086_SelfX+2
 eor #$8000
 cmp.l SourceAttackRunoff4086_Temp
 bcs SourceAttackRunoff4086_Branch10
 jmp SourceAttackRunoff4086_Left
SourceAttackRunoff4086_Branch10:
.a16
.i16
 beq SourceAttackRunoff4086_Branch11
 jmp SourceAttackRunoff4086_Rightward
SourceAttackRunoff4086_Branch11:
.a16
.i16
 lda.l SourceAttackRunoff4086_SelfX
 cmp.l SourceAttackRunoff4086_TargetX
 bcs SourceAttackRunoff4086_Branch12
 jmp SourceAttackRunoff4086_Left
SourceAttackRunoff4086_Branch12:
.a16
.i16
 bne SourceAttackRunoff4086_Branch13
 jmp SourceAttackRunoff4086_Left
SourceAttackRunoff4086_Branch13:
.a16
.i16
SourceAttackRunoff4086_Rightward:
.a16
.i16
 lda #1
 sta.l SourceAttackRunoff4086_Right
 lda.l SourceAttackRunoff4086_SelfX
 sec
 sbc.l SourceAttackRunoff4086_TargetX
 lda.l SourceAttackRunoff4086_SelfX+2
 sbc.l SourceAttackRunoff4086_TargetX+2
 jmp SourceAttackRunoff4086_Distance
SourceAttackRunoff4086_Left:
.a16
.i16
 lda #0
 sta.l SourceAttackRunoff4086_Right
 lda.l SourceAttackRunoff4086_TargetX
 sec
 sbc.l SourceAttackRunoff4086_SelfX
 lda.l SourceAttackRunoff4086_TargetX+2
 sbc.l SourceAttackRunoff4086_SelfX+2
SourceAttackRunoff4086_Distance:
.a16
.i16
 cmp #80
 bcc SourceAttackRunoff4086_NearTarget
 jmp SourceAttackRunoff4086_Good ; source avoids RNG/resource paths at >=80
SourceAttackRunoff4086_NearTarget:
.a16
.i16
 lda.l SourceMovementState4086_Ready
 cmp #$B60B
 beq SourceAttackRunoff4086_Branch14
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch14:
.a16
.i16
 lda.l SourceAI4086_Slot
 jsl SourceMovementState4086_PreflightBirth
 bcc SourceAttackRunoff4086_Branch15
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch15:
.a16
.i16
 lda.l SourceRandom4086_Ready
 cmp #$B4D4
 beq SourceAttackRunoff4086_Branch16
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch16:
.a16
.i16
 lda.l SourceRandom4086_Busy
 beq SourceAttackRunoff4086_Branch17
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch17:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $43904C,x
 cmp #$B508
 beq SourceAttackRunoff4086_Branch18
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch18:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l $42F404,x
 ora.l $42F406,x
 sta.l SourceAttackRunoff4086_Running
 beq SourceAttackRunoff4086_Branch19
 jmp SourceAttackRunoff4086_RunRole
SourceAttackRunoff4086_Branch19:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $43902E,x
 beq SourceAttackRunoff4086_Branch20
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch20:
.a16
.i16
 lda.l $43902C,x
 cmp #2
 bcc SourceAttackRunoff4086_Branch21
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch21:
.a16
.i16
 lda.l SourceAttackRunoff4086_UpID
 jsr SourceAttackRunoff4086_AbsentRole
 bcc SourceAttackRunoff4086_Branch22
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch22:
.a16
.i16
 lda.l SourceAttackRunoff4086_DownID
 jsr SourceAttackRunoff4086_AbsentRole
 bcc SourceAttackRunoff4086_Branch23
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch23:
.a16
.i16
 lda.l SourceAttackRunoff4086_BackID
 jsr SourceAttackRunoff4086_AbsentRole
 bcc SourceAttackRunoff4086_Branch24
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch24:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410018,x
 cmp #BOR_VT_INTEGER
 beq SourceAttackRunoff4086_Branch25
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch25:
.a16
.i16
 lda.l $41001A,x
 beq SourceAttackRunoff4086_Branch26
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch26:
.a16
.i16
 lda.l SourceAttackRunoff4086_WalkID
 jmp SourceAttackRunoff4086_ResolveRole
SourceAttackRunoff4086_RunRole:
.a16
.i16
 lda.l SourceAttackRunoff4086_RunID
SourceAttackRunoff4086_ResolveRole:
.a16
.i16
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcc SourceAttackRunoff4086_Branch27
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch27:
.a16
.i16
 sta.l SourceAnimationInit4086_Number
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 sta.l SourceAttackRunoff4086_Handle
 bne SourceAttackRunoff4086_Branch28
 jmp SourceAttackRunoff4086_RoleResolved
SourceAttackRunoff4086_Branch28:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda #0
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcc SourceAttackRunoff4086_Branch29
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch29:
.a16
.i16
SourceAttackRunoff4086_RoleResolved:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410038,x
 cmp #BOR_VT_DECIMAL
 beq SourceAttackRunoff4086_Branch30
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch30:
.a16
.i16
 lda.l $41003A,x
 beq SourceAttackRunoff4086_Branch31
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch31:
.a16
.i16
 lda.l $41003C,x
 sta.l SourceAttackRunoff4086_DestZ
 lda.l $41003E,x
 sta.l SourceAttackRunoff4086_DestZ+2
 lda.l SourceAI4086_Side
 tax
 lda.l $41683C,x
 sta.l SourceAttackRunoff4086_VelX
 lda.l $41683E,x
 sta.l SourceAttackRunoff4086_VelX+2
 lda.l SourceAttackRunoff4086_Right
 beq SourceAttackRunoff4086_Branch32
 jmp SourceAttackRunoff4086_AddDest
SourceAttackRunoff4086_Branch32:
.a16
.i16
 lda.l SourceAttackRunoff4086_VelX+2
 cmp #$8000
 beq SourceAttackRunoff4086_Branch33
 jmp SourceAttackRunoff4086_NegateSpeed
SourceAttackRunoff4086_Branch33:
.a16
.i16
 lda.l SourceAttackRunoff4086_VelX
 bne SourceAttackRunoff4086_Branch34
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch34:
.a16
.i16
SourceAttackRunoff4086_NegateSpeed:
.a16
.i16
 lda #0
 sec
 sbc.l SourceAttackRunoff4086_VelX
 sta.l SourceAttackRunoff4086_VelX
 lda #0
 sbc.l SourceAttackRunoff4086_VelX+2
 sta.l SourceAttackRunoff4086_VelX+2
 lda.l SourceAttackRunoff4086_SelfX
 sta.l SourceAttackRunoff4086_DestX
 lda.l SourceAttackRunoff4086_SelfX+2
 sec
 sbc #40
 bvc SourceAttackRunoff4086_Branch35
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch35:
.a16
.i16
 sta.l SourceAttackRunoff4086_DestX+2
 lda.l SourceAttackRunoff4086_TargetX+2
 sec
 sbc #80
 bvc SourceAttackRunoff4086_Branch36
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch36:
.a16
.i16
 sta.l SourceAttackRunoff4086_TargetX+2
 jmp SourceAttackRunoff4086_ChooseDest
SourceAttackRunoff4086_AddDest:
.a16
.i16
 lda.l SourceAttackRunoff4086_SelfX
 sta.l SourceAttackRunoff4086_DestX
 lda.l SourceAttackRunoff4086_SelfX+2
 clc
 adc #40
 bvc SourceAttackRunoff4086_Branch37
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch37:
.a16
.i16
 sta.l SourceAttackRunoff4086_DestX+2
 lda.l SourceAttackRunoff4086_TargetX+2
 clc
 adc #80
 bvc SourceAttackRunoff4086_Branch38
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch38:
.a16
.i16
 sta.l SourceAttackRunoff4086_TargetX+2
SourceAttackRunoff4086_ChooseDest:
.a16
.i16
 lda.l SourceAttackRunoff4086_TargetX+2
 eor #$8000
 sta.l SourceAttackRunoff4086_Temp
 lda.l SourceAttackRunoff4086_DestX+2
 eor #$8000
 cmp.l SourceAttackRunoff4086_Temp
 bcs SourceAttackRunoff4086_Branch39
 jmp SourceAttackRunoff4086_DestSmaller
SourceAttackRunoff4086_Branch39:
.a16
.i16
 beq SourceAttackRunoff4086_Branch40
 jmp SourceAttackRunoff4086_DestLarger
SourceAttackRunoff4086_Branch40:
.a16
.i16
 lda.l SourceAttackRunoff4086_DestX
 cmp.l SourceAttackRunoff4086_TargetX
 bcs SourceAttackRunoff4086_Branch41
 jmp SourceAttackRunoff4086_DestSmaller
SourceAttackRunoff4086_Branch41:
.a16
.i16
SourceAttackRunoff4086_DestLarger:
.a16
.i16
 lda.l SourceAttackRunoff4086_Right
 bne SourceAttackRunoff4086_Branch42
 jmp SourceAttackRunoff4086_DestChosen
SourceAttackRunoff4086_Branch42:
.a16
.i16
 jmp SourceAttackRunoff4086_CopyTarget
SourceAttackRunoff4086_DestSmaller:
.a16
.i16
 lda.l SourceAttackRunoff4086_Right
 beq SourceAttackRunoff4086_Branch43
 jmp SourceAttackRunoff4086_DestChosen
SourceAttackRunoff4086_Branch43:
.a16
.i16
SourceAttackRunoff4086_CopyTarget:
.a16
.i16
 lda.l SourceAttackRunoff4086_TargetX
 sta.l SourceAttackRunoff4086_DestX
 lda.l SourceAttackRunoff4086_TargetX+2
 sta.l SourceAttackRunoff4086_DestX+2
SourceAttackRunoff4086_DestChosen:
.a16
.i16
 lda #1
 sta.l SourceAttackRunoff4086_Mode
SourceAttackRunoff4086_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl

; After source velocity/action clear. RNG is consumed only by the literal gate.
; A=0 uses idle, A=1 awaits real frame zero, A=2 completed runoff.
SourceAttackRunoff4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAttackRunoff4086_Ready
 cmp #$B60C
 beq SourceAttackRunoff4086_Branch44
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch44:
.a16
.i16
 lda.l SourceAttackRunoff4086_Mode
 cmp #1
 beq SourceAttackRunoff4086_Branch45
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch45:
.a16
.i16
 jsl SourceRandom4086_Next
 bcc SourceAttackRunoff4086_Branch46
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch46:
.a16
.i16
 lda.l VmNativeVariant_Result+4
 and #3
 bne SourceAttackRunoff4086_Branch47
 jmp SourceAttackRunoff4086_UseIdle
SourceAttackRunoff4086_Branch47:
.a16
.i16
 lda #2
 sta.l SourceAttackRunoff4086_Mode
 lda.l SourceAI4086_Side
 tax
 lda.l SourceAttackRunoff4086_VelX
 sta.l $416824,x
 lda.l SourceAttackRunoff4086_VelX+2
 sta.l $416826,x
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 tax
 lda.l SourceAttackRunoff4086_DestX
 sta.l SOURCE_ENTITY_MOVEMENT_DEST,x
 lda.l SourceAttackRunoff4086_DestX+2
 sta.l SOURCE_ENTITY_MOVEMENT_DEST+2,x
 lda.l SourceAttackRunoff4086_DestZ
 sta.l SOURCE_ENTITY_MOVEMENT_DEST+4,x
 lda.l SourceAttackRunoff4086_DestZ+2
 sta.l SOURCE_ENTITY_MOVEMENT_DEST+6,x
 lda.l SourceAttackRunoff4086_Handle
 bne SourceAttackRunoff4086_Branch48
 jmp SourceAttackRunoff4086_PostWalk
SourceAttackRunoff4086_Branch48:
.a16
.i16
 jsl SourceAnimationInit4086_Begin
 bcc SourceAttackRunoff4086_Branch49
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch49:
.a16
.i16
 lda.l SourceAnimationInit4086_State
 cmp #2
 bne SourceAttackRunoff4086_Branch50
 jmp SourceAttackRunoff4086_PostWalk
SourceAttackRunoff4086_Branch50:
.a16
.i16
 cmp #1
 beq SourceAttackRunoff4086_Branch51
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch51:
.a16
.i16
 lda #1
 sta.l SourceAttackRunoff4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceAttackRunoff4086_UseIdle:
.a16
.i16
 lda #0
 sta.l SourceAttackRunoff4086_Mode
 lda #2
 sta.l SourceAttackRunoff4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceAttackRunoff4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAttackRunoff4086_Ready
 cmp #$B60C
 beq SourceAttackRunoff4086_Branch52
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch52:
.a16
.i16
 lda.l SourceAttackRunoff4086_Status
 cmp #1
 beq SourceAttackRunoff4086_Branch53
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch53:
.a16
.i16
 lda.l SourceAttackRunoff4086_Mode
 cmp #2
 beq SourceAttackRunoff4086_Branch54
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch54:
.a16
.i16
 lda.l SourceAI4086_Slot
 cmp.l SourceAnimationInit4086_Slot
 beq SourceAttackRunoff4086_Branch55
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch55:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceAttackRunoff4086_Branch56
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch56:
.a16
.i16
 jsl SourceAnimationInit4086_Ack
 bcc SourceAttackRunoff4086_Branch57
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch57:
.a16
.i16
SourceAttackRunoff4086_PostWalk:
.a16
.i16
 lda.l SourceAttackRunoff4086_Running
 beq SourceAttackRunoff4086_Branch58
 jmp SourceAttackRunoff4086_SetIdling
SourceAttackRunoff4086_Branch58:
.a16
.i16
 ; Re-read actual fields after animation callbacks, matching source ordering.
 lda.l SourceAI4086_View
 tax
 lda.l $410018,x
 cmp #BOR_VT_INTEGER
 beq SourceAttackRunoff4086_Branch59
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch59:
.a16
.i16
 lda.l $41001A,x
 beq SourceAttackRunoff4086_Branch60
 jmp SourceAttackRunoff4086_Bad
SourceAttackRunoff4086_Branch60:
.a16
.i16
 lda.l $41001E,x
 beq SourceAttackRunoff4086_Branch61
 jmp SourceAttackRunoff4086_NotRight
SourceAttackRunoff4086_Branch61:
.a16
.i16
 lda.l $41001C,x
 cmp #1
 beq SourceAttackRunoff4086_Branch62
 jmp SourceAttackRunoff4086_NotRight
SourceAttackRunoff4086_Branch62:
.a16
.i16
 lda.l SourceAI4086_Side
 tax
 lda.l $416826,x
 bpl SourceAttackRunoff4086_Branch63
 jmp SourceAttackRunoff4086_Reverse
SourceAttackRunoff4086_Branch63:
.a16
.i16
 jmp SourceAttackRunoff4086_Forward
SourceAttackRunoff4086_NotRight:
.a16
.i16
 lda.l SourceAI4086_Side
 tax
 lda.l $416826,x
 bpl SourceAttackRunoff4086_Branch64
 jmp SourceAttackRunoff4086_Forward
SourceAttackRunoff4086_Branch64:
.a16
.i16
 ora.l $416824,x
 beq SourceAttackRunoff4086_Branch65
 jmp SourceAttackRunoff4086_Reverse
SourceAttackRunoff4086_Branch65:
.a16
.i16
SourceAttackRunoff4086_Forward:
.a16
.i16
 lda #1
 jmp SourceAttackRunoff4086_Playback
SourceAttackRunoff4086_Reverse:
.a16
.i16
 lda #$FFFF
SourceAttackRunoff4086_Playback:
.a16
.i16
 pha
 lda.l SourceAI4086_Slot
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 tax
 pla
 pla
 sta.l $41F510,x
SourceAttackRunoff4086_SetIdling:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda #1
 sta.l $43EB00,x
 lda #0
 sta.l $43EB02,x
 lda #2
 sta.l SourceAttackRunoff4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceAttackRunoff4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAttackRunoff4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceAttackRunoff4086_AbsentRole:
.a16
.i16
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcc SourceAttackRunoff4086_Branch66
 jmp SourceAttackRunoff4086_RoleBad
SourceAttackRunoff4086_Branch66:
.a16
.i16
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 beq SourceAttackRunoff4086_Branch67
 jmp SourceAttackRunoff4086_RoleBad
SourceAttackRunoff4086_Branch67:
.a16
.i16
 clc
 rts
SourceAttackRunoff4086_RoleBad:
.a16
.i16
 sec
 rts
