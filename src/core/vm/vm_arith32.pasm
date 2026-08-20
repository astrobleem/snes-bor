; ============================================================================
; core/vm/vm_arith32.pasm -- Gate 2 (plan_vm.md §4): the integer unary/binary
; family. LOAD/SAVE/INC/DEC/POS/NEG/NOT/MUL/DIV/MOD/SUB/SHL/SHR/GE/LE/LT/GT/
; NE/OR/AND/BIT_OR/XOR/BIT_AND.
;
; Included in main.pasm directly after vm_run.pasm. Forward-references
; Core_Math_Mul (core/math.pasm, included later in main.pasm) and every
; Vm_* symbol vm_run.pasm/vm_consts.pasm/bor_vm_opcodes.pasm define --
; vm_run.pasm's own dispatch table already forward-references handlers
; defined hundreds of lines further down in the SAME file (e.g.
; Vm_Dispatch_02 -> Vm_Op_ConstInt), so this project's Poppy build resolves
; global labels regardless of definition order; this file relies on exactly
; that already-proven behavior, just across a file boundary instead of
; within one.
;
; Two-word (Lo/Hi) 32-bit values throughout, exactly like vm_run.pasm's own
; VmPriv_LeftLo/Hi convention -- Lo is bits 0-15, Hi is bits 16-31.
;
; ASL/LSR/ROL/ROR have no absolute-long addressing mode on real 65816 (see
; core/math.pasm's header comment and Core_Math_Mul's own low16-alias
; workaround) -- and this file's scratch cells all live in bank $7F, which
; has no low-RAM mirror the way bank $7E's $0000-$1FFF does, so the alias
; trick core/math.pasm uses isn't available here either. Every shift in this
; file is done via `lda.l cell` / `asl a` or `rol a` (Accumulator mode, which
; every 65816 opcode of this family supports) / `sta.l cell` instead --
; carry propagates between words through the C flag exactly the way a
; memory-operand rol chain would, just one register-mode step at a time.
;
; Integer overflow = two's-complement 32-bit wrap throughout (plan_vm.md
; §4's own decision). Shift counts normalized `count & 31` (low 5 bits of
; the right operand's low word -- bits 5-31 can never affect a mod-32
; result, so the high word and the top 11 bits of the low word are never
; even read). DIV by zero -> destination slot becomes EMPTY, not a fault
; (historical behavior, plan_vm.md §4). MOD by zero -> VMERR_DIV_ZERO,
; deliberately diverging from the historical (unsafe, unguarded) behavior --
; also plan_vm.md §4's decision, not an oversight.
;
; NEG on a non-INTEGER slot (this gate has no DECIMAL yet -- that's Gate 5,
; plan_vm.md §7) is left unchanged, not faulted -- the same "other types are
; unchanged" precedent opcode_manifest.csv states explicitly for INC/DEC,
; applied here by symmetry since the manifest's own NEG row only warns to
; verify the DECIMAL case (out of scope this gate) and says nothing about
; non-numeric types. This is a documented decision, not a guess: no historical
; behavior is being reproduced blind (plan_vm.md §4's own instruction).
;
; Global (not @-local) labels; jsr/rts (bank 0); explicit width directive
; before every width-dependent immediate reachable from a branch/jump
; target (poppy#386, still live -- tools/rom_audit/check_width_directives.py);
; no nop guards (that bug is fixed); every conditional branch here is local
; and short, but every fault exit still uses the near-branch-to-local-
; trampoline-then-brl shape (matching vm_run.pasm's own Vm_Op_Add), since a
; shared fault trampoline (Vm_BinaryInt_BadType) is called from many sites
; scattered through this file, some of which are not guaranteed to be
; within a `bcc`/`bcs`'s +-127 byte reach of it.
; ============================================================================

; --- Scratch WRAM. Free region grep-confirmed clear at Gate 2: VmPriv_*
; and vm_load.pasm's own VmLoad_Crc0-3/VmLoad_Cursor end at $7FE0C9;
; VmFrames_Wram (Gate 3, still unimplemented) doesn't start until $7FE100 --
; see vm_consts.pasm's own header note on that relocation. 28 bytes of
; named cells here plus an 8-byte copy buffer, both comfortably inside that
; $7FE0C9-$7FE0FF gap. ---
VmArith_Lo         = $7FE0C9   ; .dw -- Vm_Mul32 result, low word
VmArith_Hi         = $7FE0CB   ; .dw -- Vm_Mul32 result, high word
VmArith_QLo        = $7FE0CD   ; .dw -- Vm_DivMod32* quotient, low word
VmArith_QHi        = $7FE0CF   ; .dw -- quotient, high word
VmArith_RemLo      = $7FE0D1   ; .dw -- remainder, low word
VmArith_RemHi      = $7FE0D3   ; .dw -- remainder, high word
VmArith_DivLo      = $7FE0D5   ; .dw -- Vm_DivMod32Unsigned's divisor, low
VmArith_DivHi      = $7FE0D7   ; .dw -- divisor, high word
VmArith_LeftSign   = $7FE0D9   ; .dw -- Vm_DivMod32Signed: $8000 or $0000
VmArith_RightSign  = $7FE0DB   ; .dw
VmArith_NegLo      = $7FE0DD   ; .dw -- Vm_Negate32's in-place operand, low
VmArith_NegHi      = $7FE0DF   ; .dw -- high word
VmArith_CmpLT      = $7FE0E1   ; .dw -- Vm_CompareInt result: left < right
VmArith_CmpEQ      = $7FE0E3   ; .dw -- Vm_CompareInt result: left == right
VmArith_CopyBuf    = $7FE0E5   ; 8 B -- Vm_SlotCopy's staging buffer
VmArith_TruthyIdx  = $7FE0ED   ; .dw -- Vm_TruthySlot's saved slot index
                                 ; (Gate 4: WRAM scratch instead of a stack
                                 ; pha/pla, since Vm_TruthySlot's STR path
                                 ; needs the index back after a sep/rep width
                                 ; change and a pha/pla pair must never cross
                                 ; a width change with mismatched pull width)
; Ends $7FE0EF. VmFrames_Wram starts $7FE100 -- 17 bytes of slack kept.

; ============================================================================
; Vm_Negate32 -- two's-complement negate of VmArith_NegLo/Hi, in place.
; 0 - value with borrow chain; self-inverse on $80000000 by construction,
; which is exactly the "signed wrap" decision this gate stamps (negating
; INT_MIN wraps back to INT_MIN, never faults or clamps).
; ============================================================================
Vm_Negate32:
    php
    rep #$31
.a16
.i16
    sec
    lda #0
    sbc.l VmArith_NegLo
    sta.l VmArith_NegLo
    lda #0
    sbc.l VmArith_NegHi
    sta.l VmArith_NegHi
    plp
    rts

; ============================================================================
; Vm_Mul32 -- in: VmPriv_LeftLo/Hi (multiplicand), VmPriv_RightLo/Hi
; (multiplier). out: VmPriv_LeftLo/Hi = low 32 bits of the product.
;
; Two's-complement multiplication mod 2^32 is identical whether the operands
; are read as signed or unsigned -- only the *value* of the wrapped low 32
; bits matters here (plan_vm.md §4's wrap decision), so this is a plain
; unsigned 32x32->64 multiply with the high 32 bits of the product simply
; never computed: full 64-bit product bits 16-31 come from
; low(Left)*low(Right)'s own high word PLUS the low 16 bits of each
; cross term (low(Left)*high(Right) and high(Left)*low(Right)) --
; contributions from bit 32 and up of either cross term, and all of
; high(Left)*high(Right), only ever affect bits 32-63, which this gate never
; keeps. Core_Math_Mul (core/math.pasm) is the 16x16->32 unsigned primitive
; this composes three calls of.
; ============================================================================
Vm_Mul32:
    php
    rep #$31
.a16
.i16
    ; LDX/STX have no long-addressing form either (same restriction as
    ; ROL/ASL -- see this file's header note), so X is always loaded via
    ; `lda.l/tax` and saved via `txa/sta.l` here, never `ldx.l`/`stx.l`.
    lda.l VmPriv_RightLo
    tax
    lda.l VmPriv_LeftLo
    jsr Core_Math_Mul           ; a = low16(Left*Right), x = high16
    sta.l VmArith_Lo
    txa
    sta.l VmArith_Hi

    lda.l VmPriv_RightHi
    tax
    lda.l VmPriv_LeftLo
    jsr Core_Math_Mul           ; a = low16 of the cross term -- only half
                                 ; of it (the low word) ever lands inside
                                 ; the kept 32 bits; x (its high16) is
                                 ; discarded on purpose.
    clc
    adc.l VmArith_Hi
    sta.l VmArith_Hi

    lda.l VmPriv_RightLo
    tax
    lda.l VmPriv_LeftHi
    jsr Core_Math_Mul
    clc
    adc.l VmArith_Hi
    sta.l VmArith_Hi

    lda.l VmArith_Lo
    sta.l VmPriv_LeftLo
    lda.l VmArith_Hi
    sta.l VmPriv_LeftHi
    plp
    rts

; ============================================================================
; Vm_DivMod32Unsigned -- restoring binary long division, 32 bits, unsigned.
; in: VmArith_QLo/Hi (dividend, becomes the quotient), VmArith_DivLo/Hi
; (divisor, caller-guaranteed nonzero). out: VmArith_QLo/Hi = quotient,
; VmArith_RemLo/Hi = remainder.
;
; Classic shift-dividend-into-remainder algorithm: each of the 32 steps
; shifts the 64-bit (Remainder:Quotient) pair left by one bit, then
; subtracts the divisor from the remainder (and sets the just-shifted-in
; quotient bit to 1) if the remainder is now >= the divisor. The 64-bit
; shift is done as four separate `lda.l/asl-or-rol a/sta.l` steps rather
; than a memory-operand rol chain -- see this file's header note on why
; ROL has no long-addressing form and this file's scratch cells have no
; low-mirror alias to fall back on the way core/math.pasm's bank-$7E cells
; do.
; ============================================================================
Vm_DivMod32Unsigned:
    php
    rep #$31
.a16
.i16
    lda #0
    sta.l VmArith_RemLo
    sta.l VmArith_RemHi
    ldx #32

Vm_DivMod32Unsigned__loop:
.a16
.i16
    clc
    lda.l VmArith_QLo
    rol a
    sta.l VmArith_QLo
    lda.l VmArith_QHi
    rol a
    sta.l VmArith_QHi
    lda.l VmArith_RemLo
    rol a
    sta.l VmArith_RemLo
    lda.l VmArith_RemHi
    rol a
    sta.l VmArith_RemHi

    lda.l VmArith_RemHi
    cmp.l VmArith_DivHi
    bcc Vm_DivMod32Unsigned__skip     ; RemHi < DivHi (unsigned) -> Rem < Div
    bne Vm_DivMod32Unsigned__dosub    ; RemHi > DivHi -> Rem > Div
    lda.l VmArith_RemLo
    cmp.l VmArith_DivLo
    bcc Vm_DivMod32Unsigned__skip     ; hi equal, RemLo < DivLo -> Rem < Div

Vm_DivMod32Unsigned__dosub:
.a16
.i16
    sec
    lda.l VmArith_RemLo
    sbc.l VmArith_DivLo
    sta.l VmArith_RemLo
    lda.l VmArith_RemHi
    sbc.l VmArith_DivHi
    sta.l VmArith_RemHi
    lda.l VmArith_QLo
    ora #1
    sta.l VmArith_QLo

Vm_DivMod32Unsigned__skip:
.a16
.i16
    dex
    bne Vm_DivMod32Unsigned__loop

    plp
    rts

; ============================================================================
; Vm_DivMod32Signed -- in: VmPriv_LeftLo/Hi (dividend), VmPriv_RightLo/Hi
; (divisor, caller-guaranteed nonzero). out: VmArith_QLo/Hi = quotient
; truncated toward zero, VmArith_RemLo/Hi = remainder (sign follows the
; dividend, or zero -- the truncate-toward-zero/C-`%` convention;
; opcode_manifest.csv's DIV row states truncate-toward-zero explicitly,
; MOD's row doesn't specify beyond "integer-converted remainder", so this
; picks the convention consistent with DIV rather than inventing a second
; one). Clobbers VmPriv_LeftLo/Hi and VmPriv_RightLo/Hi (turned into
; absolute values in place as a working step).
;
; $80000000 negated is $80000000 (two's complement, see Vm_Negate32) --
; abs(INT_MIN)/abs(-1) both stay well-formed 32-bit magnitudes here with no
; special case, and the sign-XOR step below naturally reproduces the
; documented wrap behavior for INT_MIN/-1 without extra logic: both signs
; are set, XOR is 0, quotient is left unnegated, which is exactly
; $80000000 -- the correct wrapped answer, not a coincidence.
; ============================================================================
Vm_DivMod32Signed:
    php
    rep #$31
.a16
.i16
    lda.l VmPriv_LeftHi
    and #$8000
    sta.l VmArith_LeftSign
    lda.l VmPriv_RightHi
    and #$8000
    sta.l VmArith_RightSign

    lda.l VmArith_LeftSign
    beq Vm_DivMod32Signed__left_pos
    lda.l VmPriv_LeftLo
    sta.l VmArith_NegLo
    lda.l VmPriv_LeftHi
    sta.l VmArith_NegHi
    jsr Vm_Negate32
    lda.l VmArith_NegLo
    sta.l VmPriv_LeftLo
    lda.l VmArith_NegHi
    sta.l VmPriv_LeftHi

Vm_DivMod32Signed__left_pos:
.a16
.i16
    lda.l VmArith_RightSign
    beq Vm_DivMod32Signed__right_pos
    lda.l VmPriv_RightLo
    sta.l VmArith_NegLo
    lda.l VmPriv_RightHi
    sta.l VmArith_NegHi
    jsr Vm_Negate32
    lda.l VmArith_NegLo
    sta.l VmPriv_RightLo
    lda.l VmArith_NegHi
    sta.l VmPriv_RightHi

Vm_DivMod32Signed__right_pos:
.a16
.i16
    lda.l VmPriv_LeftLo
    sta.l VmArith_QLo
    lda.l VmPriv_LeftHi
    sta.l VmArith_QHi
    lda.l VmPriv_RightLo
    sta.l VmArith_DivLo
    lda.l VmPriv_RightHi
    sta.l VmArith_DivHi

    jsr Vm_DivMod32Unsigned

    lda.l VmArith_LeftSign
    eor.l VmArith_RightSign
    beq Vm_DivMod32Signed__q_done
    lda.l VmArith_QLo
    sta.l VmArith_NegLo
    lda.l VmArith_QHi
    sta.l VmArith_NegHi
    jsr Vm_Negate32
    lda.l VmArith_NegLo
    sta.l VmArith_QLo
    lda.l VmArith_NegHi
    sta.l VmArith_QHi

Vm_DivMod32Signed__q_done:
.a16
.i16
    lda.l VmArith_LeftSign
    beq Vm_DivMod32Signed__done
    lda.l VmArith_RemLo
    sta.l VmArith_NegLo
    lda.l VmArith_RemHi
    sta.l VmArith_NegHi
    jsr Vm_Negate32
    lda.l VmArith_NegLo
    sta.l VmArith_RemLo
    lda.l VmArith_NegHi
    sta.l VmArith_RemHi

Vm_DivMod32Signed__done:
.a16
.i16
    plp
    rts

; ============================================================================
; Vm_LoadBinaryInt -- in: VmPriv_B/VmPriv_C (already staged by Vm_Fetch).
; out: carry CLEAR and VmPriv_LeftLo/Hi + VmPriv_RightLo/Hi loaded, if both
; slots are VT_INTEGER; carry SET (operands not touched further) otherwise.
; Never jumps to Vm_Fault itself -- unlike Vm_Fetch, this is `jsr`'d from
; inside a dispatch-reached handler (which itself was reached by `jmp`, not
; `jsr` -- see vm_run.pasm's own header note on why handlers can `jmp
; Vm_Fault` directly), so a `jsr` callee jumping to Vm_Fault from in here
; would abandon ITS OWN jsr return address on the stack permanently,
; corrupting the very next `rts` anywhere in the interpreter. Returning a
; flag and letting the (jmp-reached, stack-clean) caller do the actual
; `jmp Vm_Fault` keeps every stack frame this file ever creates strictly
; balanced.
; ============================================================================
Vm_LoadBinaryInt:
    php
    rep #$31
.a16
.i16
    lda.l VmPriv_B
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    beq Vm_LoadBinaryInt__left_ok
    plp
    sec
    rts

Vm_LoadBinaryInt__left_ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_LeftLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_LeftHi

    lda.l VmPriv_C
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    beq Vm_LoadBinaryInt__right_ok
    plp
    sec
    rts

Vm_LoadBinaryInt__right_ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_RightLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_RightHi
    plp
    clc
    rts

; Shared fault trampoline for every Vm_LoadBinaryInt caller in this file --
; `bcc <local_ok_label>` / `brl Vm_BinaryInt_BadType` at each call site,
; matching vm_run.pasm's Vm_Op_Add invert-and-brl shape, since a `bcs`
; straight here from a distant handler is not guaranteed to be in a
; conditional branch's +-127 byte range.
Vm_BinaryInt_BadType:
    rep #$31
.a16
.i16
    lda #VMERR_BAD_TYPE
    jmp Vm_Fault

; ============================================================================
; Vm_StoreIntResult -- in: VmPriv_A (dest slot), VmPriv_LeftLo/Hi (the
; result). out: slot VmPriv_A set to VT_INTEGER with that value. Never
; faults -- safe to `jsr` from anywhere, including after a `jmp`-reached
; handler that itself came in via the normal dispatch (matches
; vm_run.pasm's ADD/EQ store boilerplate, factored out once here instead of
; repeated per Gate-2 opcode).
; ============================================================================
Vm_StoreIntResult:
    php
    rep #$31
.a16
.i16
    lda.l VmPriv_A
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda #BOR_VT_INTEGER
    sta.l VmSlots_Wram+0,x
    lda #0
    sta.l VmSlots_Wram+1,x
    rep #$31
.a16
.i16
    lda #0
    sta.l VmSlots_Wram+2,x
    lda.l VmPriv_LeftLo
    sta.l VmSlots_Wram+4,x
    lda.l VmPriv_LeftHi
    sta.l VmSlots_Wram+6,x
    plp
    rts

; ============================================================================
; Vm_CompareInt -- in: VmPriv_LeftLo/Hi, VmPriv_RightLo/Hi (already loaded
; by Vm_LoadBinaryInt -- both are VT_INTEGER by the time this runs). out:
; VmArith_CmpLT and VmArith_CmpEQ, each 0 or 1.
;
; Signed 32-bit compare via the standard sign-bit-flip trick: XOR-ing bit 31
; of both operands turns a signed compare into a plain unsigned one (it
; maps the signed ordering ... -2,-1,0,1,2 ... onto the unsigned ordering
; 0,1,...,0x7FFFFFFF,0x80000000,...,0xFFFFFFFF -- exactly the transform two's
; complement already almost provides, off by the sign bit). Avoids the
; overflow bookkeeping a subtract-based signed compare would otherwise need
; for cases like $7FFFFFFF vs $80000000.
; ============================================================================
Vm_CompareInt:
    php
    rep #$31
.a16
.i16
    lda.l VmPriv_RightHi
    eor #$8000
    sta.l VmArith_DivHi           ; scratch reuse: flipped right-hi (this
                                   ; routine never runs interleaved with
                                   ; Vm_DivMod32Unsigned, safe to borrow)
    lda.l VmPriv_LeftHi
    eor #$8000
    cmp.l VmArith_DivHi
    bcc Vm_CompareInt__lt
    bne Vm_CompareInt__gt
    lda.l VmPriv_LeftLo
    cmp.l VmPriv_RightLo
    bcc Vm_CompareInt__lt
    bne Vm_CompareInt__gt

    lda #1
    sta.l VmArith_CmpEQ
    lda #0
    sta.l VmArith_CmpLT
    plp
    rts

Vm_CompareInt__lt:
.a16
.i16
    lda #1
    sta.l VmArith_CmpLT
    lda #0
    sta.l VmArith_CmpEQ
    plp
    rts

Vm_CompareInt__gt:
.a16
.i16
    lda #0
    sta.l VmArith_CmpLT
    sta.l VmArith_CmpEQ
    plp
    rts

; ============================================================================
; Vm_TruthySlot -- in: A (16-bit) = slot index. out: A (16-bit) = 0 or 1.
; VM truthiness (Branch_FALSE/TRUE's own precedent, reused rather than
; re-derived): VT_INTEGER and nonzero is true; every other type, including
; EMPTY, is false. Used by OR/AND, which per opcode_manifest.csv evaluate
; truthiness directly rather than requiring VT_INTEGER-or-fault the way
; ADD/MUL/etc. do.
; ============================================================================
; Gate 4 (plan_vm.md §6) adds STR: truthy iff aux (cached length) is nonzero
; (README §6's truthiness table). Still INTEGER-nonzero-or-STR-nonempty-or-
; falsy -- PTR truthiness is out of scope until a real typed-handle native
; needs it, same "documented decision, not a guess" precedent this file's
; header already uses for NEG's non-INTEGER case.
Vm_TruthySlot:
    php
    rep #$31
.a16
.i16
    sta.l VmArith_TruthyIdx      ; keep the slot index -- Vm_Str_TruthySlot
                                   ; needs it again on the STR path
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    beq Vm_TruthySlot__integer
    cmp #BOR_VT_STR
    beq Vm_TruthySlot__str
    rep #$31
.a16
.i16
    lda #0
    plp
    rts

Vm_TruthySlot__integer:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    ora.l VmSlots_Wram+6,x
    beq Vm_TruthySlot__falsy
    lda #1
    plp
    rts

Vm_TruthySlot__str:
.a8
    rep #$31
.a16
.i16
    lda.l VmArith_TruthyIdx
    jsr Vm_Str_TruthySlot
    plp
    rts

Vm_TruthySlot__falsy:
.a16
.i16
    lda #0
    plp
    rts

; ============================================================================
; Vm_SlotCopy -- in: VmPriv_A (dest slot), VmPriv_B (source slot). out: the
; full 8-byte slot record copied B -> A, byte for byte, any type. Shared by
; LOAD (3) and SAVE (4) -- opcode_manifest.csv gives both the same (a=dest,
; b=source) operand shape; the "variable slot" vs. "expression slot"
; distinction in their two descriptions is purely a host-linker-side
; naming convention (plan_vm.md §0.4: variables and expression temporaries
; share one flat 1024-slot array at runtime), not a runtime difference.
;
; Gate 4 (plan_vm.md §6): retains B's value before releasing A's OLD value,
; not the other way around -- if A and B name the same slot (a plain
; self-copy), retain-then-release nets to zero on the SAME object instead of
; freeing it out from under itself before the copy even happens. Both
; Vm_Str_RetainIfDynamic/ReleaseIfDynamic are no-ops on non-STR and ROM-
; string slots, so this costs nothing on the integer-only path Gate 2 already
; exercises.
; ============================================================================
Vm_SlotCopy:
    php
    rep #$31
.a16
.i16
    lda.l VmPriv_B
    jsr Vm_Str_RetainIfDynamic
    lda.l VmPriv_A
    jsr Vm_Str_ReleaseIfDynamic

    lda.l VmPriv_B
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    sta.l VmArith_CopyBuf+0
    lda.l VmSlots_Wram+1,x
    sta.l VmArith_CopyBuf+1
    lda.l VmSlots_Wram+2,x
    sta.l VmArith_CopyBuf+2
    lda.l VmSlots_Wram+3,x
    sta.l VmArith_CopyBuf+3
    lda.l VmSlots_Wram+4,x
    sta.l VmArith_CopyBuf+4
    lda.l VmSlots_Wram+5,x
    sta.l VmArith_CopyBuf+5
    lda.l VmSlots_Wram+6,x
    sta.l VmArith_CopyBuf+6
    lda.l VmSlots_Wram+7,x
    sta.l VmArith_CopyBuf+7

    rep #$31
.a16
.i16
    lda.l VmPriv_A
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmArith_CopyBuf+0
    sta.l VmSlots_Wram+0,x
    lda.l VmArith_CopyBuf+1
    sta.l VmSlots_Wram+1,x
    lda.l VmArith_CopyBuf+2
    sta.l VmSlots_Wram+2,x
    lda.l VmArith_CopyBuf+3
    sta.l VmSlots_Wram+3,x
    lda.l VmArith_CopyBuf+4
    sta.l VmSlots_Wram+4,x
    lda.l VmArith_CopyBuf+5
    sta.l VmSlots_Wram+5,x
    lda.l VmArith_CopyBuf+6
    sta.l VmSlots_Wram+6,x
    lda.l VmArith_CopyBuf+7
    sta.l VmSlots_Wram+7,x

    plp
    rts

; ============================================================================
; Opcode handlers -- Gate 2 (plan_vm.md §4).
; ============================================================================

Vm_Op_Load:
    jsr Vm_SlotCopy
    jmp Vm_Next

Vm_Op_Save:
    jsr Vm_SlotCopy
    jmp Vm_Next

; INC/DEC -- INTEGER only at this gate (DECIMAL is Gate 5); every other
; type, per opcode_manifest.csv, is left unchanged. a = operand slot,
; doubles as the destination (in place).
Vm_Op_Inc:
    rep #$31
.a16
.i16
    lda.l VmPriv_A
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    bne Vm_Op_Inc__skip
    rep #$31
.a16
.i16
    clc
    lda.l VmSlots_Wram+4,x
    adc #1
    sta.l VmSlots_Wram+4,x
    lda.l VmSlots_Wram+6,x
    adc #0
    sta.l VmSlots_Wram+6,x
    jmp Vm_Next

Vm_Op_Inc__skip:
.a8
    rep #$31
.a16
.i16
    jmp Vm_Next

Vm_Op_Dec:
    rep #$31
.a16
.i16
    lda.l VmPriv_A
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    bne Vm_Op_Dec__skip
    rep #$31
.a16
.i16
    sec
    lda.l VmSlots_Wram+4,x
    sbc #1
    sta.l VmSlots_Wram+4,x
    lda.l VmSlots_Wram+6,x
    sbc #0
    sta.l VmSlots_Wram+6,x
    jmp Vm_Next

Vm_Op_Dec__skip:
.a8
    rep #$31
.a16
.i16
    jmp Vm_Next

; POS -- historical implementation is intentionally inert (opcode_manifest.
; csv); a true no-op, not even a type check.
Vm_Op_Pos:
    jmp Vm_Next

; NEG -- INTEGER only at this gate; non-INTEGER unchanged (see this file's
; header note on why, and the DECIMAL caveat this deliberately does not
; resolve).
Vm_Op_Neg:
    rep #$31
.a16
.i16
    lda.l VmPriv_A
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    bne Vm_Op_Neg__skip
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmArith_NegLo
    lda.l VmSlots_Wram+6,x
    sta.l VmArith_NegHi
    jsr Vm_Negate32
    lda.l VmArith_NegLo
    sta.l VmSlots_Wram+4,x
    lda.l VmArith_NegHi
    sta.l VmSlots_Wram+6,x
    jmp Vm_Next

Vm_Op_Neg__skip:
.a8
    rep #$31
.a16
.i16
    jmp Vm_Next

; NOT -- always replaces the operand slot with VT_INTEGER 0 or 1 (VM
; truthiness), regardless of the operand's original type.
Vm_Op_Not:
    rep #$31
.a16
.i16
    lda.l VmPriv_A
    jsr Vm_TruthySlot
    eor #1
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_Mul:
    jsr Vm_LoadBinaryInt
    bcc Vm_Op_Mul__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Mul__ok:
.a8
    jsr Vm_Mul32
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_Sub:
    jsr Vm_LoadBinaryInt
    bcc Vm_Op_Sub__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Sub__ok:
.a8
    rep #$31
.a16
.i16
    sec
    lda.l VmPriv_LeftLo
    sbc.l VmPriv_RightLo
    sta.l VmPriv_LeftLo
    lda.l VmPriv_LeftHi
    sbc.l VmPriv_RightHi
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

; DIV -- divisor zero -> destination becomes EMPTY (historical behavior,
; not a fault). Otherwise signed 32-bit division truncated toward zero.
Vm_Op_Div:
    jsr Vm_LoadBinaryInt
    bcc Vm_Op_Div__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Div__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmPriv_RightLo
    ora.l VmPriv_RightHi
    bne Vm_Op_Div__nonzero

    lda.l VmPriv_A
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda #BOR_VT_EMPTY
    sta.l VmSlots_Wram+0,x
    lda #0
    sta.l VmSlots_Wram+1,x
    rep #$31
.a16
.i16
    lda #0
    sta.l VmSlots_Wram+2,x
    sta.l VmSlots_Wram+4,x
    sta.l VmSlots_Wram+6,x
    jmp Vm_Next

Vm_Op_Div__nonzero:
.a16
.i16
    jsr Vm_DivMod32Signed
    lda.l VmArith_QLo
    sta.l VmPriv_LeftLo
    lda.l VmArith_QHi
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

; MOD -- divisor zero -> VMERR_DIV_ZERO fault (plan_vm.md §4's deliberate
; divergence from the historical, unguarded behavior). Otherwise the
; remainder of the same truncated-toward-zero division DIV performs (sign
; follows the dividend).
Vm_Op_Mod:
    jsr Vm_LoadBinaryInt
    bcc Vm_Op_Mod__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Mod__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmPriv_RightLo
    ora.l VmPriv_RightHi
    bne Vm_Op_Mod__nonzero
    lda #VMERR_DIV_ZERO
    jmp Vm_Fault

Vm_Op_Mod__nonzero:
.a16
.i16
    jsr Vm_DivMod32Signed
    lda.l VmArith_RemLo
    sta.l VmPriv_LeftLo
    lda.l VmArith_RemHi
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

; SHL/SHR -- count = right operand's low word & 31 (bits 5-31 of a 32-bit
; shift count can never change a mod-32 result, so the high word and the
; low word's own top 11 bits are simply never read -- this is what
; "normalized count & 31" means, applied to the full 32-bit right operand).
; Logical (unsigned) shift, 32-bit wrap, one bit at a time via the
; Accumulator-mode shift chain this file's header note explains.
Vm_Op_Shl:
    jsr Vm_LoadBinaryInt
    bcc Vm_Op_Shl__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Shl__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmPriv_RightLo
    and #$001F
    tax
    beq Vm_Op_Shl__done

Vm_Op_Shl__loop:
.a16
.i16
    lda.l VmPriv_LeftLo
    asl a
    sta.l VmPriv_LeftLo
    lda.l VmPriv_LeftHi
    rol a
    sta.l VmPriv_LeftHi
    dex
    bne Vm_Op_Shl__loop

Vm_Op_Shl__done:
.a16
.i16
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_Shr:
    jsr Vm_LoadBinaryInt
    bcc Vm_Op_Shr__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Shr__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmPriv_RightLo
    and #$001F
    tax
    beq Vm_Op_Shr__done

Vm_Op_Shr__loop:
.a16
.i16
    lda.l VmPriv_LeftHi
    lsr a
    sta.l VmPriv_LeftHi
    lda.l VmPriv_LeftLo
    ror a
    sta.l VmPriv_LeftLo
    dex
    bne Vm_Op_Shr__loop

Vm_Op_Shr__done:
.a16
.i16
    jsr Vm_StoreIntResult
    jmp Vm_Next

; GE/LE/LT/GT/NE -- INTEGER pair or STR pair (Gate 4, plan_vm.md §6, README
; §6 "Comparisons": string pairs compare lexicographically, exactly like
; EQ/NE); any other pairing (including a mismatched INTEGER/STR pair) faults
; VMERR_BAD_TYPE. Vm_LoadAndCompare (core/vm/vm_string.pasm) tries the
; INTEGER pairing first, falls back to STR, and leaves the 0/1 result in
; VmArith_CmpLT/CmpEQ either way -- the store logic below is unchanged from
; Gate 2's INTEGER-only version, since it only ever reads those two cells.
Vm_Op_Ge:
    jsr Vm_LoadAndCompare
    bcc Vm_Op_Ge__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Ge__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmArith_CmpLT
    eor #1
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_Le:
    jsr Vm_LoadAndCompare
    bcc Vm_Op_Le__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Le__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmArith_CmpLT
    ora.l VmArith_CmpEQ
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_Lt:
    jsr Vm_LoadAndCompare
    bcc Vm_Op_Lt__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Lt__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmArith_CmpLT
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_Gt:
    jsr Vm_LoadAndCompare
    bcc Vm_Op_Gt__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Gt__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmArith_CmpLT
    ora.l VmArith_CmpEQ
    eor #1
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_Ne:
    jsr Vm_LoadAndCompare
    bcc Vm_Op_Ne__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Ne__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmArith_CmpEQ
    eor #1
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

; OR/AND -- truthiness of both operands, no type fault (opcode_manifest.csv:
; "truth(left) OR/AND truth(right)" -- Branch_FALSE/TRUE's non-INTEGER-is-
; falsy precedent, not EQ's INTEGER-only-or-fault one).
Vm_Op_Or:
    rep #$31
.a16
.i16
    lda.l VmPriv_B
    jsr Vm_TruthySlot
    sta.l VmArith_CmpLT           ; scratch reuse: truth(left)
    lda.l VmPriv_C
    jsr Vm_TruthySlot
    ora.l VmArith_CmpLT
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_And:
    rep #$31
.a16
.i16
    lda.l VmPriv_B
    jsr Vm_TruthySlot
    sta.l VmArith_CmpLT
    lda.l VmPriv_C
    jsr Vm_TruthySlot
    and.l VmArith_CmpLT
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

; BIT_OR/XOR/BIT_AND -- INTEGER-only-or-fault (same rule as ADD/SUB/MUL:
; only VT_INTEGER exists to "integer-convert" at this gate, so a type
; mismatch faults rather than silently coercing).
Vm_Op_BitOr:
    jsr Vm_LoadBinaryInt
    bcc Vm_Op_BitOr__ok
    brl Vm_BinaryInt_BadType

Vm_Op_BitOr__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmPriv_LeftLo
    ora.l VmPriv_RightLo
    sta.l VmPriv_LeftLo
    lda.l VmPriv_LeftHi
    ora.l VmPriv_RightHi
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_Xor:
    jsr Vm_LoadBinaryInt
    bcc Vm_Op_Xor__ok
    brl Vm_BinaryInt_BadType

Vm_Op_Xor__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmPriv_LeftLo
    eor.l VmPriv_RightLo
    sta.l VmPriv_LeftLo
    lda.l VmPriv_LeftHi
    eor.l VmPriv_RightHi
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_BitAnd:
    jsr Vm_LoadBinaryInt
    bcc Vm_Op_BitAnd__ok
    brl Vm_BinaryInt_BadType

Vm_Op_BitAnd__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmPriv_LeftLo
    and.l VmPriv_RightLo
    sta.l VmPriv_LeftLo
    lda.l VmPriv_LeftHi
    and.l VmPriv_RightHi
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next
