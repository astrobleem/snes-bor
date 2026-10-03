; Isolated single-actor timed raster host. Initial upload under reset blank;
; subsequent uploads never force blank. Every elapsed NTSC field feeds the
; existing rational 200Hz clock; publish the latest source frame before draw.
; This is a bounded one-actor admission probe, not arbitrary-Pak throughput.
TimedStart:
    rep #$30
    .a16
    .i16
    jsl S6_RasterUpload
    lda #0
    sta.l $7E2014
    sta.l $7E2020
    lda #$1400
    tcd
    ldx #30
    lda #0
TimedClearClock:
    .a16
    .i16
    sta $00,x
    dex
    dex
    bpl TimedClearClock
    lda #$B796
    sta $08
    lda #$0147
    sta $0A
    sep #$20
    .a8
    lda #15
    sta $2100
    ; Anchor time0 at a vblank edge. Each following interval includes scanline
    ; 240 of the starting field (its $213F.7 determines the four-clock shortfall).
    jsr RasterWaitVblank
TimedLoop:
    rep #$30
    .a16
    .i16
    lda #$1400
    tcd
    lda #$99C0
    sta $00
    lda #$0442
    sta $02
    sep #$20
    .a8
    lda $213F
    and #$80
    sta $1E
    beq TimedClockReady
    rep #$20
    .a16
    lda $00
    sec
    sbc #800
    sta $00
    lda $02
    sbc #0
    sta $02
TimedClockReady:
    rep #$30
    .a16
    .i16
    jsl S5_ClockAdvance
    lda #$1000
    tcd
    lda.l $7E2014
    beq TimedWait
    jsl S6_RasterPrepare
TimedWait:
    sep #$20
    .a8
    .i16
    jsr RasterWaitVblank
    rep #$30
    .a16
    .i16
    lda.l $7E2014
    beq TimedPublish
    jsl S6_RasterCommit
    jsl S6_RasterPublish
    lda #0
    sta.l $7E2014
TimedPublish:
    rep #$30
    .a16
    .i16
    lda.l $7E2020
    asl a
    asl a
    asl a
    asl a
    tax
    lda $D0
    sta.l $7E6000,x
    lda $06
    sta.l $7E6002,x
    lda $14
    sta.l $7E6004,x
    lda $10
    sta.l $7E6006,x
    lda.l $7E2010
    sta.l $7E6008,x
    lda $141E
    and #$00FF
    sta.l $7E600C,x
    lda $1404
    sta.l $7E600E,x
    lda.l $7E2016
    and #$00FF
    sta.l $7E600A,x
    sep #$20
    .a8
    lda $4212
    sta.l $7E7000,x
    lda $213F
    and #$80
    sta.l $7E7002,x
    rep #$20
    .a16
    lda.l $7E2020
    inc a
    sta.l $7E2020
    cmp #30
    bcs TimedFinished
    jmp TimedLoop
TimedFinished:
    .a16
    .i16
    lda #$5636
    sta.l $7E200A
Done:
    .a16
    .i16
    bra Done

S5_HostSourceTick:
    rep #$30
    .a16
    .i16
    phd
    lda #$1000
    tcd
    inc $D0
    bne TimedTickReady
    inc $D2
TimedTickReady:
    .a16
    .i16
    jsl S6_AnimationPass
    pld
    rtl
