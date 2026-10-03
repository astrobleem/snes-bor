; ============================================================================
; core/stream_cache.pasm — Phase 9 (plan.md 2.7) streaming BG1 tile cache
;
; A level too wide to fit its whole tileset in VRAM (warehouse: 13,437
; distinct tiles against a ~1023-slot VRAM budget) needs a ring buffer: only
; the tiles actually near the camera are VRAM-resident at any moment, and
; the tilemap the engine streams in refers to tiles by a stable LEVEL tile
; ID, not a VRAM slot -- see bg_converter/snes_tiles.py's
; encode_tilemap_cache_entry for the on-disk format this reads.
;
; Ported (redesigned for snes-bor's constraints, not a literal port) from
; SNES-SuperMonkeyIsland's room_scroll.65816/room_cache.h, a real shipped
; 65816 SNES engine that solved the identical problem. Two real differences
; from that source, both load-bearing:
;   - SMI caps a room at 2048 distinct tile IDs and keeps its WHOLE tilemap
;     resident in WRAM. snes-bor's level (composited whole, all 21.5 screens
;     of warehouse at once) measured 13,437 -- SMI's design doesn't fit.
;     Tile2Slot here is sized STREAM_MAX_TILE_IDS (16384) entries, and the
;     tilemap itself stays in the MSU-1 blob, seeked column-by-column
;     (StageColumn, not yet written) rather than held resident.
;   - SMI packs (tile_id | stamp<<11) into one 16-bit Slot2Tile entry. That
;     only leaves 5 stamp bits when tile IDs need 11. snes-bor's tile IDs
;     need up to 16 bits, so Slot2Tile and SlotStamp are kept as two
;     separate arrays instead of one bit-packed word -- costs ~1KB more
;     WRAM, avoids the kind of bit-packing arithmetic that has bitten this
;     project's Poppy build before (see CLAUDE.md's checklist).
;
; This module owns allocation/eviction only (Core_StreamCache_Init,
; Core_StreamCache_AllocateSlot). It does not touch MSU-1 or VRAM -- that is
; StageColumn's job, a separate not-yet-written piece that calls this to get
; a slot for each cache-miss tile it fetches.
;
; Indexed WRAM/bank-$7F access uses `.l` (or bare) throughout, never `.w` --
; see core/dma_channel.pasm's header for why `.w` on an indexed non-zero-bank
; symbol silently corrupts the instruction stream in this Poppy build. Uses
; global (not @-local) labels throughout, matching every other core/*.pasm
; file's convention for the same reason (local labels mis-resolve once
; .include'd).
; ============================================================================

; --- Ring buffer sizing ---
; BG1 spans 1024 4bpp slots at words $0000-$3FFF. Slot 0 is the known blank.
; Stage-scoped reservations keep allocations out of BG3 and active BG2 owners.
STREAM_CACHE_SLOTS   = 1024
STREAM_CACHE_USABLE  = 1023      ; slots 1..1023 before stage reservations
STREAM_CACHE_STRIDE  = 337       ; coprime with 1023 (=3*11*31; 337 is prime
                                   ; and shares no factor) -- advances the
                                   ; persistent scan cursor BETWEEN calls so
                                   ; successive allocations don't all start
                                   ; scanning from the same ring position.
; STREAM_CACHE_SCAN_LIMIT: candidates probed before forced eviction. Set to
; the FULL usable ring (not a small window) -- found necessary, not just
; conservative, via Bg_LoadScene_Streaming's real bulk load (~755 distinct
; tiles for warehouse's initial 32-column viewport): StreamCache_CurrentStamp
; never advances until SyncScroll (plan.md Phase 9 step 4) exists, so the
; protection-window check below is degenerate right now -- EVERY occupied
; slot's stamp distance is 0 (< STREAM_CACHE_PROTECT_WINDOW), so every
; occupied slot looks "just touched" and nothing is ever evictable. With a
; 64-candidate limit, once the stride-337 cursor's 64-slot scan window
; started overlapping earlier allocations, the scan exhausted its budget
; without ever reaching one of the hundreds of still-free slots elsewhere in
; the ring, and force-evicted a slot that didn't need evicting at all --
; caught by phase9_stagecolumn_spotcheck.py (tile IDs correctly decoded and
; attributed, but slot 64 kept recurring across many distinct real tile IDs,
; and Tile2Slot entries for already-allocated tiles were silently wiped by
; those spurious evictions). A full-ring scan guarantees finding a genuinely
; free slot whenever one exists, independent of the degenerate protection
; check. Once SyncScroll makes CurrentStamp advance for real, protection
; becomes meaningful again and a smaller limit may be worth revisiting for
; per-frame scan cost -- re-verify then, don't assume this value is final.
STREAM_CACHE_SCAN_LIMIT = STREAM_CACHE_USABLE
STREAM_CACHE_PROTECT_WINDOW = 16

; A streamed level's distinct-tile-ID ceiling. Sized for warehouse
; (13,437 measured, plan.md Phase 9) with headroom; bump and rebuild if a
; future level needs more -- this is a build-time constant, not something
; sized per-level at runtme, because WRAM is allocated statically.
STREAM_MAX_TILE_IDS = 16384

; --- Bank $7F tables (grep-confirmed unused by anything else in this
; project as of Phase 9 -- see plan.md's Phase 9 finding) ---
StreamCache_Tile2Slot = $7F0000   ; STREAM_MAX_TILE_IDS words (32768 bytes,
                                    ; $7F0000-$7F7FFF): tile ID -> VRAM slot,
                                    ; or $FFFF if not cached.
StreamCache_Slot2Tile = $7F8000   ; STREAM_CACHE_SLOTS words (2048 bytes,
                                    ; $7F8000-$7F87FF): VRAM slot -> tile ID,
                                    ; or $FFFF if free.
StreamCache_SlotStamp = $7F8800   ; STREAM_CACHE_SLOTS bytes
                                    ; ($7F8800-$7F8BFF): VRAM slot -> the
                                    ; StreamCache_CurrentStamp value at the
                                    ; time it was last allocated/touched.

; --- Small $7E scratch ---
StreamCache_CurrentStamp = $7E2500   ; .db -- advanced externally (SyncScroll,
                                       ; not yet written); this module only
                                       ; reads it.
StreamCache_ScanCursor   = $7E2501   ; .dw -- persists across calls
StreamCache_NewTileId    = $7E2503   ; .dw -- AllocateSlot's stashed param
StreamCache_Candidate    = $7E2505   ; .dw
StreamCache_Chosen       = $7E2507   ; .dw
StreamCache_OldTile      = $7E2509   ; .dw
; Smoke-test-only scratch (see the bottom of this file) -- not touched by
; Init/AllocateSlot themselves.
StreamCache_Test_Results = $7E250B   ; .dw x 8 -- allocated slots from a
                                       ; synthetic access pattern
STREAM_CACHE_TEST_RESULTS_COUNT = 8
StreamCache_Test_Index = $7E251B     ; .dw -- loop index (see Core_StreamCache_Test)
StreamCache_Test_Slot  = $7E251D     ; .dw -- scratch for this iteration's result
StreamCache_Test_CallCount = $7E251F ; .dw -- counts AllocateSlot entries total
                                       ; (not just this test's 8) -- cheap,
                                       ; kept permanently as a quick sanity
                                       ; check when debugging future callers.
; Mode flags occupy the verified three-byte gap between StreamScroll's
; FetchBufSel ($7E2599) and the frontpanel cache state ($7E25A0 onward).
; Do not place these beside the cache allocator scratch: $7E2521-$7E2523
; belongs to StreamScroll_Enabled/StagedLo, and aliasing it breaks the first
; BG1 MSU seek during cold boot.
StreamCache_NormalLayout = $7E259A ; .db -- Normal reclaims legacy BG3 FP cache
StreamCache_BG2Capacity = $7E259B ; .db -- Normal BG2 cache slots admitted
StreamCache_LegacyFpActive = $7E259C ; .db -- Easy retains BG3 FP cache ownership

Core_StreamCache_Init:
	php
	sei
	rep #$31
.a16
.i16
	; NOTE: STZ/INC have no absolute-LONG addressing mode on real 65816 --
	; Poppy accepts `stz Symbol`/`inc Symbol` for a bank-$7E symbol anyway
	; and silently emits the absolute (2-byte, DBR-relative) form instead
	; of erroring, which during boot (DBR=$00) targets bank $00, not $7E --
	; same bug class CLAUDE.md already documents for STZ specifically, that
	; this file's first version missed also applies to INC/DEC/STX/STY.
	; LDA/STA DO have a long form and Poppy correctly auto-selects it for
	; these same symbols (confirmed via disassembly) -- so every site
	; below uses `lda #.. / sta Symbol` or `lda Symbol / inc a / sta
	; Symbol` instead.
	lda #1
	sta StreamCache_ScanCursor      ; cursor starts at slot 1 (0 is reserved)
	lda #0
	sta StreamCache_Test_CallCount  ; see its declaration's comment above
	sta.l StreamCache_NormalLayout
	sta.l StreamCache_BG2Capacity
	sta.l StreamCache_LegacyFpActive

	lda #$FFFF
	ldx #0
Core_StreamCache_Init__tile2slot:
	sta.l StreamCache_Tile2Slot,x
	inx
	inx
	cpx #STREAM_MAX_TILE_IDS*2
	bcc Core_StreamCache_Init__tile2slot

	lda #$FFFF
	ldx #0
Core_StreamCache_Init__slot2tile:
	sta.l StreamCache_Slot2Tile,x
	inx
	inx
	cpx #STREAM_CACHE_SLOTS*2
	bcc Core_StreamCache_Init__slot2tile

	sep #$20
.a8
	lda #0
	sta StreamCache_CurrentStamp
	rep #$31
.a16
.i16
	lda #0
	ldx #0
Core_StreamCache_Init__slotstamp:
	sep #$20
.a8
	sta.l StreamCache_SlotStamp,x
	rep #$31
.a16
.i16
	inx
	cpx #STREAM_CACHE_SLOTS
	bcc Core_StreamCache_Init__slotstamp

	plp
	rep #$31
.a16
.i16
	rts

; Allocates a VRAM cache slot for a tile ID the caller has already confirmed
; is a cache miss (StreamCache_Tile2Slot[tile_id] == $FFFF -- this routine
; does not check for an existing hit). Evicts an existing slot if nothing is
; free, protecting slots touched within STREAM_CACHE_PROTECT_WINDOW of the
; current stamp where the scan budget allows.
; @param X<16-bit>  tile_id to allocate a slot for (0..STREAM_MAX_TILE_IDS-1)
; @return A<16-bit>  the allocated slot number (1..STREAM_CACHE_USABLE)
; Clobbers X, Y.
Core_StreamCache_AllocateSlot:
	php
	sei
	rep #$31
.a16
.i16
	; lda/inc a/sta, not `inc` directly -- see the header note on
	; Core_StreamCache_Init.
	lda StreamCache_Test_CallCount
	inc a
	sta StreamCache_Test_CallCount
	; STX has no long-addressing mode either -- txa/sta instead of
	; `stx StreamCache_NewTileId` (same bug class, see above).
	txa
	sta StreamCache_NewTileId

	; This call's scan starts at the current cursor; advance the persisted
	; cursor by STREAM_CACHE_STRIDE now so the NEXT call starts elsewhere.
	lda StreamCache_ScanCursor
	sta StreamCache_Candidate
	clc
	adc #STREAM_CACHE_STRIDE
	cmp #STREAM_CACHE_USABLE+1
	bcc Core_StreamCache_AllocateSlot__cursor_ok
	sec
	sbc #STREAM_CACHE_USABLE
Core_StreamCache_AllocateSlot__cursor_ok:
	sta StreamCache_ScanCursor

	ldy #0                          ; scan counter
Core_StreamCache_AllocateSlot__scan:
rep #$31
.a16
.i16
	lda StreamCache_Candidate
	jsl Core_StreamCache_IsReserved
	bcs Core_StreamCache_AllocateSlot__advance
	; Slot2Tile[candidate] -- word index -> byte offset
	lda StreamCache_Candidate
	asl a
	tax
	lda.l StreamCache_Slot2Tile,x
	cmp #$FFFF
	beq Core_StreamCache_AllocateSlot__found

	; occupied -- check protection window (8-bit modular distance). The
	; CMP/branch decision is made HERE, still in 8-bit mode, deliberately --
	; `rep #$31` (used everywhere else in this file to return to 16-bit)
	; clears the carry flag (bit 0 of its #$31 operand), so testing this
	; CMP's carry AFTER switching width back would read a clobbered value,
	; not the comparison result.
	lda StreamCache_Candidate
	tax                              ; byte index for SlotStamp (== candidate,
                                        ; NOT candidate*2 -- SlotStamp is a
                                        ; byte array, Slot2Tile a word array)
	sep #$20
.a8
	lda StreamCache_CurrentStamp
	sec
	sbc.l StreamCache_SlotStamp,x
	cmp #STREAM_CACHE_PROTECT_WINDOW
	bcc Core_StreamCache_AllocateSlot__protected

	rep #$31
.a16
.i16
Core_StreamCache_AllocateSlot__evictable:
	lda StreamCache_Candidate
	sta StreamCache_Chosen
	bra Core_StreamCache_AllocateSlot__allocate

Core_StreamCache_AllocateSlot__protected:
	rep #$31
.a16
.i16
	bra Core_StreamCache_AllocateSlot__advance

Core_StreamCache_AllocateSlot__found:
	rep #$31
.a16
.i16
	lda StreamCache_Candidate
	sta StreamCache_Chosen
	bra Core_StreamCache_AllocateSlot__allocate

Core_StreamCache_AllocateSlot__advance:
	rep #$31
.a16
.i16
	lda StreamCache_Candidate
	inc a
	cmp #STREAM_CACHE_USABLE+1
	bcc Core_StreamCache_AllocateSlot__advance_ok
	lda #1
Core_StreamCache_AllocateSlot__advance_ok:
	sta StreamCache_Candidate

	iny
	cpy #STREAM_CACHE_SCAN_LIMIT
	bcc Core_StreamCache_AllocateSlot__scan

	; scan budget exhausted -- force-evict a legal slot, never a live owner.
	brl Core_StreamCache_AllocateSlot__force_find
Core_StreamCache_AllocateSlot__force_find:
	lda StreamCache_Candidate
	jsl Core_StreamCache_IsReserved
	bcc Core_StreamCache_AllocateSlot__force_choose
	lda StreamCache_Candidate
	inc a
	cmp #STREAM_CACHE_USABLE+1
	bcc Core_StreamCache_AllocateSlot__force_next
	lda #1
Core_StreamCache_AllocateSlot__force_next:
	sta StreamCache_Candidate
	bra Core_StreamCache_AllocateSlot__force_find
Core_StreamCache_AllocateSlot__force_choose:
	lda StreamCache_Candidate
	sta StreamCache_Chosen

Core_StreamCache_AllocateSlot__allocate:
	rep #$31
.a16
.i16
	; If the chosen slot was occupied, clear the old tile's Tile2Slot entry
	; first -- otherwise that tile ID would keep reporting itself cached at
	; a slot it no longer occupies.
	lda StreamCache_Chosen
	asl a
	tax
	lda.l StreamCache_Slot2Tile,x
	cmp #$FFFF
	beq Core_StreamCache_AllocateSlot__no_evict
	sta StreamCache_OldTile
	lda StreamCache_OldTile
	asl a
	tax
	lda #$FFFF
	sta.l StreamCache_Tile2Slot,x

Core_StreamCache_AllocateSlot__no_evict:
	lda StreamCache_Chosen
	asl a
	tax
	lda StreamCache_NewTileId
	sta.l StreamCache_Slot2Tile,x

	lda StreamCache_Chosen
	tax                              ; byte-indexed for SlotStamp
	sep #$20
.a8
	lda StreamCache_CurrentStamp
	sta.l StreamCache_SlotStamp,x
	rep #$31
.a16
.i16

	lda StreamCache_NewTileId
	asl a
	tax
	lda StreamCache_Chosen
	sta.l StreamCache_Tile2Slot,x

	lda StreamCache_Chosen

	plp
	rep #$31
.a16
.i16
	rts

; Carry set means the physical BG1 tile slot is owned by another live layer.
; Normal reclaims the legacy BG3 foreground-cache band for BG1; Easy retains
; that band only while its legacy foreground is active.
; Bank $0C has grown through the former $8B00 helper address (scene-video
; frame loading now occupies that range). Keep this shared allocator helper
; in a dedicated ROM bank so later bank-$0C growth cannot replace its bytes
; while leaving the symbol table apparently intact.
.bank 27
.org $8000
Core_StreamCache_IsReserved:
	rep #$30
.a16
.i16
	lda StreamCache_Candidate
	cmp #512
	bcc Core_StreamCache_IsReserved__legacy
	cmp #518
	bcc Core_StreamCache_IsReserved__yes ; BG3 HUD words $2000-$205F
Core_StreamCache_IsReserved__legacy:
	sep #$20
.a8
	lda.l StreamCache_NormalLayout
	bne Core_StreamCache_IsReserved__font
	lda.l StreamCache_LegacyFpActive
	beq Core_StreamCache_IsReserved__font
	rep #$30
.a16
.i16
	lda StreamCache_Candidate
	cmp #528
	bcc Core_StreamCache_IsReserved__font
	cmp #656
	bcc Core_StreamCache_IsReserved__yes ; Easy legacy BG3 foreground cache
Core_StreamCache_IsReserved__font:
	rep #$30
.a16
.i16
	lda StreamCache_Candidate
	cmp #656
	bcc Core_StreamCache_IsReserved__bg2
	cmp #704
	bcc Core_StreamCache_IsReserved__yes ; BG3 font words $2900-$2BF7
Core_StreamCache_IsReserved__bg2:
	sep #$20
.a8
	lda.l StreamCache_NormalLayout
	beq Core_StreamCache_IsReserved__no
	lda.l StreamCache_BG2Capacity
	beq Core_StreamCache_IsReserved__no
	rep #$30
.a16
.i16
	lda StreamCache_Candidate
	cmp #1023
	beq Core_StreamCache_IsReserved__yes ; BG2 transparent tile 255
	cmp #768
	bcc Core_StreamCache_IsReserved__no
	sec
	sbc #768
	sta StreamCache_OldTile
	sep #$20
.a8
	lda.l StreamCache_BG2Capacity
	rep #$30
.a16
.i16
	and #$00FF
	cmp StreamCache_OldTile
	bcc Core_StreamCache_IsReserved__no
	beq Core_StreamCache_IsReserved__no
Core_StreamCache_IsReserved__yes:
	rep #$30
.a16
.i16
	sec
	rtl
Core_StreamCache_IsReserved__no:
	rep #$30
.a16
.i16
	clc
	rtl

; The streamed tilemap encodes blank cells as cache slot 0. Power-on VRAM is
; not guaranteed to be zero, so establish the reserved blank before computing
; the first resident column. This wrapper preserves the existing initial-
; column call while keeping the 32-byte PPU clear out of the full bank-0
; runtime window.
.org $8080
Core_StreamCache_InitialColumnSetup:
	sep #$20
.a8
	lda #$80
	sta.l $002115             ; VMAIN: increment after the high-byte write
	rep #$31
.a16
.i16
	lda #BG1_TILES_VRAM_WORD
	sta.l $002116             ; VMADD = BG1 tile slot 0
	sep #$20
.a8
	lda #0
	ldx #16                   ; one 4bpp tile = 16 VRAM words = 32 bytes
Core_StreamCache_InitialColumnSetup__clear:
	sta.l $002118
	sta.l $002119
	dex
	bne Core_StreamCache_InitialColumnSetup__clear
	rep #$31
.a16
.i16
	jsl Stage_StreamInitialColumn
	rtl
.bank 0

; ----------------------------------------------------------------------
; Standalone smoke test (plan.md Phase 9 step 2): exercises AllocateSlot
; against a synthetic access pattern with NO MSU-1/VRAM involvement, per
; this project's established "exercise a new subsystem in isolation before
; wiring it into the real boot path" convention (core/oop.pasm's Phase 1/2
; precedent). Call Core_StreamCache_Test once after Core_StreamCache_Init;
; it allocates STREAM_CACHE_TEST_RESULTS_COUNT slots for distinct synthetic
; tile IDs and stores each result into StreamCache_Test_Results for
; external (Mesen2) inspection. Not called from the real boot path.
; ----------------------------------------------------------------------
Core_StreamCache_Test:
	php
	sei
	rep #$31
.a16
.i16
	; loop index kept in WRAM, not Y -- AllocateSlot clobbers Y internally
	; (its own scan counter), so Y can't survive the jsr below. `lda #0/
	; sta`, not `stz` -- see Core_StreamCache_Init's header note.
	lda #0
	sta StreamCache_Test_Index
Core_StreamCache_Test__loop:
	lda StreamCache_Test_Index
	tax                              ; tile_id = loop index (0..7)
	jsr Core_StreamCache_AllocateSlot
	sta StreamCache_Test_Slot

	lda StreamCache_Test_Index
	asl a
	tax
	lda StreamCache_Test_Slot
	sta.l StreamCache_Test_Results,x

	lda StreamCache_Test_Index      ; `inc a/sta`, not `inc Symbol` -- see
	inc a                            ; Core_StreamCache_Init's header note.
	sta StreamCache_Test_Index
	cmp #STREAM_CACHE_TEST_RESULTS_COUNT
	bcc Core_StreamCache_Test__loop

	plp
	rep #$31
.a16
.i16
	rts
