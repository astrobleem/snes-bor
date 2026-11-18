; At most one normal and one mirror OBJ per source piece: 8*N bytes.
; If that upper bound fits, the original emission pass still clips every row.
; Near full OAM, retain the exact original visible-count pass.
; A16/I16 entry; A and C scratch; X/Y/D/DB and decimal mode unchanged.
SourceOam_CountBound:
.a16
.i16
    lda #0
    sta.l SourceVisual_VisiblePieces
    sta.l SourceVisual_PieceIndex
    php
    sep #$20
.a8
    pla
    and #8
    rep #$30
.a16
.i16
    bne SourceOam_CountBound_No
    lda.l SourceVisual_PieceCount
    cmp #66
    bcs SourceOam_CountBound_No
    asl a
    asl a
    asl a
    clc
    adc.l Oam_CurrentSlot
    bcs SourceOam_CountBound_No
    cmp #513
    bcs SourceOam_CountBound_No
SourceOam_CountBound_Yes:
.a16
.i16
    sec
    rtl
SourceOam_CountBound_No:
.a16
.i16
    clc
    rtl
SourceOam_CountBound_End:
