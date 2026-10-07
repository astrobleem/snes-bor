; Generic check_range numeric primitive. Explicit ACCEPTED_COMPAT_Q16_16.
; Input staging is not an entity binding. Bounds remain full signed32.
; Extended signed48 differences prevent Q16 endpoint overflow/wrap.
SourceCheckRange4086_Ready = $43BDE4
SourceCheckRange4086_Status = $43BDE6
SourceCheckRange4086_Present = $43BDE8
SourceCheckRange4086_Direction = $43BDEA
SourceCheckRange4086_Source = $43BDEE ; x,z,y,base Q16 signed32
SourceCheckRange4086_Target = $43BDFE
SourceCheckRange4086_Ranges = $43BE0E ; min/max for x,z,y,base signed32
SourceCheckRange4086_Result = $43BE2E ; boolean32
SourceCheckRange4086_Axis = $43BE32
SourceCheckRange4086_Left = $43BE34 ; signed48 operands
SourceCheckRange4086_Right = $43BE3A
SourceCheckRange4086_Difference = $43BE40
SourceCheckRange4086_End = $43BE46
SourceCheckRange4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCheckRange4086_Ready
 cmp #$B5F7
 beq SourceCheckRange4086_Lease
 jmp SourceCheckRange4086_Bad
SourceCheckRange4086_Lease:
.a16
.i16
 lda.l SourceCheckRange4086_Status
 beq SourceCheckRange4086_Start
 cmp #2
 beq SourceCheckRange4086_Start
 jmp SourceCheckRange4086_Bad
SourceCheckRange4086_Start:
.a16
.i16
 lda #1
 sta.l SourceCheckRange4086_Status
 lda.l SourceCheckRange4086_Present
 bne SourceCheckRange4086_PresentTarget
 jmp SourceCheckRange4086_False
SourceCheckRange4086_PresentTarget:
.a16
.i16
 lda #0
 sta.l SourceCheckRange4086_Axis
SourceCheckRange4086_Loop:
.a16
.i16
 lda.l SourceCheckRange4086_Axis
 asl a
 asl a
 tax
 lda.l SourceCheckRange4086_Target,x
 sta.l SourceCheckRange4086_Left
 lda.l SourceCheckRange4086_Target+2,x
 sta.l SourceCheckRange4086_Left+2
 lda.l SourceCheckRange4086_Left+2
 bpl SourceCheckRange4086_TargetPositive
 lda #$FFFF
 bra SourceCheckRange4086_TargetSign
SourceCheckRange4086_TargetPositive:
.a16
.i16
 lda #0
SourceCheckRange4086_TargetSign:
.a16
.i16
 sta.l SourceCheckRange4086_Left+4
 lda.l SourceCheckRange4086_Source,x
 sta.l SourceCheckRange4086_Right
 lda.l SourceCheckRange4086_Source+2,x
 sta.l SourceCheckRange4086_Right+2
 bpl SourceCheckRange4086_SourcePositive
 lda #$FFFF
 bra SourceCheckRange4086_SourceSign
SourceCheckRange4086_SourcePositive:
.a16
.i16
 lda #0
SourceCheckRange4086_SourceSign:
.a16
.i16
 sta.l SourceCheckRange4086_Right+4
 lda.l SourceCheckRange4086_Axis
 bne SourceCheckRange4086_Subtract
 ; X alone truncates TARGET first, not target minus self.
 lda.l SourceCheckRange4086_Left+4
 bpl SourceCheckRange4086_ClearXFraction
 lda.l SourceCheckRange4086_Left
 beq SourceCheckRange4086_ClearXFraction
 lda.l SourceCheckRange4086_Left+2
 clc
 adc #1
 sta.l SourceCheckRange4086_Left+2
 lda.l SourceCheckRange4086_Left+4
 adc #0
 sta.l SourceCheckRange4086_Left+4
SourceCheckRange4086_ClearXFraction:
.a16
.i16
 lda #0
 sta.l SourceCheckRange4086_Left
 lda.l SourceCheckRange4086_Direction+2
 bne SourceCheckRange4086_Swap
 lda.l SourceCheckRange4086_Direction
 cmp #1
 beq SourceCheckRange4086_Subtract
SourceCheckRange4086_Swap:
.a16
.i16
 ; Left-facing comparison uses self minus truncated target.
 ldx #4
SourceCheckRange4086_SwapWord:
.a16
.i16
 lda.l SourceCheckRange4086_Left,x
 tay
 lda.l SourceCheckRange4086_Right,x
 sta.l SourceCheckRange4086_Left,x
 tya
 sta.l SourceCheckRange4086_Right,x
 dex
 dex
 bpl SourceCheckRange4086_SwapWord
SourceCheckRange4086_Subtract:
.a16
.i16
 lda.l SourceCheckRange4086_Left
 sec
 sbc.l SourceCheckRange4086_Right
 sta.l SourceCheckRange4086_Difference
 lda.l SourceCheckRange4086_Left+2
 sbc.l SourceCheckRange4086_Right+2
 sta.l SourceCheckRange4086_Difference+2
 lda.l SourceCheckRange4086_Left+4
 sbc.l SourceCheckRange4086_Right+4
 sta.l SourceCheckRange4086_Difference+4
 lda.l SourceCheckRange4086_Axis
 beq SourceCheckRange4086_Compare
 ; Other axes truncate the extended difference toward zero.
 lda.l SourceCheckRange4086_Difference+4
 bpl SourceCheckRange4086_ClearDifferenceFraction
 lda.l SourceCheckRange4086_Difference
 beq SourceCheckRange4086_ClearDifferenceFraction
 lda.l SourceCheckRange4086_Difference+2
 clc
 adc #1
 sta.l SourceCheckRange4086_Difference+2
 lda.l SourceCheckRange4086_Difference+4
 adc #0
 sta.l SourceCheckRange4086_Difference+4
SourceCheckRange4086_ClearDifferenceFraction:
.a16
.i16
 lda #0
 sta.l SourceCheckRange4086_Difference
SourceCheckRange4086_Compare:
.a16
.i16
 lda.l SourceCheckRange4086_Axis
 asl a
 asl a
 asl a
 tax
 ; Signed high word, then unsigned middle/low. Min's low word is zero.
 lda.l SourceCheckRange4086_Ranges+2,x
 eor #$8000
 sta.l SourceCheckRange4086_Left
 lda.l SourceCheckRange4086_Difference+4
 eor #$8000
 cmp.l SourceCheckRange4086_Left
 bcc SourceCheckRange4086_False
 bne SourceCheckRange4086_Maximum
 lda.l SourceCheckRange4086_Difference+2
 cmp.l SourceCheckRange4086_Ranges,x
 bcc SourceCheckRange4086_False
SourceCheckRange4086_Maximum:
.a16
.i16
 lda.l SourceCheckRange4086_Ranges+6,x
 eor #$8000
 sta.l SourceCheckRange4086_Left
 lda.l SourceCheckRange4086_Difference+4
 eor #$8000
 cmp.l SourceCheckRange4086_Left
 bcc SourceCheckRange4086_Next
 bne SourceCheckRange4086_False
 lda.l SourceCheckRange4086_Difference+2
 cmp.l SourceCheckRange4086_Ranges+4,x
 bcc SourceCheckRange4086_Next
 bne SourceCheckRange4086_False
 lda.l SourceCheckRange4086_Difference
 bne SourceCheckRange4086_False
SourceCheckRange4086_Next:
.a16
.i16
 lda.l SourceCheckRange4086_Axis
 inc a
 sta.l SourceCheckRange4086_Axis
 cmp #4
 bcs SourceCheckRange4086_True
 jmp SourceCheckRange4086_Loop
SourceCheckRange4086_True:
.a16
.i16
 lda #1
 bra SourceCheckRange4086_ResultValue
SourceCheckRange4086_False:
.a16
.i16
 lda #0
SourceCheckRange4086_ResultValue:
.a16
.i16
 sta.l SourceCheckRange4086_Result
 lda #0
 sta.l SourceCheckRange4086_Result+2
 lda #2
 sta.l SourceCheckRange4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceCheckRange4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCheckRange4086_Status
 ply
 plx
 plp
 sec
 rtl
