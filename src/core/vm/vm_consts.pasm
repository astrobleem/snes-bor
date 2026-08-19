; ============================================================================
; core/vm/vm_consts.pasm -- VM status codes, fault codes, and WRAM map.
; Equates only, no code. .include'd FIRST inside main.pasm's .org $9000 block
; so every later vm/*.pasm file sees these names.
;
; If main.pasm itself ever needs one of these, move that single constant to
; main.pasm ABOVE its .org $C100 include block instead -- main.pasm has twice
; been bitten by a constant used textually before the .include that defined it
; (see its own notes near "declared here, textually before core/nmi.pasm's
; .include").
; ============================================================================

; --- Status. Held in VmState_Status as ONE byte. ---
; UNINIT is deliberately 0 so that "boot zeroed this WRAM and the loader never
; ran" is distinguishable from "the loader ran and succeeded". Never renumber
; READY to 0.
VMSTAT_UNINIT   = 0
VMSTAT_READY    = 1
VMSTAT_RUNNING  = 2
VMSTAT_YIELDED  = 3
VMSTAT_DONE     = 4
VMSTAT_FAULT    = 5

; --- Fault codes. Held in VmState_Error as a 16-bit word.
; $0001-$000F are the bootstrap package's own recommended values (its README
; section 9) -- do not renumber them, the gate fixtures use them.
VMERR_NONE            = $0000
VMERR_BAD_OPCODE      = $0001   ; opcode value >= 48
VMERR_FIELD_OPCODE    = $0002   ; opcode 7 (FIELD) -- always a fault, never a no-op
VMERR_EXPLICIT_ERR    = $0003   ; opcode 15 (ERR)
VMERR_BAD_SLOT        = $0004
VMERR_BAD_TYPE        = $0005
VMERR_DIV_ZERO        = $0006
VMERR_CALL_DEPTH      = $0007
VMERR_NO_CALL_FRAME   = $0008
VMERR_BAD_CALLSITE    = $0009
VMERR_BAD_NATIVE      = $000A
VMERR_STRING_POOL     = $000B
VMERR_STRING_OVERFLOW = $000C
VMERR_BAD_JUMP        = $000D   ; IP outside 0..instruction_count-1
VMERR_BAD_MODULE      = $000E   ; header validation failed (Gate 0a)
VMERR_BUDGET_PROTOCOL = $000F   ; opcode budget exhausted without a yield
VMERR_UNIMPLEMENTED   = $0010   ; opcode is a VALID ABI value but this gate
                                ; has not implemented it yet. See the note
                                ; below -- this is NOT the same as $0001.

; --- WRAM map (plan_vm.md 0.4). Absolute addresses, never Direct Page.
; End addresses are written out on purpose -- see 0.4's note about the guard
; region that was originally placed inside the slot array. ---
VmCode_Wram     = $7E6000   ; 32768 B, ends $7EDFFF
VmGuardLo       = $7EE000   ; 16 B of $A5
VmSlots_Wram    = $7EE010   ; 1024 slots x 8 B = 8192 B, ends $7F000F
VmFrames_Wram   = $7F0100   ; 64 frames x 12 B = 768 B   (Gate 3)
VmStrPool_Wram  = $7F0400   ; 4096 B string pool         (Gate 4)
VmTrace_Wram    = $7F1400   ; 32 x 4 B = 128 B           (Gate 0)
VmGuardHi       = $7F1480   ; 16 B of $5A
VM_GUARD_LEN    = 16
VM_GUARD_LO_FILL = $A5
VM_GUARD_HI_FILL = $5A
VM_CODE_MAX      = 32768
VM_INSTR_MAX     = 4096
VM_SLOT_MAX      = 1024

; --- VmState_* scalars. One per line, plain absolute addresses, exactly like
; core/spawn.pasm's Spawn_Index / Spawn_Scratch* block. ---
VmState_Status      = $7F1500   ; .db -- VMSTAT_*
VmState_Error       = $7F1501   ; .dw -- VMERR_*
VmState_Ip          = $7F1503   ; .dw -- current instruction index
VmState_ErrorIp     = $7F1505   ; .dw -- IP at time of fault
VmState_ErrorOpcode = $7F1507   ; .db -- opcode at time of fault
VmState_Budget      = $7F1508   ; .dw -- opcodes remaining this frame
VmState_FrameTop    = $7F150A   ; .dw -- call-frame depth        (Gate 3)
VmState_TraceHead   = $7F150C   ; .db -- trace ring write index  (Gate 0)
VmState_InstrCount  = $7F150D   ; .dw -- copied from header at load
VmState_SlotCount   = $7F150F   ; .dw -- copied from header at load
VmState_Scratch0    = $7F1511   ; .dw
VmState_Scratch1    = $7F1513   ; .dw
VM_STATE_FIRST      = $7F1500
VM_STATE_LAST       = $7F1515   ; exclusive -- zero [FIRST,LAST) at boot
