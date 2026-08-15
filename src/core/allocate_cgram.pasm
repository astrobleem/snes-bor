; ============================================================================
; core/allocate_cgram.pasm — dynamic CGRAM (palette) block allocator
;
; Ported (redesigned) from SNES-SuperBossGaiden (src/core/allocate_cgram.65816
; + allocate_cgram.h), used with the original author's permission. Hands out
; stepsize-aligned regions of the 512-byte CGRAM (256 colors x 2 bytes) by
; allocation id — the same free-list-by-fixed-block idea as
; core/allocate_vram.pasm, rescaled: 64 blocks of 8 bytes (4 colors) instead
; of 512 blocks of 128.
;
; Deliberately simplified, not a byte-for-byte port — see core/allocate_wram.pasm
; and core/allocate_vram.pasm's header notes for the two simplifications this
; shares with them:
;  - Plain linear scan + a simple wrapping id counter, not upstream's
;    `.rept`-unrolled uniqueness-check table.
;  - Ids just count up forever (wrapping 1-255, skipping 0); no "reclaim the
;    id if you deallocate the topmost block" logic.
;  - Zero-length requests trigger the crash handler (`Error_CGallocInvalidLength`)
;    rather than upstream's silent no-op return, same as allocate_vram.pasm.
;
; What IS carried over from upstream (unlike allocate_vram.pasm's general
; allocator, which doesn't need either of these): an explicit range check on
; the caller-supplied start address (`Error_CGallocInvalidStart`), and a
; bound check after a candidate run is found that the allocated region can't
; extend past 8 stepsize-widths from the requested start
; (`stepsize * 8`, precomputed as `CgramAlloc_MaxLength`) — palette ids on
; real hardware only go 0-7, so a run that drifted further than that while
; searching for free space isn't a usable palette no matter how free it is.
;
; Index registers stay 16-bit throughout, like allocate_vram.pasm, even
; though CGRAM_ALLOCATION_BLOCKS (64) would fit an 8-bit index the way
; allocate_wram.pasm's 48 blocks do — kept consistent with allocate_vram.pasm
; instead of re-deriving the 8-bit-index optimization for a table this small;
; neither allocator is on a timing budget that needs it yet.
;
; Uses global (not @-local) labels throughout — see core/random.pasm's header
; comment for why.
;
; Indexed WRAM access (the CgramAlloc_Blocks tracking table) uses `.l`, never
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

CGRAM_ALLOCATION_BLOCKS    = 64   ; 64 blocks * 8 bytes = 512 bytes = full CGRAM (256 colors * 2 bytes)
CGRAM_ALLOCATION_BLOCKSIZE = $8   ; 8 bytes/block = 4 colors

CGRAM_ALLOCATION_STEP_MIN = CGRAM_ALLOCATION_BLOCKSIZE
CGRAM_ALLOCATION_STEP_MAX = $200

CgramAlloc_CurrentId  = $7E06FD   ; .db
CgramAlloc_Stepsize   = $7E06FE   ; .dw scratch: input alignment stepsize
CgramAlloc_Length     = $7E0700   ; .dw scratch: requested length (bytes); also the reset value for CgramAlloc_NeedBytes
CgramAlloc_InputStart = $7E0702   ; .dw scratch: original requested start address (bytes) — fixed, unlike CgramAlloc_Start
CgramAlloc_Start      = $7E0704   ; .dw scratch: current candidate run's start address; holds the result on success
CgramAlloc_NeedBytes  = $7E0706   ; .dw scratch: bytes still needed to satisfy the current candidate run
CgramAlloc_MaxLength  = $7E0708   ; .dw scratch: stepsize * 8 (max palette id is 8), precomputed at entry
CgramAlloc_Blocks     = $7E070A   ; 64 bytes, $7E070A-$7E0749: 0=free, else owning id

Core_Cgram_Init:
	php
	sep #$20
.a8
	rep #$10
.i16
	ldx #0
Core_Cgram_Init__clear_blocks:
	; STZ has no long addressing mode on 65816 — `.l` on it doesn't error
	; here, it silently emits a malformed encoding (confirmed by isolated
	; repro — see core/dma_channel.pasm's header note). lda #0 / sta.l is
	; the correct equivalent.
	lda #0
	sta.l CgramAlloc_Blocks,x
	inx
	cpx #CGRAM_ALLOCATION_BLOCKS
	bcc Core_Cgram_Init__clear_blocks
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
CgramAlloc_CurrentId_Lo = $06FD
CgramAlloc_Length_Lo = $0700
CgramAlloc_NeedBytes_Lo = $0706
CgramAlloc_Start_Lo = $0704

	stz.w CgramAlloc_CurrentId_Lo

	plp
	rts

; @param a<16-bit>  alignment stepsize (CGRAM_ALLOCATION_STEP_MIN..CGRAM_ALLOCATION_STEP_MAX)
; @param x<16-bit>  desired size in bytes (must be nonzero)
; @param y<16-bit>  desired start address in bytes (must be within CGRAM)
; @return carry<bool>  set on success
; @return a<8-bit>      allocation id (only meaningful on success)
; @return x<16-bit>     start address of the allocated block (only meaningful
;                        on success)
Core_Cgram_Allocate:
	php
	rep #$31
.a16
.i16
	cmp #CGRAM_ALLOCATION_STEP_MIN
	bcs Core_Cgram_Allocate__step_min_ok
	; Inlined instead of `@Core_Error_Trigger` — see header note.
	pea Error_CGallocBadStepsize
	jsr Core_Error_Handler

Core_Cgram_Allocate__step_min_ok:
	cmp #CGRAM_ALLOCATION_STEP_MAX + 1
	bcc Core_Cgram_Allocate__step_ok
	pea Error_CGallocBadStepsize
	jsr Core_Error_Handler

Core_Cgram_Allocate__step_ok:
	sta CgramAlloc_Stepsize
	; max.length = stepsize * 8 (three left shifts)
	asl a
	asl a
	asl a
	sta CgramAlloc_MaxLength

	cpx #0
	bne Core_Cgram_Allocate__valid_length
	pea Error_CGallocInvalidLength
	jsr Core_Error_Handler

Core_Cgram_Allocate__valid_length:
	stx.w CgramAlloc_Length_Lo
	stx.w CgramAlloc_NeedBytes_Lo

	tya
	sta CgramAlloc_InputStart
	sta CgramAlloc_Start

	; block index = start / CGRAM_ALLOCATION_BLOCKSIZE ($8 -> three >>1's)
	lsr a
	lsr a
	lsr a
	cmp #CGRAM_ALLOCATION_BLOCKS
	bcc Core_Cgram_Allocate__start_ok
	pea Error_CGallocInvalidStart
	jsr Core_Error_Handler

Core_Cgram_Allocate__start_ok:
	tax

Core_Cgram_Allocate__seek:
	sep #$20
.a8
	lda.l CgramAlloc_Blocks,x
	beq Core_Cgram_Allocate__block_free

	; occupied: reset the run's need, advance the candidate start by stepsize
	rep #$31
.a16
	lda CgramAlloc_Length
	sta CgramAlloc_NeedBytes

	lda CgramAlloc_Start
	clc
	adc CgramAlloc_Stepsize
	sta CgramAlloc_Start
	lsr a
	lsr a
	lsr a
	cmp #CGRAM_ALLOCATION_BLOCKS
	bcc Core_Cgram_Allocate__advance_ok
	; ran off the end of cgram without finding enough space
	plp
	clc
	rts

Core_Cgram_Allocate__advance_ok:
	tax
	bra Core_Cgram_Allocate__seek

Core_Cgram_Allocate__block_free:
	rep #$31
.a16
	inx
	cpx #CGRAM_ALLOCATION_BLOCKS + 1
	bne Core_Cgram_Allocate__block_inrange
	plp
	clc
	rts

Core_Cgram_Allocate__block_inrange:
	lda CgramAlloc_NeedBytes
	sec
	sbc #CGRAM_ALLOCATION_BLOCKSIZE
	sta CgramAlloc_NeedBytes
	beq Core_Cgram_Allocate__found
	bcs Core_Cgram_Allocate__seek
	; fallthrough: needed fewer bytes than a full block — already satisfied

Core_Cgram_Allocate__found:
	; bound check: (Start + Length - InputStart) must not exceed MaxLength —
	; a run that drifted further than 8 stepsize-widths from the requested
	; start isn't a usable palette id, even though the space itself is free.
	lda CgramAlloc_Start
	clc
	adc CgramAlloc_Length
	sec
	sbc CgramAlloc_InputStart
	cmp CgramAlloc_MaxLength
	beq Core_Cgram_Allocate__bound_ok
	bcc Core_Cgram_Allocate__bound_ok
	plp
	clc
	rts

Core_Cgram_Allocate__bound_ok:
	; blocksToMark = ceil(Length / CGRAM_ALLOCATION_BLOCKSIZE)
	lda CgramAlloc_Length
	clc
	adc #CGRAM_ALLOCATION_BLOCKSIZE - 1
	lsr a
	lsr a
	lsr a
	tay

	lda CgramAlloc_Start
	lsr a
	lsr a
	lsr a
	tax

	sep #$20
.a8
	; new id: increment, skip 0 on wrap
	lda CgramAlloc_CurrentId
	inc a
	bne Core_Cgram_Allocate__id_ok
	inc a
Core_Cgram_Allocate__id_ok:
	sta CgramAlloc_CurrentId

Core_Cgram_Allocate__mark:
	sta.l CgramAlloc_Blocks,x
	inx
	dey
	bne Core_Cgram_Allocate__mark

	rep #$31
.a16
	ldx.w CgramAlloc_Start_Lo
	sep #$20
.a8
	lda CgramAlloc_CurrentId

	plp
	sec
	rts

; @param a<8-bit>  allocation id to release
Core_Cgram_Deallocate:
	php
	sep #$20
.a8
	rep #$10
.i16
	ldx #0
Core_Cgram_Deallocate__scan:
	cmp.l CgramAlloc_Blocks,x
	bne Core_Cgram_Deallocate__next
	; STZ has no long addressing mode on 65816 (see core/dma_channel.pasm's
	; header note); lda #0 / sta.l is correct, but that clobbers A, which
	; this loop's `cmp` above depends on holding the caller's id every
	; iteration — stash/restore it around the zero-write.
	pha
	lda #0
	sta.l CgramAlloc_Blocks,x
	pla
Core_Cgram_Deallocate__next:
	inx
	cpx #CGRAM_ALLOCATION_BLOCKS
	bcc Core_Cgram_Deallocate__scan

	plp
	rts
