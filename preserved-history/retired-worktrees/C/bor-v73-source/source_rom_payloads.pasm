; S-CPU-only WRAM scratch $46C0..46CF is disjoint from journal/ring/debug.
; Immutable source payloads occupy previously unused ROM banks. The cache,
; palette leases, original DMA budget/slots and OAM publisher stay authoritative.
SOURCE_ROM_BLOCK_COUNT = 708
SourceRom_Index = $7E46C0
SourceRom_Bank = $7E46C2
SourceRom_Address = $7E46C4
SourceRom_DmaScan = $7E46C6
SourceRom_Incomplete = $7E46CA
SourceRom_Hi = $7E46CC
SourceRom_Lo = $7E46CE

; Resolve full global ID. Only scratch is written; X/Y/P widths are preserved.
SourceRom_Resolve:
.a16
.i16
    php
    rep #$31
    phx
    phy
    lda #0
    sta.l SourceRom_Bank
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceRom_Resolve__scope1
    brl SourceRom_Resolve__no
SourceRom_Resolve__scope1:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceRom_Resolve__scope2
    brl SourceRom_Resolve__no
SourceRom_Resolve__scope2:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceRom_Resolve__scope3
    brl SourceRom_Resolve__no
SourceRom_Resolve__scope3:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceRom_Resolve__scope4
    brl SourceRom_Resolve__no
SourceRom_Resolve__scope4:
.a16
.i16
    bra SourceRom_Resolve__search_init
; Existing ROM-tagged pending rows keep their immutable source across scope
; changes. New admission always enters through the fully scoped Resolve above.
SourceRom_ResolveTagged:
.a16
.i16
    php
    rep #$31
    phx
    phy
    lda #0
    sta.l SourceRom_Bank
SourceRom_Resolve__search_init:
.a16
.i16
    lda.l SourceVisual_BlockIndex
    cmp #17286
    bcc SourceRom_Resolve__bounded
    brl SourceRom_Resolve__no
SourceRom_Resolve__bounded:
.a16
.i16
    cmp #16384
    bcc SourceRom_Resolve__dense_low
    sec
    sbc #16384
    asl a
    tax
    lda.l SourceRom_Dense39,x
    bra SourceRom_Resolve__dense_read
SourceRom_Resolve__dense_low:
.a16
.i16
    asl a
    tax
    lda.l SourceRom_Dense38,x
SourceRom_Resolve__dense_read:
.a16
.i16
    bne SourceRom_Resolve__dense_hit
    brl SourceRom_Resolve__no
SourceRom_Resolve__dense_hit:
.a16
.i16
    dec a
    sta.l SourceRom_Index
SourceRom_Resolve__found:
.a16
.i16
    lda.l SourceRom_Index
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    asl a
    tax
    lda.l SourceRom_PayloadBanks,x
    sta.l SourceRom_Bank
    lda.l SourceRom_Index
    and #127
    xba
    clc
    adc #$8000
    sta.l SourceRom_Address
    ply
    plx
    plp
    sec
    rts
SourceRom_Resolve__no:
.a16
.i16
    ply
    plx
    plp
    clc
    rts

; Resolve has selected this immutable 256-byte payload. A block cannot retire
; while ANY active queue row still reads that payload. No staging alias exists.
SourceRom_HasBlockDma:
.a16
.i16
    rep #$31
    lda #0
    sta.l SourceRom_DmaScan
SourceRom_HasBlockDma__scan:
.a16
.i16
    lda.l SourceRom_DmaScan
    tax
    sep #$20
.a8
    lda.l DmaQueue+4,x
    bit #DMA_OPT_ACTIVE
    beq SourceRom_HasBlockDma__next8
    lda.l DmaQueue+7,x
    cmp.l SourceRom_Bank
    bne SourceRom_HasBlockDma__next8
    rep #$31
.a16
.i16
    lda.l DmaQueue+5,x
    sec
    sbc.l SourceRom_Address
    cmp #256
    bcs SourceRom_HasBlockDma__next
    sec
    rts
SourceRom_HasBlockDma__next8:
.a8
.i16
    rep #$31
.a16
.i16
SourceRom_HasBlockDma__next:
.a16
.i16
    lda.l SourceRom_DmaScan
    clc
    adc #8
    sta.l SourceRom_DmaScan
    cmp #64
    bcc SourceRom_HasBlockDma__scan
    clc
    rts

; ROM payloads can coexist because they never change. WRAM payloads keep the
; original global idle fence, single producer, and pending return contract.
; C=1 permits admission only when no unfinished WRAM producer blocks it.
SourceRom_ResumePending:
.a16
.i16
    rep #$31
    lda #0
    sta.l SourceVisual_BlockScan
SourceRom_ResumePending__scan:
.a16
.i16
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcc SourceRom_ResumePending__row
    brl SourceRom_ResumePending__none
SourceRom_ResumePending__row:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    beq SourceRom_ResumePending__found
    brl SourceRom_ResumePending__next
SourceRom_ResumePending__found:
.a16
.i16
    txa
    sta.l SourceVisual_BlockRecord
    lda.l SourceVisual_BlockCache,x
    sta.l SourceVisual_BlockIndex
    lda.l SourceVisual_BlockScan
    sta.l SourceVisual_BlockSlot
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+6,x
    cmp #2
    rep #$31
.a16
.i16
    bne SourceRom_ResumePending__wram
    jsr SourceRom_ResolveTagged
    bcs SourceRom_ResumePending__rom_valid
    brl SourceRom_ResumePending__pending
SourceRom_ResumePending__rom_valid:
.a16
.i16
    jsr SourceRom_HasBlockDma
    bcs SourceRom_ResumePending__next
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+5,x
    cmp #4
    beq SourceRom_ResumePending__complete8
    rep #$31
.a16
.i16
    jsr SourceVisual_QueueBlockRows
    bra SourceRom_ResumePending__next
SourceRom_ResumePending__wram:
.a16
.i16
    jsr SourceRom_HasStagingDma
    bcs SourceRom_ResumePending__pending
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+5,x
    cmp #4
    beq SourceRom_ResumePending__complete8
    rep #$31
.a16
.i16
    jsr SourceVisual_QueueBlockRows
    clc
    rts
SourceRom_ResumePending__complete8:
.a8
.i16
    rep #$31
.a16
.i16
    lda #2
    sta.l SourceVisual_BlockCache+2,x
SourceRom_ResumePending__completed:
.a16
.i16
SourceRom_ResumePending__next:
.a16
.i16
    rep #$31
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    brl SourceRom_ResumePending__scan
SourceRom_ResumePending__pending:
.a16
.i16
    clc
    rts
SourceRom_ResumePending__none:
.a16
.i16
    sec
    rts

SourceVisual_ReadSelectedPieces:
.a16
.i16
    lda.l SourceVisual_EntryScratch+16
    sta.l SourceVisual_Temp
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Offset
    lda.l SourceVisual_Temp
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    sta.l SourceVisual_Offset+2
    lda.l SourceVisual_Offset
    clc
    adc #SOURCE_VISUAL_PIECE_OFFSET
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda.l SourceVisual_Offset+2
    adc #((SOURCE_VISUAL_PIECE_OFFSET >> 16) & $FF)
    sta.l SourceVisual_Offset+2
    lda #((SOURCE_VISUAL_PIECE_OFFSET >> 24) & $FF)
    adc #0
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    jsr SourceVisual_AddCatalogBase
    jsr SourceVisual_ReadPieces
    rts

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

; Only fresh ROM-tagged blocks use the complete immutable descriptor.
; Partial legacy rows retain the original per-row continuation above.
SourceRom_QueueWholeBlock:
.a16
.i16
    rep #$31
    lda.l SourceVisual_BlockSlot
    cmp #64
    bcc SourceRom_QueueWholeBlock__slot_ok
    brl SourceRom_QueueWholeBlock__pending
SourceRom_QueueWholeBlock__slot_ok:
.a16
.i16
    lda #256
    jsr SourceRom_CheckDmaSlot
    bcs SourceRom_QueueWholeBlock__capacity
    brl SourceRom_QueueWholeBlock__pending
SourceRom_QueueWholeBlock__capacity:
.a16
.i16
    ; Retained ROM-tagged jobs remain legal after scope transitions, but
    ; the original DMA byte cap applies even outside the BOR reservation gate.
    lda.l DmaQueue_BudgetTotal
    clc
    adc #256
    cmp #DMA_TRANSFER_MAX_BYTES
    bcc SourceRom_QueueWholeBlock__budget_valid
    brl SourceRom_QueueWholeBlock__pending
SourceRom_QueueWholeBlock__budget_valid:
.a16
.i16
    jsr SourceVisual_BlockSlotToTile
    lda.l SourceVisual_BlockTileBase
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #SOURCE_VISUAL_VRAM_BASE
    sta.l DmaRequest_TargetAddr
    clc
    adc #1600
    cmp #SOURCE_VISUAL_VRAM_END+1
    bcs SourceRom_QueueWholeBlock__pending
    lda.l SourceRom_Address
    sta.l DmaRequest_SourceAddrLow
    lda #256
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda.l SourceRom_Bank
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_SOURCE_BLOCK
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsl Core_Dma_Enqueue_Long
    bcc SourceRom_QueueWholeBlock__pending
    jsr SourceVisual_TrackRequest
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda #4
    sta.l SourceVisual_BlockCache+5,x
SourceRom_QueueWholeBlock__pending:
    rep #$31
.a16
.i16
    clc
    rts

; Release may retain an unowned completed immutable ROM block. It acquires
; no pins; the ordinary allocator may evict it after the same live-pin check.
; Pending state can never pass, and no readiness or DMA state is written.
SourceRom_RetainReadyBlock:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceRom_RetainReadyBlock__no
    lda.l SourceVisual_BlockCache+6,x
    and #$00FF
    cmp #2
    bne SourceRom_RetainReadyBlock__no
    phx
    jsr SVActor_Enabled
    plx
    rts
SourceRom_RetainReadyBlock__no:
.a16
.i16
    clc
    rts
