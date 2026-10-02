; ============================================================================
; core/vm/vm_call.pasm -- Gate 3 (plan_vm.md §5): CALL/PARAM/JUMPR/RET with
; real call frames, plus a minimal native function table (abs/min/max/log).
;
; Frame layout (VM_FRAME_SIZE=12, vm_consts.pasm) is the bootstrap package's
; README §7 BorCallFrame, deviation 1 already in effect project-wide (plain
; WRAM at VmFrames_Wram, not BW-RAM):
;   +0  .dw return_ip
;   +2  .dw caller_result_slot
;   +4  .dw callsite_id
;   +6  .dw arg_cursor
;   +8  .dw return_source_slot   -- $FFFF sentinel until JUMPR stages one
;   +10 .dw reserved
; VmState_FrameTop is the frame COUNT (0 = root, no active frame). The
; active frame, when FrameTop > 0, is always index FrameTop-1 -- CALL writes
; a new frame at the OLD FrameTop before incrementing; PARAM/JUMPR/RET all
; read/write index FrameTop-1.
;
; Callsite table record layout (VM_CALLSITE_SIZE=12, FORMAT.md "Callsite
; table"):
;   +0  .db target_kind   -- VM_TARGET_KIND_SCRIPT/IMPORT/NATIVE
;   +1  .db argc
;   +2  .dw target_id     -- stable native ID (native) or unused (script --
;                             CALL's own operand A is the authoritative
;                             script entry, per the package's README §7 CALL
;                             step 2: "jump to the script entry in operand a")
;   +4  .dw result_slot   -- not read here; CALL's own operand B is
;                             authoritative (README §7 step 3: "write the
;                             result to operand b"), same precedent as
;                             target_id above. A real exporter keeps both
;                             fields in agreement; this interpreter only
;                             ever trusts the instruction record.
;   +6  .dw arg_list_index -- into the flat u16 arg-slot-id table at
;                              VmCall_ArgSlotsOff
;   +8  .dw flags          -- unused, Gate 3
;   +A  .dw debug_name_id  -- unused, Gate 3
; Addressed exactly like instruction records (vm_run.pasm's Vm_Fetch):
; X = VmCall_CallsitesOff + callsite_id*VM_CALLSITE_SIZE, then
; `lda.l VmCode_Wram+n,x` per field -- both offsets are cached once at load
; by vm_slots.pasm's Vm_LoadSlots (header +$20/+$24), the same pattern it
; already uses for instructions_offset.
;
; Native-call ABI (README §7 "Native-call ABI", adapted off Direct Page --
; DP belongs to core/oop.pasm project-wide, vm_run.pasm's own header note):
; a native routine is `jsr`'d with VmCall_TargetId/Argc/ArgListIndex already
; staged by Vm_Op_Call, and returns exactly like vm_arith32.pasm's
; Vm_LoadBinaryInt does -- carry CLEAR + VmPriv_LeftLo/Hi holding the 32-bit
; INTEGER result on success, carry SET + A (.a16) holding a VMERR_* code on
; failure. This is not a stylistic choice: every native here is `jsr`'d from
; Vm_Op_Call, which was itself reached by `jmp` from the dispatcher (stack
; clean) -- a native `jmp`-ing straight to Vm_Fault would abandon its own
; jsr return address permanently, corrupting the next `rts` anywhere in the
; interpreter. Same reasoning vm_arith32.pasm's header already documents for
; Vm_LoadBinaryInt; natives just reuse the identical shape.
;
; Two-word (Lo/Hi) 32-bit scratch reuse: this file borrows vm_arith32.pasm's
; VmArith_NegLo/Hi + Vm_Negate32 (native abs), and VmPriv_LeftLo/Hi +
; RightLo/Hi + Vm_CompareInt (native min/max) -- same cross-file scratch
; reuse vm_arith32.pasm itself already established against vm_run.pasm's
; cells. CALL/PARAM/JUMPR/RET's own frame/callsite index arithmetic reuses
; VmPriv_LeftLo/RightLo/RightHi too, never concurrently with an opcode
; handler's own use of them (a single dispatch never runs two handlers).
;
; Global (not @-local) labels; jsr/rts (bank 0); explicit width directive
; after every label (poppy#386, still live); no nop guards (that bug is
; fixed); every far fault exit uses the near-branch-to-local-trampoline-
; then-brl shape vm_run.pasm/vm_arith32.pasm both already use.
; ============================================================================

; --- Scratch WRAM. Free region grep-confirmed clear at Gate 3: everything
; from VM_STATE_LAST through VmArith_CopyBuf (vm_arith32.pasm) ends at
; $7FE0ED; VmFrames_Wram (this gate's own frame stack) starts at $7FE100 and
; runs to $7FE3FF; VmStrPool_Wram (Gate 4, unimplemented) reserves
; $7FE400-$7FF3FF. Placed after both reservations, at $7FF400, rather than
; squeezed into the 19-byte $7FE0ED-$7FE100 gap: comfortably free (nothing
; in src/ references $7FF400+), and keeps this file's cells out of Gate 4's
; way entirely instead of relying on a gap that would need re-measuring
; every time either reservation's size changes. ---
VmCall_CallsitesOff = $7FF400   ; .dw -- cached callsites_offset (header +$20)
VmCall_ArgSlotsOff  = $7FF402   ; .dw -- cached arg_slot_ids_offset (header +$24)
VmCall_TargetKind   = $7FF404   ; .db -- current callsite's target_kind
VmCall_Argc         = $7FF405   ; .db -- current callsite's argc
VmCall_TargetId     = $7FF406   ; .dw -- current callsite's target_id (native ID)
VmCall_ArgListIndex = $7FF408   ; .dw -- current callsite's arg_list_index
VmNative_LogLastLo  = $7FF40A   ; .dw -- test-visible: last value the log
VmNative_LogLastHi  = $7FF40C   ; .dw    native was called with
; Ends $7FF40E.

; ============================================================================
; Vm_CallArgSlot -- in: A (.a16) = zero-based argument index n. Uses
; VmCall_ArgListIndex (already staged by the CALL that is dispatching this
; native). out: X = byte offset of argument n's slot within VmSlots_Wram.
; Never faults, never bounds-checks n against argc -- every native here
; checks VmCall_Argc itself before calling this, exactly once per argument
; it actually needs.
; ============================================================================
Vm_CallArgSlot:
    php
    rep #$31
.a16
.i16
    clc
    adc.l VmCall_ArgListIndex
    asl a                        ; *2 -- each arg-slot-id table entry is u16
    clc
    adc.l VmCall_ArgSlotsOff
    tax
    lda.l VmCode_Wram,x          ; slot id
    asl a
    asl a
    asl a                        ; slot_id*8
    tax
    plp
    rts

; ============================================================================
; Vm_NativeAbs -- argc must be 1; arg0 must be VT_INTEGER. Result is the
; two's-complement absolute value (INT_MIN stays INT_MIN, same wrap rule
; vm_arith32.pasm's Vm_Negate32 already documents).
; ============================================================================
Vm_NativeAbs:
    php
    rep #$31
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #1
    beq Vm_NativeAbs__argc_ok
    plp
    sec
    lda #VMERR_BAD_NATIVE
    rts

Vm_NativeAbs__argc_ok:
.a16
    lda #0
    jsr Vm_CallArgSlot
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    beq Vm_NativeAbs__type_ok
    rep #$31
.a16
.i16
    plp
    sec
    lda #VMERR_BAD_TYPE
    rts

Vm_NativeAbs__type_ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmArith_NegLo
    lda.l VmSlots_Wram+6,x
    sta.l VmArith_NegHi
    and #$8000
    beq Vm_NativeAbs__nonneg      ; sign bit clear -- already non-negative
    jsr Vm_Negate32

Vm_NativeAbs__nonneg:
.a16
    lda.l VmArith_NegLo
    sta.l VmPriv_LeftLo
    lda.l VmArith_NegHi
    sta.l VmPriv_LeftHi
    plp
    clc
    rts

; ============================================================================
; Vm_NativeMinMax -- shared body for min/max. argc must be 2; both arg0/
; arg1 must be VT_INTEGER. Uses vm_arith32.pasm's Vm_CompareInt (needs
; VmPriv_Left/RightLo/Hi already loaded, which is exactly this routine's own
; job). X (.i16) selects which operand Vm_CompareInt's outcome should keep:
; entered with X=0 for MIN (keep left when left<right), X=1 for MAX (keep
; left when NOT left<right) -- see the two public entry points below.
; ============================================================================
Vm_NativeMinMax:
    php
    rep #$31
.a16
.i16
    txa
    pha                           ; stash the min/max selector across the
                                   ; argc/type checks and Vm_CallArgSlot
                                   ; calls below, all of which clobber X
    lda.l VmCall_Argc
    and #$00FF
    cmp #2
    beq Vm_NativeMinMax__argc_ok
    pla
    plp
    sec
    lda #VMERR_BAD_NATIVE
    rts

Vm_NativeMinMax__argc_ok:
.a16
    lda #0
    jsr Vm_CallArgSlot
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    beq Vm_NativeMinMax__left_ok
    rep #$31
.a16
.i16
    pla
    plp
    sec
    lda #VMERR_BAD_TYPE
    rts

Vm_NativeMinMax__left_ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_LeftLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_LeftHi

    lda #1
    jsr Vm_CallArgSlot
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    beq Vm_NativeMinMax__right_ok
    rep #$31
.a16
.i16
    pla
    plp
    sec
    lda #VMERR_BAD_TYPE
    rts

Vm_NativeMinMax__right_ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_RightLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_RightHi

    jsr Vm_CompareInt

    pla                            ; recover the min/max selector
    beq Vm_NativeMinMax__is_min

    ; MAX: keep left when NOT (left < right)
    lda.l VmArith_CmpLT
    bne Vm_NativeMinMax__take_right
    bra Vm_NativeMinMax__take_left

Vm_NativeMinMax__is_min:
.a16
    ; MIN: keep left when left < right
    lda.l VmArith_CmpLT
    bne Vm_NativeMinMax__take_left

Vm_NativeMinMax__take_right:
.a16
    lda.l VmPriv_RightLo
    sta.l VmPriv_LeftLo
    lda.l VmPriv_RightHi
    sta.l VmPriv_LeftHi

Vm_NativeMinMax__take_left:
.a16
    ; result already sits in VmPriv_LeftLo/Hi either way
    plp
    clc
    rts

Vm_NativeMin:
.i16
    ldx #0
    jmp Vm_NativeMinMax

Vm_NativeMax:
.i16
    ldx #1
    jmp Vm_NativeMinMax

; ============================================================================
; Vm_NativeLog -- argc must be 1; arg0 must be VT_INTEGER. Test-logging
; function (plan_vm.md §5): records the value for a gate script to inspect
; via WRAM, and returns it unchanged (log-and-pass-through, rather than a
; void return with no way to confirm the call happened from outside).
; ============================================================================
Vm_NativeLog:
    php
    rep #$31
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #1
    beq Vm_NativeLog__argc_ok
    plp
    sec
    lda #VMERR_BAD_NATIVE
    rts

Vm_NativeLog__argc_ok:
.a16
    lda #0
    jsr Vm_CallArgSlot
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    beq Vm_NativeLog__type_ok
    rep #$31
.a16
.i16
    plp
    sec
    lda #VMERR_BAD_TYPE
    rts

Vm_NativeLog__type_ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_LeftLo
    sta.l VmNative_LogLastLo
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_LeftHi
    sta.l VmNative_LogLastHi
    plp
    clc
    rts

; ============================================================================
; Vm_Op_Call (opcode 8) -- a=script entry / unused for native, b=result
; slot, c=callsite metadata ID. Reads the callsite record at c, then
; dispatches on its target_kind.
; ============================================================================
Vm_Op_Call:
    rep #$31
.a16
.i16
    lda.l VmPriv_C
    asl a
    asl a
    sta.l VmPriv_RightLo          ; c*4
    lda.l VmPriv_C
    asl a
    asl a
    asl a                         ; c*8
    clc
    adc.l VmPriv_RightLo          ; c*12 = VM_CALLSITE_SIZE
    clc
    adc.l VmCall_CallsitesOff
    tax

    sep #$20
.a8
    lda.l VmCode_Wram+0,x
    sta.l VmCall_TargetKind
    lda.l VmCode_Wram+1,x
    sta.l VmCall_Argc
    rep #$31
.a16
.i16
    lda.l VmCode_Wram+2,x
    sta.l VmCall_TargetId
    lda.l VmCode_Wram+6,x
    sta.l VmCall_ArgListIndex

    sep #$20
.a8
    lda.l VmCall_TargetKind
    cmp #VM_TARGET_KIND_NATIVE
    beq Vm_Op_Call__native
    brl Vm_Op_Call__script

; --- Script (and imported-script, normalized identically -- see this
; file's header) target: push a frame, jump to CALL's own operand A. ---
Vm_Op_Call__script:
.a8
    rep #$31
.a16
.i16
    lda.l VmState_FrameTop
    cmp #VM_FRAME_MAX
    bcc Vm_Op_Call__script_ok
    lda #VMERR_CALL_DEPTH
    jmp Vm_Fault

Vm_Op_Call__script_ok:
.a16
    lda.l VmState_FrameTop
    asl a
    asl a
    sta.l VmPriv_RightLo           ; FrameTop*4
    lda.l VmState_FrameTop
    asl a
    asl a
    asl a                          ; FrameTop*8
    clc
    adc.l VmPriv_RightLo           ; FrameTop*12 -- new frame's byte offset
    tax

    lda.l VmState_Ip
    inc a
    sta.l VmFrames_Wram+VMFRAME_RETURN_IP,x
    lda.l VmPriv_B
    sta.l VmFrames_Wram+VMFRAME_RESULT_SLOT,x
    lda.l VmPriv_C
    sta.l VmFrames_Wram+VMFRAME_CALLSITE_ID,x
    lda #0
    sta.l VmFrames_Wram+VMFRAME_ARG_CURSOR,x
    lda #VMFRAME_RETURN_SRC_EMPTY
    sta.l VmFrames_Wram+VMFRAME_RETURN_SRC,x
    lda #0
    sta.l VmFrames_Wram+VMFRAME_RESERVED,x

    lda.l VmState_FrameTop
    inc a
    sta.l VmState_FrameTop

    lda.l VmPriv_A
    sta.l VmState_Ip
    jmp Vm_Run__loop

; --- Native target: dispatch by stable ID, then store the result (every
; native here returns an INTEGER in VmPriv_LeftLo/Hi on success) into
; CALL's own operand B, exactly like every Gate 2 binary-op handler already
; stores into operand A via Vm_StoreIntResult. ---
Vm_Op_Call__native:
.a8
    rep #$31
.a16
.i16
    lda.l VmCall_TargetId
    cmp #VM_NATIVE_ABS
    beq Vm_Op_Call__native_abs
    cmp #VM_NATIVE_MIN
    beq Vm_Op_Call__native_min
    cmp #VM_NATIVE_MAX
    beq Vm_Op_Call__native_max
    cmp #VM_NATIVE_LOG
    beq Vm_Op_Call__native_log
    cmp #100                        ; Gate 6 engine natives (vm_native_engine.pasm,
    bcs Vm_Op_Call__native_engine   ; bank 1) start at 100 -- see vm_consts.pasm.
                                     ; Collapsed to ONE range check + ONE jsl instead
                                     ; of nine, each with its own cmp/beq/jsl/brl:
                                     ; bank 0's $9000-$AC00 VM window had no room left
                                     ; for nine of those blocks (measured -- the first
                                     ; attempt overlapped LoadAudioData's fixed $AC00
                                     ; org by 46 bytes). The 9-way dispatch itself now
                                     ; lives in bank 1 (Vm_NativeEng_Dispatch), which
                                     ; has real headroom.
    lda #VMERR_BAD_NATIVE
    jmp Vm_Fault

Vm_Op_Call__native_abs:
.a16
    jsr Vm_NativeAbs
    brl Vm_Op_Call__native_done
Vm_Op_Call__native_min:
.a16
    jsr Vm_NativeMin
    brl Vm_Op_Call__native_done
Vm_Op_Call__native_max:
.a16
    jsr Vm_NativeMax
    brl Vm_Op_Call__native_done
Vm_Op_Call__native_log:
.a16
    jsr Vm_NativeLog
    brl Vm_Op_Call__native_done
Vm_Op_Call__native_engine:
.a16
    jsl Vm_NativeEng_Dispatch

Vm_Op_Call__native_done:
.a16
    bcc Vm_Op_Call__native_ok
    jmp Vm_Fault                   ; A (.a16) already holds the VMERR_* code

Vm_Op_Call__native_ok:
.a16
    lda.l VmPriv_B
    sta.l VmPriv_A                 ; Vm_StoreIntResult's dest is VmPriv_A;
                                    ; CALL's own operand A (script entry) is
                                    ; irrelevant on the native path, safe to
                                    ; overwrite.
    jsr Vm_StoreIntResult
    jmp Vm_Next

; ============================================================================
; Vm_Op_Param (opcode 40) -- a=destination slot. Copies the active frame's
; next argument (via its callsite's arg_list_index+arg_cursor) into
; VmPriv_A, then advances arg_cursor. Cursor >= argc: destination cleared to
; EMPTY instead of a fault (plan_vm.md §5's own instruction), cursor still
; advances either way -- keeps every PARAM in a sequence, missing or not, a
; single uniform code path.
; ============================================================================
Vm_Op_Param:
    rep #$31
.a16
.i16
    lda.l VmState_FrameTop
    bne Vm_Op_Param__has_frame
    lda #VMERR_NO_CALL_FRAME
    jmp Vm_Fault

Vm_Op_Param__has_frame:
.a16
    dec a                          ; active frame index = FrameTop-1
    asl a
    asl a
    sta.l VmPriv_RightLo            ; index*4
    lda.l VmState_FrameTop
    dec a
    asl a
    asl a
    asl a                           ; index*8
    clc
    adc.l VmPriv_RightLo             ; index*12 -- frame byte offset
    sta.l VmPriv_RightHi             ; keep it; X gets clobbered below
    tax

    lda.l VmFrames_Wram+VMFRAME_CALLSITE_ID,x
    sta.l VmPriv_LeftLo               ; callsite_id
    lda.l VmFrames_Wram+VMFRAME_ARG_CURSOR,x
    sta.l VmPriv_LeftHi               ; arg_cursor

    ; callsite record byte offset = VmCall_CallsitesOff + callsite_id*12
    lda.l VmPriv_LeftLo
    asl a
    asl a
    sta.l VmArith_CmpLT                ; scratch reuse (vm_arith32.pasm's
                                        ; 2-word compare result cell -- free
                                        ; here, Vm_CompareInt isn't running)
    lda.l VmPriv_LeftLo
    asl a
    asl a
    asl a
    clc
    adc.l VmArith_CmpLT
    clc
    adc.l VmCall_CallsitesOff
    tax

    sep #$20
.a8
    lda.l VmCode_Wram+1,x            ; argc
    rep #$31
.a16
.i16
    and #$00FF
    cmp.l VmPriv_LeftHi               ; argc vs. arg_cursor
    bcc Vm_Op_Param__no_arg           ; argc <= cursor -> exhausted
    beq Vm_Op_Param__no_arg

    lda.l VmCode_Wram+6,x             ; arg_list_index
    clc
    adc.l VmPriv_LeftHi                ; + arg_cursor
    asl a                               ; *2 -- u16 table entries
    clc
    adc.l VmCall_ArgSlotsOff
    tax
    lda.l VmCode_Wram,x                ; argument's slot id
    sta.l VmPriv_B
    jsr Vm_SlotCopy                    ; VmPriv_A (PARAM's own operand,
                                        ; untouched since fetch) <- VmPriv_B
    brl Vm_Op_Param__advance

Vm_Op_Param__no_arg:
.a16
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

Vm_Op_Param__advance:
.a16
    lda.l VmPriv_RightHi               ; frame byte offset, saved above
    tax
    lda.l VmFrames_Wram+VMFRAME_ARG_CURSOR,x
    inc a
    sta.l VmFrames_Wram+VMFRAME_ARG_CURSOR,x
    jmp Vm_Next

; ============================================================================
; Vm_Op_Jumpr (opcode 46) -- a=epilogue target, b=return-value source slot.
; Stages b into the active frame's return_source_slot, then jumps to a.
; ============================================================================
Vm_Op_Jumpr:
    rep #$31
.a16
.i16
    lda.l VmState_FrameTop
    bne Vm_Op_Jumpr__has_frame
    lda #VMERR_NO_CALL_FRAME
    jmp Vm_Fault

Vm_Op_Jumpr__has_frame:
.a16
    dec a
    asl a
    asl a
    sta.l VmPriv_RightLo
    lda.l VmState_FrameTop
    dec a
    asl a
    asl a
    asl a
    clc
    adc.l VmPriv_RightLo
    tax

    lda.l VmPriv_B
    sta.l VmFrames_Wram+VMFRAME_RETURN_SRC,x
    lda.l VmPriv_A
    sta.l VmState_Ip
    jmp Vm_Run__loop

; ============================================================================
; Vm_Op_Ret (opcode 43) -- with an active frame: if JUMPR staged a return
; value, copy it into the caller's result slot, then pop the frame and
; resume at return_ip. Without a frame: root return, VMSTAT_DONE.
; ============================================================================
Vm_Op_Ret:
    rep #$31
.a16
.i16
    lda.l VmState_FrameTop
    bne Vm_Op_Ret__has_frame
    jmp Vm_Done

Vm_Op_Ret__has_frame:
.a16
    dec a
    asl a
    asl a
    sta.l VmPriv_RightLo
    lda.l VmState_FrameTop
    dec a
    asl a
    asl a
    asl a
    clc
    adc.l VmPriv_RightLo
    tax                                  ; X = active frame byte offset

    lda.l VmFrames_Wram+VMFRAME_RETURN_SRC,x
    cmp #VMFRAME_RETURN_SRC_EMPTY
    beq Vm_Op_Ret__no_value

    sta.l VmPriv_B                        ; A unchanged by cmp: source slot
    lda.l VmFrames_Wram+VMFRAME_RESULT_SLOT,x
    sta.l VmPriv_A
    txa
    sta.l VmPriv_RightHi                  ; save frame offset -- Vm_SlotCopy
                                            ; clobbers X
    jsr Vm_SlotCopy
    lda.l VmPriv_RightHi
    tax

Vm_Op_Ret__no_value:
.a16
    lda.l VmFrames_Wram+VMFRAME_RETURN_IP,x
    sta.l VmState_Ip
    lda.l VmState_FrameTop
    dec a
    sta.l VmState_FrameTop
    jmp Vm_Run__loop
