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
SourceVisual_State           = $7E4A80 ; 6 * 32-byte actor visual leases
SourceVisual_DebugSeek      = $7E4A50 ; last 32-bit native seek, diagnostic
SourceVisual_DebugIndex     = $7E4A54 ; matched catalog entry index
SourceVisual_DebugD         = $7E4A56
SourceVisual_DebugLastError = $7E4A58
; Mutable lookup/queue state lives in WRAM.  These must not be emitted as
; .dw ROM labels because the native publisher writes them through long
; addressing on every actor render.
SourceVisual_Temp            = $7E4B50
SourceVisual_BaseTile        = $7E4B52
SourceVisual_PieceCount      = $7E4B54
SourceVisual_SheetBytes      = $7E4B56
SourceVisual_ChunkCount      = $7E4B58
SourceVisual_TotalBytes      = $7E4B5A
SourceVisual_PaletteMask     = $7E4B5C
SourceVisual_PieceIndex      = $7E4B5E
SourceVisual_PaletteSlot     = $7E4B60
SourceVisual_Record          = $7E4B62 ; current actor's 32-byte lease offset
SourceVisual_PaletteBase     = $7E4B64 ; physical OBJ palette base for actor slot
SourceVisual_PresentationMask = $7E4B66 ; actor leases touched this pass
SourceVisual_PresentationField = $7E4B68 ; NMI field owning the presentation mask
SourceVisual_ActorSlot       = $7E4B6A ; actor-context slot 0..5
SourceVisual_DebugRecord     = $7E4B6C ; 8-byte debug row offset for actor slot
SourceVisual_AllocCandidate  = $7E4B70
SourceVisual_AllocRequired   = $7E4B72
SourceVisual_AllocEnd        = $7E4B74
SourceVisual_AllocScan       = $7E4B76
SourceVisual_AllocOtherStart = $7E4B78
SourceVisual_AllocOtherEnd   = $7E4B7A
SourceVisual_AllocPaletteCount = $7E4B7C
SourceVisual_BlockIndex      = $7E4B80
SourceVisual_BlockSlot       = $7E4B82
SourceVisual_BlockRecord     = $7E4B84
SourceVisual_BlockProgress   = $7E4B86
SourceVisual_ActorMapBase    = $7E4B88
SourceVisual_ActorMapIndex   = $7E4B8A
SourceVisual_BlockTileBase   = $7E4B8C
SourceVisual_BlockActorMask  = $7E4B8E
SourceVisual_BlockRow        = $7E4B90
SourceVisual_BlockScan       = $7E4B92
SourceVisual_BlockOther      = $7E4B94
SourceVisual_BlockOther2     = $7E4B96
SourceVisual_BlockDataBytes  = $7E4B98
SourceVisual_BlockTemp       = $7E4B9A
SourceVisual_PaletteGlobalIndex = $7E4B9C ; catalog-global palette identity
SourceVisual_PaletteCacheOffset = $7E4B9E
SourceVisual_PaletteOwnerBit = $7E4BA0
SourceVisual_PaletteOwnerNotBit = $7E4BA1
SourceVisual_PaletteScan     = $7E4BA2
SourceVisual_PaletteLocalSlot = $7E4BA4
SourceVisual_PaletteCacheSlot = $7E4BA6
SourceVisual_PaletteExpectedMask = $7E4BA8
SourceVisual_PieceOffset     = $7E4BAA
; Unlinked contexts retain their visual blocks until the owned DMA fence is
; clear. A slot that is rebound before retirement cancels its queued bit.
SourceVisual_RetireMask      = $7E4BAC
SourceVisual_RetireBit       = $7E4BAD
SourceVisual_RetireScan      = $7E4BAE
SourceVisual_RetireEntityOffset = $7E4BB0
SourceVisual_BlockCache      = $7E4C00 ; 64 * 8-byte content-addressed slots
SourceVisual_ActorPieceMap   = $7E4E00 ; 6 * 65 one-byte block-slot maps
; Eight 8-byte rows: global palette ID [0..1], transfer state [3]
; (0=reserved, 1=ready, 2=DMA pending), actor-owner mask [4].
SourceVisual_PaletteCache    = $7E4FA0
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
SourceVisual_EmitBoundsMode    = $7E44A4 ; 1=pit depth projection / behind panels
SourceVisual_EmitPieceX        = $7E44A6 ; signed viewport coordinates
SourceVisual_EmitPieceY        = $7E44A8
SourceVisual_VisiblePieces     = $7E44AA
SourceVisual_EmitPieceWidth    = $7E44AC
SourceVisual_EmitPieceHeight   = $7E44AE
SourceVisual_PaletteTransferBit = $7E44B0 ; .dw, disjoint from persistent BaseTile
; Persistent Normal rows publish a sampled runtime-role key/frame into the
; same 133-byte StageEnv row. A zero bridge policy remains S-CPU-owned and
; continues to use its native CHAR_SELECTED/CHAR_FRAME_INDEX mapping.
SourceVisual_Sa1OwnerPolicy    = $7E550F+64
SourceVisual_Sa1Frame           = $7E550F+84
SourceVisual_Sa1RuntimeRole    = $7E550F+86
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
SOURCE_VISUAL_TILE_STRIDE = 128 ; legacy constant retained for ABI diagnostics
SOURCE_VISUAL_TILE_BLOCK_BYTES = 256
SOURCE_VISUAL_TILE_BLOCKS = SOURCE_VISUAL_MAX_SHEET / SOURCE_VISUAL_TILE_BLOCK_BYTES
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
    ; Tile staging is a single shared producer, so a queued block must keep
    ; advancing even if the actor that requested it is retired before its
    ; next compositor pass.  Service it independently of the current actor's
    ; residency fast path; otherwise ready actors never visit PrepareBlocks
    ; and an orphaned state-1 cache row can pin the staging slot forever.
    jsr SourceVisual_ResumePendingBlock
    ; Pit-retired actors remain in the gameplay list until canonical unlink.
    ; Do not reacquire their visual lease or emit stale source pieces meanwhile.
    jsl StageBoundsHost_Normal
    bcc SourceVisual_RenderCurrent__lookup
    jsl StageBounds_Row
    lda.l StageBounds_State,x
    cmp #2
    beq SourceVisual_RenderCurrent__retired
SourceVisual_RenderCurrent__lookup:
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
.a16
    jsr SourceVisual_FindEntry
    bcc SourceVisual_RenderCurrent__fail_near
    ; Admission must obey the same viewport as publication. Wholly offscreen
    ; source frames cannot pin the bounded OBJ cache needed by visible actors.
    jsr SourceVisual_FrameInViewport
    bcs SourceVisual_RenderCurrent__visible
    tdc
    sec
    sbc #$0A00
    tax
    jsl SourceVisual_QueueRetireEntityOffset
    jsr SourceVisual_ProcessRetired
    bra SourceVisual_RenderCurrent__retired
SourceVisual_RenderCurrent__visible:
    jsr SourceVisual_SelectResidency
    bcc SourceVisual_RenderCurrent__fail_near
    jsr SourceVisual_LoadResources
    bcc SourceVisual_RenderCurrent__fail_near
    jsr SourceVisual_Emit
    bcc SourceVisual_RenderCurrent__fail_near
    bra SourceVisual_RenderCurrent__publish
SourceVisual_RenderCurrent__fail_near:
    brl SourceVisual_RenderCurrent__fail
SourceVisual_RenderCurrent__publish:
    ; Once this exact source packet has reached the OAM shadow, mark the
    ; actor lease as presentable.  An in-flight lease is kept on its chosen
    ; catalog entry until it emits once; otherwise a fast animation can
    ; replace its key every sampled field and starve multi-block admission.
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+28,x
    rep #$31
.a16
.i16
    sec
    ply
    plx
    pld
    plb
    plp
    rtl
SourceVisual_RenderCurrent__retired:
    rep #$31
.a16
.i16
    sec
    ply
    plx
    pld
    plb
    plp
    rtl

; Conservative source-image rectangle, before any resource lease is pinned.
; SVIS carries source width/height and authored origin in bytes 4..11. The
; artwork is unchanged; per-piece clipping still handles partially visible
; frames. Signed world coordinates never wrap into the 256x224 viewport.
SourceVisual_FrameInViewport:
    rep #$31
    .a16
    .i16
    lda CHAR_POS_X
    sec
    sbc Screen_PosX
    sta.l SourceVisual_EmitBaseX
    lda CHAR_FACING_LEFT
    and #$00FF
    beq SourceVisual_FrameInViewport__right
    lda.l SourceVisual_EmitBaseX
    clc
    adc.l SourceVisual_EntryScratch+8
    inc a                       ; authored mirrored offsets include +1
    sec
    sbc.l SourceVisual_EntryScratch+4
    bra SourceVisual_FrameInViewport__x
SourceVisual_FrameInViewport__right:
    lda.l SourceVisual_EmitBaseX
    sec
    sbc.l SourceVisual_EntryScratch+8
SourceVisual_FrameInViewport__x:
.a16
    bmi SourceVisual_FrameInViewport__x_end
    cmp #256
    bcs SourceVisual_FrameInViewport__outside
SourceVisual_FrameInViewport__x_end:
.a16
    clc
    adc.l SourceVisual_EntryScratch+4
    bmi SourceVisual_FrameInViewport__outside
    beq SourceVisual_FrameInViewport__outside
    lda CHAR_POS_Y
    sta.l SourceVisual_EmitBaseY
    jsl StageBoundsHost_Normal
    bcc SourceVisual_FrameInViewport__y
    jsl StageBounds_Row
    lda.l StageBounds_State,x
    beq SourceVisual_FrameInViewport__y
    cmp #2
    beq SourceVisual_FrameInViewport__outside
    lda.l StageBounds_DrawY,x
    cmp #240
    bcs SourceVisual_FrameInViewport__outside
    sta.l SourceVisual_EmitBaseY
SourceVisual_FrameInViewport__y:
.a16
    lda.l SourceVisual_EmitBaseY
    sec
    sbc.l SourceVisual_EntryScratch+10
    bmi SourceVisual_FrameInViewport__y_end
    cmp #224
    bcs SourceVisual_FrameInViewport__outside
SourceVisual_FrameInViewport__y_end:
    clc
    adc.l SourceVisual_EntryScratch+6
    bmi SourceVisual_FrameInViewport__outside
    beq SourceVisual_FrameInViewport__outside
    sec
    rts
SourceVisual_FrameInViewport__outside:
    jsr SourceVisual_FrameMirrorInViewport
    rts
 ; BOR display_ents mirror uses the same unflipped image at source foot
; (PLAYER_MIN_Z-10)+(PLAYER_MIN_Z-z)-a. The established 4/5 coordinate
; adapter gives ground foot 248-nativeY; authored pose offsets are unchanged.
SourceVisual_FrameMirrorInViewport:
.a16
    lda.l Stage_Mirror
    and #$00FF
    bne SourceVisual_FrameMirrorInViewport__active
    clc
    rts
SourceVisual_FrameMirrorInViewport__active:
.a16
    lda CHAR_POS_X
    sec
    sbc Screen_PosX
    sta.l SourceVisual_EmitBaseX
    lda CHAR_FACING_LEFT
    and #$00FF
    beq SourceVisual_FrameMirrorInViewport__right
    lda.l SourceVisual_EmitBaseX
    clc
    adc.l SourceVisual_EntryScratch+8
    inc a
    sec
    sbc.l SourceVisual_EntryScratch+4
    bra SourceVisual_FrameMirrorInViewport__x
SourceVisual_FrameMirrorInViewport__right:
    lda.l SourceVisual_EmitBaseX
    sec
    sbc.l SourceVisual_EntryScratch+8
SourceVisual_FrameMirrorInViewport__x:
.a16
    bmi SourceVisual_FrameMirrorInViewport__x_end
    cmp #256
    bcs SourceVisual_FrameMirrorInViewport__outside
SourceVisual_FrameMirrorInViewport__x_end:
.a16
    clc
    adc.l SourceVisual_EntryScratch+4
    bmi SourceVisual_FrameMirrorInViewport__outside
    beq SourceVisual_FrameMirrorInViewport__outside
    lda #248
    sec
    sbc CHAR_POS_Y
    sec
    sbc.l SourceVisual_EntryScratch+10
    bmi SourceVisual_FrameMirrorInViewport__y_end
    cmp #224
    bcs SourceVisual_FrameMirrorInViewport__outside
SourceVisual_FrameMirrorInViewport__y_end:
    clc
    adc.l SourceVisual_EntryScratch+6
    bmi SourceVisual_FrameMirrorInViewport__outside
    beq SourceVisual_FrameMirrorInViewport__outside
    sec
    rts
SourceVisual_FrameMirrorInViewport__outside:
    clc
    rts
SourceVisual_RenderCurrent__fail:
.a16
.i16
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
    lda.l SourceVisual_DebugRecord
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
    rep #$31
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    sep #$20
.a8
    lda CHAR_ROSTER_INDEX
    sta.l SourceVisual_Key+0
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_HOLE
    beq SourceVisual_FindEntry__hole
    lda.l SourceVisual_Sa1OwnerPolicy,x
    beq SourceVisual_FindEntry__native_state
    ; The SA-1 owns grounded source roles. BOR's existing player jump remains
    ; a native physical-frame substate, so use its source-sized jump key/frame
    ; while that discriminator is active without exporting it back to WRAM.
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_JUMP
    beq SourceVisual_FindEntry__source_jump
    lda.l SourceVisual_Sa1RuntimeRole,x
    sta.l SourceVisual_Key+1
    lda.l SourceVisual_Sa1Frame,x
    sta.l SourceVisual_Key+2
    brl SourceVisual_FindEntry__map_ready
SourceVisual_FindEntry__source_jump:
.a8
    ; The source-sized catalog keys the player's authored jump animation by
    ; its SOURCE runtime role 7, not the legacy physical selected value 5.
    ; Keep frame lookup on the native player frame index.
    lda #7
    sta.l SourceVisual_Key+1
    lda CHAR_FRAME_INDEX
    cmp #$FF
    bne SourceVisual_FindEntry__source_jump_frame
    lda #0
SourceVisual_FindEntry__source_jump_frame:
    sta.l SourceVisual_Key+2
    bra SourceVisual_FindEntry__map_ready
SourceVisual_FindEntry__hole:
.a8
    ; Pit descent is a per-instance physics state, but its authored visual is
    ; the model's first source fall pose. Do not inherit the interrupted role's
    ; frame or map while Z motion is active.
    lda #4
    sta.l SourceVisual_Key+1
    lda #0
    sta.l SourceVisual_Key+2
    sta.l SourceVisual_Key+3
    bra SourceVisual_FindEntry__key_ready
SourceVisual_FindEntry__native_state:
.a8
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
    cmp #CHAR_SELECTED_THROWN
    beq SourceVisual_FindEntry__thrown
    brl SourceVisual_FindEntry__unsupported
SourceVisual_FindEntry__idle:
.a8
    lda #0
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__walk:
.a8
    lda #1
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__attack:
.a8
    lda CHAR_ATTACK_VARIANT
    beq SourceVisual_FindEntry__attack1
    lda #3
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__attack1:
.a8
    lda #2
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__fall:
.a8
    lda #4
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__rise:
.a8
    lda #5
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__special:
.a8
    lda #6
    bra SourceVisual_FindEntry__role
SourceVisual_FindEntry__thrown:
.a8
    ; THROWN is a physics substate, not a distinct authored visual role.
    ; Present the first source-sized fall pose until the native landing path
    ; enters CHAR_SELECTED_FALL. Its map is animation-specific, so do not
    ; reuse the stale map index from the attack/idle role that was interrupted.
    lda #4
    sta.l SourceVisual_Key+1
    lda #0
    sta.l SourceVisual_Key+2
    sta.l SourceVisual_Key+3
    bra SourceVisual_FindEntry__key_ready
SourceVisual_FindEntry__role:
.a8
    sta.l SourceVisual_Key+1
    lda CHAR_FRAME_INDEX
    cmp #$FF
    bne SourceVisual_FindEntry__frame_ready
    lda #0
SourceVisual_FindEntry__frame_ready:
    sta.l SourceVisual_Key+2
SourceVisual_FindEntry__map_ready:
    .a8
    lda CHAR_MAP_INDEX
    sta.l SourceVisual_Key+3
SourceVisual_FindEntry__key_ready:

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
    brl SourceVisual_FindEntry__unsupported_scan
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
    ; Preserve the carry out of index*24 before adding the 18-byte header.
    ; The full catalog reaches byte offset $01553A; adding the header first
    ; and then using ADC's carry loses that multiply carry whenever the low
    ; word itself does not overflow on the header addition.
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
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda #0
    adc #0
    sta.l SourceVisual_Offset+2
    lda #0
    sta.l SourceVisual_Offset+3
    rep #$20
.a16
    clc
    lda.l SourceVisual_Offset
    adc #18
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda.l SourceVisual_Offset+2
    adc #0
    sta.l SourceVisual_Offset+2
    rep #$31
.a16
.i16
    jsr SourceVisual_AddCatalogBase
    jsr SourceVisual_ReadEntry
    sec
    rts

; Select the lease owned by this actor context. Sheets are allocated later,
; after the catalog row supplies their exact byte size. A changed actor key
; may release only that actor's old lease; other actors' live OAM resources
; are never evicted to make the new frame fit.
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
.a16
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
    jsr SourceVisual_CancelActorRetire
    ; Record stride is 32 bytes, while the adjacent diagnostic row
    ; remains the historical 8-byte-per-actor layout.
    tya
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Record
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    sta.l SourceVisual_DebugRecord
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+6,x
    beq SourceVisual_SelectResidency__replace
    ; A reused physical slot is a new source identity. An unfinished packet
    ; from its previous model must never be resumed for the new actor.
    sep #$20
    .a8
    lda.l SourceVisual_State+29,x
    cmp.l SourceVisual_Key
    bne SourceVisual_SelectResidency__identity_changed
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceVisual_SelectResidency__found
    ; Do not abandon a source frame whose tiles/palette have not yet produced
    ; one complete OAM packet.  Its catalog key is the lease entry, not the
    ; actor's newer live animation key; resume it and publish once before
    ; beginning the next sampled frame transaction.
    sep #$20
.a8
    lda.l SourceVisual_State+28,x
    bne SourceVisual_SelectResidency__replace_ready
    rep #$31
.a16
.i16
    jsr SourceVisual_LoadPendingEntry
    brl SourceVisual_SelectResidency__found
SourceVisual_SelectResidency__replace_ready:
    rep #$31
.a16
.i16
    bra SourceVisual_SelectResidency__replace
SourceVisual_SelectResidency__identity_changed:
    rep #$31
    .a16
    .i16
SourceVisual_SelectResidency__replace:
    ; The shared source staging buffer and queued DMA must be retired before
    ; the old lease can be returned to the bounded allocator.
    jsr SourceVisual_HasOwnedDma
    bcc SourceVisual_SelectResidency__clear_record
    brl SourceVisual_SelectResidency__busy
SourceVisual_SelectResidency__clear_record:
.a16
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes
    lda.l SourceVisual_Record
    tax
    lda #0
    ldy #16
SourceVisual_SelectResidency__clear_loop:
    sta.l SourceVisual_State,x
    inx
    inx
    dey
    bne SourceVisual_SelectResidency__clear_loop
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_State,x
    sep #$20
    .a8
    lda.l SourceVisual_Key
    sta.l SourceVisual_State+29,x
    rep #$31
    .a16
    .i16
    lda #1
    sta.l SourceVisual_State+6,x
    lda #0
    sta.l SourceVisual_BaseTile
    sta.l SourceVisual_PaletteBase
    bra SourceVisual_SelectResidency__mark
SourceVisual_SelectResidency__found:
    ; ReadEntry clobbers X when an unfinished animation lease is resumed.
    ; Resolve the actor record again before loading persistent lease fields.
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+8,x
    sta.l SourceVisual_BaseTile
    lda.l SourceVisual_State+12,x
    sta.l SourceVisual_PaletteBase
SourceVisual_SelectResidency__mark:
.a16
    ; Retain the per-field actor witness for runtime diagnostics.
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_SelectResidency__mask_shift:
.i16
    cpx #0
    beq SourceVisual_SelectResidency__mask_ready
    asl a
    dex
    bra SourceVisual_SelectResidency__mask_shift
SourceVisual_SelectResidency__mask_ready:
    ora.l SourceVisual_PresentationMask
    sta.l SourceVisual_PresentationMask
    jsr SourceVisual_ProcessRetired
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

; Restore the catalog row selected by this actor's unfinished lease after
; FindEntry observed a newer live animation key.  The 24-byte entry table is
; addressed by 18 + entryIndex*24 in the compiler-owned SVIS stream.
SourceVisual_LoadPendingEntry:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State,x
    sta.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_DebugIndex
    sta.l SourceVisual_Temp
    asl a
    clc
    adc.l SourceVisual_Temp
    asl a
    asl a
    asl a
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda #0
    adc #0
    sta.l SourceVisual_Offset+2
    lda #0
    sta.l SourceVisual_Offset+3
    rep #$20
.a16
    clc
    lda.l SourceVisual_Offset
    adc #18
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda.l SourceVisual_Offset+2
    adc #0
    sta.l SourceVisual_Offset+2
    rep #$31
.a16
.i16
    jsr SourceVisual_AddCatalogBase
    jsr SourceVisual_ReadEntry
    ; The first four entry bytes are the exact roster/role/frame/map key.
    ; Keep FindEntry's one-key cache coherent with the restored lease so the
    ; next live-key change takes the normal catalog lookup path.
    lda.l SourceVisual_EntryScratch
    sta.l SourceVisual_Key
    sta.l SourceVisual_KeySaved
    lda.l SourceVisual_EntryScratch+2
    sta.l SourceVisual_Key+2
    sta.l SourceVisual_KeySaved+2
    sec
    rts

; Remove a newly live actor slot from the deferred-retirement set. This runs
; as soon as the current source key resolves, before any old lease is tested
; or resource admission can fail.
SourceVisual_CancelActorRetire:
    php
    pha
    phx
    phy
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    tay
    lda #1
SourceVisual_CancelActorRetire__shift:
.i16
    cpy #0
    beq SourceVisual_CancelActorRetire__mask
    asl a
    dey
    bra SourceVisual_CancelActorRetire__shift
SourceVisual_CancelActorRetire__mask:
    sep #$20
.a8
    eor #$FF
    and.l SourceVisual_RetireMask
    sta.l SourceVisual_RetireMask
    rep #$31
.a16
.i16
    ply
    plx
    pla
    plp
    rts

; S6Host_RemoveHandle queues the native entity offset after the worker has
; confirmed unlink. The source lease is retired later, outside any transfer
; that may still reference its staging payload.
SourceVisual_QueueRetireEntityOffset:
    php
    pha
    phx
    phy
    rep #$31
.a16
.i16
    txa
    ldy #0
SourceVisual_QueueRetireEntityOffset__slot:
.a16
    cmp #0
    beq SourceVisual_QueueRetireEntityOffset__bit
    sec
    sbc #CHAR_ZP_LEN
    bcc SourceVisual_QueueRetireEntityOffset__return
    iny
    cpy #6
    bcc SourceVisual_QueueRetireEntityOffset__slot
    bra SourceVisual_QueueRetireEntityOffset__return
SourceVisual_QueueRetireEntityOffset__bit:
.i16
    cpy #6
    bcs SourceVisual_QueueRetireEntityOffset__return
    lda #1
SourceVisual_QueueRetireEntityOffset__shift:
.i16
    cpy #0
    beq SourceVisual_QueueRetireEntityOffset__mark
    asl a
    dey
    bra SourceVisual_QueueRetireEntityOffset__shift
SourceVisual_QueueRetireEntityOffset__mark:
    sep #$20
.a8
    ora.l SourceVisual_RetireMask
    sta.l SourceVisual_RetireMask
    rep #$31
.a16
.i16
SourceVisual_QueueRetireEntityOffset__return:
    ply
    plx
    pla
    plp
    rtl

; Drain unlink retirements only after every source-owned DMA has retired.
; Release the complete actor ownership mask, not just the last requested
; frame, so a dead slot cannot pin blocks needed by a later active actor.
SourceVisual_ProcessRetired:
    php
    pha
    phx
    phy
    rep #$31
.a16
    .i16
    lda.l SourceVisual_RetireMask
    and #$00FF
    bne SourceVisual_ProcessRetired__mask_present
    brl SourceVisual_ProcessRetired__return
SourceVisual_ProcessRetired__mask_present:
    jsr SourceVisual_HasOwnedDma
    bcc SourceVisual_ProcessRetired__dma_idle
    brl SourceVisual_ProcessRetired__return
SourceVisual_ProcessRetired__dma_idle:
.a16
    lda.l SourceVisual_ActorSlot
    pha
    lda.l SourceVisual_Record
    pha
    lda #0
    sta.l SourceVisual_RetireScan
SourceVisual_ProcessRetired__scan:
.a16
    lda.l SourceVisual_RetireScan
    cmp #6
    bcs SourceVisual_ProcessRetired__restore
    lda.l SourceVisual_RetireScan
    tay
    lda #1
SourceVisual_ProcessRetired__bit:
.i16
    cpy #0
    beq SourceVisual_ProcessRetired__check
    asl a
    dey
    bra SourceVisual_ProcessRetired__bit
SourceVisual_ProcessRetired__check:
    sep #$20
.a8
    sta.l SourceVisual_RetireBit
    and.l SourceVisual_RetireMask
    beq SourceVisual_ProcessRetired__next8
    rep #$31
.a16
.i16
    lda.l SourceVisual_RetireScan
    sta.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Record
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes
    lda.l SourceVisual_Record
    clc
    adc #6
    tax
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_State+6,x
    lda.l SourceVisual_RetireBit
    eor #$FF
    and.l SourceVisual_RetireMask
    sta.l SourceVisual_RetireMask
    rep #$31
.a16
.i16
    bra SourceVisual_ProcessRetired__next
SourceVisual_ProcessRetired__next8:
    rep #$31
.a16
.i16
SourceVisual_ProcessRetired__next:
    lda.l SourceVisual_RetireScan
    inc a
    sta.l SourceVisual_RetireScan
    bra SourceVisual_ProcessRetired__scan
SourceVisual_ProcessRetired__restore:
    pla
    sta.l SourceVisual_Record
    pla
    sta.l SourceVisual_ActorSlot
SourceVisual_ProcessRetired__return:
    ply
    plx
    pla
    plp
    rts

; Release the current actor's references from the shared content-addressed
; cache. SelectResidency calls this only after source DMA has retired.
SourceVisual_ReleaseActorBlocks:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_ReleaseActorBlocks__mask:
.i16
    cpx #0
    beq SourceVisual_ReleaseActorBlocks__mask_ready
    asl a
    dex
    bra SourceVisual_ReleaseActorBlocks__mask
SourceVisual_ReleaseActorBlocks__mask_ready:
    sep #$20
.a8
    sta.l SourceVisual_BlockActorMask
    eor #$FF
    sta.l SourceVisual_BlockOther2
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockScan
SourceVisual_ReleaseActorBlocks__scan:
.a16
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcs SourceVisual_ReleaseActorBlocks__done
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    and.l SourceVisual_BlockOther2
    sta.l SourceVisual_BlockCache+4,x
    bne SourceVisual_ReleaseActorBlocks__next
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockCache+2,x
    sta.l SourceVisual_BlockCache+6,x
SourceVisual_ReleaseActorBlocks__next:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    bra SourceVisual_ReleaseActorBlocks__scan
SourceVisual_ReleaseActorBlocks__done:
    rts

; Drop this actor's references to exact, globally deduplicated CGRAM palettes.
; Residency replacement reaches here only after its owned palette DMA retires.
SourceVisual_ReleaseActorPalettes:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_ReleaseActorPalettes__owner_bit:
.i16
    cpx #0
    beq SourceVisual_ReleaseActorPalettes__owner_ready
    asl a
    dex
    bra SourceVisual_ReleaseActorPalettes__owner_bit
SourceVisual_ReleaseActorPalettes__owner_ready:
    sep #$20
.a8
    sta.l SourceVisual_PaletteOwnerBit
    eor #$FF
    sta.l SourceVisual_PaletteOwnerNotBit
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_PaletteScan
SourceVisual_ReleaseActorPalettes__scan:
.a16
    lda.l SourceVisual_PaletteScan
    cmp #8
    bcs SourceVisual_ReleaseActorPalettes__done
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    and.l SourceVisual_PaletteOwnerNotBit
    sta.l SourceVisual_PaletteCache+4,x
    bne SourceVisual_ReleaseActorPalettes__next
    lda #0
    sta.l SourceVisual_PaletteCache+3,x
    rep #$20
.a16
    lda #0
    sta.l SourceVisual_PaletteCache,x
    sep #$20
.a8
SourceVisual_ReleaseActorPalettes__next:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteScan
    inc a
    sta.l SourceVisual_PaletteScan
    bra SourceVisual_ReleaseActorPalettes__scan
SourceVisual_ReleaseActorPalettes__done:
    rts

; Retained diagnostic-era whole-sheet allocator. Source-sized publication now
; resolves per-piece content blocks through SourceVisual_BlockCache instead.
SourceVisual_AllocateTiles:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+10,x
    beq SourceVisual_AllocateTiles__find
    lda.l SourceVisual_State+8,x
    sta.l SourceVisual_BaseTile
    sec
    rts
SourceVisual_AllocateTiles__find:
.a16
    lda.l SourceVisual_SheetBytes
    clc
    adc #SOURCE_VISUAL_TILE_BLOCK_BYTES-1
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    sta.l SourceVisual_AllocRequired
    lda.l SourceVisual_AllocRequired
    bne SourceVisual_AllocateTiles__nonzero
    brl SourceVisual_AllocateTiles__fail
SourceVisual_AllocateTiles__nonzero:
.a16
    lda #0
    sta.l SourceVisual_AllocCandidate
SourceVisual_AllocateTiles__candidate:
.a16
    lda.l SourceVisual_AllocCandidate
    clc
    adc.l SourceVisual_AllocRequired
    cmp #SOURCE_VISUAL_TILE_BLOCKS+1
    bcc SourceVisual_AllocateTiles__range_ok
    brl SourceVisual_AllocateTiles__fail
SourceVisual_AllocateTiles__range_ok:
.a16
    sta.l SourceVisual_AllocEnd
    lda #0
    sta.l SourceVisual_AllocScan
SourceVisual_AllocateTiles__scan:
.a16
    lda.l SourceVisual_AllocScan
    cmp #6
    bcs SourceVisual_AllocateTiles__claim
    asl a
    asl a
    asl a
    sta.l SourceVisual_Temp
    asl a
    clc
    adc.l SourceVisual_Temp
    tax
    txa
    cmp.l SourceVisual_Record
    beq SourceVisual_AllocateTiles__next
    lda.l SourceVisual_State+10,x
    beq SourceVisual_AllocateTiles__next
    lda.l SourceVisual_State+8,x
    lsr a
    lsr a
    lsr a
    sta.l SourceVisual_AllocOtherStart
    clc
    adc.l SourceVisual_State+10,x
    sta.l SourceVisual_AllocOtherEnd
    lda.l SourceVisual_AllocCandidate
    cmp.l SourceVisual_AllocOtherEnd
    bcs SourceVisual_AllocateTiles__next
    lda.l SourceVisual_AllocEnd
    cmp.l SourceVisual_AllocOtherStart
    bcc SourceVisual_AllocateTiles__next
    lda.l SourceVisual_AllocCandidate
    inc a
    sta.l SourceVisual_AllocCandidate
    bra SourceVisual_AllocateTiles__candidate
SourceVisual_AllocateTiles__next:
    lda.l SourceVisual_AllocScan
    inc a
    sta.l SourceVisual_AllocScan
    bra SourceVisual_AllocateTiles__scan
SourceVisual_AllocateTiles__claim:
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_AllocCandidate
    asl a
    asl a
    asl a
    sta.l SourceVisual_State+8,x
    sta.l SourceVisual_BaseTile
    lda.l SourceVisual_AllocRequired
    sta.l SourceVisual_State+10,x
    sec
    rts
SourceVisual_AllocateTiles__fail:
    clc
    rts

; Build a per-actor local-selector -> physical OBJ-palette map. Global palette
; table rows are content-addressed by the compiler, so identical source
; palettes share one of the eight physical SNES OBJ palette slots.
SourceVisual_AllocatePalettes:
    rep #$31
.a16
.i16
    lda.l SourceVisual_EntryScratch+14
    and #$00FF
    bne SourceVisual_AllocatePalettes__count_nonzero
    brl SourceVisual_AllocatePalettes__fail
SourceVisual_AllocatePalettes__count_nonzero:
.a16
    cmp #9
    bcc SourceVisual_AllocatePalettes__count_ok
    brl SourceVisual_AllocatePalettes__fail
SourceVisual_AllocatePalettes__count_ok:
    sta.l SourceVisual_AllocPaletteCount
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+14,x
    beq SourceVisual_AllocatePalettes__map
    cmp.l SourceVisual_AllocPaletteCount
    beq SourceVisual_AllocatePalettes__already_mapped
    brl SourceVisual_AllocatePalettes__fail
SourceVisual_AllocatePalettes__already_mapped:
    ; Physical CGRAM slots can be reused after a retirement or failed
    ; admission. A matching selector count is not an identity/ownership proof.
    jsr SourceVisual_ValidatePaletteMap
    bcc SourceVisual_AllocatePalettes__repair_map
    sec
    rts
SourceVisual_AllocatePalettes__repair_map:
.a16
    jsr SourceVisual_ReleaseActorPalettes
    lda.l SourceVisual_Record
    tax
    lda #0
    sta.l SourceVisual_State+4,x
    sta.l SourceVisual_State+14,x
    ; Rebuild every local selector below; stale physical pointers are ignored.

SourceVisual_AllocatePalettes__map:
.a16
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_AllocatePalettes__owner_bit:
.i16
    cpx #0
    beq SourceVisual_AllocatePalettes__owner_ready
    asl a
    dex
    bra SourceVisual_AllocatePalettes__owner_bit
SourceVisual_AllocatePalettes__owner_ready:
    sep #$20
.a8
    sta.l SourceVisual_PaletteOwnerBit
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_PaletteMask
    sta.l SourceVisual_PieceIndex
SourceVisual_AllocatePalettes__piece:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceVisual_AllocatePalettes__piece_present
    brl SourceVisual_AllocatePalettes__complete
SourceVisual_AllocatePalettes__piece_present:
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_PaletteLocalSlot
    lda.l SourceVisual_PieceTable+8,x
    sta.l SourceVisual_PaletteLocalSlot
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceTable+10,x
    sta.l SourceVisual_PaletteGlobalIndex
    lda.l SourceVisual_PaletteLocalSlot
    cmp.l SourceVisual_AllocPaletteCount
    bcc SourceVisual_AllocatePalettes__local_ok
    brl SourceVisual_AllocatePalettes__bad_map
SourceVisual_AllocatePalettes__local_ok:
.a16
    lda.l SourceVisual_PaletteLocalSlot
    tax
    lda #1
SourceVisual_AllocatePalettes__piece_mask_shift:
.i16
    cpx #0
    beq SourceVisual_AllocatePalettes__piece_mask_ready
    asl a
    dex
    bra SourceVisual_AllocatePalettes__piece_mask_shift
SourceVisual_AllocatePalettes__piece_mask_ready:
.a16
    sta.l SourceVisual_Temp
    lda.l SourceVisual_PaletteMask
    and.l SourceVisual_Temp
    bne SourceVisual_AllocatePalettes__piece_next
    lda.l SourceVisual_PaletteMask
    ora.l SourceVisual_Temp
    sta.l SourceVisual_PaletteMask
    jsr SourceVisual_AllocatePaletteIdentity
    bcc SourceVisual_AllocatePalettes__bad_map
    lda.l SourceVisual_Record
    clc
    adc #16
    clc
    adc.l SourceVisual_PaletteLocalSlot
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCacheSlot
    inc a
    sta.l SourceVisual_State,x
    rep #$31
.a16
.i16
SourceVisual_AllocatePalettes__piece_next:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    brl SourceVisual_AllocatePalettes__piece

SourceVisual_AllocatePalettes__complete:
.a16
    lda #0
    sta.l SourceVisual_PaletteExpectedMask
    lda #1
    sta.l SourceVisual_Temp
    lda.l SourceVisual_AllocPaletteCount
    tax
SourceVisual_AllocatePalettes__expected_loop:
.i16
    cpx #0
    beq SourceVisual_AllocatePalettes__expected_ready
    lda.l SourceVisual_PaletteExpectedMask
    ora.l SourceVisual_Temp
    sta.l SourceVisual_PaletteExpectedMask
    lda.l SourceVisual_Temp
    asl a
    sta.l SourceVisual_Temp
    dex
    bra SourceVisual_AllocatePalettes__expected_loop
SourceVisual_AllocatePalettes__expected_ready:
.a16
    lda.l SourceVisual_PaletteMask
    cmp.l SourceVisual_PaletteExpectedMask
    bne SourceVisual_AllocatePalettes__bad_map
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_AllocPaletteCount
    sta.l SourceVisual_State+14,x
    lda #0
    sta.l SourceVisual_State+12,x
    sec
    rts

SourceVisual_AllocatePalettes__bad_map:
.a16
.i16
    jsr SourceVisual_ReleaseActorPalettes
    lda.l SourceVisual_Record
    clc
    adc #16
    tax
    sep #$20
.a8
    lda #0
    ldy #8
SourceVisual_AllocatePalettes__clear_map:
    sta.l SourceVisual_State,x
    inx
    dey
    bne SourceVisual_AllocatePalettes__clear_map
    rep #$31
.a16
.i16
SourceVisual_AllocatePalettes__fail:
.a16
    lda.l SourceVisual_Record
    tax
    lda #0
    sta.l SourceVisual_State+12,x
    sta.l SourceVisual_State+14,x
    clc
    rts

; A16/I16, C=true only when every immutable piece palette still resolves
; to the actor-owned content identity. Transfer retirement is fenced later.
SourceVisual_ValidatePaletteMap:
.a16
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_ValidatePaletteMap__owner:
.i16
    cpx #0
    beq SourceVisual_ValidatePaletteMap__owner_ready
    asl a
    dex
    bra SourceVisual_ValidatePaletteMap__owner
SourceVisual_ValidatePaletteMap__owner_ready:
.a16
    sta.l SourceVisual_PaletteTransferBit
    lda #0
    sta.l SourceVisual_PieceIndex
SourceVisual_ValidatePaletteMap__piece:
.a16
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcs SourceVisual_ValidatePaletteMap__valid
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+10,x
    sta.l SourceVisual_PaletteGlobalIndex
    lda.l SourceVisual_PieceTable+8,x
    and #$00FF
    clc
    adc.l SourceVisual_Record
    clc
    adc #16
    tax
    lda.l SourceVisual_State,x
    and #$00FF
    beq SourceVisual_ValidatePaletteMap__invalid
    dec a
    cmp #8
    bcs SourceVisual_ValidatePaletteMap__invalid
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache,x
    cmp.l SourceVisual_PaletteGlobalIndex
    bne SourceVisual_ValidatePaletteMap__invalid
    lda.l SourceVisual_PaletteCache+4,x
    and #$00FF
    and.l SourceVisual_PaletteTransferBit
    beq SourceVisual_ValidatePaletteMap__invalid
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    bra SourceVisual_ValidatePaletteMap__piece
SourceVisual_ValidatePaletteMap__valid:
    sec
    rts
SourceVisual_ValidatePaletteMap__invalid:
    clc
    rts

SourceVisual_AllocatePaletteIdentity:
.a16
    lda #0
    sta.l SourceVisual_PaletteScan
SourceVisual_AllocatePaletteIdentity__find:
.a16
    lda.l SourceVisual_PaletteScan
    cmp #8
    bcs SourceVisual_AllocatePaletteIdentity__free_start
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    beq SourceVisual_AllocatePaletteIdentity__find_next_a8
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteCache,x
    cmp.l SourceVisual_PaletteGlobalIndex
    beq SourceVisual_AllocatePaletteIdentity__found
    bra SourceVisual_AllocatePaletteIdentity__find_next
SourceVisual_AllocatePaletteIdentity__find_next_a8:
    rep #$31
.a16
.i16
SourceVisual_AllocatePaletteIdentity__find_next:
    lda.l SourceVisual_PaletteScan
    inc a
    sta.l SourceVisual_PaletteScan
    bra SourceVisual_AllocatePaletteIdentity__find
SourceVisual_AllocatePaletteIdentity__found:
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    ora.l SourceVisual_PaletteOwnerBit
    sta.l SourceVisual_PaletteCache+4,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteScan
    sta.l SourceVisual_PaletteCacheSlot
    sec
    rts
SourceVisual_AllocatePaletteIdentity__free_start:
.a16
.i16
    lda #0
    sta.l SourceVisual_PaletteScan
SourceVisual_AllocatePaletteIdentity__free:
.a16
    lda.l SourceVisual_PaletteScan
    cmp #8
    bcs SourceVisual_AllocatePaletteIdentity__fail
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    bne SourceVisual_AllocatePaletteIdentity__free_next_a8
    lda.l SourceVisual_PaletteOwnerBit
    sta.l SourceVisual_PaletteCache+4,x
    lda #0
    sta.l SourceVisual_PaletteCache+3,x
    rep #$20
.a16
    lda.l SourceVisual_PaletteGlobalIndex
    sta.l SourceVisual_PaletteCache,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteScan
    sta.l SourceVisual_PaletteCacheSlot
    sec
    rts
SourceVisual_AllocatePaletteIdentity__free_next_a8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteScan
    inc a
    sta.l SourceVisual_PaletteScan
    bra SourceVisual_AllocatePaletteIdentity__free
SourceVisual_AllocatePaletteIdentity__fail:
    clc
    rts

SourceVisual_MarkPaletteDmaRetired:
.a16
    lda #0
    sta.l SourceVisual_PaletteScan
SourceVisual_MarkPaletteDmaRetired__scan:
.a16
    lda.l SourceVisual_PaletteScan
    cmp #8
    bcs SourceVisual_MarkPaletteDmaRetired__done
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    beq SourceVisual_MarkPaletteDmaRetired__next_a8
    lda.l SourceVisual_PaletteCache+3,x
    cmp #2
    bne SourceVisual_MarkPaletteDmaRetired__next_a8
    lda #1
    sta.l SourceVisual_PaletteCache+3,x
SourceVisual_MarkPaletteDmaRetired__next_a8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteScan
    inc a
    sta.l SourceVisual_PaletteScan
    bra SourceVisual_MarkPaletteDmaRetired__scan
SourceVisual_MarkPaletteDmaRetired__done:
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
SourceVisual_FindEntry__unsupported_scan:
    plx
SourceVisual_FindEntry__unsupported:
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
    sta.l SourceVisual_PieceCount
    beq SourceVisual_LoadResources__piece_count_valid
    cmp #SOURCE_VISUAL_MAX_PIECES+1
    bcc SourceVisual_LoadResources__piece_count_valid
    brl SourceVisual_LoadResources__bad
SourceVisual_LoadResources__piece_count_valid:
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
    lda.l SourceVisual_DebugRecord
    tax
    lda.l SourceVisual_Key
    sta.l SourceVisual_DebugTrace,x
    lda.l SourceVisual_Key+2
    sta.l SourceVisual_DebugTrace+2,x
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_DebugTrace+4,x
    lda.l SourceVisual_PieceCount
    beq SourceVisual_LoadResources__transparent
    ; Normal visuals resolve shared source OBJ blocks. Palette identities are
    ; mapped after the piece rows have been loaded on the block path below.
    brl SourceVisual_LoadResources__block_path

SourceVisual_LoadResources__transparent:
.a16
    ; An authored frame with no visible pixels is a valid zero-OAM
    ; presentation, not malformed resource metadata. No palette or tile lease
    ; is required; SelectResidency already released the actor's old resources.
    lda.l SourceVisual_Record
    tax
    lda #2
    sta.l SourceVisual_State+6,x
    sec
    rts

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
.a16
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
    jsr SourceVisual_AllocateTiles
    bcs SourceVisual_LoadResources__tiles_allocated
    brl SourceVisual_LoadResources__tile_admission
SourceVisual_LoadResources__tiles_allocated:
.a16
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
.a16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+2,x
    cmp.l SourceVisual_ChunkCount
    bcc SourceVisual_LoadResources__need_transfer
    lda #2
    sta.l SourceVisual_State+6,x
    brl SourceVisual_LoadResources__ready
SourceVisual_LoadResources__need_transfer:
.a16
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
.a16
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
.a16
    lda.l SourceVisual_Record
    tax
    lda #1
    sta.l SourceVisual_State+4,x
    lda #6
    sta.l SourceVisual_DebugQueueStage
SourceVisual_LoadResources__palette_done:
    jsr SourceVisual_QueueSheet
    bcs SourceVisual_LoadResources__sheet_queue_ok
    brl SourceVisual_LoadResources__bad
SourceVisual_LoadResources__sheet_queue_ok:
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+2,x
    cmp.l SourceVisual_ChunkCount
    bcc SourceVisual_LoadResources__pending
    ; The final chunk was only queued on this invocation.  It is not ready
    ; until the next compositor pass observes the completed DMA fence.
SourceVisual_LoadResources__pending:
.a16
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
SourceVisual_LoadResources__palette_admission:
    sep #$20
.a8
    lda #$26
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_LoadResources__tile_admission:
    sep #$20
.a8
    lda #$24
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

SourceVisual_LoadResources__block_path:
.a16
    ; Retain the catalog's source-sheet bound as the fail-closed guard for the
    ; known oversized frame set, but do not reserve or upload this padded sheet.
    lda.l SourceVisual_EntryScratch+20
    sta.l SourceVisual_DebugD
    lda.l SourceVisual_DebugD
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Temp
    lda.l SourceVisual_DebugD
    asl a
    asl a
    asl a
    clc
    adc.l SourceVisual_Temp
    clc
    adc.l SourceVisual_DebugD
    clc
    adc.l SourceVisual_DebugD
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
    jsr SourceVisual_ReadRow
    lda.l SourceVisual_RowScratch+32
    cmp #SOURCE_VISUAL_MAX_SHEET+1
    bcc SourceVisual_LoadResources__block_sheet_ok
    brl SourceVisual_LoadResources__large
SourceVisual_LoadResources__block_sheet_ok:
.a16
    sta.l SourceVisual_SheetBytes

    ; Read the source piece rows; their block identities are globally
    ; content-addressed and may share one of the 64 resident 16x32 slots.
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
    jsr SourceVisual_PrepareBlocks
    bcs SourceVisual_LoadResources__blocks_ready
    brl SourceVisual_LoadResources__block_pending
SourceVisual_LoadResources__blocks_ready:
    jsr SourceVisual_AllocatePalettes
    bcs SourceVisual_LoadResources__palettes_allocated
    brl SourceVisual_LoadResources__palette_admission
SourceVisual_LoadResources__palettes_allocated:
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+4,x
    bne SourceVisual_LoadResources__block_palette_done
    jsr SourceVisual_QueuePalettes
    bcs SourceVisual_LoadResources__block_palette_queued
    brl SourceVisual_LoadResources__block_palette_pending
SourceVisual_LoadResources__block_palette_queued:
.a16
    lda.l SourceVisual_Record
    tax
    lda #1
    sta.l SourceVisual_State+4,x
SourceVisual_LoadResources__block_palette_done:
    ; Palette DMA and tile DMA share the fail-closed publication fence. Never
    ; write OAM that selects a palette until its CGRAM row has retired.
    jsr SourceVisual_HasOwnedDma
    bcs SourceVisual_LoadResources__block_palette_pending
    jsr SourceVisual_MarkPaletteDmaRetired
    sec
    rts
SourceVisual_LoadResources__block_palette_pending:
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_LoadResources__block_pending:
    sep #$20
.a8
    lda #$27
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
.i16
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

; Resolve each 16x32 piece to a pinned, content-addressed 256-byte block.
; A source frame can reference blocks shared with other live actors; only
; unique blocks consume one of the 64 physical OBJ slots.
SourceVisual_PrepareBlocks:
    rep #$31
.a16
.i16
    ; ActorPieceMap row = actorSlot * 65.
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceVisual_ActorSlot
    sta.l SourceVisual_ActorMapBase
    ; Actor reference bit.
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_PrepareBlocks__mask:
.i16
    cpx #0
    beq SourceVisual_PrepareBlocks__mask_ready
    asl a
    dex
    bra SourceVisual_PrepareBlocks__mask
SourceVisual_PrepareBlocks__mask_ready:
    sep #$20
.a8
    sta.l SourceVisual_BlockActorMask
    rep #$31
.a16
.i16
SourceVisual_PrepareBlocks__needs_blocks:

    jsr SourceVisual_ResumePendingBlock
    bcs SourceVisual_PrepareBlocks__scan_start
    brl SourceVisual_PrepareBlocks__pending
SourceVisual_PrepareBlocks__scan_start:
.a16
    ; Camera/actor movement can expose new pieces without changing the pose.
    ; Refresh ownership before admission, including every already-resident
    ; visible block. Offscreen pieces cannot hold scarce OBJ slots hostage.
    jsr SourceVisual_PinVisibleBlocks
    lda #0
    sta.l SourceVisual_PieceIndex
SourceVisual_PrepareBlocks__piece:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcs SourceVisual_PrepareBlocks__ready
    jsr SourceVisual_ViewportPiece
    bcs SourceVisual_PrepareBlocks__visible_piece
    brl SourceVisual_PrepareBlocks__next_piece
SourceVisual_PrepareBlocks__visible_piece:
    lda.l SourceVisual_PieceIndex
    ; Read the globally assigned block ID at piece row +12.
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+12,x
    sta.l SourceVisual_BlockIndex
    jsr SourceVisual_FindBlock
    bcs SourceVisual_PrepareBlocks__found
    jsr SourceVisual_AllocateBlock
    bcs SourceVisual_PrepareBlocks__allocated
    brl SourceVisual_PrepareBlocks__admission
SourceVisual_PrepareBlocks__allocated:
    jsr SourceVisual_ReadBlockPayload
    bcs SourceVisual_PrepareBlocks__payload_ready
    brl SourceVisual_PrepareBlocks__oversized
SourceVisual_PrepareBlocks__payload_ready:
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_BlockCache+6,x ; immutable staging payload is ready
    rep #$31
.a16
.i16
    jsr SourceVisual_QueueBlockRows
    brl SourceVisual_PrepareBlocks__pending
SourceVisual_PrepareBlocks__found:
    ; Pin the resident/pending block to this actor before using its slot.
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    ora.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache+4,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceVisual_PrepareBlocks__map_piece
    ; The sole shared staging payload is still being uploaded. Keep the
    ; frame closed until the DMA fence observes completion.
    jsr SourceVisual_QueueBlockRows
    brl SourceVisual_PrepareBlocks__pending
SourceVisual_PrepareBlocks__map_piece:
    jsr SourceVisual_MapCurrentPiece
SourceVisual_PrepareBlocks__next_piece:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    bra SourceVisual_PrepareBlocks__piece
SourceVisual_PrepareBlocks__ready:
.a16
    lda.l SourceVisual_Record
    tax
    lda #2
    sta.l SourceVisual_State+6,x
    brl SourceVisual_PrepareBlocks__apply_all
SourceVisual_PrepareBlocks__apply_all:
.a16
    lda #0
    sta.l SourceVisual_PieceIndex
SourceVisual_PrepareBlocks__apply_loop:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcs SourceVisual_PrepareBlocks__success
    jsr SourceVisual_ViewportPiece
    bcc SourceVisual_PrepareBlocks__apply_next
    jsr SourceVisual_ApplyMappedPiece
SourceVisual_PrepareBlocks__apply_next:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    bra SourceVisual_PrepareBlocks__apply_loop
SourceVisual_PrepareBlocks__success:
    sec
    rts
SourceVisual_PrepareBlocks__pending:
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_PrepareBlocks__admission:
    sep #$20
.a8
    lda #$24
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_PrepareBlocks__oversized:
    sep #$20
.a8
    lda #$22
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts

; Called only after ResumePendingBlock observes the shared DMA fence. Clear
; this actor's ownership, retain resident content, then repin every visible
; block before a missing block may evict an unowned cache record. This also
; protects later pieces while an earlier visible piece uploads over fields.
SourceVisual_PinVisibleBlocks:
    sep #$20
    .a8
    lda.l SourceVisual_BlockActorMask
    eor #$FF
    sta.l SourceVisual_BlockOther2
    rep #$31
    .a16
    .i16
    ldx #0
SourceVisual_PinVisibleBlocks__clear:
    sep #$20
    .a8
    lda.l SourceVisual_BlockCache+4,x
    and.l SourceVisual_BlockOther2
    sta.l SourceVisual_BlockCache+4,x
    rep #$31
    .a16
    .i16
    txa
    clc
    adc #8
    tax
    cpx #SOURCE_VISUAL_TILE_BLOCKS*8
    bcc SourceVisual_PinVisibleBlocks__clear
    lda #0
    sta.l SourceVisual_PieceIndex
SourceVisual_PinVisibleBlocks__piece:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcs SourceVisual_PinVisibleBlocks__done
    jsr SourceVisual_ViewportPiece
    bcc SourceVisual_PinVisibleBlocks__next
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+12,x
    sta.l SourceVisual_BlockIndex
    jsr SourceVisual_FindBlock
    bcc SourceVisual_PinVisibleBlocks__next
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
    .a8
    lda.l SourceVisual_BlockCache+4,x
    ora.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache+4,x
    rep #$31
    .a16
    .i16
SourceVisual_PinVisibleBlocks__next:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    bra SourceVisual_PinVisibleBlocks__piece
SourceVisual_PinVisibleBlocks__done:
    rts

; A cache record is {blockId:u16, state:u16, owners:u8, progress:u8,
; payloadLoaded:u8, reserved:u8}. State 1 is loading, 2 is fully resident.
SourceVisual_FindBlock:
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockScan
SourceVisual_FindBlock__scan:
.a16
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcs SourceVisual_FindBlock__miss
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+2,x
    beq SourceVisual_FindBlock__next
    lda.l SourceVisual_BlockCache,x
    cmp.l SourceVisual_BlockIndex
    beq SourceVisual_FindBlock__hit
SourceVisual_FindBlock__next:
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    bra SourceVisual_FindBlock__scan
SourceVisual_FindBlock__hit:
    txa
    sta.l SourceVisual_BlockRecord
    lsr a
    lsr a
    lsr a
    sta.l SourceVisual_BlockSlot
    sec
    rts
SourceVisual_FindBlock__miss:
    clc
    rts

SourceVisual_AllocateBlock:
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockScan
SourceVisual_AllocateBlock__scan:
.a16
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcs SourceVisual_AllocateBlock__fail
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+2,x
    beq SourceVisual_AllocateBlock__claim
    cmp #1
    beq SourceVisual_AllocateBlock__next
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    bne SourceVisual_AllocateBlock__next8
    rep #$31
.a16
.i16
    bra SourceVisual_AllocateBlock__claim
SourceVisual_AllocateBlock__next8:
    rep #$31
.a16
.i16
SourceVisual_AllocateBlock__next:
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    bra SourceVisual_AllocateBlock__scan
SourceVisual_AllocateBlock__claim:
.a16
    txa
    sta.l SourceVisual_BlockRecord
    tax
    lda.l SourceVisual_BlockIndex
    sta.l SourceVisual_BlockCache,x
    lda #1
    sta.l SourceVisual_BlockCache+2,x
    sep #$20
.a8
    lda.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache+4,x
    lda #0
    sta.l SourceVisual_BlockCache+5,x
    sta.l SourceVisual_BlockCache+6,x
    rep #$31
.a16
.i16
    txa
    lsr a
    lsr a
    lsr a
    sta.l SourceVisual_BlockSlot
    sec
    rts
SourceVisual_AllocateBlock__fail:
    clc
    rts

; Finish or continue the sole tile-staging upload. Carry is clear while a
; block remains in flight and set when there is no pending block.
SourceVisual_ResumePendingBlock:
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockScan
SourceVisual_ResumePendingBlock__scan:
.a16
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcs SourceVisual_ResumePendingBlock__none
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    beq SourceVisual_ResumePendingBlock__found
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    bra SourceVisual_ResumePendingBlock__scan
SourceVisual_ResumePendingBlock__found:
    txa
    sta.l SourceVisual_BlockRecord
    lda.l SourceVisual_BlockScan
    sta.l SourceVisual_BlockSlot
    jsr SourceVisual_HasOwnedDma
    bcs SourceVisual_ResumePendingBlock__pending
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+5,x
    cmp #4
    beq SourceVisual_ResumePendingBlock__complete8
    rep #$31
.a16
.i16
    jsr SourceVisual_QueueBlockRows
    clc
    rts
SourceVisual_ResumePendingBlock__complete8:
    rep #$31
.a16
.i16
    lda #2
    sta.l SourceVisual_BlockCache+2,x
    sec
    rts
SourceVisual_ResumePendingBlock__pending:
    clc
    rts
SourceVisual_ResumePendingBlock__none:
    sec
    rts

SourceVisual_QueueBlockRows:
    rep #$31
.a16
.i16
    jsr SourceVisual_HasOwnedDma
    bcc SourceVisual_QueueBlockRows__staging_free
    brl SourceVisual_QueueBlockRows__pending
SourceVisual_QueueBlockRows__staging_free:
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+6,x
    bne SourceVisual_QueueBlockRows__payload_loaded8
    rep #$31
    .a16
.i16
    jsr SourceVisual_ReadBlockPayload
    bcs SourceVisual_QueueBlockRows__payload_read
    brl SourceVisual_QueueBlockRows__bad_payload
SourceVisual_QueueBlockRows__payload_read:
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_BlockCache+6,x
SourceVisual_QueueBlockRows__payload_loaded8:
    rep #$31
.a16
.i16
SourceVisual_QueueBlockRows__row:
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+5,x
    cmp #4
    bcc SourceVisual_QueueBlockRows__has_row
    brl SourceVisual_QueueBlockRows__queued
SourceVisual_QueueBlockRows__has_row:
    sta.l SourceVisual_BlockProgress
    rep #$31
.a16
.i16
    jsl Core_Dma_HasFreeSlot_Long
    bcs SourceVisual_QueueBlockRows__slot_available
    brl SourceVisual_QueueBlockRows__pending
SourceVisual_QueueBlockRows__slot_available:
.a16
    lda.l DmaQueue_BudgetTotal
    clc
    adc #64
    cmp #DMA_TRANSFER_MAX_BYTES
    bcs SourceVisual_QueueBlockRows__pending
    ; Source pointer is one 64-byte horizontal row of two adjacent tiles.
    lda.l SourceVisual_BlockProgress
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #SourceVisual_TileStaging
    sta.l DmaRequest_SourceAddrLow
    ; Destination = $8000 + physicalTile*32 + verticalRow*512.
    jsr SourceVisual_BlockSlotToTile
    lda.l SourceVisual_BlockTileBase
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_BlockDataBytes
    lda.l SourceVisual_BlockProgress
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceVisual_BlockDataBytes
    adc #SOURCE_VISUAL_VRAM_BASE
    sta.l DmaRequest_TargetAddr
    clc
    adc #64
    cmp #SOURCE_VISUAL_VRAM_END+1
    bcs SourceVisual_QueueBlockRows__pending
    lda #64
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
    jsl Core_Dma_Enqueue_Long
    bcc SourceVisual_QueueBlockRows__pending
    jsr SourceVisual_TrackRequest
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+5,x
    inc a
    sta.l SourceVisual_BlockCache+5,x
    rep #$31
.a16
.i16
    brl SourceVisual_QueueBlockRows__row
SourceVisual_QueueBlockRows__queued:
    clc
    rts
SourceVisual_QueueBlockRows__pending:
    clc
    rts
SourceVisual_QueueBlockRows__bad_payload:
    clc
    rts

; Return the legal 16x32 OBJ tile origin for cache slot 0..63. Each page has
; eight block columns and four block rows in SNES OBJ name-table ordering.
SourceVisual_BlockSlotToTile:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockSlot
    cmp #32
    bcc SourceVisual_BlockSlotToTile__page0
    sec
    sbc #32
    sta.l SourceVisual_BlockTemp
    lda #256
    bra SourceVisual_BlockSlotToTile__page_ready
SourceVisual_BlockSlotToTile__page0:
.a16
    lda.l SourceVisual_BlockSlot
    sta.l SourceVisual_BlockTemp
    lda #0
SourceVisual_BlockSlotToTile__page_ready:
.a16
    sta.l SourceVisual_BlockTileBase
    lda.l SourceVisual_BlockTemp
    and #7
    asl a
    clc
    adc.l SourceVisual_BlockTileBase
    sta.l SourceVisual_BlockTileBase
    lda.l SourceVisual_BlockTemp
    lsr a
    lsr a
    lsr a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceVisual_BlockTileBase
    sta.l SourceVisual_BlockTileBase
    rts

SourceVisual_MapCurrentPiece:
    ; Save the selected cache slot into actor map[PieceIndex], then patch the
    ; current piece's tile origin for this packet.
    lda.l SourceVisual_PieceIndex
    clc
    adc.l SourceVisual_ActorMapBase
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockSlot
    sta.l SourceVisual_ActorPieceMap,x
    rep #$31
.a16
.i16
    jsr SourceVisual_BlockSlotToTile
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+14,x
    and #$8000
    ora.l SourceVisual_BlockTileBase
    sta.l SourceVisual_PieceTable+14,x
    rts

SourceVisual_ApplyMappedPiece:
    lda.l SourceVisual_PieceIndex
    clc
    adc.l SourceVisual_ActorMapBase
    tax
    sep #$20
.a8
    lda.l SourceVisual_ActorPieceMap,x
    rep #$31
.a16
.i16
    and #$00FF
    sta.l SourceVisual_BlockSlot
    jsr SourceVisual_BlockSlotToTile
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+14,x
    and #$8000
    ora.l SourceVisual_BlockTileBase
    sta.l SourceVisual_PieceTable+14,x
    rts

; Resolve the block table row and copy only its immutable 256-byte payload to
; staging. The catalog may contain 1024-byte blocks, which remain explicitly
; rejected until the separate oversized-frame policy is addressed.
SourceVisual_ReadBlockPayload:
    rep #$31
.a16
.i16
    lda #((SOURCE_VISUAL_BLOCK_OFFSET) & $FFFF)
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda #((SOURCE_VISUAL_BLOCK_OFFSET >> 16) & $FF)
    sta.l SourceVisual_Offset+2
    lda #((SOURCE_VISUAL_BLOCK_OFFSET >> 24) & $FF)
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    ldy #42
SourceVisual_ReadBlockPayload__row_offset:
    lda.l SourceVisual_Offset
    clc
    adc.l SourceVisual_BlockIndex
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda.l SourceVisual_Offset+2
    adc #0
    sta.l SourceVisual_Offset+2
    lda.l SourceVisual_Offset+3
    adc #0
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    dey
    bne SourceVisual_ReadBlockPayload__row_offset
    jsr SourceVisual_AddCatalogBase
    jsr SourceVisual_ReadRow
    lda.l SourceVisual_RowScratch+32
    cmp #SOURCE_VISUAL_TILE_BLOCK_BYTES
    beq SourceVisual_ReadBlockPayload__size_ok
    clc
    rts
SourceVisual_ReadBlockPayload__size_ok:
    lda.l SourceVisual_RowScratch+34
    sta.l SourceVisual_Offset
    lda.l SourceVisual_RowScratch+36
    sta.l SourceVisual_Offset+2
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    jsr SourceVisual_AddCatalogBase
    jsr SourceVisual_Seek
    ldx #0
SourceVisual_ReadBlockPayload__read:
    sep #$20
.a8
    lda $2001
    sta.l SourceVisual_TileStaging,x
    rep #$31
.a16
.i16
    inx
    cpx #SOURCE_VISUAL_TILE_BLOCK_BYTES
    bcc SourceVisual_ReadBlockPayload__read
    sec
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
.a16
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
.a16
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
    clc
    adc.l SourceVisual_ChunkBytes
    cmp #SOURCE_VISUAL_VRAM_END+1
    bcs SourceVisual_QueueSheet__fail
    rep #$31
.a16
.i16
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
.a16
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
    rep #$31
.a16
.i16
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
    brl SourceVisual_QueuePalettes__piece
SourceVisual_QueuePalettes__piece:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceVisual_QueuePalettes__have_piece
    brl SourceVisual_QueuePalettes__done
SourceVisual_QueuePalettes__have_piece:
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    txa
    sta.l SourceVisual_PieceOffset
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_PaletteLocalSlot
    lda.l SourceVisual_PieceTable+8,x
    sta.l SourceVisual_PaletteLocalSlot
rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteLocalSlot
    cmp.l SourceVisual_AllocPaletteCount
    bcc SourceVisual_QueuePalettes__local_ok
    brl SourceVisual_QueuePalettes__fail
SourceVisual_QueuePalettes__local_ok:
.a16
    lda.l SourceVisual_Record
    clc
    adc #16
    clc
    adc.l SourceVisual_PaletteLocalSlot
    tax
    sep #$20
.a8
    lda.l SourceVisual_State,x
    bne SourceVisual_QueuePalettes__mapped_slot
    brl SourceVisual_QueuePalettes__fail
SourceVisual_QueuePalettes__mapped_slot:
.a8
    dec a
    sta.l SourceVisual_PaletteSlot
    cmp #8
    bcc SourceVisual_QueuePalettes__palette_ok
    brl SourceVisual_QueuePalettes__fail
SourceVisual_QueuePalettes__palette_ok:
    rep #$31
.a16
.i16
    ; One transfer per physical slot, even when local selectors alias.
    lda.l SourceVisual_PaletteSlot
    and #$00FF
    tax
    lda #1
SourceVisual_QueuePalettes__mask_shift:
.i16
    cpx #0
    beq SourceVisual_QueuePalettes__mask_ready
    asl a
    dex
    bra SourceVisual_QueuePalettes__mask_shift
SourceVisual_QueuePalettes__mask_ready:
    sta.l SourceVisual_PaletteTransferBit
    lda.l SourceVisual_PaletteMask
    and.l SourceVisual_PaletteTransferBit
    beq SourceVisual_QueuePalettes__mask_new
    brl SourceVisual_QueuePalettes__next
SourceVisual_QueuePalettes__mask_new:
    lda.l SourceVisual_PaletteTransferBit
    ora.l SourceVisual_PaletteMask
    sta.l SourceVisual_PaletteMask
SourceVisual_QueuePalettes__palette_lookup:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceOffset
    tax
    lda.l SourceVisual_PieceTable+10,x
    sta.l SourceVisual_PaletteGlobalIndex
    sta.l SourceVisual_DebugD
    lda.l SourceVisual_PaletteSlot
    and #$00FF
    asl a
    asl a
    asl a
    sta.l SourceVisual_PaletteCacheOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+3,x
    beq SourceVisual_QueuePalettes__palette_needs_dma
    rep #$31
.a16
.i16
    brl SourceVisual_QueuePalettes__next
SourceVisual_QueuePalettes__palette_needs_dma:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteGlobalIndex
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
    brl SourceVisual_QueuePalettes__next
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
.a16
    lda #7
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
.i16
    ldx #0
SourceVisual_ReadPalettePayload__copy0_loop:
.i16
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+0,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy0_loop
    brl SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy1:
.i16
    ldx #0
SourceVisual_ReadPalettePayload__copy1_loop:
.i16
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+32,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy1_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy2:
.i16
    ldx #0
SourceVisual_ReadPalettePayload__copy2_loop:
.i16
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+64,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy2_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy3:
.i16
    ldx #0
SourceVisual_ReadPalettePayload__copy3_loop:
.i16
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+96,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy3_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy4:
.i16
    ldx #0
SourceVisual_ReadPalettePayload__copy4_loop:
.i16
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+128,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy4_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy5:
.i16
    ldx #0
SourceVisual_ReadPalettePayload__copy5_loop:
.i16
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+160,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy5_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy6:
.i16
    ldx #0
SourceVisual_ReadPalettePayload__copy6_loop:
.i16
    lda.l SourceVisual_PaletteTemp,x
    sta.l SourceVisual_PaletteStaging+192,x
    inx
    inx
    cpx #32
    bcc SourceVisual_ReadPalettePayload__copy6_loop
    bra SourceVisual_ReadPalettePayload__queue
SourceVisual_ReadPalettePayload__copy7:
.i16
    ldx #0
SourceVisual_ReadPalettePayload__copy7_loop:
.i16
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
.a16
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
    lda #((SourceVisual_PaletteStaging >> 16) & $FF)
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_CGRAM
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsl Core_Dma_Enqueue_Long
    jsr SourceVisual_TrackRequest
    lda.l SourceVisual_PaletteCacheOffset
    tax
    sep #$20
.a8
    lda #2
    sta.l SourceVisual_PaletteCache+3,x
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
    ; Both staging buffers live in bank $7E. Fence the relocated palette
    ; arena as well as tile rows before reusing their immutable payloads.
    cmp #(SourceVisual_PaletteStaging & $FFFF)
    bcc SourceVisual_HasOwnedDma__tile_bank
    cmp #((SourceVisual_PaletteStaging & $FFFF) + 256)
    bcc SourceVisual_HasOwnedDma__owned
SourceVisual_HasOwnedDma__tile_bank:
    rep #$31
.a16
.i16
    lda.l DmaQueue+5,x
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
.a16
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
    sta.l OamSetSprite_X
    sta.l SourceVisual_EmitBaseX
    lda #0
    sta.l SourceVisual_EmitBoundsMode
    ; Source-sized actors bypass Character_RenderFrame. Apply pit foot depth
    ; here while retaining authored per-piece offsets from the actor's foot.
    jsl StageBoundsHost_Normal
    bcc SourceVisual_Emit__ground_y
    jsl StageBounds_Row
    lda.l StageBounds_State,x
    beq SourceVisual_Emit__ground_y
    cmp #2
    bne SourceVisual_Emit__not_hidden
    brl SourceVisual_Emit__hidden
SourceVisual_Emit__not_hidden:
.a16
    lda.l StageBounds_DrawY,x
    cmp #240
    bcc SourceVisual_Emit__height_visible
    brl SourceVisual_Emit__hidden
SourceVisual_Emit__height_visible:
.a16
    sta.l SourceVisual_EmitBaseY
    lda #1
    sta.l SourceVisual_EmitBoundsMode
    bra SourceVisual_Emit__y_ready
SourceVisual_Emit__ground_y:
    lda CHAR_POS_Y
    sta.l SourceVisual_EmitBaseY
SourceVisual_Emit__y_ready:
.a16
    ; Count only pieces intersecting the real viewport before reserving the
    ; whole visible packet. World coordinates must not wrap into screen X:
    ; old offscreen props otherwise consume OAM and can hide the player.
    lda #0
    sta.l SourceVisual_VisiblePieces
    sta.l SourceVisual_PieceIndex
SourceVisual_Emit__count_visible:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcs SourceVisual_Emit__reserve_visible
    jsr SourceVisual_ViewportNormalPiece
    bcc SourceVisual_Emit__count_mirror
    lda.l SourceVisual_VisiblePieces
    inc a
    sta.l SourceVisual_VisiblePieces
SourceVisual_Emit__count_mirror:
    jsr SourceVisual_ViewportMirrorPiece
    bcc SourceVisual_Emit__count_next
    lda.l SourceVisual_VisiblePieces
    inc a
    sta.l SourceVisual_VisiblePieces
SourceVisual_Emit__count_next:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    bra SourceVisual_Emit__count_visible
SourceVisual_Emit__reserve_visible:
.a16
    lda.l SourceVisual_VisiblePieces
    asl a
    asl a
    clc
    adc.l $7E53A0
    cmp #513
    bcc SourceVisual_Emit__oam_capacity_ok
    sep #$20
.a8
    lda #$2B
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
    sta.l SourceVisual_PieceIndex
    bra SourceVisual_Emit__piece
SourceVisual_Emit__hidden:
    sec
    rts
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
    jsr SourceVisual_ViewportPiece
    bcs SourceVisual_Emit__visible_piece
    brl SourceVisual_Emit__next_piece
SourceVisual_Emit__visible_piece:
.a16
    lda.l SourceVisual_EmitPieceX
    sta.l OamSetSprite_X
    lda.l SourceVisual_EmitPieceY
    sta.l OamSetSprite_Y
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    sta.l SourceVisual_PieceOffset
    lda.l SourceVisual_PieceTable+14,x
    and #$01FF
    clc
    adc.l SourceVisual_BaseTile
    sep #$20
.a8
    sta.l OamSetSprite_Tile
    lda.l SourceVisual_PieceTable+8,x
    sta.l SourceVisual_PaletteLocalSlot
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    clc
    adc #16
    clc
    adc.l SourceVisual_PaletteLocalSlot
    tax
    sep #$20
.a8
    lda.l SourceVisual_State,x
    beq SourceVisual_Emit__palette_bad_near
    dec a
    sta.l SourceVisual_DebugEmitPiece+60
    cmp #8
    bcc SourceVisual_Emit__palette_ok
SourceVisual_Emit__palette_bad_near:
    brl SourceVisual_Emit__palette_fail
SourceVisual_Emit__palette_ok:
    rep #$20
.a16
    lda.l SourceVisual_PieceOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_DebugEmitPiece+60
    asl a
    ora #$30
    sta.l OamSetSprite_Attr
    ; OBJ names 0..255 address one 8-KiB name table. Include the atlas
    ; origin, not only its residency base, when selecting the second table.
    rep #$20
.a16
    lda.l SourceVisual_PieceTable+14,x
    and #$01FF
    clc
    adc.l SourceVisual_BaseTile
    and #$0100
    beq SourceVisual_Emit__name_table0
    sep #$20
.a8
    lda.l OamSetSprite_Attr
    ora #$01
    sta.l OamSetSprite_Attr
SourceVisual_Emit__name_table0:
    sep #$20
.a8
    lda CHAR_FACING_LEFT
    beq SourceVisual_Emit__right
    lda.l OamSetSprite_Attr
    ora #$40
    sta.l OamSetSprite_Attr
    bra SourceVisual_Emit__write
SourceVisual_Emit__right:
SourceVisual_Emit__write:
.a8
    lda.l SourceVisual_EmitBoundsMode
    beq SourceVisual_Emit__priority_ready
    lda.l OamSetSprite_Attr
    and #$CF                     ; falling source pieces pass behind panels
    sta.l OamSetSprite_Attr
SourceVisual_Emit__priority_ready:
.a8
    lda #37
    sta.l SourceVisual_DebugQueueStage
    lda #1
    sta.l SourceVisual_DebugEmitPiece+48
    rep #$20
.a16
    lda.l SourceVisual_PieceTable+14,x
    and #$8000
    beq SourceVisual_Emit__small_obj
    sep #$20
.a8
    lda #2
    bra SourceVisual_Emit__obj_size_ready
SourceVisual_Emit__small_obj:
    sep #$20
.a8
    lda #0
SourceVisual_Emit__obj_size_ready:
    sta.l OamSetSprite_Hi
    rep #$20
.a16
    lda.l SourceVisual_EmitPieceX
    and #$0100
    beq SourceVisual_Emit__x_high_ready
    sep #$20
.a8
    lda.l OamSetSprite_Hi
    ora #1
    sta.l OamSetSprite_Hi
SourceVisual_Emit__x_high_ready:
    ; Negative screen X takes the A8 high-bit path above. Restore the
    ; viewport helper ABI on both paths before reading 16-bit coordinates.
    rep #$31
.a16
.i16
    jsr SourceVisual_ViewportNormalPiece
    bcc SourceVisual_Emit__mirror
    jsr SourceVisual_WriteCurrentPiece
SourceVisual_Emit__mirror:
    jsr SourceVisual_ViewportMirrorPiece
    bcc SourceVisual_Emit__next_piece
SourceVisual_WriteMirror:
    ; Source mirror depth is behind the floor/frontpanel. No vflip, resize,
    ; extra tile allocation, changed source pose or extra actor is involved.
    sep #$20
    .a8
    lda.l OamSetSprite_Attr
    and #$CF
    ora #$20                    ; above clean BG1, behind foreground BG2
    sta.l OamSetSprite_Attr
    rep #$31
    .a16
    .i16
SourceVisual_WriteMirror__emit:
    jsr SourceVisual_WriteCurrentPiece
SourceVisual_Emit__next_piece:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    jmp SourceVisual_Emit__piece
SourceVisual_Emit__done:
.a16
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
.i16
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
.i16
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

SourceVisual_WriteCurrentPiece:
    ; OAM request coordinates are bytes; A16 Y would clear adjacent Tile.
    sep #$20
    .a8
    lda.l SourceVisual_EmitPieceX
    sta.l OamSetSprite_X
    lda.l SourceVisual_EmitPieceY
    sta.l OamSetSprite_Y
    sep #$20
    .a8
    lda.l OamSetSprite_Attr
    jsl StageFp_BG2OamAttr
    sta.l OamSetSprite_Attr
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
    rts

; A16/I16. Resolve one authored 16x32 or 32x64 piece without byte wrapping.
; C=true iff at least one of its pixels can intersect the 256x224 viewport.
; Count and emission use this same predicate, keeping OAM admission atomic.
SourceVisual_ViewportPiece:
    jsr SourceVisual_ViewportNormalPiece
    bcs SourceVisual_ViewportPiece__union_visible
    jsr SourceVisual_ViewportMirrorPiece
SourceVisual_ViewportPiece__union_visible:
    rts

SourceVisual_ViewportNormalPiece:
.a16
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+14,x
    and #$8000
    beq SourceVisual_ViewportPiece__small
    lda #32
    sta.l SourceVisual_EmitPieceWidth
    lda #64
    bra SourceVisual_ViewportPiece__height
SourceVisual_ViewportPiece__small:
.a16
    lda #16
    sta.l SourceVisual_EmitPieceWidth
    lda #32
SourceVisual_ViewportPiece__height:
.a16
    sta.l SourceVisual_EmitPieceHeight
    lda CHAR_FACING_LEFT
    and #$00FF
    beq SourceVisual_ViewportPiece__right
    lda.l SourceVisual_PieceTable+4,x
    clc
    adc.l SourceVisual_EmitBaseX
    sta.l SourceVisual_EmitPieceX
    lda.l SourceVisual_PieceTable+6,x
    bra SourceVisual_ViewportPiece__y
SourceVisual_ViewportPiece__right:
    lda.l SourceVisual_PieceTable,x
    clc
    adc.l SourceVisual_EmitBaseX
    sta.l SourceVisual_EmitPieceX
    lda.l SourceVisual_PieceTable+2,x
SourceVisual_ViewportPiece__y:
.a16
    clc
    adc.l SourceVisual_EmitBaseY
    sta.l SourceVisual_EmitPieceY
    lda.l SourceVisual_EmitPieceX
    bmi SourceVisual_ViewportPiece__x_end
    cmp #256
    bcs SourceVisual_ViewportPiece__outside
SourceVisual_ViewportPiece__x_end:
.a16
    clc
    adc.l SourceVisual_EmitPieceWidth
    bmi SourceVisual_ViewportPiece__outside
    beq SourceVisual_ViewportPiece__outside
    lda.l SourceVisual_EmitPieceY
    bmi SourceVisual_ViewportPiece__y_end
    cmp #224
    bcs SourceVisual_ViewportPiece__outside
SourceVisual_ViewportPiece__y_end:
    clc
    adc.l SourceVisual_EmitPieceHeight
    bmi SourceVisual_ViewportPiece__outside
    beq SourceVisual_ViewportPiece__outside
    sec
    rts
SourceVisual_ViewportPiece__outside:
    clc
    rts

SourceVisual_ViewportMirrorPiece:
.a16
    lda.l Stage_Mirror
    and #$00FF
    bne SourceVisual_ViewportMirrorPiece__active
    clc
    rts
SourceVisual_ViewportMirrorPiece__active:
.a16
    jsr SourceVisual_ViewportNormalPiece
    lda.l SourceVisual_EmitPieceY
    sec
    sbc.l SourceVisual_EmitBaseY
    clc
    adc #248
    sec
    sbc CHAR_POS_Y
    sta.l SourceVisual_EmitPieceY
    lda.l SourceVisual_EmitPieceX
    bmi SourceVisual_ViewportMirrorPiece__x_end
    cmp #256
    bcs SourceVisual_ViewportMirrorPiece__outside
SourceVisual_ViewportMirrorPiece__x_end:
.a16
    clc
    adc.l SourceVisual_EmitPieceWidth
    bmi SourceVisual_ViewportMirrorPiece__outside
    beq SourceVisual_ViewportMirrorPiece__outside
    lda.l SourceVisual_EmitPieceY
    bmi SourceVisual_ViewportMirrorPiece__y_end
    cmp #224
    bcs SourceVisual_ViewportMirrorPiece__outside
SourceVisual_ViewportMirrorPiece__y_end:
    clc
    adc.l SourceVisual_EmitPieceHeight
    bmi SourceVisual_ViewportMirrorPiece__outside
    beq SourceVisual_ViewportMirrorPiece__outside
    sec
    rts
SourceVisual_ViewportMirrorPiece__outside:
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
