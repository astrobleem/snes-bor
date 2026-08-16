; ============================================================================
; core/stream_cache_fp.pasm — Phase 10 (plan.md 2.10) streaming BG3
; frontpanel tile cache
;
; A second, independent instance of core/stream_cache.pasm's ring-buffer
; allocator, sized for the frontpanel layer instead of BG1's backdrop.
; Deliberately a NEAR-DUPLICATE, not a parameterized/shared version of that
; file: this project's assembler (Poppy) has no clean way to pass a "which
; layer" parameter through to indexed banked-symbol access without either
; self-modifying code or a runtime-computed base address added to every
; single access (itself a known Poppy hazard -- see CLAUDE.md's indexed-
; banked-access warnings), and this project has an established precedent
; for preferring plain duplication over that kind of cleverness when
; correctness risk is at stake (see Character_HitApply_VsEntity1/2/3,
; main.pasm -- "kept separate rather than inlined or parameterized-by-
; register"). Read stream_cache.pasm's own header first; this file only
; documents what's DIFFERENT.
;
; Sizing (measured via tools/bg_converter/convert_frontpanel.py against
; stage 1A, plan.md 2.10 Step 1 -- see out/fp_stage1a/manifest.json):
;   - 535 unique tiles total, 143 worst-case in any 40-column camera
;     window. Budgeted well above both, not tight against either, matching
;     STREAM_CACHE_USABLE's own "measured worst case, not the theoretical
;     ceiling" precedent.
;   - VRAM: BG3 tiles are 2bpp (8 words/tile, not BG1's 16), based at
;     BG3_TILES_VRAM_WORD ($5000, main.pasm). STREAM_FP_CACHE_USABLE (256)
;     slots x 8 words = 2048 words -- comfortably inside the free
;     $5000-$5FFF gap (4096 words minus the HUD's own ~12 tiles) without
;     needing the BG1 or BG3 tilemap to move. Re-verify this arithmetic
;     against the actual build before relying on it if either budget
;     shifts.
;
; WRAM (bank $7F): grep-confirmed unused as of Phase 10 (nothing in
; src/main.pasm or src/core/*.pasm references $7FA000+ before this file).
; Placed well clear of stream_cache.pasm's own tables ($7F0000-$7F90BF)
; with generous spacing, not packed tight against them, so either file's
; tables can grow without touching this one.
; ============================================================================

STREAM_FP_CACHE_SLOTS   = 257     ; slot 0 reserved blank + 256 usable
STREAM_FP_CACHE_USABLE  = 256     ; slots 1..256
STREAM_FP_CACHE_STRIDE  = 97      ; prime, coprime with 256 -- see
                                    ; stream_cache.pasm's identical rationale
                                    ; for why this must not share a factor
                                    ; with CACHE_USABLE
STREAM_FP_CACHE_SCAN_LIMIT = STREAM_FP_CACHE_USABLE  ; full-ring scan --
                                    ; see stream_cache.pasm's header for why
                                    ; a smaller limit force-evicts slots
                                    ; that don't need it
STREAM_FP_CACHE_PROTECT_WINDOW = 16 ; same viewport+prefetch window as BG1
                                    ; (STREAM_STAGE_VIEWPORT_COLS+2*
                                    ; STREAM_SCROLL_PREFETCH) -- both layers
                                    ; share the same camera, so the same
                                    ; protection width applies

; Headroom above the measured 535, not sized exactly to it (a future level
; could measure higher -- see plan.md 2.10's stop conditions).
STREAM_FP_MAX_TILE_IDS = 768

StreamCacheFp_Tile2Slot = $7FA000  ; STREAM_FP_MAX_TILE_IDS words (1536
                                     ; bytes, $7FA000-$7FA5FF)
StreamCacheFp_Slot2Tile = $7FB000  ; STREAM_FP_CACHE_SLOTS words (514
                                     ; bytes, $7FB000-$7FB201)
StreamCacheFp_SlotStamp = $7FB800  ; STREAM_FP_CACHE_SLOTS bytes
                                     ; ($7FB800-$7FB900)

; Small $7E scratch. Placed in the gap after StreamScroll_FetchBufSel
; ($7E2599, 1 byte) -- grep-confirmed unused up to $7E4FFF as of Phase 10
; (that whole span is core/allocate_wram.pasm's nominal 12KB WramBuffer
; pool, $7E2000-$7E4FFF, but Core_Wram_Allocate/Deallocate are not called
; by anything -- every existing Stream* structure already lives at a fixed
; address inside this same nominal pool by the same established
; convention, not through the dynamic allocator).
StreamCacheFp_CurrentStamp = $7E25A0  ; .db
StreamCacheFp_ScanCursor   = $7E25A1  ; .dw
StreamCacheFp_NewTileId    = $7E25A3  ; .dw
StreamCacheFp_Candidate    = $7E25A5  ; .dw
StreamCacheFp_Chosen       = $7E25A7  ; .dw
StreamCacheFp_OldTile      = $7E25A9  ; .dw

	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_Init:
	php
	sei
	rep #$31
.a16
.i16
	lda #1
	sta StreamCacheFp_ScanCursor    ; cursor starts at slot 1 (0 reserved)

	lda #$FFFF
	ldx #0
	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_Init__tile2slot:
	sta.l StreamCacheFp_Tile2Slot,x
	inx
	inx
	cpx #STREAM_FP_MAX_TILE_IDS*2
	bcc Core_StreamCacheFp_Init__tile2slot

	lda #$FFFF
	ldx #0
	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_Init__slot2tile:
	sta.l StreamCacheFp_Slot2Tile,x
	inx
	inx
	cpx #STREAM_FP_CACHE_SLOTS*2
	bcc Core_StreamCacheFp_Init__slot2tile

	sep #$20
.a8
	lda #0
	sta StreamCacheFp_CurrentStamp
	rep #$31
.a16
.i16
	lda #0
	ldx #0
	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_Init__slotstamp:
	sep #$20
.a8
	sta.l StreamCacheFp_SlotStamp,x
	rep #$31
.a16
.i16
	inx
	cpx #STREAM_FP_CACHE_SLOTS
	bcc Core_StreamCacheFp_Init__slotstamp

	plp
	rep #$31
.a16
.i16
	rts

; Identical contract to Core_StreamCache_AllocateSlot (stream_cache.pasm) --
; see that routine's header. Same algorithm, this instance's own tables.
; @param X<16-bit>  tile_id to allocate a slot for (0..STREAM_FP_MAX_TILE_IDS-1)
; @return A<16-bit>  the allocated slot number (1..STREAM_FP_CACHE_USABLE)
; Clobbers X, Y.
	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_AllocateSlot:
	php
	sei
	rep #$31
.a16
.i16
	txa
	sta StreamCacheFp_NewTileId

	lda StreamCacheFp_ScanCursor
	sta StreamCacheFp_Candidate
	clc
	adc #STREAM_FP_CACHE_STRIDE
	cmp #STREAM_FP_CACHE_USABLE+1
	bcc Core_StreamCacheFp_AllocateSlot__cursor_ok
	sec
	sbc #STREAM_FP_CACHE_USABLE
	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_AllocateSlot__cursor_ok:
	sta StreamCacheFp_ScanCursor

	ldy #0
	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_AllocateSlot__scan:
	rep #$31
.a16
.i16
	lda StreamCacheFp_Candidate
	asl a
	tax
	lda.l StreamCacheFp_Slot2Tile,x
	cmp #$FFFF
	beq Core_StreamCacheFp_AllocateSlot__found

	lda StreamCacheFp_Candidate
	tax
	sep #$20
.a8
	lda StreamCacheFp_CurrentStamp
	sec
	sbc.l StreamCacheFp_SlotStamp,x
	cmp #STREAM_FP_CACHE_PROTECT_WINDOW
	bcc Core_StreamCacheFp_AllocateSlot__protected

	rep #$31
.a16
.i16
	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_AllocateSlot__evictable:
	lda StreamCacheFp_Candidate
	sta StreamCacheFp_Chosen
	bra Core_StreamCacheFp_AllocateSlot__allocate

	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_AllocateSlot__protected:
	rep #$31
.a16
.i16
	bra Core_StreamCacheFp_AllocateSlot__advance

	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_AllocateSlot__found:
	rep #$31
.a16
.i16
	lda StreamCacheFp_Candidate
	sta StreamCacheFp_Chosen
	bra Core_StreamCacheFp_AllocateSlot__allocate

	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_AllocateSlot__advance:
	rep #$31
.a16
.i16
	lda StreamCacheFp_Candidate
	inc a
	cmp #STREAM_FP_CACHE_USABLE+1
	bcc Core_StreamCacheFp_AllocateSlot__advance_ok
	lda #1
	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_AllocateSlot__advance_ok:
	sta StreamCacheFp_Candidate

	iny
	cpy #STREAM_FP_CACHE_SCAN_LIMIT
	bcc Core_StreamCacheFp_AllocateSlot__scan

	lda StreamCacheFp_Candidate
	sta StreamCacheFp_Chosen

	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_AllocateSlot__allocate:
	rep #$31
.a16
.i16
	lda StreamCacheFp_Chosen
	asl a
	tax
	lda.l StreamCacheFp_Slot2Tile,x
	cmp #$FFFF
	beq Core_StreamCacheFp_AllocateSlot__no_evict
	sta StreamCacheFp_OldTile
	lda StreamCacheFp_OldTile
	asl a
	tax
	lda #$FFFF
	sta.l StreamCacheFp_Tile2Slot,x

	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_AllocateSlot__no_evict:
	lda StreamCacheFp_Chosen
	asl a
	tax
	lda StreamCacheFp_NewTileId
	sta.l StreamCacheFp_Slot2Tile,x

	lda StreamCacheFp_Chosen
	tax
	sep #$20
.a8
	lda StreamCacheFp_CurrentStamp
	sta.l StreamCacheFp_SlotStamp,x
	rep #$31
.a16
.i16

	lda StreamCacheFp_NewTileId
	asl a
	tax
	lda StreamCacheFp_Chosen
	sta.l StreamCacheFp_Tile2Slot,x

	lda StreamCacheFp_Chosen

	plp
	rep #$31
.a16
.i16
	rts

; ----------------------------------------------------------------------
; Standalone smoke test, same convention as stream_cache.pasm's
; Core_StreamCache_Test -- do NOT call this from the real boot path. That
; file's own header explains why: a boot-time smoke test allocating slots
; for synthetic tile IDs 0-7 against the SAME Tile2Slot table real content
; uses silently poisons the cache for any real tile ID in that range,
; caught only by phase9_stagecolumn_spotcheck.py after the fact. Call
; Core_StreamCacheFp_Init then this once, manually, via a temporary call
; site for ad hoc Mesen2 verification, and remove that call site before
; committing.
; ----------------------------------------------------------------------
StreamCacheFp_Test_Results = $7E25AB  ; .dw x 8
STREAM_FP_CACHE_TEST_RESULTS_COUNT = 8
StreamCacheFp_Test_Index = $7E25BB    ; .dw
StreamCacheFp_Test_Slot  = $7E25BD    ; .dw

	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_Test:
	php
	sei
	rep #$31
.a16
.i16
	lda #0
	sta StreamCacheFp_Test_Index
	nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamCacheFp_Test__loop:
	lda StreamCacheFp_Test_Index
	tax
	jsr Core_StreamCacheFp_AllocateSlot
	sta StreamCacheFp_Test_Slot

	lda StreamCacheFp_Test_Index
	asl a
	tax
	lda StreamCacheFp_Test_Slot
	sta.l StreamCacheFp_Test_Results,x

	lda StreamCacheFp_Test_Index
	inc a
	sta StreamCacheFp_Test_Index
	cmp #STREAM_FP_CACHE_TEST_RESULTS_COUNT
	bcc Core_StreamCacheFp_Test__loop

	plp
	rep #$31
.a16
.i16
	rts
