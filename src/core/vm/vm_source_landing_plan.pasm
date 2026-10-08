; B625 immutable B4LP identity-bound landing plan lookup. No actor mutation.
SourceLandingPlan4086_Ready = $41FFC2
SourceLandingPlan4086_Status = $41FFC4
SourceLandingPlan4086_Base = $41FFC6
SourceLandingPlan4086_Bank = $41FFC8
SourceLandingPlan4086_Bytes = $41FFCA
SourceLandingPlan4086_Animations = $41FFCC
SourceLandingPlan4086_Handle = $41FFCE
SourceLandingPlan4086_Model = $41FFD0
SourceLandingPlan4086_Bounce = $41FFD2
SourceLandingPlan4086_ModelBounce = $41FFD6
SourceLandingPlan4086_Noquake = $41FFDA
SourceLandingPlan4086_Temp = $41FFDE
SourceLandingPlan4086_Row = $41FFE0
SourceLandingPlan4086_Scratch = $41FFE2
SourceLandingPlan4086_End = $41FFEE
SourceLandingPlan4086_Query:
.a16
.i16
 php
 rep #$38
 pha
 phx
 phy
 lda.l SourceLandingPlan4086_Ready
 cmp #$B625
 beq SourceLandingPlan4086_Guard1
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard1:
.a16
.i16
 lda.l SourceLandingPlan4086_Status
 beq SourceLandingPlan4086_Guard2
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard2:
.a16
.i16
 lda.l SourceLandingPlan4086_Bank
 and #$FF00
 beq SourceLandingPlan4086_Guard3
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard3:
.a16
.i16
 lda.l SourceLandingPlan4086_Bank
 cmp #$40
 bcc SourceLandingPlan4086_RomBank
 cmp #$80

 bcs SourceLandingPlan4086_Guard4
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard4:
.a16
.i16
SourceLandingPlan4086_RomBank:
.a16
.i16
 lda.l SourceLandingPlan4086_Animations
 bne SourceLandingPlan4086_Guard5
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard5:
.a16
.i16
 cmp #129
 bcc SourceLandingPlan4086_Guard6
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard6:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 clc
 adc #16
 cmp.l SourceLandingPlan4086_Bytes
 beq SourceLandingPlan4086_Guard7
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard7:
.a16
.i16
 lda.l SourceLandingPlan4086_Base
 cmp #$8000
 bcs SourceLandingPlan4086_Guard8
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard8:
.a16
.i16
 cmp #$FFF1
 bcc SourceLandingPlan4086_Guard9
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard9:
.a16
.i16
 clc
 adc.l SourceLandingPlan4086_Bytes
 bcc SourceLandingPlan4086_SpanValid
 cmp #0
 beq SourceLandingPlan4086_Guard10
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard10:
.a16
.i16
SourceLandingPlan4086_SpanValid:
.a16
.i16
 lda.l SourceLandingPlan4086_Base
 tax
 jsr SourceLandingPlan4086_Read
 cmp #$3442
 beq SourceLandingPlan4086_Guard11
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard11:
.a16
.i16
 inx
 inx
 jsr SourceLandingPlan4086_Read
 cmp #$504C
 beq SourceLandingPlan4086_Guard12
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard12:
.a16
.i16
 inx
 inx
 jsr SourceLandingPlan4086_Read
 cmp #1
 beq SourceLandingPlan4086_Guard13
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard13:
.a16
.i16
 inx
 inx
 jsr SourceLandingPlan4086_Read
 cmp.l SourceLandingPlan4086_Animations
 beq SourceLandingPlan4086_Guard14
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard14:
.a16
.i16
 inx
 inx
 jsr SourceLandingPlan4086_Read
 cmp #16
 beq SourceLandingPlan4086_Guard15
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard15:
.a16
.i16
 inx
 inx
 jsr SourceLandingPlan4086_Read
 cmp #0
 beq SourceLandingPlan4086_Guard16
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard16:
.a16
.i16
 inx
 inx
 jsr SourceLandingPlan4086_Read
 cmp #0
 beq SourceLandingPlan4086_Guard17
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard17:
.a16
.i16
 inx
 inx
 jsr SourceLandingPlan4086_Read
 cmp #0
 beq SourceLandingPlan4086_Guard18
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard18:
.a16
.i16
 inx
 inx
 lda.l SourceLandingPlan4086_Handle
 bne SourceLandingPlan4086_Guard19
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard19:
.a16
.i16
 cmp.l SourceLandingPlan4086_Animations
 beq SourceLandingPlan4086_HandleValid

 bcc SourceLandingPlan4086_Guard20
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard20:
.a16
.i16
SourceLandingPlan4086_HandleValid:
.a16
.i16
 dec a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #16
 clc
 adc.l SourceLandingPlan4086_Base
 tax
 sta.l SourceLandingPlan4086_Row
 jsr SourceLandingPlan4086_Read
 cmp.l SourceLandingPlan4086_Handle
 beq SourceLandingPlan4086_Guard21
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard21:
.a16
.i16
 inx
 inx
 jsr SourceLandingPlan4086_Read
 cmp.l SourceLandingPlan4086_Model
 beq SourceLandingPlan4086_Guard22
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard22:
.a16
.i16
 cmp #128
 bcc SourceLandingPlan4086_Guard23
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard23:
.a16
.i16
 inx
 inx
 ldy #0
SourceLandingPlan4086_Stage:
.a16
.i16
 jsr SourceLandingPlan4086_Read
 phx
 tyx
 sta.l SourceLandingPlan4086_Scratch,x
 plx
 inx
 inx
 iny
 iny
 cpy #12
 bne SourceLandingPlan4086_Stage
 lda.l SourceLandingPlan4086_Scratch+8
 and #$FFFC
 beq SourceLandingPlan4086_Guard24
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard24:
.a16
.i16
 lda.l SourceLandingPlan4086_Scratch+10
 beq SourceLandingPlan4086_Guard25
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard25:
.a16
.i16
 lda.l SourceLandingPlan4086_Scratch+2
 and #$7F80
 cmp #$7F80
 bne SourceLandingPlan4086_Guard26
 jmp SourceLandingPlan4086_Bad
SourceLandingPlan4086_Guard26:
.a16
.i16
 ldx #0
SourceLandingPlan4086_Publish:
.a16
.i16
 lda.l SourceLandingPlan4086_Scratch,x
 sta.l SourceLandingPlan4086_Bounce,x
 inx
 inx
 cpx #12
 bne SourceLandingPlan4086_Publish
 lda #2
 sta.l SourceLandingPlan4086_Status
 ply
 plx
 pla
 plp
 clc
 rtl
SourceLandingPlan4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceLandingPlan4086_Status
 ply
 plx
 pla
 plp
 sec
 rtl
SourceLandingPlan4086_Read:
.a16
.i16
 phb
 sep #$20
.a8
 lda.l SourceLandingPlan4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plb
 ora #0
 rts

