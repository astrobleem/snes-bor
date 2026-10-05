; ============================================================================
; core/vm/vm_string.pasm -- Gate 4 (plan_vm.md §6): interned/dynamic strings,
; refcounting, and the shared int-or-string comparison path GE/LE/LT/GT/EQ/NE
; all use (README §6 "Comparisons": string pairs compare lexicographically by
; bytes, same as numeric pairs compare numerically -- one shared class, not a
; special case bolted onto EQ/NE alone).
;
; Included in main.pasm directly after vm_call.pasm (last in the vm/ block).
; Forward-references VmArith_CmpLT/CmpEQ, Vm_LoadBinaryInt, Vm_CompareInt
; (vm_arith32.pasm) and is itself forward-referenced BY vm_run.pasm/
; vm_arith32.pasm/vm_slots.pasm (earlier files calling into Vm_Str_* symbols
; defined below) -- both directions already proven safe project-wide
; (vm_arith32.pasm's own header note on cross-file forward references).
;
; --- String representation (vm_consts.pasm has the authoritative layout
; comment; summarized here for this file's own routines) ---
; A BOR_VT_STR slot's value field (VmSlots_Wram+4 low word, +6 high word) is
; a handle, never a raw pointer:
;   high word bit15 SET   -> low word is a VmStrPool_Wram object index
;                             (a dynamic, refcounted string)
;   high word bit15 CLEAR -> low word is an index into the module's own
;                             interned-string table (FORMAT.md "Interned
;                             strings"), a ROM string -- never refcounted,
;                             Vm_Str_RetainIfDynamic/ReleaseIfDynamic both
;                             no-op on it
; aux (+2) is always the string's byte length, kept in sync by every routine
; here that writes a STR slot -- CONSTSTR's own prelinked slot image is
; exporter-provided and trusted the same way every other module field is.
;
; --- Scratch WRAM. Placed directly after vm_call.pasm's own scratch block,
; which itself ends at $7FF40E (see that file's header note on why it sits
; past VmStrPool_Wram's $7FE400-$7FF3FF reservation rather than the tiny
; $7FE0ED-$7FE100 gap). Grep-confirmed clear: nothing in src/ references
; $7FF40E+ before this file. ---
VmStr_StringsOff  = $7FF40E   ; .dw -- cached strings_offset (header +$28)
VmStr_ScratchA    = $7FF410   ; 62 B -- left/first operand's raw bytes
VmStr_LenA        = $7FF44E   ; .dw
VmStr_ScratchB    = $7FF450   ; 62 B -- right/second operand's raw bytes
VmStr_LenB        = $7FF48E   ; .dw
VmStr_ScanIdx     = $7FF490   ; .dw -- Vm_Str_Alloc's pool scan index
VmStr_NewIdx      = $7FF492   ; .dw -- Vm_Str_Alloc's result (pool object index)
VmStr_CopyI       = $7FF494   ; .dw -- generic byte-copy/compare loop index
VmStr_Tmp0        = $7FF496   ; .dw -- Vm_Str_Resolve/ConcatOp scratch
VmStr_Tmp1        = $7FF498   ; .dw
VmStr_Tmp2        = $7FF49A   ; .dw
VmStr_SrcOff      = $7FF49C   ; .dw -- Vm_Str_Resolve's resolved source offset
VmStr_CopyLen     = $7FF49E   ; .dw -- Vm_Str_Resolve's resolved length
VmStr_SrcIsPool   = $7FF4A0   ; .db -- Vm_Str_Resolve: 1 = VmStrPool_Wram, 0 = ROM
; Ends $7FF4A1.

; ============================================================================
; Vm_Str_Alloc -- scans the 64-object pool for a free slot (refcount==0),
; claims it (refcount=1), and returns its index in VmStr_NewIdx. Carry CLEAR
; on success; carry SET (VmStr_NewIdx untouched) if the pool is exhausted --
; the caller faults VMERR_STRING_POOL, matching every other Vm_Load*/Resolve
; routine's "return a flag, let the jmp-reached caller jmp Vm_Fault" contract
; (vm_arith32.pasm's own header note on why: a jsr callee must never jmp
; Vm_Fault itself, or it abandons its own return address permanently).
; ============================================================================
Vm_Str_Alloc:
    php
    rep #$31
.a16
.i16
    lda #0
    sta.l VmStr_ScanIdx

Vm_Str_Alloc__loop:
.a16
.i16
    lda.l VmStr_ScanIdx
    cmp #VMSTRPOOL_OBJ_COUNT
    bcc Vm_Str_Alloc__check
    plp
    sec
    rts

Vm_Str_Alloc__check:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a                       ; index * VMSTRPOOL_OBJ_SIZE (64)
    tax
    sep #$20
.a8
    lda.l VmStrPool_Wram+0,x    ; refcount
    bne Vm_Str_Alloc__next
    lda #1
    sta.l VmStrPool_Wram+0,x    ; claim it
    rep #$31
.a16
.i16
    lda.l VmStr_ScanIdx
    sta.l VmStr_NewIdx
    plp
    clc
    rts

Vm_Str_Alloc__next:
.a8
    rep #$31
.a16
.i16
    lda.l VmStr_ScanIdx
    inc a
    sta.l VmStr_ScanIdx
    bra Vm_Str_Alloc__loop

; ============================================================================
; Vm_Str_RetainIfDynamic / Vm_Str_ReleaseIfDynamic -- in: A (.a16) = slot
; index. No-op on any non-STR slot and on ROM strings (never refcounted);
; on a dynamic string, increments/decrements the pool object's refcount.
; Retain saturates at 255 rather than wrapping to 0 (which would read as
; "free"); release refuses to decrement an already-0 refcount for the same
; reason -- both defensive, neither should be reachable through normal use
; (every dynamic handle in a slot was put there by Vm_Str_ConcatOp, which
; only ever hands out objects Vm_Str_Alloc just set to 1).
; ============================================================================
Vm_Str_RetainIfDynamic:
    php
    rep #$31
.a16
.i16
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_STR
    beq Vm_Str_RetainIfDynamic__isstr
    plp
    rts

Vm_Str_RetainIfDynamic__isstr:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+6,x
    and #$8000
    beq Vm_Str_RetainIfDynamic__done
    lda.l VmSlots_Wram+4,x
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmStrPool_Wram+0,x
    cmp #$FF
    beq Vm_Str_RetainIfDynamic__done8
    inc a
    sta.l VmStrPool_Wram+0,x

Vm_Str_RetainIfDynamic__done8:
.a8
    rep #$31
.a16
.i16

Vm_Str_RetainIfDynamic__done:
.a16
.i16
    plp
    rts

Vm_Str_ReleaseIfDynamic:
    php
    rep #$31
.a16
.i16
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_STR
    beq Vm_Str_ReleaseIfDynamic__isstr
    plp
    rts

Vm_Str_ReleaseIfDynamic__isstr:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+6,x
    and #$8000
    beq Vm_Str_ReleaseIfDynamic__done
    lda.l VmSlots_Wram+4,x
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmStrPool_Wram+0,x
    beq Vm_Str_ReleaseIfDynamic__done8
    dec a
    sta.l VmStrPool_Wram+0,x

Vm_Str_ReleaseIfDynamic__done8:
.a8
    rep #$31
.a16
.i16

Vm_Str_ReleaseIfDynamic__done:
.a16
.i16
    plp
    rts

; ============================================================================
; Vm_Str_Resolve -- in: A (.a16) = slot index, ALREADY known to be BOR_VT_STR
; (every caller checks the type itself first, same precedent as
; Vm_LoadBinaryInt's callers checking nothing -- here the check lives in
; Vm_Str_LoadA/LoadB below). out: VmStr_SrcOff = byte offset of the string's
; data (within VmStrPool_Wram if VmStr_SrcIsPool=1, within VmCode_Wram if
; =0), VmStr_CopyLen = its length clamped to VMSTRPOOL_MAX_LEN. Never faults.
; ============================================================================
Vm_Str_Resolve:
    php
    rep #$31
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l VmSlots_Wram+6,x
    and #$8000
    beq Vm_Str_Resolve__rom

    ; --- dynamic pool string ---
    lda.l VmSlots_Wram+4,x       ; pool object index
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a                        ; * VMSTRPOOL_OBJ_SIZE (64)
    sta.l VmStr_SrcOff
    tax
    sep #$20
.a8
    lda.l VmStrPool_Wram+1,x     ; object's length byte
    rep #$31
.a16
.i16
    and #$00FF
    sta.l VmStr_CopyLen
    lda.l VmStr_SrcOff
    clc
    adc #2                       ; skip the refcount/length header
    sta.l VmStr_SrcOff
    sep #$20
.a8
    lda #1
    sta.l VmStr_SrcIsPool
    rep #$31
.a16
.i16
    bra Vm_Str_Resolve__clamp

Vm_Str_Resolve__rom:
.a16
.i16
    lda.l VmSlots_Wram+4,x        ; ROM string-table index
    sta.l VmStr_Tmp0
    lda.l VmStr_StringsOff
    tax
    lda.l VmCode_Wram,x           ; string_count
    sta.l VmStr_Tmp1
    lda.l VmStr_Tmp0
    asl a                         ; index * 2
    clc
    adc.l VmStr_StringsOff
    clc
    adc #2                        ; -> address of offset[index]
    tax
    lda.l VmCode_Wram,x           ; start
    sta.l VmStr_Tmp2
    lda.l VmCode_Wram+2,x         ; offset[index+1] = end
    sec
    sbc.l VmStr_Tmp2
    sta.l VmStr_CopyLen
    lda.l VmStr_Tmp1
    inc a
    asl a                         ; (string_count+1) * 2
    clc
    adc.l VmStr_StringsOff
    clc
    adc #2                        ; -> bytes[] base
    clc
    adc.l VmStr_Tmp2              ; + start -> this string's byte offset
    sta.l VmStr_SrcOff
    sep #$20
.a8
    lda #0
    sta.l VmStr_SrcIsPool
    rep #$31
.a16
.i16

Vm_Str_Resolve__clamp:
.a16
.i16
    lda.l VmStr_CopyLen
    cmp #VMSTRPOOL_MAX_LEN
    bcc Vm_Str_Resolve__done
    lda #VMSTRPOOL_MAX_LEN
    sta.l VmStr_CopyLen

Vm_Str_Resolve__done:
.a16
.i16
    plp
    rts

; ============================================================================
; Vm_Str_LoadA / Vm_Str_LoadB -- in: A (.a16) = slot index, already known to
; be BOR_VT_STR. Resolves it (Vm_Str_Resolve) and copies its bytes into
; VmStr_ScratchA/LenA (LoadA) or VmStr_ScratchB/LenB (LoadB). Never faults --
; length is already clamped by Vm_Str_Resolve. Byte-copy shape (push across
; the .a8/.a16 boundary, reload X, store) matches vm_slots.pasm's
; Vm_LoadSlots__copy_loop exactly; long-indexed addressing is X-only on real
; 65816 (CLAUDE.md), so the source and destination cursors can't both live
; in X/Y simultaneously the way a same-mode copy would -- recomputing X for
; each side, once per byte, is the established workaround here.
; ============================================================================
Vm_Str_LoadA:
    php
    jsr Vm_Str_Resolve
    rep #$31
.a16
.i16
    lda.l VmStr_CopyLen
    sta.l VmStr_LenA
    lda #0
    sta.l VmStr_CopyI
    sep #$20
.a8
    lda.l VmStr_SrcIsPool
    bne Vm_Str_LoadA__pool
    rep #$31
.a16
.i16
    bra Vm_Str_LoadA__rom_loop

Vm_Str_LoadA__pool:
.a8
    rep #$31
.a16
.i16
    bra Vm_Str_LoadA__pool_loop

Vm_Str_LoadA__rom_loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenA
    bcs Vm_Str_LoadA__done
    clc
    lda.l VmStr_SrcOff
    adc.l VmStr_CopyI
    tax
    sep #$20
.a8
    lda.l VmCode_Wram,x
    pha
    rep #$31
.a16
.i16
    lda.l VmStr_CopyI
    tax
    sep #$20
.a8
    pla
    sta.l VmStr_ScratchA,x
    rep #$31
.a16
.i16
    lda.l VmStr_CopyI
    inc a
    sta.l VmStr_CopyI
    bra Vm_Str_LoadA__rom_loop

Vm_Str_LoadA__pool_loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenA
    bcs Vm_Str_LoadA__done
    clc
    lda.l VmStr_SrcOff
    adc.l VmStr_CopyI
    tax
    sep #$20
.a8
    lda.l VmStrPool_Wram,x
    pha
    rep #$31
.a16
.i16
    lda.l VmStr_CopyI
    tax
    sep #$20
.a8
    pla
    sta.l VmStr_ScratchA,x
    rep #$31
.a16
.i16
    lda.l VmStr_CopyI
    inc a
    sta.l VmStr_CopyI
    bra Vm_Str_LoadA__pool_loop

Vm_Str_LoadA__done:
.a16
.i16
    plp
    rts

Vm_Str_LoadB:
    php
    jsr Vm_Str_Resolve
    rep #$31
.a16
.i16
    lda.l VmStr_CopyLen
    sta.l VmStr_LenB
    lda #0
    sta.l VmStr_CopyI
    sep #$20
.a8
    lda.l VmStr_SrcIsPool
    bne Vm_Str_LoadB__pool
    rep #$31
.a16
.i16
    bra Vm_Str_LoadB__rom_loop

Vm_Str_LoadB__pool:
.a8
    rep #$31
.a16
.i16
    bra Vm_Str_LoadB__pool_loop

Vm_Str_LoadB__rom_loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenB
    bcs Vm_Str_LoadB__done
    clc
    lda.l VmStr_SrcOff
    adc.l VmStr_CopyI
    tax
    sep #$20
.a8
    lda.l VmCode_Wram,x
    pha
    rep #$31
.a16
.i16
    lda.l VmStr_CopyI
    tax
    sep #$20
.a8
    pla
    sta.l VmStr_ScratchB,x
    rep #$31
.a16
.i16
    lda.l VmStr_CopyI
    inc a
    sta.l VmStr_CopyI
    bra Vm_Str_LoadB__rom_loop

Vm_Str_LoadB__pool_loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenB
    bcs Vm_Str_LoadB__done
    clc
    lda.l VmStr_SrcOff
    adc.l VmStr_CopyI
    tax
    sep #$20
.a8
    lda.l VmStrPool_Wram,x
    pha
    rep #$31
.a16
.i16
    lda.l VmStr_CopyI
    tax
    sep #$20
.a8
    pla
    sta.l VmStr_ScratchB,x
    rep #$31
.a16
.i16
    lda.l VmStr_CopyI
    inc a
    sta.l VmStr_CopyI
    bra Vm_Str_LoadB__pool_loop

Vm_Str_LoadB__done:
.a16
.i16
    plp
    rts

; ============================================================================
; Vm_LoadBinaryStr -- in: VmPriv_B/VmPriv_C (already staged by Vm_Fetch).
; out: carry CLEAR and VmStr_ScratchA/LenA + ScratchB/LenB loaded, if both
; slots are BOR_VT_STR (ROM or dynamic, either/both); carry SET otherwise.
; Same "jsr, never jmp Vm_Fault" contract as Vm_LoadBinaryInt.
; ============================================================================
Vm_LoadBinaryStr:
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
    cmp #BOR_VT_STR
    beq Vm_LoadBinaryStr__left_ok
    plp
    sec
    rts

Vm_LoadBinaryStr__left_ok:
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
    cmp #BOR_VT_STR
    beq Vm_LoadBinaryStr__right_ok
    plp
    sec
    rts

Vm_LoadBinaryStr__right_ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmPriv_B
    jsr Vm_Str_LoadA
    lda.l VmPriv_C
    jsr Vm_Str_LoadB
    plp
    clc
    rts

; ============================================================================
; Vm_CompareStr -- in: VmStr_ScratchA/LenA, ScratchB/LenB already loaded.
; out: VmArith_CmpLT / VmArith_CmpEQ (0 or 1), same cells and same 0/1
; contract as vm_arith32.pasm's Vm_CompareInt -- lexicographic byte compare;
; a string that is a strict prefix of the other is LT; equal bytes and equal
; length is EQ.
; ============================================================================
Vm_CompareStr:
    php
    rep #$31
.a16
.i16
    lda #0
    sta.l VmStr_CopyI

Vm_CompareStr__loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenA
    bcs Vm_CompareStr__a_done
    lda.l VmStr_CopyI
    cmp.l VmStr_LenB
    bcs Vm_CompareStr__greater      ; A has a byte here, B ran out -> A > B

    lda.l VmStr_CopyI
    tax
    sep #$20
.a8
    lda.l VmStr_ScratchA,x
    cmp.l VmStr_ScratchB,x
    beq Vm_CompareStr__eq_byte
    bcc Vm_CompareStr__less
    bra Vm_CompareStr__greater8

Vm_CompareStr__eq_byte:
.a8
    rep #$31
.a16
.i16
    lda.l VmStr_CopyI
    inc a
    sta.l VmStr_CopyI
    bra Vm_CompareStr__loop

Vm_CompareStr__a_done:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenB
    bcs Vm_CompareStr__equal        ; both exhausted at the same index
    lda #1
    sta.l VmArith_CmpLT
    lda #0
    sta.l VmArith_CmpEQ
    plp
    rts

Vm_CompareStr__less:
.a8
    rep #$31
.a16
.i16
    lda #1
    sta.l VmArith_CmpLT
    lda #0
    sta.l VmArith_CmpEQ
    plp
    rts

Vm_CompareStr__greater8:
.a8
    rep #$31
.a16
.i16
Vm_CompareStr__greater:
.a16
.i16
    lda #0
    sta.l VmArith_CmpLT
    sta.l VmArith_CmpEQ
    plp
    rts

Vm_CompareStr__equal:
.a16
.i16
    lda #1
    sta.l VmArith_CmpEQ
    lda #0
    sta.l VmArith_CmpLT
    plp
    rts

; ============================================================================
; Vm_LoadAndCompare -- shared entry for GE/LE/LT/GT/EQ/NE (vm_arith32.pasm
; and vm_run.pasm's Vm_Op_Eq): tries the INTEGER/DECIMAL numeric pair first
; (Gate 5, plan_vm.md §7 -- vm_dec16.pasm's Vm_LoadBinaryNumeric, which
; also accepts a pure-INTEGER pair unchanged from Gate 2/4 and promotes a
; mixed pair to Q16.16; Vm_CompareInt's signed 32-bit raw compare works
; unmodified on promoted Q16.16 values, since Q16.16's raw bit pattern
; preserves int32 ordering exactly), falls back to the STR pair, and
; either way leaves the result in VmArith_CmpLT/CmpEQ so every caller's
; existing downstream store logic (already written against those two
; cells) needs no per-type branching of its own. Carry CLEAR on success,
; SET if neither pairing matched (caller faults VMERR_BAD_TYPE).
; ============================================================================
Vm_LoadAndCompare:
    jsr Vm_LoadBinaryNumeric
    bcc Vm_LoadAndCompare__int
    jsr Vm_LoadBinaryStr
    bcc Vm_LoadAndCompare__str
    jsl Vm_SourceVariantCompareFallback
    rts

Vm_LoadAndCompare__int:
.a8
    jsr Vm_CompareInt
    clc
    rts

Vm_LoadAndCompare__str:
.a8
    jsr Vm_CompareStr
    clc
    rts

; ============================================================================
; Vm_Str_ConcatOp -- ADD's string path (vm_run.pasm's Vm_Op_Add), called
; once VmPriv_A/B/C are known: B and C are both BOR_VT_STR. Loads both,
; allocates a new pool object, writes the concatenated bytes, releases the
; destination slot's OLD value (only after both operands are safely copied
; into scratch buffers, so this is correct even if the destination slot
; aliases B or C), and writes the new dynamic-string handle into A.
; Out: carry CLEAR on success; carry SET + A (.a16) = VMERR_* on failure
; (pool exhausted or combined length over VMSTRPOOL_MAX_LEN). Same
; "jsr, never jmp Vm_Fault" contract as every other Vm_Load*/Op_* helper.
; ============================================================================
Vm_Str_ConcatOp:
    php
    rep #$31
.a16
.i16
    lda.l VmPriv_B
    jsr Vm_Str_LoadA
    lda.l VmPriv_C
    jsr Vm_Str_LoadB

; Vm_Str_ConcatOp__FromScratch -- Gate 5's vm_dec16.pasm Vm_Dec_ConcatCoerce
; (ADD's STR+numeric coercion path) tail-jumps in here via `brl` once it has
; populated VmStr_ScratchA/LenA and VmStr_ScratchB/LenB itself (one side
; via the normal Vm_Str_LoadA/LoadB call, the other from a formatted
; numeric buffer) -- everything below is byte-identical to Vm_Str_ConcatOp
; proper, just entered without its own two jsr Vm_Str_LoadA/LoadB calls
; (which read from actual STR slots the numeric side doesn't have). Same
; php-protected stack frame as Vm_Str_ConcatOp itself -- the tail-jumper's
; OWN `php` (never separately `plp`'d before the jump) supplies the byte
; this routine's `plp` exits below expect to pop; see vm_dec16.pasm's own
; header for why that is correct, not a leak.
Vm_Str_ConcatOp__FromScratch:
.a16
.i16

    lda.l VmStr_LenA
    clc
    adc.l VmStr_LenB
    cmp #VMSTRPOOL_MAX_LEN
    bcc Vm_Str_ConcatOp__len_ok
    beq Vm_Str_ConcatOp__len_ok
    plp
    lda #VMERR_STRING_OVERFLOW
    sec
    rts

Vm_Str_ConcatOp__len_ok:
.a16
.i16
    sta.l VmStr_Tmp0             ; total length
    jsr Vm_Str_Alloc
    bcc Vm_Str_ConcatOp__alloc_ok
    plp
    lda #VMERR_STRING_POOL
    sec
    rts

Vm_Str_ConcatOp__alloc_ok:
.a16
.i16
    lda.l VmStr_NewIdx
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #2                        ; -> new object's data start (past header)
    sta.l VmStr_SrcOff             ; scratch reuse: dest base for the writes below

    lda #0
    sta.l VmStr_CopyI

Vm_Str_ConcatOp__copyA_loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenA
    bcs Vm_Str_ConcatOp__copyB_start
    lda.l VmStr_CopyI
    tax
    sep #$20
.a8
    lda.l VmStr_ScratchA,x
    pha
    rep #$31
.a16
.i16
    clc
    lda.l VmStr_SrcOff
    adc.l VmStr_CopyI
    tax
    sep #$20
.a8
    pla
    sta.l VmStrPool_Wram,x
    rep #$31
.a16
.i16
    lda.l VmStr_CopyI
    inc a
    sta.l VmStr_CopyI
    bra Vm_Str_ConcatOp__copyA_loop

Vm_Str_ConcatOp__copyB_start:
.a16
.i16
    lda #0
    sta.l VmStr_CopyLen           ; scratch reuse: B-copy index

Vm_Str_ConcatOp__copyB_loop:
.a16
.i16
    lda.l VmStr_CopyLen
    cmp.l VmStr_LenB
    bcs Vm_Str_ConcatOp__copy_done
    tax
    sep #$20
.a8
    lda.l VmStr_ScratchB,x
    pha
    rep #$31
.a16
.i16
    clc
    lda.l VmStr_SrcOff
    adc.l VmStr_LenA
    clc
    adc.l VmStr_CopyLen
    tax
    sep #$20
.a8
    pla
    sta.l VmStrPool_Wram,x
    rep #$31
.a16
.i16
    lda.l VmStr_CopyLen
    inc a
    sta.l VmStr_CopyLen
    bra Vm_Str_ConcatOp__copyB_loop

Vm_Str_ConcatOp__copy_done:
.a16
.i16
    lda.l VmStr_NewIdx
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmStr_Tmp0              ; total length (<=62, fits one byte)
    sta.l VmStrPool_Wram+1,x
    rep #$31
.a16
.i16

    lda.l VmPriv_A
    jsr Vm_Str_ReleaseIfDynamic

    lda.l VmPriv_A
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda #BOR_VT_STR
    sta.l VmSlots_Wram+0,x
    lda #2                        ; flags bit1: dynamic-string (FORMAT.md)
    sta.l VmSlots_Wram+1,x
    rep #$31
.a16
.i16
    lda.l VmStr_Tmp0
    sta.l VmSlots_Wram+2,x        ; aux = length
    lda.l VmStr_NewIdx
    sta.l VmSlots_Wram+4,x        ; value lo = pool index
    lda #VMSTR_DYNAMIC_HI
    sta.l VmSlots_Wram+6,x        ; value hi = dynamic marker

    plp
    clc
    rts

; ============================================================================
; Vm_Str_TruthySlot -- in: A (.a16) = slot index, ALREADY known to be
; BOR_VT_STR. out: A (.a16) = 0 or 1 (empty string is falsy, README §6).
; Reads aux (the cached length) directly -- never touches the pool/ROM
; string table, since length alone answers truthiness.
; ============================================================================
Vm_Str_TruthySlot:
    php
    rep #$31
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l VmSlots_Wram+2,x
    beq Vm_Str_TruthySlot__falsy
    lda #1
    plp
    rts

Vm_Str_TruthySlot__falsy:
.a16
.i16
    lda #0
    plp
    rts
