; ============================================================================
; core/screen.pasm — camera / screen-position manager
;
; Ported (redesigned) from SNES-SuperBossGaiden (src/core/screen.65816 +
; screen.h), used with the original author's permission. Tracks the
; top-left corner of the visible playfield window and eases it toward
; whatever object is "focused" — the classic beat-em-up follow-camera: ease
; speed scales with distance (a lookup table, not a flat speed), and
; vertical follow freezes while the focused object is airborne so the
; camera doesn't jerk on every jump.
;
; Deliberately simplified, not a byte-for-byte port:
;  - The focused object's position/mode is fetched through core/oop.pasm's
;    generic command dispatch (Core_Oop_Call), matching upstream's own
;    architecture (a `lifeform.library.oncommand` method call) — but through
;    THIS project's much smaller generic-command mechanism rather than
;    upstream's whole interface/mixin routine-table system. See
;    Core_Screen__SetTargetPosition below for the exact contract. Since no
;    class in this project implements that command yet (there are no
;    entities at all), this path is included and boot-verified but not
;    exercised end-to-end — same status as core/oop.pasm's own
;    Create/Play/Call machinery before a real class exists.
;  - Upstream's per-direction "lead the camera slightly ahead of movement
;    direction" offset (`SCREEN.DIRECTION.OFFSET`, the 3-bit direction field
;    and its LUT dispatch) isn't ported. It's a real polish feature, but a
;    second return channel and dispatch layer with zero current consumers
;    isn't worth the added surface area yet — the command contract below
;    has room to grow into it later without breaking anything.
;  - Sub-pixel position is a plain (fraction:8, integer:16) fixed-point pair
;    (Screen_PosXFrac/Screen_PosX), not upstream's `ds 3` block accessed via
;    `(Symbol&$ffff)+1`-style offset arithmetic. Same reasoning as
;    core/oop.pasm's handle layout: distinct named fields instead of
;    manual offsets into a shared block avoids ever doing `Symbol+N`
;    arithmetic on a bank-$7E symbol feeding a long-addressable instruction
;    (see core/math.pasm's header for why that's the one to avoid).
;  - `_getCustomTableValue`/`.y` clamp their lookup index against
;    `core.screen.move.lut`'s length even when about to read from the
;    (shorter) airborne table — reading past the end of
;    `core.screen.move.airborne.lut` into whatever ROM data follows it for
;    large enough vertical distances while airborne. Harmless today only
;    because that table happens to be all zeros; not a bug worth carrying
;    forward. This port clamps each lookup against its OWN table's length
;    (Core_Screen__LutLookupX/Y below).
;
; Indexed WRAM access uses `.l`, never `.w` — see core/dma_channel.pasm's
; header note for why `.w` on an indexed bank-$7E symbol silently corrupts
; the instruction stream in this Poppy build.
;
; Uses global (not @-local) labels throughout — see core/random.pasm's
; header comment for why.
; ============================================================================

SCREEN_DEFAULT_SIZE_X = 256
SCREEN_DEFAULT_SIZE_Y = 224

SCREEN_MODE_VOID     = 0
SCREEN_MODE_GROUNDED = 1
SCREEN_MODE_AIRBORNE = 2

; core/oop.pasm generic-command id for "give me your camera-follow data".
; Contract: @param OopCall_Param unused (0); @return carry=handled,
; a<16-bit>=mode (SCREEN_MODE_*), OopCall_ResultX/Y<16-bit>=target position.
SCREEN_CMD_GET_CAMERA_DATA = 1

SCREEN_DEFAULT_SPEED = $0200

.enum $7E1600
	Screen_PosXFrac .db
	Screen_PosX     .dw
	Screen_PosYFrac .db
	Screen_PosY     .dw
	Screen_SizeX    .dw
	Screen_SizeY    .dw
	Screen_MinX     .dw
	Screen_MinY     .dw
	Screen_MaxX     .dw
	Screen_MaxY     .dw
	Screen_RightX   .dw   ; Screen_PosX + Screen_SizeX, cached for onscreen checks
	Screen_BottomY  .dw
	Screen_TargetX  .dw
	Screen_TargetY  .dw
	Screen_Mode     .dw
	Screen_ShakeOffsetX .dw

	; focused object handle — same 3-register shape core/oop.pasm's other
	; handle-consuming functions take (num/id/slot); id=0 means "no focus"
	Screen_FocusNum  .dw
	Screen_FocusId   .dw   ; low byte valid
	Screen_FocusSlot .dw   ; low byte valid

	; internal scratch
	Screen__StepLo      .db
	Screen__StepHi       .db
	Screen__LutDistance .dw
	Screen__Half        .dw
.ende

; (was: .section "screen.luts" superfree -- a WLA-DX leftover from the
; SuperBossGaiden port. Poppy has no .section support and silently ignored the
; directive, so these LUTs have always been placed inline at the current address;
; removing it is byte-identical. It only became visible once the assembler
; started reporting the parse errors it had been swallowing, poppy#382.)
ScreenMoveLut:
	.dw 0, 0, 0, 0, 0
	.dw SCREEN_DEFAULT_SPEED/16, SCREEN_DEFAULT_SPEED/16, SCREEN_DEFAULT_SPEED/16, SCREEN_DEFAULT_SPEED/16
	.dw SCREEN_DEFAULT_SPEED/8, SCREEN_DEFAULT_SPEED/8, SCREEN_DEFAULT_SPEED/8, SCREEN_DEFAULT_SPEED/8
	.dw SCREEN_DEFAULT_SPEED/4, SCREEN_DEFAULT_SPEED/4, SCREEN_DEFAULT_SPEED/4, SCREEN_DEFAULT_SPEED/4
	.dw SCREEN_DEFAULT_SPEED, SCREEN_DEFAULT_SPEED, SCREEN_DEFAULT_SPEED, SCREEN_DEFAULT_SPEED, SCREEN_DEFAULT_SPEED, SCREEN_DEFAULT_SPEED, SCREEN_DEFAULT_SPEED
	.dw SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2
	.dw SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2
	.dw SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2
	.dw SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2, SCREEN_DEFAULT_SPEED*2
	.dw SCREEN_DEFAULT_SPEED*3, SCREEN_DEFAULT_SPEED*3, SCREEN_DEFAULT_SPEED*3, SCREEN_DEFAULT_SPEED*3, SCREEN_DEFAULT_SPEED*3, SCREEN_DEFAULT_SPEED*3
	.dw SCREEN_DEFAULT_SPEED*4-1, SCREEN_DEFAULT_SPEED*4-1
ScreenMoveLutEnd:

; all zeros: vertical follow freezes entirely while the focused object is
; airborne (see Core_Screen__LutLookupY). Kept as real (if currently inert)
; data, not a hardcoded shortcut, so tuning "slow vertical drift while
; airborne" later is a data change here, not a structural one.
ScreenMoveAirborneLut:
	.dw 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
	.dw 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
	.dw 0, 0, 0, 0, 0, 0, 0, 0, 0
ScreenMoveAirborneLutEnd:
.ends

Core_Screen_Init:
	php
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
OopCall_Param_Lo = $0782
Screen_BottomY_Lo = $1614
Screen_FocusId_Lo = $1620
Screen_FocusNum_Lo = $161E
Screen_FocusSlot_Lo = $1622
Screen_MinX_Lo = $160A
Screen_MinY_Lo = $160C
Screen_PosX_Lo = $1601
Screen_PosXFrac_Lo = $1600
Screen_PosY_Lo = $1604
Screen_PosYFrac_Lo = $1603
Screen_RightX_Lo = $1612
Screen_ShakeOffsetX_Lo = $161C

	stz.w Screen_PosX_Lo
	stz.w Screen_PosY_Lo
	stz.w Screen_RightX_Lo
	stz.w Screen_BottomY_Lo
	lda #SCREEN_DEFAULT_SIZE_X
	sta Screen_SizeX
	lda #SCREEN_DEFAULT_SIZE_Y
	sta Screen_SizeY
	stz.w Screen_MinX_Lo
	stz.w Screen_MinY_Lo
	stz.w Screen_ShakeOffsetX_Lo
	lda #$ffff-SCREEN_DEFAULT_SIZE_X
	sta Screen_MaxX
	lda #$ffff-SCREEN_DEFAULT_SIZE_Y
	sta Screen_MaxY
	stz.w Screen_FocusNum_Lo
	stz.w Screen_FocusId_Lo
	stz.w Screen_FocusSlot_Lo
	sep #$20
.a8
	stz.w Screen_PosXFrac_Lo
	stz.w Screen_PosYFrac_Lo
	rep #$31
.a16
	plp
	rts

; @return x<16-bit>  current x position (integer part)
; @return y<16-bit>  current y position (integer part)
Core_Screen_GetPosition:
	ldx.w Screen_PosX_Lo
	ldy.w Screen_PosY_Lo
	rts

; @param a<16-bit>  handle num
; @param x<16-bit>  handle id (low byte)
; @param y<16-bit>  handle slot byte-offset
Core_Screen_Focus:
	php
	rep #$31
.a16
	sta Screen_FocusNum
	stx.w Screen_FocusId_Lo
	sty.w Screen_FocusSlot_Lo
	plp
	rts

; same params as Core_Screen_Focus, but snaps the camera to the target
; immediately instead of easing toward it over subsequent frames
Core_Screen_FocusImmediate:
	php
	rep #$31
.a16
	sta Screen_FocusNum
	stx.w Screen_FocusId_Lo
	sty.w Screen_FocusSlot_Lo

	jsr Core_Screen__SetTargetPosition
	bcc Core_Screen_FocusImmediate__clamp
		lda Screen_TargetX
		sta Screen_PosX
		sep #$20
.a8
		stz.w Screen_PosXFrac_Lo
		rep #$30
.a16
		lda Screen_TargetY
		sta Screen_PosY
		sep #$20
.a8
		stz.w Screen_PosYFrac_Lo
		rep #$30
.a16

Core_Screen_FocusImmediate__clamp:
	jsr Core_Screen__ClampToScreen
	plp
	rts

Core_Screen_Blur:
	php
	rep #$31
.a16
	stz.w Screen_FocusNum_Lo
	stz.w Screen_FocusId_Lo
	stz.w Screen_FocusSlot_Lo
	plp
	rts

; Sets the scrollable playfield bounds. Split into two calls (x bounds here,
; y bounds via Core_Screen_SetPlayfieldHeight) since there's no room for 4
; params across 3 registers — matches how core/oop.pasm handles the same
; register-starvation problem elsewhere, just via two small calls instead
; of a staging scratch var, since these aren't called from a shared hot path.
;
; @param a<16-bit>  playfield min x
; @param x<16-bit>  playfield min y
; @param y<16-bit>  playfield width (max scrollable x = width - size.x - 1)
Core_Screen_SetPlayfieldBorder:
	php
	rep #$31
.a16
	sta Screen_MinX
	stx.w Screen_MinY_Lo
	tya
	sec
	sbc Screen_SizeX
	dec a
	sta Screen_MaxX
	plp
	rts

; @param a<16-bit>  playfield height (max scrollable y = height - size.y - 1)
Core_Screen_SetPlayfieldHeight:
	php
	rep #$31
.a16
	sec
	sbc Screen_SizeY
	dec a
	sta Screen_MaxY
	plp
	rts

; @param x<16-bit>  absolute x position
; @param y<16-bit>  absolute y position
; @return x<16-bit>  screen-relative x (only meaningful if carry set)
; @return y<16-bit>  screen-relative y (only meaningful if carry set)
; @return carry<bool>  set if the position is onscreen
Core_Screen_ConvertAbsoluteToScreen:
	php
	rep #$31
.a16
	cpx.w Screen_PosX_Lo
	bcc Core_Screen_ConvertAbsoluteToScreen__off
	cpy.w Screen_PosY_Lo
	bcc Core_Screen_ConvertAbsoluteToScreen__off
	cpx.w Screen_RightX_Lo
	bcs Core_Screen_ConvertAbsoluteToScreen__off
	cpy.w Screen_BottomY_Lo
	bcs Core_Screen_ConvertAbsoluteToScreen__off

	txa
	sec
	sbc Screen_PosX
	tax
	tya
	sec
	sbc Screen_PosY
	tay
	plp
	sec
	rts

Core_Screen_ConvertAbsoluteToScreen__off:
	plp
	clc
	rts

; @param x<16-bit>  absolute x position
; @param y<16-bit>  absolute y position
; @return carry<bool>  set if any part of a Screen_SizeX x Screen_SizeY box
;                       at (x,y) would be visible onscreen
Core_Screen_CheckIfOnScreen:
	php
	rep #$31
.a16
	cpx.w Screen_PosX_Lo
	bcc Core_Screen_CheckIfOnScreen__off
	txa
	sec
	sbc Screen_SizeX
	cmp Screen_PosX
	bcs Core_Screen_CheckIfOnScreen__off
	cpy.w Screen_PosY_Lo
	bcc Core_Screen_CheckIfOnScreen__off
	tya
	sec
	sbc Screen_SizeY
	cmp Screen_PosY
	bcs Core_Screen_CheckIfOnScreen__off
	plp
	sec
	rts

Core_Screen_CheckIfOnScreen__off:
	plp
	clc
	rts

; @return carry<bool>  true if a focused object supplied fresh target data
;                       (Screen_TargetX/Y, Screen_Mode)
Core_Screen__SetTargetPosition:
	rep #$31
.a16
	lda.l G13_TwoPlayerEnabled
	and #$00FF
	beq Core_Screen__SetTargetPosition__single
	jsl G13_Screen_SetTargetPosition
	sec
	rts

Core_Screen__SetTargetPosition__single:
	rep #$31
	.a16
	.i16
	lda Screen_FocusId
	and #$00ff
	bne Core_Screen__SetTargetPosition__has_focus
	clc
	rts

Core_Screen__SetTargetPosition__has_focus:
	stz.w OopCall_Param_Lo
	lda #SCREEN_CMD_GET_CAMERA_DATA
	sta OopCall_CommandId

	lda Screen_FocusNum
	ldx.w Screen_FocusSlot_Lo
	ldy.w Screen_FocusId_Lo
	jsr Core_Oop_Call
	stx.w Screen_FocusSlot_Lo
	bcs Core_Screen__SetTargetPosition__handled
	clc
	rts

Core_Screen__SetTargetPosition__handled:
	sta Screen_Mode

	lda Screen_SizeX
	lsr a
	sta Screen__Half
	lda OopCall_ResultX
	sec
	sbc Screen__Half
	bcs Core_Screen__SetTargetPosition__x_ok
		lda #0
Core_Screen__SetTargetPosition__x_ok:
	sta Screen_TargetX

	lda Screen_SizeY
	lsr a
	sta Screen__Half
	lda OopCall_ResultY
	sec
	sbc Screen__Half
	bcs Core_Screen__SetTargetPosition__y_ok
		lda #0
Core_Screen__SetTargetPosition__y_ok:
	sta Screen_TargetY

	sec
	rts

; adds `a` (16-bit step magnitude, bits 0-7 -> fraction, bits 8-15 ->
; integer) to (Screen_PosXFrac,Screen_PosX) as a 24-bit fixed-point value.
Core_Screen__AddStepX:
	pha
	and #$00ff
	sep #$20
.a8
	clc
	adc Screen_PosXFrac
	sta Screen_PosXFrac
	rep #$30
.a16
	pla
	xba
	and #$00ff
	sta Screen__StepHi
	lda Screen_PosX
	adc Screen__StepHi
	sta Screen_PosX
	rts

Core_Screen__SubStepX:
	pha
	and #$00ff
	sep #$20
.a8
	sta Screen__StepLo
	lda Screen_PosXFrac
	sec
	sbc Screen__StepLo
	sta Screen_PosXFrac
	rep #$30
.a16
	pla
	xba
	and #$00ff
	sta Screen__StepHi
	lda Screen_PosX
	sbc Screen__StepHi
	sta Screen_PosX
	rts

Core_Screen__AddStepY:
	pha
	and #$00ff
	sep #$20
.a8
	clc
	adc Screen_PosYFrac
	sta Screen_PosYFrac
	rep #$30
.a16
	pla
	xba
	and #$00ff
	sta Screen__StepHi
	lda Screen_PosY
	adc Screen__StepHi
	sta Screen_PosY
	rts

Core_Screen__SubStepY:
	pha
	and #$00ff
	sep #$20
.a8
	sta Screen__StepLo
	lda Screen_PosYFrac
	sec
	sbc Screen__StepLo
	sta Screen_PosYFrac
	rep #$30
.a16
	pla
	xba
	and #$00ff
	sta Screen__StepHi
	lda Screen_PosY
	sbc Screen__StepHi
	sta Screen_PosY
	rts

; @param a<16-bit>  distance (already non-negative)
; @return a<16-bit>  step magnitude — x axis always follows regardless of
;                     grounded/airborne (see header note)
Core_Screen__LutLookupX:
	asl a
	cmp #ScreenMoveLutEnd-ScreenMoveLut
	bcc Core_Screen__LutLookupX__inrange
		lda #ScreenMoveLutEnd-ScreenMoveLut-2
Core_Screen__LutLookupX__inrange:
	tax
	lda.l ScreenMoveLut,x
	rts

; @param a<16-bit>  distance (already non-negative)
; @return a<16-bit>  step magnitude — y axis freezes (0) while airborne
Core_Screen__LutLookupY:
	sta Screen__LutDistance
	lda Screen_Mode
	cmp #SCREEN_MODE_AIRBORNE
	beq Core_Screen__LutLookupY__airborne

	lda Screen__LutDistance
	asl a
	cmp #ScreenMoveLutEnd-ScreenMoveLut
	bcc Core_Screen__LutLookupY__grounded_inrange
		lda #ScreenMoveLutEnd-ScreenMoveLut-2
Core_Screen__LutLookupY__grounded_inrange:
	tax
	lda.l ScreenMoveLut,x
	rts

Core_Screen__LutLookupY__airborne:
	lda Screen__LutDistance
	asl a
	cmp #ScreenMoveAirborneLutEnd-ScreenMoveAirborneLut
	bcc Core_Screen__LutLookupY__airborne_inrange
		lda #ScreenMoveAirborneLutEnd-ScreenMoveAirborneLut-2
Core_Screen__LutLookupY__airborne_inrange:
	tax
	lda.l ScreenMoveAirborneLut,x
	rts

Core_Screen__EaseX:
	sec
	sbc Screen_PosX
	bcc Core_Screen__EaseX__negative
	jsr Core_Screen__LutLookupX
	jmp Core_Screen__AddStepX

Core_Screen__EaseX__negative:
	eor #$ffff
	inc a
	jsr Core_Screen__LutLookupX
	jmp Core_Screen__SubStepX

Core_Screen__EaseY:
	sec
	sbc Screen_PosY
	bcc Core_Screen__EaseY__negative
	jsr Core_Screen__LutLookupY
	jmp Core_Screen__AddStepY

Core_Screen__EaseY__negative:
	eor #$ffff
	inc a
	jsr Core_Screen__LutLookupY
	jmp Core_Screen__SubStepY

Core_Screen__ClampToScreen:
	lda Screen_PosX
	cmp Screen_MinX
	bcs Core_Screen__ClampToScreen__minx_ok
		lda Screen_MinX
		sta Screen_PosX
Core_Screen__ClampToScreen__minx_ok:
	lda Screen_PosX
	cmp Screen_MaxX
	bcc Core_Screen__ClampToScreen__maxx_ok
		lda Screen_MaxX
		sta Screen_PosX
Core_Screen__ClampToScreen__maxx_ok:

	lda Screen_PosY
	cmp Screen_MinY
	bcs Core_Screen__ClampToScreen__miny_ok
		lda Screen_MinY
		sta Screen_PosY
Core_Screen__ClampToScreen__miny_ok:
	lda Screen_PosY
	cmp Screen_MaxY
	bcc Core_Screen__ClampToScreen__maxy_ok
		lda Screen_MaxY
		sta Screen_PosY
Core_Screen__ClampToScreen__maxy_ok:

	lda Screen_PosX
	clc
	adc Screen_SizeX
	sta Screen_RightX
	lda Screen_PosY
	clc
	adc Screen_SizeY
	sta Screen_BottomY
	rts

; called every frame: decays any screen-shake offset, eases toward the
; focused object (if any), and re-clamps to the playfield bounds.
Core_Screen_Play:
	php
	rep #$31
.a16
	lda Screen_ShakeOffsetX
	beq Core_Screen_Play__ease
	bmi Core_Screen_Play__shake_negative
		dec.w Screen_ShakeOffsetX_Lo
		bra Core_Screen_Play__ease
Core_Screen_Play__shake_negative:
	inc.w Screen_ShakeOffsetX_Lo

Core_Screen_Play__ease:
	jsr Core_Screen__SetTargetPosition
	bcc Core_Screen_Play__no_focus

Core_Screen_Play__target_available:

	; The ease LUT deliberately goes to zero at short distances.  If the
	; followed target is beyond the right playfield bound, that deadband can
	; leave Screen_PosX just short of Screen_MaxX forever.  A source queue may
	; legitimately place its final wait/spawn trigger exactly at that bound
	; (Normal 4A does), so finish the final camera approach when only the
	; last eight pixels remain.  The ordinary easing curve is unchanged
	; everywhere else.
	lda Screen_TargetX
	cmp Screen_MaxX
	bcc Core_Screen_Play__normal_ease
	lda Screen_MaxX
	sec
	sbc Screen_PosX
	cmp #9
	bcs Core_Screen_Play__ease_to_right_edge
	lda Screen_MaxX
	sta Screen_PosX
	sep #$20
.a8
	stz.w Screen_PosXFrac_Lo
	rep #$30
.a16
	bra Core_Screen_Play__clamp

; The followed object can be well beyond the legal camera range (for example
; during a source-authored terminal wait).  Feeding that unbounded target to
; the easing LUT selects its saturated far-distance step and can strand the
; camera short of the edge.  Ease toward the legal edge instead; this keeps
; the ordinary curve while ensuring a bounded target distance.
Core_Screen_Play__ease_to_right_edge:
	lda Screen_MaxX
	jsr Core_Screen__EaseX
	lda Screen_TargetY
	jsr Core_Screen__EaseY
	bra Core_Screen_Play__clamp

Core_Screen_Play__normal_ease:

	lda Screen_TargetX
	jsr Core_Screen__EaseX
	lda Screen_TargetY
	jsr Core_Screen__EaseY
	bra Core_Screen_Play__clamp

; A focus can briefly stop returning camera data while a source actor is
; leaving the view.  Preserve the freeze for ordinary stale targets, but do
; not leave the camera short of the hard right edge when its last target was
; already beyond that edge; the bounded final approach is still required by
; a queue trigger at Screen_MaxX.
Core_Screen_Play__no_focus:
	lda Screen_TargetX
	cmp Screen_MaxX
	bcc Core_Screen_Play__clamp
	bra Core_Screen_Play__target_available

Core_Screen_Play__clamp:
	jsr Core_Screen__ClampToScreen
	plp
	rts
