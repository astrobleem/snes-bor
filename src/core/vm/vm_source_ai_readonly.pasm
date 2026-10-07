; Actual ai_check_warp early-return paths and complete ai_check_busy.
; Full FOLLOW+parent distance/action path explicitly requires another backend.
; No source actor-name dispatch; full DWORD idling and physical link truth.
SourceAIReadonly4086_Ready = $43BD48
SourceAIReadonly4086_Status = $43BD4A
SourceAIReadonly4086_Relation = $43BD4C
SourceAIReadonly4086_Result = $43BD4E
SourceAIReadonly4086_End = $43BD50
SourceAIReadonly4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAIReadonly4086_Ready
 cmp #$B5E8
 beq SourceAIReadonly4086_Far1
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Far1:
.a16
.i16
 lda.l SourceAIReadonly4086_Status
 beq SourceAIReadonly4086_Far2
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Far2:
.a16
.i16
 lda.l SourceRetirement4086_Ready
 cmp #$B4F8
 beq SourceAIReadonly4086_Far3
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Far3:
.a16
.i16
 jsl SourceCommonThink4086_CheckOwner
 bcc SourceAIReadonly4086_Far4
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Far4:
.a16
.i16
 lda.l SourceCommonThink4086_State
 cmp #1
 bne SourceAIReadonly4086_Far5
 jmp SourceAIReadonly4086_Warp
SourceAIReadonly4086_Far5:
.a16
.i16
 cmp #6
 bne SourceAIReadonly4086_Far6
 jmp SourceAIReadonly4086_Busy
SourceAIReadonly4086_Far6:
.a16
.i16
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Warp:
.a16
.i16
 jsr SourceAIReadonly4086_Link
 ora #0
 beq SourceAIReadonly4086_Far7
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Far7:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $439032,x
 beq SourceAIReadonly4086_Far8
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Far8:
.a16
.i16
 lda.l $439030,x
 cmp #10
 beq SourceAIReadonly4086_Far9
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Far9:
.a16
.i16
 lda.l SourceAIReadonly4086_Relation
 tax
 lda.l $409000,x
 ora.l $409002,x
 bne SourceAIReadonly4086_Far10
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Far10:
.a16
.i16
 ; A true FOLLOW+parent needs range/pointer/distance and npc_warp semantics.
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Busy:
.a16
.i16
 jsr SourceAIReadonly4086_Link
 ora #0
 beq SourceAIReadonly4086_Far11
 jmp SourceAIReadonly4086_True
SourceAIReadonly4086_Far11:
.a16
.i16
 lda.l SourceAI4086_Flags
 tax
 lda.l $43EB00,x
 ora.l $43EB02,x
 beq SourceAIReadonly4086_Far12
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Far12:
.a16
.i16
SourceAIReadonly4086_True:
.a16
.i16
 lda #1
 jmp SourceAIReadonly4086_Publish
SourceAIReadonly4086_False:
.a16
.i16
 lda #0
SourceAIReadonly4086_Publish:
.a16
.i16
 sta.l SourceAIReadonly4086_Result
 sta.l SourceCommonThink4086_Response
 lda #0
 sta.l SourceCommonThink4086_Response+2
 lda #2
 sta.l SourceAIReadonly4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceAIReadonly4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAIReadonly4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceAIReadonly4086_Link:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceAIReadonly4086_Relation
 tax
 lda.l $40901C,x
 ora.l $40901E,x
 rts
