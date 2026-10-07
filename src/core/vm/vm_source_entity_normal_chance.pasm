; Actual current model/aiattack/self X/source camera -> immutable C cutoff.
; B601 admits a CLOSED static coefficient profile: attackthrottle/global
; coefficients may not be mutated through an unbound source property API.
; Source viewport is retained independently of native presentation cropping.
SourceEntityNormalChance4086_Ready = $43BEFC
SourceEntityNormalChance4086_Status = $43BEFE
SourceEntityNormalChance4086_Bank = $43BF00
SourceEntityNormalChance4086_Base = $43BF02
SourceEntityNormalChance4086_Bytes = $43BF04
SourceEntityNormalChance4086_Models = $43BF06
SourceEntityNormalChance4086_Offscreen = $43BF08
SourceEntityNormalChance4086_Result = $43BF0A
SourceEntityNormalChance4086_End = $43BF0E
SourceEntityNormalChance4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 tsc
 sec
 sbc #16
 tcs
 inc a
 tcd
 lda.l SourceEntityNormalChance4086_Ready
 cmp #$B601
 beq SourceEntityNormalChance4086_G1
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G1:
.a16
.i16
 lda.l SourceEntityNormalChance4086_Status
 beq SourceEntityNormalChance4086_Start
 cmp #2
 beq SourceEntityNormalChance4086_Start
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_Start:
.a16
.i16
 lda #1
 sta.l SourceEntityNormalChance4086_Status
 jsl SourceCommonThink4086_CheckOwner
 bcc SourceEntityNormalChance4086_G2
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G2:
.a16
.i16
 lda.l SourceAI4086_Flags
 asl a
 clc
 adc.l SourceAI4086_Flags
 tax
 lda.l $40C038,x
 sta.l SourceNormalChance4086_AI
 lda.l $40C03A,x
 sta.l SourceNormalChance4086_AI+2
 lda.l SourceNormalChance4086_AI
 and #8
 beq SourceEntityNormalChance4086_Profile
 jmp SourceEntityNormalChance4086_Call
SourceEntityNormalChance4086_Profile:
.a16
.i16
 lda.l SourceEntityNormalChance4086_Bank
 beq SourceEntityNormalChance4086_BankBad
 cmp #64
 bcc SourceEntityNormalChance4086_G3
SourceEntityNormalChance4086_BankBad:
.a16
.i16
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G3:
.a16
.i16
 sta $02
 lda.l SourceEntityNormalChance4086_Base
 cmp #$8000
 bcs SourceEntityNormalChance4086_G4
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G4:
.a16
.i16
 sta $00
 clc
 adc.l SourceEntityNormalChance4086_Bytes
 bcc SourceEntityNormalChance4086_Extent
 beq SourceEntityNormalChance4086_Extent
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_Extent:
.a16
.i16
 ldy #0
 lda [$00],y
 cmp #$3442
 beq SourceEntityNormalChance4086_G5
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G5:
.a16
.i16
 ldy #2
 lda [$00],y
 cmp #$434E
 beq SourceEntityNormalChance4086_G6
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G6:
.a16
.i16
 ldy #4
 lda [$00],y
 cmp #1
 beq SourceEntityNormalChance4086_G7
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G7:
.a16
.i16
 ldy #6
 lda [$00],y
 beq SourceEntityNormalChance4086_CountBad
 cmp #17
 bcc SourceEntityNormalChance4086_G8
SourceEntityNormalChance4086_CountBad:
.a16
.i16
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G8:
.a16
.i16
 cmp.l SourceModelAnimationCopy4086_Models
 beq SourceEntityNormalChance4086_G9
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G9:
.a16
.i16
 sta.l SourceEntityNormalChance4086_Models
 asl a
 asl a
 clc
 adc #16
 cmp.l SourceEntityNormalChance4086_Bytes
 beq SourceEntityNormalChance4086_G10
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G10:
.a16
.i16
 ldy #8
 lda [$00],y
 cmp #4
 beq SourceEntityNormalChance4086_G11
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G11:
.a16
.i16
 lda.l SourceCameraMotion4086_Ready
 cmp #$B5DB
 beq SourceEntityNormalChance4086_G12
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G12:
.a16
.i16
 ldy #10
 lda [$00],y
 beq SourceEntityNormalChance4086_CameraBad
 cmp.l SourceCameraMotion4086_HRes
 beq SourceEntityNormalChance4086_G13
SourceEntityNormalChance4086_CameraBad:
.a16
.i16
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G13:
.a16
.i16
 ldy #12
 lda [$00],y
 beq SourceEntityNormalChance4086_CameraBad
 cmp.l SourceCameraMotion4086_VRes
 beq SourceEntityNormalChance4086_G14
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G14:
.a16
.i16
 ldy #14
 lda [$00],y
 beq SourceEntityNormalChance4086_G15
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G15:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410030,x
 cmp #2
 beq SourceEntityNormalChance4086_G16
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G16:
.a16
.i16
 lda.l $410032,x
 beq SourceEntityNormalChance4086_G17
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_G17:
.a16
.i16
 ; Extended signed 48-bit Q16 subtraction, with no 32-bit wrap or
 ; truncation at the strict -10/+HRes+10 screen thresholds.
 lda.l $410036,x
 sta $06
 bmi SourceEntityNormalChance4086_SelfNegative
 lda #0
 bra SourceEntityNormalChance4086_SelfSign
SourceEntityNormalChance4086_SelfNegative:
.a16
.i16
 lda #$FFFF
SourceEntityNormalChance4086_SelfSign:
.a16
.i16
 sta $08
 lda.l VmSourceWorld_AdvanceX+2
 bmi SourceEntityNormalChance4086_CameraNegative
 lda #0
 bra SourceEntityNormalChance4086_CameraSign
SourceEntityNormalChance4086_CameraNegative:
.a16
.i16
 lda #$FFFF
SourceEntityNormalChance4086_CameraSign:
.a16
.i16
 sta $0C
 lda.l $410034,x
 sec
 sbc.l VmSourceWorld_AdvanceX
 sta $04
 lda $06
 sbc.l VmSourceWorld_AdvanceX+2
 sta $06
 lda $08
 sbc $0C
 sta $08
 bmi SourceEntityNormalChance4086_Left
 lda.l SourceCameraMotion4086_HRes
 clc
 adc #10
 bcs SourceEntityNormalChance4086_Inside
 cmp $06
 bcc SourceEntityNormalChance4086_Outside
 bne SourceEntityNormalChance4086_Inside
 lda $04
 bne SourceEntityNormalChance4086_Outside
 bra SourceEntityNormalChance4086_Inside
SourceEntityNormalChance4086_Left:
.a16
.i16
 lda $06
 cmp #$FFF6
 bcc SourceEntityNormalChance4086_Outside
SourceEntityNormalChance4086_Inside:
.a16
.i16
 lda #0
 bra SourceEntityNormalChance4086_Which
SourceEntityNormalChance4086_Outside:
.a16
.i16
 lda #1
SourceEntityNormalChance4086_Which:
.a16
.i16
 sta.l SourceEntityNormalChance4086_Offscreen
 lda.l SourceAI4086_Model
 asl a
 asl a
 clc
 adc #16
 tay
 lda [$00],y
 cmp #$FFFF
 beq SourceEntityNormalChance4086_OnValid
 cmp #10000
 bcc SourceEntityNormalChance4086_OnValid
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_OnValid:
.a16
.i16
 sta $0E
 iny
 iny
 lda [$00],y
 cmp #$FFFF
 beq SourceEntityNormalChance4086_OffValid
 cmp #10000
 bcc SourceEntityNormalChance4086_OffValid
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_OffValid:
.a16
.i16
 sta $0C
 lda.l SourceEntityNormalChance4086_Offscreen
 beq SourceEntityNormalChance4086_Onscreen
 lda $0C
 bra SourceEntityNormalChance4086_Selected
SourceEntityNormalChance4086_Onscreen:
.a16
.i16
 lda $0E
SourceEntityNormalChance4086_Selected:
.a16
.i16
 sta.l SourceNormalChance4086_Cutoff
SourceEntityNormalChance4086_Call:
.a16
.i16
 jsl SourceNormalChance4086_Execute
 bcc SourceEntityNormalChance4086_Success
 jmp SourceEntityNormalChance4086_Bad
SourceEntityNormalChance4086_Success:
.a16
.i16
 lda.l SourceNormalChance4086_Result
 sta.l SourceEntityNormalChance4086_Result
 lda.l SourceNormalChance4086_Result+2
 sta.l SourceEntityNormalChance4086_Result+2
 lda #2
 sta.l SourceEntityNormalChance4086_Status
 tsc
 clc
 adc #16
 tcs
 pld
 ply
 plx
 plp
 clc
 rtl
SourceEntityNormalChance4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceEntityNormalChance4086_Status
 tsc
 clc
 adc #16
 tcs
 pld
 ply
 plx
 plp
 sec
 rtl
