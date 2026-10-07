; ============================================================================
; core/allocate_vram.pasm — dynamic VRAM block allocator
;
; Ported (redesigned) from SNES-SuperBossGaiden (src/core/allocate_vram.65816
; + allocate_vram.h), used with the original author's permission. Hands out
; stepsize-aligned regions of the 64KB VRAM address space by allocation id,
; the same free-list-by-fixed-block idea as core/allocate_wram.pasm but
; sized for VRAM (512 blocks of 128 bytes instead of 48 blocks of 256) and
; with a caller-supplied search start + alignment stepsize, since tile data
; and tilemaps generally need to land on specific boundaries, not just
; anywhere free.
;
; Deliberately simplified, not a byte-for-byte port:
;  - Upstream's seek/mark routines are a fully `.rept`-unrolled 512-entry
;    table for allocation-id uniqueness checking — see core/allocate_wram.pasm's
;    header note for why that pattern (and its `\@` per-iteration unique-label
;    counter) isn't used here. This port uses a plain linear scan and a
;    simple wrapping id counter instead, same as allocate_wram.pasm.
;  - Allocation ids just count up forever (wrapping 1-255, skipping 0) rather
;    than upstream's "reclaim the id if you deallocate the topmost block"
;    logic, same reasoning as allocate_wram.pasm: ids are opaque handles
;    here, nothing to reclaim.
;  - `core.vram.allocate.tile.sprite` (upstream's dual 8x8/32x32-interlaced
;    allocator that seeks from both ends of VRAM at once, for their specific
;    OAM tile pool layout) is not ported. It depends on
;    `SPRITE.TILE.INTERLACE.LENGTH`/`GLOBAL.oam.vram.start` and a nametable-
;    boundary check that only make sense alongside the OAM tile pool system
;    that consumes them — neither exists in this project yet (see
;    `core/oop.pasm`/`core/screen.pasm` in the upstream repo, still unported).
;    `Core_Vram_Allocate` below (the general single-region allocator) is the
;    part of upstream that stands on its own; bring the sprite-tile variant
;    back if/when the OAM pool it's designed for gets ported too.
;  - Zero-length requests trigger the crash handler (`Error_VallocInvalidLength`)
;    rather than upstream's silent "id 0, carry set" no-op return — matches
;    allocate_wram.pasm's convention instead, so a caller bug here fails loud.
;
; Index registers stay 16-bit throughout (unlike allocate_wram.pasm's 8-bit
; optimization) because VRAM_ALLOCATION_BLOCKS (512) doesn't fit in a byte.
;
; Uses global (not @-local) labels throughout — see core/random.pasm's header
; comment for why.
;
; Indexed WRAM access (the VramAlloc_Blocks tracking table) uses `.l`, never
; `.w` — see core/dma_channel.pasm's header note for why `.w` on an indexed
; bank-$7E symbol silently corrupts the instruction stream in this Poppy
; build. STZ has no long addressing mode at all, so its one site below is
; `lda #0` / `sta.l` instead of `stz.l` (which also doesn't error, just
; silently emits garbage).
;
; `@Core_Error_Trigger` is never invoked directly below, same reason as
; core/dma_channel.pasm: this Poppy build's forward address-estimation pass
; counts a macro invocation as 0 bytes, so a branch skipping over one gets
; a wrong offset. `pea`+`jsr Core_Error_Handler` inlined by hand instead.
; ============================================================================

VRAM_ALLOCATION_BLOCKS    = $200   ; 512 blocks * 128 bytes = 64KB = full VRAM
VRAM_ALLOCATION_BLOCKSIZE = $80    ; 128 bytes/block

VRAM_ALLOCATION_STEP_MIN = VRAM_ALLOCATION_BLOCKSIZE
VRAM_ALLOCATION_STEP_MAX = $4000

VramAlloc_CurrentId = $7E04F4   ; .db
VramAlloc_Stepsize  = $7E04F5   ; .dw scratch: input alignment stepsize
VramAlloc_Length    = $7E04F7   ; .dw scratch: requested length (bytes); also the reset value for VramAlloc_NeedBytes
VramAlloc_NeedBytes = $7E04F9   ; .dw scratch: bytes still needed to satisfy the current candidate run
VramAlloc_Start     = $7E04FB   ; .dw scratch: current candidate run's start address; holds the result on success
VramAlloc_Blocks    = $7E04FD   ; 512 bytes, $7E04FD-$7E06FC: 0=free, else owning id

Core_Vram_Init:
	php
	sep #$20
.a8
	rep #$10
.i16
	ldx #0
Core_Vram_Init__clear_blocks:
.a8
.i16
	; STZ has no long addressing mode on 65816 — `.l` on it doesn't error
	; here, it silently emits a malformed encoding (confirmed by isolated
	; repro — see core/dma_channel.pasm's header note). lda #0 / sta.l is
	; the correct equivalent.
	lda #0
	sta.l VramAlloc_Blocks,x
	inx
	cpx #VRAM_ALLOCATION_BLOCKS
	bcc Core_Vram_Init__clear_blocks
; --- Poppy-fork migration: low16 aliases for STZ/INC/DEC/STX/STY/LDX/LDY/BIT/
; TSB/TRB/CPX/CPY/ASL/LSR/ROL/ROR/indirect-indexed JSR(,x)/JMP(,x) sites below.
; Real 65816 has no absolute-long encoding for these mnemonics. Old Poppy
; silently truncated a $7Exxxx operand to its low 16 bits (2-byte absolute,
; DBR-relative); new Poppy correctly refuses to do this truncation implicitly.
; This project confines all code+data to ROM bank 0 (see CLAUDE.md), and DBR
; is never set outside {$00-$3F,$7E,$7F} at runtime, so for any symbol whose
; offset is <$2000 the WRAM mirror at $0000-$1FFF (present in every bank
; $00-$3F/$80-$BF) makes the plain 2-byte absolute form land on the exact
; same physical byte as the canonical $7Exxxx symbol, regardless of DBR's
; exact value. These _Lo aliases reproduce that byte-identical encoding
; explicitly. Use ONLY at a site with no long-addressing alternative --
; never as a general substitute for the canonical long-addressed symbol.
VramAlloc_CurrentId_Lo = $04F4
VramAlloc_Length_Lo = $04F7
VramAlloc_NeedBytes_Lo = $04F9
VramAlloc_Start_Lo = $04FB

	stz.w VramAlloc_CurrentId_Lo

	plp
	rts

; @param a<16-bit>  alignment stepsize (VRAM_ALLOCATION_STEP_MIN..VRAM_ALLOCATION_STEP_MAX)
; @param x<16-bit>  desired size in bytes (must be nonzero)
; @param y<16-bit>  search start address in bytes
; @return carry<bool>  set on success
; @return a<8-bit>      allocation id (only meaningful on success)
; @return x<16-bit>     start address of the allocated block (only meaningful
;                        on success)
Core_Vram_Allocate:
	php
	rep #$31
.a16
.i16
	cmp #VRAM_ALLOCATION_STEP_MIN
	bcs Core_Vram_Allocate__step_min_ok
	; Inlined instead of `@Core_Error_Trigger` — see header note.
	pea Error_VallocBadStepsize
	jsr Core_Error_Handler

Core_Vram_Allocate__step_min_ok:
.a16
.i16
	cmp #VRAM_ALLOCATION_STEP_MAX + 1
	bcc Core_Vram_Allocate__step_ok
	pea Error_VallocBadStepsize
	jsr Core_Error_Handler

Core_Vram_Allocate__step_ok:
.a16
.i16
	sta VramAlloc_Stepsize

	cpx #0
	bne Core_Vram_Allocate__valid_length
	pea Error_VallocInvalidLength
	jsr Core_Error_Handler

Core_Vram_Allocate__valid_length:
	stx.w VramAlloc_Length_Lo
	stx.w VramAlloc_NeedBytes_Lo

	tya
	sta VramAlloc_Start

	; block index = start / VRAM_ALLOCATION_BLOCKSIZE ($80 -> seven >>1's)
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	tax

Core_Vram_Allocate__seek:
	sep #$20
.a8
	lda.l VramAlloc_Blocks,x
	beq Core_Vram_Allocate__block_free

	; occupied: reset the run's need, advance the candidate start by stepsize
	rep #$31
.a16
	lda VramAlloc_Length
	sta VramAlloc_NeedBytes

	lda VramAlloc_Start
	clc
	adc VramAlloc_Stepsize
	bcc Core_Vram_Allocate__advance_inrange
	; wrapped past $ffff: out of vram
	plp
	clc
	rts

Core_Vram_Allocate__advance_inrange:
.a16
.i16
	sta VramAlloc_Start
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	cmp #VRAM_ALLOCATION_BLOCKS
	bcc Core_Vram_Allocate__advance_ok
	; ran off the end of vram without finding enough space
	plp
	clc
	rts

Core_Vram_Allocate__advance_ok:
	tax
	bra Core_Vram_Allocate__seek

Core_Vram_Allocate__block_free:
	rep #$31
.a16
	inx
	cpx #VRAM_ALLOCATION_BLOCKS + 1
	bne Core_Vram_Allocate__block_inrange
	plp
	clc
	rts

Core_Vram_Allocate__block_inrange:
.a16
.i16
	lda VramAlloc_NeedBytes
	sec
	sbc #VRAM_ALLOCATION_BLOCKSIZE
	sta VramAlloc_NeedBytes
	beq Core_Vram_Allocate__found
	bcs Core_Vram_Allocate__seek
	; fallthrough: needed fewer bytes than a full block — already satisfied

Core_Vram_Allocate__found:
.a16
.i16
	; blocksToMark = ceil(Length / VRAM_ALLOCATION_BLOCKSIZE)
	lda VramAlloc_Length
	clc
	adc #VRAM_ALLOCATION_BLOCKSIZE - 1
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	tay

	lda VramAlloc_Start
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	lsr a
	tax

	sep #$20
.a8
	; new id: increment, skip 0 on wrap
	lda VramAlloc_CurrentId
	inc a
	bne Core_Vram_Allocate__id_ok
	inc a
Core_Vram_Allocate__id_ok:
	sta VramAlloc_CurrentId

Core_Vram_Allocate__mark:
	sta.l VramAlloc_Blocks,x
	inx
	dey
	bne Core_Vram_Allocate__mark

	rep #$31
.a16
	ldx.w VramAlloc_Start_Lo
	sep #$20
.a8
	lda VramAlloc_CurrentId

	plp
	sec
	rts

; @param a<8-bit>  allocation id to release
Core_Vram_Deallocate:
	php
	sep #$20
.a8
	rep #$10
.i16
	ldx #0
Core_Vram_Deallocate__scan:
.a8
.i16
	cmp.l VramAlloc_Blocks,x
	bne Core_Vram_Deallocate__next
	; STZ has no long addressing mode on 65816 (see core/dma_channel.pasm's
	; header note); lda #0 / sta.l is correct, but that clobbers A, which
	; this loop's `cmp` above depends on holding the caller's id every
	; iteration — stash/restore it around the zero-write.
	pha
	lda #0
	sta.l VramAlloc_Blocks,x
	pla
Core_Vram_Deallocate__next:
.a8
.i16
	inx
	cpx #VRAM_ALLOCATION_BLOCKS
	bcc Core_Vram_Deallocate__scan

	plp
	rts
