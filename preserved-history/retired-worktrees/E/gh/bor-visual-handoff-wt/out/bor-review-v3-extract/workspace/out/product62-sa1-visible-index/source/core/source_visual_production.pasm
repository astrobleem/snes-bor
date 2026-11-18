; Production SOURCE_SIZED visual consumer.
;
; This module is deliberately presentation-only.  It reads the compiler-owned
; SVIS1 catalog from the MSU data stream, while the actor's accepted gameplay
; context remains the authoritative source of role/frame/map/position.
; Source-policy actors are fail-closed: no legacy 32x48 fallback is allowed.

; The source publisher must not overlap the legacy animation/MSU staging
; records at $7E2000-$7E23FF. The verified gap after HUD staging is
; $7E5B00-$7E5FFF. The 1 KiB DMA staging buffer occupies $7E5B00-$7E5EFF;
; candidate-admission scratch occupies $7E5F00-$7E5F91, disjoint from it.
SourceVisual_TileStaging    = $7E5B00 ; 1 KiB, disjoint from legacy staging
SourceVisual_PieceTable     = $7E4000 ; up to 65 * 16-byte piece rows
; The 65-row table ends at $4410.  Keep loader scratch in the checked free
; publisher arena rather than truncating Normal's 65-piece K9999 upper frame.
; PieceTable itself is one global row buffer, so its validity is tagged with
; the actor and catalog entry that last completed a full read. $4410-$449F is
; the verified 144-byte gap before the next publisher scratch at $44A0.
SourceVisual_PieceTableValid = $7E4410
SourceVisual_PieceTableOwner = $7E4411
SourceVisual_PieceTableEntry = $7E4412 ; u16
; RowScratch is shared by every actor and every 42-byte table-row reader.
; These bytes tag the only case where a block payload row may be reused.
; The free $4414-$449F gap is bounded by the debug table at $4500.
SourceVisual_RowScratchBlockIndex = $7E4414 ; u16, catalog block ID
SourceVisual_RowScratchBlockValid = $7E4416 ; set only after a full block row
SourceVisual_EntryScratch   = $7E4800 ; 24-byte SVIS entry
SourceVisual_RowScratch     = $7E4840 ; 64-byte table-row scratch
SourceVisual_PaletteTemp    = $7E4880 ; 32-byte palette read scratch
SourceVisual_PaletteStaging = $7E4900 ; 8 * 32-byte OBJ palettes
SourceVisual_Offset         = $7E4A00 ; 32-bit MSU seek scratch
SourceVisual_Key            = $7E4A04 ; roster, role, frame, map
SourceVisual_Error          = $7E4A08 ; diagnostic byte
SourceVisual_State           = $7E4A80 ; 6 * 32-byte published actor visual leases
; Palette selection and resource-cache fields share bytes +16..+23. Keep the
; entry-row-valid marker in its own byte so a palette value cannot masquerade
; as a cached entry row on a later loader pass.
SOURCE_VISUAL_STATE_SHEET_ROW_VALID = 24
SOURCE_VISUAL_STATE_PIECE_ROWS_VALID = 25
SOURCE_VISUAL_STATE_ENTRY_ROW_VALID = 26
; One 32-byte sidecar per supported actor slot: 6 * 32 = 192 bytes total.
; It starts after the last BOR-owned byte at $7E53D5 and ends at $7E5497,
; before Spawn_Index at $7E5500. This is one table, not 192 bytes per actor.
SourceVisual_CandidateState   = $7E53D8
; Complete source geometry cache. Authored right-facing X/Y, tile, canonical
; attribute, and size/mirror flags use seven bytes per piece. Left-facing X/Y
; are a separate signed-word sidecar (four bytes per piece), copied with the
; packet before its published valid flag is set. Six published rows are fixed
; at 6*65*7=2,730 bytes plus 6*65*4=1,560 sidecar bytes. One global 65-piece
; candidate row is admitted at a time; other actors keep rendering complete
; published rows until this bounded lane is free.
; Verified free WRAM: $7EEAB7-$7EEFFF (1,353 bytes), $7F8C00-$7F8FFF
; (1,024 bytes), and $7F9120-$7F9FFF (3,808 bytes). Published rows occupy
; 2,730 bytes in the last range; one candidate row and metadata occupy 455
; bytes in the first. Candidate left geometry occupies 260 bytes after its
; owner byte. Published left geometry is split into 780-byte groups for slots
; 0..2 and 3..5. The first group starts after OAM fence scratch at $7F9CF0;
; the second occupies $7F8C00-$7F8F0B. Published metadata, current-field
; flags, queue sequence tags, and fence state remain disjoint.
SourceVisual_CandidatePacketData = $7EEAB7 ; 65 * 7 = 455 bytes
SourceVisual_CandidatePacketMeta = $7EEC7E ; 16-byte candidate descriptor
SourceVisual_PacketCandidateOwner = $7EEC8E ; $FF free, else actor slot 0..5
SourceVisual_CandidateLeftGeometry = $7EEC8F ; 65 * (signed X,Y words) = 260 bytes
SourceVisual_PacketData       = $7F9120 ; 6 * 65 * 7 = 2,730 bytes
SourceVisual_PacketMeta       = $7F9BCA ; 6 * 16 = 96 bytes, published rows
SourceVisual_FrameMeta        = $7F9C2A ; 6 * 16 = 96 bytes, this render pass
SourceVisual_PublishedLeftGeometry012 = $7F9CF0 ; slots 0..2, 3 * 65 * 4
SourceVisual_PublishedLeftGeometry345 = $7F8C00 ; slots 3..5, 3 * 65 * 4
SOURCE_VISUAL_PACKET_META_STRIDE = 16
SOURCE_VISUAL_PACKET_META_COUNT = 0 ; authored-piece count
SOURCE_VISUAL_PACKET_META_WIDTH = 2 ; source frame width
SOURCE_VISUAL_PACKET_META_ENTRY = 4 ; catalog entry index
SOURCE_VISUAL_PACKET_META_VALID = 6 ; set last, after complete row copy
SOURCE_VISUAL_PACKET_META_OWNER = 7 ; candidate actor slot
SOURCE_VISUAL_PACKET_META_FENCE = 8 ; candidate OAM sequence, u32
SOURCE_VISUAL_PACKET_META_EPOCH = 12 ; non-aliasing OAM token epoch, u32
; FrameMeta bytes 0..3 snapshot the live key immediately after FindEntry.
; Offset 8 is otherwise unused in FrameMeta (PacketMeta is a separate array).
SOURCE_VISUAL_FRAME_ACTION_ROSTER = 0
SOURCE_VISUAL_FRAME_ACTION_ROLE = 1
SOURCE_VISUAL_FRAME_ACTION_FRAME = 2
SOURCE_VISUAL_FRAME_ACTION_MAP = 3
SOURCE_VISUAL_FRAME_ACTION_VALID = 8
SOURCE_VISUAL_ACTION_NONE = 0
SOURCE_VISUAL_ACTION_LIVE = 1
SOURCE_VISUAL_ACTION_STALE_FENCE = 2
SOURCE_VISUAL_PACKET_ROW_BYTES = 7
SOURCE_VISUAL_PACKET_ACTOR_BYTES = SOURCE_VISUAL_MAX_PIECES * SOURCE_VISUAL_PACKET_ROW_BYTES
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
SourceVisual_PresentationField = $7E4B68 ; retained diagnostic NMI field
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
; (0=reserved, 1=ready, 2=DMA pending), published owners [4], candidate owners [5].
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
SourceVisual_CandidateBase    = $7E4BD2 ; sidecar offset = actorSlot * 32
SourceVisual_OwnerChannel     = $7E4BD4 ; 0=published, 1=candidate
SourceVisual_UseCandidate     = $7E4BD5 ; selected lease for this compositor pass
SourceVisual_OwnerOffset      = $7E4BD6 ; .dw block/palette owner byte offset
SourceVisual_PreflightCount   = $7E4BD8 ; bounded resource admission count
SourceVisual_PreflightScan    = $7E4BDA
SourceVisual_PreflightNeed    = $7E4BDC
SourceVisual_PreflightFree    = $7E4BDE
SourceVisual_PreflightId      = $7E4BE0
SourceVisual_PreflightIds     = $7E5F00 ; 65 u16 IDs, outside the DMA staging window
SourceVisual_PreflightPaletteIds = $7E5F82 ; 8 u16 palette identities
SourceVisual_CandidateAction  = $7E4BB2 ; restore dispatch: 0=old, 1=capacity, 2=terminal
; Six 3-byte semantic identities (roster, role, map) plus one valid byte per
; actor. $7E4BB4-$7E4BCB is the symbol-map-verified gap before PacketCopyCount
; at $7E4BD0. These identities are derived from the immutable candidate key,
; not the live FrameMeta request. Frame is intentionally excluded; facing is
; sampled by Emit from CHAR_FACING_LEFT and uses the packet's stored geometry.
SourceVisual_CandidateActionIdentity = $7E4BB4 ; 6 * (roster, role, map)
SourceVisual_CandidateActionValid = $7E4BC6 ; .db x6
SourceVisual_CurrentActionScratch = $7E4BCC ; 3 bytes copied from live FrameMeta
SourceVisual_OamFenceSubmitted  = Oam_VisualFenceSubmitted
SourceVisual_OamFenceSubmittedEpoch = Oam_VisualFenceSubmittedEpoch
SourceVisual_OamFenceCompleted  = Oam_VisualFenceCompleted
SourceVisual_OamFenceCompletedValid = Oam_VisualFenceCompletedValid
SourceVisual_OamFenceCompletedEpoch = Oam_VisualFenceCompletedEpoch
SourceVisual_OamFenceCompletionVersion = Oam_VisualFenceCompletionVersion
SourceVisual_PacketCandidateLaneOwner = SourceVisual_PacketCandidateOwner
SourceVisual_CommitMask         = Oam_VisualCommitMask
SourceVisual_PacketMetaOffset = $7E4BE2
SourceVisual_PacketStart      = $7E4BE4
SourceVisual_PacketCount      = $7E4BE6
SourceVisual_PacketTotal      = $7E4BE8
SourceVisual_PacketDataIndex  = $7E4BEA
SourceVisual_PacketOamIndex   = $7E4BEC
SourceVisual_PacketAnchorX    = $7E4BEE
SourceVisual_PacketDrawY      = $7E4BF0
SourceVisual_PacketActorY     = $7E4BF2
SourceVisual_PacketOldX       = $7E4BF4
SourceVisual_PacketNewX       = $7E4BF6
SourceVisual_PacketDeltaY     = $7E4BF8
SourceVisual_PacketFacing     = $7E4BFA
SourceVisual_PacketSourceRow  = $7E4BFC
SourceVisual_OamRetireMask    = $7E4BFE
; One actor may complete at most one shared staging block before yielding the
; rest of its render call. This gives later actor contexts a turn at the same
; DMA boundary instead of letting an earlier actor immediately admit another
; block and monopolize the sole staging buffer.
SourceVisual_BlockCompletedThisCall = $7E4BFF
SourceVisual_PacketCopyCount  = $7E4BD0
SourceVisual_EmitOamStart     = $7E44B4
SourceVisual_EmitActorY       = $7E44B6
SourceVisual_EmitFrameWidth   = $7E44B8
SourceVisual_PacketOldIdentity = $7E44BA
; Left-facing geometry-cache index/values and per-slot actor-base calculation.
SourceVisual_PacketLeftActorLocal = $7EED94 ; slot within its 0..2 sidecar group
SourceVisual_PacketLeftGroup  = $7EED96 ; 0=slots 0..2, 1=slots 3..5
SourceVisual_PacketLeftBaseOffset = $7EED98 ; actor slot * 260 within group
SourceVisual_PacketLeftPieceOffset = $7EED9A ; piece index * 4
SourceVisual_PacketLeftX      = $7EED9C ; signed 16-bit cached left X
SourceVisual_PacketLeftY      = $7EED9E ; signed 16-bit cached left Y
SourceVisual_PacketLeftCursor = $7EEDA0 ; candidate-to-published copy cursor
; One durable absolute MSU payload offset per 8-byte block-cache record. This
; preserves a completed 42-byte row's useful result when shared RowScratch is
; reused by another actor between reader turns. Cache state+6=2 is the valid
; bit; allocation resets it before this sidecar can be consumed. 64 * 4 bytes
; occupy $7EEDA2-$7EEEA1, within the verified free arena ending at $7EEFFF.
SourceVisual_BlockPayloadOffsets = $7EEDA2
; Candidate asset identity is separate from the live request and loader scratch.
; Six 4-byte keys occupy $7EEEA2-$7EEEB9, immediately after the 64-entry
; BlockPayloadOffsets sidecar ($7EEDA2-$7EEEA1), within the verified free arena.
SourceVisual_CandidateKey = $7EEEA2 ; six immutable [roster, role, frame, map] keys
; The one-byte MSU/catalog binding latch and its owner use the remaining
; checked bytes after CandidateKey ($7EEEA2-$7EEEB9).
SourceVisual_CatalogBindState = $7EEEBA ; 0=unchecked, 1=read pending, 2=valid, $FF=bad
SourceVisual_CatalogBindOwner = $7EEEBB ; actor that owns the one-time SVIX read
SourceVisual_PacketOldValid   = $7E44BB
SourceVisual_PacketNewIdentity = $7E44BC
SourceVisual_PacketNewValid   = $7E44BD
SourceVisual_PacketCopyByte   = $7E44BE
SourceVisual_PacketSpriteX    = $7E44C0
SourceVisual_PacketSpriteY    = $7E44C2
SourceVisual_PacketSpriteHigh = $7E44C4
SourceVisual_PacketDirectionChanged = $7E44C6
SourceVisual_PacketSpriteAttr = $7E44C7
SourceVisual_PacketOldWidth   = $7E44C8
SourceVisual_PacketOldDrawY   = $7E44CA
SourceVisual_PacketOldActorY  = $7E44CC
SourceVisual_PacketOldFacing  = $7E44CE
SourceVisual_PacketSpriteRelX = $7E44D0
; One bounded MSU-1 reader owns the shared seek/data cursor. The async state
; uses the verified $7E5498-$7E54FF gap after the six 32-byte candidate rows.
; State: 0=idle, 1=seek pending, 2=chunk boundary, 3=abandoned seek drain.
SourceVisual_LoaderOwner       = $7E5498 ; $FF when no candidate owns scratch
SourceVisual_ReadState         = $7E5499
SourceVisual_ReadRequestKind   = $7E549A ; 1 entry, 2 row, 3 pieces, 4 tile, 5 palette, 6 binding
SourceVisual_ReadKind          = $7E549B
SourceVisual_ReadOwner         = $7E549C
SourceVisual_ReadOffset        = $7E549D ; u32 descriptor
SourceVisual_ReadLength        = $7E54A1 ; u16 descriptor
SourceVisual_ReadCursor        = $7E54A3 ; u16 bytes already copied
SourceVisual_ReadSeek          = $7E54A5 ; u32 current seek = offset + cursor
; Keep these 16-bit words disjoint: ReadChunk is charged to WorkRemaining,
; while ReadRemaining drives the local copy loop. $54E8-$54E9 is free in the
; verified $5498-$54FF reader gap after the queue cursor at $54E6.
SourceVisual_ReadChunk         = $7E54E8 ; u16 bytes copied this service turn
SourceVisual_ReadRemaining     = $7E54AA ; u16 bounded copy loop
SourceVisual_EntryReady        = $7E54AC
SourceVisual_EntryReadySlot    = $7E54AD
SourceVisual_EntryReadyIndex   = $7E54AE ; u16
SourceVisual_LoaderEntryValid  = $7E54B0
SourceVisual_LoaderEntryIndex  = $7E54B1 ; u16 immutable candidate identity
SourceVisual_LoaderKey         = $7E54B3 ; four-byte candidate key
SourceVisual_PublishedFastPath = $7E54B7
SourceVisual_ReadRequestLength = $7E54B8 ; u16 input length for async reader
SourceVisual_WorkRemaining     = $7E54BA ; u16 shared byte/parse budget per main-loop turn
SourceVisual_FindScanOwner     = $7E54BC
SourceVisual_FindScanActive    = $7E54BD
SourceVisual_FindScanKey       = $7E54BE ; four-byte key retained across bounded lookup turns
SourceVisual_FindScanCursor    = $7E54C2 ; u16 key-table byte offset
SourceVisual_FindScanEnd       = $7E54C4 ; u16 exclusive end offset
SourceVisual_PreflightState    = $7E54C6 ; 0=idle, 1..8 resumable phases, $FF=done
SourceVisual_PreflightActor    = $7E54C7
SourceVisual_PreflightEntry    = $7E54C8 ; u16
SourceVisual_ReadTurnUsed      = $7E54CA ; one seek/poll/copy turn per game loop
SourceVisual_PublishedKey     = $7E54CC ; six 4-byte published source keys
SourceVisual_PlayerPriorityOwner = $7E54E4 ; $FF none; reserved next actor slot
SourceVisual_WaitingActorMask    = $7E54E5 ; queued requests, one bit per actor slot
SourceVisual_QueueCursor         = $7E54E6 ; last actor admitted, round-robin
; Sticky for the current exclusive loader-owner epoch. Only durable actor
; block-offset/map writes set it; global PieceTable/RowScratch do not qualify.
SourceVisual_LoaderDurableProgress = $7E54E7
SOURCE_VISUAL_WORK_BUDGET      = 512
SOURCE_VISUAL_MSU_READ_CHUNK   = SOURCE_VISUAL_WORK_BUDGET
SOURCE_VISUAL_MSU_READ_ENTRY   = 1
SOURCE_VISUAL_MSU_READ_ROW     = 2
SOURCE_VISUAL_MSU_READ_PIECES  = 3
SOURCE_VISUAL_MSU_READ_TILE    = 4
SOURCE_VISUAL_MSU_READ_PALETTE = 5
SOURCE_VISUAL_MSU_READ_BIND    = 6 ; 8-byte SVIX catalog-version footer
SOURCE_VISUAL_ERROR_PUBLISHED_NOT_RESIDENT = $3A
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
    jsr SourceVisual_ResolveActorSlotFromContext
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_BlockCompletedThisCall
    rep #$31
.a16
.i16
    ; Despawns can happen between MSU chunks. Retire a dead candidate reader
    ; even when the entity no longer reaches its own render hook.
    jsr SourceVisual_ProcessRetired
    ; Pit-retired actors remain in the gameplay list until canonical unlink.
    ; Do not reacquire their visual lease or emit stale source pieces meanwhile.
    jsl StageBoundsHost_Normal
    bcc SourceVisual_RenderCurrent__lookup
    jsl StageBounds_Row
    lda.l StageBounds_State,x
    cmp #2
    bne SourceVisual_RenderCurrent__stage_live
    brl SourceVisual_RenderCurrent__retired
SourceVisual_RenderCurrent__stage_live:
SourceVisual_RenderCurrent__lookup:
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    jsr SourceVisual_FindEntry
    bcs SourceVisual_RenderCurrent__entry_found
    sep #$20
.a8
    lda.l SourceVisual_Error
    cmp #$27
    beq SourceVisual_RenderCurrent__entry_pending8
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__fail_near
SourceVisual_RenderCurrent__entry_pending8:
    rep #$31
.a16
.i16
    ; A pending catalog read must not hide an actor that already has a valid
    ; published packet. Rebuild its current-position packet while the bounded
    ; candidate reader resumes on later service turns.
    lda #$0A00
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_ENTRY,x
    sta.l SourceVisual_EntryIndexSaved
    jsr SourceVisual_SetFramePacketIdentity
    jsr SourceVisual_EmitPublishedPacket
    bcs SourceVisual_RenderCurrent__entry_pending_emitted
    brl SourceVisual_RenderCurrent__fail_near
SourceVisual_RenderCurrent__entry_pending_emitted:
    brl SourceVisual_RenderCurrent__publish
SourceVisual_RenderCurrent__entry_found:
    ; FindEntry captured the live semantic identity at key_ready, before its
    ; same-owner path could restore LoaderKey into shared SourceVisual_Key.
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
    brl SourceVisual_RenderCurrent__retired
SourceVisual_RenderCurrent__visible:
    jsr SourceVisual_SelectResidency
    bcs SourceVisual_RenderCurrent__residency_ready
    sep #$20
.a8
    lda.l SourceVisual_Error
    cmp #$27
    beq SourceVisual_RenderCurrent__residency_pending8
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__fail_near
SourceVisual_RenderCurrent__residency_pending8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_ENTRY,x
    sta.l SourceVisual_EntryIndexSaved
    jsr SourceVisual_SetFramePacketIdentity
    jsr SourceVisual_EmitPublishedPacket
    bcs SourceVisual_RenderCurrent__residency_pending_emitted
    brl SourceVisual_RenderCurrent__fail_near
SourceVisual_RenderCurrent__residency_pending_emitted:
    brl SourceVisual_RenderCurrent__publish
SourceVisual_RenderCurrent__residency_ready:
    ; Resume block I/O only after this actor's key, entry, record, and owner
    ; channel have been resolved. Before FindEntry, the shared key/index scratch
    ; can still belong to the previously rendered actor.
    jsr SourceVisual_ResumePendingBlock
    jsr SourceVisual_SetFramePacketIdentity
    sep #$20
.a8
    lda.l SourceVisual_UseCandidate
    beq SourceVisual_RenderCurrent__primary8
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate
SourceVisual_RenderCurrent__primary8:
    rep #$31
.a16
.i16
    ; The residency selector has proved this key is the published lease.
    ; Reposition its cached authored packet without rereading MSU tables.
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    beq SourceVisual_RenderCurrent__primary_load8
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_ENTRY,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceVisual_RenderCurrent__primary_cached
    brl SourceVisual_RenderCurrent__primary_load
SourceVisual_RenderCurrent__primary_load8:
    rep #$31
.a16
.i16
SourceVisual_RenderCurrent__primary_load:
    jsr SourceVisual_LoadResources
    bcs SourceVisual_RenderCurrent__primary_loaded
    brl SourceVisual_RenderCurrent__fail_near
SourceVisual_RenderCurrent__primary_cached:
    jsr SourceVisual_EmitPublishedPacket
    bcs SourceVisual_RenderCurrent__primary_cached_ok
    brl SourceVisual_RenderCurrent__fail_near
SourceVisual_RenderCurrent__primary_cached_ok:
    brl SourceVisual_RenderCurrent__publish
SourceVisual_RenderCurrent__primary_loaded:
    ; The first successful primary emission is the initial published frame.
    ; Route it through the bounded candidate packet lane so it is not displayed
    ; without a complete authored fallback packet while its OAM DMA is pending.
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    beq SourceVisual_RenderCurrent__primary_seed
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__primary_emit
SourceVisual_RenderCurrent__primary_seed:
    rep #$31
.a16
.i16
    jsr SourceVisual_BeginInitialPacket
    bcs SourceVisual_RenderCurrent__primary_seed_ready
    brl SourceVisual_RenderCurrent__fail_near
SourceVisual_RenderCurrent__primary_seed_ready:
    jsr SourceVisual_Emit
    bcs SourceVisual_RenderCurrent__primary_seed_emitted
    jsr SourceVisual_AbortInitialPacket
    brl SourceVisual_RenderCurrent__fail_near
SourceVisual_RenderCurrent__primary_seed_emitted:
    sep #$20
.a8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    bne SourceVisual_RenderCurrent__primary_seed_packet_ready8
    rep #$31
.a16
.i16
    jsr SourceVisual_AbortInitialPacket
    brl SourceVisual_RenderCurrent__primary_emitted
SourceVisual_RenderCurrent__primary_seed_packet_ready8:
    rep #$31
.a16
.i16
    ; Preserve the initial source lease in the normal candidate sidecar. OAM
    ; binding and commit then use the same exact DMA fence as later changes.
    jsr SourceVisual_SaveCandidateSidecar
    lda.l SourceVisual_CandidateBase
    tax
    sep #$20
.a8
    lda #3
    sta.l SourceVisual_CandidateState+30,x
    lda #0
    sta.l SourceVisual_CandidateState+31,x
    rep #$31
.a16
.i16
    jsr SourceVisual_MarkCandidateFence
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_UseCandidate
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #4
    sta.l SourceVisual_OwnerOffset
    brl SourceVisual_RenderCurrent__primary_emitted
SourceVisual_RenderCurrent__primary_emit:
    jsr SourceVisual_Emit
    bcs SourceVisual_RenderCurrent__primary_emitted
    brl SourceVisual_RenderCurrent__fail_near
SourceVisual_RenderCurrent__primary_emitted:
    brl SourceVisual_RenderCurrent__publish
SourceVisual_RenderCurrent__candidate:
    ; Keep the 32-byte published lease below this render's nested calls while
    ; the candidate temporarily occupies the loader's existing state row.
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    ldy #0
SourceVisual_RenderCurrent__candidate_save:
    lda.l SourceVisual_State,x
    pha
    inx
    inx
    iny
    iny
    cpy #32
    bcc SourceVisual_RenderCurrent__candidate_save
    jsr SourceVisual_ActivateCandidate
    bcs SourceVisual_RenderCurrent__candidate_activated
    brl SourceVisual_RenderCurrent__candidate_pending
SourceVisual_RenderCurrent__candidate_activated:
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda.l SourceVisual_State+30,x
    cmp #1
    bne SourceVisual_RenderCurrent__candidate_not_capacity
    brl SourceVisual_RenderCurrent__candidate_capacity_wait
SourceVisual_RenderCurrent__candidate_not_capacity:
    cmp #2
    bne SourceVisual_RenderCurrent__candidate_not_terminal
    brl SourceVisual_RenderCurrent__candidate_terminal_wait
SourceVisual_RenderCurrent__candidate_not_terminal:
    cmp #3
    bne SourceVisual_RenderCurrent__candidate_load
    rep #$31
.a16
.i16
    jsr SourceVisual_CandidateFenceComplete
    bcs SourceVisual_RenderCurrent__candidate_commit
    brl SourceVisual_RenderCurrent__candidate_load
SourceVisual_RenderCurrent__candidate_commit:
    lda.l SourceVisual_ActorSlot
    tax
    sep #$20
.a8
    lda.l SourceVisual_CandidateActionValid,x
    cmp #SOURCE_VISUAL_ACTION_STALE_FENCE
    beq SourceVisual_RenderCurrent__candidate_stale_fence_complete
    rep #$31
.a16
.i16
    ; OAM submission is irreversible, but publication is not. Recheck the
    ; live action snapshot after the exact fence before promoting its lease.
    jsr SourceVisual_CandidateActionMatches
    bcs SourceVisual_RenderCurrent__candidate_commit_current
    jsr SourceVisual_CandidateBeginStaleFallback
    bcs SourceVisual_RenderCurrent__candidate_stale_fallback
    ; Bootstrap packets have no old packet to fall back to. The pre-submit
    ; guard still rejects stale initial packets; once submitted, retain this
    ; first fenced packet so a later current packet can replace it safely.
    brl SourceVisual_RenderCurrent__candidate_commit_current
SourceVisual_RenderCurrent__candidate_stale_fence_complete:
    rep #$31
.a16
.i16
    ; This fence belongs to the already-emitted published fallback, not the
    ; obsolete candidate packet. Retire candidate pins only if the exact token
    ; and all source DMA are complete; otherwise keep drawing the old packet.
    jsr SourceVisual_CandidateRetireStale
    sep #$20
.a8
    lda #4
    sta.l SourceVisual_CandidateAction
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_restore
SourceVisual_RenderCurrent__candidate_stale_fallback:
    jsr SourceVisual_SaveCandidateSidecar
    sep #$20
.a8
    lda #4
    sta.l SourceVisual_CandidateAction
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_restore
SourceVisual_RenderCurrent__candidate_commit_current:
    ; This exact candidate was present in hardware OAM at the matching NMI.
    ; Promote its owner lane only now; the prior published resources remained
    ; pinned until this branch.
    jsr SourceVisual_CommitCandidate
    jsr SourceVisual_Emit
    bcs SourceVisual_RenderCurrent__candidate_committed_emit
    jsr SourceVisual_EmitPublishedPacket
SourceVisual_RenderCurrent__candidate_committed_emit:
    ldy #16
SourceVisual_RenderCurrent__candidate_committed_drop:
    pla
    dey
    bne SourceVisual_RenderCurrent__candidate_committed_drop
    brl SourceVisual_RenderCurrent__publish
SourceVisual_RenderCurrent__candidate_load:
    rep #$31
.a16
.i16
    jsr SourceVisual_LoadResources
    bcs SourceVisual_RenderCurrent__candidate_ready
    sep #$20
.a8
    lda.l SourceVisual_Error
    cmp #$27
    bne SourceVisual_RenderCurrent__candidate_error_not_pending
    brl SourceVisual_RenderCurrent__candidate_pending
SourceVisual_RenderCurrent__candidate_error_not_pending:
    cmp #$24
    bne SourceVisual_RenderCurrent__candidate_error_not_capacity24
    brl SourceVisual_RenderCurrent__candidate_capacity
SourceVisual_RenderCurrent__candidate_error_not_capacity24:
    cmp #$26
    bne SourceVisual_RenderCurrent__candidate_error_terminal
    brl SourceVisual_RenderCurrent__candidate_capacity
SourceVisual_RenderCurrent__candidate_error_terminal:
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_terminal
SourceVisual_RenderCurrent__candidate_ready:
    ; The candidate may have spent many paced turns loading after its action
    ; ended. Reject a role/map/roster change before packet construction; frame
    ; changes within the same action remain eligible.
    jsr SourceVisual_CandidateActionMatches
    bcs SourceVisual_RenderCurrent__candidate_action_current
    ; There is no old packet to draw while the first packet is being loaded.
    ; Abort that initial lease instead of parking a stale, never-presented
    ; candidate indefinitely. A replacement candidate keeps the old packet
    ; and its published owner lane through the normal pending fallback.
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    bne SourceVisual_RenderCurrent__candidate_stale_published8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    jsr SourceVisual_AbortInitialPacket
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_CandidateAction
    rep #$31
.a16
.i16
SourceVisual_RenderCurrent__candidate_initial_stale_aborted:
    brl SourceVisual_RenderCurrent__candidate_restore
SourceVisual_RenderCurrent__candidate_stale_published8:
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_packet_wait
SourceVisual_RenderCurrent__candidate_action_current:
    jsr SourceVisual_Emit
    bcs SourceVisual_RenderCurrent__candidate_emit_ok
    sep #$20
.a8
    lda.l SourceVisual_Error
    cmp #$27
    beq SourceVisual_RenderCurrent__candidate_packet_wait
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_terminal
SourceVisual_RenderCurrent__candidate_emit_ok:
    ; Candidate output is in this frame's OAM shadow. Keep both owner lanes
    ; until Oam_Play tags the main-table request and NMI acknowledges it.
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #3
    sta.l SourceVisual_State+30,x
    lda #0
    sta.l SourceVisual_State+31,x
    rep #$31
.a16
.i16
    jsr SourceVisual_SaveCandidateSidecar
    jsr SourceVisual_MarkCandidateFence
    sep #$20
.a8
    lda #3
    sta.l SourceVisual_CandidateAction
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_restore
SourceVisual_RenderCurrent__candidate_packet_wait:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #4
    sta.l SourceVisual_State+30,x
    rep #$31
.a16
.i16
    jsr SourceVisual_SaveCandidateSidecar
    sep #$20
.a8
    lda #4
    sta.l SourceVisual_CandidateAction
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_restore
SourceVisual_RenderCurrent__candidate_pending:
    rep #$31
.a16
.i16
    jsr SourceVisual_SaveCandidateSidecar
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_CandidateAction
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_restore
SourceVisual_RenderCurrent__candidate_capacity:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+30,x
    lda.l SourceVisual_Error
    sta.l SourceVisual_State+31,x
    rep #$31
.a16
.i16
    jsr SourceVisual_SaveCandidateSidecar
    jsr SourceVisual_ReleaseLoaderOwner
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_CandidateAction
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_restore
SourceVisual_RenderCurrent__candidate_capacity_wait:
    rep #$31
.a16
.i16
    jsr SourceVisual_ReleaseLoaderOwner
    jsr SourceVisual_SaveCandidateSidecar
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_CandidateAction
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_restore
SourceVisual_RenderCurrent__candidate_terminal:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #2
    sta.l SourceVisual_State+30,x
    lda.l SourceVisual_Error
    sta.l SourceVisual_State+31,x
    rep #$31
.a16
.i16
    jsr SourceVisual_SaveCandidateSidecar
    jsr SourceVisual_ReleaseLoaderOwner
    sep #$20
.a8
    lda #2
    sta.l SourceVisual_CandidateAction
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_restore
SourceVisual_RenderCurrent__candidate_terminal_wait:
    rep #$31
.a16
.i16
    jsr SourceVisual_ReleaseLoaderOwner
    jsr SourceVisual_SaveCandidateSidecar
    sep #$20
.a8
    lda #2
    sta.l SourceVisual_CandidateAction
    rep #$31
.a16
.i16
SourceVisual_RenderCurrent__candidate_restore:
    ; Restore stack words in reverse order; each is the exact old published
    ; record, including its local palette map and readiness bits.
    lda.l SourceVisual_Record
    clc
    adc #30
    tax
    ldy #16
SourceVisual_RenderCurrent__candidate_restore_loop:
    pla
    sta.l SourceVisual_State,x
    dex
    dex
    dey
    bne SourceVisual_RenderCurrent__candidate_restore_loop
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_UseCandidate
    sta.l SourceVisual_OwnerChannel
    lda.l SourceVisual_CandidateAction
    sta.l SourceVisual_Temp
    rep #$31
.a16
.i16
    lda #4
    sta.l SourceVisual_OwnerOffset
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+8,x
    sta.l SourceVisual_BaseTile
    lda.l SourceVisual_State+12,x
    sta.l SourceVisual_PaletteBase
    sep #$20
.a8
    lda.l SourceVisual_Temp
    beq SourceVisual_RenderCurrent__candidate_fallback
    cmp #1
    beq SourceVisual_RenderCurrent__candidate_restore_capacity
    cmp #3
    beq SourceVisual_RenderCurrent__candidate_emitted
    cmp #4
    beq SourceVisual_RenderCurrent__candidate_fallback
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_restore_terminal
SourceVisual_RenderCurrent__candidate_restore_capacity:
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__candidate_fallback
SourceVisual_RenderCurrent__candidate_emitted:
    rep #$31
.a16
.i16
    brl SourceVisual_RenderCurrent__publish
SourceVisual_RenderCurrent__candidate_restore_terminal:
    rep #$31
.a16
.i16
    jsr SourceVisual_HasOwnedDma
    bcs SourceVisual_RenderCurrent__candidate_fallback
    jsr SourceVisual_DiscardAllActorVisuals
    brl SourceVisual_RenderCurrent__fail_near
SourceVisual_RenderCurrent__candidate_fallback:
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State,x
    sta.l SourceVisual_EntryIndexSaved
    jsr SourceVisual_SetFramePacketIdentity
    jsr SourceVisual_EmitPublishedPacket
    bcc SourceVisual_RenderCurrent__fail_near
    brl SourceVisual_RenderCurrent__publish
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
    ply
    plx
    pld
    plb
    plp
    sec
    rtl
SourceVisual_RenderCurrent__retired:
    rep #$31
.a16
.i16
    jsr SourceVisual_ClearQueuedActor
    jsr SourceVisual_ReleaseLoaderOwner
    jsr SourceVisual_MarkActorForOamRetire
    ply
    plx
    pld
    plb
    plp
    sec
    rtl

; Drop only the candidate lane and its sidecar after the candidate DMA fence.
SourceVisual_DiscardCandidatePins:
    jsr SourceVisual_ReleaseLoaderOwner
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #7
    sta.l SourceVisual_OwnerOffset
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes
    lda.l SourceVisual_CandidateBase
    tax
    lda #0
    ldy #16
SourceVisual_DiscardCandidatePins__clear:
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    dey
    bne SourceVisual_DiscardCandidatePins__clear
    jsr SourceVisual_CandidateActionClear
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_OwnerChannel
    sta.l SourceVisual_UseCandidate
    lda.l SourceVisual_PacketCandidateOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_DiscardCandidatePins__lane_done
    lda #$FF
    sta.l SourceVisual_PacketCandidateOwner
    lda #0
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
SourceVisual_DiscardCandidatePins__lane_done:
    rep #$31
.a16
.i16
    lda #4
    sta.l SourceVisual_OwnerOffset
    rts

; Terminal decode/emission failure retires both leases only when no transfer
; can still reference their staging data.
SourceVisual_DiscardAllActorVisuals:
    ; Terminal failure hides this actor in the next OAM packet. Its tile and
    ; palette owners remain pinned until that packet's DMA fence completes.
    jsr SourceVisual_MarkActorForOamRetire
    rts

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
    sep #$20
.a8
    lda.l SourceVisual_Error
    cmp #$27
    beq SourceVisual_RenderCurrent__fail_keep_reader8
    rep #$31
.a16
.i16
    jsr SourceVisual_ReleaseLoaderOwner
    bra SourceVisual_RenderCurrent__fail_log
SourceVisual_RenderCurrent__fail_keep_reader8:
    rep #$31
.a16
.i16
SourceVisual_RenderCurrent__fail_log:
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
SourceVisual_RenderCurrent__fail_return:
    ply
    plx
    pld
    plb
    plp
    clc
    rtl

; Build the presentation key from accepted-compat state and find its compiler
; generated entry.  No model-name branch exists here.
SourceVisual_ConsumeWork:
    rep #$31
.a16
.i16
    lda.l SourceVisual_WorkRemaining
    beq SourceVisual_ConsumeWork__empty
    dec a
    sta.l SourceVisual_WorkRemaining
    sec
    rts
SourceVisual_ConsumeWork__empty:
    clc
    rts

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
    ; Snapshot the actor's current semantic action before an active loader
    ; restores its immutable catalog key into SourceVisual_Key. Frame, facing,
    ; and loader request identity remain separate from this per-pass snapshot.
    jsr SourceVisual_CaptureCurrentAction
    bcs SourceVisual_FindEntry__key_action_captured
    rep #$31
    .a16
    .i16
    clc
    rts
SourceVisual_FindEntry__key_action_captured:
    sep #$20
    .a8
    ; Preserve changed requests behind the active immutable read. A reserved
    ; next owner blocks fresh scans, while the current scan/read owner can
    ; finish its bounded work and yield at a descriptor boundary.
    jsr SourceVisual_QueueChangedLoaderKey
    jsr SourceVisual_PriorityGate
    bcc SourceVisual_FindEntry__loader_busy8
    sep #$20
.a8
    lda.l SourceVisual_FindScanActive
    beq SourceVisual_FindEntry__check_loader8
    lda.l SourceVisual_FindScanOwner
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_FindEntry__resume_scan_key8
    jsr SourceVisual_QueueCurrentActor
    jsr SourceVisual_RequestPlayerPriority
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_FindEntry__resume_scan_key8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_FindScanKey
    sta.l SourceVisual_Key
    lda.l SourceVisual_FindScanKey+2
    sta.l SourceVisual_Key+2
    sep #$20
.a8
SourceVisual_FindEntry__check_loader8:
    lda.l SourceVisual_LoaderOwner
    cmp #$FF
    bne SourceVisual_FindEntry__loader_set8
    brl SourceVisual_FindEntry__no_loader8
SourceVisual_FindEntry__loader_set8:
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_FindEntry__different_owner8
    brl SourceVisual_FindEntry__loader_owner8
SourceVisual_FindEntry__different_owner8:
    ; A changed input-driven player gets one safe priority turn. Every blocked
    ; actor also enters the bounded round-robin wait mask.
    jsr SourceVisual_QueueCurrentActor
    jsr SourceVisual_RequestPlayerPriority
    brl SourceVisual_FindEntry__loader_busy
SourceVisual_FindEntry__loader_busy:
    sep #$20
SourceVisual_FindEntry__loader_busy8:
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_FindEntry__loader_owner8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_LoaderKey
    sta.l SourceVisual_Key
    sta.l SourceVisual_KeySaved
    lda.l SourceVisual_LoaderKey+2
    sta.l SourceVisual_Key+2
    sta.l SourceVisual_KeySaved+2
    lda.l SourceVisual_LoaderEntryIndex
    sta.l SourceVisual_EntryIndexSaved
    brl SourceVisual_FindEntry__cached_key_check
SourceVisual_FindEntry__no_loader8:
    rep #$31
.a16
.i16

    ; The accepted renderer asks for the same visual key on every pass while
    ; a frame remains current.  Reusing the compiler entry already loaded for
    ; that key avoids rescanning the 3,640-row native key table on every
    ; compositor invocation.  EntryScratch is immutable catalog data and is
    ; only replaced on a cold-key lookup, so this is safe for same-key
    ; instances and does not create a second simulation state.
    rep #$31
.a16
.i16
SourceVisual_FindEntry__cached_key_check:
    lda.l SourceVisual_Key
    cmp.l SourceVisual_KeySaved
    bne SourceVisual_FindEntry__cold
    lda.l SourceVisual_Key+2
    cmp.l SourceVisual_KeySaved+2
    bne SourceVisual_FindEntry__cold
    lda.l SourceVisual_EntryIndexSaved
    cmp #SOURCE_VISUAL_CATALOG_COUNT
    bcs SourceVisual_FindEntry__cold
    sep #$20
.a8
    lda.l SourceVisual_EntryReady
    cmp #1
    bne SourceVisual_FindEntry__cached_entry_missing8
    lda.l SourceVisual_EntryReadySlot
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_FindEntry__cached_entry_missing8
    rep #$31
.a16
.i16
    lda.l SourceVisual_EntryReadyIndex
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceVisual_FindEntry__cached_entry_ready
    brl SourceVisual_FindEntry__saved_entry_read
SourceVisual_FindEntry__cached_entry_missing8:
    rep #$31
.a16
.i16
    brl SourceVisual_FindEntry__saved_entry_read
SourceVisual_FindEntry__cached_entry_ready:
    jsr SourceVisual_ClearQueuedActor
    sec
    rts
SourceVisual_FindEntry__cold:

    sep #$20
.a8
    lda.l SourceVisual_FindScanActive
    beq SourceVisual_FindEntry__fresh_scan8
    brl SourceVisual_FindEntry__scan_resume8
SourceVisual_FindEntry__fresh_scan8:
    rep #$31
.a16
.i16

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
    lda.l SourceVisual_Key
    sta.l SourceVisual_FindTrace,x
    lda.l SourceVisual_Key+2
    sta.l SourceVisual_FindTrace+2,x
    tdc
    sta.l SourceVisual_FindTrace+4,x
    lda.l SourceVisual_FindTraceIndex
    inc a
    sta.l SourceVisual_FindTraceIndex
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
    sta.l SourceVisual_FindScanEnd
    lda.l SourceVisual_Temp
    sta.l SourceVisual_FindScanCursor
    sep #$20
.a8
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_FindScanOwner
    lda.l SourceVisual_Key
    sta.l SourceVisual_FindScanKey
    lda.l SourceVisual_Key+1
    sta.l SourceVisual_FindScanKey+1
    lda.l SourceVisual_Key+2
    sta.l SourceVisual_FindScanKey+2
    lda.l SourceVisual_Key+3
    sta.l SourceVisual_FindScanKey+3
    lda #1
    sta.l SourceVisual_FindScanActive
    rep #$31
.a16
.i16
    lda.l SourceVisual_FindScanCursor
    tax
    lda.l SourceVisual_FindScanEnd
    sta.l SourceVisual_DebugD
    bra SourceVisual_FindEntry__scan
SourceVisual_FindEntry__scan_resume8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_FindScanCursor
    tax
    lda.l SourceVisual_FindScanEnd
    sta.l SourceVisual_DebugD
SourceVisual_FindEntry__scan:
    txa
    cmp.l SourceVisual_DebugD
    bcc SourceVisual_FindEntry__scan_budget_check
    brl SourceVisual_FindEntry__unsupported_scan
SourceVisual_FindEntry__scan_budget_check:
.a16
.i16
    jsr SourceVisual_ConsumeWork
    bcs SourceVisual_FindEntry__scan_budget_ok
    txa
    sta.l SourceVisual_FindScanCursor
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_FindEntry__scan_budget_ok:
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
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_FindScanActive
    rep #$31
.a16
.i16
    lda.l SourceVisual_FindTraceOffset
    tax
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_FindTrace+6,x
    lda.l SourceVisual_Key
    sta.l SourceVisual_KeySaved
    lda.l SourceVisual_Key+2
    sta.l SourceVisual_KeySaved+2
    brl SourceVisual_FindEntry__saved_entry_read

SourceVisual_FindEntry__saved_entry_read:
    rep #$31
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
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
    sep #$20
    .a8
    lda #0
    sta.l SourceVisual_UseCandidate
    sta.l SourceVisual_OwnerChannel
    rep #$31
    .a16
    .i16
    lda #4
    sta.l SourceVisual_OwnerOffset
    ; Record stride is 32 bytes, while the adjacent diagnostic row
    ; remains the historical 8-byte-per-actor layout.
    tya
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Record
    sta.l SourceVisual_CandidateBase
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
    ; Finish an open packet before adopting another sampled animation key.
    sep #$20
    .a8
    lda.l SourceVisual_State+28,x
    beq SourceVisual_SelectResidency__compare_entry8
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_CandidateBase
    tax
    sep #$20
    .a8
    lda.l SourceVisual_CandidateState+6,x
    bne SourceVisual_SelectResidency__replace_ready
    rep #$31
    .a16
    .i16
SourceVisual_SelectResidency__compare_entry8:
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    bne SourceVisual_SelectResidency__entry_changed
    brl SourceVisual_SelectResidency__found
SourceVisual_SelectResidency__entry_changed:
    sep #$20
.a8
    lda.l SourceVisual_State+28,x
    bne SourceVisual_SelectResidency__replace_ready
    ; No OAM packet has ever been published for this lease, so a changed live
    ; key can replace it safely. Published actors use the candidate lane above.
    brl SourceVisual_SelectResidency__replace
SourceVisual_SelectResidency__replace_ready:
    rep #$31
.a16
.i16
    jsr SourceVisual_SelectCandidate
    bcc SourceVisual_SelectResidency__candidate_failed
    brl SourceVisual_SelectResidency__mark
SourceVisual_SelectResidency__candidate_failed:
    clc
    rts
SourceVisual_SelectResidency__identity_changed:
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_State+28,x
    beq SourceVisual_SelectResidency__replace
    ; Keep the displayed identity's published lease while a different actor
    ; identity is admitted through the independent candidate owner lane.
    jsr SourceVisual_SelectCandidate
    bcc SourceVisual_SelectResidency__candidate_failed
    brl SourceVisual_SelectResidency__mark
SourceVisual_SelectResidency__replace:
    ; The shared source staging buffer and queued DMA must be retired before
    ; the old lease can be returned to the bounded allocator.
    jsr SourceVisual_HasOwnedDma
    bcc SourceVisual_SelectResidency__clear_record
    brl SourceVisual_SelectResidency__busy
SourceVisual_SelectResidency__clear_record:
    ; A newly found catalog entry is the input to the resource transaction we
    ; are about to start. Keep that completed entry (and its loader identity)
    ; across the initial empty-lease allocation; otherwise the next render
    ; re-reads the key before LoadResources can resume its queued sheet row.
    sep #$20
.a8
    lda.l SourceVisual_EntryReady
    cmp #1
    bne SourceVisual_SelectResidency__clear_release_loader8
    lda.l SourceVisual_EntryReadySlot
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_SelectResidency__clear_release_loader8
    rep #$31
.a16
.i16
    lda.l SourceVisual_EntryReadyIndex
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceVisual_SelectResidency__clear_loader_preserved
    brl SourceVisual_SelectResidency__clear_release_loader
SourceVisual_SelectResidency__clear_release_loader8:
    rep #$31
.a16
.i16
SourceVisual_SelectResidency__clear_release_loader:
    jsr SourceVisual_ReleaseLoaderOwner
    bra SourceVisual_SelectResidency__clear_loader_done
SourceVisual_SelectResidency__clear_loader_preserved:
SourceVisual_SelectResidency__clear_loader_done:
    jsr SourceVisual_ReleaseActorOwnership
    lda.l SourceVisual_CandidateBase
    tax
    lda #0
    ldy #16
SourceVisual_SelectResidency__clear_candidate:
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    dey
    bne SourceVisual_SelectResidency__clear_candidate
    jsr SourceVisual_CandidateActionClear
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
    ; Bind the first lease's semantic identity before any paced MSU resource
    ; work can outlive the request. BeginInitialPacket later checks this saved
    ; asset key against fresh FrameMeta instead of recapturing mutable Key.
    jsr SourceVisual_CandidateActionCapture
    bcs SourceVisual_SelectResidency__initial_action_ready
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_SelectResidency__initial_action_ready:
    lda.l SourceVisual_Record
    tax
    lda #1
    sta.l SourceVisual_State+6,x
    lda #0
    sta.l SourceVisual_BaseTile
    sta.l SourceVisual_PaletteBase
    bra SourceVisual_SelectResidency__mark
SourceVisual_SelectResidency__found:
    ; Default to published ownership; SelectCandidate marks its sidecar path.
    sep #$20
    .a8
    lda #0
    sta.l SourceVisual_UseCandidate
    sta.l SourceVisual_OwnerChannel
    rep #$31
    .a16
    .i16
    lda #4
    sta.l SourceVisual_OwnerOffset
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

; Select or create one bounded replacement packet while preserving the
; published lease in SourceVisual_State and its independent owner lane.
SourceVisual_SelectCandidate:
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidateBase
    tax
    sep #$20
.a8
    lda.l SourceVisual_CandidateState+6,x
    bne SourceVisual_SelectCandidate__existing
    brl SourceVisual_SelectCandidate__new
SourceVisual_SelectCandidate__existing:
    lda.l SourceVisual_CandidateState+29,x
    cmp.l SourceVisual_Key
    bne SourceVisual_SelectCandidate__identity_replace
    rep #$31
    .a16
    .i16
    jsr SourceVisual_CandidateActionMatches
    bcs SourceVisual_SelectCandidate__action_matches
    brl SourceVisual_SelectCandidate__identity_replace
SourceVisual_SelectCandidate__action_matches:
    ; CandidateActionMatches uses X for its compact identity record. Restore
    ; the 32-byte lane index before reading candidate status bytes.
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_CandidateBase
    tax
    sep #$20
    .a8
    lda.l SourceVisual_CandidateState+30,x
    cmp #1
    bne SourceVisual_SelectCandidate__status_not_capacity
    brl SourceVisual_SelectCandidate__capacity_wait
SourceVisual_SelectCandidate__status_not_capacity:
    cmp #2
    bne SourceVisual_SelectCandidate__not_terminal
    brl SourceVisual_SelectCandidate__terminal_wait
SourceVisual_SelectCandidate__not_terminal:
    cmp #4
    bne SourceVisual_SelectCandidate__selected_existing
    lda.l SourceVisual_PacketCandidateOwner
    cmp #$FF
    beq SourceVisual_SelectCandidate__selected_existing
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_SelectCandidate__selected_existing
    brl SourceVisual_SelectCandidate__pending_existing
SourceVisual_SelectCandidate__selected_existing:
    rep #$31
.a16
.i16
    brl SourceVisual_SelectCandidate__selected
SourceVisual_SelectCandidate__identity_replace:
    rep #$31
.a16
.i16
    ; A candidate that already reached OAM must be promoted before this lane
    ; can be reused. An uncommitted candidate is held until its outstanding
    ; source DMA and, when applicable, OAM fence have retired.
    lda.l SourceVisual_CandidateBase
    tax
    sep #$20
.a8
    lda.l SourceVisual_CandidateState+30,x
    cmp #3
    bne SourceVisual_SelectCandidate__identity_wait
    rep #$31
.a16
.i16
    jsr SourceVisual_CandidateFenceComplete
    bcs SourceVisual_SelectCandidate__identity_commit
    brl SourceVisual_SelectCandidate__identity_wait
SourceVisual_SelectCandidate__identity_commit:
    ; The candidate packet's exact OAM fence is complete. Compare against the
    ; live action snapshot from FindEntry, never the catalog key restored while
    ; loading the candidate.
    jsr SourceVisual_CandidateActionMatches
    bcs SourceVisual_SelectCandidate__identity_commit_current
    lda.l SourceVisual_ActorSlot
    tax
    sep #$20
    .a8
    lda.l SourceVisual_CandidateActionValid,x
    cmp #SOURCE_VISUAL_ACTION_STALE_FENCE
    beq SourceVisual_SelectCandidate__identity_retire_stale
    rep #$31
    .a16
    .i16
    jsr SourceVisual_CandidateBeginStaleFallback
    bcs SourceVisual_SelectCandidate__identity_stale_fallback
    ; With no prior packet, the first fenced packet is the only safe visible
    ; bootstrap. It can be replaced on a later pass after a current action is
    ; resolved; the pre-submit guard still prevents recording stale initial OAM.
    brl SourceVisual_SelectCandidate__identity_commit_current
SourceVisual_SelectCandidate__identity_stale_fallback:
    sep #$20
    .a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
    .a16
    .i16
    clc
    rts
SourceVisual_SelectCandidate__identity_retire_stale:
    rep #$31
    .a16
    .i16
    jsr SourceVisual_CandidateRetireStale
    bcs SourceVisual_SelectCandidate__identity_stale_retired
    sep #$20
    .a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
    .a16
    .i16
    clc
    rts
SourceVisual_SelectCandidate__identity_stale_retired:
    ; CandidateRetireStale has cleared candidate ownership and the completed
    ; reader. Shared Key/EntryIndexSaved can still name that retired asset, so
    ; defer replacement until the next FindEntry resolves the live request.
    brl SourceVisual_SelectCandidate__identity_wait_retry
SourceVisual_SelectCandidate__identity_commit_current:
    jsr SourceVisual_ActivateCandidate
    jsr SourceVisual_CommitCandidate
    brl SourceVisual_SelectCandidate__new
SourceVisual_SelectCandidate__identity_wait:
    rep #$31
.a16
.i16
    ; A stale submitted candidate must never be reactivated while its DMA or
    ; OAM fence is still outstanding. Keep the old published packet visible.
    jsr SourceVisual_CandidateActionMatches
    bcs SourceVisual_SelectCandidate__identity_wait_action_current
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    beq SourceVisual_SelectCandidate__identity_wait_no_old8
    ; The old published packet is a valid fallback, but an unsubmitted stale
    ; candidate must not retain the completed shared reader forever. Preserve
    ; any candidate that has an OAM owner/token or source DMA; otherwise discard
    ; only its lane and release its reader descriptor before resolving the
    ; current live key. State+30=3 remains governed by the exact-fence path.
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_CandidateBase
    tax
    sep #$20
    .a8
    lda.l SourceVisual_CandidateState+30,x
    cmp #3
    beq SourceVisual_SelectCandidate__identity_wait_keep_old8
    lda.l SourceVisual_PacketCandidateOwner
    cmp #$FF
    bne SourceVisual_SelectCandidate__identity_wait_keep_old8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    bne SourceVisual_SelectCandidate__identity_wait_keep_old8
    rep #$31
    .a16
    .i16
    jsr SourceVisual_HasOwnedDma
    bcs SourceVisual_SelectCandidate__identity_wait_retry
    jsr SourceVisual_DiscardCandidatePins
    ; FindEntry may have restored an older same-owner LoaderKey before this
    ; stale-action check. After cleanup, return pending so the next render
    ; recomputes the live key instead of admitting that stale asset again.
    brl SourceVisual_SelectCandidate__identity_wait_retry
SourceVisual_SelectCandidate__identity_wait_keep_old8:
    rep #$31
    .a16
    .i16
SourceVisual_SelectCandidate__identity_wait_retry:
    .a16
    .i16
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_SelectCandidate__identity_wait_no_old8:
    rep #$31
.a16
.i16
SourceVisual_SelectCandidate__identity_wait_action_current:
    jsr SourceVisual_HasOwnedDma
    bcc SourceVisual_SelectCandidate__identity_dma_idle
    brl SourceVisual_SelectCandidate__pending_existing
SourceVisual_SelectCandidate__identity_dma_idle:
    ; A completed candidate may have been on hardware OAM. Keep the lane
    ; immutable until the next matching scene DMA has replaced that packet.
    lda.l SourceVisual_CandidateBase
    tax
    sep #$20
.a8
    lda.l SourceVisual_CandidateState+30,x
    cmp #3
    bne SourceVisual_SelectCandidate__identity_releasable
    brl SourceVisual_SelectCandidate__pending_existing
SourceVisual_SelectCandidate__identity_releasable:
    rep #$31
.a16
.i16
    sep #$20
    .a8
    lda.l SourceVisual_PacketCandidateOwner
    cmp #$FF
    bne SourceVisual_SelectCandidate__pending_existing
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    bne SourceVisual_SelectCandidate__pending_existing
    rep #$31
    .a16
    .i16
    ; This covers both a stale candidate with no published fallback and a
    ; same-action key replacement. The common helper releases a completed
    ; ReadState=4 descriptor as well as candidate-only cache pins; published
    ; State, packet metadata, OAM, and owner lane are untouched.
    jsr SourceVisual_DiscardCandidatePins
    ; EntryIndexSaved/Key may describe the just-retired request. Re-run
    ; FindEntry on the next render before creating a replacement candidate.
    brl SourceVisual_SelectCandidate__identity_wait_retry
SourceVisual_SelectCandidate__capacity_wait:
    rep #$31
.a16
.i16
    ; A failed capacity admission is latched for this exact catalog entry.
    ; Do not repeat an impossible preflight every field; retry only if the
    ; actor requests a different entry. Any partial candidate pins are dropped
    ; only after the shared DMA fence is clear.
    lda.l SourceVisual_CandidateBase
    tax
    lda.l SourceVisual_CandidateState,x
    cmp.l SourceVisual_EntryIndexSaved
    bne SourceVisual_SelectCandidate__capacity_replace
    jsr SourceVisual_HasOwnedDma
    bcs SourceVisual_SelectCandidate__pending_existing
    brl SourceVisual_SelectCandidate__capacity_drop_partial
SourceVisual_SelectCandidate__capacity_replace:
    jsr SourceVisual_HasOwnedDma
    bcs SourceVisual_SelectCandidate__pending_existing
SourceVisual_SelectCandidate__capacity_drop_partial:
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #7
    sta.l SourceVisual_OwnerOffset
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes
    lda.l SourceVisual_CandidateBase
    tax
    rep #$31
.a16
.i16
    ; Keep the bounded capacity-failure marker when the same entry remains
    ; requested. A different entry gets a fresh candidate below.
    lda.l SourceVisual_CandidateState,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceVisual_SelectCandidate__selected
    brl SourceVisual_SelectCandidate__clear_sidecar_new
SourceVisual_SelectCandidate__terminal_wait:
    rep #$31
.a16
.i16
    jsr SourceVisual_HasOwnedDma
    bcs SourceVisual_SelectCandidate__pending_existing
    lda.l SourceVisual_CandidateBase
    tax
    sep #$20
.a8
    lda.l SourceVisual_CandidateState+31,x
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    ; Terminal failure hides the current OAM packet, but the published tile
    ; and palette owners remain pinned until that OAM DMA completes.
    jsr SourceVisual_DiscardCandidatePins
    jsr SourceVisual_MarkActorForOamRetire
    brl SourceVisual_SelectCandidate__clear_sidecar_fail
SourceVisual_SelectCandidate__pending_existing:
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    brl SourceVisual_SelectCandidate__selected
SourceVisual_SelectCandidate__new:
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidateBase
    tax
    lda #0
    ldy #16
SourceVisual_SelectCandidate__zero_new:
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    dey
    bne SourceVisual_SelectCandidate__zero_new
    lda.l SourceVisual_CandidateBase
    tax
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_CandidateState,x
    lda #1
    sta.l SourceVisual_CandidateState+6,x
    sep #$20
.a8
    lda.l SourceVisual_Key
    sta.l SourceVisual_CandidateState+29,x
    rep #$31
.a16
.i16
    jsr SourceVisual_CandidateActionCapture
    bcs SourceVisual_SelectCandidate__new_action_captured
    sep #$20
    .a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
    .a16
    .i16
    brl SourceVisual_SelectCandidate__clear_sidecar_fail
SourceVisual_SelectCandidate__new_action_captured:
SourceVisual_SelectCandidate__selected:
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_UseCandidate
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #7
    sta.l SourceVisual_OwnerOffset
    sec
    rts
SourceVisual_SelectCandidate__clear_sidecar_new:
    lda.l SourceVisual_CandidateBase
    tax
    lda #0
    ldy #16
SourceVisual_SelectCandidate__clear_new:
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    dey
    bne SourceVisual_SelectCandidate__clear_new
    jsr SourceVisual_CandidateActionClear
    brl SourceVisual_SelectCandidate__new
SourceVisual_SelectCandidate__clear_sidecar_fail:
    lda.l SourceVisual_CandidateBase
    tax
    lda #0
    ldy #16
SourceVisual_SelectCandidate__clear_fail:
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    dey
    bne SourceVisual_SelectCandidate__clear_fail
    jsr SourceVisual_CandidateActionClear
    clc
    rts

; Activate a selected candidate only after the caller has saved the published
; record on its bounded per-render stack frame.
SourceVisual_ActivateCandidate:
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidateBase
    tax
    ldy #0
SourceVisual_ActivateCandidate__copy:
    lda.l SourceVisual_CandidateState,x
    sta.l SourceVisual_State,x
    inx
    inx
    iny
    iny
    cpy #32
    bcc SourceVisual_ActivateCandidate__copy
    jsr SourceVisual_LoadPendingEntry
    bcs SourceVisual_ActivateCandidate__entry_ready
    rts
SourceVisual_ActivateCandidate__entry_ready:
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+8,x
    sta.l SourceVisual_BaseTile
    lda.l SourceVisual_State+12,x
    sta.l SourceVisual_PaletteBase
    sec
    rts

; Initial primary publication uses the same packet lane and NMI fence as a
; replacement candidate. Keep its already-resident published lease pinned in
; both owner lanes until CommitCandidate atomically promotes the fenced packet.
SourceVisual_BeginInitialPacket:
    sep #$20
.a8
    lda.l SourceVisual_PacketCandidateOwner
    cmp #$FF
    bne SourceVisual_BeginInitialPacket__busy8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    bne SourceVisual_BeginInitialPacket__busy8
    rep #$31
.a16
.i16
    jsr SourceVisual_PinCurrentLeaseCandidate
    ; The key/identity was captured when this initial lease was created, before
    ; resource loading. Recheck against this pass's live snapshot; never let a
    ; later request relabel the already-loaded asset.
    jsr SourceVisual_CandidateActionMatches
    bcs SourceVisual_BeginInitialPacket__action_matches
    sep #$20
    .a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
    .a16
    .i16
    jsr SourceVisual_AbortInitialPacket
    clc
    rts
SourceVisual_BeginInitialPacket__action_matches:
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_UseCandidate
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #7
    sta.l SourceVisual_OwnerOffset
    sec
    rts
SourceVisual_BeginInitialPacket__busy8:
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts

; Capture the full resolved asset key [roster, role, frame, map], then derive
; the action identity [roster, role, map]. The key belongs to EntryIndexSaved
; after a fresh key match or same-owner LoaderKey restore. FrameMeta remains
; the independent live request. Facing is sampled at Emit time; packets store
; both authored orientations. CandidateKey lives in its separately checked
; $7EEEA2 sidecar; the compact action identity remains in $7E4BB4-$7E4BCB.
SourceVisual_CaptureCurrentAction:
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcs SourceVisual_CaptureCurrentAction__bad
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
    .a8
    lda #0
    sta.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_VALID,x
    lda.l SourceVisual_Key
    sta.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_ROSTER,x
    lda.l SourceVisual_Key+1
    sta.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_ROLE,x
    lda.l SourceVisual_Key+2
    sta.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_FRAME,x
    lda.l SourceVisual_Key+3
    sta.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_MAP,x
    lda #1
    sta.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_VALID,x
    rep #$31
    .a16
    .i16
    sec
    rts
SourceVisual_CaptureCurrentAction__bad:
    clc
    rts

SourceVisual_CandidateActionCapture:
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcs SourceVisual_CandidateActionCapture__bad
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
    .a8
    lda.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_VALID,x
    cmp #SOURCE_VISUAL_ACTION_LIVE
    bne SourceVisual_CandidateActionCapture__bad8
    rep #$31
    .a16
    .i16
    ; SourceVisual_Key is the key for the resolved EntryIndexSaved here: a
    ; same-owner lookup has already restored LoaderKey, while a fresh lookup
    ; still holds the key that produced EntryReady. Save all four bytes now;
    ; FrameMeta remains the independently captured live request used by guards.
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    tax
    lda.l SourceVisual_Key
    sta.l SourceVisual_CandidateKey,x
    lda.l SourceVisual_Key+2
    sta.l SourceVisual_CandidateKey+2,x
    sep #$20
    .a8
    lda.l SourceVisual_CandidateKey,x
    sta.l SourceVisual_CurrentActionScratch
    lda.l SourceVisual_CandidateKey+1,x
    sta.l SourceVisual_CurrentActionScratch+1
    lda.l SourceVisual_CandidateKey+3,x
    sta.l SourceVisual_CurrentActionScratch+2
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_ActorSlot
    asl a
    clc
    adc.l SourceVisual_ActorSlot
    tax
    sep #$20
    .a8
    lda.l SourceVisual_CurrentActionScratch
    sta.l SourceVisual_CandidateActionIdentity,x
    lda.l SourceVisual_CurrentActionScratch+1
    sta.l SourceVisual_CandidateActionIdentity+1,x
    lda.l SourceVisual_CurrentActionScratch+2
    sta.l SourceVisual_CandidateActionIdentity+2,x
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_ActorSlot
    tax
    sep #$20
    .a8
    lda #1
    sta.l SourceVisual_CandidateActionValid,x
    rep #$31
    .a16
    .i16
    sec
    rts
SourceVisual_CandidateActionCapture__bad8:
    rep #$31
    .a16
    .i16
SourceVisual_CandidateActionCapture__bad:
    clc
    rts

; C=1 only when this actor still requests the candidate key's semantic action.
; Frame byte 2 may advance within a role; facing is intentionally excluded.
SourceVisual_CandidateActionMatches:
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcs SourceVisual_CandidateActionMatches__bad
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
    .a8
    lda.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_VALID,x
    cmp #SOURCE_VISUAL_ACTION_LIVE
    bne SourceVisual_CandidateActionMatches__bad8
    lda.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_ROSTER,x
    sta.l SourceVisual_CurrentActionScratch
    lda.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_ROLE,x
    sta.l SourceVisual_CurrentActionScratch+1
    lda.l SourceVisual_FrameMeta+SOURCE_VISUAL_FRAME_ACTION_MAP,x
    sta.l SourceVisual_CurrentActionScratch+2
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_ActorSlot
    tax
    sep #$20
    .a8
    lda.l SourceVisual_CandidateActionValid,x
    cmp #SOURCE_VISUAL_ACTION_LIVE
    bne SourceVisual_CandidateActionMatches__bad8
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_ActorSlot
    asl a
    clc
    adc.l SourceVisual_ActorSlot
    tax
    sep #$20
    .a8
    lda.l SourceVisual_CandidateActionIdentity,x
    cmp.l SourceVisual_CurrentActionScratch
    bne SourceVisual_CandidateActionMatches__bad8
    lda.l SourceVisual_CandidateActionIdentity+1,x
    cmp.l SourceVisual_CurrentActionScratch+1
    bne SourceVisual_CandidateActionMatches__bad8
    lda.l SourceVisual_CandidateActionIdentity+2,x
    cmp.l SourceVisual_CurrentActionScratch+2
    bne SourceVisual_CandidateActionMatches__bad8
    rep #$31
    .a16
    .i16
    sec
    rts
SourceVisual_CandidateActionMatches__bad8:
    rep #$31
    .a16
    .i16
SourceVisual_CandidateActionMatches__bad:
    clc
    rts

; Clear the current actor's candidate-key validity and key bytes. Callers own
; candidate-lane retirement; clearing identity never releases resources or
; changes a fence.
SourceVisual_CandidateActionClear:
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcs SourceVisual_CandidateActionClear__done
    tax
    sep #$20
    .a8
    lda #SOURCE_VISUAL_ACTION_NONE
    sta.l SourceVisual_CandidateActionValid,x
    rep #$31
    .a16
    .i16
    ; Invalidate before clearing the immutable key so no consumer can mistake
    ; a partially cleared row for a live candidate identity.
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    tax
    lda #0
    sta.l SourceVisual_CandidateKey,x
    sta.l SourceVisual_CandidateKey+2,x
SourceVisual_CandidateActionClear__done:
    rts

; Begin a two-fence retirement for a stale, already-submitted candidate.
; Caller has proven the candidate's exact sequence+epoch fence completed.
; Return C=1 only when a valid old packet exists and must be re-emitted.
; The old published owner lane stays pinned; candidate owners stay pinned until
; the fallback OAM fence completes. A first packet has no fallback and returns
; C=0 so the caller can retain the only fenced packet as a bootstrap.
SourceVisual_CandidateBeginStaleFallback:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcs SourceVisual_CandidateBeginStaleFallback__no
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    beq SourceVisual_CandidateBeginStaleFallback__no8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    beq SourceVisual_CandidateBeginStaleFallback__no8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_OWNER
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_CandidateBeginStaleFallback__no8
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    tax
    sep #$20
.a8
    lda.l SourceVisual_CandidateActionValid,x
    cmp #SOURCE_VISUAL_ACTION_LIVE
    bne SourceVisual_CandidateBeginStaleFallback__no8
    lda #SOURCE_VISUAL_ACTION_STALE_FENCE
    sta.l SourceVisual_CandidateActionValid,x
    lda #0
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+1
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+2
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+3
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH+1
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH+2
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH+3
    rep #$31
.a16
.i16
    sec
    rts
SourceVisual_CandidateBeginStaleFallback__no8:
    rep #$31
.a16
.i16
SourceVisual_CandidateBeginStaleFallback__no:
    clc
    rts

; Retire only the candidate owner channel after its fallback OAM fence has
; completed. Published packet metadata and published cache-owner bits remain
; intact. Return C=0 while any source DMA is still owned.
SourceVisual_CandidateRetireStale:
    sep #$20
.a8
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcs SourceVisual_CandidateRetireStale__not_ready8
    tax
    lda.l SourceVisual_CandidateActionValid,x
    cmp #SOURCE_VISUAL_ACTION_STALE_FENCE
    bne SourceVisual_CandidateRetireStale__not_ready8
    lda.l SourceVisual_PacketCandidateOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_CandidateRetireStale__not_ready8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    beq SourceVisual_CandidateRetireStale__not_ready8
    rep #$31
.a16
.i16
    jsr SourceVisual_CandidateFenceComplete
    bcc SourceVisual_CandidateRetireStale__not_ready
    jsr SourceVisual_HasOwnedDma
    bcc SourceVisual_CandidateRetireStale__dma_idle
SourceVisual_CandidateRetireStale__not_ready:
    clc
    rts
SourceVisual_CandidateRetireStale__not_ready8:
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_CandidateRetireStale__dma_idle:
    jsr SourceVisual_ReleaseLoaderOwner
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #7
    sta.l SourceVisual_OwnerOffset
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes
    lda.l SourceVisual_CandidateBase
    tax
    lda #0
    ldy #16
SourceVisual_CandidateRetireStale__clear_sidecar:
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    dey
    bne SourceVisual_CandidateRetireStale__clear_sidecar
    sep #$20
.a8
    lda.l SourceVisual_PacketCandidateOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_CandidateRetireStale__restore_channel8
    lda #$FF
    sta.l SourceVisual_PacketCandidateOwner
    lda #0
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+1
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+2
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+3
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH+1
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH+2
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH+3
SourceVisual_CandidateRetireStale__restore_channel8:
    lda #0
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #4
    sta.l SourceVisual_OwnerOffset
    jsr SourceVisual_CandidateActionClear
    sec
    rts

; Copy only this actor's current published owner bits into the candidate lane.
; The content stays resident throughout the OAM fence, including blocks and
; palettes shared with other actors.
SourceVisual_PinCurrentLeaseCandidate:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_PinCurrentLeaseCandidate__block_mask:
.i16
    cpx #0
    beq SourceVisual_PinCurrentLeaseCandidate__block_mask_ready
    asl a
    dex
    bra SourceVisual_PinCurrentLeaseCandidate__block_mask
SourceVisual_PinCurrentLeaseCandidate__block_mask_ready:
    sep #$20
.a8
    sta.l SourceVisual_BlockActorMask
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockScan
SourceVisual_PinCurrentLeaseCandidate__block:
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcs SourceVisual_PinCurrentLeaseCandidate__palette_start
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    and.l SourceVisual_BlockActorMask
    beq SourceVisual_PinCurrentLeaseCandidate__block_next8
    lda.l SourceVisual_BlockCache+7,x
    ora.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache+7,x
SourceVisual_PinCurrentLeaseCandidate__block_next8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    bra SourceVisual_PinCurrentLeaseCandidate__block
SourceVisual_PinCurrentLeaseCandidate__palette_start:
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_PinCurrentLeaseCandidate__palette_mask:
.i16
    cpx #0
    beq SourceVisual_PinCurrentLeaseCandidate__palette_mask_ready
    asl a
    dex
    bra SourceVisual_PinCurrentLeaseCandidate__palette_mask
SourceVisual_PinCurrentLeaseCandidate__palette_mask_ready:
    sep #$20
.a8
    sta.l SourceVisual_PaletteOwnerBit
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_PaletteScan
SourceVisual_PinCurrentLeaseCandidate__palette:
    lda.l SourceVisual_PaletteScan
    cmp #8
    bcs SourceVisual_PinCurrentLeaseCandidate__done
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    and.l SourceVisual_PaletteOwnerBit
    beq SourceVisual_PinCurrentLeaseCandidate__palette_next8
    lda.l SourceVisual_PaletteCache+5,x
    ora.l SourceVisual_PaletteOwnerBit
    sta.l SourceVisual_PaletteCache+5,x
SourceVisual_PinCurrentLeaseCandidate__palette_next8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteScan
    inc a
    sta.l SourceVisual_PaletteScan
    bra SourceVisual_PinCurrentLeaseCandidate__palette
SourceVisual_PinCurrentLeaseCandidate__done:
    rts

; Roll back the extra owner lane if the first packet could not be emitted.
SourceVisual_AbortInitialPacket:
    ; Initial candidates have no published owner to preserve. Retire any
    ; completed reader descriptor and clear the entire candidate sidecar/meta
    ; so the next hook can admit the actor's new live key from a clean lane.
    jsr SourceVisual_ReleaseLoaderOwner
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #7
    sta.l SourceVisual_OwnerOffset
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes
    sep #$20
.a8
    lda.l SourceVisual_PacketCandidateOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_AbortInitialPacket__lane_done8
    lda #$FF
    sta.l SourceVisual_PacketCandidateOwner
    lda #0
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
SourceVisual_AbortInitialPacket__lane_done8:
    lda #0
    sta.l SourceVisual_UseCandidate
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidateBase
    tax
    lda #0
    ldy #16
SourceVisual_AbortInitialPacket__clear_sidecar:
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    dey
    bne SourceVisual_AbortInitialPacket__clear_sidecar
    ldx #0
    ldy #8
SourceVisual_AbortInitialPacket__clear_meta:
    sta.l SourceVisual_CandidatePacketMeta,x
    inx
    inx
    dey
    bne SourceVisual_AbortInitialPacket__clear_meta
    sep #$20
.a8
    lda #$FF
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_OWNER
    rep #$31
.a16
.i16
    jsr SourceVisual_CandidateActionClear
    lda #4
    sta.l SourceVisual_OwnerOffset
    rts

; Save candidate progress in its sidecar while the caller restores the
; published record from the stack.
SourceVisual_SaveCandidateSidecar:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    ldy #0
SourceVisual_SaveCandidateSidecar__copy:
    lda.l SourceVisual_State,x
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    iny
    iny
    cpy #32
    bcc SourceVisual_SaveCandidateSidecar__copy
    rts

; Published packet rows are tightly packed at 65*7 bytes per actor.
SourceVisual_GetPublishedPacketOffset:
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_PacketDataIndex
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_PacketSourceRow
SourceVisual_GetPublishedPacketOffset__loop:
    lda.l SourceVisual_PacketSourceRow
    beq SourceVisual_GetPublishedPacketOffset__done
    lda.l SourceVisual_PacketDataIndex
    clc
    adc #SOURCE_VISUAL_PACKET_ACTOR_BYTES
    sta.l SourceVisual_PacketDataIndex
    lda.l SourceVisual_PacketSourceRow
    dec a
    sta.l SourceVisual_PacketSourceRow
    bra SourceVisual_GetPublishedPacketOffset__loop
SourceVisual_GetPublishedPacketOffset__done:
    rts

; Called only after SourceVisual_Emit has returned success. Retire the old
; published lane, then move the candidate lane into it. Shared block/palette
; identities remain live because the candidate bit is set before the old bit
; is removed by the row-release helpers.
SourceVisual_CommitCandidate:
    rep #$31
.a16
.i16
    ; Copy the complete candidate geometry only after its exact OAM DMA fence
    ; was observed. Keep the candidate lane locked and valid until every byte
    ; and descriptor field has reached the published bank.
    jsr SourceVisual_GetPublishedPacketOffset
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_COUNT
    sta.l SourceVisual_PacketCount
    asl a
    asl a
    asl a
    sec
    sbc.l SourceVisual_PacketCount
    sta.l SourceVisual_PacketCopyCount
    lda #0
    sta.l SourceVisual_PacketTotal
    sep #$20
.a8
SourceVisual_CommitCandidate__copy_packet:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketTotal
    cmp.l SourceVisual_PacketCopyCount
    bcs SourceVisual_CommitCandidate__packet_copied
    lda.l SourceVisual_PacketTotal
    tax
    sep #$20
.a8
    lda.l SourceVisual_CandidatePacketData,x
    sta.l SourceVisual_PacketSpriteHigh
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketDataIndex
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketSpriteHigh
    sta.l SourceVisual_PacketData,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketDataIndex
    inc a
    sta.l SourceVisual_PacketDataIndex
    lda.l SourceVisual_PacketTotal
    inc a
    sta.l SourceVisual_PacketTotal
    bra SourceVisual_CommitCandidate__copy_packet
SourceVisual_CommitCandidate__packet_copied:
    rep #$31
.a16
.i16
    ; Copy left-facing authored offsets into the slot's sidecar before the
    ; packet metadata valid byte publishes this complete geometry generation.
    jsr SourceVisual_CopyCandidateLeftGeometry
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_COUNT
    sta.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_COUNT,x
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_WIDTH
    sta.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_WIDTH,x
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_ENTRY
    sta.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_ENTRY,x
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_COUNT
    beq SourceVisual_CommitCandidate__empty_packet
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    bra SourceVisual_CommitCandidate__packet_ready
SourceVisual_CommitCandidate__empty_packet:
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
SourceVisual_CommitCandidate__packet_ready:
    ; Persist the exact key represented by the newly committed packet. Lookup
    ; uses it to distinguish a real player pose change from a cached old pose.
    sep #$20
.a8
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    beq SourceVisual_CommitCandidate__clear_published_key8
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    tax
    lda.l SourceVisual_CandidateKey,x
    sta.l SourceVisual_PublishedKey,x
    lda.l SourceVisual_CandidateKey+2,x
    sta.l SourceVisual_PublishedKey+2,x
    brl SourceVisual_CommitCandidate__published_key_ready
SourceVisual_CommitCandidate__clear_published_key8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    tax
    lda #0
    sta.l SourceVisual_PublishedKey,x
    sta.l SourceVisual_PublishedKey+2,x
SourceVisual_CommitCandidate__published_key_ready:
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #4
    sta.l SourceVisual_OwnerOffset
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes

    ; Actor mask used by both cache transfer loops.
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_CommitCandidate__mask:
.i16
    cpx #0
    beq SourceVisual_CommitCandidate__mask_ready
    asl a
    dex
    bra SourceVisual_CommitCandidate__mask
SourceVisual_CommitCandidate__mask_ready:
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
SourceVisual_CommitCandidate__block:
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcs SourceVisual_CommitCandidate__palette_start
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+7,x
    and.l SourceVisual_BlockActorMask
    beq SourceVisual_CommitCandidate__block_next8
    lda.l SourceVisual_BlockCache+4,x
    ora.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache+4,x
    lda.l SourceVisual_BlockCache+7,x
    and.l SourceVisual_BlockOther2
    sta.l SourceVisual_BlockCache+7,x
SourceVisual_CommitCandidate__block_next8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    bra SourceVisual_CommitCandidate__block
SourceVisual_CommitCandidate__palette_start:
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_CommitCandidate__palette_mask:
.i16
    cpx #0
    beq SourceVisual_CommitCandidate__palette_mask_ready
    asl a
    dex
    bra SourceVisual_CommitCandidate__palette_mask
SourceVisual_CommitCandidate__palette_mask_ready:
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
SourceVisual_CommitCandidate__palette:
    lda.l SourceVisual_PaletteScan
    cmp #8
    bcs SourceVisual_CommitCandidate__done
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+5,x
    and.l SourceVisual_PaletteOwnerBit
    beq SourceVisual_CommitCandidate__palette_next8
    lda.l SourceVisual_PaletteCache+4,x
    ora.l SourceVisual_PaletteOwnerBit
    sta.l SourceVisual_PaletteCache+4,x
    lda.l SourceVisual_PaletteCache+5,x
    and.l SourceVisual_PaletteOwnerNotBit
    sta.l SourceVisual_PaletteCache+5,x
SourceVisual_CommitCandidate__palette_next8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteScan
    inc a
    sta.l SourceVisual_PaletteScan
    bra SourceVisual_CommitCandidate__palette
SourceVisual_CommitCandidate__done:
    lda.l SourceVisual_CandidateBase
    tax
    lda #0
    ldy #16
SourceVisual_CommitCandidate__clear:
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    dey
    bne SourceVisual_CommitCandidate__clear
    jsr SourceVisual_CandidateActionClear
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_OwnerChannel
    sta.l SourceVisual_UseCandidate
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    lda #$FF
    sta.l SourceVisual_PacketCandidateOwner
    rep #$31
.a16
.i16
    jsr SourceVisual_ReleaseLoaderOwner
    ; Preserve lease palette/resource fields in +16..+23 while clearing the
    ; transient row-valid flags in +24..+27.
    lda.l SourceVisual_Record
    tax
    lda #0
    ldy #2
SourceVisual_CommitCandidate__clear_read_stages:
    sta.l SourceVisual_State+24,x
    inx
    inx
    dey
    bne SourceVisual_CommitCandidate__clear_read_stages
    lda #4
    sta.l SourceVisual_OwnerOffset
    rts

; Return the published sidecar actor-base offset in PacketLeftBaseOffset and
; the 0..2 / 3..5 segment selector in PacketLeftGroup. Each actor row is
; exactly 65 * 4 = 260 bytes. The groups are deliberately split across the
; two checked free WRAM ranges documented above.
SourceVisual_GetPublishedLeftActorBase:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #3
    bcc SourceVisual_GetPublishedLeftActorBase__group012
    sec
    sbc #3
    sta.l SourceVisual_PacketLeftActorLocal
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_PacketLeftGroup
    rep #$31
.a16
.i16
    bra SourceVisual_GetPublishedLeftActorBase__offset
SourceVisual_GetPublishedLeftActorBase__group012:
    sta.l SourceVisual_PacketLeftActorLocal
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_PacketLeftGroup
    rep #$31
.a16
.i16
SourceVisual_GetPublishedLeftActorBase__offset:
    ; localActor * 260 = localActor * 256 + localActor * 4.
    lda.l SourceVisual_PacketLeftActorLocal
    asl a
    asl a
    sta.l SourceVisual_PacketLeftPieceOffset
    lda.l SourceVisual_PacketLeftActorLocal
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceVisual_PacketLeftPieceOffset
    sta.l SourceVisual_PacketLeftBaseOffset
    rts

; Copy all authored left-facing words alongside the candidate packet. The
; published PacketMeta valid byte is still zero, so no renderer can observe a
; mixed-generation sidecar; CommitCandidate sets valid only after this returns.
SourceVisual_CopyCandidateLeftGeometry:
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_PacketLeftCursor
    jsr SourceVisual_GetPublishedLeftActorBase
SourceVisual_CopyCandidateLeftGeometry__piece:
    lda.l SourceVisual_PacketLeftCursor
    cmp.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_COUNT
    bcs SourceVisual_CopyCandidateLeftGeometry__done
    asl a
    asl a
    sta.l SourceVisual_PacketLeftPieceOffset
    tax
    lda.l SourceVisual_CandidateLeftGeometry,x
    sta.l SourceVisual_PacketLeftX
    inx
    inx
    lda.l SourceVisual_CandidateLeftGeometry,x
    sta.l SourceVisual_PacketLeftY
    lda.l SourceVisual_PacketLeftBaseOffset
    clc
    adc.l SourceVisual_PacketLeftPieceOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketLeftGroup
    beq SourceVisual_CopyCandidateLeftGeometry__store012
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketLeftX
    sta.l SourceVisual_PublishedLeftGeometry345,x
    inx
    inx
    lda.l SourceVisual_PacketLeftY
    sta.l SourceVisual_PublishedLeftGeometry345,x
    bra SourceVisual_CopyCandidateLeftGeometry__next
SourceVisual_CopyCandidateLeftGeometry__store012:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketLeftX
    sta.l SourceVisual_PublishedLeftGeometry012,x
    inx
    inx
    lda.l SourceVisual_PacketLeftY
    sta.l SourceVisual_PublishedLeftGeometry012,x
SourceVisual_CopyCandidateLeftGeometry__next:
    lda.l SourceVisual_PacketLeftCursor
    inc a
    sta.l SourceVisual_PacketLeftCursor
    bra SourceVisual_CopyCandidateLeftGeometry__piece
SourceVisual_CopyCandidateLeftGeometry__done:
    rts

; Compose a left-facing cached piece from the published sidecar. This helper
; never reads candidate Entry/Width/PieceTable state, so a pending replacement
; cannot move the old published pose while the actor's world anchor is fixed.
SourceVisual_CachedLeftPosition:
    rep #$31
.a16
.i16
    jsr SourceVisual_GetPublishedLeftActorBase
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    clc
    adc.l SourceVisual_PacketLeftBaseOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketLeftGroup
    beq SourceVisual_CachedLeftPosition__load012
    rep #$31
.a16
.i16
    lda.l SourceVisual_PublishedLeftGeometry345,x
    sta.l SourceVisual_PacketSpriteRelX
    lda.l SourceVisual_PublishedLeftGeometry345+2,x
    sta.l SourceVisual_PacketDeltaY
    bra SourceVisual_CachedLeftPosition__compose
SourceVisual_CachedLeftPosition__load012:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PublishedLeftGeometry012,x
    sta.l SourceVisual_PacketSpriteRelX
    lda.l SourceVisual_PublishedLeftGeometry012+2,x
    sta.l SourceVisual_PacketDeltaY
SourceVisual_CachedLeftPosition__compose:
    lda.l SourceVisual_PacketAnchorX
    clc
    adc.l SourceVisual_PacketSpriteRelX
    sta.l SourceVisual_PacketSpriteX
    lda.l SourceVisual_PacketDrawY
    clc
    adc.l SourceVisual_PacketDeltaY
    sta.l SourceVisual_PacketSpriteY
    sec
    rts

SourceVisual_ResolveActorSlotFromContext:
    rep #$31
.a16
.i16
    tdc
    sec
    sbc #$0A00
    ldy #0
SourceVisual_ResolveActorSlotFromContext__scan:
    cmp #0
    beq SourceVisual_ResolveActorSlotFromContext__found
    sec
    sbc #CHAR_ZP_LEN
    bcc SourceVisual_ResolveActorSlotFromContext__bad
    iny
    cpy #6
    bcc SourceVisual_ResolveActorSlotFromContext__scan
SourceVisual_ResolveActorSlotFromContext__bad:
    lda #0
    sta.l SourceVisual_ActorSlot
    rts
SourceVisual_ResolveActorSlotFromContext__found:
    tya
    sta.l SourceVisual_ActorSlot
    rts

SourceVisual_MarkActorForOamRetire:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_MarkActorForOamRetire__shift:
.i16
    cpx #0
    beq SourceVisual_MarkActorForOamRetire__bit
    asl a
    dex
    bra SourceVisual_MarkActorForOamRetire__shift
SourceVisual_MarkActorForOamRetire__bit:
    ora.l SourceVisual_OamRetireMask
    sta.l SourceVisual_OamRetireMask
    rts

; Initialize the bounded packet cache before the first frame can observe it.
; Packet bytes are not trusted until the metadata row's valid byte is set by
; an NMI that completed the matching main-OAM DMA generation.
SourceVisual_InitPackets:
    rep #$31
.a16
.i16
    lda #$FFFF
    sta.l SourceVisual_PresentationField
    sta.l SourceVisual_RowScratchBlockIndex
    lda #0
    sta.l SourceVisual_OamRetireMask
    sta.l SourceVisual_CommitMask
    sep #$20
.a8
    lda #$FF
    sta.l SourceVisual_PacketCandidateOwner
    sta.l SourceVisual_LoaderOwner
    sta.l SourceVisual_ReadOwner
    sta.l SourceVisual_EntryReadySlot
    sta.l SourceVisual_PieceTableOwner
    sta.l SourceVisual_CatalogBindOwner
    lda #0
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    sta.l SourceVisual_OamFenceCompletedValid
    sta.l SourceVisual_ReadState
    sta.l SourceVisual_LoaderDurableProgress
    sta.l SourceVisual_PreflightState
    sta.l SourceVisual_FindScanActive
    sta.l SourceVisual_EntryReady
    sta.l SourceVisual_PieceTableValid
    sta.l SourceVisual_RowScratchBlockValid
    sta.l SourceVisual_LoaderEntryValid
    sta.l SourceVisual_PublishedFastPath
    sta.l SourceVisual_CatalogBindState
    ; $7E2330 aliases boot-time BgHeaderStaging. Initialize the runtime
    ; stream gate explicitly after staging and before any live reader starts.
    lda #0
    sta.l Msu1_StreamBusy
    sta.l SourceVisual_ReadTurnUsed
    sta.l SourceVisual_WorkRemaining
    sta.l SourceVisual_WorkRemaining+1
    rep #$31
.a16
.i16
    lda #$FFFF
    sta.l SourceVisual_PieceTableEntry
    sta.l SourceVisual_EntryReadyIndex
    ldx #0
    lda #0
SourceVisual_InitPackets__clear_published_keys:
    sta.l SourceVisual_PublishedKey,x
    inx
    inx
    cpx #24
    bcc SourceVisual_InitPackets__clear_published_keys
    sep #$20
.a8
    lda #$FF
    sta.l SourceVisual_PlayerPriorityOwner
    lda #0
    sta.l SourceVisual_WaitingActorMask
    lda #5
    sta.l SourceVisual_QueueCursor
    rep #$31
.a16
.i16
    ldx #0
    lda #0
SourceVisual_InitPackets__clear_cache:
    sta.l SourceVisual_PacketMeta,x
    sta.l SourceVisual_FrameMeta,x
    inx
    inx
    cpx #6 * SOURCE_VISUAL_PACKET_META_STRIDE
    bcc SourceVisual_InitPackets__clear_cache
    ldx #0
SourceVisual_InitPackets__clear_candidate_state:
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    cpx #6 * 32
    bcc SourceVisual_InitPackets__clear_candidate_state
    ldx #0
    lda #0
SourceVisual_InitPackets__clear_candidate_keys:
    sta.l SourceVisual_CandidateKey,x
    inx
    inx
    cpx #6 * 4
    bcc SourceVisual_InitPackets__clear_candidate_keys
    ldx #0
    lda #0
SourceVisual_InitPackets__clear_candidate_action_valid:
    sta.l SourceVisual_CandidateActionValid,x
    inx
    inx
    cpx #6
    bcc SourceVisual_InitPackets__clear_candidate_action_valid
    rtl

; Start one compositor pass.  This must run before Character_RenderPass walks
; actors; clearing from RenderCurrent loses earlier actors' candidate marks
; when the NMI field counter advances between two actor calls.
SourceVisual_BeginRenderPass:
    php
    rep #$31
.a16
.i16
    lda.l Nmi_FrameCounter
    sta.l SourceVisual_PresentationField
    lda #0
    sta.l SourceVisual_PresentationMask
    jsr SourceVisual_ClearFramePacketMeta
    plp
    rtl

SourceVisual_ClearFramePacketMeta:
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_CommitMask
    ldx #0
SourceVisual_ClearFramePacketMeta__loop:
    sta.l SourceVisual_FrameMeta,x
    inx
    inx
    cpx #6 * SOURCE_VISUAL_PACKET_META_STRIDE
    bcc SourceVisual_ClearFramePacketMeta__loop
    rts

; FrameMeta records source actors that participated in this render pass. It is
; not a clipped sprite cache; complete authored geometry is kept separately.
SourceVisual_SetFramePacketIdentity:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_FrameMeta+SOURCE_VISUAL_PACKET_META_ENTRY,x
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_FrameMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    rep #$31
.a16
.i16
    rts

; Mark this actor present in the current field; packet geometry is authored
; and cached independently of viewport clipping.
SourceVisual_RecordFramePacket:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_FrameMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    rep #$31
.a16
.i16
    rts

SourceVisual_MarkCandidateFence:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_MarkCandidateFence__shift:
.i16
    cpx #0
    beq SourceVisual_MarkCandidateFence__ready
    asl a
    dex
    bra SourceVisual_MarkCandidateFence__shift
SourceVisual_MarkCandidateFence__ready:
    ora.l SourceVisual_CommitMask
    sta.l SourceVisual_CommitMask
    rts

; C=true only when the single admitted candidate's exact (epoch,sequence)
; OAM token completed. The version byte makes this multiword snapshot stable
; if NMI publishes another completion between S-CPU reads.
SourceVisual_CandidateFenceComplete:
    sep #$20
.a8
    lda.l SourceVisual_OamFenceCompletedValid
    beq SourceVisual_CandidateFenceComplete__no
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    beq SourceVisual_CandidateFenceComplete__no
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_OWNER
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_CandidateFenceComplete__no
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE
    ora.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+2
    beq SourceVisual_CandidateFenceComplete__no
    ; Capture the version as one byte before reading the completion record.
    ; NMI is non-nesting, so one completion changes this byte exactly once
    ; between these reads; even 8-bit wrap cannot hide one intervening update.
    sep #$20
.a8
    lda.l SourceVisual_OamFenceCompletionVersion
    pha
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE
    cmp.l SourceVisual_OamFenceCompleted
    bne SourceVisual_CandidateFenceComplete__snapshot_no
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+2
    cmp.l SourceVisual_OamFenceCompleted+2
    bne SourceVisual_CandidateFenceComplete__snapshot_no
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH
    cmp.l SourceVisual_OamFenceCompletedEpoch
    bne SourceVisual_CandidateFenceComplete__snapshot_no
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH+2
    cmp.l SourceVisual_OamFenceCompletedEpoch+2
    bne SourceVisual_CandidateFenceComplete__snapshot_no
    sep #$20
.a8
    pla
    cmp.l SourceVisual_OamFenceCompletionVersion
    bne SourceVisual_CandidateFenceComplete__no
    rep #$31
.a16
.i16
SourceVisual_CandidateFenceComplete__yes:
    sec
    rts
SourceVisual_CandidateFenceComplete__snapshot_no:
    sep #$20
.a8
    pla
    rep #$31
.a16
.i16
SourceVisual_CandidateFenceComplete__no:
    rep #$31
.a16
.i16
    clc
    rts

; Bind only candidates actually emitted in this OAM composition to the token
; stamped on Core_Oam_Play's main-table queue descriptor.
SourceVisual_BindCandidateFence:
    php
    pha
    phx
    phy
    rep #$31
.a16
.i16
    lda.l SourceVisual_CommitMask
    sta.l SourceVisual_PacketCount
    lda #0
    sta.l SourceVisual_PacketSourceRow
SourceVisual_BindCandidateFence__scan:
    lda.l SourceVisual_PacketSourceRow
    cmp #6
    bcs SourceVisual_BindCandidateFence__done
    lda.l SourceVisual_PacketCount
    and #1
    beq SourceVisual_BindCandidateFence__next
    lda.l SourceVisual_PacketSourceRow
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_CandidateState+30,x
    cmp #3
    bne SourceVisual_BindCandidateFence__next8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    beq SourceVisual_BindCandidateFence__next8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_OWNER
    cmp.l SourceVisual_PacketSourceRow
    bne SourceVisual_BindCandidateFence__next8
    rep #$31
.a16
.i16
    lda.l SourceVisual_OamFenceSubmitted
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE
    lda.l SourceVisual_OamFenceSubmitted+2
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+2
    lda.l SourceVisual_OamFenceSubmittedEpoch
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH
    lda.l SourceVisual_OamFenceSubmittedEpoch+2
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH+2
    sep #$20
.a8
SourceVisual_BindCandidateFence__next8:
    rep #$31
.a16
.i16
SourceVisual_BindCandidateFence__next:
    lda.l SourceVisual_PacketCount
    lsr a
    sta.l SourceVisual_PacketCount
    lda.l SourceVisual_PacketSourceRow
    inc a
    sta.l SourceVisual_PacketSourceRow
    bra SourceVisual_BindCandidateFence__scan
SourceVisual_BindCandidateFence__done:
    .a16
    .i16
    rep #$31
    lda #0
    sta.l SourceVisual_CommitMask
    ply
    plx
    pla
    plp
    rtl

; Re-emit the last committed actor slice from WRAM. No MSU seek, catalog read,
; piece-table rebuild, or residency-map walk occurs on this path. Coordinates
; follow the actor's current anchor; packet data is copied atomically only
; after the complete slice passes cache and OAM-capacity checks.
; Re-emit the complete published authored packet from WRAM. It contains every
; piece, including pieces clipped in the original publication. Position and
; facing are resolved from the live actor while tile/palette references remain
; protected by the published owner lane.
SourceVisual_EmitCachedPacket:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    bne SourceVisual_EmitCachedPacket__packet_valid
    brl SourceVisual_EmitCachedPacket__fail8
SourceVisual_EmitCachedPacket__packet_valid:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_COUNT,x
    bne SourceVisual_EmitCachedPacket__has_pieces
    brl SourceVisual_EmitCachedPacket__fail
SourceVisual_EmitCachedPacket__has_pieces:
    cmp #SOURCE_VISUAL_MAX_PIECES+1
    bcc SourceVisual_EmitCachedPacket__count_ok
    brl SourceVisual_EmitCachedPacket__fail
SourceVisual_EmitCachedPacket__count_ok:
    sta.l SourceVisual_PacketCount
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_WIDTH,x
    sta.l SourceVisual_PacketOldWidth
    jsr SourceVisual_GetPublishedPacketOffset
    lda.l SourceVisual_PacketDataIndex
    sta.l SourceVisual_PacketStart
    lda CHAR_POS_X
    sec
    sbc Screen_PosX
    sta.l SourceVisual_PacketAnchorX
    lda CHAR_POS_Y
    sta.l SourceVisual_PacketActorY
    sta.l SourceVisual_PacketDrawY
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_EmitBoundsMode
    rep #$31
.a16
.i16
    jsl StageBoundsHost_Normal
    bcc SourceVisual_EmitCachedPacket__anchor_ready
    jsl StageBounds_Row
    sep #$20
.a8
    lda.l StageBounds_State,x
    cmp #2
    bne SourceVisual_EmitCachedPacket__bounds_not_hidden
    brl SourceVisual_EmitCachedPacket__fail8
SourceVisual_EmitCachedPacket__bounds_not_hidden:
    cmp #0
    beq SourceVisual_EmitCachedPacket__anchor_ready8
    rep #$31
.a16
.i16
    lda.l StageBounds_DrawY,x
    cmp #240
    bcc SourceVisual_EmitCachedPacket__draw_y_ok
    brl SourceVisual_EmitCachedPacket__fail
SourceVisual_EmitCachedPacket__draw_y_ok:
    sta.l SourceVisual_PacketDrawY
    lda #1
    sta.l SourceVisual_EmitBoundsMode
    bra SourceVisual_EmitCachedPacket__anchor_ready
SourceVisual_EmitCachedPacket__anchor_ready8:
    rep #$31
.a16
.i16
SourceVisual_EmitCachedPacket__anchor_ready:
    ; Normal actors keep the authored OBJ priority; falling actors use the
    ; same behind-panel priority mask as the live emitter.
    lda.l Oam_CurrentSlot
    sta.l SourceVisual_EmitOamStart
    lda #0
    sta.l SourceVisual_VisiblePieces
    sta.l SourceVisual_PieceIndex
    ; Avoid the visibility-count pass when the worst case (every authored
    ; piece, plus its stage mirror if enabled) fits in the remaining OAM.
    ; If it does not fit, retain the exact clipped-piece preflight below.
    lda.l Stage_Mirror
    and #$00FF
    beq SourceVisual_EmitCachedPacket__fast_unmirrored
    lda.l SourceVisual_PacketCount
    asl a
    bra SourceVisual_EmitCachedPacket__fast_size
SourceVisual_EmitCachedPacket__fast_unmirrored:
    lda.l SourceVisual_PacketCount
SourceVisual_EmitCachedPacket__fast_size:
    asl a
    asl a
    clc
    adc.l Oam_CurrentSlot
    cmp #513
    bcc SourceVisual_EmitCachedPacket__fast_emit
    brl SourceVisual_EmitCachedPacket__count_loop
SourceVisual_EmitCachedPacket__fast_emit:
    brl SourceVisual_EmitCachedPacket__emit_start
SourceVisual_EmitCachedPacket__count_loop:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PacketCount
    bcs SourceVisual_EmitCachedPacket__capacity
    jsr SourceVisual_CachedNormalPosition
    bcc SourceVisual_EmitCachedPacket__count_mirror
    lda.l SourceVisual_VisiblePieces
    inc a
    sta.l SourceVisual_VisiblePieces
SourceVisual_EmitCachedPacket__count_mirror:
    lda.l Stage_Mirror
    and #$00FF
    beq SourceVisual_EmitCachedPacket__count_next
    jsr SourceVisual_CachedMirrorPosition
    bcc SourceVisual_EmitCachedPacket__count_next
    lda.l SourceVisual_VisiblePieces
    inc a
    sta.l SourceVisual_VisiblePieces
SourceVisual_EmitCachedPacket__count_next:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    brl SourceVisual_EmitCachedPacket__count_loop
SourceVisual_EmitCachedPacket__capacity:
    lda.l SourceVisual_VisiblePieces
    asl a
    asl a
    clc
    adc.l Oam_CurrentSlot
    cmp #513
    bcc SourceVisual_EmitCachedPacket__emit_start
    brl SourceVisual_EmitCachedPacket__fail
SourceVisual_EmitCachedPacket__emit_start:
    lda #0
    sta.l SourceVisual_PieceIndex
SourceVisual_EmitCachedPacket__emit_loop:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PacketCount
    bcs SourceVisual_EmitCachedPacket__emitted
    jsr SourceVisual_CachedNormalPosition
    bcc SourceVisual_EmitCachedPacket__emit_mirror
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_PacketDirectionChanged
    rep #$31
.a16
.i16
    jsr SourceVisual_WriteCachedPiece
SourceVisual_EmitCachedPacket__emit_mirror:
    lda.l Stage_Mirror
    and #$00FF
    beq SourceVisual_EmitCachedPacket__emit_next
    jsr SourceVisual_CachedMirrorPosition
    bcc SourceVisual_EmitCachedPacket__emit_next
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_PacketDirectionChanged
    rep #$31
.a16
.i16
    jsr SourceVisual_WriteCachedPiece
SourceVisual_EmitCachedPacket__emit_next:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    brl SourceVisual_EmitCachedPacket__emit_loop
SourceVisual_EmitCachedPacket__emitted:
    lda CHAR_POS_X
    sec
    sbc Screen_PosX
    sta.l SourceVisual_EmitBaseX
    lda.l SourceVisual_PacketDrawY
    sta.l SourceVisual_EmitBaseY
    lda.l SourceVisual_PacketActorY
    sta.l SourceVisual_EmitActorY
    lda.l SourceVisual_PacketOldWidth
    sta.l SourceVisual_EmitFrameWidth
    jsr SourceVisual_RecordFramePacket
    sec
    rts
SourceVisual_EmitCachedPacket__fail8:
    rep #$31
.a16
.i16
SourceVisual_EmitCachedPacket__fail:
    clc
    rts

; Load one 7-byte published descriptor and calculate its live normal position.
; C reports viewport intersection; all scratch remains relative to actor.
SourceVisual_CachedNormalPosition:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceIndex
    sta.l SourceVisual_PacketCopyCount
    asl a
    asl a
    asl a
    sec
    sbc.l SourceVisual_PacketCopyCount
    clc
    adc.l SourceVisual_PacketStart
    sta.l SourceVisual_PacketDataIndex
    tax
    lda.l SourceVisual_PacketData,x
    sta.l SourceVisual_PacketSpriteRelX
    inx
    inx
    lda.l SourceVisual_PacketData,x
    sta.l SourceVisual_PacketDeltaY
    sep #$20
.a8
    lda.l SourceVisual_PacketData+2,x
    sta.l SourceVisual_PacketCopyByte
    lda.l SourceVisual_PacketData+3,x
    sta.l SourceVisual_PacketSpriteAttr
    lda.l SourceVisual_PacketData+4,x
    sta.l SourceVisual_PacketSpriteHigh
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketSpriteHigh
    and #2
    beq SourceVisual_CachedNormalPosition__small
    lda #32
    sta.l SourceVisual_EmitPieceWidth
    lda #64
    bra SourceVisual_CachedNormalPosition__height
SourceVisual_CachedNormalPosition__small:
    lda #16
    sta.l SourceVisual_EmitPieceWidth
    lda #32
SourceVisual_CachedNormalPosition__height:
    sta.l SourceVisual_EmitPieceHeight
    sep #$20
.a8
    lda CHAR_FACING_LEFT
    beq SourceVisual_CachedNormalPosition__right
    rep #$31
.a16
.i16
    jsr SourceVisual_CachedLeftPosition
    bra SourceVisual_CachedNormalPosition__position_ready
SourceVisual_CachedNormalPosition__right:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketAnchorX
    clc
    adc.l SourceVisual_PacketSpriteRelX
    sta.l SourceVisual_PacketSpriteX
    lda.l SourceVisual_PacketDrawY
    clc
    adc.l SourceVisual_PacketDeltaY
    sta.l SourceVisual_PacketSpriteY
SourceVisual_CachedNormalPosition__position_ready:
    ; X interval must intersect [0,256).
    lda.l SourceVisual_PacketSpriteX
    bmi SourceVisual_CachedNormalPosition__x_end
    cmp #256
    bcs SourceVisual_CachedNormalPosition__outside
SourceVisual_CachedNormalPosition__x_end:
    clc
    adc.l SourceVisual_EmitPieceWidth
    bmi SourceVisual_CachedNormalPosition__outside
    beq SourceVisual_CachedNormalPosition__outside
    ; Y interval must intersect [0,224).
    lda.l SourceVisual_PacketSpriteY
    bmi SourceVisual_CachedNormalPosition__y_end
    cmp #224
    bcs SourceVisual_CachedNormalPosition__outside
SourceVisual_CachedNormalPosition__y_end:
    clc
    adc.l SourceVisual_EmitPieceHeight
    bmi SourceVisual_CachedNormalPosition__outside
    beq SourceVisual_CachedNormalPosition__outside
    sec
    rts
SourceVisual_CachedNormalPosition__outside:
    clc
    rts

; Mirror output reuses normal X/size and recomputes only reflected screen Y.
SourceVisual_CachedMirrorPosition:
    jsr SourceVisual_CachedNormalPosition
    lda.l SourceVisual_PacketDeltaY
    clc
    adc #248
    sec
    sbc CHAR_POS_Y
    sta.l SourceVisual_PacketSpriteY
    lda.l SourceVisual_PacketSpriteX
    bmi SourceVisual_CachedMirrorPosition__x_end
    cmp #256
    bcs SourceVisual_CachedMirrorPosition__outside
SourceVisual_CachedMirrorPosition__x_end:
    clc
    adc.l SourceVisual_EmitPieceWidth
    bmi SourceVisual_CachedMirrorPosition__outside
    beq SourceVisual_CachedMirrorPosition__outside
    lda.l SourceVisual_PacketSpriteY
    bmi SourceVisual_CachedMirrorPosition__y_end
    cmp #224
    bcs SourceVisual_CachedMirrorPosition__outside
SourceVisual_CachedMirrorPosition__y_end:
    clc
    adc.l SourceVisual_EmitPieceHeight
    bmi SourceVisual_CachedMirrorPosition__outside
    beq SourceVisual_CachedMirrorPosition__outside
    sec
    rts
SourceVisual_CachedMirrorPosition__outside:
    clc
    rts

SourceVisual_WriteCachedPiece:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketSpriteX
    sta.l SourceVisual_EmitPieceX
    lda.l SourceVisual_PacketSpriteY
    sta.l SourceVisual_EmitPieceY
    sep #$20
.a8
    lda.l SourceVisual_PacketCopyByte
    sta OamSetSprite_Tile
    lda.l SourceVisual_PacketSpriteAttr
    sta OamSetSprite_Attr
    lda CHAR_FACING_LEFT
    beq SourceVisual_WriteCachedPiece__facing_ready
    lda OamSetSprite_Attr
    eor #$40
    sta OamSetSprite_Attr
SourceVisual_WriteCachedPiece__facing_ready:
    lda.l SourceVisual_EmitBoundsMode
    beq SourceVisual_WriteCachedPiece__mirror
    lda OamSetSprite_Attr
    and #$CF
    sta OamSetSprite_Attr
SourceVisual_WriteCachedPiece__mirror:
    lda.l SourceVisual_PacketDirectionChanged
    beq SourceVisual_WriteCachedPiece__attr_ready
    lda OamSetSprite_Attr
    and #$CF
    ora #$20
    sta OamSetSprite_Attr
SourceVisual_WriteCachedPiece__attr_ready:
    lda.l SourceVisual_PacketSpriteHigh
    and #2
    sta OamSetSprite_Hi
    rep #$20
.a16
    lda.l SourceVisual_PacketSpriteX
    and #$0100
    beq SourceVisual_WriteCachedPiece__xhi_ready
    sep #$20
.a8
    lda.l OamSetSprite_Hi
    ora #1
    sta OamSetSprite_Hi
SourceVisual_WriteCachedPiece__xhi_ready:
    sep #$20
.a8
    lda.l SourceVisual_PacketDirectionChanged
    beq SourceVisual_WriteCachedPiece__normal_hi
    lda.l OamSetSprite_Hi
    ora #$80
    sta OamSetSprite_Hi
SourceVisual_WriteCachedPiece__normal_hi:
    rep #$31
.a16
.i16
    jsr SourceVisual_WriteCurrentPiece
    rts
; NMI hook after Core_Dma_ProcessQueue. The DMA queue records the exact wide
; OAM sequence; this hook only retires actors whose hidden OAM was transferred.
; Candidate packet promotion stays on SCPU so vblank work remains bounded.
SourceVisual_OnOamComplete:
    php
    phb
    phd
    pha
    phx
    phy
    sep #$20
.a8
    lda.l SourceVisual_OamFenceCompletedValid
    bne SourceVisual_OnOamComplete__has_fence
    brl SourceVisual_OnOamComplete__done8
SourceVisual_OnOamComplete__has_fence:
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_RetireScan
SourceVisual_OnOamComplete__actor:
    lda.l SourceVisual_RetireScan
    cmp #6
    bcc SourceVisual_OnOamComplete__actor_valid
    brl SourceVisual_OnOamComplete__done
SourceVisual_OnOamComplete__actor_valid:
    tay
    lda #1
SourceVisual_OnOamComplete__mask:
.i16
    cpy #0
    beq SourceVisual_OnOamComplete__mask_ready
    asl a
    dey
    bra SourceVisual_OnOamComplete__mask
SourceVisual_OnOamComplete__mask_ready:
    and.l SourceVisual_OamRetireMask
    beq SourceVisual_OnOamComplete__next
    lda.l SourceVisual_RetireScan
    sta.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Record
    sta.l SourceVisual_CandidateBase
    jsr SourceVisual_ReleaseActorOwnership
    jsr SourceVisual_ClearActorVisualRows
    ; Invalidate the full authored packet after the hardware OAM transfer.
    lda.l SourceVisual_RetireScan
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    sta.l SourceVisual_FrameMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    lda.l SourceVisual_PacketCandidateOwner
    cmp.l SourceVisual_RetireScan
    bne SourceVisual_OnOamComplete__clear_retire8
    lda #$FF
    sta.l SourceVisual_PacketCandidateOwner
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
SourceVisual_OnOamComplete__clear_retire8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_RetireScan
    tay
    lda #1
SourceVisual_OnOamComplete__clear_shift:
.i16
    cpy #0
    beq SourceVisual_OnOamComplete__clear_bit
    asl a
    dey
    bra SourceVisual_OnOamComplete__clear_shift
SourceVisual_OnOamComplete__clear_bit:
    eor #$FFFF
    and.l SourceVisual_OamRetireMask
    sta.l SourceVisual_OamRetireMask
SourceVisual_OnOamComplete__next:
    lda.l SourceVisual_RetireScan
    inc a
    sta.l SourceVisual_RetireScan
    brl SourceVisual_OnOamComplete__actor
SourceVisual_OnOamComplete__done8:
    rep #$31
.a16
.i16
SourceVisual_OnOamComplete__done:
    ply
    plx
    pla
    pld
    plb
    plp
    rtl
SourceVisual_ClearActorVisualRows:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda #0
    ldy #16
SourceVisual_ClearActorVisualRows__primary:
    sta.l SourceVisual_State,x
    inx
    inx
    dey
    bne SourceVisual_ClearActorVisualRows__primary
    lda.l SourceVisual_CandidateBase
    tax
    lda #0
    ldy #16
SourceVisual_ClearActorVisualRows__candidate:
    sta.l SourceVisual_CandidateState,x
    inx
    inx
    dey
    bne SourceVisual_ClearActorVisualRows__candidate
    jsr SourceVisual_CandidateActionClear
    rts

SourceVisual_ClearPublishedVisualRow:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda #0
    ldy #16
SourceVisual_ClearPublishedVisualRow__loop:
    sta.l SourceVisual_State,x
    inx
    inx
    dey
    bne SourceVisual_ClearPublishedVisualRow__loop
    rts

SourceVisual_EmitPublishedPacket:
    rep #$31
.a16
.i16
    jsr SourceVisual_EmitCachedPacket
    bcs SourceVisual_EmitPublishedPacket__emitted
    clc
    rts
SourceVisual_EmitPublishedPacket__emitted:
    ; A stale submitted candidate is retired only after a second, exact OAM
    ; fence for the old published fallback. Mark that fence once; rebinding on
    ; each redraw would continuously move the retirement target.
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcs SourceVisual_EmitPublishedPacket__done
    tax
    sep #$20
.a8
    lda.l SourceVisual_CandidateActionValid,x
    cmp #SOURCE_VISUAL_ACTION_STALE_FENCE
    bne SourceVisual_EmitPublishedPacket__done8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    beq SourceVisual_EmitPublishedPacket__done8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_OWNER
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_EmitPublishedPacket__done8
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE
    ora.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+2
    ora.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH
    ora.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_EPOCH+2
    bne SourceVisual_EmitPublishedPacket__done
    jsr SourceVisual_MarkCandidateFence
    brl SourceVisual_EmitPublishedPacket__done
SourceVisual_EmitPublishedPacket__done8:
    rep #$31
.a16
.i16
SourceVisual_EmitPublishedPacket__done:
    sec
    rts
SourceVisual_EmitPublishedPacket__fail:
    clc
    rts

; Map every visible old piece to a ready content block. The published owner
; bit is added before a newly exposed ready block is referenced, so candidate
; retirement cannot reclaim it prematurely. Any missing/not-ready visible
; block means a published lease was evicted or corrupted and fails closed.
SourceVisual_RebuildPublishedMap:
    rep #$31
.a16
.i16
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
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_RebuildPublishedMap__mask:
.i16
    cpx #0
    beq SourceVisual_RebuildPublishedMap__mask_ready
    asl a
    dex
    bra SourceVisual_RebuildPublishedMap__mask
SourceVisual_RebuildPublishedMap__mask_ready:
    sep #$20
.a8
    sta.l SourceVisual_BlockActorMask
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_PieceIndex
SourceVisual_RebuildPublishedMap__piece:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcs SourceVisual_RebuildPublishedMap__done
    jsr SourceVisual_ViewportPiece
    bcc SourceVisual_RebuildPublishedMap__next
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+12,x
    sta.l SourceVisual_BlockIndex
    jsr SourceVisual_FindBlock
    bcc SourceVisual_RebuildPublishedMap__missing
    lda.l SourceVisual_BlockRecord
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceVisual_RebuildPublishedMap__missing
    ; Pin this visible old reference before mapping its physical tile slot.
    lda.l SourceVisual_BlockRecord
    clc
    adc.l SourceVisual_OwnerOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache,x
    ora.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache,x
    rep #$31
.a16
.i16
    jsr SourceVisual_MapCurrentPiece
    bra SourceVisual_RebuildPublishedMap__next
SourceVisual_RebuildPublishedMap__missing:
    sep #$20
.a8
    lda #SOURCE_VISUAL_ERROR_PUBLISHED_NOT_RESIDENT
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_RebuildPublishedMap__next:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    bra SourceVisual_RebuildPublishedMap__piece
SourceVisual_RebuildPublishedMap__done:
    sec
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
    sep #$20
.a8
    ; EntryScratch is one global row. The per-actor historical flag cannot
    ; prove that this actor still owns its bytes, so validate the current
    ; completed-read slot/index on every use.
SourceVisual_LoadPendingEntry__check_ready8:
    lda.l SourceVisual_EntryReady
    cmp #1
    bne SourceVisual_LoadPendingEntry__read8
    lda.l SourceVisual_EntryReadySlot
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_LoadPendingEntry__read8
    rep #$31
.a16
.i16
    lda.l SourceVisual_EntryReadyIndex
    cmp.l SourceVisual_EntryIndexSaved
    bne SourceVisual_LoadPendingEntry__read
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+SOURCE_VISUAL_STATE_ENTRY_ROW_VALID,x
    bra SourceVisual_LoadPendingEntry__loaded8
SourceVisual_LoadPendingEntry__read8:
    rep #$31
.a16
.i16
SourceVisual_LoadPendingEntry__read:
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
    bcs SourceVisual_LoadPendingEntry__read_complete
    rts
SourceVisual_LoadPendingEntry__read_complete:
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+SOURCE_VISUAL_STATE_ENTRY_ROW_VALID,x
SourceVisual_LoadPendingEntry__loaded8:
    rep #$31
.a16
.i16
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
    pha
    sep #$20
.a8
    eor #$FF
    and.l SourceVisual_RetireMask
    sta.l SourceVisual_RetireMask
    rep #$20
.a16
    pla
.i16
    eor #$FFFF
    and.l SourceVisual_OamRetireMask
    sta.l SourceVisual_OamRetireMask
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
    pha
    sep #$20
.a8
    ora.l SourceVisual_RetireMask
    sta.l SourceVisual_RetireMask
    rep #$20
.a16
    pla
    ora.l SourceVisual_OamRetireMask
    sta.l SourceVisual_OamRetireMask
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
    bcc SourceVisual_ProcessRetired__scan_actor
    brl SourceVisual_ProcessRetired__restore
SourceVisual_ProcessRetired__scan_actor:
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
    sep #$20
.a8
    lda.l SourceVisual_LoaderOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_ProcessRetired__reader_done8
    rep #$31
.a16
.i16
    jsr SourceVisual_ReleaseLoaderOwner
    bra SourceVisual_ProcessRetired__reader_done
SourceVisual_ProcessRetired__reader_done8:
    rep #$31
.a16
.i16
SourceVisual_ProcessRetired__reader_done:
    lda.l SourceVisual_RetireBit
    and #$00FF
    ora.l SourceVisual_OamRetireMask
    sta.l SourceVisual_OamRetireMask
    sep #$20
.a8
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
    brl SourceVisual_ProcessRetired__scan
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

; Release only the selected published/candidate owner channel. Cache rows are
; reclaimed only when neither channel (nor another actor) still references it.
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
    txa
    sta.l SourceVisual_BlockRecord
    clc
    adc.l SourceVisual_OwnerOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache,x
    and.l SourceVisual_BlockOther2
    sta.l SourceVisual_BlockCache,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    ora.l SourceVisual_BlockCache+7,x
    bne SourceVisual_ReleaseActorBlocks__next8
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockCache+2,x
    sta.l SourceVisual_BlockCache+6,x
SourceVisual_ReleaseActorBlocks__next8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    bra SourceVisual_ReleaseActorBlocks__scan
SourceVisual_ReleaseActorBlocks__done:
    rts

; Drop this actor's selected reference to an exact, globally deduplicated
; CGRAM palette. Palette rows remain reserved while either owner channel lives.
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
    lda.l SourceVisual_OwnerChannel
    beq SourceVisual_ReleaseActorPalettes__published
    lda.l SourceVisual_PaletteCache+5,x
    and.l SourceVisual_PaletteOwnerNotBit
    sta.l SourceVisual_PaletteCache+5,x
    bra SourceVisual_ReleaseActorPalettes__check_owners
SourceVisual_ReleaseActorPalettes__published:
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    and.l SourceVisual_PaletteOwnerNotBit
    sta.l SourceVisual_PaletteCache+4,x
SourceVisual_ReleaseActorPalettes__check_owners:
    lda.l SourceVisual_PaletteCache+4,x
    ora.l SourceVisual_PaletteCache+5,x
    bne SourceVisual_ReleaseActorPalettes__next
    lda #0
    sta.l SourceVisual_PaletteCache+3,x
    rep #$20
.a16
    lda #0
    sta.l SourceVisual_PaletteCache,x
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

; Lifecycle replacement/despawn releases both channels after the DMA fence.
SourceVisual_ReleaseActorOwnership:
    rep #$31
.a16
.i16
    lda.l SourceVisual_OwnerChannel
    pha
    lda.l SourceVisual_OwnerOffset
    pha
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #4
    sta.l SourceVisual_OwnerOffset
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_OwnerChannel
    rep #$31
.a16
.i16
    lda #7
    sta.l SourceVisual_OwnerOffset
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes
    pla
    sta.l SourceVisual_OwnerOffset
    pla
    sta.l SourceVisual_OwnerChannel
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
    sep #$20
.a8
    lda.l SourceVisual_OwnerChannel
    beq SourceVisual_ValidatePaletteMap__published_owner
    lda.l SourceVisual_PaletteCache+5,x
    bra SourceVisual_ValidatePaletteMap__owner_test
SourceVisual_ValidatePaletteMap__published_owner:
    lda.l SourceVisual_PaletteCache+4,x
SourceVisual_ValidatePaletteMap__owner_test:
    and.l SourceVisual_PaletteTransferBit
    beq SourceVisual_ValidatePaletteMap__invalid
    rep #$31
.a16
.i16
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
    ora.l SourceVisual_PaletteCache+5,x
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
    lda.l SourceVisual_OwnerChannel
    beq SourceVisual_AllocatePaletteIdentity__found_published
    lda.l SourceVisual_PaletteCache+5,x
    ora.l SourceVisual_PaletteOwnerBit
    sta.l SourceVisual_PaletteCache+5,x
    bra SourceVisual_AllocatePaletteIdentity__found_done
SourceVisual_AllocatePaletteIdentity__found_published:
    lda.l SourceVisual_PaletteCache+4,x
    ora.l SourceVisual_PaletteOwnerBit
    sta.l SourceVisual_PaletteCache+4,x
SourceVisual_AllocatePaletteIdentity__found_done:
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
    ora.l SourceVisual_PaletteCache+5,x
    bne SourceVisual_AllocatePaletteIdentity__free_next_a8
    lda.l SourceVisual_OwnerChannel
    beq SourceVisual_AllocatePaletteIdentity__free_published
    lda.l SourceVisual_PaletteOwnerBit
    sta.l SourceVisual_PaletteCache+5,x
    bra SourceVisual_AllocatePaletteIdentity__free_claimed
SourceVisual_AllocatePaletteIdentity__free_published:
    lda.l SourceVisual_PaletteOwnerBit
    sta.l SourceVisual_PaletteCache+4,x
SourceVisual_AllocatePaletteIdentity__free_claimed:
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
    ora.l SourceVisual_PaletteCache+5,x
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
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_FindScanActive
    rep #$31
.a16
.i16
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

; If an actor retires while MSU-1 is still seeking, keep the cursor lock until
; one later service sees ready. A different reader may then safely take over.
SourceVisual_ServicePendingRead:
    php
    rep #$30
.a16
.i16
    pha
    phb
    phd
    phx
    phy
    rep #$31
.a16
.i16
    lda #SOURCE_VISUAL_WORK_BUDGET
    sta.l SourceVisual_WorkRemaining
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_ReadTurnUsed
    jsr SourceVisual_ServiceAbandonedRead
    ; The helper's common return restores A16. ReadState is one byte and the
    ; following byte is stale ReadRequestKind; keep this test byte-wide so a
    ; zero state does not become a nonzero 16-bit value and skip idle service.
    sep #$20
.a8
    lda.l SourceVisual_ReadState
    beq SourceVisual_ServicePendingRead__idle8
    cmp #1
    beq SourceVisual_ServicePendingRead__active8
    cmp #2
    beq SourceVisual_ServicePendingRead__active8
    bra SourceVisual_ServicePendingRead__done8
SourceVisual_ServicePendingRead__idle8:
    ; A reader can own the candidate identity before the shared stream becomes
    ; free. Keep retrying that same request here even when the render gate skips
    ; this actor; otherwise state 0 waits for another gated render forever.
    lda.l SourceVisual_LoaderOwner
    cmp #$FF
    beq SourceVisual_ServicePendingRead__done8
    lda.l SourceVisual_LoaderEntryValid
    cmp #1
    bne SourceVisual_ServicePendingRead__done8
SourceVisual_ServicePendingRead__active8:
    lda.l SourceVisual_LoaderOwner
    cmp.l SourceVisual_ReadOwner
    bne SourceVisual_ServicePendingRead__done8
    rep #$31
.a16
.i16
    ; Rehydrate the exact pending descriptor, independent of which actor the
    ; renderer happens to visit this frame. AsyncRead still owns all cursor
    ; and candidate-identity validation.
    lda.l SourceVisual_ReadOwner
    and #$00FF
    sta.l SourceVisual_ActorSlot
    lda.l SourceVisual_ReadOffset
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda.l SourceVisual_ReadOffset+2
    sta.l SourceVisual_Offset+2
    lda.l SourceVisual_ReadOffset+3
    sta.l SourceVisual_Offset+3
    lda.l SourceVisual_ReadKind
    sta.l SourceVisual_ReadRequestKind
    rep #$31
.a16
.i16
    lda.l SourceVisual_ReadLength
    sta.l SourceVisual_ReadRequestLength
    jsr SourceVisual_AsyncRead
SourceVisual_ServicePendingRead__done8:
    rep #$31
.a16
.i16
    ; The read service alone can leave a complete descriptor sitting in the
    ; shared scratch until this actor reaches RenderCurrent again. Advance the
    ; current owner here as well, before presentation/actor gates; both paths
    ; use the same bounded LoadResources state machine and shared work budget.
    jsr SourceVisual_ServiceCandidateStage
    ply
    plx
    pld
    plb
    pla
    plp
    rtl

; Resume the active resource state machine for the exact loader owner. The
; primary row is used only before that actor has a published packet; otherwise
; load the candidate sidecar into the existing row temporarily, then restore
; the published lease before actor rendering starts. AsyncRead's per-turn and
; byte budget remain shared with the later compositor call.
SourceVisual_ServiceCandidateStage:
    php
    phx
    phy
    phd
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda.l SourceVisual_ReadState
    cmp #4
    beq SourceVisual_ServiceCandidateStage__read_complete8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__read_complete8:
    lda.l SourceVisual_LoaderOwner
    cmp #$FF
    bne SourceVisual_ServiceCandidateStage__has_owner8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__has_owner8:
    lda.l SourceVisual_LoaderEntryValid
    cmp #1
    beq SourceVisual_ServiceCandidateStage__entry_valid8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__entry_valid8:
    lda.l SourceVisual_LoaderOwner
    cmp.l SourceVisual_ReadOwner
    beq SourceVisual_ServiceCandidateStage__owner_matches8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__owner_matches8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_LoaderOwner
    and #$00FF
    sta.l SourceVisual_ActorSlot
    ; LoadResources shares the renderer's actor-context contract. The ungated
    ; main-loop service has D=0, so reconstruct the owning CHAR direct-page
    ; base here; the PHD/PLD pair keeps the service caller's D unchanged.
    lda.l SourceVisual_ActorSlot
    tax
    lda #$0A00
    cpx #0
    beq SourceVisual_ServiceCandidateStage__actor_dp_ready
SourceVisual_ServiceCandidateStage__actor_dp_loop:
    clc
    adc #CHAR_ZP_LEN
    dex
    bne SourceVisual_ServiceCandidateStage__actor_dp_loop
SourceVisual_ServiceCandidateStage__actor_dp_ready:
    tcd
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Record
    sta.l SourceVisual_CandidateBase
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_PacketMetaOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    bne SourceVisual_ServiceCandidateStage__published8
    brl SourceVisual_ServiceCandidateStage__primary8
SourceVisual_ServiceCandidateStage__published8:
    ; A published actor keeps its primary lease live while its one candidate
    ; advances. Never run the candidate over a different packet-lane owner.
    lda.l SourceVisual_PacketCandidateOwner
    cmp #$FF
    beq SourceVisual_ServiceCandidateStage__candidate_lane_free8
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_ServiceCandidateStage__candidate_lane_free8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__candidate_lane_free8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidateBase
    tax
    sep #$20
.a8
    lda.l SourceVisual_CandidateState+6,x
    bne SourceVisual_ServiceCandidateStage__candidate_active8
    brl SourceVisual_ServiceCandidateStage__published_idle8
SourceVisual_ServiceCandidateStage__candidate_active8:
    lda.l SourceVisual_CandidateState+30,x
    beq SourceVisual_ServiceCandidateStage__candidate_running8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__candidate_running8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidateState,x
    cmp.l SourceVisual_LoaderEntryIndex
    beq SourceVisual_ServiceCandidateStage__candidate_entry_matches
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__candidate_entry_matches:
    ; Keep all 32 bytes of the published lease on the bounded CPU stack while
    ; the candidate uses the existing loader state row.
    lda.l SourceVisual_Record
    tax
    ldy #0
SourceVisual_ServiceCandidateStage__save_published:
    lda.l SourceVisual_State,x
    pha
    inx
    inx
    iny
    iny
    cpy #32
    bcc SourceVisual_ServiceCandidateStage__save_published
    lda.l SourceVisual_CandidateBase
    tax
    ldy #0
SourceVisual_ServiceCandidateStage__load_candidate:
    lda.l SourceVisual_CandidateState,x
    sta.l SourceVisual_State,x
    inx
    inx
    iny
    iny
    cpy #32
    bcc SourceVisual_ServiceCandidateStage__load_candidate
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_UseCandidate
    sta.l SourceVisual_OwnerChannel
    lda #0
    sta.l SourceVisual_Error
    lda #0
    sta.l SourceVisual_BlockCompletedThisCall
    rep #$31
.a16
.i16
    lda #7
    sta.l SourceVisual_OwnerOffset
    lda.l SourceVisual_LoaderKey
    sta.l SourceVisual_Key
    lda.l SourceVisual_LoaderKey+2
    sta.l SourceVisual_Key+2
    jsr SourceVisual_ActivateCandidate
    bcc SourceVisual_ServiceCandidateStage__save_candidate
    jsr SourceVisual_LoadResources
    bcs SourceVisual_ServiceCandidateStage__save_candidate
    sep #$20
.a8
    lda.l SourceVisual_Error
    cmp #$27
    beq SourceVisual_ServiceCandidateStage__save_candidate
    cmp #$24
    beq SourceVisual_ServiceCandidateStage__candidate_capacity8
    cmp #$26
    beq SourceVisual_ServiceCandidateStage__candidate_capacity8
    lda #2
    bra SourceVisual_ServiceCandidateStage__candidate_terminal8
SourceVisual_ServiceCandidateStage__candidate_capacity8:
    lda #1
SourceVisual_ServiceCandidateStage__candidate_terminal8:
    ; Preserve the selected capacity/terminal state across loading the actor
    ; record offset. The state byte must not inherit Record's low byte.
    pha
    rep #$20
.a16
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    pla
    sta.l SourceVisual_State+30,x
    lda.l SourceVisual_Error
    sta.l SourceVisual_State+31,x
    rep #$31
.a16
.i16
    jsr SourceVisual_ReleaseLoaderOwner
    brl SourceVisual_ServiceCandidateStage__save_candidate
SourceVisual_ServiceCandidateStage__save_candidate:
    rep #$31
.a16
.i16
    jsr SourceVisual_SaveCandidateSidecar
    lda.l SourceVisual_Record
    tax
    clc
    txa
    adc #30
    tax
    ldy #16
SourceVisual_ServiceCandidateStage__restore_published:
    pla
    sta.l SourceVisual_State,x
    dex
    dex
    dey
    bne SourceVisual_ServiceCandidateStage__restore_published
    brl SourceVisual_ServiceCandidateStage__done

SourceVisual_ServiceCandidateStage__primary8:
    ; A completed first catalog read has no primary lease yet. Admit that
    ; immutable loader request before comparing State.entry; otherwise the
    ; zero-initialized lease row rejects it forever and no render-gated caller
    ; gets a chance to consume EntryReady. The loader key/index remain the
    ; identity even if the live actor has advanced to another animation frame.
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda.l SourceVisual_State+6,x
    bne SourceVisual_ServiceCandidateStage__primary_has_lease8
SourceVisual_ServiceCandidateStage__initial_entry8:
    jsr SourceVisual_ServiceAdmitInitialEntry
    bcs SourceVisual_ServiceCandidateStage__initial_entry_admitted8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__initial_entry_admitted8:
    brl SourceVisual_ServiceCandidateStage__primary_continue8
SourceVisual_ServiceCandidateStage__primary_has_lease8:
    ; State+28 is set only after this actor's packet has successfully reached
    ; the OAM shadow. An initial P1 lease has no published packet to fall back
    ; to, so keep its shared-reader turn until that first packet is emitted.
    brl SourceVisual_ServiceCandidateStage__primary_continue8
SourceVisual_ServiceCandidateStage__primary_continue8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_LoaderEntryIndex
    beq SourceVisual_ServiceCandidateStage__primary_entry_matches
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__primary_entry_matches:
    sep #$20
.a8
    lda.l SourceVisual_State+6,x
    bne SourceVisual_ServiceCandidateStage__primary_live8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__primary_live8:
    lda.l SourceVisual_State+30,x
    beq SourceVisual_ServiceCandidateStage__primary_status_ok8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__primary_status_ok8:
    lda #0
    sta.l SourceVisual_UseCandidate
    sta.l SourceVisual_OwnerChannel
    sta.l SourceVisual_Error
    lda #0
    sta.l SourceVisual_BlockCompletedThisCall
    rep #$31
.a16
.i16
    lda #4
    sta.l SourceVisual_OwnerOffset
    lda.l SourceVisual_LoaderKey
    sta.l SourceVisual_Key
    lda.l SourceVisual_LoaderKey+2
    sta.l SourceVisual_Key+2
    jsr SourceVisual_LoadPendingEntry
    bcs SourceVisual_ServiceCandidateStage__primary_entry_consumed
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__primary_entry_consumed:
    jsr SourceVisual_LoadResources
    bcs SourceVisual_ServiceCandidateStage__resources_ready
    ; $27 is retryable pending. Other carry-clear LoadResources results are
    ; terminal/nonretryable here, so release the reader even when this owner
    ; epoch has not yet produced a durable row/map continuation.
    sep #$20
.a8
    lda.l SourceVisual_Error
    cmp #$27
    beq SourceVisual_ServiceCandidateStage__resources_pending8
    rep #$31
.a16
.i16
    jsr SourceVisual_ReleaseLoaderOwner
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__resources_pending8:
    rep #$31
.a16
.i16
SourceVisual_ServiceCandidateStage__resources_ready:
    ; ReadState zero is the bounded handoff point. The sticky owner-epoch bit
    ; below proves that a durable per-actor row/map continuation exists.
    sep #$20
.a8
    lda.l SourceVisual_PlayerPriorityOwner
    cmp #$FF
    bne SourceVisual_ServiceCandidateStage__yield_other_owner8
    brl SourceVisual_ServiceCandidateStage__yield_not_priority8
SourceVisual_ServiceCandidateStage__yield_other_owner8:
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_ServiceCandidateStage__yield_not_priority8
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__yield_not_priority8:
    ; A reservation is held until its owner gets a real seek or ready-data
    ; turn. With no reservation, yield at this idle-descriptor boundary to any
    ; other queued actor so new player keys cannot keep winning each turn.
    lda.l SourceVisual_PlayerPriorityOwner
    cmp #$FF
    bne SourceVisual_ServiceCandidateStage__yield_has_other8
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    and #$00FF
    tax
    sep #$20
.a8
    lda.l SourceVisual_ActorWaitBits,x
    eor #$FF
    and.l SourceVisual_WaitingActorMask
    beq SourceVisual_ServiceCandidateStage__yield_no_other8
SourceVisual_ServiceCandidateStage__yield_has_other8:
    ; Preserve the initial primary (slot 0) lease until it has emitted one
    ; packet. State+28 is the per-actor presentable latch, not CandidateMeta
    ; VALID (which may be zero for a legitimate empty frame). Other actors
    ; still yield at the normal bounded descriptor boundary below.
    lda.l SourceVisual_ActorSlot
    bne SourceVisual_ServiceCandidateStage__yield_initial_p1_checked8
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda.l SourceVisual_State+28,x
    bne SourceVisual_ServiceCandidateStage__yield_initial_p1_checked8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__yield_initial_p1_checked8:
    ; Both incoming paths are A8. Keep A8 for byte-sized owner/valid tests,
    ; while restoring the 16-bit index width needed by the next actor lookup.
    rep #$10
.a8
.i16
    lda.l SourceVisual_PacketCandidateOwner
    cmp #$FF
    beq SourceVisual_ServiceCandidateStage__yield_lane_free8
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__yield_no_other8:
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__yield_lane_free8:
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    beq SourceVisual_ServiceCandidateStage__yield_packet_free8
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__yield_packet_free8:
    sep #$20
.a8
    lda.l SourceVisual_ReadState
    beq SourceVisual_ServiceCandidateStage__yield_reader_free8
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__yield_reader_free8:
    lda.l SourceVisual_LoaderDurableProgress
    bne SourceVisual_ServiceCandidateStage__yield_progress_ready8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__yield_progress_ready8:
    ; Keep this unfinished actor in the bounded queue before releasing the
    ; shared reader. Otherwise ClaimQueuedActor has already cleared its waiter
    ; bit, and a stream of fresh player-key priority tokens can repeatedly win
    ; the next descriptor boundary before this actor is rendered again.
SourceVisual_ServiceCandidateStage__yield_requeue:
    jsr SourceVisual_QueueCurrentActor
    rep #$31
.a16
.i16
    jsr SourceVisual_ReleaseLoaderOwner
SourceVisual_ServiceCandidateStage__yield_released:
    brl SourceVisual_ServiceCandidateStage__done

; A completed ENTRY read can be redundant once this actor's exact key and
; entry already have a valid published packet. Retire only after ReadEntry has
; tagged EntryScratch for this actor/index; preserve that tag across the owner
; release so FindEntry's existing same-key cache remains usable. Never release
; another kind/actor's descriptor or a reader with candidate/scan state active.
SourceVisual_ServiceCandidateStage__published_idle8:
    sep #$20
.a8
    lda.l SourceVisual_PacketCandidateOwner
    cmp #$FF
    beq SourceVisual_ServiceCandidateStage__published_lane_free8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__published_lane_free8:
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    beq SourceVisual_ServiceCandidateStage__published_packet_free8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__published_packet_free8:
    lda.l SourceVisual_CandidateState+30,x
    beq SourceVisual_ServiceCandidateStage__published_status_free8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__published_status_free8:
    lda.l SourceVisual_ReadKind
    cmp #SOURCE_VISUAL_MSU_READ_ENTRY
    beq SourceVisual_ServiceCandidateStage__published_kind_ok8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__published_kind_ok8:
    lda.l SourceVisual_ReadRequestKind
    cmp #SOURCE_VISUAL_MSU_READ_ENTRY
    beq SourceVisual_ServiceCandidateStage__published_request_ok8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__published_request_ok8:
    lda.l SourceVisual_EntryReady
    cmp #1
    beq SourceVisual_ServiceCandidateStage__published_ready8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__published_ready8:
    lda.l SourceVisual_EntryReadySlot
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_ServiceCandidateStage__published_ready_owner8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__published_ready_owner8:
    lda.l SourceVisual_FindScanActive
    beq SourceVisual_ServiceCandidateStage__published_no_scan8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__published_no_scan8:
    lda.l SourceVisual_PreflightState
    beq SourceVisual_ServiceCandidateStage__published_no_preflight8
    brl SourceVisual_ServiceCandidateStage__done8
SourceVisual_ServiceCandidateStage__published_no_preflight8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ReadLength
    cmp #24
    beq SourceVisual_ServiceCandidateStage__published_length_ok
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__published_length_ok:
    lda.l SourceVisual_ReadCursor
    cmp.l SourceVisual_ReadLength
    beq SourceVisual_ServiceCandidateStage__published_cursor_ok
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__published_cursor_ok:
    lda.l SourceVisual_EntryReadyIndex
    cmp.l SourceVisual_LoaderEntryIndex
    beq SourceVisual_ServiceCandidateStage__published_ready_index_ok
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__published_ready_index_ok:
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_LoaderEntryIndex
    beq SourceVisual_ServiceCandidateStage__published_state_index_ok
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__published_state_index_ok:
    lda.l SourceVisual_PacketMetaOffset
    tax
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_ENTRY,x
    cmp.l SourceVisual_LoaderEntryIndex
    beq SourceVisual_ServiceCandidateStage__published_meta_index_ok
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__published_meta_index_ok:
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    tax
    lda.l SourceVisual_PublishedKey,x
    cmp.l SourceVisual_LoaderKey
    beq SourceVisual_ServiceCandidateStage__published_key_low_ok
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__published_key_low_ok:
    lda.l SourceVisual_PublishedKey+2,x
    cmp.l SourceVisual_LoaderKey+2
    beq SourceVisual_ServiceCandidateStage__published_key_match
    brl SourceVisual_ServiceCandidateStage__done
SourceVisual_ServiceCandidateStage__published_key_match:
    ; ReleaseLoaderOwner invalidates EntryReady. Its bytes and slot/index tag
    ; remain valid until another ENTRY seek actually starts, so restore only the
    ; already-validated ready bit after the completed descriptor is retired.
    jsr SourceVisual_ReleaseLoaderOwner
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_EntryReady
    brl SourceVisual_ServiceCandidateStage__done8

; Consume the completed immutable catalog-entry descriptor and create the
; actor's first primary lease before any sheet/piece reads can be serviced.
; Called only from the primary path with D set to the owner actor's CHAR row.
; A later native animation key cannot replace LoaderKey/LoaderEntryIndex while
; the catalog seek is pending, so the first request is admitted exactly once.
SourceVisual_ServiceAdmitInitialEntry:
    sep #$20
.a8
    lda.l SourceVisual_ReadState
    cmp #4
    beq SourceVisual_ServiceAdmitInitialEntry__complete8
    brl SourceVisual_ServiceAdmitInitialEntry__pending8
SourceVisual_ServiceAdmitInitialEntry__complete8:
    lda.l SourceVisual_LoaderEntryValid
    cmp #1
    bne SourceVisual_ServiceAdmitInitialEntry__pending8
    lda.l SourceVisual_LoaderOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_ServiceAdmitInitialEntry__pending8
    lda.l SourceVisual_ReadOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_ServiceAdmitInitialEntry__pending8
    lda.l SourceVisual_ReadKind
    cmp #SOURCE_VISUAL_MSU_READ_ENTRY
    bne SourceVisual_ServiceAdmitInitialEntry__pending8
    rep #$31
.a16
.i16
    lda.l SourceVisual_ReadLength
    cmp #24
    bne SourceVisual_ServiceAdmitInitialEntry__pending
    ; Rehydrate the exact completed read descriptor before ReadEntry validates
    ; it and publishes the EntryReady slot/index consumed by SelectResidency.
    lda.l SourceVisual_LoaderEntryIndex
    sta.l SourceVisual_EntryIndexSaved
    lda.l SourceVisual_LoaderKey
    sta.l SourceVisual_Key
    lda.l SourceVisual_LoaderKey+2
    sta.l SourceVisual_Key+2
    lda.l SourceVisual_ReadOffset
    sta.l SourceVisual_Offset
    lda.l SourceVisual_ReadOffset+2
    sta.l SourceVisual_Offset+2
    jsr SourceVisual_ReadEntry
    bcc SourceVisual_ServiceAdmitInitialEntry__pending
    jsr SourceVisual_SelectResidency
    bcc SourceVisual_ServiceAdmitInitialEntry__pending
    sec
    rts
SourceVisual_ServiceAdmitInitialEntry__pending8:
    rep #$31
.a16
.i16
SourceVisual_ServiceAdmitInitialEntry__pending:
    clc
    rts

SourceVisual_ServiceCandidateStage__done8:
    rep #$31
.a16
.i16
SourceVisual_ServiceCandidateStage__done:
    pld
    ply
    plx
    plp
    rts

; Clear only the visual seek bit as one 65816 memory-RMW instruction. NMI
; clears the legacy DMA bit with its own read/write; it cannot interrupt a
; TRB opcode, so this cannot restore a stale bit-0 value. The DBR window is
; explicit: TRB has absolute, not long, addressing on the 65816.
SourceVisual_ClearSeekReservation:
    php
    phb
    sep #$20
.a8
    lda #$7E
    pha
    plb
    lda #$80
    trb.w $2330
    plb
    plp
    rts

SourceVisual_ServiceAbandonedRead:
    sep #$20
.a8
    lda.l SourceVisual_ReadState
    cmp #3
    bne SourceVisual_ServiceAbandonedRead__done8
    lda #1
    sta.l SourceVisual_ReadTurnUsed
    lda $2000
    bmi SourceVisual_ServiceAbandonedRead__done8
    jsr SourceVisual_ClearSeekReservation
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_ReadState
    sta.l SourceVisual_LoaderEntryValid
    lda #$FF
    sta.l SourceVisual_LoaderOwner
    sta.l SourceVisual_ReadOwner
    lda #0
    sta.l SourceVisual_LoaderDurableProgress
SourceVisual_ServiceAbandonedRead__done8:
    rep #$31
.a16
.i16
    rts

; Release a completed/abandoned candidate's MSU ownership. A seek that is
; still busy drains asynchronously before another reader may alter the cursor.
SourceVisual_ReleaseLoaderOwner:
    sep #$20
.a8
    lda.l SourceVisual_LoaderOwner
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_ReleaseLoaderOwner__owned8
    lda.l SourceVisual_FindScanActive
    bne SourceVisual_ReleaseLoaderOwner__foreign_find_scan8
    brl SourceVisual_ReleaseLoaderOwner__done8
SourceVisual_ReleaseLoaderOwner__foreign_find_scan8:
    lda.l SourceVisual_FindScanOwner
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_ReleaseLoaderOwner__clear_find_scan8
    brl SourceVisual_ReleaseLoaderOwner__done8
SourceVisual_ReleaseLoaderOwner__clear_find_scan8:
.a8
    lda #0
    sta.l SourceVisual_FindScanActive
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
    rts
SourceVisual_ReleaseLoaderOwner__owned8:
    ; This branch target follows an A16 return path in the linear source, so
    ; establish the byte width here as well as at the routine entry.
    sep #$20
.a8
    lda.l SourceVisual_ReadState
    cmp #0
    beq SourceVisual_ReleaseLoaderOwner__retry_unstarted8
    cmp #1
    beq SourceVisual_ReleaseLoaderOwner__abandon
    cmp #3
    beq SourceVisual_ReleaseLoaderOwner__done8
    bra SourceVisual_ReleaseLoaderOwner__drop_descriptor8
SourceVisual_ReleaseLoaderOwner__retry_unstarted8:
    ; State zero is a registered descriptor whose seek has not started. Drop
    ; only this transient global descriptor; the actor's candidate/cache stage
    ; remains authoritative and will reconstruct the same request on its next
    ; grant. RowScratch identity remains tagged, so a tile retry can use it only
    ; if it still belongs to that exact block.
SourceVisual_ReleaseLoaderOwner__drop_descriptor8:
    jsr SourceVisual_ClearSeekReservation
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_ReadState
    sta.l SourceVisual_EntryReady
    sta.l SourceVisual_LoaderEntryValid
    sta.l SourceVisual_LoaderDurableProgress
    lda.l SourceVisual_CatalogBindState
    cmp #1
    bne SourceVisual_ReleaseLoaderOwner__binding_released8
    lda.l SourceVisual_CatalogBindOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_ReleaseLoaderOwner__binding_released8
    lda #0
    sta.l SourceVisual_CatalogBindState
    lda #$FF
    sta.l SourceVisual_CatalogBindOwner
SourceVisual_ReleaseLoaderOwner__binding_released8:
    lda #$FF
    sta.l SourceVisual_LoaderOwner
    sta.l SourceVisual_ReadOwner
    jsr SourceVisual_GrantNextQueuedActor
    bra SourceVisual_ReleaseLoaderOwner__done8
SourceVisual_ReleaseLoaderOwner__abandon:
.a8
    lda #3
    sta.l SourceVisual_ReadState
    lda.l SourceVisual_CatalogBindState
    cmp #1
    bne SourceVisual_ReleaseLoaderOwner__done8
    lda.l SourceVisual_CatalogBindOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_ReleaseLoaderOwner__done8
    lda #0
    sta.l SourceVisual_CatalogBindState
    lda #$FF
    sta.l SourceVisual_CatalogBindOwner
    bra SourceVisual_ReleaseLoaderOwner__done8
SourceVisual_ReleaseLoaderOwner__done8:
.a8
    lda #0
    sta.l SourceVisual_PreflightState
    sta.l SourceVisual_FindScanActive
    rep #$31
.a16
.i16
    rts

; One call issues a seek, polls an outstanding seek once, or copies at most
; SOURCE_VISUAL_MSU_READ_CHUNK ready bytes. Partial reads save their cursor and
; re-seek on the next turn because other animation readers share MSU-1's cursor.
; Carry set means the requested buffer is complete; clear means try next turn.
SourceVisual_AsyncRead:
    rep #$31
.a16
.i16
    sep #$20
.a8
    ; Keep the one-I/O-turn-per-frame budget, but do not drop a later
    ; descriptor when an earlier reader already used this turn. A completed
    ; catalog row can be followed by a sheet/piece-row request in the same
    ; render pass; latch that next descriptor for ServicePendingRead instead
    ; of returning an unowned $27 that the next animation key can overwrite.
    lda.l SourceVisual_LoaderOwner
    cmp #$FF
    bne SourceVisual_AsyncRead__owner_present
    lda.l SourceVisual_PlayerPriorityOwner
    cmp #$FF
    beq SourceVisual_AsyncRead__fresh_owner8
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_AsyncRead__fresh_owner8
    jsr SourceVisual_QueueCurrentActor
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__fresh_owner8:
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_LoaderOwner
    sta.l SourceVisual_ReadOwner
    lda #1
    sta.l SourceVisual_LoaderEntryValid
    lda #0
    sta.l SourceVisual_LoaderDurableProgress
    rep #$31
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_LoaderEntryIndex
    lda.l SourceVisual_Key
    sta.l SourceVisual_LoaderKey
    lda.l SourceVisual_Key+2
    sta.l SourceVisual_LoaderKey+2
    jsr SourceVisual_ClaimQueuedActor
    brl SourceVisual_AsyncRead__state
SourceVisual_AsyncRead__owner_present:
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_AsyncRead__owner_ok8
    jsr SourceVisual_QueueCurrentActor
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__owner_ok8:
    rep #$31
.a16
.i16
SourceVisual_AsyncRead__state:
    sep #$20
.a8
    lda.l SourceVisual_ReadState
    bne SourceVisual_AsyncRead__state_nonzero8
    lda.l SourceVisual_ReadTurnUsed
    beq SourceVisual_AsyncRead__state_idle_turn_free8
    brl SourceVisual_AsyncRead__queue_descriptor8
SourceVisual_AsyncRead__state_idle_turn_free8:
    brl SourceVisual_AsyncRead__start
SourceVisual_AsyncRead__state_nonzero8:
    cmp #1
    beq SourceVisual_AsyncRead__compare
    cmp #2
    beq SourceVisual_AsyncRead__compare
    cmp #4
    beq SourceVisual_AsyncRead__compare
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__compare:
    lda.l SourceVisual_ReadOwner
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_AsyncRead__owner_match
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__owner_match:
    lda.l SourceVisual_ReadKind
    cmp.l SourceVisual_ReadRequestKind
    beq SourceVisual_AsyncRead__compare_kind_ok
    ; A different kind can mean the previous descriptor completed (for
    ; example, catalog entry -> sheet row). Let descriptor_mismatch decide:
    ; completed reads may be replaced/queued, while active reads stay pending.
    brl SourceVisual_AsyncRead__descriptor_mismatch
SourceVisual_AsyncRead__compare_kind_ok:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ReadLength
    cmp.l SourceVisual_ReadRequestLength
    beq SourceVisual_AsyncRead__compare_length_ok
    brl SourceVisual_AsyncRead__descriptor_mismatch
SourceVisual_AsyncRead__compare_length_ok:
    lda.l SourceVisual_ReadOffset
    cmp.l SourceVisual_Offset
    beq SourceVisual_AsyncRead__compare_offset_low_ok
    brl SourceVisual_AsyncRead__descriptor_mismatch
SourceVisual_AsyncRead__compare_offset_low_ok:
    lda.l SourceVisual_ReadOffset+2
    cmp.l SourceVisual_Offset+2
    beq SourceVisual_AsyncRead__compare_offset_high_ok
    brl SourceVisual_AsyncRead__descriptor_mismatch
SourceVisual_AsyncRead__compare_offset_high_ok:
    sep #$20
.a8
    lda.l SourceVisual_ReadState
    cmp #4
    beq SourceVisual_AsyncRead__latched_complete8
    lda.l SourceVisual_ReadTurnUsed
    beq SourceVisual_AsyncRead__state_turn_free8
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__state_turn_free8:
    lda.l SourceVisual_ReadState
    cmp #2
    bne SourceVisual_AsyncRead__poll_ready8
    brl SourceVisual_AsyncRead__resume
SourceVisual_AsyncRead__poll_ready8:
    lda #1
    sta.l SourceVisual_ReadTurnUsed
    lda $2000
    bpl SourceVisual_AsyncRead__ready
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__latched_complete8:
    rep #$31
.a16
.i16
    sec
    rts
SourceVisual_AsyncRead__descriptor_mismatch:
    sep #$20
.a8
    lda.l SourceVisual_ReadState
    cmp #4
    beq SourceVisual_AsyncRead__discard_complete8
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__discard_complete8:
    lda.l SourceVisual_ReadTurnUsed
    bne SourceVisual_AsyncRead__queue_descriptor8
    lda #0
    sta.l SourceVisual_ReadState
    rep #$31
.a16
.i16
    brl SourceVisual_AsyncRead__start
SourceVisual_AsyncRead__queue_descriptor8:
    ; Descriptor registration is metadata work only: no seek, ready poll, or
    ; payload copy consumes a second MSU turn. ServicePendingRead will replay
    ; the complete descriptor at the next service point. Publish state zero
    ; after all 16/32-bit fields and owner identity are stored.
    rep #$31
.a16
.i16
    lda.l SourceVisual_Offset
    sta.l SourceVisual_ReadOffset
    lda.l SourceVisual_Offset+2
    sta.l SourceVisual_ReadOffset+2
    lda.l SourceVisual_ReadRequestLength
    sta.l SourceVisual_ReadLength
    lda #0
    sta.l SourceVisual_ReadCursor
    sep #$20
.a8
    lda.l SourceVisual_ReadRequestKind
    sta.l SourceVisual_ReadKind
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_ReadOwner
    lda #0
    sta.l SourceVisual_ReadState
    ; This descriptor is retained for the next service turn, so callers must
    ; classify the clear-carry return as pending rather than terminal failure.
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_AsyncRead__ready:
    ; A priority grant is spent only when this turn can consume ready bytes,
    ; not on a busy poll that made no resource progress.
    jsr SourceVisual_ConsumePriorityTurn
    rep #$31
.a16
.i16
    brl SourceVisual_AsyncRead__copy_chunk
SourceVisual_AsyncRead__start:
    sep #$20
.a8
    lda.l Msu1_StreamBusy
    beq SourceVisual_AsyncRead__stream_free
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__stream_free:
    ; The dispatch above inspects ReadState in A8. A fresh descriptor copies
    ; 16-bit offsets, length, and cursor; restore A16/I16 before those stores or
    ; stale high bytes turn a short row request into an enormous read.
    rep #$31
.a16
.i16
    lda.l SourceVisual_Offset
    sta.l SourceVisual_ReadOffset
    lda.l SourceVisual_Offset+2
    sta.l SourceVisual_ReadOffset+2
    lda.l SourceVisual_ReadRequestLength
    sta.l SourceVisual_ReadLength
    lda #0
    sta.l SourceVisual_ReadCursor
    sep #$20
.a8
    lda.l SourceVisual_ReadRequestKind
    sta.l SourceVisual_ReadKind
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_ReadOwner
    brl SourceVisual_AsyncRead__issue_seek
SourceVisual_AsyncRead__resume:
    sep #$20
.a8
    lda.l Msu1_StreamBusy
    beq SourceVisual_AsyncRead__stream_free_resume
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__stream_free_resume:
    rep #$31
.a16
.i16
    brl SourceVisual_AsyncRead__issue_seek
SourceVisual_AsyncRead__issue_seek:
    sep #$20
.a8
    ; These buffers are global scratch. Invalidate their owner tags only when a
    ; seek that will write them actually starts, not when another actor merely
    ; queues behind the current MSU owner.
    lda.l SourceVisual_ReadKind
    cmp #SOURCE_VISUAL_MSU_READ_ENTRY
    bne SourceVisual_AsyncRead__issue_not_entry8
    lda #0
    sta.l SourceVisual_EntryReady
SourceVisual_AsyncRead__issue_not_entry8:
    lda.l SourceVisual_ReadKind
    cmp #SOURCE_VISUAL_MSU_READ_PIECES
    bne SourceVisual_AsyncRead__issue_row_tag8
    lda #0
    sta.l SourceVisual_PieceTableValid
SourceVisual_AsyncRead__issue_row_tag8:
    ; ReadRow calls can be denied while a different actor owns the active
    ; descriptor. Invalidate shared RowScratch only when this row's seek is
    ; actually admitted, alongside the other global-buffer tags.
    lda.l SourceVisual_ReadKind
    cmp #SOURCE_VISUAL_MSU_READ_ROW
    beq SourceVisual_AsyncRead__invalidate_row_tag8
    cmp #SOURCE_VISUAL_MSU_READ_BIND
    bne SourceVisual_AsyncRead__issue_buffers_valid8
SourceVisual_AsyncRead__invalidate_row_tag8:
    lda #0
    sta.l SourceVisual_RowScratchBlockValid
SourceVisual_AsyncRead__issue_buffers_valid8:
    lda #1
    sta.l SourceVisual_ReadTurnUsed
    rep #$31
.a16
.i16
    lda.l SourceVisual_ReadOffset
    clc
    adc.l SourceVisual_ReadCursor
    sta.l SourceVisual_ReadSeek
    sta.l SourceVisual_DebugSeek
    sep #$20
.a8
    lda.l SourceVisual_ReadOffset+2
    adc #0
    sta.l SourceVisual_ReadSeek+2
    sta.l SourceVisual_DebugSeek+2
    lda.l SourceVisual_ReadOffset+3
    adc #0
    sta.l SourceVisual_ReadSeek+3
    sta.l SourceVisual_DebugSeek+3
    lda #$80
    sta.l Msu1_StreamBusy
    lda #1
    sta.l SourceVisual_ReadState
    lda.l SourceVisual_ReadSeek
    sta $2000
    lda.l SourceVisual_ReadSeek+1
    sta $2001
    lda.l SourceVisual_ReadSeek+2
    sta $2002
    lda.l SourceVisual_ReadSeek+3
    sta $2003
    jsr SourceVisual_ConsumePriorityTurn
SourceVisual_AsyncRead__seek_poll8:
    ; One status sample lets an immediately-ready seek consume this turn's
    ; existing work budget. If it is still busy, return pending without
    ; polling in a loop or changing the descriptor/owner.
    lda $2000
    bpl SourceVisual_AsyncRead__seek_ready8
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__seek_ready8:
    brl SourceVisual_AsyncRead__copy_chunk
SourceVisual_AsyncRead__copy_chunk:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ReadLength
    sec
    sbc.l SourceVisual_ReadCursor
    bne SourceVisual_AsyncRead__remaining
    brl SourceVisual_AsyncRead__complete
SourceVisual_AsyncRead__remaining:
    lda.l SourceVisual_WorkRemaining
    bne SourceVisual_AsyncRead__work_available
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__work_available:
    ; Consume no more than the shared byte/parse budget remaining this turn.
    lda.l SourceVisual_ReadLength
    sec
    sbc.l SourceVisual_ReadCursor
    cmp.l SourceVisual_WorkRemaining
    bcc SourceVisual_AsyncRead__chunk_sized
    beq SourceVisual_AsyncRead__chunk_sized
    lda.l SourceVisual_WorkRemaining
SourceVisual_AsyncRead__chunk_sized:
    sta.l SourceVisual_ReadChunk
    sta.l SourceVisual_ReadRemaining
    lda.l SourceVisual_ReadCursor
    tax
    sep #$20
.a8
    lda.l SourceVisual_ReadKind
    cmp #SOURCE_VISUAL_MSU_READ_ENTRY
    beq SourceVisual_AsyncRead__copy_entry
    cmp #SOURCE_VISUAL_MSU_READ_ROW
    beq SourceVisual_AsyncRead__copy_row
    cmp #SOURCE_VISUAL_MSU_READ_PIECES
    beq SourceVisual_AsyncRead__copy_pieces
    cmp #SOURCE_VISUAL_MSU_READ_TILE
    beq SourceVisual_AsyncRead__copy_tile
    cmp #SOURCE_VISUAL_MSU_READ_PALETTE
    beq SourceVisual_AsyncRead__copy_palette
    cmp #SOURCE_VISUAL_MSU_READ_BIND
    beq SourceVisual_AsyncRead__copy_bind
    brl SourceVisual_AsyncRead__bad_kind
SourceVisual_AsyncRead__copy_entry:
    lda $2001
    sta.l SourceVisual_EntryScratch,x
    rep #$31
.a16
.i16
    inx
    jsr SourceVisual_AsyncRead__dec_remaining
    bne SourceVisual_AsyncRead__copy_entry
    brl SourceVisual_AsyncRead__copied
SourceVisual_AsyncRead__copy_row:
    lda $2001
    sta.l SourceVisual_RowScratch,x
    rep #$31
.a16
.i16
    inx
    jsr SourceVisual_AsyncRead__dec_remaining
    bne SourceVisual_AsyncRead__copy_row
    brl SourceVisual_AsyncRead__copied
SourceVisual_AsyncRead__copy_pieces:
    lda $2001
    sta.l SourceVisual_PieceTable,x
    rep #$31
.a16
.i16
    inx
    jsr SourceVisual_AsyncRead__dec_remaining
    bne SourceVisual_AsyncRead__copy_pieces
    brl SourceVisual_AsyncRead__copied
SourceVisual_AsyncRead__copy_tile:
    lda $2001
    sta.l SourceVisual_TileStaging,x
    rep #$31
.a16
.i16
    inx
    jsr SourceVisual_AsyncRead__dec_remaining
    bne SourceVisual_AsyncRead__copy_tile
    brl SourceVisual_AsyncRead__copied
SourceVisual_AsyncRead__copy_palette:
    lda $2001
    sta.l SourceVisual_PaletteTemp,x
    rep #$31
.a16
.i16
    inx
    jsr SourceVisual_AsyncRead__dec_remaining
    bne SourceVisual_AsyncRead__copy_palette
    brl SourceVisual_AsyncRead__copied
SourceVisual_AsyncRead__copy_bind:
    lda $2001
    sta.l SourceVisual_RowScratch,x
    rep #$31
.a16
.i16
    inx
    jsr SourceVisual_AsyncRead__dec_remaining
    bne SourceVisual_AsyncRead__copy_bind
SourceVisual_AsyncRead__copied:
    txa
    sta.l SourceVisual_ReadCursor
    lda.l SourceVisual_WorkRemaining
    sec
    sbc.l SourceVisual_ReadChunk
    sta.l SourceVisual_WorkRemaining
    lda.l SourceVisual_ReadCursor
    cmp.l SourceVisual_ReadLength
    bcs SourceVisual_AsyncRead__complete
    sep #$20
.a8
    lda #2
    sta.l SourceVisual_ReadState
    jsr SourceVisual_ClearSeekReservation
    sep #$20
.a8
    brl SourceVisual_AsyncRead__pending
SourceVisual_AsyncRead__dec_remaining:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ReadRemaining
    dec a
    sta.l SourceVisual_ReadRemaining
    cmp #0
    rts
SourceVisual_AsyncRead__complete:
    jsr SourceVisual_ClearSeekReservation
    sep #$20
.a8
    lda #4
    sta.l SourceVisual_ReadState
    rep #$31
.a16
.i16
    sec
    rts
SourceVisual_AsyncRead__bad_kind:
    sep #$20
.a8
    lda #$23
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_AsyncRead__pending:
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
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
    sep #$20
.a8
    lda #SOURCE_VISUAL_MSU_READ_ENTRY
    sta.l SourceVisual_ReadRequestKind
    rep #$31
.a16
.i16
    lda #24
    sta.l SourceVisual_ReadRequestLength
    jsr SourceVisual_AsyncRead
    bcc SourceVisual_ReadEntry__return
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_EntryReady
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_EntryReadySlot
    rep #$31
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_EntryReadyIndex
    ; REP #$31 clears carry.  ReadEntry returns the AsyncRead completion
    ; contract to FindEntry, so restore success after recording the cache.
    sec
SourceVisual_ReadEntry__return:
    rts

SourceVisual_ReadRow:
    sep #$20
.a8
    ; AsyncRead invalidates RowScratchBlockValid only if this actor's seek is
    ; admitted. A foreign owner may queue this call without touching the bytes.
    lda #SOURCE_VISUAL_MSU_READ_ROW
    sta.l SourceVisual_ReadRequestKind
    rep #$31
.a16
.i16
    lda #42
    sta.l SourceVisual_ReadRequestLength
    jmp SourceVisual_AsyncRead

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
    bcs SourceVisual_LoadResources__legacy_sheet_row_ready
    brl SourceVisual_LoadResources__pending
SourceVisual_LoadResources__legacy_sheet_row_ready:
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
    bcs SourceVisual_LoadResources__legacy_sheet_chunk_ready
    brl SourceVisual_LoadResources__pending
SourceVisual_LoadResources__legacy_sheet_chunk_ready:

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
    bcs SourceVisual_LoadResources__legacy_pieces_ready
    brl SourceVisual_LoadResources__pending
SourceVisual_LoadResources__legacy_pieces_ready:
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
    bcs SourceVisual_LoadResources__legacy_final_pieces_ready
    brl SourceVisual_LoadResources__pending
SourceVisual_LoadResources__legacy_final_pieces_ready:
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
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda.l SourceVisual_State+SOURCE_VISUAL_STATE_SHEET_ROW_VALID,x
    cmp #1
    beq SourceVisual_LoadResources__block_sheet_cached8
    rep #$31
.a16
.i16
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
    bcs SourceVisual_LoadResources__block_sheet_read
    brl SourceVisual_LoadResources__block_pending
SourceVisual_LoadResources__block_sheet_read:
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+SOURCE_VISUAL_STATE_SHEET_ROW_VALID,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_RowScratch+32
    sta.l SourceVisual_State+22,x
    bra SourceVisual_LoadResources__block_sheet_cached
SourceVisual_LoadResources__block_sheet_cached8:
    rep #$31
.a16
.i16
SourceVisual_LoadResources__block_sheet_cached:
    lda.l SourceVisual_State+22,x
    cmp #SOURCE_VISUAL_MAX_SHEET+1
    bcc SourceVisual_LoadResources__block_sheet_ok
    brl SourceVisual_LoadResources__large
SourceVisual_LoadResources__block_sheet_ok:
.a16
    sta.l SourceVisual_SheetBytes

    ; State+25 remembers this actor's earlier read, but PieceTable is one
    ; global 65-row scratch buffer. Reuse it only when the global completed-read
    ; tag still names this actor and catalog entry.
SourceVisual_LoadResources__piece_table_check:
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda.l SourceVisual_State+SOURCE_VISUAL_STATE_PIECE_ROWS_VALID,x
    cmp #1
    bne SourceVisual_LoadResources__block_pieces_need_read8
    lda.l SourceVisual_PieceTableValid
    cmp #1
    bne SourceVisual_LoadResources__block_pieces_need_read8
    lda.l SourceVisual_PieceTableOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_LoadResources__block_pieces_need_read8
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceTableEntry
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceVisual_LoadResources__block_pieces_cached
    brl SourceVisual_LoadResources__block_pieces_need_read8
SourceVisual_LoadResources__block_pieces_need_read8:
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
    bcs SourceVisual_LoadResources__block_pieces_read
    brl SourceVisual_LoadResources__block_pending
SourceVisual_LoadResources__block_pieces_read:
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+SOURCE_VISUAL_STATE_PIECE_ROWS_VALID,x
    bra SourceVisual_LoadResources__block_pieces_cached
SourceVisual_LoadResources__block_pieces_cached8:
    rep #$31
.a16
.i16
SourceVisual_LoadResources__block_pieces_cached:
    ; A candidate must prove the complete current tile/palette footprint fits
    ; beside every published lease before it acquires any new cache ownership.
    sep #$20
.a8
    lda.l SourceVisual_OwnerChannel
    beq SourceVisual_LoadResources__preflight_done8
    rep #$31
.a16
.i16
    jsr SourceVisual_PreflightCandidate
    bcs SourceVisual_LoadResources__preflight_done
    clc
    rts
SourceVisual_LoadResources__preflight_done8:
    rep #$31
.a16
.i16
SourceVisual_LoadResources__preflight_done:
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

; Exact bounded admission for one candidate packet. The two compact ID lists
; deduplicate visible tile blocks and all referenced palettes before any new
; DMA or pin is admitted, so a frame that cannot fit beside the published
; packet applies backpressure without repeatedly uploading a partial prefix.
SourceVisual_PreflightCandidate:
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda.l SourceVisual_PreflightState
    beq SourceVisual_PreflightCandidate__initialize8
    lda.l SourceVisual_PreflightActor
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_PreflightCandidate__initialize8
    rep #$31
.a16
.i16
    lda.l SourceVisual_PreflightEntry
    cmp.l SourceVisual_EntryIndexSaved
    bne SourceVisual_PreflightCandidate__initialize
    sep #$20
.a8
    lda.l SourceVisual_PreflightState
    cmp #$FF
    bne SourceVisual_PreflightCandidate__state_not_done8
    brl SourceVisual_PreflightCandidate__ready8
SourceVisual_PreflightCandidate__state_not_done8:
    cmp #1
    bne SourceVisual_PreflightCandidate__state_not_block_piece8
    brl SourceVisual_PreflightCandidate__resume_block_piece8
SourceVisual_PreflightCandidate__state_not_block_piece8:
    cmp #2
    bne SourceVisual_PreflightCandidate__state_not_block_seen8
    brl SourceVisual_PreflightCandidate__resume_block_seen8
SourceVisual_PreflightCandidate__state_not_block_seen8:
    cmp #3
    bne SourceVisual_PreflightCandidate__state_not_block_free8
    brl SourceVisual_PreflightCandidate__resume_block_free8
SourceVisual_PreflightCandidate__state_not_block_free8:
    cmp #4
    bne SourceVisual_PreflightCandidate__state_not_palette_piece8
    brl SourceVisual_PreflightCandidate__resume_palette_piece8
SourceVisual_PreflightCandidate__state_not_palette_piece8:
    cmp #5
    bne SourceVisual_PreflightCandidate__state_not_palette_scan8
    brl SourceVisual_PreflightCandidate__resume_palette_cache_scan8
SourceVisual_PreflightCandidate__state_not_palette_scan8:
    cmp #6
    bne SourceVisual_PreflightCandidate__state_not_palette_seen8
    brl SourceVisual_PreflightCandidate__resume_palette_seen8
SourceVisual_PreflightCandidate__state_not_palette_seen8:
    cmp #7
    bne SourceVisual_PreflightCandidate__state_unknown8
    brl SourceVisual_PreflightCandidate__resume_palette_free8
SourceVisual_PreflightCandidate__state_unknown8:
    cmp #8
    bne SourceVisual_PreflightCandidate__state_unknown2_8
    brl SourceVisual_PreflightCandidate__resume_block_cache8
SourceVisual_PreflightCandidate__state_unknown2_8:
    brl SourceVisual_PreflightCandidate__initialize8
SourceVisual_PreflightCandidate__initialize8:
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__initialize:
    sep #$20
.a8
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_PreflightActor
    rep #$31
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_PreflightEntry
    ; The actor's cache ownership bit.
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_PreflightCandidate__mask:
.i16
    cpx #0
    beq SourceVisual_PreflightCandidate__mask_ready
    asl a
    dex
    bra SourceVisual_PreflightCandidate__mask
SourceVisual_PreflightCandidate__mask_ready:
    sep #$20
.a8
    sta.l SourceVisual_BlockActorMask
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_PreflightCount
    sta.l SourceVisual_PieceIndex
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__block_piece:
    jsr SourceVisual_ConsumeWork
    bcs SourceVisual_PreflightCandidate__block_piece_budget_ok
    brl SourceVisual_PreflightCandidate__yield
SourceVisual_PreflightCandidate__block_piece_budget_ok:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceVisual_PreflightCandidate__block_piece_in_range
    brl SourceVisual_PreflightCandidate__block_free_start
SourceVisual_PreflightCandidate__block_piece_in_range:
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+12,x
    sta.l SourceVisual_BlockIndex
    lda #0
    sta.l SourceVisual_BlockScan
    sep #$20
.a8
    lda #8
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__block_cache_scan:
    jsr SourceVisual_ConsumeWork
    bcs SourceVisual_PreflightCandidate__block_cache_budget_ok
    brl SourceVisual_PreflightCandidate__yield
SourceVisual_PreflightCandidate__block_cache_budget_ok:
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcs SourceVisual_PreflightCandidate__block_cache_miss
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+2,x
    beq SourceVisual_PreflightCandidate__block_cache_next
    lda.l SourceVisual_BlockCache,x
    cmp.l SourceVisual_BlockIndex
    beq SourceVisual_PreflightCandidate__block_next
SourceVisual_PreflightCandidate__block_cache_next:
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    bra SourceVisual_PreflightCandidate__block_cache_scan
SourceVisual_PreflightCandidate__block_cache_miss:
    lda #0
    sta.l SourceVisual_PreflightScan
    sep #$20
.a8
    lda #2
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__block_seen:
    jsr SourceVisual_ConsumeWork
    bcs SourceVisual_PreflightCandidate__block_seen_budget_ok
    brl SourceVisual_PreflightCandidate__yield
SourceVisual_PreflightCandidate__block_seen_budget_ok:
    lda.l SourceVisual_PreflightScan
    cmp.l SourceVisual_PreflightCount
    bcs SourceVisual_PreflightCandidate__block_add
    asl a
    tax
    lda.l SourceVisual_PreflightIds,x
    cmp.l SourceVisual_BlockIndex
    beq SourceVisual_PreflightCandidate__block_next
    lda.l SourceVisual_PreflightScan
    inc a
    sta.l SourceVisual_PreflightScan
    bra SourceVisual_PreflightCandidate__block_seen
SourceVisual_PreflightCandidate__block_add:
    lda.l SourceVisual_PreflightCount
    asl a
    tax
    lda.l SourceVisual_BlockIndex
    sta.l SourceVisual_PreflightIds,x
    lda.l SourceVisual_PreflightCount
    inc a
    sta.l SourceVisual_PreflightCount
SourceVisual_PreflightCandidate__block_next:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
    brl SourceVisual_PreflightCandidate__block_piece
SourceVisual_PreflightCandidate__block_free_start:
.a16
.i16
    lda #0
    sta.l SourceVisual_PreflightFree
    sta.l SourceVisual_BlockScan
    sep #$20
.a8
    lda #3
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__block_free:
    jsr SourceVisual_ConsumeWork
    bcs SourceVisual_PreflightCandidate__block_free_budget_ok
    brl SourceVisual_PreflightCandidate__yield
SourceVisual_PreflightCandidate__block_free_budget_ok:
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcs SourceVisual_PreflightCandidate__block_capacity
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+2,x
    beq SourceVisual_PreflightCandidate__block_slot_free
    cmp #2
    bne SourceVisual_PreflightCandidate__block_free_next
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    ora.l SourceVisual_BlockCache+7,x
    bne SourceVisual_PreflightCandidate__block_free_next8
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__block_slot_free:
    lda.l SourceVisual_PreflightFree
    inc a
    sta.l SourceVisual_PreflightFree
SourceVisual_PreflightCandidate__block_free_next:
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__block_free_next8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    bra SourceVisual_PreflightCandidate__block_free
SourceVisual_PreflightCandidate__block_capacity:
    lda.l SourceVisual_PreflightCount
    cmp.l SourceVisual_PreflightFree
    bcc SourceVisual_PreflightCandidate__palette_start
    beq SourceVisual_PreflightCandidate__palette_start
    sep #$20
.a8
    lda #$24
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_PreflightCandidate__palette_start:
.a16
.i16
    lda #0
    sta.l SourceVisual_PreflightCount
    sta.l SourceVisual_PieceIndex
    sep #$20
.a8
    lda #4
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__palette_piece:
    jsr SourceVisual_ConsumeWork
    bcs SourceVisual_PreflightCandidate__palette_piece_budget_ok
    brl SourceVisual_PreflightCandidate__yield
SourceVisual_PreflightCandidate__palette_piece_budget_ok:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceVisual_PreflightCandidate__palette_piece_ready
    brl SourceVisual_PreflightCandidate__palette_free_start
SourceVisual_PreflightCandidate__palette_piece_ready:
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+10,x
    sta.l SourceVisual_PreflightId
    lda #0
    sta.l SourceVisual_PreflightScan
    sep #$20
.a8
    lda #5
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__palette_cache_scan:
    jsr SourceVisual_ConsumeWork
    bcs SourceVisual_PreflightCandidate__palette_cache_budget_ok
    brl SourceVisual_PreflightCandidate__yield
SourceVisual_PreflightCandidate__palette_cache_budget_ok:
    lda.l SourceVisual_PreflightScan
    cmp #8
    bcs SourceVisual_PreflightCandidate__palette_seen_start
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    ora.l SourceVisual_PaletteCache+5,x
    beq SourceVisual_PreflightCandidate__palette_cache_next8
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteCache,x
    cmp.l SourceVisual_PreflightId
    beq SourceVisual_PreflightCandidate__palette_next
    bra SourceVisual_PreflightCandidate__palette_cache_next
SourceVisual_PreflightCandidate__palette_cache_next8:
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__palette_cache_next:
    lda.l SourceVisual_PreflightScan
    inc a
    sta.l SourceVisual_PreflightScan
    bra SourceVisual_PreflightCandidate__palette_cache_scan
SourceVisual_PreflightCandidate__palette_seen_start:
.a16
.i16
    lda #0
    sta.l SourceVisual_PreflightScan
    sep #$20
.a8
    lda #6
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__palette_seen:
    jsr SourceVisual_ConsumeWork
    bcs SourceVisual_PreflightCandidate__palette_seen_budget_ok
    brl SourceVisual_PreflightCandidate__yield
SourceVisual_PreflightCandidate__palette_seen_budget_ok:
    lda.l SourceVisual_PreflightScan
    cmp.l SourceVisual_PreflightCount
    bcs SourceVisual_PreflightCandidate__palette_add
    asl a
    tax
    lda.l SourceVisual_PreflightPaletteIds,x
    cmp.l SourceVisual_PreflightId
    beq SourceVisual_PreflightCandidate__palette_next
    lda.l SourceVisual_PreflightScan
    inc a
    sta.l SourceVisual_PreflightScan
    bra SourceVisual_PreflightCandidate__palette_seen
SourceVisual_PreflightCandidate__palette_add:
    lda.l SourceVisual_PreflightCount
    cmp #8
    bcs SourceVisual_PreflightCandidate__palette_invalid
    asl a
    tax
    lda.l SourceVisual_PreflightId
    sta.l SourceVisual_PreflightPaletteIds,x
    lda.l SourceVisual_PreflightCount
    inc a
    sta.l SourceVisual_PreflightCount
SourceVisual_PreflightCandidate__palette_next:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    sep #$20
.a8
    lda #4
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
    brl SourceVisual_PreflightCandidate__palette_piece
SourceVisual_PreflightCandidate__palette_free_start:
    lda #0
    sta.l SourceVisual_PreflightFree
    sta.l SourceVisual_PaletteScan
    sep #$20
.a8
    lda #7
    sta.l SourceVisual_PreflightState
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__palette_free:
    jsr SourceVisual_ConsumeWork
    bcs SourceVisual_PreflightCandidate__palette_free_budget_ok
    brl SourceVisual_PreflightCandidate__yield
SourceVisual_PreflightCandidate__palette_free_budget_ok:
    lda.l SourceVisual_PaletteScan
    cmp #8
    bcs SourceVisual_PreflightCandidate__palette_capacity
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    ora.l SourceVisual_PaletteCache+5,x
    bne SourceVisual_PreflightCandidate__palette_free_next8
    rep #$31
.a16
.i16
    lda.l SourceVisual_PreflightFree
    inc a
    sta.l SourceVisual_PreflightFree
SourceVisual_PreflightCandidate__palette_free_next:
    rep #$31
.a16
.i16
SourceVisual_PreflightCandidate__palette_free_next8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteScan
    inc a
    sta.l SourceVisual_PaletteScan
    bra SourceVisual_PreflightCandidate__palette_free
SourceVisual_PreflightCandidate__palette_invalid:
    sep #$20
.a8
    lda #$26
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_PreflightCandidate__palette_capacity:
    lda.l SourceVisual_PreflightCount
    cmp.l SourceVisual_PreflightFree
    bcc SourceVisual_PreflightCandidate__ready
    beq SourceVisual_PreflightCandidate__ready
    sep #$20
.a8
    lda #$26
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_PreflightCandidate__ready:
    sep #$20
.a8
    lda #$FF
    sta.l SourceVisual_PreflightState
SourceVisual_PreflightCandidate__ready8:
    rep #$31
.a16
.i16
    sec
    rts
SourceVisual_PreflightCandidate__yield:
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_PreflightCandidate__resume_block_piece8:
    rep #$31
.a16
.i16
    brl SourceVisual_PreflightCandidate__block_piece
SourceVisual_PreflightCandidate__resume_block_cache8:
    rep #$31
.a16
.i16
    brl SourceVisual_PreflightCandidate__block_cache_scan
SourceVisual_PreflightCandidate__resume_block_seen8:
    rep #$31
.a16
.i16
    brl SourceVisual_PreflightCandidate__block_seen
SourceVisual_PreflightCandidate__resume_block_free8:
    rep #$31
.a16
.i16
    brl SourceVisual_PreflightCandidate__block_free
SourceVisual_PreflightCandidate__resume_palette_piece8:
    rep #$31
.a16
.i16
    brl SourceVisual_PreflightCandidate__palette_piece
SourceVisual_PreflightCandidate__resume_palette_cache_scan8:
    rep #$31
.a16
.i16
    brl SourceVisual_PreflightCandidate__palette_cache_scan
SourceVisual_PreflightCandidate__resume_palette_seen8:
    rep #$31
.a16
.i16
    brl SourceVisual_PreflightCandidate__palette_seen
SourceVisual_PreflightCandidate__resume_palette_free8:
    rep #$31
.a16
.i16
    brl SourceVisual_PreflightCandidate__palette_free

SourceVisual_ReadSheet:
    sep #$20
.a8
    lda #SOURCE_VISUAL_MSU_READ_TILE
    sta.l SourceVisual_ReadRequestKind
    rep #$31
.a16
.i16
    lda.l SourceVisual_ChunkBytes
    sta.l SourceVisual_ReadRequestLength
    jmp SourceVisual_AsyncRead

SourceVisual_ReadPieces:
    sep #$20
.a8
    lda #SOURCE_VISUAL_MSU_READ_PIECES
    sta.l SourceVisual_ReadRequestKind
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_ReadRequestLength
    jsr SourceVisual_AsyncRead
    bcc SourceVisual_ReadPieces__return
    ; Publish the shared table identity only after AsyncRead completed the full
    ; descriptor. The valid byte is written last so no consumer can accept a
    ; partially copied row.
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_PieceTableEntry
    sep #$20
.a8
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_PieceTableOwner
    lda #1
    sta.l SourceVisual_PieceTableValid
    rep #$31
.a16
.i16
    sec
SourceVisual_ReadPieces__return:
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
    ; Completing a block releases the sole 1-KiB staging buffer. Yield this
    ; actor's admission for the rest of the call so another waiting actor can
    ; claim that buffer before this actor queues its next replacement block.
    sep #$20
.a8
    lda.l SourceVisual_BlockCompletedThisCall
    beq SourceVisual_PrepareBlocks__scan_start8
    brl SourceVisual_PrepareBlocks__pending
SourceVisual_PrepareBlocks__scan_start8:
    rep #$31
.a16
.i16
.a16
    ; Keep every authored piece resident and pinned: the published packet may
    ; be re-emitted at a new position while a replacement frame is pending.
    jsr SourceVisual_PinVisibleBlocks
    lda #0
    sta.l SourceVisual_PieceIndex
SourceVisual_PrepareBlocks__piece:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceVisual_PrepareBlocks__piece_in_range
    brl SourceVisual_PrepareBlocks__ready
SourceVisual_PrepareBlocks__piece_in_range:
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
    sep #$20
.a8
    lda.l SourceVisual_Error
    cmp #$27
    beq SourceVisual_PrepareBlocks__read_pending8
    rep #$31
.a16
.i16
    brl SourceVisual_PrepareBlocks__oversized
SourceVisual_PrepareBlocks__read_pending8:
    rep #$31
.a16
.i16
    brl SourceVisual_PrepareBlocks__pending
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
    ; Pin the resident/pending block in the selected published/candidate lane.
    lda.l SourceVisual_BlockRecord
    clc
    adc.l SourceVisual_OwnerOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache,x
    ora.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockRecord
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceVisual_PrepareBlocks__map_piece
    ; The sole shared staging payload is still being uploaded. Keep the
    ; frame closed until the DMA fence observes completion.
    jsr SourceVisual_QueueBlockRows
    brl SourceVisual_PrepareBlocks__pending
SourceVisual_PrepareBlocks__map_piece:
    jsr SourceVisual_MapCurrentPiece
    ; This is the candidate/primary cache-hit path after BlockCache state==2.
    ; RebuildPublishedMap also calls MapCurrentPiece, but does not count as
    ; progress for a loader owner epoch.
    sep #$20
.a8
    lda.l SourceVisual_LoaderOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_PrepareBlocks__map_piece_no_epoch_progress8
    lda #1
    sta.l SourceVisual_LoaderDurableProgress
SourceVisual_PrepareBlocks__map_piece_no_epoch_progress8:
    rep #$31
.a16
.i16
SourceVisual_PrepareBlocks__next_piece:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    brl SourceVisual_PrepareBlocks__piece
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
    lda #0
    sta.l SourceVisual_BlockScan
SourceVisual_PinVisibleBlocks__clear:
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS*8
    bcs SourceVisual_PinVisibleBlocks__clear_done
    tax
    txa
    sta.l SourceVisual_BlockRecord
    clc
    adc.l SourceVisual_OwnerOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache,x
    and.l SourceVisual_BlockOther2
    sta.l SourceVisual_BlockCache,x
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_BlockScan
    clc
    adc #8
    sta.l SourceVisual_BlockScan
    bra SourceVisual_PinVisibleBlocks__clear
SourceVisual_PinVisibleBlocks__clear_done:
.a16
.i16
    lda #0
    sta.l SourceVisual_PieceIndex
SourceVisual_PinVisibleBlocks__piece:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcs SourceVisual_PinVisibleBlocks__done
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
    clc
    adc.l SourceVisual_OwnerOffset
    tax
    sep #$20
    .a8
    lda.l SourceVisual_BlockCache,x
    ora.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache,x
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

; A cache record is {blockId:u16, state:u16, published owners:u8, progress:u8,
; payloadLoaded:u8, candidate owners:u8}. State 1 is loading, 2 is fully resident.
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
    bcc SourceVisual_AllocateBlock__slot_scan
    brl SourceVisual_AllocateBlock__fail
SourceVisual_AllocateBlock__slot_scan:
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
    ora.l SourceVisual_BlockCache+7,x
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
    lda.l SourceVisual_BlockRecord
    clc
    adc.l SourceVisual_OwnerOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_BlockCache+4,x
    sta.l SourceVisual_BlockCache+7,x
    lda.l SourceVisual_OwnerOffset
    cmp #4
    bne SourceVisual_AllocateBlock__candidate_owner
    lda.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache+4,x
    bra SourceVisual_AllocateBlock__owner_set
SourceVisual_AllocateBlock__candidate_owner:
    lda.l SourceVisual_BlockActorMask
    sta.l SourceVisual_BlockCache+7,x
SourceVisual_AllocateBlock__owner_set:
    lda #0
    sta.l SourceVisual_BlockCache+5,x
    sta.l SourceVisual_BlockCache+6,x
    rep #$31
.a16
.i16
    ; The cache record's payload-ready state is the validity tag for its
    ; per-cache continuation. Clear both halves whenever this slot is reused.
    lda.l SourceVisual_BlockRecord
    lsr a
    tax
    lda #0
    sta.l SourceVisual_BlockPayloadOffsets,x
    sta.l SourceVisual_BlockPayloadOffsets+2,x
    lda.l SourceVisual_BlockRecord
    tax
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
    sep #$20
.a8
    lda.l SourceVisual_LoaderOwner
    cmp #$FF
    beq SourceVisual_ResumePendingBlock__loader_ok8
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_ResumePendingBlock__loader_ok8
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_ResumePendingBlock__loader_ok8:
    rep #$31
.a16
.i16
    ; Cache rows are shared. Bind the resume to this actor's selected lease
    ; channel so another actor cannot claim its row with stale global identity.
    lda.l SourceVisual_ActorSlot
    and #$00FF
    cmp #6
    bcc SourceVisual_ResumePendingBlock__owner_slot_valid
    brl SourceVisual_ResumePendingBlock__none
SourceVisual_ResumePendingBlock__owner_slot_valid:
    tax
    lda #1
SourceVisual_ResumePendingBlock__owner_bit:
    cpx #0
    beq SourceVisual_ResumePendingBlock__owner_bit_ready
    asl a
    dex
    bra SourceVisual_ResumePendingBlock__owner_bit
SourceVisual_ResumePendingBlock__owner_bit_ready:
    sep #$20
.a8
    sta.l SourceVisual_BlockActorMask
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockScan
SourceVisual_ResumePendingBlock__scan:
.a16
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcc SourceVisual_ResumePendingBlock__scan_in_range
    brl SourceVisual_ResumePendingBlock__none
SourceVisual_ResumePendingBlock__scan_in_range:
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    beq SourceVisual_ResumePendingBlock__check_owner
    brl SourceVisual_ResumePendingBlock__next
SourceVisual_ResumePendingBlock__check_owner:
    txa
    clc
    adc.l SourceVisual_OwnerOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache,x
    and.l SourceVisual_BlockActorMask
    bne SourceVisual_ResumePendingBlock__owner_match8
    rep #$31
.a16
.i16
    brl SourceVisual_ResumePendingBlock__next
SourceVisual_ResumePendingBlock__owner_match8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockScan
    asl a
    asl a
    asl a
    sta.l SourceVisual_BlockRecord
    brl SourceVisual_ResumePendingBlock__found
SourceVisual_ResumePendingBlock__next:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    bra SourceVisual_ResumePendingBlock__scan
SourceVisual_ResumePendingBlock__found:
    lda.l SourceVisual_BlockScan
    sta.l SourceVisual_BlockSlot
    jsr SourceVisual_HasOwnedDma
    bcs SourceVisual_ResumePendingBlock__pending
    lda.l SourceVisual_BlockRecord
    tax
    ; BlockIndex is global scratch. Restore it from the selected cache record
    ; before QueueBlockRows can resume a row/payload lookup for this actor.
    lda.l SourceVisual_BlockCache,x
    sta.l SourceVisual_BlockIndex
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+5,x
    cmp #4
    beq SourceVisual_ResumePendingBlock__complete8
    rep #$31
.a16
.i16
    jsr SourceVisual_QueueBlockRows
    ; QueueBlockRows reaches its completed-row branch from A8. Restore the
    ; caller's width contract before returning to RenderCurrent/PrepareBlocks.
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_ResumePendingBlock__complete8:
    rep #$31
.a16
.i16
    lda #2
    sta.l SourceVisual_BlockCache+2,x
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_BlockCompletedThisCall
    rep #$31
.a16
.i16
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
    cmp #1
    beq SourceVisual_QueueBlockRows__payload_loaded8
    rep #$31
    .a16
.i16
    jsr SourceVisual_ReadBlockPayload
    bcs SourceVisual_QueueBlockRows__payload_read
    sep #$20
.a8
    lda.l SourceVisual_Error
    cmp #$27
    beq SourceVisual_QueueBlockRows__async_pending8
    rep #$31
.a16
.i16
    brl SourceVisual_QueueBlockRows__bad_payload
SourceVisual_QueueBlockRows__async_pending8:
    rep #$31
.a16
.i16
    brl SourceVisual_QueueBlockRows__pending
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

; Verify the ROM block-offset index is paired with this exact MSU catalog.
; The eight-byte SVIX footer is read once through the existing bounded reader;
; a foreign owner is queued without changing its active descriptor.
SourceVisual_EnsureCatalogBinding:
    sep #$20
.a8
    lda.l SourceVisual_CatalogBindState
    cmp #2
    bne SourceVisual_EnsureCatalogBinding__check_invalid8
    brl SourceVisual_EnsureCatalogBinding__valid8
SourceVisual_EnsureCatalogBinding__check_invalid8:
    cmp #$FF
    bne SourceVisual_EnsureCatalogBinding__check_pending8
    brl SourceVisual_EnsureCatalogBinding__invalid8
SourceVisual_EnsureCatalogBinding__check_pending8:
    cmp #1
    beq SourceVisual_EnsureCatalogBinding__already_pending8
    lda.l SourceVisual_LoaderOwner
    cmp #$FF
    beq SourceVisual_EnsureCatalogBinding__owner_available8
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_EnsureCatalogBinding__claim8
    jsr SourceVisual_QueueCurrentActor
    brl SourceVisual_EnsureCatalogBinding__pending
SourceVisual_EnsureCatalogBinding__owner_available8:
    ; A free reader may begin the single shared binding transaction.
SourceVisual_EnsureCatalogBinding__claim8:
    lda #1
    sta.l SourceVisual_CatalogBindState
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_CatalogBindOwner
    brl SourceVisual_EnsureCatalogBinding__request8
SourceVisual_EnsureCatalogBinding__already_pending8:
    lda.l SourceVisual_CatalogBindOwner
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_EnsureCatalogBinding__request8
    jsr SourceVisual_QueueCurrentActor
    brl SourceVisual_EnsureCatalogBinding__pending
SourceVisual_EnsureCatalogBinding__request8:
    lda #SOURCE_VISUAL_MSU_READ_BIND
    sta.l SourceVisual_ReadRequestKind
    rep #$31
.a16
.i16
    lda #SOURCE_VISUAL_MSU_BIND_BYTES
    sta.l SourceVisual_ReadRequestLength
    lda #((SOURCE_VISUAL_MSU_BIND_OFFSET) & $FFFF)
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda #((SOURCE_VISUAL_MSU_BIND_OFFSET >> 16) & $FF)
    sta.l SourceVisual_Offset+2
    lda #((SOURCE_VISUAL_MSU_BIND_OFFSET >> 24) & $FF)
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    jsr SourceVisual_AsyncRead
    bcs SourceVisual_EnsureCatalogBinding__read_ready
    ; Only $27 is a retryable reader result. Preserve terminal reader errors
    ; and retire this binding attempt; do not mistake a fatal error for an
    ; indefinitely pending footer transaction. The reader descriptor itself
    ; remains under AsyncRead ownership and is not discarded here.
    sep #$20
.a8
    lda.l SourceVisual_Error
    cmp #$27
    bne SourceVisual_EnsureCatalogBinding__read_fatal8
    brl SourceVisual_EnsureCatalogBinding__pending
SourceVisual_EnsureCatalogBinding__read_fatal8:
    lda #$FF
    sta.l SourceVisual_CatalogBindState
    sta.l SourceVisual_CatalogBindOwner
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_EnsureCatalogBinding__read_ready:
    sep #$20
.a8
    lda.l SourceVisual_RowScratch+0
    cmp #$53 ; 'S'
    bne SourceVisual_EnsureCatalogBinding__mismatch8
    lda.l SourceVisual_RowScratch+1
    cmp #$56 ; 'V'
    bne SourceVisual_EnsureCatalogBinding__mismatch8
    lda.l SourceVisual_RowScratch+2
    cmp #$49 ; 'I'
    bne SourceVisual_EnsureCatalogBinding__mismatch8
    lda.l SourceVisual_RowScratch+3
    cmp #$58 ; 'X'
    bne SourceVisual_EnsureCatalogBinding__mismatch8
    rep #$31
.a16
.i16
    lda.l SourceVisual_RowScratch+4
    cmp #((SOURCE_VISUAL_CATALOG_CRC32) & $FFFF)
    bne SourceVisual_EnsureCatalogBinding__mismatch
    lda.l SourceVisual_RowScratch+6
    cmp #((SOURCE_VISUAL_CATALOG_CRC32 >> 16) & $FFFF)
    bne SourceVisual_EnsureCatalogBinding__mismatch
    sep #$20
.a8
    lda #2
    sta.l SourceVisual_CatalogBindState
    lda #$FF
    sta.l SourceVisual_CatalogBindOwner
    rep #$31
.a16
.i16
    sec
    rts
SourceVisual_EnsureCatalogBinding__mismatch8:
    rep #$31
.a16
.i16
SourceVisual_EnsureCatalogBinding__mismatch:
    sep #$20
.a8
    lda #$FF
    sta.l SourceVisual_CatalogBindState
    sta.l SourceVisual_CatalogBindOwner
    lda #$23
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_EnsureCatalogBinding__invalid8:
.a8
    lda #$23
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_EnsureCatalogBinding__valid8:
    rep #$31
.a16
.i16
    sec
    rts
SourceVisual_EnsureCatalogBinding__pending:
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts

; Resolve a block ID through the immutable ROM index. The first ROM bank holds
; 10,922 packed 24-bit offsets (32,766 bytes); the remainder is in bank 81.
; Offsets are relative to the validated SVIS catalog and retain the existing
; fail-closed 256-byte tile-block policy.
SourceVisual_ReadBlockOffsetIndex:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockIndex
    cmp #SOURCE_VISUAL_BLOCK_INDEX_COUNT
    bcc SourceVisual_ReadBlockOffsetIndex__in_range
    brl SourceVisual_ReadBlockOffsetIndex__bad
SourceVisual_ReadBlockOffsetIndex__in_range:
    cmp #SOURCE_VISUAL_BLOCK_INDEX_BANK0_COUNT
    bcc SourceVisual_ReadBlockOffsetIndex__bank0
    sec
    sbc #SOURCE_VISUAL_BLOCK_INDEX_BANK0_COUNT
    sta.l SourceVisual_Temp
    asl a
    clc
    adc.l SourceVisual_Temp
    tax
    lda.l SourceVisual_BlockOffsetIndexBank1,x
    sta.l SourceVisual_Offset
    inx
    inx
    sep #$20
.a8
    lda.l SourceVisual_BlockOffsetIndexBank1,x
    sta.l SourceVisual_Offset+2
    lda #0
    sta.l SourceVisual_Offset+3
    brl SourceVisual_ReadBlockOffsetIndex__check_bound8
SourceVisual_ReadBlockOffsetIndex__bank0:
    asl a
    clc
    adc.l SourceVisual_BlockIndex
    tax
    lda.l SourceVisual_BlockOffsetIndexBank0,x
    sta.l SourceVisual_Offset
    inx
    inx
    sep #$20
.a8
    lda.l SourceVisual_BlockOffsetIndexBank0,x
    sta.l SourceVisual_Offset+2
    lda #0
    sta.l SourceVisual_Offset+3
SourceVisual_ReadBlockOffsetIndex__check_bound8:
    lda.l SourceVisual_Offset+2
    cmp #((SOURCE_VISUAL_BLOCK_INDEX_MAX_OFFSET >> 16) & $FF)
    bcc SourceVisual_ReadBlockOffsetIndex__valid8
    beq SourceVisual_ReadBlockOffsetIndex__check_low8
    brl SourceVisual_ReadBlockOffsetIndex__bad8
SourceVisual_ReadBlockOffsetIndex__check_low8:
    rep #$31
.a16
.i16
    lda.l SourceVisual_Offset
    cmp #((SOURCE_VISUAL_BLOCK_INDEX_MAX_OFFSET) & $FFFF)
    bcc SourceVisual_ReadBlockOffsetIndex__valid
    beq SourceVisual_ReadBlockOffsetIndex__valid
    brl SourceVisual_ReadBlockOffsetIndex__bad
SourceVisual_ReadBlockOffsetIndex__valid8:
    rep #$31
.a16
.i16
SourceVisual_ReadBlockOffsetIndex__valid:
    sec
    rts
SourceVisual_ReadBlockOffsetIndex__bad8:
    rep #$31
.a16
.i16
SourceVisual_ReadBlockOffsetIndex__bad:
    sep #$20
.a8
    lda #$23
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts

; Copy the catalog-bound immutable 256-byte payload to staging. A cache slot's
; state+6=2 stores the validated absolute offset so resumed reads never depend
; on shared RowScratch. The 42-byte block metadata seek is replaced by one ROM
; table lookup; the existing 512-byte budget and one MSU turn remain unchanged.
SourceVisual_ReadBlockPayload:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockRecord
    tax
    ; The actor/cache switch can leave BlockIndex from another block. The cache
    ; record is the identity authority for both the row lookup and payload.
    lda.l SourceVisual_BlockCache,x
    sta.l SourceVisual_BlockIndex
    jsr SourceVisual_EnsureCatalogBinding
    bcs SourceVisual_ReadBlockPayload__binding_valid
    rts
SourceVisual_ReadBlockPayload__binding_valid:
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+6,x
    cmp #1
    bne SourceVisual_ReadBlockPayload__check_payload8
    brl SourceVisual_ReadBlockPayload__already_ready
SourceVisual_ReadBlockPayload__check_payload8:
    cmp #2
    beq SourceVisual_ReadBlockPayload__cached_payload8
    brl SourceVisual_ReadBlockPayload__row_offset_start
SourceVisual_ReadBlockPayload__cached_payload8:
    rep #$31
.a16
.i16
    ; State +6=2 is the valid tag for this cache record's durable offset.
    ; RowScratch is shared and may now hold a different actor's block row.
    lda.l SourceVisual_BlockRecord
    lsr a
    tax
    lda.l SourceVisual_BlockPayloadOffsets,x
    sta.l SourceVisual_Offset
    lda.l SourceVisual_BlockPayloadOffsets+2,x
    sta.l SourceVisual_Offset+2
    brl SourceVisual_ReadBlockPayload__payload_offset
SourceVisual_ReadBlockPayload__row_offset_start:
    jsr SourceVisual_ReadBlockOffsetIndex
    bcc SourceVisual_ReadBlockPayload__return
    jsr SourceVisual_AddCatalogBase
    lda.l SourceVisual_BlockRecord
    lsr a
    tax
    lda.l SourceVisual_Offset
    sta.l SourceVisual_BlockPayloadOffsets,x
    lda.l SourceVisual_Offset+2
    sta.l SourceVisual_BlockPayloadOffsets+2,x
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda #2
    sta.l SourceVisual_BlockCache+6,x ; durable row/offset continuation valid
    lda.l SourceVisual_LoaderOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_ReadBlockPayload__size_ok_no_epoch_progress8
    lda #1
    sta.l SourceVisual_LoaderDurableProgress
SourceVisual_ReadBlockPayload__size_ok_no_epoch_progress8:
    rep #$31
.a16
.i16
SourceVisual_ReadBlockPayload__payload_offset:
    sep #$20
.a8
    lda #SOURCE_VISUAL_MSU_READ_TILE
    sta.l SourceVisual_ReadRequestKind
    rep #$31
.a16
.i16
    lda #SOURCE_VISUAL_TILE_BLOCK_BYTES
    sta.l SourceVisual_ReadRequestLength
    jsr SourceVisual_AsyncRead
    bcc SourceVisual_ReadBlockPayload__return
    lda.l SourceVisual_BlockRecord
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_BlockCache+6,x ; complete staging payload
    rep #$31
.a16
.i16
    sec
    rts
SourceVisual_ReadBlockPayload__already_ready:
    rep #$31
.a16
.i16
    sec
SourceVisual_ReadBlockPayload__return:
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
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda.l SourceVisual_State+19,x
    cmp #1
    bne SourceVisual_QueuePalettes__palette_row_needed8
    rep #$31
.a16
.i16
    lda.l SourceVisual_State+20,x
    cmp.l SourceVisual_PaletteGlobalIndex
    beq SourceVisual_QueuePalettes__palette_payload
    sep #$20
.a8
SourceVisual_QueuePalettes__palette_row_needed8:
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
    bcs SourceVisual_QueuePalettes__palette_row_read
    brl SourceVisual_QueuePalettes__fail
SourceVisual_QueuePalettes__palette_row_read:
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+19,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_PaletteGlobalIndex
    sta.l SourceVisual_State+20,x
SourceVisual_QueuePalettes__palette_payload:
    jsr SourceVisual_ReadPalettePayload
    bcs SourceVisual_QueuePalettes__palette_queued
    brl SourceVisual_QueuePalettes__fail
SourceVisual_QueuePalettes__palette_queued:
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_State+19,x
    rep #$31
.a16
.i16
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
    sep #$20
.a8
    lda #SOURCE_VISUAL_MSU_READ_PALETTE
    sta.l SourceVisual_ReadRequestKind
    rep #$31
.a16
.i16
    lda #32
    sta.l SourceVisual_ReadRequestLength
    jsr SourceVisual_AsyncRead
    bcs SourceVisual_ReadPalettePayload__payload_ready
    rts
SourceVisual_ReadPalettePayload__payload_ready:
    lda #11
    sta.l SourceVisual_DebugQueueStage
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
    sec
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

; Verify every visible OAM tile reference against the selected ownership lane.
; $FF is never a valid map entry; it is treated as an invariant violation.
SourceVisual_ValidateEmitMap:
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceVisual_ValidateEmitMap__mask:
.i16
    cpx #0
    beq SourceVisual_ValidateEmitMap__mask_ready
    asl a
    dex
    bra SourceVisual_ValidateEmitMap__mask
SourceVisual_ValidateEmitMap__mask_ready:
    sep #$20
.a8
    sta.l SourceVisual_BlockActorMask
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_PieceIndex
SourceVisual_ValidateEmitMap__piece:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceVisual_ValidateEmitMap__piece_in_range
    brl SourceVisual_ValidateEmitMap__valid
SourceVisual_ValidateEmitMap__piece_in_range:
    lda.l SourceVisual_PieceIndex
    clc
    adc.l SourceVisual_ActorMapBase
    tax
    sep #$20
.a8
    lda.l SourceVisual_ActorPieceMap,x
    cmp #$FF
    beq SourceVisual_ValidateEmitMap__invalid8
    rep #$31
.a16
.i16
    and #$00FF
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcs SourceVisual_ValidateEmitMap__invalid
    sta.l SourceVisual_BlockSlot
    lda.l SourceVisual_BlockSlot
    asl a
    asl a
    asl a
    sta.l SourceVisual_BlockRecord
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceVisual_ValidateEmitMap__invalid
    lda.l SourceVisual_BlockRecord
    clc
    adc.l SourceVisual_OwnerOffset
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache,x
    and.l SourceVisual_BlockActorMask
    beq SourceVisual_ValidateEmitMap__invalid8
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
    and #$01FF
    cmp.l SourceVisual_BlockTileBase
    bne SourceVisual_ValidateEmitMap__invalid
SourceVisual_ValidateEmitMap__next:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    brl SourceVisual_ValidateEmitMap__piece
SourceVisual_ValidateEmitMap__invalid8:
    rep #$31
.a16
.i16
SourceVisual_ValidateEmitMap__invalid:
    clc
    rts
SourceVisual_ValidateEmitMap__valid:
    sec
    rts

; Build one complete, un-clipped candidate from the mapped catalog rows. The
; global candidate lane is admitted one actor at a time; each row is
; {rightX:i16,rightY:i16,tile:u8,attr:u8,sizeFlags:u8}.
SourceVisual_BuildCandidatePacket:
    sep #$20
.a8
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    beq SourceVisual_BuildCandidatePacket__fresh
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_OWNER
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_BuildCandidatePacket__fresh
    rep #$31
.a16
.i16
    lda.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE
    ora.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+2
    beq SourceVisual_BuildCandidatePacket__fresh
    brl SourceVisual_BuildCandidatePacket__already_ready
SourceVisual_BuildCandidatePacket__fresh:
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceCount
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_COUNT
    lda.l SourceVisual_EntryScratch+4
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_WIDTH
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_ENTRY
    lda #0
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_FENCE+2
    sta.l SourceVisual_PieceIndex
SourceVisual_BuildCandidatePacket__piece:
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceVisual_BuildCandidatePacket__piece_ready
    brl SourceVisual_BuildCandidatePacket__publish
SourceVisual_BuildCandidatePacket__piece_ready:
    ; Source row offset = piece*16; packet offset = piece*7.
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_PieceOffset
    tax
    lda.l SourceVisual_PieceIndex
    sta.l SourceVisual_PacketCopyCount
    asl a
    asl a
    asl a
    sec
    sbc.l SourceVisual_PacketCopyCount
    sta.l SourceVisual_PacketDataIndex
    lda.l SourceVisual_PieceTable,x
    sta.l SourceVisual_PacketSpriteRelX
    lda.l SourceVisual_PieceTable+2,x
    sta.l SourceVisual_PacketDeltaY
    lda.l SourceVisual_PacketDataIndex
    tax
    lda.l SourceVisual_PacketSpriteRelX
    sta.l SourceVisual_CandidatePacketData,x
    lda.l SourceVisual_PacketDataIndex
    clc
    adc #2
    tax
    lda.l SourceVisual_PacketDeltaY
    sta.l SourceVisual_CandidatePacketData,x
    ; Preserve the authored left-facing position as signed offsets too. The
    ; published fallback must not synthesize it from a frame width or any
    ; mutable candidate-table state while a replacement is pending.
SourceVisual_BuildCandidatePacket__capture_left:
    lda.l SourceVisual_PieceOffset
    tax
    lda.l SourceVisual_PieceTable+4,x
    sta.l SourceVisual_PacketLeftX
    lda.l SourceVisual_PieceTable+6,x
    sta.l SourceVisual_PacketLeftY
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    tax
    lda.l SourceVisual_PacketLeftX
    sta.l SourceVisual_CandidateLeftGeometry,x
    inx
    inx
    lda.l SourceVisual_PacketLeftY
    sta.l SourceVisual_CandidateLeftGeometry,x
SourceVisual_BuildCandidatePacket__left_saved:
    lda.l SourceVisual_PieceOffset
    tax
    lda.l SourceVisual_PieceTable+14,x
    and #$01FF
    clc
    adc.l SourceVisual_BaseTile
    sta.l SourceVisual_PacketTotal
    lda.l SourceVisual_PacketDataIndex
    clc
    adc #4
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketTotal
    sta.l SourceVisual_CandidatePacketData,x
    ; Palette mapping is one-based in the actor row; OAM attribute palette
    ; bits are zero-based and normalized to right-facing (H-flip clear).
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceOffset
    tax
    lda.l SourceVisual_PieceTable+8,x
    and #$00FF
    clc
    adc.l SourceVisual_Record
    clc
    adc #16
    tax
    sep #$20
.a8
    lda.l SourceVisual_State,x
    bne SourceVisual_BuildCandidatePacket__palette_ready
    brl SourceVisual_BuildCandidatePacket__bad_palette
SourceVisual_BuildCandidatePacket__palette_ready:
    dec a
    asl a
    ora #$30
    sta.l SourceVisual_PacketSpriteAttr
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketTotal
    and #$0100
    beq SourceVisual_BuildCandidatePacket__name_ready
    sep #$20
.a8
    lda.l SourceVisual_PacketSpriteAttr
    ora #$01
    sta.l SourceVisual_PacketSpriteAttr
    rep #$31
.a16
.i16
SourceVisual_BuildCandidatePacket__name_ready:
    sep #$20
.a8
SourceVisual_BuildCandidatePacket__priority_ready:
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketDataIndex
    clc
    adc #5
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketSpriteAttr
    sta.l SourceVisual_CandidatePacketData,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceOffset
    tax
    lda.l SourceVisual_PieceTable+14,x
    and #$8000
    beq SourceVisual_BuildCandidatePacket__small
    sep #$20
.a8
    lda #2
    bra SourceVisual_BuildCandidatePacket__size_ready
SourceVisual_BuildCandidatePacket__small:
    sep #$20
.a8
    lda #0
SourceVisual_BuildCandidatePacket__size_ready:
    sta.l SourceVisual_PacketSpriteHigh
    rep #$31
.a16
.i16
    lda.l SourceVisual_PacketDataIndex
    clc
    adc #6
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketSpriteHigh
    sta.l SourceVisual_CandidatePacketData,x
    rep #$31
.a16
.i16
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    brl SourceVisual_BuildCandidatePacket__piece
SourceVisual_BuildCandidatePacket__publish:
    ; Publish metadata only after every authored descriptor is complete.
    lda.l SourceVisual_ActorSlot
    sep #$20
.a8
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_OWNER
    lda #1
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    rep #$31
.a16
.i16
    sec
    rts
SourceVisual_BuildCandidatePacket__already_ready:
    sec
    rts
SourceVisual_BuildCandidatePacket__bad_palette:
    rep #$31
.a16
.i16
    clc
    rts

SourceVisual_Emit:
    rep #$31
.a16
.i16
    lda.l Oam_CurrentSlot
    sta.l SourceVisual_EmitOamStart
    lda CHAR_POS_Y
    sta.l SourceVisual_EmitActorY
    lda.l SourceVisual_EntryScratch+4
    sta.l SourceVisual_EmitFrameWidth
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
    lda.l SourceVisual_PieceIndex
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
    ; Validate every live tile/palette mapping before writing the first OAM
    ; byte. This makes a successful Emit a complete packet commit, never a
    ; partial candidate followed by a fallback over a half-written buffer.
    jsr SourceVisual_ValidateEmitMap
    bcs SourceVisual_Emit__tile_map_valid
    brl SourceVisual_Emit__tile_fail
SourceVisual_Emit__tile_map_valid:
    jsr SourceVisual_ValidatePaletteMap
    bcs SourceVisual_Emit__palette_map_valid
    brl SourceVisual_Emit__palette_fail_before_write
SourceVisual_Emit__palette_map_valid:
    ; A single full-packet staging row is sufficient because only one
    ; candidate may be published per OAM field. Other candidates keep their
    ; prior published rows and receive explicit status-4 backpressure.
    sep #$20
.a8
    lda.l SourceVisual_UseCandidate
    beq SourceVisual_Emit__candidate_lane_ready8
    lda.l SourceVisual_PacketCandidateOwner
    cmp #$FF
    beq SourceVisual_Emit__candidate_lane_claim
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_Emit__candidate_lane_ready8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_Emit__candidate_lane_claim:
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_PacketCandidateOwner
SourceVisual_Emit__candidate_lane_ready8:
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_PieceIndex
    bra SourceVisual_Emit__piece
SourceVisual_Emit__tile_fail:
    sep #$20
.a8
    lda #$29
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_Emit__palette_fail_before_write:
    sep #$20
.a8
    lda #$2A
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    clc
    rts
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
    sep #$20
.a8
    lda.l OamSetSprite_Hi
    ora #$80
    sta.l OamSetSprite_Hi
    rep #$31
.a16
.i16
    jsr SourceVisual_WriteCurrentPiece
SourceVisual_Emit__next_piece:
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    jmp SourceVisual_Emit__piece
SourceVisual_Emit__done:
.a16
    sep #$20
.a8
    lda.l SourceVisual_UseCandidate
    beq SourceVisual_Emit__packet_record
    rep #$31
.a16
.i16
    jsr SourceVisual_BuildCandidatePacket
    bcs SourceVisual_Emit__packet_record
    ; No OAM bytes have been committed when packet construction fails; roll
    ; back the append cursor and release admission before returning failure.
    lda.l SourceVisual_EmitOamStart
    sta.l Oam_CurrentSlot
    sep #$20
.a8
    lda #$FF
    sta.l SourceVisual_PacketCandidateOwner
    lda #0
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    rep #$31
.a16
.i16
    clc
    rts
SourceVisual_Emit__packet_record:
    rep #$31
.a16
.i16
    sep #$20
    .a8
    lda.l SourceVisual_UseCandidate
    beq SourceVisual_Emit__record_frame
    rep #$31
    .a16
    .i16
    jsr SourceVisual_CandidateActionMatches
    bcs SourceVisual_Emit__record_frame
    ; The built packet has not been recorded/submitted yet. Roll back only this
    ; actor's appended shadow OAM. A replacement keeps its candidate lease
    ; pinned for normal identity retirement; an initial packet has no prior
    ; frame to fall back to, so abort its candidate lease here. A submitted
    ; DMA is never cancelled here.
    lda.l SourceVisual_EmitOamStart
    sta.l Oam_CurrentSlot
    sep #$20
    .a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$31
    .a16
    .i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
    .a8
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    bne SourceVisual_Emit__stale_replacement8
    rep #$31
    .a16
    .i16
    jsr SourceVisual_AbortInitialPacket
    clc
    rts
SourceVisual_Emit__stale_replacement8:
.a8
.i16
    lda #$FF
    sta.l SourceVisual_PacketCandidateOwner
    lda #0
    sta.l SourceVisual_CandidatePacketMeta+SOURCE_VISUAL_PACKET_META_VALID
    rep #$31
    .a16
    .i16
    clc
    rts
SourceVisual_Emit__record_frame:
    rep #$31
    .a16
    .i16
    jsr SourceVisual_RecordFramePacket
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


; A reservation is a bounded six-slot round-robin token. It remains until the
; reserved actor claims the stream or proves its request already published.
SourceVisual_PriorityGate:
    php
    rep #$30
.a16
.i16
    pha
    phx
    sep #$20
.a8
    lda.l SourceVisual_PlayerPriorityOwner
    cmp #$FF
    beq SourceVisual_PriorityGate__allow8
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_PriorityGate__allow8
    lda.l SourceVisual_LoaderOwner
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_PriorityGate__allow8
    lda.l SourceVisual_FindScanActive
    beq SourceVisual_PriorityGate__blocked8
    lda.l SourceVisual_FindScanOwner
    cmp.l SourceVisual_ActorSlot
    beq SourceVisual_PriorityGate__allow8
SourceVisual_PriorityGate__blocked8:
    jsr SourceVisual_QueueCurrentActor
    rep #$30
.a16
.i16
    plx
    pla
    plp
    clc
    rts
SourceVisual_PriorityGate__allow8:
    rep #$30
.a16
.i16
    plx
    pla
    plp
    sec
    rts

; Preserve a new key while its current immutable descriptor is in flight.
SourceVisual_QueueChangedLoaderKey:
    php
    rep #$30
.a16
.i16
    pha
    phx
    sep #$20
.a8
    lda.l SourceVisual_LoaderOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_QueueChangedLoaderKey__done8
    rep #$30
.a16
.i16
    lda.l SourceVisual_Key
    cmp.l SourceVisual_LoaderKey
    bne SourceVisual_QueueChangedLoaderKey__enqueue
    lda.l SourceVisual_Key+2
    cmp.l SourceVisual_LoaderKey+2
    beq SourceVisual_QueueChangedLoaderKey__done
SourceVisual_QueueChangedLoaderKey__enqueue:
    jsr SourceVisual_QueueCurrentActor
    bra SourceVisual_QueueChangedLoaderKey__done
SourceVisual_QueueChangedLoaderKey__done8:
    rep #$30
.a16
.i16
SourceVisual_QueueChangedLoaderKey__done:
    plx
    pla
    plp
    rts

; Only CHAR_INPUT_DRIVEN==1 is a player; slot numbers are not ownership.
SourceVisual_RequestPlayerPriority:
    php
    rep #$30
.a16
.i16
    pha
    phx
    sep #$20
.a8
    lda CHAR_INPUT_DRIVEN
    cmp #1
    bne SourceVisual_RequestPlayerPriority__done8
    rep #$30
.a16
.i16
    lda.l SourceVisual_ActorSlot
    and #$00FF
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PacketMeta+SOURCE_VISUAL_PACKET_META_VALID,x
    beq SourceVisual_RequestPlayerPriority__done8
    rep #$30
.a16
.i16
    lda.l SourceVisual_ActorSlot
    and #$00FF
    asl a
    asl a
    tax
    lda.l SourceVisual_Key
    cmp.l SourceVisual_PublishedKey,x
    bne SourceVisual_RequestPlayerPriority__changed
    lda.l SourceVisual_Key+2
    cmp.l SourceVisual_PublishedKey+2,x
    beq SourceVisual_RequestPlayerPriority__done
SourceVisual_RequestPlayerPriority__changed:
    jsr SourceVisual_QueueCurrentActor
    sep #$20
.a8
    lda.l SourceVisual_PlayerPriorityOwner
    cmp #$FF
    bne SourceVisual_RequestPlayerPriority__done8
    ; Do not mint another player token while a different actor is already
    ; waiting. The queue's next release grants that actor before the player's
    ; next changed key can reserve the stream again.
    rep #$31
.a16
.i16
    lda.l SourceVisual_ActorSlot
    and #$00FF
    tax
    sep #$20
.a8
    lda.l SourceVisual_ActorWaitBits,x
    eor #$FF
    and.l SourceVisual_WaitingActorMask
    bne SourceVisual_RequestPlayerPriority__done8
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_PlayerPriorityOwner
SourceVisual_RequestPlayerPriority__done8:
    rep #$30
.a16
.i16
SourceVisual_RequestPlayerPriority__done:
    plx
    pla
    plp
    rts

; One request bit per actor; latest keys are recomputed on that actor's turn.
SourceVisual_QueueCurrentActor:
    php
    rep #$30
.a16
.i16
    pha
    phx
    lda.l SourceVisual_ActorSlot
    and #$00FF
    cmp #6
    bcs SourceVisual_QueueCurrentActor__done
    tax
    sep #$20
.a8
    lda.l SourceVisual_ActorWaitBits,x
    ora.l SourceVisual_WaitingActorMask
    sta.l SourceVisual_WaitingActorMask
    rep #$30
.a16
.i16
SourceVisual_QueueCurrentActor__done:
    plx
    pla
    plp
    rts

SourceVisual_ClearQueuedActor:
    php
    rep #$30
.a16
.i16
    pha
    phx
    lda.l SourceVisual_ActorSlot
    and #$00FF
    cmp #6
    bcs SourceVisual_ClearQueuedActor__done
    tax
    sep #$20
.a8
    lda.l SourceVisual_ActorWaitBits,x
    eor #$FF
    and.l SourceVisual_WaitingActorMask
    sta.l SourceVisual_WaitingActorMask
    lda.l SourceVisual_PlayerPriorityOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_ClearQueuedActor__done8
    lda #$FF
    sta.l SourceVisual_PlayerPriorityOwner
    lda.l SourceVisual_LoaderOwner
    cmp #$FF
    bne SourceVisual_ClearQueuedActor__done8
    jsr SourceVisual_GrantNextQueuedActor
SourceVisual_ClearQueuedActor__done8:
    rep #$30
.a16
.i16
SourceVisual_ClearQueuedActor__done:
    plx
    pla
    plp
    rts

; A fresh AsyncRead owner claim consumes this actor's queue bit and grant.
SourceVisual_ClaimQueuedActor:
    php
    rep #$30
.a16
.i16
    pha
    phx
    lda.l SourceVisual_ActorSlot
    and #$00FF
    cmp #6
    bcs SourceVisual_ClaimQueuedActor__done
    tax
    sep #$20
.a8
    lda.l SourceVisual_ActorWaitBits,x
    eor #$FF
    and.l SourceVisual_WaitingActorMask
    sta.l SourceVisual_WaitingActorMask
    lda.l SourceVisual_ActorSlot
    sta.l SourceVisual_QueueCursor
SourceVisual_ClaimQueuedActor__done8:
    rep #$30
.a16
.i16
SourceVisual_ClaimQueuedActor__done:
    plx
    pla
    plp
    rts

; Reserve the next waiter after a reader releases a completed descriptor.
; The reservation remains until that actor starts a seek or consumes ready
; bytes; then other waiters advance by bounded round-robin.
SourceVisual_GrantNextQueuedActor:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    sep #$20
.a8
    lda.l SourceVisual_PlayerPriorityOwner
    cmp #$FF
    beq SourceVisual_GrantNextQueuedActor__select
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_GrantNextQueuedActor__done8
    lda #$FF
    sta.l SourceVisual_PlayerPriorityOwner
SourceVisual_GrantNextQueuedActor__select:
    rep #$30
.a16
.i16
    lda.l SourceVisual_QueueCursor
    and #$00FF
    inc a
    cmp #6
    bcc SourceVisual_GrantNextQueuedActor__start
    lda #0
SourceVisual_GrantNextQueuedActor__start:
    tax
    ldy #6
SourceVisual_GrantNextQueuedActor__scan:
    sep #$20
.a8
    lda.l SourceVisual_ActorWaitBits,x
    and.l SourceVisual_WaitingActorMask
    bne SourceVisual_GrantNextQueuedActor__found8
    rep #$30
.a16
.i16
    inx
    cpx #6
    bcc SourceVisual_GrantNextQueuedActor__index_ok
    ldx #0
SourceVisual_GrantNextQueuedActor__index_ok:
    dey
    bne SourceVisual_GrantNextQueuedActor__scan
    sep #$20
.a8
    lda #$FF
    sta.l SourceVisual_PlayerPriorityOwner
    bra SourceVisual_GrantNextQueuedActor__done8
SourceVisual_GrantNextQueuedActor__found8:
    txa
    sta.l SourceVisual_PlayerPriorityOwner
SourceVisual_GrantNextQueuedActor__done8:
    rep #$30
.a16
.i16
SourceVisual_GrantNextQueuedActor__done:
    ply
    plx
    pla
    plp
    rts

SourceVisual_ActorWaitBits:
    .db $01, $02, $04, $08, $10, $20

; Consume a priority reservation only when AsyncRead has real I/O progress.
; Preserve the caller's accumulator, width flags, and other processor state.
SourceVisual_ConsumePriorityTurn:
    php
    rep #$30
.a16
.i16
    pha
    sep #$20
.a8
    lda.l SourceVisual_PlayerPriorityOwner
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_ConsumePriorityTurn__done8
    lda #$FF
    sta.l SourceVisual_PlayerPriorityOwner
SourceVisual_ConsumePriorityTurn__done8:
    rep #$30
.a16
.i16
    pla
    plp
    rts

