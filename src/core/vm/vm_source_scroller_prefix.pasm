; Exact source update_scroller prefix before queue/completion/camera work.
; Inputs retain full-width C truth values and unsigned advancetime. Source
; scrolldx/scrolldy are reset even on a freeze/time/completed early return.
; A=1 continue source scroller branch; A=0 early return. C=fault.
; Require the previous queue branch retired before opening another invocation.
SourceScrollerPrefix4086_Ready = $43BB82
SourceScrollerPrefix4086_State = $43BB84
SourceScrollerPrefix4086_AdvanceTime = $43BB86
SourceScrollerPrefix4086_FreezeAll = $43BB8A
SourceScrollerPrefix4086_Completed = $43BB8E
SourceScrollerPrefix4086_ScrollDX = $43BB92
SourceScrollerPrefix4086_ScrollDY = $43BB96
SourceScrollerPrefix4086_End = $43BB9A
SourceScrollerPrefix4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceScrollerPrefix4086_Ready
 cmp #$B5D7
 beq SourceScrollerPrefix4086_G1
 jmp SourceScrollerPrefix4086_Bad
SourceScrollerPrefix4086_G1:
.a16
.i16
 lda.l SourceStageProducer4086_Ready
 cmp #$B5D6
 beq SourceScrollerPrefix4086_G2
 jmp SourceScrollerPrefix4086_Bad
SourceScrollerPrefix4086_G2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceScrollerPrefix4086_G3
 jmp SourceScrollerPrefix4086_Bad
SourceScrollerPrefix4086_G3:
.a16
.i16
 lda.l VmSourceWorld_Level
 cmp #1
 beq SourceScrollerPrefix4086_G4
 jmp SourceScrollerPrefix4086_Bad
SourceScrollerPrefix4086_G4:
.a16
.i16
 lda.l SourceStageProducer4086_State
 beq SourceScrollerPrefix4086_PreviousDone
 cmp #4

 beq SourceScrollerPrefix4086_G5
 jmp SourceScrollerPrefix4086_Bad
SourceScrollerPrefix4086_G5:
.a16
.i16
SourceScrollerPrefix4086_PreviousDone:
.a16
.i16
 lda #0
 sta.l SourceScrollerPrefix4086_ScrollDX
 sta.l SourceScrollerPrefix4086_ScrollDX+2
 sta.l SourceScrollerPrefix4086_ScrollDY
 sta.l SourceScrollerPrefix4086_ScrollDY+2
 sta.l SourceStageProducer4086_Completed
 lda.l SourceScrollerPrefix4086_Completed
 ora.l SourceScrollerPrefix4086_Completed+2
 beq SourceScrollerPrefix4086_CompletionCopied
 lda #1
 sta.l SourceStageProducer4086_Completed
SourceScrollerPrefix4086_CompletionCopied:
.a16
.i16
 lda.l SourceScrollerPrefix4086_FreezeAll
 ora.l SourceScrollerPrefix4086_FreezeAll+2
 bne SourceScrollerPrefix4086_Early
 lda.l VmSourceWorld_Time+2
 cmp.l SourceScrollerPrefix4086_AdvanceTime+2
 bcc SourceScrollerPrefix4086_Early
 bne SourceScrollerPrefix4086_Advance
 lda.l VmSourceWorld_Time
 cmp.l SourceScrollerPrefix4086_AdvanceTime
 bcc SourceScrollerPrefix4086_Early
SourceScrollerPrefix4086_Advance:
.a16
.i16
 lda.l VmSourceWorld_Time
 sta.l SourceScrollerPrefix4086_AdvanceTime
 lda.l VmSourceWorld_Time+2
 sta.l SourceScrollerPrefix4086_AdvanceTime+2
 lda.l SourceStageProducer4086_Completed
 bne SourceScrollerPrefix4086_Early
 lda #0
 sta.l SourceStageProducer4086_State
 lda #2
 sta.l SourceScrollerPrefix4086_State
 lda #1
 bra SourceScrollerPrefix4086_Return
SourceScrollerPrefix4086_Early:
.a16
.i16
 lda #4
 sta.l SourceStageProducer4086_State
 sta.l SourceScrollerPrefix4086_State
 lda #0
SourceScrollerPrefix4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceScrollerPrefix4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceScrollerPrefix4086_State
 sta.l SourceStageProducer4086_State
 ply
 plx
 plp
 sec
 rtl
