; ============================================================================
; core/input.pasm — controller polling with press/trigger/old edge detection
;
; Ported to Poppy syntax from SNES-SuperBossGaiden (src/core/input.65816),
; used with the original author's permission. Trimmed to a single controller
; (port 1) — the original supports 3 devices via manual WRIO strobing for
; multitap; that's not needed yet, so it's left out rather than carried over
; unused. Bring the multi-device version back if/when a second player lands.
;
; Uses hardware auto-joypad-read ($4200 bit 0) instead of manual strobing,
; gated on $4212 (HVBJOY) bit 0 so a poll never reads mid-latch.
;
; Uses global (not @-local) labels throughout — see core/random.pasm's header
; comment for why: @-local labels mis-resolve once reached via .include in
; this Poppy build, confirmed by isolated repro.
; ============================================================================

INPUT_SIGNATURE_MASK = $000f   ; low 4 bits of JOY1L are always 0 on a real pad

.enum $7E0410
	Input_press    .dw
	Input_trigger  .dw
	Input_old      .dw
.ende

; Call once during boot.
Core_Input_Init:
	sep #$20
.a8
	lda #$01
	sta $4200            ; enable auto-joypad read only (NMI/IRQ stay off)
	rep #$31
.a16
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
Input_old_Lo = $0414
Input_press_Lo = $0410
Input_trigger_Lo = $0412

	stz.w Input_press_Lo
	stz.w Input_trigger_Lo
	stz.w Input_old_Lo
	rts

; Call once per frame. Safe to call more than once per frame (idempotent
; between hardware auto-reads): trigger only reflects the edge since the
; last *hardware* latch, not the last call.
;
; @return Input_press    currently-held buttons
; @return Input_trigger  buttons newly pressed since the last poll
Core_Input_Poll:
	rep #$31
.a16
Core_Input_Poll__wait_busy:
	lda $4212            ; HVBJOY
	and #$0001           ; bit0: auto-joypad-read in progress
	bne Core_Input_Poll__wait_busy

	lda $4218            ; JOY1L/JOY1H combined (B Y Sel Start U D L R | A X L R 0 0 0 0)
	bit #INPUT_SIGNATURE_MASK
	bne Core_Input_Poll__no_pad   ; low 4 bits set -> not a real controller, ignore

	pha
	lda Input_press
	sta Input_old
	eor #$ffff
	sta Input_trigger    ; ~old, stashed
	pla
	sta Input_press
	and Input_trigger
	sta Input_trigger    ; = new & ~old = newly-pressed bits
	rts

Core_Input_Poll__no_pad:
	stz.w Input_press_Lo
	stz.w Input_old_Lo
	stz.w Input_trigger_Lo
	rts
