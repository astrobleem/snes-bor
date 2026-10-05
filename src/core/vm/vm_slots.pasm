; ============================================================================
; core/vm/vm_slots.pasm -- Gate 0 (plan_vm.md §2): copy the module's initial
; slot image into VmSlots_Wram, and stage the one other header field the
; interpreter needs but Gate 0a's Vm_ValidateHeader didn't store.
;
; Gate 0a loaded the module image and validated its header, but deliberately
; did not copy the initial slot image out of it -- that is this file's job,
; called once at boot, directly after Vm_Load.
;
; Two header fields are read here, both u32 at the offsets FORMAT.md gives,
; treated as 16-bit (module_size is 184 bytes; no field in a Gate-0-scope
; module ever needs the high word, same simplification Vm_ValidateHeader
; already made for module_size itself):
;   - initial_slots_offset (header +$1C), used immediately below.
;   - instructions_offset (header +$18), cached to VmPriv_InstrOff (declared
;     in vm_run.pasm) for every later record fetch to fold into its index.
;     The plan's own fetch formula ("X = IP*8, then lda.l VmCode_Wram,x")
;     omits this add, which only works if instructions_offsets is always
;     exactly HEADER_SIZE (64) -- true for every module the canonical
;     exporter will ever produce (FORMAT.md's normalization rules), but
;     Vm_ValidateHeader does not assert it (deferred, like the CRC32 TODO).
;     Reading and folding in the real field, the same way the plan explicitly
;     asks for initial_slots_offset just below, costs one extra header read
;     and removes the assumption entirely -- so that is what this does.
;
; Global (not @-local) labels; jsr/rts (bank 0); explicit width directive
; after every label (poppy#386); no nop guards (that bug is fixed).
; ============================================================================

; --- Vm_Boot -- the single boot-time call site main.pasm uses (replacing
; the bare `jsr Vm_Load` Gate 0a originally wired in). Runs Vm_Load then
; Vm_LoadSlots as one step. This exists purely to keep scpu_boot's own byte
; count unchanged as Gate 0 adds a second boot-time step: scpu_boot's fixed
; $FC00-$FF60 region had only 6 bytes of margin left (see
; tools/rom_audit/audit_all.py's own main-loop-margin check), not enough for
; two new 3-byte jsr calls. Swapping the existing call's TARGET costs nothing
; extra there; only Vm_Run's new per-frame call in scpu_main_loop needed the
; margin. Vm_Load's own behavior, and everything Gate 0a's vm_gate0a.py
; verifies, is unchanged -- it is simply invoked one level of indirection
; deeper now. ---
Vm_Boot:
    jsl Vm_FetchSourceInit
    jsr Vm_Load
    jsr Vm_LoadSlots
    rts

; --- Vm_LoadSlots -- called from Vm_Boot, directly after Vm_Load. Copies
; VmState_SlotCount * 8 bytes from VmCode_Wram + initial_slots_offset to
; VmSlots_Wram, and caches instructions_offset for the interpreter. ---
Vm_LoadSlots:
    php
    rep #$31
.a16
.i16

    ; instructions_offset (header +$18) -> VmPriv_InstrOff, read once and
    ; cached: it does not change for the life of a loaded module, and folding
    ; it into every single record fetch's index arithmetic (Gate 0's hottest
    ; path from Gate 1 onward) is cheaper done once here than re-read from
    ; VmCode_Wram on every fetch.
    lda.l VmCode_Wram+$18
    sta.l VmPriv_InstrOff

    ; callsites_offset (header +$20) / arg_slot_ids_offset (header +$24) --
    ; Gate 3 (plan_vm.md §5): cached once here, same rationale as
    ; instructions_offset just above -- CALL/PARAM re-read these on every
    ; call/param, so folding the header lookup in here once is cheaper than
    ; re-reading VmCode_Wram+$20/+$24 from vm_call.pasm on every dispatch.
    lda.l VmCode_Wram+$20
    sta.l VmCall_CallsitesOff
    lda.l VmCode_Wram+$24
    sta.l VmCall_ArgSlotsOff

    ; strings_offset (header +$28) -- Gate 4 (plan_vm.md §6): cached once
    ; here, same rationale as callsites_offset/arg_slot_ids_offset just
    ; above. Vm_Str_Resolve (core/vm/vm_string.pasm) re-reads this on every
    ; ROM-string load. VmStr_StringsOff is declared in vm_string.pasm, which
    ; is .include'd AFTER this file -- a forward reference across files, the
    ; same one this whole vm/ directory already relies on throughout
    ; (vm_arith32.pasm's own header note; vm_run.pasm's dispatch table
    ; forward-references handlers hundreds of lines below it in the SAME
    ; file). Poppy resolves global labels regardless of definition order.
    lda.l VmCode_Wram+$28
    sta.l VmStr_StringsOff

    ; initial_slots_offset (header +$1C) -- used immediately, not cached.
    lda.l VmCode_Wram+$1C
    sta.l VmPriv_CopySrc            ; source cursor starts at the slot image

    lda #0
    sta.l VmPriv_CopyDst             ; dest cursor starts at VmSlots_Wram+0

    lda.l VmState_SlotCount
    asl a
    asl a
    asl a                             ; slot_count * 8 -- VM_SLOT_MAX (1024)
                                       ; keeps this well under 16 bits (8192 max)
    sta.l VmPriv_CopyLen

Vm_LoadSlots__copy_loop:
    rep #$31
.a16
.i16
    lda.l VmPriv_CopyDst
    cmp.l VmPriv_CopyLen
    bcs Vm_LoadSlots__done

    lda.l VmPriv_CopySrc
    tax
    sep #$20
.a8
    lda.l VmCode_Wram,x               ; read one source byte
    pha                                ; preserve across the dest index reload
    rep #$31
.a16
.i16
    lda.l VmPriv_CopyDst
    tax
    sep #$20
.a8
    pla
    sta.l VmSlots_Wram,x               ; write one dest byte

    rep #$31
.a16
.i16
    lda.l VmPriv_CopySrc
    inc a
    sta.l VmPriv_CopySrc
    lda.l VmPriv_CopyDst
    inc a
    sta.l VmPriv_CopyDst
    bra Vm_LoadSlots__copy_loop

Vm_LoadSlots__done:
    plp
    rts
