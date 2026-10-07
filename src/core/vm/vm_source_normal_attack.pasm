; Pinned normal_attack ordered selector owner. Executable selector bodies are
; explicit requests: grab/upper/block/runattack/normalattack/jumpattack (1..6).
; Full32 response truth short-circuits and clears source running, without an
; inserted exists/dead test. Parent remains common_think ATTACK request 7.
SourceNormalAttack4086_Ready = $43BD68
SourceNormalAttack4086_State = $43BD6A ; 1..6 request,7 done,8 fault
SourceNormalAttack4086_Response = $43BD6C
SourceNormalAttack4086_Slot = $43BD70
SourceNormalAttack4086_Row = $43BD72
SourceNormalAttack4086_Result = $43BD74
SourceNormalAttack4086_End = $43BD76
SourceNormalAttack4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceNormalAttack4086_State
 beq SourceNormalAttack4086_Start
 cmp #7
 beq SourceNormalAttack4086_Start
 jmp SourceNormalAttack4086_Bad
SourceNormalAttack4086_Start:
.a16
.i16
 jsr SourceNormalAttack4086_Preflight
 bcc SourceNormalAttack4086_StartValid
 jmp SourceNormalAttack4086_Bad
SourceNormalAttack4086_StartValid:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceNormalAttack4086_Slot
 lda #0
 sta.l SourceNormalAttack4086_Result
 lda #1
 jmp SourceNormalAttack4086_Request
SourceNormalAttack4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 cmp.l SourceNormalAttack4086_State
 bne SourceNormalAttack4086_Bad
 cmp #1
 bcc SourceNormalAttack4086_Bad
 cmp #7
 bcs SourceNormalAttack4086_Bad
 jsr SourceNormalAttack4086_Preflight
 bcs SourceNormalAttack4086_Bad
 lda.l SourceNormalAttack4086_Slot
 cmp.l SourceAI4086_Slot
 bne SourceNormalAttack4086_Bad
 lda.l SourceNormalAttack4086_Response
 ora.l SourceNormalAttack4086_Response+2
 beq SourceNormalAttack4086_False
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 sta.l SourceNormalAttack4086_Row
 asl a
 clc
 adc.l SourceNormalAttack4086_Row
 tax
 lda #0
 sta.l SOURCE_ENTITY_AI_STATE+4,x
 sta.l SOURCE_ENTITY_AI_STATE+6,x
 lda #1
 sta.l SourceNormalAttack4086_Result
 jmp SourceNormalAttack4086_Done
SourceNormalAttack4086_False:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 cmp #6
 beq SourceNormalAttack4086_Done
 inc a
SourceNormalAttack4086_Request:
.a16
.i16
 sta.l SourceNormalAttack4086_State
 pha
 lda #0
 sta.l SourceNormalAttack4086_Response
 sta.l SourceNormalAttack4086_Response+2
 pla
 jmp SourceNormalAttack4086_Good
SourceNormalAttack4086_Done:
.a16
.i16
 lda #7
 sta.l SourceNormalAttack4086_State
 lda #0
SourceNormalAttack4086_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceNormalAttack4086_Bad:
.a16
.i16
 lda #8
 sta.l SourceNormalAttack4086_State
 ply
 plx
 plp
 sec
 rtl
SourceNormalAttack4086_Preflight:
.a16
.i16
 lda.l SourceNormalAttack4086_Ready
 cmp #$B5EB
 bne SourceNormalAttack4086_PreflightBad
 lda.l SourceCommonThink4086_State
 cmp #7
 bne SourceNormalAttack4086_PreflightBad
 jsl SourceCommonThink4086_CheckOwner
 bcs SourceNormalAttack4086_PreflightBad
 clc
 rts
SourceNormalAttack4086_PreflightBad:
.a16
.i16
 sec
 rts
