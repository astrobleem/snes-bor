; S-CPU-only WRAM scratch $46C0..46CF is disjoint from journal/ring/debug.
; Immutable source payloads occupy previously unused ROM banks. The cache,
; palette leases, original DMA budget/slots and OAM publisher stay authoritative.
SOURCE_ROM_BLOCK_COUNT = 720
; Durable identity of the sole shared 256-byte WRAM block, S-CPU only.
; Published after the complete payload, invalidated before every writer.
; $46E0..E5 is disjoint from clock $46DC..DF and journal $4700 onward.
SourceRom_StagingRecord = $7E46E0
SourceRom_StagingBlock = $7E46E2
SourceRom_StagingMagic = $7E46E4
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
    jsr SourceRom_HasBlockId
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

; Pure membership for the already scoped physical-player classifier. Test
; each actually read piece ID without repeating scope checks or calculating
; payload bank/address. Queue submission still uses the full resolver.
; A16=global ID, C=present; X/A are scratch, no WRAM writes.
SourceRom_HasBlockId:
.a16
.i16
    cmp #17286
    bcs SourceRom_HasBlockId__no
    cmp #16384
    bcc SourceRom_HasBlockId__low
    sec
    sbc #16384
    asl a
    tax
    lda.l SourceRom_Dense39,x
    bra SourceRom_HasBlockId__present
SourceRom_HasBlockId__low:
.a16
.i16
    asl a
    tax
    lda.l SourceRom_Dense38,x
SourceRom_HasBlockId__present:
.a16
.i16
    bne SourceRom_HasBlockId__yes
SourceRom_HasBlockId__no:
.a16
.i16
    clc
    rts
SourceRom_HasBlockId__yes:
.a16
.i16
    sec
    rts

; Player pose replacement may coexist only with authenticated foreign ROM
; block jobs. All shared WRAM, this actor, unknown owners/descriptors and
; malformed cache/source/target identities retain the conservative fence.
; No readiness, ownership, queue or hardware writes occur here.
SourceRom_HasReplacementDma:
.a16
.i16
    rep #$30
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceRom_HasReplacementDma__scope1
    jmp SourceVisual_HasOwnedDma
SourceRom_HasReplacementDma__scope1:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceRom_HasReplacementDma__scope2
    jmp SourceVisual_HasOwnedDma
SourceRom_HasReplacementDma__scope2:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceRom_HasReplacementDma__scope3
    jmp SourceVisual_HasOwnedDma
SourceRom_HasReplacementDma__scope3:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceRom_HasReplacementDma__scope4
    jmp SourceVisual_HasOwnedDma
SourceRom_HasReplacementDma__scope4:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceRom_HasReplacementDma__scope5
    jmp SourceVisual_HasOwnedDma
SourceRom_HasReplacementDma__scope5:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceRom_HasReplacementDma__player
    jmp SourceVisual_HasOwnedDma
SourceRom_HasReplacementDma__player:
.a16
.i16
    phx
    phy
    lda.l SourceRom_Index
    pha
    lda.l SourceRom_Bank
    pha
    lda.l SourceRom_Address
    pha
    lda.l SourceRom_DmaScan
    pha
    lda.l SourceRom_Hi
    pha
    lda.l SourceRom_Lo
    pha
    lda.l SourceVisual_BlockIndex
    pha
    lda.l SourceVisual_BlockRecord
    pha
    jsr SourceRom_HasReplacementStagingDma
    bcc SourceRom_HasReplacementDma__check1
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check1:
.a16
.i16
    lda #0
    sta.l SourceRom_DmaScan
SourceRom_HasReplacementDma__scan:
.a16
.i16
    lda.l SourceRom_DmaScan
    tax
    lda.l DmaQueue+4,x
    and #DMA_OPT_ACTIVE
    bne SourceRom_HasReplacementDma__active
    brl SourceRom_HasReplacementDma__next
SourceRom_HasReplacementDma__active:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$35
    bcs SourceRom_HasReplacementDma__bank_min
    brl SourceRom_HasReplacementDma__foreign_bank
SourceRom_HasReplacementDma__bank_min:
.a16
.i16
    cmp #$38
    bcc SourceRom_HasReplacementDma__rom
    cmp #$3A
    bcs SourceRom_HasReplacementDma__bank_high
    brl SourceRom_HasReplacementDma__foreign_bank
SourceRom_HasReplacementDma__bank_high:
.a16
.i16
    cmp #$3D
    bcc SourceRom_HasReplacementDma__rom
    brl SourceRom_HasReplacementDma__foreign_bank
SourceRom_HasReplacementDma__rom:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #(DMA_OPT_ACTIVE | DMA_TYPE_SOURCE_BLOCK)
    beq SourceRom_HasReplacementDma__check2
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check2:
.a16
.i16
    lda.l DmaQueue,x
    cmp #256
    beq SourceRom_HasReplacementDma__check3
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check3:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourceRom_HasReplacementDma__check4
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check4:
.a16
.i16
    and #$00FF
    beq SourceRom_HasReplacementDma__check5
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check5:
.a16
.i16
    lda.l SourceRom_DmaScan
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    cmp #1
    bcs SourceRom_HasReplacementDma__check6
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check6:
.a16
.i16
    cmp #7
    bcc SourceRom_HasReplacementDma__check7
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check7:
.a16
.i16
    dec a
    cmp.l SourceVisual_ActorSlot
    bne SourceRom_HasReplacementDma__check8
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check8:
.a16
.i16
    tay
    lda #1
SourceRom_HasReplacementDma__owner_bit:
.a16
.i16
    cpy #0
    beq SourceRom_HasReplacementDma__owner_ready
    asl a
    dey
    bra SourceRom_HasReplacementDma__owner_bit
SourceRom_HasReplacementDma__owner_ready:
.a16
.i16
    sta.l SourceRom_Hi
    lda.l SourceRom_DmaScan
    tax
    lda.l DmaQueue+2,x
    sec
    sbc #SOURCE_VISUAL_VRAM_BASE
    bcs SourceRom_HasReplacementDma__check9
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check9:
.a16
.i16
    sta.l SourceRom_Lo
    and #$C63F
    beq SourceRom_HasReplacementDma__check10
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check10:
.a16
.i16
    lda.l SourceRom_Lo
    and #$3800
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    sta.l SourceRom_Index
    lda.l SourceRom_Lo
    and #$01C0
    lsr a
    lsr a
    lsr a
    ora.l SourceRom_Index
    tax
    txa
    sta.l SourceVisual_BlockRecord
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    beq SourceRom_HasReplacementDma__check11
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check11:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    cmp #$0204
    beq SourceRom_HasReplacementDma__check12
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check12:
.a16
.i16
    lda.l SourceVisual_BlockCache+4,x
    and #$00FF
    and.l SourceRom_Hi
    bne SourceRom_HasReplacementDma__check13
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check13:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    sta.l SourceVisual_BlockIndex
    jsr SourceRom_ResolveTagged
    bcs SourceRom_HasReplacementDma__check14
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check14:
.a16
.i16
    lda.l SourceRom_DmaScan
    tax
    lda.l DmaQueue+5,x
    cmp.l SourceRom_Address
    beq SourceRom_HasReplacementDma__check15
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check15:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp.l SourceRom_Bank
    beq SourceRom_HasReplacementDma__check16
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__check16:
.a16
.i16
    brl SourceRom_HasReplacementDma__next
SourceRom_HasReplacementDma__foreign_bank:
.a16
.i16
    ; Unknown specialized sources are not authenticated foreign jobs.
    ; Ordinary non-source transfers retain the historical global ABI.
    lda.l DmaQueue+4,x
    and #$001F
    cmp #DMA_TYPE_SOURCE_BLOCK
    bne SourceRom_HasReplacementDma__next
    brl SourceRom_HasReplacementDma__busy
SourceRom_HasReplacementDma__next:
.a16
.i16
    lda.l SourceRom_DmaScan
    clc
    adc #8
    sta.l SourceRom_DmaScan
    cmp #64
    bcs SourceRom_HasReplacementDma__free
    brl SourceRom_HasReplacementDma__scan
SourceRom_HasReplacementDma__free:
.a16
.i16
    clc
    bra SourceRom_HasReplacementDma__restore
SourceRom_HasReplacementDma__busy:
.a16
.i16
    sec
SourceRom_HasReplacementDma__restore:
.a16
.i16
    pla
    sta.l SourceVisual_BlockRecord
    pla
    sta.l SourceVisual_BlockIndex
    pla
    sta.l SourceRom_Lo
    pla
    sta.l SourceRom_Hi
    pla
    sta.l SourceRom_DmaScan
    pla
    sta.l SourceRom_Address
    pla
    sta.l SourceRom_Bank
    pla
    sta.l SourceRom_Index
    ply
    plx
    rts

; Replacement may ignore only exact foreign WRAM rows with a durable identity
; from the actual complete staging read. No staging writes or readiness here.
; Original HasStagingDma write fence and all four physical transfers remain.
SourceRom_HasReplacementStagingDma:
.a16
.i16
    rep #$31
    lda #0
    sta.l SourceRom_DmaScan
SourceRom_HasReplacementStagingDma__scan:
.a16
.i16
    lda.l SourceRom_DmaScan
    tax
    lda.l DmaQueue+4,x
    and #DMA_OPT_ACTIVE
    bne SourceRom_HasReplacementStagingDma__active
    brl SourceRom_HasReplacementStagingDma__next
SourceRom_HasReplacementStagingDma__active:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourceRom_HasReplacementStagingDma__wram
    brl SourceRom_HasReplacementStagingDma__next
SourceRom_HasReplacementStagingDma__wram:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$4900
    bcs SourceRom_HasReplacementStagingDma__above_palette_start
    brl SourceRom_HasReplacementStagingDma__next
SourceRom_HasReplacementStagingDma__above_palette_start:
.a16
.i16
    cmp #$4A00
    bcs SourceRom_HasReplacementStagingDma__after_palette
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__after_palette:
.a16
.i16
    cmp #$5B00
    bcs SourceRom_HasReplacementStagingDma__above_tiles
    brl SourceRom_HasReplacementStagingDma__next
SourceRom_HasReplacementStagingDma__above_tiles:
.a16
.i16
    cmp #$5F00
    bcc SourceRom_HasReplacementStagingDma__tile_staging
    brl SourceRom_HasReplacementStagingDma__next
SourceRom_HasReplacementStagingDma__tile_staging:
.a16
.i16
    sec
    sbc #$5B00
    sta.l SourceRom_Lo
    cmp #$00C1
    bcc SourceRom_HasReplacementStagingDma__row_range
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__row_range:
.a16
.i16
    and #$003F
    beq SourceRom_HasReplacementStagingDma__row_aligned
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__row_aligned:
.a16
.i16
    ; Only a missing walking role may bypass a foreign staged job. Keep
    ; idle/frame churn, attacks and native jump admission on their baseline.
    lda.l SourceVisual_Key+1
    and #$00FF
    cmp #1
    beq SourceRom_HasReplacementStagingDma__walking_request
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__walking_request:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    beq SourceRom_HasReplacementStagingDma__p1_picture
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceRom_HasReplacementStagingDma__p2_picture
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__p2_picture:
.a16
.i16
    lda.l SVActor_Data+1
    brl SourceRom_HasReplacementStagingDma__picture_role
SourceRom_HasReplacementStagingDma__p1_picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    bne SourceRom_HasReplacementStagingDma__p1_role
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__p1_role:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
SourceRom_HasReplacementStagingDma__picture_role:
.a16
.i16
    and #$00FF
    cmp #1
    bne SourceRom_HasReplacementStagingDma__missing_walk
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__missing_walk:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #DMA_OPT_ACTIVE
    beq SourceRom_HasReplacementStagingDma__exact_vram_flags
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__exact_vram_flags:
.a16
.i16
    lda.l DmaQueue,x
    cmp #64
    beq SourceRom_HasReplacementStagingDma__exact_length
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__exact_length:
.a16
.i16
    lda.l SourceRom_StagingMagic
    cmp #$5357
    beq SourceRom_HasReplacementStagingDma__identity_valid
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__identity_valid:
.a16
.i16
    lda.l SourceRom_StagingRecord
    and #$FE07
    beq SourceRom_HasReplacementStagingDma__record_range
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__record_range:
.a16
.i16
    lda.l SourceRom_StagingBlock
    cmp #SOURCE_VISUAL_BLOCK_COUNT
    bcc SourceRom_HasReplacementStagingDma__id_range
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__id_range:
.a16
.i16
    lda.l SourceRom_StagingRecord
    sta.l SourceRom_Index
    tax
    lda.l SourceVisual_BlockCache,x
    cmp.l SourceRom_StagingBlock
    beq SourceRom_HasReplacementStagingDma__id_matches
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__id_matches:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    beq SourceRom_HasReplacementStagingDma__pending_state
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__pending_state:
.a16
.i16
    lda.l SourceVisual_BlockCache+6,x
    and #$00FF
    cmp #1
    beq SourceRom_HasReplacementStagingDma__wram_kind
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__wram_kind:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    and #$00FF
    cmp #1
    bcs SourceRom_HasReplacementStagingDma__progress_min
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__progress_min:
.a16
.i16
    cmp #5
    bcc SourceRom_HasReplacementStagingDma__progress_max
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__progress_max:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceRom_Lo
    bne SourceRom_HasReplacementStagingDma__progress_not_equal
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__progress_not_equal:
.a16
.i16
    cmp.l SourceRom_Lo
    bcs SourceRom_HasReplacementStagingDma__row_was_queued
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__row_was_queued:
.a16
.i16
    lda.l SourceRom_DmaScan
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    cmp #1
    bcs SourceRom_HasReplacementStagingDma__owner_min
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__owner_min:
.a16
.i16
    cmp #162
    bcc SourceRom_HasReplacementStagingDma__owner_max
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__owner_max:
.a16
.i16
    dec a
    sta.l SourceRom_Hi
    and #$001F
    beq SourceRom_HasReplacementStagingDma__owner_record_aligned
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__owner_record_aligned:
.a16
.i16
    lda.l SourceRom_Hi
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    cmp.l SourceVisual_ActorSlot
    bne SourceRom_HasReplacementStagingDma__foreign_actor
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__foreign_actor:
.a16
.i16
    tay
    lda #1
SourceRom_HasReplacementStagingDma__owner_bit:
.a16
.i16
    cpy #0
    beq SourceRom_HasReplacementStagingDma__owner_bit_ready
    asl a
    dey
    bra SourceRom_HasReplacementStagingDma__owner_bit
SourceRom_HasReplacementStagingDma__owner_bit_ready:
.a16
.i16
    sta.l SourceRom_Hi
    lda.l SourceRom_Index
    tax
    lda.l SourceVisual_BlockCache+4,x
    and #$00C0
    beq SourceRom_HasReplacementStagingDma__owners_valid
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__owners_valid:
.a16
.i16
    lda.l SourceVisual_BlockCache+4,x
    and #$00FF
    and.l SourceRom_Hi
    bne SourceRom_HasReplacementStagingDma__owner_matches
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__owner_matches:
.a16
.i16
    lda.l SourceRom_Lo
    asl a
    asl a
    asl a
    sta.l SourceRom_Lo
    lda.l SourceRom_Index
    and #$01C0
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceRom_Address
    lda.l SourceRom_Index
    and #$0038
    asl a
    asl a
    asl a
    clc
    adc.l SourceRom_Address
    clc
    adc #SOURCE_VISUAL_VRAM_BASE
    clc
    adc.l SourceRom_Lo
    sta.l SourceRom_Address
    lda.l SourceRom_DmaScan
    tax
    lda.l DmaQueue+2,x
    cmp.l SourceRom_Address
    beq SourceRom_HasReplacementStagingDma__authenticated
    brl SourceRom_HasReplacementStagingDma__busy
SourceRom_HasReplacementStagingDma__authenticated:
.a16
.i16
    brl SourceRom_HasReplacementStagingDma__next
SourceRom_HasReplacementStagingDma__next:
.a16
.i16
    lda.l SourceRom_DmaScan
    clc
    adc #8
    sta.l SourceRom_DmaScan
    cmp #64
    bcs SourceRom_HasReplacementStagingDma__free
    brl SourceRom_HasReplacementStagingDma__scan
SourceRom_HasReplacementStagingDma__free:
.a16
.i16
    clc
    rts
SourceRom_HasReplacementStagingDma__busy:
.a16
.i16
    sec
    rts
