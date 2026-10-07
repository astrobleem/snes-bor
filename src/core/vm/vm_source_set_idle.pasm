; Generic DEFAULT_IDLE_ONLY set_idle, including existing animation transitions.
; Immutable registry admission already rejects special idle/range/subtype needs.
; Caller supplies SourceIdle.Slot. A=1 requires actual frame-zero owner; A=0 done.
SourceSetIdle4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceAnimationInit4086_CheckIdle
 bcc SourceSetIdle4086_InitIdle
 jmp SourceSetIdle4086_Bad
SourceSetIdle4086_InitIdle:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceSetIdle4086_FrameIdle
 jmp SourceSetIdle4086_Bad
SourceSetIdle4086_FrameIdle:
.a16
.i16
 lda.l SourceIdle4086_Ready
 cmp #$B4F3
 beq SourceSetIdle4086_Lease
 jmp SourceSetIdle4086_Bad
SourceSetIdle4086_Lease:
.a16
.i16
 lda.l SourceIdle4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda #0
 sta.l SourceAnimationInit4086_Number
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcc SourceSetIdle4086_Resolved
 jmp SourceSetIdle4086_Bad
SourceSetIdle4086_Resolved:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceSetIdle4086_Bad
 lda.l SourceAnimationInit4086_Count
 beq SourceSetIdle4086_Bad
 jsl SourceIdle4086_Prepare
 bcs SourceSetIdle4086_Bad
 jsl SourceAnimationInit4086_Begin
 bcs SourceSetIdle4086_Bad
 lda.l SourceAnimationInit4086_State
 cmp #1
 beq SourceSetIdle4086_Pending
 cmp #2
 bne SourceSetIdle4086_Bad
 lda #0
 bra SourceSetIdle4086_Good
SourceSetIdle4086_Pending:
.a16
.i16
 lda #1
SourceSetIdle4086_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceSetIdle4086_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
