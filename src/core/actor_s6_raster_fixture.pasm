; Isolated raster geometry/transfer host, not the production renderer.
; Shared S5 descriptor context D=$1000. A0..AF are this fixture's scratch.
; Prepare writes WRAM only; Commit owns VRAM/OAM DMA and must run in blank.
; Mode at7E2012:0 paused forced-blank proof;1 timed admission fixture.
S6_FrameChanged:
    rep #$30
    .a16
    .i16
    lda.l $7E2012
    beq S6_RasterUpload
    lda #1
    sta.l $7E2014
    rtl
S6_RasterUpload:
    rep #$30
    .a16
    .i16
    lda.l $7E2012
    bne S6_RasterUploadReady
    sep #$20
    .a8
    lda #$80
    sta $2100
S6_RasterUploadReady:
    rep #$30
    .a16
    .i16
    jsl S6_RasterPrepare
    jsl S6_RasterCommit
    jsl S6_RasterPublish
    rtl

S6_RasterPrepare:
    rep #$30
    .a16
    .i16
    lda $5E
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $018000,x
    sta $A0
    lda.l $018002,x
    sta $A2
    lda.l $018004,x
    sta $A4
    lda.l $018006,x
    sta $A6
    ldx #0
S6_RasterHide:
    .a16
    .i16
    lda #$E0C0
    sta.l $7E3000,x
    lda #0
    sta.l $7E3002,x
    inx
    inx
    inx
    inx
    cpx #512
    bne S6_RasterHide
    ldx #0
    lda #$5555
S6_RasterHigh:
    .a16
    .i16
    sta.l $7E3200,x
    inx
    inx
    cpx #32
    bne S6_RasterHigh
    lda $A6
    xba
    and #$00FF
    sta $AA
    ldy #0
    ldx #0
S6_RasterObject:
    .a16
    .i16
    lda $1A
    beq S6_RasterLeft
    lda [$A4],y
    bra S6_RasterX
S6_RasterLeft:
    .a16
    .i16
    iny
    iny
    lda [$A4],y
    dey
    dey
S6_RasterX:
    .a16
    .i16
    clc
    adc $14
    sta $AC
    iny
    iny
    iny
    iny
    lda [$A4],y
    clc
    adc $16
    sec
    sbc $18
    ; Fixture gfx_y_offset=0, advancex=0, entirely onscreen admission.
    xba
    and #$FF00
    ora $AC
    sta.l $7E3000,x
    iny
    iny
    lda [$A4],y
    ora #$3000
    sta $AC
    lda $1A
    bne S6_RasterAttributes
    lda $AC
    ora #$4000
    sta $AC
S6_RasterAttributes:
    .a16
    .i16
    lda $AC
    sta.l $7E3002,x
    ; Active admission guarantees positive X and SMALL mode: own BOTH bits.
    ; Unused entries retain the production hidden (-64,224,SMALL) contract.
    phx
    phy
    txa
    and #12
    lsr a
    tay
    lda S6_RasterHighMasks,y
    sta $AC
    txa
    lsr a
    lsr a
    lsr a
    lsr a
    tax
    lda.l $7E3200,x
    and $AC
    sta.l $7E3200,x
    ply
    plx
    iny
    iny
    inx
    inx
    inx
    inx
    dec $AA
    bne S6_RasterObject
    rtl

S6_RasterCommit:
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    .i16
    lda #$80
    sta $2115
    lda #1
    sta $4300
    lda #$18
    sta $4301
    lda $A3
    sta $AA
    stz $AB
    rep #$20
    .a16
    ldy #0
S6_RasterDma:
    .a16
    .i16
    lda [$A0],y
    sta $2116
    iny
    iny
    lda [$A0],y
    sta $4302
    iny
    iny
    sep #$20
    .a8
    lda [$A0],y
    sta $4304
    iny
    rep #$20
    .a16
    lda [$A0],y
    sta $4305
    iny
    iny
    sep #$20
    .a8
    lda #1
    sta $420B
    rep #$20
    .a16
    dec $AA
    bne S6_RasterDma
    sep #$20
    .a8
    stz $2102
    stz $2103
    stz $4300
    lda #4
    sta $4301
    lda #$7E
    sta $4304
    rep #$20
    .a16
    lda #$3000
    sta $4302
    lda.l $7E2018
    bne S6_RasterHighWaterKnown
    lda $A6
    xba
    and #$00FF
    sta.l $7E2018
    lda #512
    bra S6_RasterLowBytes
S6_RasterHighWaterKnown:
    .a16
    .i16
    lda $A6
    xba
    and #$00FF
    cmp.l $7E2018
    bcc S6_RasterHighWaterUse
    sta.l $7E2018
S6_RasterHighWaterUse:
    .a16
    .i16
    lda.l $7E2018
    asl a
    asl a
S6_RasterLowBytes:
    .a16
    .i16
    sta $4305
    sep #$20
    .a8
    lda #1
    sta $420B
    stz $2102
    lda #1
    sta $2103
    rep #$20
    .a16
    lda #$3200
    sta $4302
    lda #32
    sta $4305
    sep #$20
    .a8
    lda #1
    sta $420B
    lda $4212
    sta.l $7E2016
    rep #$30
    .a16
    .i16
    rtl

S6_RasterPublish:
    rep #$30
    .a16
    .i16
    lda.l $7E2012
    bne S6_RasterPublishReady
    sep #$20
    .a8
    jsr RasterWaitVblank
    lda #15
    sta $2100
    jsr RasterWaitVblank
    jsr RasterWaitVblank
S6_RasterPublishReady:
    rep #$30
    .a16
    .i16
    lda.l $7E2010
    inc a
    sta.l $7E2010
    lda $06
    sta.l $7E2004
    lda $1A
    sta.l $7E2006
    lda $5E
    sta.l $7E2008
    lda.l $7E2010
    sta.l $7E2000
    lda.l $7E2012
    bne S6_RasterReturn
    lda.l $7E2010
S6_RasterObserve:
    .a16
    .i16
    cmp.l $7E2002
    bne S6_RasterObserve
S6_RasterReturn:
    .a16
    .i16
    rtl

S6_RasterHighMasks:
    .dw $FFFC,$FFF3,$FFCF,$FF3F

RasterWaitVblank:
    .a8
    .i16
    lda $4212
    bmi RasterWaitVblank
RasterWaitVblankStart:
    .a8
    .i16
    lda $4212
    bpl RasterWaitVblankStart
    rts
