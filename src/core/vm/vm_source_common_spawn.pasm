; Actual common_spawn callback. Other action identities explicitly rejected.
; State1 requires actual idle frame-zero callback/effects, then Continue.
SourceCommonSpawn4086_Ready = $43BD1E
SourceCommonSpawn4086_State = $43BD20
SourceCommonSpawn4086_Slot = $43BD22
SourceCommonSpawn4086_End = $43BD24
SourceCommonSpawn4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCommonSpawn4086_State
 bne SourceCommonSpawn4086_Far1
 jmp SourceCommonSpawn4086_BeginIdle
SourceCommonSpawn4086_Far1:
.a16
.i16
 cmp #2
 bne SourceCommonSpawn4086_Far2
 jmp SourceCommonSpawn4086_BeginIdle
SourceCommonSpawn4086_Far2:
.a16
.i16
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_BeginIdle:
.a16
.i16
 jsr SourceCommonSpawn4086_Preflight
 bcs SourceCommonSpawn4086_Far3
 jmp SourceCommonSpawn4086_BeginChecked
SourceCommonSpawn4086_Far3:
.a16
.i16
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_BeginChecked:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $43900C,x
 cmp #4
 beq SourceCommonSpawn4086_Far4
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far4:
.a16
.i16
 lda.l $43900E,x
 beq SourceCommonSpawn4086_Far5
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far5:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceCommonSpawn4086_Slot
 sta.l SourceIdle4086_Slot
 asl a
 asl a
 sta.l SourceAI4086_Temp
 asl a
 asl a
 clc
 adc.l SourceAI4086_Temp
 tax
 lda.l $41F510,x
 beq SourceCommonSpawn4086_Far6
 jmp SourceCommonSpawn4086_Animating
SourceCommonSpawn4086_Far6:
.a16
.i16
 ; Preflight immutable IDLE before mutating callback/flags.
 lda.l SourceAI4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda #0
 sta.l SourceAnimationInit4086_Number
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcc SourceCommonSpawn4086_Far7
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far7:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 bne SourceCommonSpawn4086_Far8
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far8:
.a16
.i16
 lda.l SourceAnimationInit4086_Count
 bne SourceCommonSpawn4086_Far9
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far9:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda #0
 sta.l $43900C,x
 sta.l $43900E,x
 jsl SourceSetIdle4086_Begin
 bcc SourceCommonSpawn4086_Far10
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far10:
.a16
.i16
 cmp #1
 bne SourceCommonSpawn4086_Far11
 jmp SourceCommonSpawn4086_Pending
SourceCommonSpawn4086_Far11:
.a16
.i16
 jmp SourceCommonSpawn4086_Done
SourceCommonSpawn4086_Animating:
.a16
.i16
 lda.l SourceAI4086_Flags
 tax
 lda #0
 sta.l $43EB00,x
 jmp SourceCommonSpawn4086_Done
SourceCommonSpawn4086_Pending:
.a16
.i16
 lda #1
 sta.l SourceCommonSpawn4086_State
 jmp SourceCommonSpawn4086_Good
SourceCommonSpawn4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCommonSpawn4086_State
 cmp #1
 beq SourceCommonSpawn4086_Far12
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far12:
.a16
.i16
 jsr SourceCommonSpawn4086_Preflight
 bcc SourceCommonSpawn4086_Far13
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far13:
.a16
.i16
 lda.l SourceAI4086_Slot
 cmp.l SourceCommonSpawn4086_Slot
 beq SourceCommonSpawn4086_Far14
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far14:
.a16
.i16
 cmp.l SourceAnimationInit4086_Slot
 beq SourceCommonSpawn4086_Far15
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far15:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceCommonSpawn4086_Far16
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far16:
.a16
.i16
 jsl SourceAnimationInit4086_Ack
 bcc SourceCommonSpawn4086_Far17
 jmp SourceCommonSpawn4086_Bad
SourceCommonSpawn4086_Far17:
.a16
.i16
SourceCommonSpawn4086_Done:
.a16
.i16
 lda #2
 sta.l SourceCommonSpawn4086_State
 lda #0
SourceCommonSpawn4086_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceCommonSpawn4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCommonSpawn4086_State
 ply
 plx
 plp
 sec
 rtl
SourceCommonSpawn4086_Preflight:
.a16
.i16
 lda.l SourceCommonSpawn4086_Ready
 cmp #$B5E3
 beq SourceCommonSpawn4086_Far18
 jmp SourceCommonSpawn4086_PreflightBad
SourceCommonSpawn4086_Far18:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #1
 beq SourceCommonSpawn4086_Far19
 jmp SourceCommonSpawn4086_PreflightBad
SourceCommonSpawn4086_Far19:
.a16
.i16
 jsl SourceAI4086_CheckOwner
 bcc SourceCommonSpawn4086_Far20
 jmp SourceCommonSpawn4086_PreflightBad
SourceCommonSpawn4086_Far20:
.a16
.i16
 lda.l SourceIdle4086_Ready
 cmp #$B4F3
 beq SourceCommonSpawn4086_Far21
 jmp SourceCommonSpawn4086_PreflightBad
SourceCommonSpawn4086_Far21:
.a16
.i16
 clc
 rts
SourceCommonSpawn4086_PreflightBad:
.a16
.i16
 sec
 rts
