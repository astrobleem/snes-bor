; ============================================================================
; core/math.pasm — integer math primitives
;
; Ported to Poppy syntax from SNES-SuperBossGaiden (src/core/math.65816),
; used with the original author's permission. Only the LUT-free routines
; are ported here — sin/cos/atan2/direction2angle in the original depend on
; binary lookup tables (data/math/*.lut) that aren't part of this project;
; porting those needs either the original data files or freshly generated
; tables, left for later. core.math.mod was also left out: its "(x + x*y/100)"
; comment doesn't match standard modulo semantics and its actual use in the
; original wasn't clear enough to port with confidence.
;
; Uses global (not @-local) labels throughout — see core/random.pasm's header
; comment for why: @-local labels mis-resolve once reached via .include in
; this Poppy build, confirmed by isolated repro.
;
; `lda.l`/`adc.l`/`sta.l` on the `+1`-offset operands in Core_Math_Mul below
; are load-bearing, not stylistic. Bare `Symbol+1` (no explicit `.l`/.w`)
; on a bank-$7E symbol, feeding an instruction that has a long-addressing
; form, gets mis-sized by 1 byte during this Poppy build's forward
; address-estimation pass relative to what it actually emits — confirmed by
; isolated repro. Every subsequent label in the file inherits the shortfall
; (this cost core/error.pasm's Core_Error_Handler 3 stale bytes before this
; fix). Plain-symbol (no `+N`) or explicit `.l`/`.w` sizing both avoid it;
; `.l` was chosen here to keep the operand's own long-bank intent explicit.
; ============================================================================

.enum $7E0420
	Math_Mul_Multiplier    .dw
	Math_Mul_Multiplicand  .dw
	Math_Mul_ProductLo     .dw
	Math_Mul_ProductHi     .dw
	Math_Div_Quotient      .dw
.ende

; 8bit * 8bit -> unsigned 16bit, via the hardware multiplier ($4202-$4216).
; @param a<8-bit>   multiplicand a
; @param x<8-bit>   multiplicand b
; @return a<16-bit> result
Core_Math_Mul8:
	sep #$20
.a8
	sta $4202            ; WRMPYA
	txa
	sta $4203            ; WRMPYB
	nop
	nop
	nop
	nop
	nop
	nop
	nop
	nop
	rep #$31
.a16
	lda $4216            ; RDMPYL/RDMPYH
	rts

; 16bit * 16bit -> unsigned 32bit shift-and-add multiply.
; @param a<16-bit>  multiplicand a
; @param x<16-bit>  multiplicand b
; @return a<16-bit> result, low word
; @return x<16-bit> result, high word
Core_Math_Mul:
	rep #$31
.a16
	sta Math_Mul_Multiplier
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
Math_Div_Quotient_Lo = $0428
Math_Mul_Multiplicand_Lo = $0422
Math_Mul_Multiplier_Lo = $0420
Math_Mul_ProductHi_Lo = $0426
Math_Mul_ProductLo_Lo = $0424

	stx.w Math_Mul_Multiplicand_Lo
	stz.w Math_Mul_ProductLo_Lo
	stz.w Math_Mul_ProductHi_Lo
	sep #$20
.a8
	lda #0
	ldx #$10
Core_Math_Mul__bit_loop:
	lsr.w Math_Mul_Multiplier_Lo+1
	ror.w Math_Mul_Multiplier_Lo
	bcc Core_Math_Mul__skip_add
	lda Math_Mul_ProductHi
	clc
	adc Math_Mul_Multiplicand
	sta Math_Mul_ProductHi
	lda.l Math_Mul_ProductHi+1
	adc.l Math_Mul_Multiplicand+1
Core_Math_Mul__skip_add:
	ror a
	sta.l Math_Mul_ProductHi+1
	ror.w Math_Mul_ProductHi_Lo
	ror.w Math_Mul_ProductLo_Lo+1
	ror.w Math_Mul_ProductLo_Lo
	dex
	bne Core_Math_Mul__bit_loop
	rep #$31
.a16
	lda Math_Mul_ProductLo
	ldx.w Math_Mul_ProductHi_Lo
	rts

; @param a<16-bit>  integer 0
; @param x<16-bit>  integer 1
; @return a<16-bit> larger of the two (unsigned)
Core_Math_Max:
	rep #$31
.a16
	phx
	cmp 1,s
	bcs Core_Math_Max__done
	txa
Core_Math_Max__done:
	plx
	rts

; @param a<16-bit>  integer 0
; @param x<16-bit>  integer 1
; @return a<16-bit> smaller of the two (unsigned)
Core_Math_Min:
	rep #$31
.a16
	phx
	cmp 1,s
	bcc Core_Math_Min__done
	txa
Core_Math_Min__done:
	plx
	rts

; @param a<16-bit>  signed integer
; @return a<16-bit> absolute value
;
; NOTE (inherited from upstream): `rep` only changes register widths, it does
; not recompute N/Z from the new width. The `bpl` below trusts whatever N flag
; the caller's last A-affecting instruction left behind, so the caller must
; load `a` in 16-bit mode before calling — loading it in 8-bit mode leaves N
; reflecting only bit 7, not the true 16-bit sign (bit 15).
Core_Math_Abs:
	rep #$31
.a16
	bpl Core_Math_Abs__done
	eor #$ffff
	inc a
Core_Math_Abs__done:
	rts

; 16bit / 16bit -> quotient + remainder, restoring binary division.
; Division by zero returns 0 rather than the original's assert/error (this
; project doesn't have that error subsystem ported over).
; @param a<16-bit>  divisor
; @param x<16-bit>  dividend
; @return a<16-bit> quotient
; @return x<16-bit> remainder
Core_Math_Div:
	rep #$31
.a16
	stz.w Math_Div_Quotient_Lo
	ldy #1
	cmp #0
	bne Core_Math_Div__has_divisor
	lda #0
	tax
	rts

Core_Math_Div__has_divisor:
Core_Math_Div__normalize_loop:
.a16
.i16
	asl a
	bcs Core_Math_Div__normalized
	iny
	cpy #17
	bne Core_Math_Div__normalize_loop
Core_Math_Div__normalized:
	ror a
Core_Math_Div__sub_loop:
	pha
	txa
	sec
	sbc 1,s
	bcc Core_Math_Div__no_borrow
	tax
Core_Math_Div__no_borrow:
	rol.w Math_Div_Quotient_Lo
	pla
	lsr a
	dey
	bne Core_Math_Div__sub_loop

	lda Math_Div_Quotient
	rts
