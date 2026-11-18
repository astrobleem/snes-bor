; A queue-slot identity cookie, published only by an actual tracked palette
; request. Owner is already cleared before every enqueue publishes ACTIVE.
; The sixteen bytes occupy the audited $5F50..$5F5F gap below $5F80.
SourcePalette_Cookies = $7E5F50

; Same seven-byte producer seam: original TrackRequest then LDA cache offset.
SourcePalette_Track:
.a16
.i16
    phk
    .db $F4
    .dw ((SourcePalette_TrackReturned-1)&$FFFF)
    .db $F4
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceVisual_TrackRequest
SourcePalette_TrackReturned:
.a16
.i16
    php
    pha
    phx
    bcc SourcePalette_TrackRestore
    txa
    asl a
    tax
    lda.l SourceVisual_PaletteGlobalIndex
    sta.l SourcePalette_Cookies,x
SourcePalette_TrackRestore:
.a16
.i16
    plx
    pla
    plp
    lda.l SourceVisual_PaletteCacheOffset
    rtl

; Enter at the original STA MDMAEN, with the original A8/X16 and short-return
; stack. Hardware completes all 32 bytes before the instruction returns.
; Never allocate, compose, consume input, or touch foreground scratch here.
SourcePalette_AfterPhysical:
.a8
.i16
    sta $420B
    rep #$31
.a16
.i16
    php
    pha
    phx
    phy
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePalette_Guard0
    brl SourcePalette_PhysicalDone
SourcePalette_Guard0:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourcePalette_Guard1
    brl SourcePalette_PhysicalDone
SourcePalette_Guard1:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourcePalette_Guard2
    brl SourcePalette_PhysicalDone
SourcePalette_Guard2:
.a16
.i16
    lda.l Game_StageIndex
    beq SourcePalette_Guard3
    brl SourcePalette_PhysicalDone
SourcePalette_Guard3:
.a16
.i16
    txa
    and #7
    beq SourcePalette_Guard4
    brl SourcePalette_PhysicalDone
SourcePalette_Guard4:
.a16
.i16
    cpx #64
    bcc SourcePalette_Guard5
    brl SourcePalette_PhysicalDone
SourcePalette_Guard5:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #(DMA_OPT_ACTIVE | DMA_TYPE_CGRAM)
    beq SourcePalette_Guard6
    brl SourcePalette_PhysicalDone
SourcePalette_Guard6:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePalette_Guard7
    brl SourcePalette_PhysicalDone
SourcePalette_Guard7:
.a16
.i16
    lda.l DmaQueue,x
    cmp #32
    beq SourcePalette_Guard8
    brl SourcePalette_PhysicalDone
SourcePalette_Guard8:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$4900
    bcs SourcePalette_Guard9
    brl SourcePalette_PhysicalDone
SourcePalette_Guard9:
.a16
.i16
    cmp #$4A00
    bcc SourcePalette_Guard10
    brl SourcePalette_PhysicalDone
SourcePalette_Guard10:
.a16
.i16
    and #31
    beq SourcePalette_Guard11
    brl SourcePalette_PhysicalDone
SourcePalette_Guard11:
.a16
.i16
    lda.l DmaQueue+5,x
    and #$00FF
    tay
    clc
    adc #$0100
    cmp.l DmaQueue+2,x
    beq SourcePalette_Guard12
    brl SourcePalette_PhysicalDone
SourcePalette_Guard12:
.a16
.i16
    tya
    lsr a
    lsr a
    tay
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    bne SourcePalette_Guard13
    brl SourcePalette_PhysicalDone
SourcePalette_Guard13:
.a16
.i16
    dec a
    cmp #161
    bcc SourcePalette_Guard14
    brl SourcePalette_PhysicalDone
SourcePalette_Guard14:
.a16
.i16
    and #31
    beq SourcePalette_Guard15
    brl SourcePalette_PhysicalDone
SourcePalette_Guard15:
.a16
.i16
    txa
    asl a
    tax
    lda.l SourcePalette_Cookies,x
    pha
    tya
    tax
    pla
    cmp.l SourceVisual_PaletteCache,x
    beq SourcePalette_Guard16
    brl SourcePalette_PhysicalDone
SourcePalette_Guard16:
.a16
.i16
    lda.l SourceVisual_PaletteCache+3,x
    and #$00FF
    cmp #2
    beq SourcePalette_Guard17
    brl SourcePalette_PhysicalDone
SourcePalette_Guard17:
.a16
.i16
    lda.l SourceVisual_PaletteCache+4,x
    and #$00FF
    bne SourcePalette_Guard18
    brl SourcePalette_PhysicalDone
SourcePalette_Guard18:
.a16
.i16
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_PaletteCache+3,x
SourcePalette_PhysicalDone:
    rep #$30
.a16
.i16
    ply
    plx
    pla
    plp
    jml Core_Dma_RemainingFree__done
SourcePalette_End:
