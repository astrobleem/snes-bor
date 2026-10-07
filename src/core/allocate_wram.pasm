; ============================================================================
; core/allocate_wram.pasm — dynamic WRAM block allocator
;
; Ported (redesigned) from SNES-SuperBossGaiden (src/core/allocate_wram.65816
; + allocate_wram.h), used with the original author's permission. Hands out
; fixed-size blocks from a reserved WRAM buffer — for persistent, non-moving
; scratch space to DMA from/to, the kind of thing you don't want silently
; sharing an address with something else.
;
; Deliberately simplified, not a byte-for-byte port:
;  - Upstream's seek/allocate routines are a fully `.rept`-unrolled 48-entry
;    jump table (one label + comparison per block, entered at a computed
;    offset so a scan only walks the *remaining* blocks) — fast, but a lot of
;    generated code, and it leans on `.rept` + a per-iteration unique-label
;    counter (`\@`) whose exact behavior in this Poppy build hasn't been
;    verified. This port uses a plain linear scan instead: same result,
;    much less code, and nothing here is on a timing budget that needs the
;    unrolled version's speed yet. If that changes, this is the place to
;    bring the unrolled version back.
;  - Allocation ids just count up forever (wrapping 1-255, skipping 0) rather
;    than upstream's "reclaim the id if you deallocate the topmost block"
;    logic — ids are opaque handles here, not a tracked high-water mark, so
;    there's nothing to reclaim.
;
; Uses global (not @-local) labels throughout — see core/random.pasm's header
; comment for why.
;
; Indexed WRAM access uses `.l`, never `.w` — see core/dma_channel.pasm's
; header note for why `.w` on an indexed bank-$7E symbol silently corrupts
; the instruction stream in this Poppy build. STZ has no long addressing
; mode at all, so its sites are rewritten as `lda #0` / `sta.l` instead of
; `stz.l` (which also doesn't error, just silently emits garbage).
;
; `@Core_Error_Trigger` is never invoked directly below, same reason as
; core/dma_channel.pasm: this Poppy build's forward address-estimation pass
; counts a macro invocation as 0 bytes, so a branch skipping over one gets
; a wrong offset. `pea`+`jsr Core_Error_Handler` inlined by hand instead.
; ============================================================================

WRAM_ALLOCATION_BLOCKS = 48
WRAM_ALLOCATION_BLOCKSIZE = $0100   ; 256 bytes/block

WramAlloc_CurrentId  = $7E04C0                         ; .db
WramAlloc_Blocks     = $7E04C1                         ; 48 bytes, $7E04C1-$7E04F0: 0=free, else owning id
WramAlloc_NeedBlocks = $7E04F1                         ; .db scratch: blocks needed for current request
WramAlloc_RunStart   = $7E04F2                          ; .db scratch: first block index of a candidate run
WramAlloc_RunLen     = $7E04F3                          ; .db scratch: consecutive free blocks found so far

; $7E2000, not $7E1000: banks $00-$3F mirror $0000-$1FFF onto $7E0000-$7E1FFF,
; and that's exactly the window the hardware stack lives in (scpu_boot sets
; S = $1FFF). WramBuffer at $7E1000 put this clear loop's write range
; ($7E1000-$7E3FFF) on top of the live stack; the loop would run to
; completion (it's X-driven, not stack-driven) but zero out its own return
; address on the way, so Core_Wram_Init's `rts` landed in garbage. Confirmed
; by manual trace: the loop's own breadcrumbs fired but the caller-side one
; never did. $7E2000 is the first byte outside the mirrored region.
WramBuffer           = $7E2000                          ; 48*256 = 12288 bytes, $7E2000-$7E4FFF
; Low 16 bits of WramBuffer, used below for 16-bit pointer arithmetic (X is
; only 16 bits; bank is always the fixed $7E). Kept as its own constant
; instead of `#WramBuffer` truncating in an `adc #<16-bit-immediate>` — this
; Poppy build doesn't error on a 24-bit symbol in a 16-bit immediate context,
; and while $7E2000's low word happens to equal this value anyway, relying on
; that truncation being well-defined is exactly the kind of thing that's
; bitten this project before (see header note on `.w` indexed access).
WramBuffer_Lo        = $2000

Core_Wram_Init:
	php
	sep #$20
.a8
	ldx #0
Core_Wram_Init__clear_blocks:
.a8
.i16
	; STZ has no long addressing mode on 65816; `.l` on it doesn't error, it
	; silently emits a malformed instruction (confirmed by isolated repro —
	; see core/dma_channel.pasm's header note). lda #0 / sta.l is correct.
	lda #0
	sta.l WramAlloc_Blocks,x
	inx
	cpx #WRAM_ALLOCATION_BLOCKS
	bcc Core_Wram_Init__clear_blocks
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
WramAlloc_CurrentId_Lo = $04C0
WramAlloc_NeedBlocks_Lo = $04F1
WramAlloc_RunLen_Lo = $04F3
WramAlloc_RunStart_Lo = $04F2

	stz.w WramAlloc_CurrentId_Lo

	rep #$31
.a16
	ldx #0
Core_Wram_Init__clear_buffer:
.a16
.i16
	lda #0
	sta.l WramBuffer,x
	inx
	inx
	cpx #WRAM_ALLOCATION_BLOCKS * WRAM_ALLOCATION_BLOCKSIZE
	bcc Core_Wram_Init__clear_buffer

	plp
	rts

; @param x<16-bit>  desired size in bytes (must be nonzero)
; @return carry<bool>  set on success
; @return a<8-bit>      allocation id (only meaningful on success)
; @return x<16-bit>     low 16 bits of the block's address (only meaningful on
;                        success); bank is always $7E — reach the block with
;                        long (`.l`) addressing or DB=$7E, not a bank-0 `,x`
Core_Wram_Allocate:
	php
	rep #$31
.a16
	cpx #0
	bne Core_Wram_Allocate__valid_length
	; Inlined instead of `@Core_Error_Trigger` — see header note.
	pea Error_VallocInvalidLength
	jsr Core_Error_Handler

Core_Wram_Allocate__valid_length:
.a16
.i16
	; blocksNeeded = (x >> 8) + (1 if low byte nonzero else 0)
	txa
	xba
	and #$00ff
	sta WramAlloc_NeedBlocks   ; high byte = whole blocks

	txa
	and #$00ff
	beq Core_Wram_Allocate__no_partial
	inc.w WramAlloc_NeedBlocks_Lo
Core_Wram_Allocate__no_partial:

	; Block indices/counts all fit in 8 bits (0-48) — go fully 8-bit for
	; index registers too, so every memory-sourced ldx/ldy below reads
	; exactly the 1 byte its source variable actually is. (An earlier draft
	; of this routine left the index width at 16-bit from the function's
	; entry `rep #$31` and used `ldx`/`ldy` straight from 1-byte scratch
	; vars — that silently pulls in the following byte as a garbage high
	; byte. Caught before it shipped; explicit `sep #$30` here is the fix.)
	sep #$30
.a8
.i8
	stz.w WramAlloc_RunStart_Lo
	stz.w WramAlloc_RunLen_Lo
	ldx #0

Core_Wram_Allocate__scan:
	lda.l WramAlloc_Blocks,x
	bne Core_Wram_Allocate__run_broken

	inc.w WramAlloc_RunLen_Lo
	lda WramAlloc_RunLen
	cmp WramAlloc_NeedBlocks
	bcs Core_Wram_Allocate__run_found
	bra Core_Wram_Allocate__scan_next

Core_Wram_Allocate__run_broken:
	stz.w WramAlloc_RunLen_Lo
	txa
	inc a
	sta WramAlloc_RunStart

Core_Wram_Allocate__scan_next:
.a8
.i8
	inx
	cpx #WRAM_ALLOCATION_BLOCKS
	bcc Core_Wram_Allocate__scan

	; ran off the end without finding enough consecutive free blocks
	plp
	clc
	rts

Core_Wram_Allocate__run_found:
	; new id: increment, skip 0 on wrap
	lda WramAlloc_CurrentId
	inc a
	bne Core_Wram_Allocate__id_ok
	inc a
Core_Wram_Allocate__id_ok:
	sta WramAlloc_CurrentId

	ldx.w WramAlloc_RunStart_Lo
	ldy.w WramAlloc_NeedBlocks_Lo
Core_Wram_Allocate__fill:
	sta.l WramAlloc_Blocks,x
	inx
	dey
	bne Core_Wram_Allocate__fill

	; address = WramBuffer + runStart * 256: high byte of the 16-bit offset
	; is exactly runStart, so this is a byte-swap, not a multiply. Zero A
	; in 16-bit mode first, then an 8-bit load of runStart into A's low
	; byte, so the xba below produces a clean zero-extended result instead
	; of picking up whatever garbage was in A's hidden high byte.
	rep #$31
.a16
	lda #0
	sep #$20
.a8
	lda WramAlloc_RunStart
	rep #$31
.a16
	xba
	clc
	adc #WramBuffer_Lo
	tax
	lda WramAlloc_CurrentId
	and #$00ff

	plp
	sec
	rts

; @param a<8-bit>  allocation id to release
Core_Wram_Deallocate:
	php
	sep #$20
.a8
	ldx #0
Core_Wram_Deallocate__scan:
.a8
.i16
	cmp.l WramAlloc_Blocks,x
	bne Core_Wram_Deallocate__next
	; STZ has no long addressing mode on 65816 (see core/dma_channel.pasm's
	; header note); lda #0 / sta.l is correct, but that clobbers A, which
	; this loop's `cmp` above depends on holding the caller's id every
	; iteration — stash/restore it around the zero-write.
	pha
	lda #0
	sta.l WramAlloc_Blocks,x
	pla
Core_Wram_Deallocate__next:
.a8
.i16
	inx
	cpx #WRAM_ALLOCATION_BLOCKS
	bcc Core_Wram_Deallocate__scan

	plp
	rts
