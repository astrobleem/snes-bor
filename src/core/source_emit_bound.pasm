; Safe upper-bound admission avoids the first geometry scan only when
; every authored piece would fit. The original per-piece viewport, FP,
; palette, OAM writer, packet metadata and resource fences remain unchanged.
; Mirror and tight-capacity cases retain the original exact visible pre-count.
SourceEmitBound_Fast = $7E46EE
SourceEmitBound_Try:
.a16
.i16
    php
    rep #$30
    pha
    cld
    lda #0
    sta.l SourceEmitBound_Fast
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourceEmitBound_Try__no
    tdc
    cmp #$0A00
    beq SourceEmitBound_Try__player
    cmp #$0A85
    bne SourceEmitBound_Try__no
SourceEmitBound_Try__player:
.a16
.i16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    bne SourceEmitBound_Try__no
    lda.l Stage_Mirror
    and #$00FF
    bne SourceEmitBound_Try__no
    lda.l SourceVisual_PieceCount
    cmp #66
    bcs SourceEmitBound_Try__no
    lda.l $7E53A0
    cmp #513
    bcs SourceEmitBound_Try__no
    and #3
    bne SourceEmitBound_Try__no
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    clc
    adc.l $7E53A0
    cmp #513
    bcs SourceEmitBound_Try__no
    lda #1
    sta.l SourceEmitBound_Fast
    pla
    plp
    sec
    rtl
SourceEmitBound_Try__no:
.a16
.i16
    pla
    plp
    clc
    rtl

; Exact replacement of LDA EmitPieceX: retain A/N/Z and all other registers.
; Count the original normal-visible predicate, including pieces later FP-clipped.
SourceEmitBound_CountAndLoadX:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceEmitBound_Fast
    beq SourceEmitBound_CountAndLoadX__restore
    lda.l SourceVisual_VisiblePieces
    inc a
    sta.l SourceVisual_VisiblePieces
SourceEmitBound_CountAndLoadX__restore:
.a16
.i16
    pla
    plp
    lda.l SourceVisual_EmitPieceX
    rtl
SourceEmitBound_End:
