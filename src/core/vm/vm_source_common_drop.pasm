; Actual common_drop action ID5. Q16 inair is the existing explicit
; ACCEPTED_COMPAT predicate; arbitrary binary32 threshold equivalence unclaimed.
; Preflight all retirement guards before source landing writes.
SourceCommonDrop4086_Ready = $43BD34
SourceCommonDrop4086_Status = $43BD36
SourceCommonDrop4086_End = $43BD38
SourceCommonDrop4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCommonDrop4086_Ready
 cmp #$B5E5
 beq SourceCommonDrop4086_Far1
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far1:
.a16
.i16
 lda.l SourceCommonDrop4086_Status
 beq SourceCommonDrop4086_Far2
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far2:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #1
 beq SourceCommonDrop4086_Far3
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far3:
.a16
.i16
 jsl SourceAI4086_CheckOwner
 bcc SourceCommonDrop4086_Far4
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far4:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $43900C,x
 cmp #5
 beq SourceCommonDrop4086_Far5
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far5:
.a16
.i16
 lda.l $43900E,x
 beq SourceCommonDrop4086_Far6
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far6:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410008,x
 cmp #2
 beq SourceCommonDrop4086_Far7
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far7:
.a16
.i16
 lda.l $41000A,x
 beq SourceCommonDrop4086_Far8
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far8:
.a16
.i16
 lda.l $410020,x
 cmp #1
 beq SourceCommonDrop4086_Far9
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far9:
.a16
.i16
 lda.l $410022,x
 beq SourceCommonDrop4086_Far10
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far10:
.a16
.i16
 lda.l $41000C,x
 sta.l SourceModelEntityCopy4086_Lo
 lda.l $41000E,x
 sta.l SourceModelEntityCopy4086_Hi
 lda.l SourceAI4086_Side
 tax
 lda.l $416830,x
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l $416832,x
 sta.l SourceDefaultPlayer4086_InvHi
 jsl SourceInAir4086_Q16Compatibility
 ora #0
 beq SourceCommonDrop4086_Far11
 jmp SourceCommonDrop4086_Done
SourceCommonDrop4086_Far11:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410026,x
 bpl SourceCommonDrop4086_Far12
 jmp SourceCommonDrop4086_KillPreflight
SourceCommonDrop4086_Far12:
.a16
.i16
 ora.l $410024,x
 bne SourceCommonDrop4086_Far13
 jmp SourceCommonDrop4086_KillPreflight
SourceCommonDrop4086_Far13:
.a16
.i16
 jmp SourceCommonDrop4086_Land
SourceCommonDrop4086_KillPreflight:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceRetirement4086_Slot
 jsl SourceRetirement4086_PreflightNoEvents
 bcc SourceCommonDrop4086_Far14
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far14:
.a16
.i16
SourceCommonDrop4086_Land:
.a16
.i16
 lda.l SourceAI4086_Flags
 tax
 lda #1
 sta.l $43EB00,x
 lda #0
 sta.l $43EB02,x
 lda.l SourceAI4086_Life
 tax
 lda #0
 sta.l $43900C,x
 sta.l $43900E,x
 lda.l SourceAI4086_View
 tax
 lda.l $410026,x
 bpl SourceCommonDrop4086_Far15
 jmp SourceCommonDrop4086_Kill
SourceCommonDrop4086_Far15:
.a16
.i16
 ora.l $410024,x
 beq SourceCommonDrop4086_Far16
 jmp SourceCommonDrop4086_Done
SourceCommonDrop4086_Far16:
.a16
.i16
SourceCommonDrop4086_Kill:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceRetirement4086_Slot
 jsl SourceRetirement4086_ApplyNoEvents
 bcc SourceCommonDrop4086_Far17
 jmp SourceCommonDrop4086_Bad
SourceCommonDrop4086_Far17:
.a16
.i16
SourceCommonDrop4086_Done:
.a16
.i16
 lda #2
 sta.l SourceCommonDrop4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceCommonDrop4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCommonDrop4086_Status
 ply
 plx
 plp
 sec
 rtl
