; Source-only PTR/EMPTY operations needed by script-local identities.
; Build 4086 ScriptVariant.c prints PTR as '#' + signed 32-bit LONG decimal.
; Opaque tokens are source-world identities, not original-BOR player indices.
; Only an installed source caller lease enables these new operations. Legacy
; unsupported mixed variants keep their existing BAD_TYPE result.
; Entire implementation is in bank 28. Thin redirects reduce bank-0 bytes.
VmSourceOps_LeftType = $7FF656
VmSourceOps_RightType = $7FF658
VmSourceOps_Side = $7FF65A
VmSourceOps_PtrSlot = $7FF65C

Vm_SourceVariantTruthyFallback:
.a16
.i16
    php
    rep #$31
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    bne Vm_SourceVariantTruthyFallback__false
    lda.l VmSlots_Wram,x
    and #$00FF
    cmp #BOR_VT_PTR
    bne Vm_SourceVariantTruthyFallback__false
    lda.l VmSlots_Wram+4,x
    ora.l VmSlots_Wram+6,x
    beq Vm_SourceVariantTruthyFallback__false
    lda #1
    plp
    rtl
Vm_SourceVariantTruthyFallback__false:
.a16
.i16
    lda #0
    plp
    rtl

Vm_SourceVariantAddFallback:
.a16
.i16
    rep #$31
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    beq Vm_SourceVariantAddFallback__context
    jmp Vm_SourceVariantAddFallback__bad
Vm_SourceVariantAddFallback__context:
.a16
.i16
    jsr Vm_SourceOpsTypes
    lda.l VmSourceOps_LeftType
    cmp #BOR_VT_STR
    bne Vm_SourceVariantAddFallback__left_ptr
    lda.l VmSourceOps_RightType
    cmp #BOR_VT_PTR
    beq Vm_SourceVariantAddFallback__right_ptr_ok
    jmp Vm_SourceVariantAddFallback__bad
Vm_SourceVariantAddFallback__right_ptr_ok:
.a16
.i16
    lda #0
    sta.l VmSourceOps_Side
    lda.l VmPriv_B
    jsr Vm_SourceStr_LoadA
    lda.l VmPriv_C
    bra Vm_SourceVariantAddFallback__format
Vm_SourceVariantAddFallback__left_ptr:
.a16
.i16
    cmp #BOR_VT_PTR
    beq Vm_SourceVariantAddFallback__check_right
    jmp Vm_SourceVariantAddFallback__bad
Vm_SourceVariantAddFallback__check_right:
.a16
.i16
    lda.l VmSourceOps_RightType
    cmp #BOR_VT_STR
    beq Vm_SourceVariantAddFallback__left_ptr_ok
    jmp Vm_SourceVariantAddFallback__bad
Vm_SourceVariantAddFallback__left_ptr_ok:
.a16
.i16
    lda #1
    sta.l VmSourceOps_Side
    lda.l VmPriv_C
    jsr Vm_SourceStr_LoadB
    lda.l VmPriv_B
Vm_SourceVariantAddFallback__format:
.a16
.i16
    ; FormatSlot's non-DECIMAL path formats the full signed raw u32 value.
    jsl Vm_Dec_FormatSlot
    rep #$31
    lda.l VmSourceOps_Side
    bne Vm_SourceVariantAddFallback__format_left
    lda #$0023
    sta.l VmStr_ScratchB
    tya
    inc a
    sta.l VmStr_LenB
    ldx #0
Vm_SourceVariantAddFallback__copy_right:
.a16
.i16
    lda.l VmDec_FormatBuf,x
    and #$00FF
    sep #$20
.a8
    sta.l VmStr_ScratchB+1,x
    rep #$31
.a16
.i16
    inx
    txa
    cmp.l VmDec_FormatLen
    bcc Vm_SourceVariantAddFallback__copy_right
    bra Vm_SourceVariantAddFallback__concat
Vm_SourceVariantAddFallback__format_left:
.a16
.i16
    lda #$0023
    sta.l VmStr_ScratchA
    tya
    inc a
    sta.l VmStr_LenA
    ldx #0
Vm_SourceVariantAddFallback__copy_left:
.a16
.i16
    lda.l VmDec_FormatBuf,x
    and #$00FF
    sep #$20
.a8
    sta.l VmStr_ScratchA+1,x
    rep #$31
.a16
.i16
    inx
    txa
    cmp.l VmDec_FormatLen
    bcc Vm_SourceVariantAddFallback__copy_left
Vm_SourceVariantAddFallback__concat:
.a16
.i16
    jsr Vm_SourceStr_ConcatPrepared
    bcc Vm_SourceVariantAddFallback__done
    jml Vm_Fault
Vm_SourceVariantAddFallback__done:
.a16
.i16
    jml Vm_Next
Vm_SourceVariantAddFallback__bad:
.a16
.i16
    lda #VMERR_BAD_TYPE
    jml Vm_Fault

; Called after numeric/STR comparison paths refuse a pairing. Preserves the
; caller's width flags; only EQ/NE of PTR/EMPTY are admitted in this capability.
; Mixed ordered variants remain explicitly unsupported.
Vm_SourceVariantCompareFallback:
.a16
.i16
    php
    rep #$31
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    beq Vm_SourceVariantCompareFallback__context
    jmp Vm_SourceVariantCompareFallback__bad
Vm_SourceVariantCompareFallback__context:
.a16
.i16
    lda.l VmPriv_Opcode
    and #$00FF
    cmp #BOR_OP_EQ
    beq Vm_SourceVariantCompareFallback__types
    cmp #BOR_OP_NE
    beq Vm_SourceVariantCompareFallback__types
    jmp Vm_SourceVariantCompareFallback__bad
Vm_SourceVariantCompareFallback__types:
.a16
.i16
    jsr Vm_SourceOpsTypes
    lda.l VmSourceOps_LeftType
    beq Vm_SourceVariantCompareFallback__left_ok
    cmp #BOR_VT_PTR
    beq Vm_SourceVariantCompareFallback__left_ok
    jmp Vm_SourceVariantCompareFallback__bad
Vm_SourceVariantCompareFallback__left_ok:
.a16
.i16
    lda.l VmSourceOps_RightType
    beq Vm_SourceVariantCompareFallback__right_ok
    cmp #BOR_VT_PTR
    beq Vm_SourceVariantCompareFallback__right_ok
    jmp Vm_SourceVariantCompareFallback__bad
Vm_SourceVariantCompareFallback__right_ok:
.a16
.i16
    lda #0
    sta.l VmArith_CmpLT
    sta.l VmArith_CmpEQ
    lda.l VmSourceOps_RightType
    cmp.l VmSourceOps_LeftType
    bne Vm_SourceVariantCompareFallback__done
    cmp #BOR_VT_PTR
    bne Vm_SourceVariantCompareFallback__equal ; EMPTY/EMPTY
    lda.l VmPriv_B
    asl a
    asl a
    asl a
    tax
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_LeftLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_LeftHi
    lda.l VmPriv_C
    asl a
    asl a
    asl a
    tax
    lda.l VmSlots_Wram+4,x
    cmp.l VmPriv_LeftLo
    bne Vm_SourceVariantCompareFallback__done
    lda.l VmSlots_Wram+6,x
    cmp.l VmPriv_LeftHi
    bne Vm_SourceVariantCompareFallback__done
Vm_SourceVariantCompareFallback__equal:
.a16
.i16
    lda #1
    sta.l VmArith_CmpEQ
Vm_SourceVariantCompareFallback__done:
.a16
.i16
    plp
    clc
    rtl
Vm_SourceVariantCompareFallback__bad:
.a16
.i16
    plp
    sec
    rtl

Vm_SourceOpsTypes:
.a16
.i16
    lda.l VmPriv_B
    asl a
    asl a
    asl a
    tax
    lda.l VmSlots_Wram,x
    and #$00FF
    sta.l VmSourceOps_LeftType
    lda.l VmPriv_C
    asl a
    asl a
    asl a
    tax
    lda.l VmSlots_Wram,x
    and #$00FF
    sta.l VmSourceOps_RightType
    rts

Vm_SourceStr_ConcatPrepared:
.a16
.i16
    php
    rep #$31
    jmp Vm_SourceStr_ConcatOp__FromScratch

; Same-bank slab helpers derived from vm_string.pasm. No bank-0 code
; additions or cross-bank JSRs. Shared pool/scratch and ownership ABI.
Vm_SourceStr_Alloc:
    php
    rep #$31
.a16
.i16
    lda #0
    sta.l VmStr_ScanIdx

Vm_SourceStr_Alloc__loop:
.a16
.i16
    lda.l VmStr_ScanIdx
    cmp #VMSTRPOOL_OBJ_COUNT
    bcc Vm_SourceStr_Alloc__check
    plp
    sec
    rts

Vm_SourceStr_Alloc__check:
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
    bne Vm_SourceStr_Alloc__next
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

Vm_SourceStr_Alloc__next:
.a8
    rep #$31
.a16
.i16
    lda.l VmStr_ScanIdx
    inc a
    sta.l VmStr_ScanIdx
    bra Vm_SourceStr_Alloc__loop

; ============================================================================
; Vm_SourceStr_RetainIfDynamic / Vm_SourceStr_ReleaseIfDynamic -- in: A (.a16) = slot
; index. No-op on any non-STR slot and on ROM strings (never refcounted);
; on a dynamic string, increments/decrements the pool object's refcount.
; Retain saturates at 255 rather than wrapping to 0 (which would read as
; "free"); release refuses to decrement an already-0 refcount for the same
; reason -- both defensive, neither should be reachable through normal use
; (every dynamic handle in a slot was put there by Vm_SourceStr_ConcatOp, which
; only ever hands out objects Vm_SourceStr_Alloc just set to 1).
; ============================================================================

Vm_SourceStr_ReleaseIfDynamic:
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
    beq Vm_SourceStr_ReleaseIfDynamic__isstr
    plp
    rts

Vm_SourceStr_ReleaseIfDynamic__isstr:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+6,x
    and #$8000
    beq Vm_SourceStr_ReleaseIfDynamic__done
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
    beq Vm_SourceStr_ReleaseIfDynamic__done8
    dec a
    sta.l VmStrPool_Wram+0,x

Vm_SourceStr_ReleaseIfDynamic__done8:
.a8
    rep #$31
.a16
.i16

Vm_SourceStr_ReleaseIfDynamic__done:
.a16
.i16
    plp
    rts

; ============================================================================
; Vm_SourceStr_Resolve -- in: A (.a16) = slot index, ALREADY known to be BOR_VT_STR
; (every caller checks the type itself first, same precedent as
; Vm_LoadBinaryInt's callers checking nothing -- here the check lives in
; Vm_SourceStr_LoadA/LoadB below). out: VmStr_SrcOff = byte offset of the string's
; data (within VmStrPool_Wram if VmStr_SrcIsPool=1, within VmCode_Wram if
; =0), VmStr_CopyLen = its length clamped to VMSTRPOOL_MAX_LEN. Never faults.
; ============================================================================

Vm_SourceStr_Resolve:
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
    beq Vm_SourceStr_Resolve__rom

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
    bra Vm_SourceStr_Resolve__clamp

Vm_SourceStr_Resolve__rom:
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

Vm_SourceStr_Resolve__clamp:
.a16
.i16
    lda.l VmStr_CopyLen
    cmp #VMSTRPOOL_MAX_LEN
    bcc Vm_SourceStr_Resolve__done
    lda #VMSTRPOOL_MAX_LEN
    sta.l VmStr_CopyLen

Vm_SourceStr_Resolve__done:
.a16
.i16
    plp
    rts

; ============================================================================
; Vm_SourceStr_LoadA / Vm_SourceStr_LoadB -- in: A (.a16) = slot index, already known to
; be BOR_VT_STR. Resolves it (Vm_SourceStr_Resolve) and copies its bytes into
; VmStr_ScratchA/LenA (LoadA) or VmStr_ScratchB/LenB (LoadB). Never faults --
; length is already clamped by Vm_SourceStr_Resolve. Byte-copy shape (push across
; the .a8/.a16 boundary, reload X, store) matches vm_slots.pasm's
; Vm_LoadSlots__copy_loop exactly; long-indexed addressing is X-only on real
; 65816 (CLAUDE.md), so the source and destination cursors can't both live
; in X/Y simultaneously the way a same-mode copy would -- recomputing X for
; each side, once per byte, is the established workaround here.
; ============================================================================
Vm_SourceStr_LoadA:
    php
    jsr Vm_SourceStr_Resolve
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
    bne Vm_SourceStr_LoadA__pool
    rep #$31
.a16
.i16
    bra Vm_SourceStr_LoadA__rom_loop

Vm_SourceStr_LoadA__pool:
.a8
    rep #$31
.a16
.i16
    bra Vm_SourceStr_LoadA__pool_loop

Vm_SourceStr_LoadA__rom_loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenA
    bcs Vm_SourceStr_LoadA__done
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
    bra Vm_SourceStr_LoadA__rom_loop

Vm_SourceStr_LoadA__pool_loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenA
    bcs Vm_SourceStr_LoadA__done
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
    bra Vm_SourceStr_LoadA__pool_loop

Vm_SourceStr_LoadA__done:
.a16
.i16
    plp
    rts

Vm_SourceStr_LoadB:
    php
    jsr Vm_SourceStr_Resolve
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
    bne Vm_SourceStr_LoadB__pool
    rep #$31
.a16
.i16
    bra Vm_SourceStr_LoadB__rom_loop

Vm_SourceStr_LoadB__pool:
.a8
    rep #$31
.a16
.i16
    bra Vm_SourceStr_LoadB__pool_loop

Vm_SourceStr_LoadB__rom_loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenB
    bcs Vm_SourceStr_LoadB__done
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
    bra Vm_SourceStr_LoadB__rom_loop

Vm_SourceStr_LoadB__pool_loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenB
    bcs Vm_SourceStr_LoadB__done
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
    bra Vm_SourceStr_LoadB__pool_loop

Vm_SourceStr_LoadB__done:
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

Vm_SourceStr_ConcatOp__FromScratch:
.a16
.i16

    lda.l VmStr_LenA
    clc
    adc.l VmStr_LenB
    cmp #VMSTRPOOL_MAX_LEN
    bcc Vm_SourceStr_ConcatOp__len_ok
    beq Vm_SourceStr_ConcatOp__len_ok
    plp
    lda #VMERR_STRING_OVERFLOW
    sec
    rts

Vm_SourceStr_ConcatOp__len_ok:
.a16
.i16
    sta.l VmStr_Tmp0             ; total length
    jsr Vm_SourceStr_Alloc
    bcc Vm_SourceStr_ConcatOp__alloc_ok
    plp
    lda #VMERR_STRING_POOL
    sec
    rts

Vm_SourceStr_ConcatOp__alloc_ok:
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

Vm_SourceStr_ConcatOp__copyA_loop:
.a16
.i16
    lda.l VmStr_CopyI
    cmp.l VmStr_LenA
    bcs Vm_SourceStr_ConcatOp__copyB_start
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
    bra Vm_SourceStr_ConcatOp__copyA_loop

Vm_SourceStr_ConcatOp__copyB_start:
.a16
.i16
    lda #0
    sta.l VmStr_CopyLen           ; scratch reuse: B-copy index

Vm_SourceStr_ConcatOp__copyB_loop:
.a16
.i16
    lda.l VmStr_CopyLen
    cmp.l VmStr_LenB
    bcs Vm_SourceStr_ConcatOp__copy_done
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
    bra Vm_SourceStr_ConcatOp__copyB_loop

Vm_SourceStr_ConcatOp__copy_done:
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
    jsr Vm_SourceStr_ReleaseIfDynamic

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
; Vm_SourceStr_TruthySlot -- in: A (.a16) = slot index, ALREADY known to be
; BOR_VT_STR. out: A (.a16) = 0 or 1 (empty string is falsy, README §6).
; Reads aux (the cached length) directly -- never touches the pool/ROM
; string table, since length alone answers truthiness.
; ============================================================================
