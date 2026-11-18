; Private IDs and presence rows only. Capture requires acquired next pins.
; Ready is NOT a scene-publication or pin-release authorization.
SourceNextWitness_Base = $436800
SourceNextWitness_Capture:
.a16
.i16
.a16
.i16
php
rep #$30
cld
pha
phx
phy
phb
cmp #2
bcc SourceNextWitness_CaptureSlot
brl SourceNextWitness_CaptureNoEarly
SourceNextWitness_CaptureSlot:
.a16
.i16
tax
lda #0
pha
pha
txa
xba
asl a
pha
txa
beq SourceNextWitness_CaptureP1
lda #128
bra SourceNextWitness_CaptureBit
SourceNextWitness_CaptureP1:
.a16
.i16
lda #64
SourceNextWitness_CaptureBit:
.a16
.i16
pha
sep #$20
.a8
lda #$43
pha
plb
rep #$20
.a16
lda 3,s
tay
lda.l SVActor_Magic
cmp #$AC19
beq SourceNextWitness_CaptureGuard1
brl SourceNextWitness_CaptureNo
SourceNextWitness_CaptureGuard1:
.a16
.i16
lda.w $6800,y
cmp #0
beq SourceNextWitness_CaptureGuard2
brl SourceNextWitness_CaptureNo
SourceNextWitness_CaptureGuard2:
.a16
.i16
lda 3,s
tay
ldx #0
SourceNextWitness_CaptureBlockLoop:
.a16
.i16
lda.l SVActor_HeldBlocks,x
and 1,s
beq SourceNextWitness_CaptureBlockAbsent
lda #1
sta.w $6812,y
lda.l SourceVisual_BlockCache,x
sta.w $6810,y
lda 5,s
inc a
sta 5,s
bra SourceNextWitness_CaptureBlockNext
SourceNextWitness_CaptureBlockAbsent:
.a16
.i16
lda #0
sta.w $6810,y
sta.w $6812,y
SourceNextWitness_CaptureBlockNext:
.a16
.i16
inx
inx
inx
inx
inx
inx
inx
inx
iny
iny
iny
iny
cpx #512
bcs SourceNextWitness_CaptureBlockDone
brl SourceNextWitness_CaptureBlockLoop
SourceNextWitness_CaptureBlockDone:
.a16
.i16
lda 5,s
bne SourceNextWitness_CaptureGuard3
brl SourceNextWitness_CaptureNo
SourceNextWitness_CaptureGuard3:
.a16
.i16
lda 3,s
tay
ldx #0
SourceNextWitness_CapturePaletteLoop:
.a16
.i16
lda.l SVActor_HeldPalettes,x
and 1,s
beq SourceNextWitness_CapturePaletteAbsent
lda #1
sta.w $6912,y
lda.l SourceVisual_PaletteCache,x
sta.w $6910,y
lda 7,s
inc a
sta 7,s
bra SourceNextWitness_CapturePaletteNext
SourceNextWitness_CapturePaletteAbsent:
.a16
.i16
lda #0
sta.w $6910,y
sta.w $6912,y
SourceNextWitness_CapturePaletteNext:
.a16
.i16
inx
inx
inx
inx
inx
inx
inx
inx
iny
iny
iny
iny
cpx #64
bcs SourceNextWitness_CapturePaletteDone
brl SourceNextWitness_CapturePaletteLoop
SourceNextWitness_CapturePaletteDone:
.a16
.i16
lda 7,s
bne SourceNextWitness_CaptureGuard4
brl SourceNextWitness_CaptureNo
SourceNextWitness_CaptureGuard4:
.a16
.i16
lda 3,s
tay
lda 1,s
sta.w $6804,y
lda 5,s
sta.w $6806,y
lda 7,s
sta.w $6808,y
lda #$4E50
sta.w $6800,y
SourceNextWitness_CaptureYes:
.a16
.i16
pla
pla
pla
pla
plb
ply
plx
pla
plp
sec
rtl
SourceNextWitness_CaptureNo:
.a16
.i16
pla
pla
pla
pla
SourceNextWitness_CaptureNoEarly:
.a16
.i16
plb
ply
plx
pla
plp
clc
rtl
SourceNextWitness_Ready:
.a16
.i16
.a16
.i16
php
rep #$30
cld
pha
phx
phy
phb
cmp #2
bcc SourceNextWitness_ReadySlot
brl SourceNextWitness_ReadyNoEarly
SourceNextWitness_ReadySlot:
.a16
.i16
tax
lda #0
pha
pha
txa
xba
asl a
pha
txa
beq SourceNextWitness_ReadyP1
lda #128
bra SourceNextWitness_ReadyBit
SourceNextWitness_ReadyP1:
.a16
.i16
lda #64
SourceNextWitness_ReadyBit:
.a16
.i16
pha
sep #$20
.a8
lda #$43
pha
plb
rep #$20
.a16
lda 3,s
tay
lda.l SVActor_Magic
cmp #$AC19
beq SourceNextWitness_ReadyGuard1
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard1:
.a16
.i16
lda.w $6800,y
cmp #$4E50
beq SourceNextWitness_ReadyGuard2
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard2:
.a16
.i16
lda.w $6804,y
cmp 1,s
beq SourceNextWitness_ReadyGuard3
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard3:
.a16
.i16
lda 3,s
tay
ldx #0
SourceNextWitness_ReadyBlockLoop:
.a16
.i16
lda.l SVActor_HeldBlocks,x
and 1,s
beq SourceNextWitness_ReadyBlockAbsent
lda.w $6812,y
cmp #1
beq SourceNextWitness_ReadyGuard4
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard4:
.a16
.i16
lda.l SourceVisual_BlockCache,x
cmp.w $6810,y
beq SourceNextWitness_ReadyGuard5
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard5:
.a16
.i16
lda.l SourceVisual_BlockCache+2,x
cmp #2
beq SourceNextWitness_ReadyGuard6
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard6:
.a16
.i16
lda.l SourceVisual_BlockCache+5,x
and #255
cmp #4
beq SourceNextWitness_ReadyGuard7
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard7:
.a16
.i16
lda 5,s
inc a
sta 5,s
bra SourceNextWitness_ReadyBlockNext
SourceNextWitness_ReadyBlockAbsent:
.a16
.i16
lda.w $6812,y
beq SourceNextWitness_ReadyGuard8
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard8:
.a16
.i16
SourceNextWitness_ReadyBlockNext:
.a16
.i16
inx
inx
inx
inx
inx
inx
inx
inx
iny
iny
iny
iny
cpx #512
bcs SourceNextWitness_ReadyBlockDone
brl SourceNextWitness_ReadyBlockLoop
SourceNextWitness_ReadyBlockDone:
.a16
.i16
lda 5,s
bne SourceNextWitness_ReadyGuard9
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard9:
.a16
.i16
SourceNextWitness_ReadyPaletteTail:
.a16
.i16
lda 3,s
tay
ldx #0
SourceNextWitness_ReadyPaletteLoop:
.a16
.i16
lda.l SVActor_HeldPalettes,x
and 1,s
beq SourceNextWitness_ReadyPaletteAbsent
lda.w $6912,y
cmp #1
beq SourceNextWitness_ReadyGuard10
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard10:
.a16
.i16
lda.l SourceVisual_PaletteCache,x
cmp.w $6910,y
beq SourceNextWitness_ReadyGuard11
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard11:
.a16
.i16
lda.l SourceVisual_PaletteCache+3,x
and #255
cmp #1
beq SourceNextWitness_ReadyGuard12
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard12:
.a16
.i16
lda 7,s
inc a
sta 7,s
bra SourceNextWitness_ReadyPaletteNext
SourceNextWitness_ReadyPaletteAbsent:
.a16
.i16
lda.w $6912,y
beq SourceNextWitness_ReadyGuard13
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard13:
.a16
.i16
SourceNextWitness_ReadyPaletteNext:
.a16
.i16
inx
inx
inx
inx
inx
inx
inx
inx
iny
iny
iny
iny
cpx #64
bcs SourceNextWitness_ReadyPaletteDone
brl SourceNextWitness_ReadyPaletteLoop
SourceNextWitness_ReadyPaletteDone:
.a16
.i16
lda 7,s
bne SourceNextWitness_ReadyGuard14
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard14:
.a16
.i16
lda 3,s
tay
lda 5,s
cmp.w $6806,y
beq SourceNextWitness_ReadyGuard15
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard15:
.a16
.i16
lda 7,s
cmp.w $6808,y
beq SourceNextWitness_ReadyGuard16
brl SourceNextWitness_ReadyNo
SourceNextWitness_ReadyGuard16:
.a16
.i16
SourceNextWitness_ReadyYes:
.a16
.i16
pla
pla
pla
pla
plb
ply
plx
pla
plp
sec
rtl
SourceNextWitness_ReadyNo:
.a16
.i16
pla
pla
pla
pla
SourceNextWitness_ReadyNoEarly:
.a16
.i16
plb
ply
plx
pla
plp
clc
rtl
SourceNextWitness_End:
.a16
.i16
