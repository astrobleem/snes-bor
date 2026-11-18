; ============================================================================
; core/random.pasm — tiny 8-bit pseudo-random number generator
;
; Ported to Poppy syntax from SNES-SuperBossGaiden (src/core/random.65816),
; used with the original author's permission. Same add-and-shuffle 4-byte
; generator, just re-expressed for Poppy (WLA-DX .ramsection -> .enum,
; explicit byte-wide seeding instead of the 16-bit paired store trick).
;
; Uses global (not @-local) labels throughout: this Poppy build mis-resolves
; @-local labels once the containing code is reached via .include (branch
; target lookup fails at include time even though the identical code
; assembles fine standalone) — confirmed by isolated repro. main.pasm itself
; never uses local labels either, so this also matches existing convention.
; ============================================================================

.enum $7E0400
	Random_state1  .db
	Random_state2  .db
	Random_state3  .db
	Random_state4  .db
.ende

; Call once during boot.
Core_Random_Init:
	sep #$20
.a8
	lda #$34
	sta Random_state1
	lda #$12
	sta Random_state2
	lda #$aa
	sta Random_state3
	lda #$55
	sta Random_state4
	rts

; @return a<8-bit>  pseudo-random byte
Core_Random_Get:
	php
	sep #$20
.a8
	lda Random_state3
	sta Random_state4
	lda Random_state2
	sta Random_state3
	lda Random_state1
	sta Random_state2
	cmp Random_state3
	bmi Core_Random_Get__use_state3
	lda Random_state3
Core_Random_Get__use_state3:
	clc
	adc Random_state4
	sta Random_state1
	plp
	lda Random_state1
	rts
