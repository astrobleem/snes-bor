; Per-call geometry from the ORIGINAL full atomic OAM count. No retained
; picture, queue, Ready, pin or actor/world changes. Normal emitter remains
; responsible for all palettes, size bits, frontpanel priority and writing.
; Raw metadata rows use bytes 0..1071 of each 1280-byte row. These three
; unused tails reserve 130+130+65 bytes, outside all MVN save/read ranges.
SourceEmitGeometry_X = $433430
SourceEmitGeometry_Y = $433930
SourceEmitGeometry_Visible = $433E30
; EmitBoundsMode is an existing word, with all consumers using its LOW byte.
; Its high byte is initialized to zero at the start of EVERY normal Emit.
SourceEmitGeometry_Enabled = SourceVisual_EmitBoundsMode+1
SourceEmitGeometry_Begin:
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l SourceEmitGeometry_Enabled
    rep #$30
.a16
.i16
    lda.l $7E46DE
    bne SourceEmitGeometry_Begin__done
    jsr SourceNpc_Scope
    bcc SourceEmitGeometry_Begin__done
    lda.l Stage_Mirror
    and #$00FF
    bne SourceEmitGeometry_Begin__done
    lda.l SourceVisual_PieceCount
    cmp #66
    bcs SourceEmitGeometry_Begin__done
    sep #$20
.a8
    lda #1
    sta.l SourceEmitGeometry_Enabled
    rep #$30
.a16
.i16
SourceEmitGeometry_Begin__done:
    rtl

SourceEmitGeometry_CountNormal:
.a16
.i16
    jsl SourceEmitGeometry_NormalBridge
    php
    lda.l SourceEmitGeometry_Enabled
    and #$00FF
    beq SourceEmitGeometry_CountNormal__done
    lda.l SourceVisual_PieceIndex
    tax
    lda #0
    bcc SourceEmitGeometry_CountNormal__flag
    inc a
SourceEmitGeometry_CountNormal__flag:
.a16
.i16
    sep #$20
.a8
    sta.l SourceEmitGeometry_Visible,x
    rep #$20
.a16
    txa
    asl a
    tax
    lda.l SourceVisual_EmitPieceX
    sta.l SourceEmitGeometry_X,x
    lda.l SourceVisual_EmitPieceY
    sta.l SourceEmitGeometry_Y,x
SourceEmitGeometry_CountNormal__done:
    plp
    rtl

SourceEmitGeometry_GetPiece:
.a16
.i16
    lda.l SourceEmitGeometry_Enabled
    and #$00FF
    beq SourceEmitGeometry_GetPiece__fallback
    lda.l SourceVisual_PieceIndex
    tax
    lda.l SourceEmitGeometry_Visible,x
    and #$00FF
    beq SourceEmitGeometry_GetPiece__outside
    txa
    asl a
    tax
    lda.l SourceEmitGeometry_X,x
    sta.l SourceVisual_EmitPieceX
    lda.l SourceEmitGeometry_Y,x
    sta.l SourceVisual_EmitPieceY
    sec
    rtl
SourceEmitGeometry_GetPiece__outside:
    clc
    rtl
SourceEmitGeometry_GetPiece__fallback:
    jsl SourceEmitGeometry_UnionBridge
    rtl
