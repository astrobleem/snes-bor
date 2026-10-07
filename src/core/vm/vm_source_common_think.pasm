; Exact common_think ordered short-circuit owner. Handler bodies remain
; explicit services; this owner alone is not enemy AI gameplay admission.
; State 1..8 = warp/lie/grabbed/grab/escape/busy/attack/move,9 complete,10 fault.
; Continue A must match pending state; Response is full signed32 truth.
SourceCommonThink4086_Ready = $43BD3E
SourceCommonThink4086_State = $43BD40
SourceCommonThink4086_Response = $43BD42
SourceCommonThink4086_Slot = $43BD46
SourceCommonThink4086_End = $43BD48
SourceCommonThink4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCommonThink4086_State
 bne SourceCommonThink4086_Far1
 jmp SourceCommonThink4086_Start
SourceCommonThink4086_Far1:
.a16
.i16
 cmp #9
 beq SourceCommonThink4086_Far2
 jmp SourceCommonThink4086_Bad
SourceCommonThink4086_Far2:
.a16
.i16
SourceCommonThink4086_Start:
.a16
.i16
 jsr SourceCommonThink4086_Preflight
 bcc SourceCommonThink4086_Far3
 jmp SourceCommonThink4086_Bad
SourceCommonThink4086_Far3:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $439000,x
 cmp #6
 beq SourceCommonThink4086_Far15
 jmp SourceCommonThink4086_Bad
SourceCommonThink4086_Far15:
.a16
.i16
 lda.l $439002,x
 beq SourceCommonThink4086_Far16
 jmp SourceCommonThink4086_Bad
SourceCommonThink4086_Far16:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceCommonThink4086_Slot
 lda.l SourceAI4086_Life
 tax
 lda.l $439014,x
 ora.l $439016,x
 beq SourceCommonThink4086_Far4
 jmp SourceCommonThink4086_Done
SourceCommonThink4086_Far4:
.a16
.i16
 lda #1
 jmp SourceCommonThink4086_Request
SourceCommonThink4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 cmp.l SourceCommonThink4086_State
 beq SourceCommonThink4086_Far5
 jmp SourceCommonThink4086_Bad
SourceCommonThink4086_Far5:
.a16
.i16
 cmp #1
 bcs SourceCommonThink4086_Far6
 jmp SourceCommonThink4086_Bad
SourceCommonThink4086_Far6:
.a16
.i16
 cmp #9
 bcc SourceCommonThink4086_Far7
 jmp SourceCommonThink4086_Bad
SourceCommonThink4086_Far7:
.a16
.i16
 jsr SourceCommonThink4086_Preflight
 bcc SourceCommonThink4086_Far8
 jmp SourceCommonThink4086_Bad
SourceCommonThink4086_Far8:
.a16
.i16
 lda.l SourceAI4086_Slot
 cmp.l SourceCommonThink4086_Slot
 beq SourceCommonThink4086_Far9
 jmp SourceCommonThink4086_Bad
SourceCommonThink4086_Far9:
.a16
.i16
 lda.l SourceCommonThink4086_State
 cmp #8
 bne SourceCommonThink4086_Far10
 jmp SourceCommonThink4086_Done
SourceCommonThink4086_Far10:
.a16
.i16
 lda.l SourceCommonThink4086_Response
 ora.l SourceCommonThink4086_Response+2
 beq SourceCommonThink4086_Far11
 jmp SourceCommonThink4086_Done
SourceCommonThink4086_Far11:
.a16
.i16
 lda.l SourceCommonThink4086_State
 inc a
SourceCommonThink4086_Request:
.a16
.i16
 sta.l SourceCommonThink4086_State
 pha
 lda #0
 sta.l SourceCommonThink4086_Response
 sta.l SourceCommonThink4086_Response+2
 pla
 jmp SourceCommonThink4086_Good
SourceCommonThink4086_Done:
.a16
.i16
 lda #9
 sta.l SourceCommonThink4086_State
 lda #0
SourceCommonThink4086_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceCommonThink4086_Bad:
.a16
.i16
 lda #10
 sta.l SourceCommonThink4086_State
 ply
 plx
 plp
 sec
 rtl
SourceCommonThink4086_Preflight:
.a16
.i16
 lda.l SourceCommonThink4086_Ready
 cmp #$B5E7
 beq SourceCommonThink4086_Far12
 jmp SourceCommonThink4086_PreflightBad
SourceCommonThink4086_Far12:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #2
 beq SourceCommonThink4086_Far13
 jmp SourceCommonThink4086_PreflightBad
SourceCommonThink4086_Far13:
.a16
.i16
 jsl SourceAI4086_CheckOwner
 bcc SourceCommonThink4086_Far14
 jmp SourceCommonThink4086_PreflightBad
SourceCommonThink4086_Far14:
.a16
.i16
 clc
 rts
SourceCommonThink4086_PreflightBad:
.a16
.i16
 sec
 rts
