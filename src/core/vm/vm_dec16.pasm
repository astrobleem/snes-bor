; ============================================================================
; core/vm/vm_dec16.pasm -- Gate 5 (plan_vm.md §7): Q16.16 decimal glue.
;
; Bank-0 only (included inside main.pasm's $9000-$AC00 VM window, right
; after vm_string.pasm -- same forward-reference convention every other
; vm/*.pasm file already relies on). The actual Q16.16 multiply/divide/
; format PRIMITIVES live in bank 1 (appended after the TAD audio blob at
; the very end of main.pasm, see that section's own header) -- this file
; only holds the type-dispatch/promotion glue that every arithmetic/
; comparison opcode handler routes through, plus the thin jsl stubs that
; reach into bank 1. Kept in bank 0 because dispatch itself (vm_run.pasm's
; Vm_Run__loop) reaches every Vm_Op_* entry point via a same-bank `jmp`.
;
; Measured before writing this file: ~560 bytes free in the $9000-$AC00
; VM window. An earlier version of this file also included
; Vm_Dec_ConcatCoerce (ADD's STR+numeric coercion path, formatting a
; numeric operand and concatenating it via vm_string.pasm's
; Vm_Str_ConcatOp__FromScratch) -- that alone overflowed the window by
; ~166 bytes (`.org section at $AC00 overlaps previously emitted bytes`),
; so it was cut. Vm_Dec_FormatSlot (vm_dec16_heavy.pasm, bank 1) still
; implements and formats Gate 5's cartridge-defined decimal->string rule
; (vm_consts.pasm's own header has the exact format), but nothing calls it
; yet -- ADD's STR+INTEGER/STR+DECIMAL pairing still faults VMERR_BAD_TYPE,
; same as Gate 4. Wiring it back in is Gate 6's to do, once the real
; script content (and a clearer picture of the remaining bank-0 budget
; after Gate 6's own additions) exists -- a documented, budget-forced
; scope decision, not an oversight. Run
; tools/rom_audit/audit_all.py's region-occupancy check after any change
; here to confirm the window still fits.
;
; Two calling conventions coexist here on purpose:
;   - Vm_LoadBinaryNumeric / Vm_LoadBinaryIntConvert / Vm_StoreNumericResult
;     are `jsr`'d from a `jmp`-dispatched Vm_Op_* handler, exactly like
;     vm_arith32.pasm's Vm_LoadBinaryInt -- never jump to Vm_Fault
;     themselves, return carry SET instead and let the caller `jmp
;     Vm_Fault` (that file's own header explains why: a jsr callee must
;     never abandon its own return address on the stack).
;   - The bank-1 primitives are reached via `jsl`/`rtl`, a DIFFERENT
;     calling convention (3-byte return address, not 2) -- callers here
;     always `jsl`, never `jsr`, to those labels.
; ============================================================================

; ============================================================================
; Vm_LoadBinaryNumeric -- in: VmPriv_B/VmPriv_C (already staged by
; Vm_Fetch). out: carry CLEAR and VmPriv_LeftLo/Hi + VmPriv_RightLo/Hi
; loaded, if both slots are VT_INTEGER or VT_DECIMAL (any pairing); carry
; SET otherwise. VmDec_ResultIsDec is set 0 (both operands were INTEGER,
; values passed through unchanged -- byte-identical to Gate 2's
; Vm_LoadBinaryInt) or 1 (at least one operand was DECIMAL -- the other,
; if INTEGER, is promoted to Q16.16 in place: newHi=oldLo, newLo=0, per
; this gate's documented promotion rule in vm_consts.pasm).
;
; Shares vm_arith32.pasm's Vm_BinaryInt_BadType fault trampoline -- every
; caller here uses the identical `bcc <ok>` / `brl Vm_BinaryInt_BadType`
; shape its own callers already use.
; ============================================================================
Vm_LoadBinaryNumeric:
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
    beq Vm_LoadBinaryNumeric__left_int
    cmp #BOR_VT_DECIMAL
    beq Vm_LoadBinaryNumeric__left_dec
    plp
    sec
    rts

Vm_LoadBinaryNumeric__left_int:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_LeftLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_LeftHi
    sep #$20
.a8
    lda #0
    sta.l VmDec_ResultIsDec
    bra Vm_LoadBinaryNumeric__right

Vm_LoadBinaryNumeric__left_dec:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_LeftLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_LeftHi
    sep #$20
.a8
    lda #1
    sta.l VmDec_ResultIsDec

Vm_LoadBinaryNumeric__right:
.a8
    rep #$31
.a16
.i16
    lda.l VmPriv_C
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    beq Vm_LoadBinaryNumeric__right_int
    cmp #BOR_VT_DECIMAL
    beq Vm_LoadBinaryNumeric__right_dec
    plp
    sec
    rts

Vm_LoadBinaryNumeric__right_int:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_RightLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_RightHi
    sep #$20
.a8
    lda.l VmDec_ResultIsDec
    beq Vm_LoadBinaryNumeric__done   ; both plain INTEGER -- nothing to promote
    rep #$31
.a16
.i16
    lda.l VmPriv_RightLo             ; right is INTEGER, left was DECIMAL:
    sta.l VmPriv_RightHi             ; promote right (old lo -> new hi)
    lda #0
    sta.l VmPriv_RightLo
    bra Vm_LoadBinaryNumeric__done

Vm_LoadBinaryNumeric__right_dec:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_RightLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_RightHi
    sep #$20
.a8
    lda.l VmDec_ResultIsDec
    bne Vm_LoadBinaryNumeric__done   ; both DECIMAL -- nothing to promote
    lda #1
    sta.l VmDec_ResultIsDec
    rep #$31
.a16
.i16
    lda.l VmPriv_LeftLo               ; right is DECIMAL, left was INTEGER:
    sta.l VmPriv_LeftHi               ; promote left
    lda #0
    sta.l VmPriv_LeftLo

Vm_LoadBinaryNumeric__done:
.a16
.i16
    plp
    clc
    rts

; ============================================================================
; Vm_LoadBinaryIntConvert -- like vm_arith32.pasm's Vm_LoadBinaryInt, but
; used by MOD/SHL/SHR/BIT_OR/XOR/BIT_AND (opcode_manifest.csv: "Integer-
; convert operands" -- these never produce a DECIMAL result, unlike
; ADD/SUB/MUL/DIV). VT_INTEGER passes through unchanged; VT_DECIMAL is
; truncated toward zero to its 16-bit integer part, sign-extended to a
; full 32-bit INTEGER (vm_consts.pasm's own header has the exact rule and
; worked examples). Any other type -> carry SET, same fault-trampoline
; contract as every Vm_Load* helper in this VM.
; ============================================================================
Vm_LoadBinaryIntConvert:
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
    beq Vm_LoadBinaryIntConvert__left_int
    cmp #BOR_VT_DECIMAL
    beq Vm_LoadBinaryIntConvert__left_dec
    plp
    sec
    rts

Vm_LoadBinaryIntConvert__left_int:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_LeftLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_LeftHi
    bra Vm_LoadBinaryIntConvert__right

Vm_LoadBinaryIntConvert__left_dec:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_LeftLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_LeftHi
    lda.l VmPriv_LeftHi
    bpl Vm_LoadBinaryIntConvert__left_trunc_skip
    lda.l VmPriv_LeftLo
    beq Vm_LoadBinaryIntConvert__left_trunc_skip
    lda.l VmPriv_LeftHi
    clc
    adc #1
    sta.l VmPriv_LeftHi

Vm_LoadBinaryIntConvert__left_trunc_skip:
.a16
.i16
    lda.l VmPriv_LeftHi
    sta.l VmPriv_LeftLo
    bpl Vm_LoadBinaryIntConvert__left_ext_pos
    lda #$FFFF
    sta.l VmPriv_LeftHi
    bra Vm_LoadBinaryIntConvert__right

Vm_LoadBinaryIntConvert__left_ext_pos:
.a16
.i16
    lda #0
    sta.l VmPriv_LeftHi

Vm_LoadBinaryIntConvert__right:
.a16
.i16
    lda.l VmPriv_C
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    beq Vm_LoadBinaryIntConvert__right_int
    cmp #BOR_VT_DECIMAL
    beq Vm_LoadBinaryIntConvert__right_dec
    plp
    sec
    rts

Vm_LoadBinaryIntConvert__right_int:
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

Vm_LoadBinaryIntConvert__right_dec:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_RightLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_RightHi
    lda.l VmPriv_RightHi
    bpl Vm_LoadBinaryIntConvert__right_trunc_skip
    lda.l VmPriv_RightLo
    beq Vm_LoadBinaryIntConvert__right_trunc_skip
    lda.l VmPriv_RightHi
    clc
    adc #1
    sta.l VmPriv_RightHi

Vm_LoadBinaryIntConvert__right_trunc_skip:
.a16
.i16
    lda.l VmPriv_RightHi
    sta.l VmPriv_RightLo
    bpl Vm_LoadBinaryIntConvert__right_ext_pos
    lda #$FFFF
    sta.l VmPriv_RightHi
    plp
    clc
    rts

Vm_LoadBinaryIntConvert__right_ext_pos:
.a16
.i16
    lda #0
    sta.l VmPriv_RightHi
    plp
    clc
    rts

; ============================================================================
; Vm_StoreNumericResult -- like vm_arith32.pasm's Vm_StoreIntResult, but
; tags the destination slot VT_INTEGER or VT_DECIMAL based on
; VmDec_ResultIsDec (set by the caller's own Vm_LoadBinaryNumeric call).
; Used by ADD/SUB/MUL/DIV only -- MOD/SHL/SHR/BIT_OR/XOR/BIT_AND still use
; the original Vm_StoreIntResult unchanged (they always produce INTEGER,
; see Vm_LoadBinaryIntConvert's own header). Never faults -- safe to `jsr`
; from anywhere.
; ============================================================================
Vm_StoreNumericResult:
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
    lda.l VmDec_ResultIsDec        ; .db cell -- MUST read 8-bit (Gate 5 bug:
                                     ; a 16-bit read here once picked up the
                                     ; high byte's stale WRAM garbage, since
                                     ; every write to this cell is 8-bit)
    bne Vm_StoreNumericResult__dec
    lda #BOR_VT_INTEGER
    bra Vm_StoreNumericResult__tag

Vm_StoreNumericResult__dec:
.a8
    lda #BOR_VT_DECIMAL

Vm_StoreNumericResult__tag:
.a8
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

