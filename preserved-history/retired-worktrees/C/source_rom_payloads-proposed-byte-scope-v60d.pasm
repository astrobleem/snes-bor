; Immutable source payloads occupy previously unused ROM banks. The cache,
; palette leases, original DMA budget/slots and OAM publisher stay authoritative.
SOURCE_ROM_BLOCK_COUNT = 365
SourceRom_Index = $4325B0
SourceRom_Bank = $4325B2
SourceRom_Address = $4325B4
SourceRom_DmaScan = $4325B6
SourceRom_Incomplete = $4325BA
SourceRom_Hi = $4325BC
SourceRom_Lo = $4325BE

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
    lda #0
    sta.l SourceRom_Lo
    lda #SOURCE_ROM_BLOCK_COUNT
    sta.l SourceRom_Hi
SourceRom_Resolve__search:
.a16
.i16
    lda.l SourceRom_Lo
    cmp.l SourceRom_Hi
    bcc SourceRom_Resolve__mid
    brl SourceRom_Resolve__no
SourceRom_Resolve__mid:
.a16
.i16
    clc
    adc.l SourceRom_Hi
    lsr a
    sta.l SourceRom_Index
    asl a
    tax
    lda.l SourceRom_Ids,x
    cmp.l SourceVisual_BlockIndex
    beq SourceRom_Resolve__found
    bcc SourceRom_Resolve__lower
    lda.l SourceRom_Index
    sta.l SourceRom_Hi
    bra SourceRom_Resolve__search
SourceRom_Resolve__lower:
.a16
.i16
    lda.l SourceRom_Index
    inc a
    sta.l SourceRom_Lo
    bra SourceRom_Resolve__search
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
    clc
    adc #$35
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
    jsr SourceVisual_HasOwnedDma
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
