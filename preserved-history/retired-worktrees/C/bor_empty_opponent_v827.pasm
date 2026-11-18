; Empty opponent rows are canonical: a rendered target ALWAYS has a left
; bar cap at byte2, even atHP0; null target renders ALLzero. Dirty reset and
; pending-DMA checks remain before this shortcut. No new RAM or DMA.
.org $A600
SourceHudEmpty_Check:
.a16
.i16
    lda.l HudOpponent_Targets
    ora.l HudOpponent_Targets+2
    bne SourceHudEmpty_Combat
    jml SourceHudEmpty_Full
SourceHudEmpty_Combat:
.a16
.i16
    lda.l HudOpponent_Player
    tax
    lda.l HudOpponent_Targets,x
    bne SourceHudEmpty_Full
    txa
    cmp #3
    bcs SourceHudEmpty_Full
    bit #1
    bne SourceHudEmpty_Full
    lsr a
    tax
    sep #$20
.a8
    lda.l HudOpponent_Dirty,x
    bne SourceHudEmpty_Full
    rep #$20
.a16
    lda.l HudOpponent_Player
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l HudOpponent_BufferOffset
    bne SourceHudEmpty_Full
    lda.l HudOpponent_BufferOffset
    tax
    lda.l HudOpponent_Rows+2,x
    bne SourceHudEmpty_Full
    txa
    clc
    adc #64
    tax
    ldy #64
    lda #0
    cpy #64
    jml HudOpponent_Row__empty_return
SourceHudEmpty_Full:
    rep #$30
.a16
.i16
    sec
    ldx #0
    lda #0
    jml HudOpponent_Row__clear
SourceHudEmpty_End:
.assert SourceHudEmpty_End <= $27A700, "HUD empty shortcut exceeds verified gap"
