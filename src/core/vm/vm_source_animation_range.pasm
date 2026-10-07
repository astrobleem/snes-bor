; Compiler-validated immutable B4AR range table. A=actual animation handle.
; Does not resolve a role through an actor/model name or a birth cache.
SourceAnimationRange4086_Ready = $43BE46
SourceAnimationRange4086_Bank = $43BE48
SourceAnimationRange4086_Bytes = $43BE4A
SourceAnimationRange4086_Handle = $43BE4C
SourceAnimationRange4086_Status = $43BE4E
SourceAnimationRange4086_End = $43BE50
SourceAnimationRange4086_Query:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 sta.l SourceAnimationRange4086_Handle
 tsc
 sec
 sbc #8
 tcs
 inc a
 tcd
 lda.l SourceAnimationRange4086_Ready
 cmp #$B5F8
 beq SourceAnimationRange4086_Lease
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_Lease:
.a16
.i16
 lda.l SourceAnimationRange4086_Status
 beq SourceAnimationRange4086_Start
 cmp #2
 beq SourceAnimationRange4086_Start
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_Start:
.a16
.i16
 lda #1
 sta.l SourceAnimationRange4086_Status
 lda.l SourceAnimationRange4086_Bank
 cmp #64
 bcc SourceAnimationRange4086_BankOK
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_BankOK:
.a16
.i16
 sta $02
 lda #$8000
 sta $00
 lda.l SourceAnimationRange4086_Bytes
 cmp #48
 bcs SourceAnimationRange4086_SizeMin
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_SizeMin:
.a16
.i16
 cmp #$8001
 bcc SourceAnimationRange4086_Header
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_Header:
.a16
.i16
 ldy #0
 lda [$00],y
 cmp #$3442
 beq SourceAnimationRange4086_Magic1
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_Magic1:
.a16
.i16
 ldy #2
 lda [$00],y
 cmp #$5241
 beq SourceAnimationRange4086_Magic2
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_Magic2:
.a16
.i16
 ldy #4
 lda [$00],y
 cmp #1
 beq SourceAnimationRange4086_Version
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_Version:
.a16
.i16
 ldy #8
 lda [$00],y
 cmp #32
 beq SourceAnimationRange4086_Stride
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_Stride:
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
 beq SourceAnimationRange4086_Reserved
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_Reserved:
.a16
.i16
 ldy #6
 lda [$00],y
 bne SourceAnimationRange4086_CountMin
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_CountMin:
.a16
.i16
 cmp #1024
 bcc SourceAnimationRange4086_Count
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_Count:
.a16
.i16
 sta $04
 asl a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #16
 cmp.l SourceAnimationRange4086_Bytes
 beq SourceAnimationRange4086_Extent
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_Extent:
.a16
.i16
 lda.l SourceAnimationRange4086_Handle
 bne SourceAnimationRange4086_HandleMin
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_HandleMin:
.a16
.i16
 cmp $04
 bcc SourceAnimationRange4086_HandleOK
 beq SourceAnimationRange4086_HandleOK
 jmp SourceAnimationRange4086_Bad
SourceAnimationRange4086_HandleOK:
.a16
.i16
 dec a
 asl a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #16
 tay
 ldx #0
SourceAnimationRange4086_Copy:
.a16
.i16
 lda [$00],y
 sta.l SourceCheckRange4086_Ranges,x
 iny
 iny
 inx
 inx
 cpx #32
 bcc SourceAnimationRange4086_Copy
 lda #2
 sta.l SourceAnimationRange4086_Status
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
SourceAnimationRange4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAnimationRange4086_Status
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
