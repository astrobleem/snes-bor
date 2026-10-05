; ============================================================================
; core/vm/vm_run.pasm -- Gate 0 (plan_vm.md §2): fetch, dispatch, integer
; slots, branch, root RET.
;
; Public entry: Vm_Run, called once per frame from scpu_main_loop (deviation
; 1, plan_vm.md §0.2). Vm_Run itself is a no-op once the script has reached a
; terminal state (DONE/FAULT) -- VMSTAT_DONE=4 and VMSTAT_FAULT=5 are the two
; highest values in §0.8's enum specifically so "status >= VMSTAT_DONE" is one
; compare for "already terminal."
;
; The exit contract (plan_vm.md §2, "the single most bug-prone thing at this
; gate"):
;   sequential instruction -> jmp Vm_Next        ; IP += 1, then re-fetch
;   control transfer       -> jmp Vm_Run__loop   ; IP already assigned, re-fetch
;   fault                  -> jmp Vm_Fault        ; A (.a16) holds the VMERR_*
;   cooperative boundary   -> jmp Vm_Run__yield
;   root return            -> jmp Vm_Done
; The plan's own contract table names the control-transfer target "Vm_Run" --
; here that is Vm_Run__loop, the re-fetch continuation. Vm_Run (no suffix) is
; reserved for the once-per-frame jsr entry, which does one-time budget/status
; setup that must not repeat on every single instruction; re-running it every
; instruction would re-arm a full frame's budget every fetch and the
; cooperative yield could never trigger. This is a plan clarification, not a
; deviation -- the actual point of that row ("re-fetch without incrementing
; IP") is exactly what Vm_Run__loop does.
;
; VmState_Ip IS the "current instruction" register throughout -- fetch reads
; it, dispatch runs against what it names, and a fault's ErrorIp is just
; VmState_Ip read back, unmodified since the fetch that produced it. No
; separate "current IP" scratch cell exists or is needed.
;
; Record fetch (deviation 3, plan_vm.md §0.2): X = instructions_offset (cached
; by Vm_LoadSlots into VmPriv_InstrOff) + IP*8, then `lda.l VmCode_Wram,x` per
; field -- never `[ptr],y`, DP is core/oop.pasm's.
;
; Two things this file is careful about because this project has already
; shipped both bugs once:
;   - VmState_Status/VmState_TraceHead/VmState_ErrorOpcode are all single
;     bytes (.db) sitting directly next to other VmState_* fields. Every
;     write to one of them is in `.a8` mode -- a 16-bit write here would
;     silently stomp the following field's low byte.
;   - The 32-bit ADD's carry from low-word to high-word is never preceded by
;     a fresh `clc` between the two `adc`s. A stray `clc` there silently drops
;     the carry (this exact bug shipped once already, Phase 10, README.md).
;
; No `ldx.l`/`ldy.l`/`cpx.l`/`cpy.l` anywhere in this file -- none of those
; addressing modes exist on real 65816, and Poppy hard-errors on them now
; (CLAUDE.md's fixed-bug table). Loading an index register from a WRAM long
; address is always `lda.l Cell` then `tax`, never `ldx.l Cell`.
;
; Global (not @-local) labels; jsr/rts (bank 0); explicit width directive
; after every label (poppy#386, still live -- enforced by
; tools/rom_audit/check_width_directives.py); no nop guards (that bug is
; fixed). Every conditional branch that might be far uses the near-branch-
; to-a-local-trampoline-then-brl shape core/spawn.pasm and vm_load.pasm both
; already use.
; ============================================================================

; --- Private, implementation-detail WRAM. NOT part of §0.8's ABI -- nothing
; outside this file and vm_slots.pasm should reference these, and a later
; gate is free to grow this block (right after VM_STATE_LAST, verified
; collision-free with everything else in the engine). ---
; Base is VM_STATE_LAST ($7FE0AB as of the Gate 1 WRAM-collision relocation --
; see vm_consts.pasm's header note above VmSlots_Wram for why this whole
; block moved out of bank $7F's $0000-$7FFF/$1400-$153F range, which turned
; out to be inside core/stream_cache.pasm's Tile2Slot table) -- kept as a
; literal here, not the equate, to match every other absolute WRAM address in
; this project (CLAUDE.md: plain absolute addresses, never computed from
; another symbol). If VM_STATE_LAST ever moves again, grep this file's own
; header comment plus vm_slots.pasm/vm_load.pasm for `7FE0` before
; renumbering.
VmPriv_Opcode   = $7FE0AB   ; .db  -- current record's opcode byte
VmPriv_Flags    = $7FE0AC   ; .db  -- current record's flags byte (unused, Gate 0)
VmPriv_A        = $7FE0AD   ; .dw  -- current record's operand A
VmPriv_B        = $7FE0AF   ; .dw  -- operand B
VmPriv_C        = $7FE0B1   ; .dw  -- operand C
VmPriv_InstrOff = $7FE0B3   ; .dw  -- cached instructions_offset (vm_slots.pasm)
VmPriv_LeftLo   = $7FE0B5   ; .dw  -- 32-bit binary-op scratch, low/high words
VmPriv_LeftHi   = $7FE0B7   ; .dw
VmPriv_RightLo  = $7FE0B9   ; .dw
VmPriv_RightHi  = $7FE0BB   ; .dw
VmPriv_CopySrc  = $7FE0BD   ; .dw  -- vm_slots.pasm's Vm_LoadSlots copy cursors
VmPriv_CopyDst  = $7FE0BF   ; .dw
VmPriv_CopyLen  = $7FE0C1   ; .dw
; Ends $7FE0C3. vm_load.pasm's own CRC32 scratch (Gate 1) starts there, in
; that file, not here -- see its header note on why it doesn't reuse these.

; Opcodes executed per Vm_Run call before a cooperative yield. Not part of
; §0.8 (a tuning knob, not ABI); 200 matches §0.2's own stated expectation
; ("game-logic scripts run a few hundred opcodes per frame"). Gate 0's 8-
; instruction fixture finishes in the first call regardless of this value, as
; long as it is comfortably above 8, which it is by two orders of magnitude.
VM_BUDGET_PER_FRAME = 200

; ============================================================================
; Vm_Run -- the once-per-frame jsr entry.
; ============================================================================
Vm_Run:
    php
    rep #$31
.a16
.i16
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_DONE
    bcs Vm_Run__noop            ; DONE(4) or FAULT(5): already terminal

    lda #VM_BUDGET_PER_FRAME
    sta.l VmState_Budget
    sep #$20
.a8
    lda #VMSTAT_RUNNING
    sta.l VmState_Status
    bra Vm_Run__loop

Vm_Run__noop:
    plp
    rts

; ============================================================================
; Vm_Run__loop -- the tight fetch/dispatch loop. Re-entered by control-
; transfer handlers (the plan's exit-contract "jmp Vm_Run" is this label --
; see the file header). Never call this with a jsr; it only ever returns via
; Vm_Done/Vm_Fault/Vm_Run__yield's own rts, using the stack frame Vm_Run's
; jsr established.
; ============================================================================
Vm_Run__loop:
    rep #$31
.a16
.i16
    lda.l VmState_Budget
    beq Vm_Run__yield           ; budget already 0: yield WITHOUT decrementing
    dec a
    sta.l VmState_Budget

    jsr Vm_Fetch
    bcc Vm_Run__fetched
    jmp Vm_Fault
Vm_Run__fetched:
.a16
.i16
    jsr Vm_TraceWrite

    sep #$20
.a8
    lda.l VmPriv_Opcode
    cmp #BOR_OPCODE_END
    bcs Vm_Run__loop__bad_opcode
    brl Vm_Dispatch_00

Vm_Run__loop__bad_opcode:
    rep #$31
.a16
.i16
    lda #VMERR_BAD_OPCODE
    jmp Vm_Fault

Vm_Run__yield:
    sep #$20
.a8
    lda #VMSTAT_YIELDED
    sta.l VmState_Status
    plp
    rts

; ============================================================================
; Vm_Fetch -- IP bounds check, then the 8-byte record into VmPriv_Opcode/
; Flags/A/B/C. Fetch returns carry SET/A=error on failure; the dispatch loop
; then faults with only Vm_Run's own saved P/return address on its stack.
; ============================================================================
Vm_Fetch:
.a16
.i16
    jsl Vm_FetchSource
    rts

; ============================================================================
; Vm_TraceWrite -- append (VmState_Ip, VmPriv_Opcode) to the 32-entry ring at
; VmTrace_Wram, before dispatch (plan_vm.md §2: "so a faulting instruction
; appears in its own trace").
; ============================================================================
Vm_TraceWrite:
    php
    sep #$20
.a8
    lda.l VmState_TraceHead     ; single byte -- must not touch InstrCount
                                 ; right after it, hence .a8 here specifically.
    rep #$31
.a16
.i16
    and #$00FF                  ; zero-extend (an 8-bit load leaves the high
                                 ; byte of A stale, not zeroed)
    asl a
    asl a                       ; TraceHead * 4 (entry byte offset)
    tax

    lda.l VmState_Ip
    sta.l VmTrace_Wram+0,x      ; +0 u16 IP

    sep #$20
.a8
    lda.l VmPriv_Opcode
    sta.l VmTrace_Wram+2,x      ; +2 u8 opcode
    lda #0
    sta.l VmTrace_Wram+3,x      ; +3 u8 reserved

    lda.l VmState_TraceHead
    inc a
    and #$1F                    ; wrap 0..31 (32 entries, power of 2)
    sta.l VmState_TraceHead

    plp
    rts

; ============================================================================
; Explicit dispatcher. One cmp/bne/jmp per ABI opcode value, 0..47, exactly
; the scaffold's shape (plan_vm.md §2: "Do not build a jump table yet"). All
; in .a8 mode -- the opcode never exceeds 255. Values not implemented at this
; gate all jump to the single shared Vm_Op_Unimplemented, rather than each
; getting its own placeholder stub -- smaller, and Gate 1 (§3) is where most
; of these get filled in anyway.
; ============================================================================
Vm_Dispatch_00:
.a8
    cmp #BOR_OP_CONSTSTR
    bne Vm_Dispatch_01
    jmp Vm_Op_Noop
Vm_Dispatch_01:
.a8
    cmp #BOR_OP_CONSTDBL
    bne Vm_Dispatch_02
    jmp Vm_Op_Noop
Vm_Dispatch_02:
.a8
    cmp #BOR_OP_CONSTINT
    bne Vm_Dispatch_03
    jmp Vm_Op_ConstInt
Vm_Dispatch_03:
.a8
    cmp #BOR_OP_LOAD
    bne Vm_Dispatch_04
    jmp Vm_Op_Load
Vm_Dispatch_04:
.a8
    cmp #BOR_OP_SAVE
    bne Vm_Dispatch_05
    jmp Vm_Op_Save
Vm_Dispatch_05:
.a8
    cmp #BOR_OP_INC
    bne Vm_Dispatch_06
    jmp Vm_Op_Inc
Vm_Dispatch_06:
.a8
    cmp #BOR_OP_DEC
    bne Vm_Dispatch_07
    jmp Vm_Op_Dec
Vm_Dispatch_07:
.a8
    cmp #BOR_OP_FIELD
    bne Vm_Dispatch_08
    jmp Vm_Op_Field
Vm_Dispatch_08:
.a8
    cmp #BOR_OP_CALL
    bne Vm_Dispatch_09
    jmp Vm_Op_Call
Vm_Dispatch_09:
.a8
    cmp #BOR_OP_POS
    bne Vm_Dispatch_10
    jmp Vm_Op_Pos
Vm_Dispatch_10:
.a8
    cmp #BOR_OP_NEG
    bne Vm_Dispatch_11
    jmp Vm_Op_Neg
Vm_Dispatch_11:
.a8
    cmp #BOR_OP_NOT
    bne Vm_Dispatch_12
    jmp Vm_Op_Not
Vm_Dispatch_12:
.a8
    cmp #BOR_OP_MUL
    bne Vm_Dispatch_13
    jmp Vm_Op_Mul
Vm_Dispatch_13:
.a8
    cmp #BOR_OP_DIV
    bne Vm_Dispatch_14
    jmp Vm_Op_Div
Vm_Dispatch_14:
.a8
    cmp #BOR_OP_MOD
    bne Vm_Dispatch_15
    jmp Vm_Op_Mod
Vm_Dispatch_15:
.a8
    cmp #BOR_OP_ERR
    bne Vm_Dispatch_16
    jmp Vm_Op_Err
Vm_Dispatch_16:
.a8
    cmp #BOR_OP_ADD
    bne Vm_Dispatch_17
    jmp Vm_Op_Add
Vm_Dispatch_17:
.a8
    cmp #BOR_OP_SUB
    bne Vm_Dispatch_18
    jmp Vm_Op_Sub
Vm_Dispatch_18:
.a8
    cmp #BOR_OP_SHL
    bne Vm_Dispatch_19
    jmp Vm_Op_Shl
Vm_Dispatch_19:
.a8
    cmp #BOR_OP_SHR
    bne Vm_Dispatch_20
    jmp Vm_Op_Shr
Vm_Dispatch_20:
.a8
    cmp #BOR_OP_JUMP
    bne Vm_Dispatch_21
    jmp Vm_Op_Jump
Vm_Dispatch_21:
.a8
    cmp #BOR_OP_PJUMP
    bne Vm_Dispatch_22
    jmp Vm_Op_Jump              ; PJUMP (21): identical runtime effect to
                                 ; JUMP after host linking (opcode_manifest.csv)
Vm_Dispatch_22:
.a8
    cmp #BOR_OP_GE
    bne Vm_Dispatch_23
    jmp Vm_Op_Ge
Vm_Dispatch_23:
.a8
    cmp #BOR_OP_LE
    bne Vm_Dispatch_24
    jmp Vm_Op_Le
Vm_Dispatch_24:
.a8
    cmp #BOR_OP_LT
    bne Vm_Dispatch_25
    jmp Vm_Op_Lt
Vm_Dispatch_25:
.a8
    cmp #BOR_OP_GT
    bne Vm_Dispatch_26
    jmp Vm_Op_Gt
Vm_Dispatch_26:
.a8
    cmp #BOR_OP_EQ
    bne Vm_Dispatch_27
    jmp Vm_Op_Eq
Vm_Dispatch_27:
.a8
    cmp #BOR_OP_NE
    bne Vm_Dispatch_28
    jmp Vm_Op_Ne
Vm_Dispatch_28:
.a8
    cmp #BOR_OP_OR
    bne Vm_Dispatch_29
    jmp Vm_Op_Or
Vm_Dispatch_29:
.a8
    cmp #BOR_OP_AND
    bne Vm_Dispatch_30
    jmp Vm_Op_And
Vm_Dispatch_30:
.a8
    cmp #BOR_OP_BIT_OR
    bne Vm_Dispatch_31
    jmp Vm_Op_BitOr
Vm_Dispatch_31:
.a8
    cmp #BOR_OP_XOR
    bne Vm_Dispatch_32
    jmp Vm_Op_Xor
Vm_Dispatch_32:
.a8
    cmp #BOR_OP_BIT_AND
    bne Vm_Dispatch_33
    jmp Vm_Op_BitAnd
Vm_Dispatch_33:
.a8
    cmp #BOR_OP_NOOP
    bne Vm_Dispatch_34
    jmp Vm_Op_Noop
Vm_Dispatch_34:
.a8
    cmp #BOR_OP_PUSH
    bne Vm_Dispatch_35
    jmp Vm_Op_Noop
Vm_Dispatch_35:
.a8
    cmp #BOR_OP_POP
    bne Vm_Dispatch_36
    jmp Vm_Op_Noop
Vm_Dispatch_36:
.a8
    cmp #BOR_OP_BRANCH_FALSE
    bne Vm_Dispatch_37
    jmp Vm_Op_BranchFalse
Vm_Dispatch_37:
.a8
    cmp #BOR_OP_BRANCH_TRUE
    bne Vm_Dispatch_38
    jmp Vm_Op_BranchTrue
Vm_Dispatch_38:
.a8
    cmp #BOR_OP_BRANCH_EQUAL
    bne Vm_Dispatch_39
    jmp Vm_Op_BranchEqual
Vm_Dispatch_39:
.a8
    cmp #BOR_OP_DATA
    bne Vm_Dispatch_40
    jmp Vm_Op_Noop
Vm_Dispatch_40:
.a8
    cmp #BOR_OP_PARAM
    bne Vm_Dispatch_41
    jmp Vm_Op_Param
Vm_Dispatch_41:
.a8
    cmp #BOR_OP_IMMEDIATE
    bne Vm_Dispatch_42
    jmp Vm_Op_Noop
Vm_Dispatch_42:
.a8
    cmp #BOR_OP_DEFERRED
    bne Vm_Dispatch_43
    jmp Vm_Op_Noop
Vm_Dispatch_43:
.a8
    cmp #BOR_OP_RET
    bne Vm_Dispatch_44
    jmp Vm_Op_Ret
Vm_Dispatch_44:
.a8
    cmp #BOR_OP_CHECKARG
    bne Vm_Dispatch_45
    jmp Vm_Op_Noop
Vm_Dispatch_45:
.a8
    cmp #BOR_OP_CLEAN
    bne Vm_Dispatch_46
    jmp Vm_Op_Noop
Vm_Dispatch_46:
.a8
    cmp #BOR_OP_JUMPR
    bne Vm_Dispatch_47
    jmp Vm_Op_Jumpr
Vm_Dispatch_47:
.a8
    cmp #BOR_OP_FUNCDECL
    bne Vm_Op_Unimplemented     ; dead: every value 0..46 already matched
                                 ; above, so only 47 itself can reach here --
                                 ; kept as a defensive fallback, not a live path
    jmp Vm_Op_Noop

; ============================================================================
; Shared exits.
; ============================================================================
Vm_Next:
    rep #$31
.a16
.i16
    lda.l VmState_Ip
    inc a
    sta.l VmState_Ip
    jmp Vm_Run__loop

Vm_Done:
    sep #$20
.a8
    lda #VMSTAT_DONE
    sta.l VmState_Status
    plp
    rts

; Entry contract: A (16-bit, `.a16` already active) holds the VMERR_* code.
; VmState_Ip already names the faulting instruction (fetch stored it there;
; no handler advances it before reaching here) and VmPriv_Opcode already
; holds its opcode -- neither is threaded through as a parameter.
Vm_Fault:
    sta.l VmState_Error
    lda.l VmState_Ip
    sta.l VmState_ErrorIp
    lda.l VmPriv_A
    sta.l VmState_ErrorA
    lda.l VmPriv_B
    sta.l VmState_ErrorB
    lda.l VmPriv_C
    sta.l VmState_ErrorC
    sep #$20
.a8
    lda.l VmPriv_Opcode
    sta.l VmState_ErrorOpcode
    lda #VMSTAT_FAULT
    sta.l VmState_Status
    plp
    rts

; ============================================================================
; Opcode handlers.
; ============================================================================

; CONSTINT -- constants are prelinked into the initial slot image (Gate 0
; fixture's initial_slots already carries the CONSTINT values); the record is
; a runtime no-op.
Vm_Op_ConstInt:
    jmp Vm_Next

Vm_Op_Noop:
    jmp Vm_Next

Vm_Op_Field:
    rep #$31
.a16
.i16
    lda #VMERR_FIELD_OPCODE
    jmp Vm_Fault

Vm_Op_Err:
    rep #$31
.a16
.i16
    lda #VMERR_EXPLICIT_ERR
    jmp Vm_Fault

Vm_Op_Unimplemented:
    rep #$31
.a16
.i16
    lda #VMERR_UNIMPLEMENTED
    jmp Vm_Fault

; JUMP -- assign IP, do not fall through to the increment. The target is not
; separately range-checked here: Vm_Fetch re-validates IP < instruction_count
; on the very next fetch and faults VMERR_BAD_JUMP there if it is not, so a
; second check here would just duplicate that one.
Vm_Op_Jump:
    rep #$31
.a16
.i16
    lda.l VmPriv_A
    sta.l VmState_Ip
    jmp Vm_Run__loop

; RET -- real call-frame-aware implementation is vm_call.pasm's Vm_Op_Ret
; (Gate 3, plan_vm.md §5). The Gate 0 stub that lived here (every RET is a
; root return, since CALL was VMERR_UNIMPLEMENTED and VmState_FrameTop could
; never become nonzero) is gone now that CALL is real.

; Branch_FALSE -- VM truthiness (Vm_TruthySlot, vm_arith32.pasm -- Gate 4
; extends it to INTEGER-nonzero-or-STR-nonempty, see that file's own header
; note); never a fault, matching this handler's own long-standing precedent
; (this file's header note on gate0_program.json's reference oracle, which
; treats a falsy condition as "branch taken", not VMERR_BAD_TYPE).
; a = branch target if false; b = condition slot.
Vm_Op_BranchFalse:
    rep #$31
.a16
.i16
    lda.l VmPriv_B
    jsr Vm_TruthySlot
    cmp #0                        ; Vm_TruthySlot's own `plp` restores the
                                    ; flags that were live at ITS entry, not
                                    ; ones reflecting the value it returns in
                                    ; A -- an explicit cmp is required here,
                                    ; never branch on flags surviving a jsr
    bne Vm_Op_BranchFalse__not_taken

    lda.l VmPriv_A
    sta.l VmState_Ip
    jmp Vm_Run__loop

Vm_Op_BranchFalse__not_taken:
.a16
.i16
    jmp Vm_Next

; Branch_TRUE (Gate 1, plan_vm.md 3) -- the mirror image of Branch_FALSE:
; same VM truthiness, opposite direction, never a fault. a = branch target
; if true; b = condition slot.
Vm_Op_BranchTrue:
    rep #$31
.a16
.i16
    lda.l VmPriv_B
    jsr Vm_TruthySlot
    cmp #0                        ; see Branch_FALSE's own note just above:
                                    ; Vm_TruthySlot's `plp` does not leave
                                    ; flags reflecting its returned value
    beq Vm_Op_BranchTrue__not_taken

    lda.l VmPriv_A
    sta.l VmState_Ip
    jmp Vm_Run__loop

Vm_Op_BranchTrue__not_taken:
.a16
.i16
    jmp Vm_Next

; Branch_EQUAL (Gate 1, plan_vm.md 3) -- branches when left and right are
; type-equal AND value-equal. Unlike ADD/EQ (INTEGER-only-or-VMERR_BAD_TYPE,
; plan_vm.md 2), the manifest does not restrict this opcode's family to
; INTEGER, so a type mismatch is simply "not equal" (Branch_FALSE/TRUE's own
; non-INTEGER-is-falsy precedent), never a fault. a = branch target if equal;
; b = left slot; c = right slot.
Vm_Op_BranchEqual:
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
    sta.l VmPriv_LeftLo           ; left TYPE (scratch reuse -- this handler
                                   ; owns VmPriv_Left*/Right* exclusively for
                                   ; its own duration, same as ADD/EQ do)
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmPriv_LeftHi           ; left VALUE low word (scratch reuse)
    lda.l VmSlots_Wram+6,x
    sta.l VmPriv_RightLo          ; left VALUE high word (scratch reuse)

    lda.l VmPriv_C
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp.l VmPriv_LeftLo
    bne Vm_Op_BranchEqual__not_taken   ; type mismatch -> not equal
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    cmp.l VmPriv_LeftHi
    bne Vm_Op_BranchEqual__not_taken
    lda.l VmSlots_Wram+6,x
    cmp.l VmPriv_RightLo
    bne Vm_Op_BranchEqual__not_taken

    lda.l VmPriv_A
    sta.l VmState_Ip
    jmp Vm_Run__loop

Vm_Op_BranchEqual__not_taken:
    rep #$31
.a16
.i16
    jmp Vm_Next

; ADD -- numeric addition (INTEGER pair, DECIMAL pair, or mixed -- Gate 5,
; plan_vm.md §7: routed through vm_dec16.pasm's Vm_LoadBinaryNumeric/
; Vm_StoreNumericResult exactly like SUB, since Q16.16 addition is bit-
; identical to INTEGER addition -- both operands are already scaled by the
; same 65536 factor once promoted, so the raw 32-bit add/carry-propagate
; below needs no scaling correction), or STR concatenation when BOTH
; operands are STR (Gate 4, plan_vm.md §6 / opcode_manifest.csv: "or string
; concatenation when either operand is a string"). A STR paired with a
; non-STR (INTEGER/DECIMAL/PTR/EMPTY) still faults VMERR_BAD_TYPE rather
; than coercing the numeric side to text -- Gate 4's header comment
; deferred that formatting step to "Gate 5's decimal-to-string work";
; Gate 5 built and fixtures the formatter itself (vm_dec16_heavy.pasm's
; Vm_Dec_FormatSlot, bank 1) but wiring it into ADD overflowed this file's
; $9000-$AC00 budget by ~166 bytes (vm_dec16.pasm's own header has the
; measurement) -- deferred to Gate 6 as a documented, budget-forced scope
; decision, not an oversight (same precedent as NEG's non-INTEGER case).
; a = dest slot, b = left slot, c = right slot.
Vm_Op_Add:
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
    sta.l VmPriv_LeftLo           ; scratch reuse: left TYPE byte (Branch_
                                    ; EQUAL's own precedent for this trick)

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
    bne Vm_Op_Add__right_not_str
    ; right IS STR
    lda.l VmPriv_LeftLo
    cmp #BOR_VT_STR
    beq Vm_Op_Add__concat
    brl Vm_Op_Add__to_bad_type     ; right STR, left not STR -> fault

Vm_Op_Add__right_not_str:
.a8
    ; right is NOT STR
    lda.l VmPriv_LeftLo
    cmp #BOR_VT_STR
    bne Vm_Op_Add__right_not_str__left_not_str
    brl Vm_Op_Add__to_bad_type     ; left STR, right not STR -> fault

Vm_Op_Add__right_not_str__left_not_str:
.a8
    ; neither operand is STR -- both must be numeric (any INTEGER/DECIMAL
    ; pairing), via the same Vm_LoadBinaryNumeric every other Gate 5
    ; arithmetic op uses (replaces the old INTEGER-only double type check).
    rep #$31
.a16
.i16
    jsr Vm_LoadBinaryNumeric
    bcc Vm_Op_Add__numeric_path
    brl Vm_Op_Add__to_bad_type

Vm_Op_Add__concat:
.a8
    rep #$31
.a16
.i16
    jsr Vm_Str_ConcatOp
    bcc Vm_Op_Add__concat_ok
    jmp Vm_Fault                  ; A (.a16) already holds the VMERR_* code

Vm_Op_Add__concat_ok:
.a16
.i16
    jmp Vm_Next

Vm_Op_Add__numeric_path:
.a16
.i16
    ; 32-bit add: low half, then high half, carry propagates. Deliberately no
    ; `clc` between the two `adc`s -- that dropped-carry bug shipped once
    ; already (Phase 10, README.md) and is exactly what a "just be safe and
    ; clc every add" reflex would reintroduce here.
    clc
    lda.l VmPriv_LeftLo
    adc.l VmPriv_RightLo
    sta.l VmPriv_LeftLo
    lda.l VmPriv_LeftHi
    adc.l VmPriv_RightHi
    sta.l VmPriv_LeftHi
    jsr Vm_StoreNumericResult
    jmp Vm_Next

Vm_Op_Add__to_bad_type:
.a16
.i16
    jml Vm_SourceVariantAddFallback

; EQ -- INTEGER pair or STR pair (Gate 4, plan_vm.md §6 extends Gate 0's
; INTEGER-only rule the same way GE/LE/LT/GT/NE do -- see vm_arith32.pasm's
; own header note above those handlers); result is INTEGER 0/1. a = dest
; slot, b = left slot, c = right slot. Vm_LoadAndCompare/Vm_CompareInt/
; Vm_StoreIntResult are all defined later in vm_arith32.pasm/vm_string.pasm
; (.include'd after this file) -- the same cross-file forward reference
; vm_arith32.pasm's own header already documents and relies on.
Vm_Op_Eq:
    jsr Vm_LoadAndCompare
    bcc Vm_Op_Eq__ok
    brl Vm_Op_Eq__to_bad_type

Vm_Op_Eq__ok:
.a8
    rep #$31
.a16
.i16
    lda.l VmArith_CmpEQ
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    jsr Vm_StoreIntResult
    jmp Vm_Next

Vm_Op_Eq__to_bad_type:
    rep #$31
.a16
.i16
    lda #VMERR_BAD_TYPE
    jmp Vm_Fault
