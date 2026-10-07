; Immutable B4AC role profile, compiler-derived from source global arrays.
; BW role directory $435900..$43597F (64 words), separate from options buffer.
SourceAttackChoiceProfile4086_Ready = $43BEB2
SourceAttackChoiceProfile4086_Bank = $43BEB4
SourceAttackChoiceProfile4086_Bytes = $43BEB6
SourceAttackChoiceProfile4086_Status = $43BEB8
SourceAttackChoiceProfile4086_Normals = $43BEBA
SourceAttackChoiceProfile4086_Specials = $43BEBC
SourceAttackChoiceProfile4086_Maximum = $43BEBE
SourceAttackChoiceProfile4086_Total = $43BEC0
SourceAttackChoiceProfile4086_Frames = $43BEC2
SourceAttackChoiceProfile4086_Base = $43BEC4
SourceAttackChoiceProfile4086_End = $43BEC6
SOURCE_ATTACK_CHOICE_ROLES = $435900
SourceAttackChoiceProfile4086_Load:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 tsc
 sec
 sbc #14
 tcs
 inc a
 tcd
 lda.l SourceAttackChoiceProfile4086_Ready
 cmp #$B5FE
 beq SourceAttackChoiceProfile4086_Guard1
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard1:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Status
 beq SourceAttackChoiceProfile4086_Start
 cmp #2
 beq SourceAttackChoiceProfile4086_Guard2
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard2:
.a16
.i16
SourceAttackChoiceProfile4086_Start:
.a16
.i16
 lda #1
 sta.l SourceAttackChoiceProfile4086_Status
 lda.l SourceAttackChoiceProfile4086_Bank
 cmp #64
 bcc SourceAttackChoiceProfile4086_Guard3
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard3:
.a16
.i16
 sta $02
 lda.l SourceAttackChoiceProfile4086_Base
 cmp #$8000
 bcs SourceAttackChoiceProfile4086_BaseOK
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_BaseOK:
.a16
.i16
 sta $00
 lda.l SourceAttackChoiceProfile4086_Bytes
 cmp #46
 bcs SourceAttackChoiceProfile4086_Guard4
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard4:
.a16
.i16
 cmp #145
 bcc SourceAttackChoiceProfile4086_Guard5
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard5:
.a16
.i16
 lda.l SourceAttackChoiceProfile4086_Base
 clc
 adc.l SourceAttackChoiceProfile4086_Bytes
 bcc SourceAttackChoiceProfile4086_BankExtent
 beq SourceAttackChoiceProfile4086_BankExtent
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_BankExtent:
.a16
.i16
 ldy #0
 lda [$00],y
 cmp #$3442
 beq SourceAttackChoiceProfile4086_Guard6
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard6:
.a16
.i16
 ldy #2
 lda [$00],y
 cmp #$4341
 beq SourceAttackChoiceProfile4086_Guard7
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard7:
.a16
.i16
 ldy #4
 lda [$00],y
 cmp #1
 beq SourceAttackChoiceProfile4086_Guard8
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard8:
.a16
.i16
 ldy #12
 lda [$00],y
 cmp #64
 beq SourceAttackChoiceProfile4086_Guard9
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard9:
.a16
.i16
 ldy #14
 lda [$00],y
 cmp #1
 bcs SourceAttackChoiceProfile4086_FrameMin
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_FrameMin:
.a16
.i16
 cmp #2048
 bcc SourceAttackChoiceProfile4086_FrameMax
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_FrameMax:
.a16
.i16
 sta $0C
 ldy #6
 lda [$00],y
 cmp #4
 bcs SourceAttackChoiceProfile4086_Guard11
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard11:
.a16
.i16
 sta $04
 ldy #8
 lda [$00],y
 cmp #8
 bcs SourceAttackChoiceProfile4086_Guard12
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard12:
.a16
.i16
 sta $06
 clc
 adc $04
 bcc SourceAttackChoiceProfile4086_Guard13
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard13:
.a16
.i16
 clc
 adc #3
 cmp #65
 bcc SourceAttackChoiceProfile4086_Guard14
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard14:
.a16
.i16
 sta $0A
 asl a
 clc
 adc #16
 cmp.l SourceAttackChoiceProfile4086_Bytes
 beq SourceAttackChoiceProfile4086_Guard15
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard15:
.a16
.i16
 ldy #10
 lda [$00],y
 cmp #1
 bcs SourceAttackChoiceProfile4086_Guard16
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard16:
.a16
.i16
 cmp #1025
 bcc SourceAttackChoiceProfile4086_Guard17
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard17:
.a16
.i16
 sta $08
 ldx $0A
 ldy #16
SourceAttackChoiceProfile4086_ValidateRole:
.a16
.i16
 lda [$00],y
 cmp $08
 bcc SourceAttackChoiceProfile4086_Guard18
 jmp SourceAttackChoiceProfile4086_Bad
SourceAttackChoiceProfile4086_Guard18:
.a16
.i16
 iny
 iny
 dex
 bne SourceAttackChoiceProfile4086_ValidateRole
 ldy #16
 ldx #0
SourceAttackChoiceProfile4086_Copy:
.a16
.i16
 lda [$00],y
 sta.l SOURCE_ATTACK_CHOICE_ROLES,x
 iny
 iny
 inx
 inx
 txa
 lsr a
 cmp $0A
 bcc SourceAttackChoiceProfile4086_Copy
 lda $04
 sta.l SourceAttackChoiceProfile4086_Normals
 lda $06
 sta.l SourceAttackChoiceProfile4086_Specials
 lda $08
 sta.l SourceAttackChoiceProfile4086_Maximum
 lda $0A
 sta.l SourceAttackChoiceProfile4086_Total
 lda $0C
 sta.l SourceAttackChoiceProfile4086_Frames
 lda #2
 sta.l SourceAttackChoiceProfile4086_Status
SourceAttackChoiceProfile4086_Good:
.a16
.i16
 tsc
 clc
 adc #14
 tcs
 pld
 ply
 plx
 plp
 clc
 rtl
SourceAttackChoiceProfile4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAttackChoiceProfile4086_Status
 tsc
 clc
 adc #14
 tcs
 pld
 ply
 plx
 plp
 sec
 rtl
