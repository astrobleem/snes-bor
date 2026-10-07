; Executable generic anything_walk thinker (semantic callback ID15).
; Source horizontal bounds and real no-event retirement. Explicit checked
; Q16.16 coordinate domain, no position wrap or source actor-name dispatch.
SourceAnythingWalk4086_Ready = $43BD24
SourceAnythingWalk4086_Status = $43BD26
SourceAnythingWalk4086_HRes = $43BD28
SourceAnythingWalk4086_Left = $43BD2A
SourceAnythingWalk4086_Right = $43BD2E
SourceAnythingWalk4086_View = $43BD32
SourceAnythingWalk4086_End = $43BD34
SourceAnythingWalk4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAnythingWalk4086_Ready
 cmp #$B5E4
 beq SourceAnythingWalk4086_Far1
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far1:
.a16
.i16
 lda.l SourceAnythingWalk4086_Status
 beq SourceAnythingWalk4086_Far2
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far2:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #2
 beq SourceAnythingWalk4086_Far3
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far3:
.a16
.i16
 jsl SourceAI4086_CheckOwner
 bcc SourceAnythingWalk4086_Far4
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far4:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $439000,x
 cmp #15
 beq SourceAnythingWalk4086_Far5
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far5:
.a16
.i16
 lda.l $439002,x
 beq SourceAnythingWalk4086_Far6
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far6:
.a16
.i16
 lda.l SourceAnythingWalk4086_HRes
 bne SourceAnythingWalk4086_Far7
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far7:
.a16
.i16
 cmp #32688
 bcc SourceAnythingWalk4086_Far8
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far8:
.a16
.i16
 clc
 adc #80
 tay
 lda.l VmSourceWorld_AdvanceX
 sta.l SourceAnythingWalk4086_Left
 sta.l SourceAnythingWalk4086_Right
 lda.l VmSourceWorld_AdvanceX+2
 sec
 sbc #80
 bvc SourceAnythingWalk4086_Far9
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far9:
.a16
.i16
 sta.l SourceAnythingWalk4086_Left+2
 tya
 clc
 adc.l VmSourceWorld_AdvanceX+2
 bvc SourceAnythingWalk4086_Far10
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far10:
.a16
.i16
 sta.l SourceAnythingWalk4086_Right+2
 lda.l SourceAI4086_View
 sta.l SourceAnythingWalk4086_View
 tax
 lda.l $410030,x
 cmp #2
 beq SourceAnythingWalk4086_Far11
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far11:
.a16
.i16
 lda.l $410032,x
 beq SourceAnythingWalk4086_Far12
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far12:
.a16
.i16
 lda.l $410036,x
 eor #$8000
 sta.l SourceAI4086_Temp
 lda.l SourceAnythingWalk4086_Left+2
 eor #$8000
 cmp.l SourceAI4086_Temp
 bcs SourceAnythingWalk4086_Far13
 jmp SourceAnythingWalk4086_RightCheck
SourceAnythingWalk4086_Far13:
.a16
.i16
 beq SourceAnythingWalk4086_Far14
 jmp SourceAnythingWalk4086_Kill
SourceAnythingWalk4086_Far14:
.a16
.i16
 lda.l $410034,x
 cmp.l SourceAnythingWalk4086_Left
 bcs SourceAnythingWalk4086_Far15
 jmp SourceAnythingWalk4086_Kill
SourceAnythingWalk4086_Far15:
.a16
.i16
SourceAnythingWalk4086_RightCheck:
.a16
.i16
 lda.l SourceAnythingWalk4086_Right+2
 eor #$8000
 cmp.l SourceAI4086_Temp
 bcs SourceAnythingWalk4086_Far16
 jmp SourceAnythingWalk4086_Kill
SourceAnythingWalk4086_Far16:
.a16
.i16
 beq SourceAnythingWalk4086_Far17
 jmp SourceAnythingWalk4086_Done
SourceAnythingWalk4086_Far17:
.a16
.i16
 lda.l SourceAnythingWalk4086_Right
 cmp.l $410034,x
 bcs SourceAnythingWalk4086_Far18
 jmp SourceAnythingWalk4086_Kill
SourceAnythingWalk4086_Far18:
.a16
.i16
 jmp SourceAnythingWalk4086_Done
SourceAnythingWalk4086_Kill:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceRetirement4086_Slot
 jsl SourceRetirement4086_ApplyNoEvents
 bcc SourceAnythingWalk4086_Far19
 jmp SourceAnythingWalk4086_Bad
SourceAnythingWalk4086_Far19:
.a16
.i16
SourceAnythingWalk4086_Done:
.a16
.i16
 lda #2
 sta.l SourceAnythingWalk4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceAnythingWalk4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAnythingWalk4086_Status
 ply
 plx
 plp
 sec
 rtl
