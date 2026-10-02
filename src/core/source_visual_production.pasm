; Production SOURCE_SIZED visual consumer.
;
; This module is deliberately presentation-only.  It reads the compiler-owned
; SVIS1 catalog from the MSU data stream, while the actor's accepted gameplay
; context remains the authoritative source of role/frame/map/position.
; Source-policy actors are fail-closed: no legacy 32x48 fallback is allowed.

; The source publisher must not overlap the legacy animation/MSU staging
; records at $7E2000-$7E23FF.  The verified gap after HUD staging is
; $7E5B00-$7E5FFF; the publisher uses its first 1 KiB as the transient
; source-sheet DMA staging buffer.  The remaining lookup/state scratch below
; remains in the existing compiler-owned source-publisher arena.
SourceVisual_TileStaging    = $7E5B00 ; 1 KiB, disjoint from legacy staging
SourceVisual_PieceTable     = $7E4000 ; up to 65 * 16-byte piece rows
; The 65-row table ends at $4410.  Keep loader scratch in the checked free
; publisher arena rather than truncating Normal's 65-piece K9999 upper frame.
SourceVisual_EntryScratch   = $7E4800 ; 24-byte SVIS entry
SourceVisual_RowScratch     = $7E4840 ; 64-byte table-row scratch
SourceVisual_PaletteTemp    = $7E4880 ; 32-byte palette read scratch
SourceVisual_PaletteStaging = $7E4900 ; 8 * 32-byte OBJ palettes
SourceVisual_Offset         = $7E4A00 ; 32-bit MSU seek scratch
SourceVisual_Key            = $7E4A04 ; roster, role, frame, map
SourceVisual_Error          = $7E4A08 ; diagnostic byte
SourceVisual_State           = $7E4A20 ; 4 * 8-byte unique-sheet residency records
SourceVisual_DebugSeek      = $7E4A50 ; last 32-bit native seek, diagnostic
SourceVisual_DebugIndex     = $7E4A54 ; matched catalog entry index
SourceVisual_DebugD         = $7E4A56
SourceVisual_DebugLastError = $7E4A58
; Mutable lookup/queue state lives in WRAM.  These must not be emitted as
; .dw ROM labels because the native publisher writes them through long
; addressing on every actor render.
SourceVisual_Temp            = $7E4A60
SourceVisual_BaseTile        = $7E4A62
SourceVisual_PieceCount      = $7E4A64
SourceVisual_SheetBytes      = $7E4A66
SourceVisual_ChunkCount      = $7E4A68
SourceVisual_TotalBytes      = $7E4A6A
SourceVisual_PaletteMask     = $7E4A6C
SourceVisual_PieceIndex      = $7E4A6E
SourceVisual_PaletteSlot     = $7E4A70
SourceVisual_Record          = $7E4A72 ; current actor's 8-byte state offset
SourceVisual_PaletteBase     = $7E4A74 ; physical OBJ palette base for actor slot
SourceVisual_PresentationMask = $7E4A76 ; OBJ sheet slots already used this pass
SourceVisual_PresentationField = $7E4A78 ; NMI field owning the presentation mask
SourceVisual_ActorSlot       = $7E4A7A ; actor-context slot 0..5, diagnostic only
SourceVisual_DebugTrace      = $7E4500 ; 6 * (key[4], entry index[2], error[2])
SourceVisual_FindTrace       = $7E4540 ; 8 * (key[4], D[2], result[2])
SourceVisual_FindTraceIndex  = $7E4580
SourceVisual_FindTraceOffset = $7E4582
SourceVisual_CallCount       = $7E4584
SourceVisual_HostCallCount   = $7E4594
SourceVisual_RenderPassCount = $7E4596
SourceVisual_AfterPassCount  = $7E459C
SourceVisual_RenderLoopCount = $7E459E
SourceVisual_RenderLastId    = $7E45A0
SourceVisual_HostLastD       = $7E4598
SourceVisual_HostLastRoster  = $7E459A
SourceVisual_HostLastPolicy  = $7E459B
SourceVisual_KeySaved        = $7E4588
SourceVisual_EntryIndexSaved = $7E458C
SourceVisual_DebugSheetSeek  = $7E4590
SourceVisual_DebugSheetRow   = $7E45A0
SourceVisual_DebugStateCompare = $7E45D0
SourceVisual_DmaToken          = $7E45D4
SourceVisual_ChunkBytes        = $7E45D6
; Narrow live-path admission witness. Stage values: 1=before budget check,
; 2=before enqueue, 3=enqueue accepted, 4=enqueue rejected.
SourceVisual_DebugQueueStage   = $7E45D8
SourceVisual_DebugQueueBudget  = $7E45DA
SourceVisual_DebugQueueCursor  = $7E45DC
SourceVisual_DebugQueueChunk   = $7E45DE
SourceVisual_DmaOwner          = $7E4600 ; 8 queue-slot owner tokens
SourceVisual_DebugEmitPiece    = $7E4610 ; temporary native emission witness
SourceVisual_DebugEmitOam      = $7E4660 ; temporary native OAM witness
SourceVisual_EmitBaseX         = $7E44A0
SourceVisual_EmitBaseY         = $7E44A2
; Parallel per-entity visual policy, one byte at each 133-byte StageEnv row.
; The actor DP offset 67 is already CHAR_THROW_ZPOS and cannot be reused.
SourceVisual_EntityPolicy    = $7E550F+103

SOURCE_VISUAL_MAX_PIECES = 65
; Gameplay OBJ owns both OBSEL character pages.  The byte-addressed DMA
; window is $8000-$BFFF (VRAM words $4000-$5FFF), not the old first-page
; staging window.  Keep the admission bound here in lockstep with the
; compiler/linker manifests so a source-sized packet cannot be admitted to
; an address range occupied by BG2/frontpanel data.
SOURCE_VISUAL_MAX_SHEET  = 16384
SOURCE_VISUAL_VRAM_BASE  = $8000 ; Core_Dma targets byte addresses
SOURCE_VISUAL_VRAM_END   = $C000 ; exclusive byte address
SOURCE_VISUAL_TILE_STRIDE = 128 ; retained per-record stride metadata
SOURCE_VISUAL_CHUNK_BYTES = 1024
SOURCE_VISUAL_MSU_OFFSET_LO = SOURCE_VISUAL_MSU_OFFSET & $FFFF
SOURCE_VISUAL_MSU_OFFSET_MID = (SOURCE_VISUAL_MSU_OFFSET >> 16) & $FF
SOURCE_VISUAL_MSU_OFFSET_HI = (SOURCE_VISUAL_MSU_OFFSET >> 24) & $FF

; Entry: D = the real production entity context.  A16/I16.
; Carry set means this actor emitted source-sized OAM.  Carry clear means the
; caller must hide the source-policy actor and report SourceVisual_Error.
SourceVisual_RenderCurrent:
    php
    phb
    phd
    phx
    phy
    sei
    rep #$31
.a16
.i16
    lda.l SourceVisual_CallCount
    inc a
    sta.l SourceVisual_CallCount
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    lda.l Nmi_FrameCounter
    cmp.l SourceVisual_PresentationField
    beq SourceVisual_RenderCurrent__same_field
    sta.l SourceVisual_PresentationField
    lda #0
    sta.l SourceVisual_PresentationMask
SourceVisual_RenderCurrent__same_field:
    jsr SourceVisual_FindEntry
    bcc SourceVisual_RenderCurrent__fail
    jsr SourceVisual_SelectResidency
    bcc SourceVisual_RenderCurrent__fail
    jsr SourceVisual_LoadResources
    bcc SourceVisual_RenderCurrent__fail
    jsr SourceVisual_Emit
    bcc SourceVisual_RenderCurrent__fail
    sec
    ply
    plx
    pld
    plb
    plp
    rtl
SourceVisual_RenderCurrent__fail:
    lda #34
    sta.l SourceVisual_DebugQueueStage
    sep #$20
.a8
    lda.l SourceVisual_Error
    sta.l SourceVisual_DebugLastError
    ; Keep the per-slot failure visible after later actors run.  This is
    ; diagnostic only; publication still fails closed.
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda.l SourceVisual_Error
    sta.l SourceVisual_DebugTrace+6,x
    rep #$31
.a16
.i16
    clc
    ply
    plx
    pld
    plb
    plp
    rtl

; Build the presentation key from accepted-compat state and find its compiler
; generated entry.  No model-name branch exists here.
SourceVisual_FindEntry:
    sep #$20
.a8
    lda CHAR_ROSTER_INDEX
    sta.l SourceVisual_Key+0
    lda CHAR_SELECTED
    beq SourceVisual_FindEntry__idle
    cmp #1
    beq SourceVisual_FindEntry__walk
    cmp #2
    beq SourceVisual_FindEntry__attack
    cmp #3
    beq SourceVisual_FindEntry__fall
    cmp #4
    beq SourceVisual_FindEntry__rise
    cmp #5
    beq SourceVisual_FindEntry__special
    brl SourceVisual_FindEntry__unsupported
SourceVisual_FindEntry__idle:
    lda #0
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__walk:
    lda #1
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__attack:
    lda CHAR_ATTACK_VARIANT
    beq SourceVisual_FindEntry__attack1
    lda #3
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__attack1:
    lda #2
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__fall:
    lda #4
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__rise:
    lda #5
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__special:
    lda #6
SourceVisual_FindEntry__role:
    sta.l SourceVisual_Key+1
    lda CHAR_FRAME_INDEX
    cmp #$FF
    bne SourceVisual_FindEntry__frame_ready
    lda #0
SourceVisual_FindEntry__frame_ready:
    sta.l SourceVisual_Key+2
    lda CHAR_MAP_INDEX
    sta.l SourceVisual_Key+3

    ; The accepted renderer asks for the same visual key on every pass while
    ; a frame remains current.  Reusing the compiler entry already loaded for
    ; that key avoids rescanning the 3,640-row native key table on every
    ; compositor invocation.  EntryScratch is immutable catalog data and is
    ; only replaced on a cold-key lookup, so this is safe for same-key
    ; instances and does not create a second simulation state.
    rep #$31
.a16
.i16
    lda.l SourceVisual_Key
    cmp.l SourceVisual_KeySaved
    bne SourceVisual_FindEntry__cold
    lda.l SourceVisual_Key+2
    cmp.l SourceVisual_KeySaved+2
    bne SourceVisual_FindEntry__cold
    lda.l SourceVisual_EntryIndexSaved
    cmp #SOURCE_VISUAL_CATALOG_COUNT
    bcs SourceVisual_FindEntry__cold
    sec
    rts
SourceVisual_FindEntry__cold:

    ; Narrow diagnostic ring: records the actual accepted-context key and DP
    ; owner before lookup, so a failed production actor cannot be confused
    ; with a later entity's successful lookup.
    rep #$31
.a16
.i16
    lda.l SourceVisual_FindTraceIndex
    and #$0007
    asl a
    asl a
    asl a
    tax
    txa
    sta.l SourceVisual_FindTraceOffset
    phx
    lda.l SourceVisual_Key
    sta.l SourceVisual_FindTrace,x
    lda.l SourceVisual_Key+2
    sta.l SourceVisual_FindTrace+2,x
    tdc
    sta.l SourceVisual_FindTrace+4,x
    lda.l SourceVisual_FindTraceIndex
    inc a
    sta.l SourceVisual_FindTraceIndex
    lda.l SourceVisual_Key
    sta.l SourceVisual_KeySaved
    lda.l SourceVisual_Key+2
    sta.l SourceVisual_KeySaved+2

    rep #$31
.a16
.i16
    lda.l SourceVisual_Key+0
    and #$00FF
    asl a
    tax
    lda.l SourceVisual_RosterKeyStart,x
    sta.l SourceVisual_Temp
    lda.l SourceVisual_RosterKeyEnd,x
    sta.l SourceVisual_DebugD
    lda.l SourceVisual_Temp
    tax
SourceVisual_FindEntry__scan:
    txa
    cmp.l SourceVisual_DebugD
    bcc SourceVisual_FindEntry__within_roster
    brl SourceVisual_FindEntry__unsupported
.a16
.i16
SourceVisual_FindEntry__within_roster:
    .a16
    .i16
    lda.l SOURCE_VISUAL_KEY_BASE+0,x
    cmp.l SourceVisual_Key+0
    beq SourceVisual_FindEntry__roster_match
    brl SourceVisual_FindEntry__next
.a16
.i16
SourceVisual_FindEntry__roster_match:
    lda.l SOURCE_VISUAL_KEY_BASE+2,x
    cmp.l SourceVisual_Key+2
    beq SourceVisual_FindEntry__key_match
    brl SourceVisual_FindEntry__next
.a16
.i16
SourceVisual_FindEntry__key_match:
    ; Key rows carry an entry index.  The complete production table is
    ; larger than 64 KiB, so storing a byte offset in the 16-bit key row
    ; would wrap before the native lookup reaches the later roster entries.
    lda.l SOURCE_VISUAL_KEY_BASE+4,x
    sta.l SourceVisual_Temp
    sta.l SourceVisual_DebugIndex
    sta.l SourceVisual_EntryIndexSaved
    plx
    sta.l SourceVisual_FindTrace+6,x
    asl a
    clc
    adc.l SourceVisual_Temp
    asl a
    asl a
    asl a
    clc
    adc #18
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda #0
    adc #0
    sta.l SourceVisual_Offset+2
    lda #0
    adc #0
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    jsr SourceVisual_AddCatalogBase
    jsr SourceVisual_ReadEntry
    sec
    rts

; Select one of four physical 4-KiB sheet pages for the current catalog
; entry. Six actor contexts may share those pages when their exact source
; frame key is identical. The per-field mask prevents a later actor from
; evicting a page already referenced by OAM being prepared for this field.
SourceVisual_SelectResidency:
    rep #$31
.a16
.i16
    tdc
    sta.l SourceVisual_DebugD
    sec
    sbc #$0A00
    ldy #0
SourceVisual_SelectResidency__actor_scan:
    cmp #0
    beq SourceVisual_SelectResidency__actor_found
    sec
    sbc #CHAR_ZP_LEN
    iny
    cpy #6
    bcc SourceVisual_SelectResidency__actor_scan
    brl SourceVisual_SelectResidency__bad
SourceVisual_SelectResidency__actor_found:
    tya
    sta.l SourceVisual_ActorSlot
    ldx #0
SourceVisual_SelectResidency__lookup:
    lda.l SourceVisual_State+6,x
    beq SourceVisual_SelectResidency__next
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceVisual_SelectResidency__found
SourceVisual_SelectResidency__next:
    txa
    clc
    adc #8
    tax
    cpx #32
    bcc SourceVisual_SelectResidency__lookup
    bra SourceVisual_SelectResidency__allocate
SourceVisual_SelectResidency__found:
    txa
    lsr a
    lsr a
    lsr a
    tay
    bra SourceVisual_SelectResidency__claim
SourceVisual_SelectResidency__allocate:
    ; A staging DMA owns the shared 1-KiB source window until NMI retires it.
    ; Do not replace any residency record while that immutable source is live.
    jsr SourceVisual_HasOwnedDma
    bcc SourceVisual_SelectResidency__find_free
    brl SourceVisual_SelectResidency__busy
SourceVisual_SelectResidency__find_free:
    lda #0
    sta.l SourceVisual_Temp
SourceVisual_SelectResidency__free_scan:
    lda.l SourceVisual_Temp
    tax
    lda #1
    cpx #0
    beq SourceVisual_SelectResidency__free_mask_ready
SourceVisual_SelectResidency__free_mask_shift:
    asl a
    dex
    bne SourceVisual_SelectResidency__free_mask_shift
SourceVisual_SelectResidency__free_mask_ready:
    and.l SourceVisual_PresentationMask
    beq SourceVisual_SelectResidency__free_found
    lda.l SourceVisual_Temp
    inc a
    sta.l SourceVisual_Temp
    cmp #4
    bcc SourceVisual_SelectResidency__free_scan
    brl SourceVisual_SelectResidency__bad
SourceVisual_SelectResidency__free_found:
    ; Rebuild 1<<slot and mark the page for this field.
    lda.l SourceVisual_Temp
    tax
    lda #1
    beq SourceVisual_SelectResidency__free_claim_mask_ready
SourceVisual_SelectResidency__free_claim_mask_shift:
    asl a
    dex
    bne SourceVisual_SelectResidency__free_claim_mask_shift
SourceVisual_SelectResidency__free_claim_mask_ready:
    ora.l SourceVisual_PresentationMask
    sta.l SourceVisual_PresentationMask
    lda.l SourceVisual_Temp
    sta.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_State,x
    lda #0
    sta.l SourceVisual_State+2,x
    sta.l SourceVisual_State+4,x
    lda #1
    sta.l SourceVisual_State+6,x
    lda.l SourceVisual_Temp
    tay
    bra SourceVisual_SelectResidency__page_ready
SourceVisual_SelectResidency__claim:
    ; The lookup's physical slot is X/8. Preserve it while forming 1<<slot.
    tya
    sta.l SourceVisual_PieceIndex
    lda #1
    cpy #0
    beq SourceVisual_SelectResidency__claim_mask_ready
SourceVisual_SelectResidency__claim_mask_shift:
    asl a
    dey
    bne SourceVisual_SelectResidency__claim_mask_shift
SourceVisual_SelectResidency__claim_mask_ready:
    ora.l SourceVisual_PresentationMask
    sta.l SourceVisual_PresentationMask
    lda.l SourceVisual_PieceIndex
    tay
SourceVisual_SelectResidency__page_ready:
    tya
    asl a
    asl a
    asl a
    sta.l SourceVisual_Record
    tya
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_BaseTile
    ; Two OBJ palette selectors per resident sheet. This keeps four unique
    ; source sheets within the eight hardware OBJ palettes.
    tya
    asl a
    sta.l SourceVisual_PaletteBase
    sec
    rts
SourceVisual_SelectResidency__busy:
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_SelectResidency__bad:
    sep #$20
.a8
    lda #$24
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_FindEntry__next:
    rep #$31
.a16
.i16
    txa
    clc
    adc #6
    tax
    brl SourceVisual_FindEntry__scan
SourceVisual_FindEntry__unsupported:
    plx
    sep #$20
.a8
    lda #$21
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts

SourceVisual_Seek:
    lda.l SourceVisual_Offset+0
    sta.l SourceVisual_DebugSeek+0
    lda.l SourceVisual_Offset+1
    sta.l SourceVisual_DebugSeek+1
    lda.l SourceVisual_Offset+2
    sta.l SourceVisual_DebugSeek+2
    lda.l SourceVisual_Offset+3
    sta.l SourceVisual_DebugSeek+3
    sep #$20
.a8
    lda.l SourceVisual_Offset+0
    sta $2000
    lda.l SourceVisual_Offset+1
    sta $2001
    lda.l SourceVisual_Offset+2
    sta $2002
    lda.l SourceVisual_Offset+3
    sta $2003
SourceVisual_Seek__busy:
    lda $2000
    bmi SourceVisual_Seek__busy
    rts

; Add the compiler-owned catalog's full MSU-1 offset to the internal table
; offset.  The project MSU extension exposes seek bits 24..31 at $2003;
; keeping this carry-aware prevents catalogs beyond the 16 MiB boundary from
; wrapping back into unrelated MSU data.
SourceVisual_AddCatalogBase:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Offset
    clc
    adc #SOURCE_VISUAL_MSU_OFFSET_LO
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda.l SourceVisual_Offset+2
    adc #SOURCE_VISUAL_MSU_OFFSET_MID
    sta.l SourceVisual_Offset+2
    lda.l SourceVisual_Offset+3
    adc #SOURCE_VISUAL_MSU_OFFSET_HI
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    rts

SourceVisual_ReadEntry:
    jsr SourceVisual_Seek
    rep #$31
.a16
.i16
    ldx #0
SourceVisual_ReadEntry__loop:
    sep #$20
.a8
    lda $2001
    sta.l SourceVisual_EntryScratch,x
    rep #$31
.a16
.i16
    inx
    cpx #24
    bcc SourceVisual_ReadEntry__loop
    rts

SourceVisual_ReadRow:
    jsr SourceVisual_Seek
    rep #$31
.a16
.i16
    ldx #0
SourceVisual_ReadRow__loop:
    sep #$20
.a8
    lda $2001
    sta.l SourceVisual_RowScratch,x
    rep #$31
.a16
.i16
    inx
    cpx #42
    bcc SourceVisual_ReadRow__loop
    rts

; Read the selected sheet and piece rows.  The sheet is composed by the
; compiler in SNES OBJ row-stride order, so the runtime performs one or more
; contiguous VRAM transfers instead of a per-piece tile-layout guess.
SourceVisual_LoadResources:
    sep #$20
.a8
    lda #$A0
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    lda.l SourceVisual_EntryScratch+12
    and #$00FF
    bne SourceVisual_LoadResources__piece_count_ok
    brl SourceVisual_LoadResources__bad
SourceVisual_LoadResources__piece_count_ok:
    cmp #SOURCE_VISUAL_MAX_PIECES+1
    bcc SourceVisual_LoadResources__piece_count_ok2
    brl SourceVisual_LoadResources__bad
SourceVisual_LoadResources__piece_count_ok2:
    sta.l SourceVisual_PieceCount

    lda.l SourceVisual_Record
    tax
    ; Record and entry ownership were selected atomically by
    ; SourceVisual_SelectResidency before this loader was entered.
    lda.l SourceVisual_EntryIndexSaved
    cmp.l SourceVisual_State,x
    beq SourceVisual_LoadResources__record_match
    brl SourceVisual_LoadResources__bad
.a16
.i16
SourceVisual_LoadResources__record_match:
    lda.l SourceVisual_Key
    sta.l SourceVisual_DebugTrace,x
    lda.l SourceVisual_Key+2
    sta.l SourceVisual_DebugTrace+2,x
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_DebugTrace+4,x

    ; Read the selected sheet-table row.
    lda.l SourceVisual_EntryScratch+20
    sta.l SourceVisual_DebugD
    ; SVIS table rows are 42 bytes: 32 + 8 + 2.
    lda.l SourceVisual_DebugD
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Temp       ; 32 * index
    lda.l SourceVisual_DebugD
    asl a
    asl a
    asl a                         ; 8 * index
    clc
    adc.l SourceVisual_Temp
    clc
    adc.l SourceVisual_DebugD
    clc
    adc.l SourceVisual_DebugD     ; 42 * index
    clc
    adc #SOURCE_VISUAL_SHEET_OFFSET
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda #((SOURCE_VISUAL_SHEET_OFFSET >> 16) & $FF)
    adc #0
    sta.l SourceVisual_Offset+2
    lda #((SOURCE_VISUAL_SHEET_OFFSET >> 24) & $FF)
    adc #0
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    jsr SourceVisual_AddCatalogBase
    lda.l SourceVisual_Offset
    sta.l SourceVisual_DebugSheetSeek
    lda.l SourceVisual_Offset+2
    sta.l SourceVisual_DebugSheetSeek+2
    jsr SourceVisual_ReadRow
    sep #$20
.a8
    lda #$A1
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    ldx #0
SourceVisual_DebugCopySheetRow:
    sep #$20
.a8
    lda.l SourceVisual_RowScratch,x
    sta.l SourceVisual_DebugSheetRow,x
    rep #$31
.a16
.i16
    inx
    cpx #42
    bcc SourceVisual_DebugCopySheetRow
    rep #$31
.a16
.i16
    lda.l SourceVisual_RowScratch+32
    cmp #SOURCE_VISUAL_MAX_SHEET+1
    bcc SourceVisual_LoadResources__sheet_ok
    brl SourceVisual_LoadResources__large
SourceVisual_LoadResources__sheet_ok:
    sta.l SourceVisual_SheetBytes
    clc
    adc #1023
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
    sta.l SourceVisual_ChunkCount
    jsr SourceVisual_RefreshFence
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+6,x
    cmp #2
    bne SourceVisual_LoadResources__not_ready
    brl SourceVisual_LoadResources__ready
SourceVisual_LoadResources__not_ready:
    ; Tile staging is a single shared 1-KiB DMA source. Serialize producers
    ; across actors until NMI retires the current source-owned transfer.
    jsr SourceVisual_HasOwnedDma
    bcc SourceVisual_LoadResources__staging_free
    brl SourceVisual_LoadResources__pending
SourceVisual_LoadResources__staging_free:
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+2,x
    cmp.l SourceVisual_ChunkCount
    bcc SourceVisual_LoadResources__need_transfer
    lda #2
    sta.l SourceVisual_State+6,x
    brl SourceVisual_LoadResources__ready
SourceVisual_LoadResources__need_transfer:
    ; Read only the next 1-KiB chunk. Re-reading the complete sheet here
    ; made the second admission take an entire serial MSU pass and prevented
    ; the per-actor fence from advancing.
    lda.l SourceVisual_State+2,x
    sta.l SourceVisual_Temp
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_TotalBytes
    lda.l SourceVisual_SheetBytes
    sec
    sbc.l SourceVisual_TotalBytes
    cmp #SOURCE_VISUAL_CHUNK_BYTES
    bcc SourceVisual_LoadResources__read_short
    lda #SOURCE_VISUAL_CHUNK_BYTES
SourceVisual_LoadResources__read_short:
    sta.l SourceVisual_ChunkBytes
    lda.l SourceVisual_RowScratch+34
    clc
    adc.l SourceVisual_TotalBytes
    sta.l SourceVisual_Offset
    lda.l SourceVisual_RowScratch+36
    adc #0
    sta.l SourceVisual_Offset+2
    jsr SourceVisual_AddCatalogBase
    lda #9
    sta.l SourceVisual_DebugQueueStage
    jsr SourceVisual_ReadSheet

    ; Piece rows are needed for source offsets, hflip and per-piece palette.
    rep #$31
.a16
.i16
    ; The first-piece index is a u16 and the piece table is larger than
    ; 64 KiB.  Form first*16 as a real 32-bit value before adding the
    ; catalog-relative base; a 16-bit shift silently selected the wrong row
    ; for later production entries.
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
    lda #8
    sta.l SourceVisual_DebugQueueStage
    sep #$20
.a8
    lda #$A2
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+4,x
    bne SourceVisual_LoadResources__palette_done
    lda #5
    sta.l SourceVisual_DebugQueueStage
    ; Palette admission comes first. The ordinary compositor commonly owns
    ; six DMA slots already; admitting the sheet chunk first can consume the
    ; last slot and make the required CGRAM request fail even though both
    ; transfers fit the byte budget. Palette and tile readiness are one
    ; publication contract, so reserve the small palette request before the
    ; larger sheet request.
    jsr SourceVisual_QueuePalettes
    bcs SourceVisual_LoadResources__palette_ok
    brl SourceVisual_LoadResources__bad
SourceVisual_LoadResources__palette_ok:
    lda.l SourceVisual_Record
    tax
    lda #1
    sta.l SourceVisual_State+4,x
    lda #6
    sta.l SourceVisual_DebugQueueStage
SourceVisual_LoadResources__palette_done:
    jsr SourceVisual_QueueSheet
    bcc SourceVisual_LoadResources__bad
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+2,x
    cmp.l SourceVisual_ChunkCount
    bcc SourceVisual_LoadResources__pending
    ; The final chunk was only queued on this invocation.  It is not ready
    ; until the next compositor pass observes the completed DMA fence.
SourceVisual_LoadResources__pending:
    lda #33
    sta.l SourceVisual_DebugQueueStage
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_LoadResources__ready:
    ; Piece rows are still read for the current accepted frame so publication
    ; can change geometry without changing the tile residency lease.
    rep #$31
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
    sec
    rts
SourceVisual_LoadResources__large:
    sep #$20
.a8
    lda #$22
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_LoadResources__bad:
    sep #$20
.a8
    lda #$23
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts

SourceVisual_ReadSheet:
    jsr SourceVisual_Seek
    rep #$31
.a16
.i16
    ldx #0
SourceVisual_ReadSheet__loop:
    txa
    sta.l SourceVisual_DebugD
    cmp.l SourceVisual_ChunkBytes
    bcs SourceVisual_ReadSheet__done
    sep #$20
.a8
    lda $2001
    sta.l SourceVisual_TileStaging,x
    rep #$31
.a16
.i16
    inx
    bra SourceVisual_ReadSheet__loop
SourceVisual_ReadSheet__done:
    rts

SourceVisual_ReadPieces:
    jsr SourceVisual_Seek
    rep #$31
.a16
.i16
    ldx #0
SourceVisual_ReadPieces__loop:
    txa
    cmp.l SourceVisual_PieceCount
    bcs SourceVisual_ReadPieces__done
    ; 16 bytes per row; X is a piece index.
    phx
    txa
    asl a
    asl a
    asl a
    asl a
    tax
    ldy #0
SourceVisual_ReadPieces__row:
    sep #$20
.a8
    lda $2001
    sta.l SourceVisual_PieceTable,x
    rep #$31
.a16
.i16
    inx
    iny
    cpy #16
    bcc SourceVisual_ReadPieces__row
    plx
    inx
    bra SourceVisual_ReadPieces__loop
SourceVisual_ReadPieces__done:
    rts

; Admit one fixed-size sheet chunk per compositor pass.  Completion is fenced
; by the next pass; source OAM is never emitted while a chunk is still in
; flight.
SourceVisual_QueueSheet:
    sep #$20
.a8
    lda #$A3
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+2,x
    cmp.l SourceVisual_ChunkCount
    bcc SourceVisual_QueueSheet__has_chunk
    brl SourceVisual_QueueSheet__done
SourceVisual_QueueSheet__has_chunk:
    sep #$20
.a8
    lda #$A4
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+2,x
    sta.l SourceVisual_Temp
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_TotalBytes
    lda.l SourceVisual_SheetBytes
    sec
    sbc.l SourceVisual_TotalBytes
    cmp #SOURCE_VISUAL_CHUNK_BYTES
    bcc SourceVisual_QueueSheet__short
    lda #SOURCE_VISUAL_CHUNK_BYTES
SourceVisual_QueueSheet__short:
    sta.l SourceVisual_ChunkBytes
    lda #1
    sta.l SourceVisual_DebugQueueStage
    lda.l DmaQueue_BudgetTotal
    sta.l SourceVisual_DebugQueueBudget
    lda DmaQueue_CurrentSlot
    sta.l SourceVisual_DebugQueueCursor
    lda.l SourceVisual_ChunkBytes
    sta.l SourceVisual_DebugQueueChunk
    lda.l DmaQueue_BudgetTotal
    clc
    adc.l SourceVisual_ChunkBytes
    cmp #DMA_TRANSFER_MAX_BYTES
    bcc SourceVisual_QueueSheet__budget_ok
    brl SourceVisual_QueueSheet__fail
SourceVisual_QueueSheet__budget_ok:
    lda #2
    sta.l SourceVisual_DebugQueueStage
    ; SourceVisual_ReadSheet reuses the single 1-KiB staging buffer for each
    ; chunk. The chunk cursor belongs in the VRAM destination only; adding it
    ; to this source pointer read unrelated WRAM after chunk zero.
    lda #SourceVisual_TileStaging
    sta.l DmaRequest_SourceAddrLow
    ; BaseTile is an OBJ tile number.  DMA requests use a byte address
    ; (Core_Dma_TransferVram halves it for VMADDL/H), so convert tile number
    ; to bytes with *32, not *16.  The old shift overlapped the two legal
    ; 4-KiB actor sheets by 2 KiB whenever slot 1 was active.
    lda.l SourceVisual_BaseTile
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceVisual_TotalBytes
    adc #SOURCE_VISUAL_VRAM_BASE
    sta.l DmaRequest_TargetAddr
    lda.l SourceVisual_ChunkBytes
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #$7E
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    ; Enqueue performs the authoritative slot scan.  Avoid a separate
    ; probe here: the source publisher is already serialized by the render
    ; fence, and the duplicate probe can leave the caller parked in the
    ; legacy queue scan while NMI ownership changes.
    jsl Core_Dma_Enqueue_Long
    bcs SourceVisual_QueueSheet__enqueued
    bra SourceVisual_QueueSheet__fail
SourceVisual_QueueSheet__enqueued:
    lda #3
    sta.l SourceVisual_DebugQueueStage
    lda #31
    sta.l SourceVisual_DebugQueueStage
    jsr SourceVisual_TrackRequest
    lda #32
    sta.l SourceVisual_DebugQueueStage
    sep #$20
.a8
    lda #$A5
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+2,x
    inc a
    sta.l SourceVisual_State+2,x
    sta.l SourceVisual_DebugIndex
    lda.l SourceVisual_FindTraceIndex
    inc a
    sta.l SourceVisual_FindTraceIndex
    sep #$20
.a8
    lda #$A6
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
SourceVisual_QueueSheet__done:
    sec
    rts
SourceVisual_QueueSheet__fail:
    lda #4
    sta.l SourceVisual_DebugQueueStage
    sep #$20
.a8
    lda #$24
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts

; Palette transfer is intentionally isolated behind this fence.  The first
; native production packet admits one palette identity per emitted slot; the
; compiler still records all exact palette identities and the runtime rejects
; a frame needing more than eight physical OBJ slots.
SourceVisual_QueuePalettes:
    sep #$20
.a8
    lda #14
    sta.l SourceVisual_DebugQueueStage
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda #$A7
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_PaletteMask
    sta.l SourceVisual_PieceIndex
    ; Fast path for the overwhelmingly common single-palette frame.  The
    ; compiler guarantees its local palette selector is zero; read the
    ; palette identity directly from the first piece and enter the same
    ; content-addressed lookup used by the general mask path.  This avoids
    ; relying on a transient X/Y width while still preserving the exact
    ; palette identity and later per-piece selector publication.
    sep #$20
.a8
    lda.l SourceVisual_EntryScratch+14
    cmp #1
    rep #$31
.a16
.i16
    beq SourceVisual_QueuePalettes__single
    brl SourceVisual_QueuePalettes__piece
SourceVisual_QueuePalettes__single:
    ldx #0
    sep #$20
.a8
    lda.l SourceVisual_PieceTable+10,x
    sta.l SourceVisual_Temp
    lda.l SourceVisual_PieceTable+11,x
    sta.l SourceVisual_Temp+1
    rep #$31
.a16
.i16
    lda #1
    sta.l SourceVisual_PaletteMask
    sta.l SourceVisual_Temp+2
    brl SourceVisual_QueuePalettes__palette_lookup
SourceVisual_QueuePalettes__piece:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceVisual_QueuePalettes__have_piece
    brl SourceVisual_QueuePalettes__done
SourceVisual_QueuePalettes__have_piece:
    lda #16
    sta.l SourceVisual_DebugQueueStage
    sta.l SourceVisual_DebugIndex
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tay
    lda #17
    sta.l SourceVisual_DebugQueueStage
    sep #$20
.a8
    tyx
    lda.l SourceVisual_PieceTable+8,x
    clc
    adc.l SourceVisual_PaletteBase
    pha
    sta.l SourceVisual_DebugEmitPiece+60
    lda.l SourceVisual_PaletteBase
    sta.l SourceVisual_DebugEmitPiece+62
    pla
    cmp #8
    bcc SourceVisual_QueuePalettes__palette_ok
    brl SourceVisual_QueuePalettes__fail
SourceVisual_QueuePalettes__palette_ok:
    sta.l SourceVisual_PaletteSlot
    lda #18
    sta.l SourceVisual_DebugQueueStage
    lda.l SourceVisual_PieceTable+10,x
    sta.l SourceVisual_Temp
    lda.l SourceVisual_PieceTable+11,x
    sta.l SourceVisual_Temp+1
    lda #19
    sta.l SourceVisual_DebugQueueStage
    rep #$20
.a16
    ; The common one-palette case does not need a shifting loop at all.  It
    ; also makes the physical-slot width explicit; the general path below
    ; remains bounded to the eight SNES OBJ palette selectors.
    lda.l SourceVisual_EntryScratch+14
    cmp #1
    bne SourceVisual_QueuePalettes__mask_general
    lda #1
    sta.l SourceVisual_Temp+2
    bra SourceVisual_QueuePalettes__mask_ready
SourceVisual_QueuePalettes__mask_general:
    lda.l SourceVisual_PaletteSlot
    and #$00FF
    tax
    rep #$31
.a16
.i16
    lda #1
SourceVisual_QueuePalettes__mask_shift:
    cpx #0
    beq SourceVisual_QueuePalettes__mask_ready
    asl a
    dex
    bra SourceVisual_QueuePalettes__mask_shift
SourceVisual_QueuePalettes__mask_ready:
    sta.l SourceVisual_Temp+2
    lda.l SourceVisual_PaletteMask
    and.l SourceVisual_Temp+2
    beq SourceVisual_QueuePalettes__mask_new
    brl SourceVisual_QueuePalettes__next
SourceVisual_QueuePalettes__mask_new:
SourceVisual_QueuePalettes__mask_used:
    lda.l SourceVisual_Temp+2
    ora.l SourceVisual_PaletteMask
    sta.l SourceVisual_PaletteMask
SourceVisual_QueuePalettes__palette_lookup:
    ; Global palette table index was captured before X became the local slot.
    rep #$31
.a16
.i16
    lda.l SourceVisual_Temp
    sta.l SourceVisual_DebugD
    ; Palette table rows are also 42 bytes: 32 + 8 + 2.
    lda.l SourceVisual_DebugD
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Temp       ; 32 * palette index
    lda.l SourceVisual_DebugD
    asl a
    asl a
    asl a                         ; 8 * palette index
    clc
    adc.l SourceVisual_Temp
    clc
    adc.l SourceVisual_DebugD
    clc
    adc.l SourceVisual_DebugD     ; 42 * palette index
    clc
    adc #SOURCE_VISUAL_PALETTE_OFFSET
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda #((SOURCE_VISUAL_PALETTE_OFFSET >> 16) & $FF)
    adc #0
    sta.l SourceVisual_Offset+2
    lda #((SOURCE_VISUAL_PALETTE_OFFSET >> 24) & $FF)
    adc #0
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    jsr SourceVisual_AddCatalogBase
    lda #15
    sta.l SourceVisual_DebugQueueStage
    jsr SourceVisual_ReadRow
    jsr SourceVisual_ReadPalettePayload
    lda.l SourceVisual_EntryScratch+14
    cmp #1
    beq SourceVisual_QueuePalettes__done
SourceVisual_QueuePalettes__next:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    brl SourceVisual_QueuePalettes__piece
SourceVisual_QueuePalettes__done:
    sep #$20
.a8
    lda #$AA
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    sec
    rts
SourceVisual_QueuePalettes__fail:
    lda #7
    sta.l SourceVisual_DebugQueueStage
    sep #$20
.a8
    lda #$26
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts

SourceVisual_ReadPalettePayload:
    sep #$20
.a8
    lda #$A8
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    lda.l SourceVisual_RowScratch+34
    sta.l SourceVisual_Offset
    lda.l SourceVisual_RowScratch+36
    sta.l SourceVisual_Offset+2
    sep #$20
.a8
    rep #$31
.a16
.i16
    jsr SourceVisual_AddCatalogBase
    lda #10
    sta.l SourceVisual_DebugQueueStage
    jsr SourceVisual_Seek
    lda #11
    sta.l SourceVisual_DebugQueueStage
    rep #$31
.a16
.i16
    ldx #0
SourceVisual_ReadPalettePayload__read:
    txa
    sta.l SourceVisual_DebugIndex
    sep #$20
.a8
    lda $2001
    sta.l SourceVisual_PaletteTemp,x
    rep #$31
.a16
.i16
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__read
    ; Palette slot is retained explicitly; Y is the piece-row offset.
    lda.l SourceVisual_PaletteSlot
    and #$00FF
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Temp
    lda.l SourceVisual_PaletteSlot
    beq SourceVisual_ReadPalettePayload__copy0
    cmp #1
    beq SourceVisual_ReadPalettePayload__copy1
    cmp #2
    beq SourceVisual_ReadPalettePayload__copy2
    cmp #3
    beq SourceVisual_ReadPalettePayload__copy3
    cmp #4
    beq SourceVisual_ReadPalettePayload__copy4
    cmp #5
    beq SourceVisual_ReadPalettePayload__copy5
    cmp #6
    beq SourceVisual_ReadPalettePayload__copy6
    brl SourceVisual_ReadPalettePayload__copy7
SourceVisual_ReadPalettePayload__copy0:
    ldx #0
SourceVisual_ReadPalettePayload__copy0_loop:
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+0,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy0_loop
    brl SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy1:
    ldx #0
SourceVisual_ReadPalettePayload__copy1_loop:
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+32,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy1_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy2:
    ldx #0
SourceVisual_ReadPalettePayload__copy2_loop:
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+64,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy2_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy3:
    ldx #0
SourceVisual_ReadPalettePayload__copy3_loop:
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+96,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy3_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy4:
    ldx #0
SourceVisual_ReadPalettePayload__copy4_loop:
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+128,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy4_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy5:
    ldx #0
SourceVisual_ReadPalettePayload__copy5_loop:
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+160,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy5_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy6:
    ldx #0
SourceVisual_ReadPalettePayload__copy6_loop:
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+192,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy6_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy7:
    ldx #0
SourceVisual_ReadPalettePayload__copy7_loop:
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+224,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy7_loop
SourceVisual_ReadPalettePayload__queue:
    ; One source palette packet is queued with the same completion ordering as
    ; the sheet.  The actual physical slot is the local palette slot.
    jsl Core_Dma_HasFreeSlot_Long
    bcs SourceVisual_ReadPalettePayload__slot_ok
    brl SourceVisual_QueuePalettes__fail
SourceVisual_ReadPalettePayload__slot_ok:
    lda #SourceVisual_PaletteStaging
    clc
    adc.l SourceVisual_Temp
    sta.l DmaRequest_SourceAddrLow
    lda #$0100
    clc
    adc.l SourceVisual_Temp
    sta.l DmaRequest_TargetAddr
    lda #32
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #$7F
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_CGRAM
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsl Core_Dma_Enqueue_Long
    jsr SourceVisual_TrackRequest
    sep #$20
.a8
    lda #$A9
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    rts

; Associate the just-enqueued request with the queue slot that contains the
; same immutable request fields.  Core_Dma_Enqueue intentionally leaves its
; rotating cursor unchanged, so matching the published slot is safer than
; inferring it from that cursor.  This also keeps the normal DMA ABI intact.
SourceVisual_TrackRequest:
    php
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    clc
    adc #1
    sta.l SourceVisual_DmaToken
    ldx #0
SourceVisual_TrackRequest__scan:
    sep #$20
.a8
.i16
    lda.l DmaQueue+4,x
    bit #DMA_OPT_ACTIVE
    beq SourceVisual_TrackRequest__next
    and #$BF
    cmp.l DmaRequest_TypeFlags
    bne SourceVisual_TrackRequest__next
    lda.l DmaQueue+7,x
    cmp.l DmaRequest_SourceBank
    bne SourceVisual_TrackRequest__next
    rep #$31
.a16
.i16
    lda.l DmaQueue+0,x
    cmp.l DmaRequest_Length
    bne SourceVisual_TrackRequest__next16
    lda.l DmaQueue+2,x
    cmp.l DmaRequest_TargetAddr
    bne SourceVisual_TrackRequest__next16
    lda.l DmaQueue+5,x
    cmp.l DmaRequest_SourceAddrLow
    bne SourceVisual_TrackRequest__next16
    txa
    lsr a
    lsr a
    lsr a
    tay
    tya
    tax
    sep #$20
.a8
.i16
    lda.l SourceVisual_DmaToken
    sta.l SourceVisual_DmaOwner,x
    rep #$31
.a16
.i16
    plp
    sec
    rts
SourceVisual_TrackRequest__next16:
    sep #$20
.a8
.i16
SourceVisual_TrackRequest__next:
    rep #$31
.a16
.i16
    txa
    clc
    adc #DMA_QUEUE_SLOT_SIZE
    tax
    cpx #64
    bcc SourceVisual_TrackRequest__scan
    plp
    clc
    rts

; Carry set while a source-publisher staging transfer is still active.  The
; queue is the hardware ownership authority; matching the source staging
; ranges avoids depending on host-side readiness or on the rotating cursor.
SourceVisual_HasOwnedDma:
    php
    rep #$31
.a16
.i16
    ldx #0
SourceVisual_HasOwnedDma__scan:
    txa
    sta.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
.i16
    lda.l DmaQueue+4,x
    bit #DMA_OPT_ACTIVE
    beq SourceVisual_HasOwnedDma__next
    lda.l DmaQueue+7,x
    cmp #$7E
    bne SourceVisual_HasOwnedDma__next
    rep #$31
.a16
.i16
    lda.l DmaQueue+5,x
    ; Source-owned transfers come from either the eight OBJ palette slots
    ; ($4300-$43FF) or the relocated 1 KiB tile staging buffer
    ; ($5B00-$5EFF).  The old range covered only the former and allowed a
    ; later sheet chunk to overwrite the staging bytes while the prior DMA
    ; still owned them.
    cmp #$4300
    bcc SourceVisual_HasOwnedDma__tile_range
    cmp #$4400
    bcc SourceVisual_HasOwnedDma__owned
SourceVisual_HasOwnedDma__tile_range:
    cmp #$5B00
    bcc SourceVisual_HasOwnedDma__next16
    cmp #$5F00
    bcs SourceVisual_HasOwnedDma__next16
SourceVisual_HasOwnedDma__owned:
    plp
    sec
    rts
SourceVisual_HasOwnedDma__next16:
    sep #$20
.a8
.i16
SourceVisual_HasOwnedDma__next:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceIndex
    clc
    tax
    inx
    cpx #8
    bcc SourceVisual_HasOwnedDma__scan
    plp
    clc
    rts

SourceVisual_RefreshFence:
    jsr SourceVisual_HasOwnedDma
    bcs SourceVisual_RefreshFence__busy
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+2,x
    cmp.l SourceVisual_ChunkCount
    bcc SourceVisual_RefreshFence__busy
    lda.l SourceVisual_State+4,x
    beq SourceVisual_RefreshFence__busy
    lda #2
    sta.l SourceVisual_State+6,x
SourceVisual_RefreshFence__busy:
    rts

SourceVisual_Emit:
    ; Reserve the complete actor packet before touching the OAM shadow.  A
    ; larger source frame may contain 65 pieces, but the hardware shadow has
    ; only 128 entries; fail the whole actor closed instead of overrunning it
    ; or publishing a partial metasprite.
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    clc
    adc.l $7E53A0
    cmp #513
    bcc SourceVisual_Emit__oam_capacity_ok
    sep #$20
.a8
    lda #$A7
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_Emit__oam_capacity_ok:
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_DebugEmitPiece+44
    lda #36
    sta.l SourceVisual_DebugQueueStage
    rep #$31
.a16
.i16
    lda CHAR_POS_X
    sec
    sbc Screen_PosX
    and #$00FF
    sta.l OamSetSprite_X
    sta.l SourceVisual_EmitBaseX
    lda CHAR_POS_Y
    sta.l OamSetSprite_Y
    sta.l SourceVisual_EmitBaseY
    lda #0
    sta.l SourceVisual_PieceIndex
SourceVisual_Emit__piece:
    lda.l SourceVisual_PieceIndex
    sta.l SourceVisual_DebugEmitPiece+46
    sta.l SourceVisual_DebugEmitPiece+56
    lda.l SourceVisual_PieceCount
    sta.l SourceVisual_DebugEmitPiece+50
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceVisual_Emit__have_piece
    brl SourceVisual_Emit__done
SourceVisual_Emit__have_piece:
    lda.l SourceVisual_EmitBaseX
    sta.l OamSetSprite_X
    lda.l SourceVisual_EmitBaseY
    sta.l OamSetSprite_Y
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+14,x
    clc
    adc.l SourceVisual_BaseTile
    sep #$20
.a8
    sta.l OamSetSprite_Tile
    lda.l SourceVisual_PieceTable+8,x
    clc
    adc.l SourceVisual_PaletteBase
    sta.l SourceVisual_DebugEmitPiece+60
    cmp #8
    bcc SourceVisual_Emit__palette_ok
    bra SourceVisual_Emit__palette_bad_near
SourceVisual_Emit__palette_bad_near:
    brl SourceVisual_Emit__palette_fail
SourceVisual_Emit__palette_ok:
    asl a
    ora #$30
    sta.l OamSetSprite_Attr
    ; OBJ names 0..255 address the first 8-KiB character table. Physical
    ; sheet slots 2/3 live in OBSEL's second name table ($A000-$BFFF), so set
    ; OAM attribute bit 0 when the leased tile number is >= $100.
    lda.l SourceVisual_BaseTile
    and #$0100
    beq SourceVisual_Emit__name_table0
    lda.l OamSetSprite_Attr
    ora #$01
    sta.l OamSetSprite_Attr
SourceVisual_Emit__name_table0:
    lda CHAR_FACING_LEFT
    beq SourceVisual_Emit__right
    lda.l SourceVisual_PieceTable+4,x
    clc
    adc.l OamSetSprite_X
    sta.l OamSetSprite_X
    lda.l SourceVisual_PieceTable+6,x
    clc
    adc.l OamSetSprite_Y
    sta.l OamSetSprite_Y
    lda.l OamSetSprite_Attr
    ora #$40
    sta.l OamSetSprite_Attr
    bra SourceVisual_Emit__write
SourceVisual_Emit__right:
    lda.l SourceVisual_PieceTable+0,x
    clc
    adc.l OamSetSprite_X
    sta.l OamSetSprite_X
    lda.l SourceVisual_PieceTable+2,x
    clc
    adc.l OamSetSprite_Y
    sta.l OamSetSprite_Y
SourceVisual_Emit__write:
    lda #37
    sta.l SourceVisual_DebugQueueStage
    lda #1
    sta.l SourceVisual_DebugEmitPiece+48
    lda #0
    sta.l OamSetSprite_Hi
    ; Keep the native OAM write in this loop.  The old helper boundary was
    ; same-bank code, but its return convention made the generic piece loop
    ; terminate after a prefix on the production path.  This is the same
    ; shadow/cursor ABI as Core_Oam_SetSprite, with no actor-specific logic.
    rep #$31
.a16
.i16
    lda.l $7E53A0
    tax
    sep #$20
.a8
    lda.l OamSetSprite_X
    sta.l Oam_Buffer,x
    lda.l OamSetSprite_Y
    sta.l Oam_Buffer+1,x
    lda.l OamSetSprite_Tile
    sta.l Oam_Buffer+2,x
    lda.l OamSetSprite_Attr
    sta.l Oam_Buffer+3,x
    rep #$31
.a16
.i16
    lda.l $7E53A0
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l OamSetSprite_Hi
    sta.l Oam_ExpandedHi,x
    rep #$31
.a16
.i16
    lda.l $7E53A0
    clc
    adc #4
    sta.l $7E53A0
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    jmp SourceVisual_Emit__piece
SourceVisual_Emit__done:
    lda #38
    sta.l SourceVisual_DebugQueueStage
    lda.l Oam_Buffer
    sta.l SourceVisual_DebugSheetRow
    lda.l Oam_Buffer+2
    sta.l SourceVisual_DebugSheetRow+2
    lda.l $7E53A0
    sta.l SourceVisual_DebugStateCompare
    ldx #0
SourceVisual_DebugEmitCopy:
    lda.l SourceVisual_PieceTable,x
    sta.l SourceVisual_DebugEmitPiece,x
    inx
    inx
    cpx #16
    bcc SourceVisual_DebugEmitCopy
    lda.l SourceVisual_PieceCount
    sta.l SourceVisual_DebugEmitPiece+32
    lda.l $7E53A0
    sta.l SourceVisual_DebugEmitPiece+34
    lda.l Oam_Buffer+48
    sta.l SourceVisual_DebugEmitPiece+36
    lda.l Oam_Buffer+50
    sta.l SourceVisual_DebugEmitPiece+38
    ldx #0
SourceVisual_DebugEmitOamCopy:
    lda.l Oam_Buffer,x
    sta.l SourceVisual_DebugEmitOam,x
    inx
    inx
    cpx #64
    bcc SourceVisual_DebugEmitOamCopy
    lda #35
    sta.l SourceVisual_DebugQueueStage
    sec
    rts
SourceVisual_Emit__palette_fail:
    lda.l SourceVisual_PieceIndex
    sta.l SourceVisual_DebugEmitPiece+58
    sep #$20
.a8
    lda #$2A
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts

; Bank-local long-addressing form of the shared OAM shadow write.  The bank-0
; compatibility trampoline uses DB-relative legacy cells; source-sized
; publication must keep the caller's actor D/DBR context intact while writing
; the same shared OAM shadow and cursor.
SourceVisual_SetSprite:
    php
    rep #$31
.a16
.i16
    lda.l SourceVisual_DebugEmitPiece+44
    inc a
    sta.l SourceVisual_DebugEmitPiece+44
    lda.l $7E53A0
    sta.l SourceVisual_DebugEmitPiece+40
    tax
    sep #$20
.a8
    lda.l OamSetSprite_X
    sta.l Oam_Buffer,x
    lda.l OamSetSprite_Y
    sta.l Oam_Buffer+1,x
    lda.l OamSetSprite_Tile
    sta.l Oam_Buffer+2,x
    lda.l OamSetSprite_Attr
    sta.l Oam_Buffer+3,x
    rep #$31
.a16
.i16
    lda.l $7E53A0
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l OamSetSprite_Hi
    sta.l Oam_ExpandedHi,x
    rep #$31
.a16
.i16
    lda.l $7E53A0
    clc
    adc #4
    sta.l $7E53A0
    sta.l SourceVisual_DebugEmitPiece+42
    plp
    rts

; Scratch labels are explicit WRAM addresses above.
