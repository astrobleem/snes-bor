; Seek has already completed. Preserve the existing optional warm-up and
; copy exactly42 MSU bytes. Six reads per iteration remove35 redundant
; CPX/branch pairs. The original A/X/Y/P/DB/D short-return ABI remains.
SourceRowFast_Body:
.a8
.i16
    jsl SourceWarmup_Row
.a16
.i16
    sep #$20
.a8
SourceRowFast_Loop:
.a8
.i16
    lda $2001
    sta.l SourceVisual_RowScratch,x
    inx
    lda $2001
    sta.l SourceVisual_RowScratch,x
    inx
    lda $2001
    sta.l SourceVisual_RowScratch,x
    inx
    lda $2001
    sta.l SourceVisual_RowScratch,x
    inx
    lda $2001
    sta.l SourceVisual_RowScratch,x
    inx
    lda $2001
    sta.l SourceVisual_RowScratch,x
    inx
    cpx #42
    bcc SourceRowFast_Loop
    rep #$31
.a16
.i16
    jml SourceVisual_ReadPieces__done
SourceRowFast_End:
