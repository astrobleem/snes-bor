; ============================================================================
; core/vm/vm_dec16_heavy.pasm -- Gate 5 (plan_vm.md §7): Q16.16 multiply/
; divide/format primitives. Lives in bank 1, appended directly after the
; TAD audio blob's `.incbin` inside main.pasm (still `.bank 1`, no new
; `.org` -- labels resolve correctly right after the blob's bytes, same
; "Fixed" `.incbin` sizing behavior CLAUDE.md's Architecture section
; documents). Reached from bank 0 (vm_dec16.pasm/vm_arith32.pasm) via
; `jsl`/`rtl` on the three entry points below -- vm_consts.pasm's
; VM_DEC_BANK note explains why this can't live in bank 0's tight
; $9000-$AC00 VM window instead.
;
; This file was measured NOT safe to reach via a `.bank 1` -> `.bank 0`
; switch-back from inside the $9000 VM region (a real, reproduced Poppy
; hazard: a fresh 3-bank repro with a mid-file switch-away-and-back placed
; a later label's bytes at the WRONG address, overlapping earlier code --
; see the 2026-08-20 session notes). A one-directional bank sequence
; (bank 0 -> bank 1, never switching back) was separately confirmed correct
; in the same repro, which is the shape used here and by the existing
; audio-blob section above.
;
; Entirely self-contained: no calls back into bank-0 routines (Core_Math_Mul,
; Vm_DivMod32Unsigned, Vm_Negate32) since those are `jsr`/`rts` routines --
; calling them via `jsl` from here would push a 3-byte return address onto
; the stack that their `rts` only pops 2 bytes of, corrupting every
; subsequent return on the stack. Every primitive below is a fresh, local
; implementation instead (vm_consts.pasm's VmDec_* scratch cells are shared
; WRAM, safe to touch from any bank's code).
;
; Calling convention: the three `jsl` entry points (Vm_Dec_Q16Mul,
; Vm_Dec_Q16DivSigned, Vm_Dec_FormatSlot) always expect and always leave
; .a16/.i16 -- bank-0 callers arrange the entry state explicitly (see
; vm_arith32.pasm's Vm_Op_Mul/Vm_Op_Div, vm_dec16.pasm's
; Vm_Dec_ConcatCoerce). Every OTHER label in this file is a private helper,
; `jsr`'d only from elsewhere in this same file, and never bothers with
; php/plp width preservation -- this whole file operates in .a16/.i16
; throughout except the handful of explicitly `sep #$20`-bracketed spots
; that touch a single byte (a slot's type tag, or one ASCII character),
; each immediately followed by `rep #$31` before anything 16-bit resumes.
; ============================================================================
.a16
.i16

; ============================================================================
; Vm_Dec_Mul16x16 -- in: X = multiplicand, A = multiplier (both .a16).
; out: A = product low 16 bits, X = product high 16 bits. Classic shift-add
; unsigned 16x16->32 multiply -- deliberately NOT core/math.pasm's
; Core_Math_Mul (see this file's header on why a bank-1 routine can't call
; a bank-0 `jsr`/`rts` routine via `jsl`).
; ============================================================================
Vm_Dec_Mul16x16:
.a16
.i16
    sta.l VmDec_MulTmpMultiplier   ; save A (multiplier) first -- STX has no
                                     ; absolute-long form (65816 restriction,
                                     ; same as vm_arith32.pasm's own header
                                     ; note on ASL/LSR/ROL/ROR/LDX/STX), so
                                     ; X (multiplicand) must move through A
                                     ; via `txa`, which would otherwise
                                     ; clobber the multiplier if done first
    txa
    sta.l VmDec_MulTmpMultiplicand
    lda #0
    sta.l VmDec_MulTmpProdLo
    sta.l VmDec_MulTmpProdHi
    ldx #16

Vm_Dec_Mul16x16__loop:
.a16
.i16
    lda.l VmDec_MulTmpMultiplier
    lsr a
    sta.l VmDec_MulTmpMultiplier
    bcc Vm_Dec_Mul16x16__skip_add
    lda.l VmDec_MulTmpProdHi
    clc
    adc.l VmDec_MulTmpMultiplicand
    sta.l VmDec_MulTmpProdHi

Vm_Dec_Mul16x16__skip_add:
.a16
.i16
    lda.l VmDec_MulTmpProdHi
    lsr a
    sta.l VmDec_MulTmpProdHi
    lda.l VmDec_MulTmpProdLo
    ror a
    sta.l VmDec_MulTmpProdLo
    dex
    bne Vm_Dec_Mul16x16__loop

    lda.l VmDec_MulTmpProdHi
    tax
    lda.l VmDec_MulTmpProdLo
    rts

; ============================================================================
; Vm_Dec_DivModNUnsigned -- in: X = iteration count (32 for a plain 32/32
; unsigned divide, 48 for Q16Div's (a<<16)/b -- see Vm_Dec_Q16DivSigned's
; own header for why the same loop with a different count computes that
; shift for free), VmDec_DivQLo/Hi = dividend (becomes the quotient),
; VmDec_DivDLo/Hi = divisor (caller-guaranteed nonzero). out:
; VmDec_DivQLo/Hi = quotient, VmDec_DivRLo/Hi = remainder. Same restoring
; binary-division algorithm as vm_arith32.pasm's Vm_DivMod32Unsigned
; (bank 0) -- duplicated here rather than called cross-bank, per this
; file's header.
; ============================================================================
Vm_Dec_DivModNUnsigned:
.a16
.i16
    lda #0
    sta.l VmDec_DivRLo
    sta.l VmDec_DivRHi

Vm_Dec_DivModNUnsigned__loop:
.a16
.i16
    clc
    lda.l VmDec_DivQLo
    rol a
    sta.l VmDec_DivQLo
    lda.l VmDec_DivQHi
    rol a
    sta.l VmDec_DivQHi
    lda.l VmDec_DivRLo
    rol a
    sta.l VmDec_DivRLo
    lda.l VmDec_DivRHi
    rol a
    sta.l VmDec_DivRHi

    lda.l VmDec_DivRHi
    cmp.l VmDec_DivDHi
    bcc Vm_Dec_DivModNUnsigned__skip
    bne Vm_Dec_DivModNUnsigned__dosub
    lda.l VmDec_DivRLo
    cmp.l VmDec_DivDLo
    bcc Vm_Dec_DivModNUnsigned__skip

Vm_Dec_DivModNUnsigned__dosub:
.a16
.i16
    sec
    lda.l VmDec_DivRLo
    sbc.l VmDec_DivDLo
    sta.l VmDec_DivRLo
    lda.l VmDec_DivRHi
    sbc.l VmDec_DivDHi
    sta.l VmDec_DivRHi
    lda.l VmDec_DivQLo
    ora #1
    sta.l VmDec_DivQLo

Vm_Dec_DivModNUnsigned__skip:
.a16
.i16
    dex
    bne Vm_Dec_DivModNUnsigned__loop
    rts

; ============================================================================
; Vm_Dec_Q16Mul -- in: VmPriv_LeftLo/Hi (a), VmPriv_RightLo/Hi (b), raw
; Q16.16. out: VmPriv_LeftLo/Hi = (a*b)>>16, truncated toward zero (same
; convention as DIV's truncate-toward-zero, applied here by computing on
; unsigned magnitudes then reapplying the sign afterward -- an arithmetic
; right shift of a negative two's-complement product would floor instead,
; which is a different, unwanted rounding rule; see vm_consts.pasm's own
; header for why truncate-toward-zero was picked). `jsl`/`rtl` entry point.
;
; Full 64-bit unsigned product of the two magnitudes via 4 partial 16x16->32
; products (LL/LH/HL/HH), keeping only bits 16-47 (the >>16 result, mod
; 2^32 -- bits 48-63 and any final carry out of bit 47 are simply dropped,
; the same wrap convention Gate 2 already uses everywhere): word1 (bits
; 16-31) = LLhi + LHlo + HLlo, with its carry-out rippling into word2
; (bits 32-47) = LHhi + HLhi + HHlo. See this file's header comment above
; the combine step for the bit-position reasoning.
; ============================================================================
Vm_Dec_Q16Mul:
.a16
.i16
    lda.l VmPriv_LeftHi
    and #$8000
    sta.l VmDec_SignA
    lda.l VmPriv_RightHi
    and #$8000
    sta.l VmDec_SignB

    lda.l VmPriv_LeftLo
    sta.l VmDec_MagALo
    lda.l VmPriv_LeftHi
    sta.l VmDec_MagAHi
    lda.l VmDec_SignA
    beq Vm_Dec_Q16Mul__a_pos
    sec
    lda #0
    sbc.l VmDec_MagALo
    sta.l VmDec_MagALo
    lda #0
    sbc.l VmDec_MagAHi
    sta.l VmDec_MagAHi

Vm_Dec_Q16Mul__a_pos:
.a16
.i16
    lda.l VmPriv_RightLo
    sta.l VmDec_MagBLo
    lda.l VmPriv_RightHi
    sta.l VmDec_MagBHi
    lda.l VmDec_SignB
    beq Vm_Dec_Q16Mul__b_pos
    sec
    lda #0
    sbc.l VmDec_MagBLo
    sta.l VmDec_MagBLo
    lda #0
    sbc.l VmDec_MagBHi
    sta.l VmDec_MagBHi

Vm_Dec_Q16Mul__b_pos:
.a16
.i16
    lda.l VmDec_MagALo
    tax
    lda.l VmDec_MagBLo
    jsr Vm_Dec_Mul16x16          ; loA*loB -> keep only .hi (LLhi)
    txa
    sta.l VmDec_LLhi

    lda.l VmDec_MagALo
    tax
    lda.l VmDec_MagBHi
    jsr Vm_Dec_Mul16x16          ; loA*hiB -> LHlo/LHhi
    sta.l VmDec_LHlo
    txa
    sta.l VmDec_LHhi

    lda.l VmDec_MagAHi
    tax
    lda.l VmDec_MagBLo
    jsr Vm_Dec_Mul16x16          ; hiA*loB -> HLlo/HLhi
    sta.l VmDec_HLlo
    txa
    sta.l VmDec_HLhi

    lda.l VmDec_MagAHi
    tax
    lda.l VmDec_MagBHi
    jsr Vm_Dec_Mul16x16          ; hiA*hiB -> keep only .lo (HHlo)
    sta.l VmDec_HHlo

    lda #0
    sta.l VmDec_MulWord1
    sta.l VmDec_MulWord2

    clc
    lda.l VmDec_MulWord1
    adc.l VmDec_LLhi
    sta.l VmDec_MulWord1
    lda.l VmDec_MulWord2
    adc #0
    sta.l VmDec_MulWord2

    clc
    lda.l VmDec_MulWord1
    adc.l VmDec_LHlo
    sta.l VmDec_MulWord1
    lda.l VmDec_MulWord2
    adc #0
    sta.l VmDec_MulWord2

    clc
    lda.l VmDec_MulWord1
    adc.l VmDec_HLlo
    sta.l VmDec_MulWord1
    lda.l VmDec_MulWord2
    adc #0
    sta.l VmDec_MulWord2

    clc
    lda.l VmDec_MulWord2
    adc.l VmDec_LHhi
    sta.l VmDec_MulWord2

    clc
    lda.l VmDec_MulWord2
    adc.l VmDec_HLhi
    sta.l VmDec_MulWord2

    clc
    lda.l VmDec_MulWord2
    adc.l VmDec_HHlo
    sta.l VmDec_MulWord2

    lda.l VmDec_SignA
    eor.l VmDec_SignB
    beq Vm_Dec_Q16Mul__no_negate
    sec
    lda #0
    sbc.l VmDec_MulWord1
    sta.l VmDec_MulWord1
    lda #0
    sbc.l VmDec_MulWord2
    sta.l VmDec_MulWord2

Vm_Dec_Q16Mul__no_negate:
.a16
.i16
    lda.l VmDec_MulWord1
    sta.l VmPriv_LeftLo
    lda.l VmDec_MulWord2
    sta.l VmPriv_LeftHi
    rtl

; ============================================================================
; Vm_Dec_Q16DivSigned -- in: VmPriv_LeftLo/Hi (dividend 'a'),
; VmPriv_RightLo/Hi (divisor 'b', caller-guaranteed nonzero -- Vm_Op_Div's
; own EMPTY-on-zero check runs before this is ever reached). out:
; VmPriv_LeftLo/Hi = (a<<16)/b, truncated toward zero. `jsl`/`rtl` entry.
;
; Computed as abs(a)/abs(b) via Vm_Dec_DivModNUnsigned with a 48-iteration
; count instead of 32, sign reapplied after (same abs-then-sign-reapply
; shape as vm_arith32.pasm's Vm_DivMod32Signed). The extra 16 iterations
; are what supply the `<<16` for free: the restoring-division loop's own
; shift-in bit for the quotient register's LSB is always 0 unless a
; subtract sets it -- exactly "bring down a 0" in long-division terms --
; so continuing the SAME loop 16 iterations past the point where the
; seeded dividend's real bits are exhausted computes precisely
; floor(a<<16 / b) with no separate pre-shift step, and any quotient bits
; that would have landed at bit 32 or above are naturally dropped by
; VmDec_DivQLo/Hi's own 32-bit width (the same mod-2^32 wrap convention
; used throughout this VM). Verified by hand on a scaled-down 4-bit/2-extra
; worked example before writing this file (see the 2026-08-20 session
; notes) -- non-obvious enough that a future reader re-deriving this from
; scratch is expected, hence the worked-example pointer instead of just
; asserting it.
; ============================================================================
Vm_Dec_Q16DivSigned:
.a16
.i16
    lda.l VmPriv_LeftHi
    and #$8000
    sta.l VmDec_SignA
    lda.l VmPriv_RightHi
    and #$8000
    sta.l VmDec_SignB

    lda.l VmPriv_LeftLo
    sta.l VmDec_DivQLo
    lda.l VmPriv_LeftHi
    sta.l VmDec_DivQHi
    lda.l VmDec_SignA
    beq Vm_Dec_Q16DivSigned__a_pos
    sec
    lda #0
    sbc.l VmDec_DivQLo
    sta.l VmDec_DivQLo
    lda #0
    sbc.l VmDec_DivQHi
    sta.l VmDec_DivQHi

Vm_Dec_Q16DivSigned__a_pos:
.a16
.i16
    lda.l VmPriv_RightLo
    sta.l VmDec_DivDLo
    lda.l VmPriv_RightHi
    sta.l VmDec_DivDHi
    lda.l VmDec_SignB
    beq Vm_Dec_Q16DivSigned__b_pos
    sec
    lda #0
    sbc.l VmDec_DivDLo
    sta.l VmDec_DivDLo
    lda #0
    sbc.l VmDec_DivDHi
    sta.l VmDec_DivDHi

Vm_Dec_Q16DivSigned__b_pos:
.a16
.i16
    ldx #48
    jsr Vm_Dec_DivModNUnsigned

    lda.l VmDec_SignA
    eor.l VmDec_SignB
    beq Vm_Dec_Q16DivSigned__no_negate
    sec
    lda #0
    sbc.l VmDec_DivQLo
    sta.l VmDec_DivQLo
    lda #0
    sbc.l VmDec_DivQHi
    sta.l VmDec_DivQHi

Vm_Dec_Q16DivSigned__no_negate:
.a16
.i16
    lda.l VmDec_DivQLo
    sta.l VmPriv_LeftLo
    lda.l VmDec_DivQHi
    sta.l VmPriv_LeftHi
    rtl

; ============================================================================
; Vm_Dec_FormatMagnitude32 -- in: VmDec_MagALo/Hi = UNSIGNED 32-bit
; magnitude, no sign handling. Appends its plain decimal digits (no
; leading zeros; a zero value emits a single "0") at
; VmDec_FormatBuf+VmDec_FormatLen and advances VmDec_FormatLen. Repeated
; divide-by-10 via Vm_Dec_DivModNUnsigned (X=32, divisor 10), collecting
; remainders LSD-first into VmDec_DigitStack, then writing them out in
; reverse (MSD-first) -- the standard "divide, collect, reverse" integer-
; to-decimal algorithm.
; ============================================================================
Vm_Dec_FormatMagnitude32:
.a16
.i16
    lda #0
    sta.l VmDec_FmtDigitCount

    lda.l VmDec_MagALo
    ora.l VmDec_MagAHi
    bne Vm_Dec_FormatMagnitude32__loop
    sep #$20
.a8
    lda #0
    sta.l VmDec_DigitStack+0
    rep #$31
.a16
.i16
    lda #1
    sta.l VmDec_FmtDigitCount
    bra Vm_Dec_FormatMagnitude32__write

Vm_Dec_FormatMagnitude32__loop:
.a16
.i16
    lda.l VmDec_MagALo
    sta.l VmDec_DivQLo
    lda.l VmDec_MagAHi
    sta.l VmDec_DivQHi
    lda #10
    sta.l VmDec_DivDLo
    lda #0
    sta.l VmDec_DivDHi
    ldx #32
    jsr Vm_Dec_DivModNUnsigned

    lda.l VmDec_DivQLo
    sta.l VmDec_MagALo
    lda.l VmDec_DivQHi
    sta.l VmDec_MagAHi

    lda.l VmDec_FmtDigitCount
    tax
    lda.l VmDec_DivRLo
    sep #$20
.a8
    sta.l VmDec_DigitStack,x
    rep #$31
.a16
.i16
    lda.l VmDec_FmtDigitCount
    inc a
    sta.l VmDec_FmtDigitCount

    lda.l VmDec_MagALo
    ora.l VmDec_MagAHi
    bne Vm_Dec_FormatMagnitude32__loop

Vm_Dec_FormatMagnitude32__write:
.a16
.i16
    lda.l VmDec_FmtDigitCount

Vm_Dec_FormatMagnitude32__write_loop:
.a16
.i16
    beq Vm_Dec_FormatMagnitude32__write_done
    dec a
    pha
    tax
    sep #$20
.a8
    lda.l VmDec_DigitStack,x
    clc
    adc #$30                    ; ASCII '0'
    pha
    rep #$31
.a16
.i16
    lda.l VmDec_FormatLen
    tax
    sep #$20
.a8
    pla
    sta.l VmDec_FormatBuf,x
    rep #$31
.a16
.i16
    lda.l VmDec_FormatLen
    inc a
    sta.l VmDec_FormatLen
    pla
    bra Vm_Dec_FormatMagnitude32__write_loop

Vm_Dec_FormatMagnitude32__write_done:
.a16
.i16
    rts

; ============================================================================
; Vm_Dec_FormatInt32 -- in: VmDec_MagALo/Hi = signed 32-bit value. Sets
; VmDec_FormatLen=0, writes a leading '-' if negative (and negates
; VmDec_MagALo/Hi in place to its magnitude), then defers to
; Vm_Dec_FormatMagnitude32. Out: Y (.a16) = final length (also left in
; VmDec_FormatLen).
; ============================================================================
Vm_Dec_FormatInt32:
.a16
.i16
    lda #0
    sta.l VmDec_FormatLen

    lda.l VmDec_MagAHi
    and #$8000
    beq Vm_Dec_FormatInt32__no_sign
    sec
    lda #0
    sbc.l VmDec_MagALo
    sta.l VmDec_MagALo
    lda #0
    sbc.l VmDec_MagAHi
    sta.l VmDec_MagAHi
    sep #$20
.a8
    lda #$2D                    ; ASCII '-'
    sta.l VmDec_FormatBuf+0
    rep #$31
.a16
.i16
    lda #1
    sta.l VmDec_FormatLen

Vm_Dec_FormatInt32__no_sign:
.a16
.i16
    jsr Vm_Dec_FormatMagnitude32
    lda.l VmDec_FormatLen
    tay
    rts

; ============================================================================
; Vm_Dec_FracDigit -- in: VmDec_FmtFracLo/Hi = a 32-bit value whose HIGH
; word is always 0 on entry (the fractional part in progress, 0..65535
; scaled). Multiplies it by 10 (via shift-and-add: x*10 = (x<<3)+(x<<1))
; and splits the result back into digit (the new high word, 0-9) and the
; next iteration's fraction (the new low word) -- vm_consts.pasm's own
; header has the exact `frac *= 10; digit = frac >> 16; frac &= $FFFF`
; rule this implements. Out: A (.a16, low byte meaningful) = digit 0-9;
; VmDec_FmtFracLo holds the next iteration's input, VmDec_FmtFracHi is
; reset to 0.
; ============================================================================
Vm_Dec_FracDigit:
.a16
.i16
    lda.l VmDec_FmtFracLo
    asl a
    sta.l VmDec_MulWord1          ; scratch reuse: (frac<<1)
    lda.l VmDec_FmtFracHi
    rol a
    sta.l VmDec_MulWord2

    lda.l VmDec_FmtFracLo
    asl a
    sta.l VmDec_FmtFracLo
    lda.l VmDec_FmtFracHi
    rol a
    sta.l VmDec_FmtFracHi
    lda.l VmDec_FmtFracLo
    asl a
    sta.l VmDec_FmtFracLo
    lda.l VmDec_FmtFracHi
    rol a
    sta.l VmDec_FmtFracHi          ; frac now (original<<3)

    clc
    lda.l VmDec_FmtFracLo
    adc.l VmDec_MulWord1
    sta.l VmDec_FmtFracLo
    lda.l VmDec_FmtFracHi
    adc.l VmDec_MulWord2
    sta.l VmDec_FmtFracHi          ; frac now (original*10)

    lda.l VmDec_FmtFracHi          ; the digit (0-9)
    pha
    lda #0
    sta.l VmDec_FmtFracHi
    pla
    rts

; ============================================================================
; Vm_Dec_FormatSlot -- Gate 5's "cartridge-defined decimal->string format"
; (plan_vm.md §7), the sole `jsl`/`rtl` entry point wired to a real
; caller: vm_dec16.pasm's Vm_Dec_ConcatCoerce (ADD's STR+numeric coercion,
; vm_run.pasm's Vm_Op_Add). In: A (.a16) = slot index (already known
; INTEGER or DECIMAL by the caller). Out: VmDec_FormatBuf[0..Y) holds the
; ASCII text, Y (.a16) = its length.
;
; INTEGER -> bare signed decimal via Vm_Dec_FormatInt32 directly.
; DECIMAL -> sign + unsigned-integer-part digits + "." + exactly 4
; fractional digits, ALL truncated (never rounded) from the raw Q16.16
; bits, sign attached once to the whole value (vm_consts.pasm's header has
; worked examples, e.g. -0.5 -> "-0.5000", not "-1.5000" or "0.-5000").
; This requires computing the signed value's absolute magnitude ONCE up
; front (its Hi word = unsigned integer-part digits, Lo word = unsigned
; fraction) rather than formatting the raw (possibly negative-with-a-
; positive-looking-fraction) Hi/Lo split directly -- Hi alone is
; floor(value), not the truncated-toward-zero magnitude a negative
; fractional value needs.
; ============================================================================
Vm_Dec_FormatSlot:
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_DECIMAL
    beq Vm_Dec_FormatSlot__dec
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmDec_MagALo
    lda.l VmSlots_Wram+6,x
    sta.l VmDec_MagAHi
    jsr Vm_Dec_FormatInt32
    rtl

Vm_Dec_FormatSlot__dec:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmDec_MagALo             ; raw fraction (Lo word)
    lda.l VmSlots_Wram+6,x
    sta.l VmDec_MagAHi             ; raw signed integer part (Hi word)

    lda #0
    sta.l VmDec_FormatLen

    lda.l VmDec_MagAHi
    and #$8000
    sta.l VmDec_SignA
    beq Vm_Dec_FormatSlot__dec_pos
    ; negate the FULL 32-bit raw value (MagAHi:MagALo) to get the
    ; truncated-toward-zero magnitude's integer part (Hi) and fraction (Lo)
    sec
    lda #0
    sbc.l VmDec_MagALo
    sta.l VmDec_MagALo
    lda #0
    sbc.l VmDec_MagAHi
    sta.l VmDec_MagAHi
    sep #$20
.a8
    lda #$2D                       ; ASCII '-'
    sta.l VmDec_FormatBuf+0
    rep #$31
.a16
.i16
    lda #1
    sta.l VmDec_FormatLen

Vm_Dec_FormatSlot__dec_pos:
.a16
.i16
    ; save the (now-unsigned) fraction before MagALo gets overwritten by
    ; the integer-part formatting call below
    lda.l VmDec_MagALo
    sta.l VmDec_FmtFracLo
    lda #0
    sta.l VmDec_FmtFracHi

    lda.l VmDec_MagAHi
    sta.l VmDec_MagALo
    lda #0
    sta.l VmDec_MagAHi
    jsr Vm_Dec_FormatMagnitude32   ; appends integer-part digits

    lda.l VmDec_FormatLen
    tax
    sep #$20
.a8
    lda #$2E                       ; ASCII '.'
    sta.l VmDec_FormatBuf,x
    rep #$31
.a16
.i16
    lda.l VmDec_FormatLen
    inc a
    sta.l VmDec_FormatLen

    lda #4
    sta.l VmDec_MulWord1           ; scratch reuse: fractional-digit
                                     ; countdown (X is not usable as a
                                     ; loop counter here -- FormatBuf's
                                     ; indexed store below needs X, and
                                     ; long addressing has no `,y` form,
                                     ; see this file's header)

Vm_Dec_FormatSlot__frac_loop:
.a16
.i16
    jsr Vm_Dec_FracDigit
    clc
    adc #$30                       ; ASCII '0' -- A's high byte is 0 here
                                     ; (Vm_Dec_FracDigit's digit is 0-9),
                                     ; safe to adc in .a16 without masking
    sep #$20
.a8
    pha                             ; 1-byte push -- must match the 1-byte
                                     ; pull below (a mismatched push/pull
                                     ; width leaves a stray byte on the
                                     ; stack, corrupting the next return)
    rep #$31
.a16
.i16
    lda.l VmDec_FormatLen
    tax
    sep #$20
.a8
    pla
    sta.l VmDec_FormatBuf,x
    rep #$31
.a16
.i16
    lda.l VmDec_FormatLen
    inc a
    sta.l VmDec_FormatLen
    lda.l VmDec_MulWord1
    dec a
    sta.l VmDec_MulWord1
    bne Vm_Dec_FormatSlot__frac_loop

    lda.l VmDec_FormatLen
    tay
    rtl
