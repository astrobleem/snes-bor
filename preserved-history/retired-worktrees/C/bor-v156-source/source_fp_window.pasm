; Only the original campaign's normal BG2 column path uses this test.
; No pending-buffer, residency, publication, game-state or DMA writes.
; Counter latching follows the established SourcePacket NMI window protocol.
SourceFp_ColumnWindow:
.a8
.i16
    php
    rep #$30
.a16
.i16
    pha
    phx
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourceFp_ColumnWindow__yes
    lda.l Game_State
    bne SourceFp_ColumnWindow__yes
    sep #$20
.a8
    lda.l $004212
    and #$80
    beq SourceFp_ColumnWindow__no
    lda.l $004201
    pha
    ora #$80
    sta.l $004201
    lda.l $002137
    lda.l $00213F
    lda.l $00213D
    pha
    lda.l $00213D
    and #1
    beq SourceFp_ColumnWindow__low
    pla
    pla
    sta.l $004201
    bra SourceFp_ColumnWindow__no
SourceFp_ColumnWindow__low:
.a8
.i16
    pla
    rep #$20
.a16
    and #$00FF
    tax
    sep #$20
.a8
    pla
    sta.l $004201
    rep #$20
.a16
    txa
    cmp #224
    bcc SourceFp_ColumnWindow__no
    ; At250 only12 NTSC scanlines remain. Reserve >=12 whole lines
    ; for the measured <9000-clock column plus remaining PPU register tail.
    cmp #250
    bcs SourceFp_ColumnWindow__no
SourceFp_ColumnWindow__yes:
.a16
.i16
    rep #$30
    plx
    pla
    plp
    sec
    rtl
SourceFp_ColumnWindow__no:
.a16
.i16
    rep #$30
    plx
    pla
    plp
    clc
    rtl
