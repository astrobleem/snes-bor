; Source update_scroller WAIT release after queue retirement, before no-player return.
; Full signed noreset and signed timer; reject C signed multiplication overflow.
; A=1 released, A=0 unchanged, C=fault. Physical entities are readonly.
SourceWait4086_Ready = $43BBAA
SourceWait4086_Status = $43BBAC
SourceWait4086_NoReset = $43BBAE
SourceWait4086_SetTime = $43BBB2
SourceWait4086_TimeLeft = $43BBB6
SourceWait4086_Multiplicand = $43BBBA
SourceWait4086_Product = $43BBBE
SourceWait4086_End = $43BBC2
SourceWait4086_Release:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceWait4086_Ready
 cmp #$B5D9
 beq SourceWait4086_G1
 jmp SourceWait4086_Bad
SourceWait4086_G1:
.a16
.i16
 lda.l SourceScrollerPrefix4086_Ready
 cmp #$B5D7
 beq SourceWait4086_G2
 jmp SourceWait4086_Bad
SourceWait4086_G2:
.a16
.i16
 lda.l SourceScrollerPrefix4086_State
 cmp #2
 beq SourceWait4086_G3
 jmp SourceWait4086_Bad
SourceWait4086_G3:
.a16
.i16
 lda.l SourceStageProducer4086_Ready
 cmp #$B5D6
 beq SourceWait4086_G4
 jmp SourceWait4086_Bad
SourceWait4086_G4:
.a16
.i16
 lda.l SourceStageProducer4086_State
 cmp #4
 beq SourceWait4086_G5
 jmp SourceWait4086_Bad
SourceWait4086_G5:
.a16
.i16
 lda #2
 jsl SourceCountEntities4086_Count
 bcc SourceWait4086_CountOK
 jmp SourceWait4086_Bad
SourceWait4086_CountOK:
.a16
.i16
 ora #0 ; count helper preserves caller flags; test its returned A explicitly
 beq SourceWait4086_NoEnemy
 jmp SourceWait4086_Unchanged
SourceWait4086_NoEnemy:
.a16
.i16
 lda.l SourceStageProducer4086_Waiting
 bne SourceWait4086_Waiting
 jmp SourceWait4086_Unchanged
SourceWait4086_Waiting:
.a16
.i16
 lda.l SourceWait4086_NoReset+2
 bmi SourceWait4086_Reset
 beq SourceWait4086_NoResetLow
 jmp SourceWait4086_ReleaseOnly
SourceWait4086_NoResetLow:
.a16
.i16
 lda.l SourceWait4086_NoReset
 cmp #2
 bcc SourceWait4086_Reset
 jmp SourceWait4086_ReleaseOnly
SourceWait4086_Reset:
.a16
.i16
 lda.l SourceWait4086_SetTime+2
 bmi SourceWait4086_Negative
 cmp #$0051
 bcc SourceWait4086_Multiply
 bne SourceWait4086_Overflow
 lda.l SourceWait4086_SetTime
 cmp #$EB86
 bcc SourceWait4086_Multiply
 bra SourceWait4086_Overflow
SourceWait4086_Negative:
.a16
.i16
 cmp #$FFAE
 bcc SourceWait4086_Overflow
 bne SourceWait4086_Multiply
 lda.l SourceWait4086_SetTime
 cmp #$147B
 bcs SourceWait4086_Multiply
SourceWait4086_Overflow:
.a16
.i16
 jmp SourceWait4086_Bad
SourceWait4086_Multiply:
.a16
.i16
 lda.l SourceWait4086_SetTime
 sta.l SourceWait4086_Multiplicand
 lda.l SourceWait4086_SetTime+2
 sta.l SourceWait4086_Multiplicand+2
 lda #0
 sta.l SourceWait4086_Product
 sta.l SourceWait4086_Product+2
 ldy #400
SourceWait4086_MultiplyLoop:
.a16
.i16
 tya
 lsr a
 tay
 bcc SourceWait4086_Shift
 lda.l SourceWait4086_Product
 clc
 adc.l SourceWait4086_Multiplicand
 sta.l SourceWait4086_Product
 lda.l SourceWait4086_Product+2
 adc.l SourceWait4086_Multiplicand+2
 sta.l SourceWait4086_Product+2
SourceWait4086_Shift:
.a16
.i16
 lda.l SourceWait4086_Multiplicand
 asl a
 sta.l SourceWait4086_Multiplicand
 lda.l SourceWait4086_Multiplicand+2
 rol a
 sta.l SourceWait4086_Multiplicand+2
 tya
 bne SourceWait4086_MultiplyLoop
 lda.l SourceWait4086_Product
 sta.l SourceWait4086_TimeLeft
 lda.l SourceWait4086_Product+2
 sta.l SourceWait4086_TimeLeft+2
SourceWait4086_ReleaseOnly:
.a16
.i16
 lda #0
 sta.l SourceStageProducer4086_Waiting
 lda.l VmSourceWorld_Time
 clc
 adc #600
 sta.l SourceStageProducer4086_GoTime
 lda.l VmSourceWorld_Time+2
 adc #0
 sta.l SourceStageProducer4086_GoTime+2
 lda #1
 bra SourceWait4086_Done
SourceWait4086_Unchanged:
.a16
.i16
 lda #0
SourceWait4086_Done:
.a16
.i16
 pha
 lda #2
 sta.l SourceWait4086_Status
 pla
 ply
 plx
 plp
 clc
 rtl
SourceWait4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceWait4086_Status
 sta.l SourceStageProducer4086_State
 ply
 plx
 plp
 sec
 rtl
