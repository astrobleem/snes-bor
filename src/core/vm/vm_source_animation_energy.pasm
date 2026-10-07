; Compiler-validated immutable B4AE energy-cost table. A=actual animation handle.
; Does not resolve a role through an actor/model name or a birth cache.
SourceAnimationEnergy4086_Ready = $43BE94
SourceAnimationEnergy4086_Bank = $43BE96
SourceAnimationEnergy4086_Bytes = $43BE98
SourceAnimationEnergy4086_Handle = $43BE9A
SourceAnimationEnergy4086_Status = $43BE9C
SourceAnimationEnergy4086_End = $43BE9E
SourceAnimationEnergy4086_Query:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 sta.l SourceAnimationEnergy4086_Handle
 tsc
 sec
 sbc #8
 tcs
 inc a
 tcd
 lda.l SourceAnimationEnergy4086_Ready
 cmp #$B5FC
 beq SourceAnimationEnergy4086_Lease
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_Lease:
.a16
.i16
 lda.l SourceAnimationEnergy4086_Status
 beq SourceAnimationEnergy4086_Start
 cmp #2
 beq SourceAnimationEnergy4086_Start
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_Start:
.a16
.i16
 lda #1
 sta.l SourceAnimationEnergy4086_Status
 lda.l SourceAnimationEnergy4086_Bank
 cmp #64
 bcc SourceAnimationEnergy4086_BankOK
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_BankOK:
.a16
.i16
 sta $02
 lda #$8000
 sta $00
 lda.l SourceAnimationEnergy4086_Bytes
 cmp #32
 bcs SourceAnimationEnergy4086_SizeMin
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_SizeMin:
.a16
.i16
 cmp #$8001
 bcc SourceAnimationEnergy4086_Header
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_Header:
.a16
.i16
 ldy #0
 lda [$00],y
 cmp #$3442
 beq SourceAnimationEnergy4086_Magic1
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_Magic1:
.a16
.i16
 ldy #2
 lda [$00],y
 cmp #$4541
 beq SourceAnimationEnergy4086_Magic2
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_Magic2:
.a16
.i16
 ldy #4
 lda [$00],y
 cmp #1
 beq SourceAnimationEnergy4086_Version
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_Version:
.a16
.i16
 ldy #8
 lda [$00],y
 cmp #16
 beq SourceAnimationEnergy4086_Stride
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_Stride:
.a16
.i16
 ldy #10
 lda [$00],y
 iny
 iny
 ora [$00],y
 iny
 iny
 ora [$00],y
 beq SourceAnimationEnergy4086_Reserved
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_Reserved:
.a16
.i16
 ldy #6
 lda [$00],y
 bne SourceAnimationEnergy4086_CountMin
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_CountMin:
.a16
.i16
 cmp #2048
 bcc SourceAnimationEnergy4086_Count
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_Count:
.a16
.i16
 sta $04
 asl a
 asl a
 asl a
 asl a
 clc
 adc #16
 cmp.l SourceAnimationEnergy4086_Bytes
 beq SourceAnimationEnergy4086_Extent
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_Extent:
.a16
.i16
 lda.l SourceAnimationEnergy4086_Handle
 bne SourceAnimationEnergy4086_HandleMin
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_HandleMin:
.a16
.i16
 cmp $04
 bcc SourceAnimationEnergy4086_HandleOK
 beq SourceAnimationEnergy4086_HandleOK
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_HandleOK:
.a16
.i16
 dec a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #16
 tay
 tya
 sta $06
 clc
 adc #12
 tay
 lda [$00],y
 iny
 iny
 ora [$00],y
 beq SourceAnimationEnergy4086_RowReserved
 jmp SourceAnimationEnergy4086_Bad
SourceAnimationEnergy4086_RowReserved:
.a16
.i16
 ldy $06
 ldx #0
SourceAnimationEnergy4086_Copy:
.a16
.i16
 lda [$00],y
 sta.l SourceCheckEnergy4086_Cost,x
 iny
 iny
 inx
 inx
 cpx #12
 bcc SourceAnimationEnergy4086_Copy
 lda #2
 sta.l SourceAnimationEnergy4086_Status
 tsc
 clc
 adc #8
 tcs
 pld
 ply
 plx
 plp
 clc
 rtl
SourceAnimationEnergy4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAnimationEnergy4086_Status
 tsc
 clc
 adc #8
 tcs
 pld
 ply
 plx
 plp
 sec
 rtl
