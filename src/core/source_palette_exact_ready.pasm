; Only exact Kula attack-0's already mapped, physically ready palette.
; All misses retain the original global DMA fence; this routine writes nothing.
SourcePalette_ExactReady:
.a16
.i16
    rep #$31
    phx
    phy
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePalette_ExactReady__guard1
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard1:
    lda.l Game_StageIndex
    beq SourcePalette_ExactReady__guard2
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard2:
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourcePalette_ExactReady__guard3
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard3:
    lda.l SourceVisual_EntryIndexSaved
    cmp #781
    beq SourcePalette_ExactReady__guard4
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard4:
    lda.l SourceVisual_PieceCount
    cmp #10
    beq SourcePalette_ExactReady__guard5
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard5:
    lda.l SourceVisual_EntryScratch
    cmp #$0216
    beq SourcePalette_ExactReady__guard6
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard6:
    lda.l SourceVisual_EntryScratch+2
    beq SourcePalette_ExactReady__guard7
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard7:
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State,x
    cmp #781
    beq SourcePalette_ExactReady__guard8
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard8:
    lda.l SourceVisual_State+4,x
    cmp #1
    beq SourcePalette_ExactReady__guard9
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard9:
    lda.l SourceVisual_State+14,x
    cmp #1
    beq SourcePalette_ExactReady__guard10
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard10:
    lda.l SourceVisual_State+16,x
    and #$00FF
    bne SourcePalette_ExactReady__guard11
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard11:
    dec a
    cmp #8
    bcc SourcePalette_ExactReady__guard12
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard12:
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache,x
    cmp #361
    beq SourcePalette_ExactReady__guard13
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard13:
    lda.l SourceVisual_PaletteCache+3,x
    and #$00FF
    cmp #1
    beq SourcePalette_ExactReady__guard14
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard14:
    lda.l SourceVisual_ActorSlot
    beq SourcePalette_ExactReady__p1
    lda.l SourceVisual_PaletteCache+4,x
    and #2
    bra SourcePalette_ExactReady__owner
SourcePalette_ExactReady__p1:
    lda.l SourceVisual_PaletteCache+4,x
    and #1
SourcePalette_ExactReady__owner:
    bne SourcePalette_ExactReady__guard15
    brl SourcePalette_ExactReady__no
SourcePalette_ExactReady__guard15:
    ply
    plx
    sec
    rtl
SourcePalette_ExactReady__no:
    ply
    plx
    clc
    rtl
