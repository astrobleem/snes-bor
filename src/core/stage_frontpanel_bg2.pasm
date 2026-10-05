; Normal-only full foreground. See compiler stage_frontpanel_bg2.py.
; BG2 Mode1 pal0, source colors already lowered to CGRAM indices 0..15.
; Logical cache 1..256 maps through generated three-run physical tile table.
; Never writes BG1 CHR, OBJ CHR, BG3 HUD/font, or Easy FP media.
StageFp_BG2Map = $6C00
; Normal's full-height BG2 stream is a separate presentation mode.  Its
; sparse physical tile IDs live in the dedicated BG2 character window;
; the full $4000-$5FFF OBJ region is exclusively owned by gameplay sprites.
StageFp_BG2Char = $3000
StageFp_BG2Rows = 28
; BG2 has 256 physical 4bpp tiles at $3000-$3FFF. Reserve tile 255
; as the transparent blank and expose 255 recyclable cache slots.
StageFp_BG2Slots = 255
; Private allocation follows VM code+guard, precedes G12 trace at $7EF000.
; The ENTIRE $7F9200..$7F9FFF arena belongs to queue_abi, not spare WRAM.
StageFp_BG2TileBuf = $7EE020       ; 64 B, two queued 32-byte tiles
StageFp_BG2TileBank = $7E
StageFp_BG2ColBuf = $7EE060       ; 56 B, complete column publication
StageFp_BG2State = $7EE0A0         ; 34 B, ends $7EE0C1
StageFp_BG2Active = StageFp_BG2State
StageFp_BG2DmaPending = StageFp_BG2State+1
StageFp_BG2Fault = StageFp_BG2State+2
StageFp_BG2Booting = StageFp_BG2State+3
StageFp_BG2HistIndex = StageFp_BG2State+4
StageFp_BG2HistBase = StageFp_BG2State+6
StageFp_BG2Tmp = StageFp_BG2State+8
StageFp_BG2Loop = StageFp_BG2State+10
StageFp_BG2SlotScan = StageFp_BG2State+12
StageFp_BG2BootCol = StageFp_BG2State+14
StageFp_BG2BootLast = StageFp_BG2State+16
StageFp_BG2OldBg12 = StageFp_BG2State+18
StageFp_BG2PublishCol = StageFp_BG2State+20
StageFp_BG2SourceCol = StageFp_BG2State+22
StageFp_BG2SavedBusy = StageFp_BG2State+26
StageFp_BG2Loaded = StageFp_BG2State+32
StageFp_BG2History = $7EE100      ; 34*28 words = 1904 B
StageFp_BG2Refs = $7EE870         ; 257 words = 514 B
StageFp_BG2Columns = $7EEA72      ; 34 world-column words = 68 B
StageFp_BG2HistoryEnd = $7EEAB6   ; exclusive, before G12 trace $7EF000

StageFp_BG2ColdInit:
    php
    sep #$20
    .a8
    lda #BOR_BOOT_CAMPAIGN
    sta.l Game_CampaignId
    plp
    jsl StageWater_ColdInit
    jsl StageFp_Init
    jml StageFp_BG2Init
StageFp_BG2SceneReset:
    jsl StageWater_Reset
    jsl StageFp_Init
    jml StageFp_BG2Reset

StageFp_BG2Init:
    php
    rep #$30
.a16
.i16
    pha
    phx
    lda #0
    ldx #0
StageFp_BG2Init__loop:
.a16
.i16
    sta.l StageFp_BG2State,x
    inx
    inx
    cpx #34
    bcc StageFp_BG2Init__loop
    plx
    pla
    plp
    rtl

; Called under the scene loader's existing forced-blank/queue-drained lease.
; No PPU MMIO here. NMI alone publishes BG2 screen/character-base changes.
StageFp_BG2Reset:
    php
    rep #$30
.a16
.i16
    pha
    phx
    sep #$20
.a8
    lda #0
    sta.l StageFp_BG2Loaded
    sta.l StageFp_BG2DmaPending
    sta.l StageFp_BG2Fault
    sta.l StreamScrollFp_Enabled
    sta.l StreamScrollFp_ColPending
    sta.l StreamCache_NormalLayout
    sta.l StreamCache_BG2Capacity
    sta.l StreamCache_LegacyFpActive
    rep #$30
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq StageFp_BG2Reset__normal
    brl StageFp_BG2Reset__legacy
StageFp_BG2Reset__normal:
    sep #$20
.a8
    lda #1
    sta.l StreamCache_NormalLayout
    rep #$30
.a16
.i16
    lda.l Game_StageIndex
    and #$00FF
    cmp #StageFp_MapCount
    bcs StageFp_BG2Reset__done
    tax
    sep #$20
.a8
    lda.l StageFp_ModeMap,x
    beq StageFp_BG2Reset__done
    lda.l StageFp_BG2CapacityMap,x
    sta.l StreamCache_BG2Capacity
    bra StageFp_BG2Reset__done
StageFp_BG2Reset__legacy:
.a16
.i16
    lda.l Game_StageIndex
    and #$00FF
    cmp #StageFp_MapCount
    bcs StageFp_BG2Reset__done
    tax
    sep #$20
.a8
    lda.l StageFp_ModeMap,x
    beq StageFp_BG2Reset__done
    lda #1
    sta.l StreamCache_LegacyFpActive
StageFp_BG2Reset__done:
    rep #$30
.a16
.i16
    plx
    pla
    plp
    rtl

; Internal A16/I16. Binding independent of state: boot may be in CHARSELECT.
StageFp_BG2Binding:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne StageFp_BG2Binding__off
    lda.l Game_StageIndex
    and #$00FF
    cmp #StageFp_MapCount
    bcs StageFp_BG2Binding__off
    tax
    lda.l StageFp_ModeMap,x
    and #$00FF
    rts
StageFp_BG2Binding__off:
.a16
.i16
    lda #0
    rts

; A16 world source-screen X -> floor(A*7/5), clobbers X, no HW math race.
; Compiler bounds the generated maximum camera; not all 16-bit inputs fit.
StageFp_BG2Camera:
.a16
.i16
    sta.l StageFp_Num
    lda #0
    sta.l StageFp_Rem
    ldx #16
StageFp_BG2Camera__bit:
.a16
.i16
    lda.l StageFp_Num
    asl a
    sta.l StageFp_Num
    lda.l StageFp_Rem
    rol a
    cmp #5
    bcc StageFp_BG2Camera__rem
    sbc #5
    sta.l StageFp_Rem
    lda.l StageFp_Num
    ora #1
    sta.l StageFp_Num
    bra StageFp_BG2Camera__next
StageFp_BG2Camera__rem:
.a16
.i16
    sta.l StageFp_Rem
StageFp_BG2Camera__next:
.a16
.i16
    dex
    bne StageFp_BG2Camera__bit
    lda.l StageFp_Rem
    tax
    lda.l StageFp_Remainder,x
    and #$00FF
    sta.l StageFp_Rem
    lda.l StageFp_Num
    asl a
    asl a
    asl a
    sec
    sbc.l StageFp_Num
    clc
    adc.l StageFp_Rem
    rts

; A16=logical slot (0 is the dedicated transparent tile) -> physical tile.
StageFp_BG2Physical:
.a16
.i16
    phx
    asl a
    tax
    lda.l StageFp_BG2SlotMap,x
    plx
    rts
StageFp_BG2TileWord:
.a16
.i16
    jsr StageFp_BG2Physical
    asl a
    asl a
    asl a
    asl a
    clc
    adc #StageFp_BG2Char
    rts

; A16=world column -> map word at row zero, preserving X/Y.
StageFp_BG2MapWord:
.a16
.i16
    and #63
    cmp #32
    bcc StageFp_BG2MapWord__a
    and #31
    clc
    adc #1024
StageFp_BG2MapWord__a:
.a16
.i16
    clc
    adc #StageFp_BG2Map
    rts

; The old displayed 33 columns plus one pending column stay pinned.
; Only refs==0 slots can be reused. No forced eviction fallback.
StageFp_BG2Allocate:
.a16
.i16
    ldy #StageFp_BG2Slots
StageFp_BG2Allocate__scan:
.a16
.i16
    lda.l StageFp_BG2SlotScan
    inc a
    cmp #StageFp_BG2Slots+1
    bcc StageFp_BG2Allocate__candidate
    lda #1
StageFp_BG2Allocate__candidate:
.a16
.i16
    sta.l StageFp_BG2SlotScan
    asl a
    tax
    lda.l StageFp_BG2Refs,x
    beq StageFp_BG2Allocate__free
    dey
    bne StageFp_BG2Allocate__scan
    clc
    rts
StageFp_BG2Allocate__free:
.a16
.i16
    lda.l StreamCacheFp_Slot2Tile,x
    cmp #$FFFF
    beq StageFp_BG2Allocate__map
    phx
    asl a
    tax
    lda #$FFFF
    sta.l StreamCacheFp_Tile2Slot,x
    plx
StageFp_BG2Allocate__map:
.a16
.i16
    lda.l StreamStageFp_TileId
    sta.l StreamCacheFp_Slot2Tile,x
    asl a
    tax
    lda.l StageFp_BG2SlotScan
    sta.l StreamCacheFp_Tile2Slot,x
    sta.l StreamStageFp_Slot
    sec
    rts

; Initialize only residency metadata; the existing cache owns its own tables.
StageFp_BG2HistoryInit:
.a16
.i16
    lda #0
    ldx #0
StageFp_BG2HistoryInit__refs:
.a16
.i16
    sta.l StageFp_BG2Refs,x
    inx
    inx
    cpx #514
    bcc StageFp_BG2HistoryInit__refs
    lda #$FFFF
    ldx #0
StageFp_BG2HistoryInit__cols:
.a16
.i16
    sta.l StageFp_BG2Columns,x
    inx
    inx
    cpx #68
    bcc StageFp_BG2HistoryInit__cols
    lda #0
    sta.l StageFp_BG2SlotScan
    ; BG2 uses logical cache slots 1..K, where K is the compiler-proven
    ; 34-column active-plus-pending residency. Permanently pin the remainder
    ; so an unexpected source demand fails closed instead of overwriting BG1.
    lda.l StreamCache_BG2Capacity
    and #$00FF
    inc a
    asl a
    tax
    lda #1
StageFp_BG2HistoryInit__reserve:
.a16
.i16
    cpx #512
    bcs StageFp_BG2HistoryInit__done
    sta.l StageFp_BG2Refs,x
    inx
    inx
    bra StageFp_BG2HistoryInit__reserve
StageFp_BG2HistoryInit__done:
    rts

; Retire columns only AFTER their replacement was committed by NMI.
StageFp_BG2Retire:
.a16
.i16
    lda #0
    sta.l StageFp_BG2Loop
StageFp_BG2Retire__column:
.a16
.i16
    lda.l StageFp_BG2Loop
    asl a
    tax
    lda.l StageFp_BG2Columns,x
    cmp #$FFFF
    beq StageFp_BG2Retire__next
    cmp.l StreamScrollFp_StagedLo
    bcc StageFp_BG2Retire__drop
    cmp.l StreamScrollFp_StagedHi
    bcc StageFp_BG2Retire__next
    beq StageFp_BG2Retire__next
StageFp_BG2Retire__drop:
.a16
.i16
    lda #$FFFF
    sta.l StageFp_BG2Columns,x
    lda.l StageFp_BG2Loop
    ldx #56
    jsl StageFp_HostMul
    sta.l StageFp_BG2Tmp
    ldy #28
StageFp_BG2Retire__row:
.a16
.i16
    lda.l StageFp_BG2Tmp
    tax
    lda.l StageFp_BG2History,x
    asl a
    tax
    lda.l StageFp_BG2Refs,x
    dec a
    sta.l StageFp_BG2Refs,x
    lda.l StageFp_BG2Tmp
    inc a
    inc a
    sta.l StageFp_BG2Tmp
    dey
    bne StageFp_BG2Retire__row
StageFp_BG2Retire__next:
.a16
.i16
    lda.l StageFp_BG2Loop
    inc a
    sta.l StageFp_BG2Loop
    cmp #34
    bcc StageFp_BG2Retire__column
    rts

StageFp_BG2NewHistory:
.a16
.i16
    ldx #0
StageFp_BG2NewHistory__scan:
.a16
.i16
    lda.l StageFp_BG2Columns,x
    cmp #$FFFF
    beq StageFp_BG2NewHistory__found
    inx
    inx
    cpx #68
    bcc StageFp_BG2NewHistory__scan
    clc
    rts
StageFp_BG2NewHistory__found:
.a16
.i16
    lda.l StreamScrollFp_PendCol
    sta.l StageFp_BG2Columns,x
    txa
    lsr a
    sta.l StageFp_BG2HistIndex
    ldx #56
    jsl StageFp_HostMul
    sta.l StageFp_BG2HistBase
    sec
    rts

; A complete column's pin list is immutable until Retire, never NMI-owned.
StageFp_BG2PinRow:
.a16
.i16
    lda.l StreamScrollFp_PendTile
    asl a
    clc
    adc.l StageFp_BG2HistBase
    tax
    lda.l StreamStageFp_Slot
    sta.l StageFp_BG2History,x
    asl a
    tax
    lda.l StageFp_BG2Refs,x
    inc a
    sta.l StageFp_BG2Refs,x
    rts

; Seek helpers use long MMIO and explicit 24-bit carries.
StageFp_BG2SeekColumn:
.a16
.i16
    lda.l StreamScrollFp_PendCol
    pha
    jsr StageFp_BG2Binding
    txa
    asl a
    tax
    lda.l StageFp_PeriodMap,x
    beq StageFp_BG2SeekColumn__invalid
    sta.l StageFp_BG2Tmp
    pla
StageFp_BG2SeekColumn__wrap:
.a16
.i16
    cmp.l StageFp_BG2Tmp
    bcc StageFp_BG2SeekColumn__multiply
    sec
    sbc.l StageFp_BG2Tmp
    bra StageFp_BG2SeekColumn__wrap
StageFp_BG2SeekColumn__multiply:
.a16
.i16
    ldx #84
    jsl StageFp_HostMul
    clc
    adc.l StreamScrollFp_TilemapOffLo
    sta.l StreamStageFp_SeekLo
    txa
    sep #$20
.a8
    adc.l StreamScrollFp_TilemapOffHi
    sta.l StreamStageFp_SeekHi
    jsr StageFp_BG2Seek
    rep #$30
.a16
.i16
    ldx #0
StageFp_BG2SeekColumn__read:
    sep #$20
.a8
    lda.l $002001
    sta.l StreamStageFp_Entries,x
    rep #$30
.a16
.i16
    inx
    cpx #84
    bcc StageFp_BG2SeekColumn__read
    sec
    rts
StageFp_BG2SeekColumn__invalid:
.a16
.i16
    pla
    jmp StageFp_BG2Fail

StageFp_BG2Seek:
    sep #$20
.a8
    lda.l StreamStageFp_SeekLo
    sta.l $002000
    lda.l StreamStageFp_SeekLo+1
    sta.l $002001
    lda.l StreamStageFp_SeekHi
    sta.l $002002
    lda #0
    sta.l $002003
StageFp_BG2Seek__busy:
.a8
    lda.l $002000
    bmi StageFp_BG2Seek__busy
    rts

StageFp_BG2SeekTile:
    rep #$30
.a16
.i16
    lda.l StreamStageFp_TileId
    asl a
    asl a
    asl a
    asl a
    asl a                    ; compiler Tile2Slot domain <=768: <=24544
    clc
    adc.l StreamStageFp_TilesBaseLo
    sta.l StreamStageFp_SeekLo
    sep #$20
.a8
    lda.l StreamStageFp_TilesBaseHi
    adc #0
    sta.l StreamStageFp_SeekHi
    jsr StageFp_BG2Seek
    rts

StageFp_BG2FetchBoot:
    jsr StageFp_BG2SeekTile
    rep #$30
.a16
.i16
    lda.l StreamStageFp_Slot
    jsr StageFp_BG2TileWord
    sta.l $002116
    ldx #16
StageFp_BG2FetchBoot__word:
    sep #$20
.a8
    lda.l $002001
    sta.l $002118
    lda.l $002001
    sta.l $002119
    rep #$30
.a16
.i16
    dex
    bne StageFp_BG2FetchBoot__word
    rts

StageFp_BG2FetchQueued:
    jsr StageFp_BG2SeekTile
    rep #$30
.a16
.i16
    lda.l StreamScrollFp_Budget
    and #$00FF
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    clc
    adc #(StageFp_BG2TileBuf & $FFFF)
    sta.l DmaRequest_SourceAddrLow
    ldy #32
StageFp_BG2FetchQueued__byte:
    sep #$20
.a8
    lda.l $002001
    sta.l StageFp_BG2TileBuf,x
    rep #$30
.a16
.i16
    inx
    dey
    bne StageFp_BG2FetchQueued__byte
    lda.l StreamStageFp_Slot
    jsr StageFp_BG2TileWord
    asl a
    sta.l DmaRequest_TargetAddr
    lda #32
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #StageFp_BG2TileBank
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$30
.a16
.i16
    jsl StageFp_HostEnqueue
    bcc StageFp_BG2FetchQueued__done
    sep #$20
.a8
    lda #1
    sta.l StageFp_BG2DmaPending
    lda.l StreamScrollFp_Budget
    inc a
    sta.l StreamScrollFp_Budget
    rep #$30
.a16
.i16
    sec
StageFp_BG2FetchQueued__done:
.a16
.i16
    rts

StageFp_BG2Resolve:
    rep #$30
.a16
.i16
StageFp_BG2Resolve__row:
.a16
.i16
    lda.l StreamScrollFp_PendTile
    cmp #28
    bcc StageFp_BG2Resolve__have_row
    sec
    rts
StageFp_BG2Resolve__have_row:
.a16
.i16
    sta.l StageFp_BG2Tmp
    asl a
    clc
    adc.l StageFp_BG2Tmp
    tax
    lda.l StreamStageFp_Entries,x
    cmp #STREAM_FP_MAX_TILE_IDS
    bcc StageFp_BG2Resolve__id_ok
    jmp StageFp_BG2Fail
StageFp_BG2Resolve__id_ok:
.a16
.i16
    sta.l StreamStageFp_TileId
    lda.l StreamStageFp_Entries+2,x
    and #$0018              ; only h/v flips; BG2 palette is always zero
    sep #$20
.a8
    sta.l StreamStageFp_Attr
    rep #$30
.a16
.i16
    lda.l StreamStageFp_TileId
    asl a
    tax
    lda.l StreamCacheFp_Tile2Slot,x
    cmp #$FFFF
    beq StageFp_BG2Resolve__miss
    sta.l StreamStageFp_Slot
    jmp StageFp_BG2Resolve__resolved
StageFp_BG2Resolve__miss:
.a16
.i16
    lda.l StageFp_BG2Booting
    and #$00FF
    bne StageFp_BG2Resolve__boot
    lda.l StreamScrollFp_Budget
    and #$00FF
    cmp #2
    bcc StageFp_BG2Resolve__queue
    clc
    rts
StageFp_BG2Resolve__queue:
.a16
.i16
    jsl StageFp_HostHasFree
    bcs StageFp_BG2Resolve__allocate
    clc
    rts
StageFp_BG2Resolve__allocate:
.a16
.i16
    jsr StageFp_BG2Allocate
    bcs StageFp_BG2Resolve__fetch
    jmp StageFp_BG2Fail
StageFp_BG2Resolve__fetch:
.a16
.i16
    jsr StageFp_BG2FetchQueued
    bcs StageFp_BG2Resolve__resolved
    jmp StageFp_BG2Fail
StageFp_BG2Resolve__boot:
.a16
.i16
    jsr StageFp_BG2Allocate
    bcs StageFp_BG2Resolve__boot_fetch
    jmp StageFp_BG2Fail
StageFp_BG2Resolve__boot_fetch:
.a16
.i16
    jsr StageFp_BG2FetchBoot
StageFp_BG2Resolve__resolved:
.a16
.i16
    jsr StageFp_BG2PinRow
    lda.l StreamStageFp_Slot
    jsr StageFp_BG2Physical
    ora #$2000
    sta.l StageFp_BG2Tmp
    lda.l StreamStageFp_Attr
    and #$0018
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a                    ; source bits3/4 -> PPU bits10/11? shift11 below
    asl a
    asl a
    asl a
    asl a                    ; -> PPU hflip14/vflip15
    ora.l StageFp_BG2Tmp
    pha
    lda.l StreamScrollFp_PendTile
    asl a
    tax
    pla
    sta.l StageFp_BG2ColBuf,x
    lda.l StreamScrollFp_PendTile
    inc a
    sta.l StreamScrollFp_PendTile
    jmp StageFp_BG2Resolve__row

StageFp_BG2Fail:
    sep #$20
.a8
    lda #1
    sta.l StageFp_BG2Fault
    rep #$30
.a16
.i16
    clc
    rts

; Boot or NMI accepted forced blank only. Complete 28-row buffer immutable.
StageFp_BG2WriteColumn:
    rep #$30
.a16
.i16
    lda.l StreamScrollFp_PendCol
    jsr StageFp_BG2MapWord
    sta.l StreamScrollFp_ColTargetWord
    ldx #0
StageFp_BG2WriteColumn__row:
.a16
.i16
    lda.l StreamScrollFp_ColTargetWord
    sta.l $002116
    lda.l StageFp_BG2ColBuf,x
    sep #$20
.a8
    sta.l $002118
    xba
    sta.l $002119
    rep #$30
.a16
.i16
    lda.l StreamScrollFp_ColTargetWord
    clc
    adc #32
    sta.l StreamScrollFp_ColTargetWord
    inx
    inx
    cpx #56
    bcc StageFp_BG2WriteColumn__row
    rts

; Public boot dispatch: C=1 handled Normal, C=0 run untouched Easy loader.
StageFp_BG2BootDispatch:
    rep #$30
.a16
.i16
    cld
    jsr StageFp_BG2Binding
    bne StageFp_BG2BootDispatch__normal
    clc
    rtl
StageFp_BG2BootDispatch__normal:
.a16
.i16
    jsr StageFp_BG2BootLoad
    rep #$30
.a16
.i16
    sec
    rtl

StageFp_BG2BootLoad:
    php
    rep #$30
.a16
.i16
    jsl StageFp_HostCacheInit
    jsr StageFp_BG2HistoryInit
    lda #0
    sta.l StageFp_BG2Fault
    sta.l StageFp_BG2DmaPending
    sta.l StageFp_BG2Loaded
    sta.l StreamScrollFp_ColPending
    sep #$20
.a8
    lda #1
    sta.l StageFp_BG2Booting
    lda #$80
    sta.l $002115
    rep #$30
.a16
.i16
    lda #0
    jsr StageFp_BG2TileWord
    sta.l $002116
    ldx #16
    lda #0
StageFp_BG2BootLoad__blank:
.a16
.i16
    sta.l $002118
    dex
    bne StageFp_BG2BootLoad__blank
    lda #StageFp_BG2Map
    sta.l $002116
    lda #0
    jsr StageFp_BG2Physical
    ldx #2048
StageFp_BG2BootLoad__map:
.a16
.i16
    sta.l $002118
    dex
    bne StageFp_BG2BootLoad__map

    lda.l BgRecordStaging+28
    sta.l StreamStageFp_SeekLo
    sep #$20
.a8
    lda.l BgRecordStaging+30
    sta.l StreamStageFp_SeekHi
    jsr StageFp_BG2Seek
    rep #$30
.a16
.i16
    ldx #0
StageFp_BG2BootLoad__header:
    sep #$20
.a8
    lda.l $002001
    sta.l StreamStageFp_Entries,x
    rep #$30
.a16
.i16
    inx
    cpx #16
    bcc StageFp_BG2BootLoad__header
    lda.l StreamStageFp_Entries+2
    cmp #$041C                ; height=28, explicit bpp=4 header marker
    beq StageFp_BG2BootLoad__header_ok
    jsr StageFp_BG2Fail
    jmp StageFp_BG2BootLoad__done
StageFp_BG2BootLoad__header_ok:
.a16
.i16
    lda.l StreamStageFp_Entries+8
    sta.l StreamScrollFp_TilemapOffLo
    lda.l StreamStageFp_Entries+12
    sta.l StreamStageFp_TilesBaseLo
    sep #$20
.a8
    lda.l StreamStageFp_Entries+10
    sta.l StreamScrollFp_TilemapOffHi
    lda.l StreamStageFp_Entries+14
    sta.l StreamStageFp_TilesBaseHi
    ldx #8
StageFp_BG2BootLoad__palette_skip:
.a8
.i16
    lda.l $002001
    dex
    bne StageFp_BG2BootLoad__palette_skip
    lda #4
    sta.l $002121
    ldx #24
StageFp_BG2BootLoad__palette:
.a8
.i16
    lda.l $002001
    sta.l $002122
    dex
    bne StageFp_BG2BootLoad__palette
    rep #$30
.a16
.i16
    jsr StageFp_BG2Binding
    cmp #2
    beq StageFp_BG2BootLoad__vertical
    lda.l StreamScroll_StagedLo
    asl a
    asl a
    asl a
    jsr StageFp_BG2Camera
    bra StageFp_BG2BootLoad__camera
StageFp_BG2BootLoad__vertical:
.a16
.i16
    lda #0
StageFp_BG2BootLoad__camera:
.a16
.i16
    sta.l StageFp_Request
    lsr a
    lsr a
    lsr a
    sta.l StreamScrollFp_StagedLo
    sta.l StreamScrollFp_RepairCur
    sta.l StageFp_BG2BootCol
    clc
    adc #32
    sta.l StreamScrollFp_StagedHi
    sta.l StageFp_BG2BootLast
StageFp_BG2BootLoad__column:
.a16
.i16
    lda.l StageFp_BG2BootCol
    sta.l StreamScrollFp_PendCol
    jsr StageFp_BG2NewHistory
    bcs StageFp_BG2BootLoad__have_history
    jsr StageFp_BG2Fail
    jmp StageFp_BG2BootLoad__done
StageFp_BG2BootLoad__have_history:
.a16
.i16
    jsr StageFp_BG2SeekColumn
    bcs StageFp_BG2BootLoad__seek_ok
    jmp StageFp_BG2BootLoad__done
StageFp_BG2BootLoad__seek_ok:
.a16
.i16
    lda #0
    sta.l StreamScrollFp_PendTile
    jsr StageFp_BG2Resolve
    bcs StageFp_BG2BootLoad__resolved
    jmp StageFp_BG2BootLoad__done
StageFp_BG2BootLoad__resolved:
.a16
.i16
    jsr StageFp_BG2WriteColumn
    lda.l StageFp_BG2BootCol
    inc a
    sta.l StageFp_BG2BootCol
    cmp.l StageFp_BG2BootLast
    bcc StageFp_BG2BootLoad__column
    beq StageFp_BG2BootLoad__column
    sep #$20
.a8
    lda #1
    sta.l StreamScrollFp_Enabled
    sta.l StageFp_BG2Loaded
    sta.l StageFp_Ready
StageFp_BG2BootLoad__done:
    rep #$30
.a16
.i16
    lda #$FFFF
    sta.l StreamScrollFp_PendCol
    sep #$20
.a8
    lda #0
    sta.l StageFp_BG2Booting
    plp
    rep #$30
.a16
.i16
    rts

; Main-thread producer: lease FrameBusy before any queue/buffer mutation.
; Resume only after a successful NMI has drained our previous tile transfers.
StageFp_BG2PlayDispatch:
    rep #$30
.a16
.i16
    cld
    jsr StageFp_BG2Binding
    bne StageFp_BG2PlayDispatch__normal
    clc
    rtl
StageFp_BG2PlayDispatch__normal:
    php
    sep #$20
.a8
    lda.l Nmi_FrameBusy
    pha
    lda #1
    sta.l Nmi_FrameBusy
    lda.l StageFp_BG2Loaded
    bne StageFp_BG2PlayDispatch__loaded
    jmp StageFp_BG2PlayDispatch__done
StageFp_BG2PlayDispatch__loaded:
.a8
    lda.l StageFp_BG2Fault
    ora.l StageFp_BG2DmaPending
    ora.l Msu1_StreamBusy
    ora.l StreamScrollFp_ColPending
    beq StageFp_BG2PlayDispatch__free
    jmp StageFp_BG2PlayDispatch__done
StageFp_BG2PlayDispatch__free:
.a8
    lda #0
    sta.l StreamScrollFp_Budget
    rep #$30
.a16
.i16
    lda.l StreamScrollFp_PendCol
    cmp #$FFFF
    bne StageFp_BG2PlayDispatch__resume
    jsl StageFp_Pick
    bcs StageFp_BG2PlayDispatch__picked
    jmp StageFp_BG2PlayDispatch__done
StageFp_BG2PlayDispatch__picked:
.a16
.i16
    cmp.l StreamScrollFp_StagedLo
    bcc StageFp_BG2PlayDispatch__new
    cmp.l StreamScrollFp_StagedHi
    bcc StageFp_BG2PlayDispatch__done
    beq StageFp_BG2PlayDispatch__done
StageFp_BG2PlayDispatch__new:
.a16
.i16
    sta.l StreamScrollFp_PendCol
    jsr StageFp_BG2Retire
    jsr StageFp_BG2NewHistory
    bcs StageFp_BG2PlayDispatch__history
    jsr StageFp_BG2Fail
    bra StageFp_BG2PlayDispatch__done
StageFp_BG2PlayDispatch__history:
.a16
.i16
    jsr StageFp_BG2SeekColumn
    bcc StageFp_BG2PlayDispatch__done
    lda #0
    sta.l StreamScrollFp_PendTile
StageFp_BG2PlayDispatch__resume:
.a16
.i16
    jsr StageFp_BG2Resolve
    bcc StageFp_BG2PlayDispatch__done
    sep #$20
.a8
    lda #1
    sta.l StreamScrollFp_ColPending
StageFp_BG2PlayDispatch__done:
    sep #$20
.a8
    pla
    sta.l Nmi_FrameBusy
    plp
    rep #$30
.a16
.i16
    sec
    rtl

; Replaces the old FP column-commit call INSIDE the accepted NMI bracket.
; Core_Dma_ProcessQueue already completed. Skipped NMIs never reach here.
StageFp_BG2CommitDispatch:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    cld
    jsr StageFp_BG2Binding
    bne StageFp_BG2CommitDispatch__normal
    jsl StageFp_BG2LegacyCommit
    jmp StageFp_BG2CommitDispatch__presentation
StageFp_BG2CommitDispatch__normal:
    sep #$20
.a8
    lda #0
    sta.l StageFp_BG2DmaPending
    lda.l StreamScrollFp_ColPending
    beq StageFp_BG2CommitDispatch__presentation
    lda #$80
    sta.l $002115
    rep #$30
.a16
.i16
    jsr StageFp_BG2WriteColumn
    lda.l StreamScrollFp_PendCol
    cmp.l StreamScrollFp_StagedLo
    bcs StageFp_BG2CommitDispatch__right
    sta.l StreamScrollFp_StagedLo
    clc
    adc #32
    sta.l StreamScrollFp_StagedHi
    bra StageFp_BG2CommitDispatch__committed
StageFp_BG2CommitDispatch__right:
.a16
.i16
    sta.l StreamScrollFp_StagedHi
    sec
    sbc #32
    sta.l StreamScrollFp_StagedLo
StageFp_BG2CommitDispatch__committed:
.a16
.i16
    lda #$FFFF
    sta.l StreamScrollFp_PendCol
    sep #$20
.a8
    lda #0
    sta.l StreamScrollFp_ColPending
StageFp_BG2CommitDispatch__presentation:
    rep #$30
.a16
.i16
    jsr StageFp_Mode
    bne StageFp_BG2CommitDispatch__mode_on
    jmp StageFp_BG2CommitDispatch__off
StageFp_BG2CommitDispatch__mode_on:
    sep #$20
.a8
    lda.l StageFp_BG2Loaded
    bne StageFp_BG2CommitDispatch__loaded
    jmp StageFp_BG2CommitDispatch__off
StageFp_BG2CommitDispatch__loaded:
.a8
    lda.l StageFp_BG2Fault
    beq StageFp_BG2CommitDispatch__healthy
    jmp StageFp_BG2CommitDispatch__off
StageFp_BG2CommitDispatch__healthy:
.a8
    lda.l StageFp_BG2Active
    bne StageFp_BG2CommitDispatch__owned
    lda.l Nmi_BgTilesVram12
    sta.l StageFp_BG2OldBg12
    lda #1
    sta.l StageFp_BG2Active
StageFp_BG2CommitDispatch__owned:
.a8
    lda #$6D
    sta.l $002108             ; BG2 64x32 map at word $6C00
    lda.l Nmi_BgTilesVram12
    and #$0F
    ora #$30
    sta.l Nmi_BgTilesVram12
    lda.l Nmi_MainScreen
    ora #2
    sta.l Nmi_MainScreen
    rep #$30
.a16
.i16
    lda.l StreamScrollFp_StagedHi
    sec
    sbc #31
    asl a
    asl a
    asl a
    cmp.l StageFp_Request
    bcc StageFp_BG2CommitDispatch__max
    lda.l StageFp_Request
StageFp_BG2CommitDispatch__max:
.a16
.i16
    pha
    lda.l StreamScrollFp_StagedLo
    asl a
    asl a
    asl a
    sta.l Nmi_Bg2ScrollX
    pla
    cmp.l Nmi_Bg2ScrollX
    bcs StageFp_BG2CommitDispatch__position
    lda.l Nmi_Bg2ScrollX
StageFp_BG2CommitDispatch__position:
.a16
.i16
    sta.l Nmi_Bg2ScrollX
    lda #0
    sta.l Nmi_Bg2ScrollY
    jmp StageFp_BG2CommitDispatch__done
StageFp_BG2CommitDispatch__off:
    sep #$20
.a8
    lda.l StageFp_BG2Active
    beq StageFp_BG2CommitDispatch__done
    lda.l Nmi_MainScreen
    and #$FD
    sta.l Nmi_MainScreen
    lda.l StageFp_BG2OldBg12
    and #$F0
    sta.l StageFp_BG2OldBg12
    lda.l Nmi_BgTilesVram12
    and #$0F
    ora.l StageFp_BG2OldBg12
    sta.l Nmi_BgTilesVram12
    lda #0
    sta.l StageFp_BG2Active
StageFp_BG2CommitDispatch__done:
    rep #$30
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; A8 sprite attributes -> Normal OBJ priority2, otherwise byte-identical.
; P/X/Y/D/DBR preserved. BG2 high(8)>OBJ2(7); BG3 high HUD(11)>both.
StageFp_BG2OamAttr:
    php
    rep #$10
.i16
    phx
    sep #$20
.a8
    pha
    rep #$20
.a16
    jsr StageFp_BG2Binding
    beq StageFp_BG2OamAttr__easy
    sep #$20
.a8
    pla
    and #$EF
    bra StageFp_BG2OamAttr__done
StageFp_BG2OamAttr__easy:
    sep #$20
.a8
    pla
StageFp_BG2OamAttr__done:
.a8
.i16
    plx
    plp
    rtl
