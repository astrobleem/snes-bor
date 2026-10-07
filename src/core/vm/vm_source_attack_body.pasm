; Exact noflip and twelve atchain integers from an immutable B4BC profile.
; Actor rows: noflip int32, chain codes 36 bits+length 4 bits, B605 marker.
; Slots 0..95: $435980..$435D9F. Slots 96..127: $40BDCC..$40BF2B.
; This component grants no attack callback and does not execute a chain.
SourceAttackBody4086_Ready = $43BF2C
SourceAttackBody4086_Status = $43BF2E
SourceAttackBody4086_Bank = $43BF30
SourceAttackBody4086_Base = $43BF32
SourceAttackBody4086_Bytes = $43BF34
SourceAttackBody4086_Models = $43BF36
SourceAttackBody4086_NoFlip = $43BF38
SourceAttackBody4086_Chain = $43BF3C ; low36 chain codes, high nibble length
SourceAttackBody4086_End = $43BF42
SourceAttackBody4086_CopyEntity:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 pha
 txa
 pha
 tsc
 sec
 sbc #26
 tcs
 inc a
 tcd
 lda #0
 sta $18
 bra SourceAttackBody4086_Inputs
SourceAttackBody4086_PreflightEntity:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 pha
 txa
 pha
 tsc
 sec
 sbc #26
 tcs
 inc a
 tcd
 lda #1
 sta $18
 bra SourceAttackBody4086_Inputs
SourceAttackBody4086_ReadEntity:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 pha
 txa
 pha
 tsc
 sec
 sbc #26
 tcs
 inc a
 tcd
 lda #2
 sta $18
SourceAttackBody4086_Inputs:
.a16
.i16
 lda 27,s
 sta $06
 lda 29,s
 sta $04
 lda.l SourceAttackBody4086_Ready
 cmp #$B605
 beq SourceAttackBody4086_Guard1
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard1:
.a16
.i16
 lda.l SourceAttackBody4086_Status
 beq SourceAttackBody4086_Start
 cmp #2
 beq SourceAttackBody4086_Guard2
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard2:
.a16
.i16
SourceAttackBody4086_Start:
.a16
.i16
 lda $04
 cmp #128
 bcc SourceAttackBody4086_Guard3
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard3:
.a16
.i16
 lda.l SourceAttackBody4086_Bank
 bne SourceAttackBody4086_Guard4
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard4:
.a16
.i16
 cmp #64
 bcc SourceAttackBody4086_Guard5
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard5:
.a16
.i16
 sta $02
 lda.l SourceAttackBody4086_Base
 cmp #$8000
 bcs SourceAttackBody4086_Guard6
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard6:
.a16
.i16
 sta $00
 clc
 adc.l SourceAttackBody4086_Bytes
 bcc SourceAttackBody4086_Extent
 cmp #0
 beq SourceAttackBody4086_Guard7
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard7:
.a16
.i16
SourceAttackBody4086_Extent:
.a16
.i16
 ldy #0
 ldy #0
 lda [$00],y
 cmp #13378
 beq SourceAttackBody4086_Guard8
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard8:
.a16
.i16
 ldy #2
 lda [$00],y
 cmp #17218
 beq SourceAttackBody4086_Guard9
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard9:
.a16
.i16
 ldy #4
 lda [$00],y
 cmp #1
 beq SourceAttackBody4086_Guard10
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard10:
.a16
.i16
 ldy #6
 lda [$00],y
 bne SourceAttackBody4086_Guard11
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard11:
.a16
.i16
 cmp #17
 bcc SourceAttackBody4086_Guard12
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard12:
.a16
.i16
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceAttackBody4086_Guard13
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard13:
.a16
.i16
 sta $08
 cmp $06
 bne SourceAttackBody4086_Guard14
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard14:
.a16
.i16
 cmp $06
 bcs SourceAttackBody4086_Guard15
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard15:
.a16
.i16
 asl a
 asl a
 asl a
 clc
 adc $08
 clc
 adc #16
 cmp.l SourceAttackBody4086_Bytes
 beq SourceAttackBody4086_Guard16
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard16:
.a16
.i16
 ldy #8
 lda [$00],y
 cmp #9
 beq SourceAttackBody4086_Guard17
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard17:
.a16
.i16
 ldy #10
 lda [$00],y
 cmp #12
 beq SourceAttackBody4086_Guard18
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard18:
.a16
.i16
 ldy #14
 lda [$00],y
 cmp #0
 beq SourceAttackBody4086_Guard19
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard19:
.a16
.i16
 ldy #12
 lda [$00],y
 bne SourceAttackBody4086_Guard20
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard20:
.a16
.i16
 cmp #8
 bcc SourceAttackBody4086_Guard21
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard21:
.a16
.i16
 sta $14
 lda $06
 asl a
 asl a
 asl a
 clc
 adc $06
 clc
 adc #16
 tay
 lda [$00],y
 sta $08
 iny
 iny
 lda [$00],y
 sta $0A
 iny
 iny
 lda [$00],y
 sta $0C
 iny
 iny
 lda [$00],y
 sta $0E
 iny
 iny
 sep #$20
.a8
 lda [$00],y
 sta $10
 rep #$20
.a16
 lda $10
 and #$00F0
 cmp #$00D0
 bcc SourceAttackBody4086_Guard22
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard22:
.a16
.i16
 lda $0C
 sta $12
 lda $0E
 sta $14
 lda $10
 and #$000F
 sta $16
 ldx #12
SourceAttackBody4086_ChainCheck:
.a16
.i16
 lda $12
 and #7
 ldy #12
 cmp [$00],y
 beq SourceAttackBody4086_Guard23
 bcc SourceAttackBody4086_Guard23
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_Guard23:
.a16
.i16
 lsr $16
 ror $14
 ror $12
 lsr $16
 ror $14
 ror $12
 lsr $16
 ror $14
 ror $12
 dex
 bne SourceAttackBody4086_ChainCheck
 ldy #6
 sep #$20
.a8
 lda [$00],y
 sta $11
 rep #$20
.a16
 lda $18
 cmp #1
 bne SourceAttackBody4086_Install
 lda $10
 xba
 and #$00FF
 sta.l SourceAttackBody4086_Models
 lda #2
 sta.l SourceAttackBody4086_Status
 jmp SourceAttackBody4086_Return
SourceAttackBody4086_Install:
.a16
.i16
 lda $04
 cmp #96
 bcc SourceAttackBody4086_LowRows
 sec
 sbc #96
 sta $04
 lda #$40
 sta $02
 lda #$BDCC
 sta $06
 bra SourceAttackBody4086_Destination
SourceAttackBody4086_LowRows:
.a16
.i16
 lda #$43
 sta $02
 lda #$5980
 sta $06
SourceAttackBody4086_Destination:
.a16
.i16
 lda $04
 asl a
 sta $12
 asl a
 asl a
 clc
 adc $12
 clc
 adc $04
 clc
 adc $06
 sta $00
 lda $18
 cmp #2
 bne SourceAttackBody4086_WriteRow
 jmp SourceAttackBody4086_ReadRow
SourceAttackBody4086_WriteRow:
.a16
.i16
 lda #1
 sta.l SourceAttackBody4086_Status
 lda #0
 ldy #9
 sta [$00],y
 ldy #0
 lda $08
 sta [$00],y
 iny
 iny
 lda $0A
 sta [$00],y
 iny
 iny
 lda $0C
 sta [$00],y
 iny
 iny
 lda $0E
 sta [$00],y
 iny
 iny
 sep #$20
.a8
 lda $10
 sta [$00],y
 rep #$20
.a16
 ldy #9
 lda #$B605
 sta [$00],y
 lda $10
 xba
 and #$00FF
 sta.l SourceAttackBody4086_Models
 lda #2
 sta.l SourceAttackBody4086_Status
 jmp SourceAttackBody4086_Return
SourceAttackBody4086_ReadRow:
.a16
.i16
 ldy #9
 lda [$00],y
 cmp #$B605
 beq SourceAttackBody4086_ReadMarker
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_ReadMarker:
.a16
.i16
 ldy #0
 lda [$00],y
 cmp $08
 beq SourceAttackBody4086_ReadWord0
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_ReadWord0:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp $0A
 beq SourceAttackBody4086_ReadWord1
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_ReadWord1:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp $0C
 beq SourceAttackBody4086_ReadWord2
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_ReadWord2:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp $0E
 beq SourceAttackBody4086_ReadWord3
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_ReadWord3:
.a16
.i16
 iny
 iny
 sep #$20
.a8
 lda [$00],y
 cmp $10
 rep #$20
.a16
 beq SourceAttackBody4086_ReadByte
 jmp SourceAttackBody4086_Bad
SourceAttackBody4086_ReadByte:
.a16
.i16
 lda $08
 sta.l SourceAttackBody4086_NoFlip
 lda $0A
 sta.l SourceAttackBody4086_NoFlip+2
 lda $0C
 sta.l SourceAttackBody4086_Chain
 lda $0E
 sta.l SourceAttackBody4086_Chain+2
 lda $10
 and #$00FF
 sta.l SourceAttackBody4086_Chain+4
 lda $10
 xba
 and #$00FF
 sta.l SourceAttackBody4086_Models
 lda #2
 sta.l SourceAttackBody4086_Status
 jmp SourceAttackBody4086_Return
SourceAttackBody4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAttackBody4086_Status
SourceAttackBody4086_Return:
.a16
.i16
 tsc
 clc
 adc #26
 tcs
 lda.l SourceAttackBody4086_Status
 cmp #2
 beq SourceAttackBody4086_Good
 pla
 pla
 pld
 ply
 plx
 plp
 sec
 rtl
SourceAttackBody4086_Good:
.a16
.i16
 pla
 pla
 pld
 ply
 plx
 plp
 clc
 rtl
