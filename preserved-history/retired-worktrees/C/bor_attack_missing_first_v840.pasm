; Pressure recovery starts at the first absent physical tile, rather than
; spending the only bounded idle visit on already-resident prefix pieces.
; Hints are suggestions only; every hit checks full ID and Ready state.
; No cache/pin/queue mutation, no added job count or readiness publication.
.bank 5
.org $C700
SourceAttackMissing_First:
.a16
.i16
    php
    rep #$30
    phx
    phy
    ldy #0
SourceAttackMissing_Piece:
.a16
.i16
    tya
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceStandby_PiecesLong+12,x
    pha
    and #63
    tax
    lda.l SourceVisual_BlockHint,x
    and #255
    beq SourceAttackMissing_ScanStart
    dec a
    cmp #64
    bcs SourceAttackMissing_ScanStart
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache,x
    cmp 1,s
    bne SourceAttackMissing_ScanStart
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceAttackMissing_Found
SourceAttackMissing_ScanStart:
.a16
.i16
    ldx #0
SourceAttackMissing_Scan:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    cmp 1,s
    bne SourceAttackMissing_NextSlot
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceAttackMissing_Found
SourceAttackMissing_NextSlot:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceAttackMissing_Scan
    pla
    tya
    bra SourceAttackMissing_Save
SourceAttackMissing_Found:
.a16
.i16
    pla
    iny
    cpy #10
    bcc SourceAttackMissing_Piece
    lda #0
SourceAttackMissing_Save:
.a16
.i16
    sta.l SourcePrefetch_Cursor
    ply
    plx
    plp
    lda #0
    rtl
SourceAttackMissing_End:
.assert SourceAttackMissing_End <= $05C900, "missing-first recovery exceeds gap"
