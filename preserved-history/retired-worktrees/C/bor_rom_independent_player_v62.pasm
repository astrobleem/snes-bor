
SourceRom_PlayerMode = $7E46C8
SourceRom_RequestBytes = SourceRom_Index

; Only current physical players whose complete selected pose is ROM-backed
; may bypass another actor's shared WRAM producer lease. Metadata reads use
; the ordinary immutable source path; no ownership/readiness/publication writes.
SourceRom_ClassifyPlayer:
.a16
.i16
    rep #$31
    lda #0
    sta.l SourceRom_PlayerMode
    jsr SVActor_Enabled
    bcs SourceRom_ClassifyPlayer__scope
    brl SourceRom_ClassifyPlayer__no
SourceRom_ClassifyPlayer__scope:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceRom_ClassifyPlayer__actor
    brl SourceRom_ClassifyPlayer__no
SourceRom_ClassifyPlayer__actor:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceRom_ClassifyPlayer__player
    brl SourceRom_ClassifyPlayer__no
SourceRom_ClassifyPlayer__player:
.a16
.i16
    cmp #1
    bne SourceRom_ClassifyPlayer__record
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceRom_ClassifyPlayer__record
    brl SourceRom_ClassifyPlayer__no
SourceRom_ClassifyPlayer__record:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    beq SourceRom_ClassifyPlayer__entry
    brl SourceRom_ClassifyPlayer__no
SourceRom_ClassifyPlayer__entry:
.a16
.i16
    tax
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceRom_ClassifyPlayer__count
    brl SourceRom_ClassifyPlayer__no
SourceRom_ClassifyPlayer__count:
.a16
.i16
    lda.l SourceVisual_EntryScratch+12
    and #$00FF
    bne SourceRom_ClassifyPlayer__nonempty
    brl SourceRom_ClassifyPlayer__no
SourceRom_ClassifyPlayer__nonempty:
.a16
.i16
    cmp #SOURCE_VISUAL_MAX_PIECES+1
    bcc SourceRom_ClassifyPlayer__read
    brl SourceRom_ClassifyPlayer__no
SourceRom_ClassifyPlayer__read:
.a16
.i16
    sta.l SourceVisual_PieceCount
    jsr SourceVisual_ReadSelectedPieces
    lda #0
    sta.l SourceVisual_PieceIndex
SourceRom_ClassifyPlayer__piece:
.a16
.i16
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcs SourceRom_ClassifyPlayer__yes
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+12,x
    sta.l SourceVisual_BlockIndex
    jsr SourceRom_Resolve
    bcc SourceRom_ClassifyPlayer__no
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    bra SourceRom_ClassifyPlayer__piece
SourceRom_ClassifyPlayer__yes:
.a16
.i16
    lda #1
    sta.l SourceRom_PlayerMode
    sec
    rts
SourceRom_ClassifyPlayer__no:
.a16
.i16
    clc
    rts

; Staging sources are independent of immutable ROM. Preserve the original
; WRAM tile/palette fence without waiting for unrelated ROM transfers.
SourceRom_HasStagingDma:
.a16
.i16
    rep #$31
    lda #0
    sta.l SourceRom_DmaScan
SourceRom_HasStagingDma__scan:
.a16
.i16
    lda.l SourceRom_DmaScan
    tax
    lda.l DmaQueue+4,x
    and #DMA_OPT_ACTIVE
    beq SourceRom_HasStagingDma__next
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    bne SourceRom_HasStagingDma__next
    lda.l DmaQueue+5,x
    cmp #$4900
    bcc SourceRom_HasStagingDma__next
    cmp #$4A00
    bcc SourceRom_HasStagingDma__yes
    cmp #$5B00
    bcc SourceRom_HasStagingDma__next
    cmp #$5F00
    bcc SourceRom_HasStagingDma__yes
SourceRom_HasStagingDma__next:
.a16
.i16
    lda.l SourceRom_DmaScan
    clc
    adc #8
    sta.l SourceRom_DmaScan
    cmp #64
    bcc SourceRom_HasStagingDma__scan
    clc
    rts
SourceRom_HasStagingDma__yes:
.a16
.i16
    sec
    rts

SourceRom_HasPaletteDma:
.a16
.i16
    rep #$31
    lda #0
    sta.l SourceRom_DmaScan
SourceRom_HasPaletteDma__scan:
.a16
.i16
    lda.l SourceRom_DmaScan
    tax
    lda.l DmaQueue+4,x
    and #DMA_OPT_ACTIVE
    beq SourceRom_HasPaletteDma__next
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    bne SourceRom_HasPaletteDma__next
    lda.l DmaQueue+5,x
    cmp #$4900
    bcc SourceRom_HasPaletteDma__next
    cmp #$4A00
    bcc SourceRom_HasPaletteDma__yes
SourceRom_HasPaletteDma__next:
.a16
.i16
    lda.l SourceRom_DmaScan
    clc
    adc #8
    sta.l SourceRom_DmaScan
    cmp #64
    bcc SourceRom_HasPaletteDma__scan
    clc
    rts
SourceRom_HasPaletteDma__yes:
.a16
.i16
    sec
    rts

; A=request bytes. Before early submission, retain two queue slots and the
; worst-case 512+32 OAM bytes. After submission, use the ordinary slot gate.
SourceRom_CheckDmaSlot:
.a16
.i16
    rep #$31
    sta.l SourceRom_RequestBytes
    jsr SVActor_Enabled
    bcc SourceRom_CheckDmaSlot__ordinary
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SourceRom_CheckDmaSlot__ordinary
    lda.l SourceVisual_CompletedEarly
    bne SourceRom_CheckDmaSlot__ordinary
    lda #0
    sta.l SourceRom_Hi
    ldx #0
SourceRom_CheckDmaSlot__scan:
.a16
.i16
    lda.l DmaQueue+4,x
    and #DMA_OPT_ACTIVE
    bne SourceRom_CheckDmaSlot__next
    lda.l SourceRom_Hi
    inc a
    sta.l SourceRom_Hi
SourceRom_CheckDmaSlot__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceRom_CheckDmaSlot__scan
    lda.l SourceRom_Hi
    cmp #3
    bcc SourceRom_CheckDmaSlot__no
    lda.l DmaQueue_BudgetTotal
    clc
    adc.l SourceRom_RequestBytes
    clc
    adc #544
    cmp #DMA_TRANSFER_MAX_BYTES
    bcs SourceRom_CheckDmaSlot__no
    sec
    rts
SourceRom_CheckDmaSlot__ordinary:
.a16
.i16
    jsl Core_Dma_HasFreeSlot_Long
    rts
SourceRom_CheckDmaSlot__no:
.a16
.i16
    clc
    rts
