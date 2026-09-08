; ============================================================================
; core/input.pasm — controller polling with press/trigger/old edge detection
;
; Ported to Poppy syntax from SNES-SuperBossGaiden (src/core/input.65816),
; used with the original author's permission. The accepted one-player path
; remains the JOY1 state below. The bounded G13 slice adds an independent JOY2
; state block without adding multitap support or changing the P1 aliases.
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

.enum $7E0416
	Input2_press   .dw
	Input2_trigger .dw
	Input2_old     .dw
.ende

; Boundary-proof latches. These retain the exact hardware words consumed by
; the most recent poll, so the verifier does not infer delivery from the
; post-release edge state. They occupy the documented gap before Math_*.
Input_last_raw_Addr  = $7E041C
Input2_last_raw_Addr = $7E041E

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
Input2_press_Lo = $0416
Input2_trigger_Lo = $0418
Input2_old_Lo = $041A
Input_press_Addr = $7E0410
Input_trigger_Addr = $7E0412
Input_old_Addr = $7E0414
Input2_press_Addr = $7E0416
Input2_trigger_Addr = $7E0418
Input2_old_Addr = $7E041A

	lda #0
	sta.l Input_press_Addr
	sta.l Input_trigger_Addr
	sta.l Input_old_Addr
	sta.l Input2_press_Addr
	sta.l Input2_trigger_Addr
	sta.l Input2_old_Addr
	sta.l Input_last_raw_Addr
	sta.l Input2_last_raw_Addr
	sta.l G13_TwoPlayerEnabled
	lda #0
	sta.l G13_P1Out
	sta.l G13_P2Out
	; Power-on WRAM is undefined; explicitly initialize the standalone P2
	; invulnerability timer with the other G13 boot state.
	sep #$20
.a8
	sta.l G13_P2_InvulnFrames
	rep #$31
.a16
.i16
	sta.l G13_P2StartSeen
	sta.l G13_P2TriggerSnapshot
	sta.l G13_P2MaskResult
	rtl

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
	sta.l Input_last_raw_Addr
	bit #INPUT_SIGNATURE_MASK
	bne Core_Input_Poll__no_pad1  ; low 4 bits set -> not a real controller

	pha
	lda.l Input_press_Addr
	sta.l Input_old_Addr
	eor #$ffff
	sta.l Input_trigger_Addr    ; ~old, stashed
	pla
	sta.l Input_press_Addr
	and.l Input_trigger_Addr
	sta.l Input_trigger_Addr    ; = new & ~old = newly-pressed bits
	jsl Core_Input_Poll_P2
	rtl

Core_Input_Poll__no_pad1:
	lda #0
	sta.l Input_press_Addr
	sta.l Input_old_Addr
	sta.l Input_trigger_Addr
	jsl Core_Input_Poll_P2
	rtl
