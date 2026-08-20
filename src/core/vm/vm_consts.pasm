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
VmGuardLo       = $7EE000   ; 16 B of $A5, ends $7EE00F

; --- Gate 1 (plan_vm.md 3) WRAM-collision fix -----------------------------
; Everything below USED to live at $7EE010/$7F01xx/$7F14xx/$7F15xx. That
; entire span is inside core/stream_cache.pasm's StreamCache_Tile2Slot table
; ($7F0000-$7F7FFF, a full 32KB tile-ID->VRAM-slot array) -- this file's own
; grep-based "confirmed unused" claims never covered bank $7F because nobody
; re-grepped stream_cache.pasm's header comment against the VM's addresses
; when the VM's WRAM map was first written. This is a real, independent
; latent bug -- found while investigating a tools/verify/phase9.py failure,
; but NOT what was actually causing that failure (relocating every address
; here reproduced phase9's failure identically; see vm_load.pasm's own note
; for the real cause, a harness timing-margin issue, fixed separately in
; phase9.py itself). Worth fixing regardless: Gate 3's still-unimplemented
; VmFrames_Wram (768B) and Gate 4's VmStrPool_Wram (4096B) would have
; written deep into Tile2Slot's live entries once built.
;
; New home: $7FC000-$7FFFFF (16 KB). Grep-confirmed free as of Gate 1 --
; stream_cache.pasm's own tables end at $7F8BFE, StreamScroll_TileBufN/
; StreamScrollFp_TileBufN occupy $7F9000-$7F911F, and stream_cache_fp.pasm's
; tables end at $7FB8FF (main.pasm:3096, stream_cache_fp.pasm:60-65) --
; nothing references $7FC000+ anywhere in src/. VmSlots_Wram moved here too
; (its old base spilled 16 bytes into Tile2Slot's own first entries) rather
; than just shrinking the gap after VmGuardLo, so Code/GuardLo can stay
; exactly where they are (proven collision-free, zero risk) and everything
; that touches the tile cache moves together as one block with headroom for
; Gate 3/4's still-unimplemented Frames/StrPool reservations.
; ----------------------------------------------------------------------------
VmSlots_Wram    = $7FC000   ; 1024 slots x 8 B = 8192 B, ends $7FDFFF
VmGuardHi       = $7FE000   ; 16 B of $5A, ends $7FE00F
VmTrace_Wram    = $7FE010   ; 32 x 4 B = 128 B, ends $7FE08F           (Gate 0)
VM_GUARD_LEN    = 16
VM_GUARD_LO_FILL = $A5
VM_GUARD_HI_FILL = $5A
VM_CODE_MAX      = 32768
VM_INSTR_MAX     = 4096
VM_SLOT_MAX      = 1024

; --- VmState_* scalars. One per line, plain absolute addresses, exactly like
; core/spawn.pasm's Spawn_Index / Spawn_Scratch* block. Base is VmTrace_Wram's
; end ($7FE090, see the relocation note above VmSlots_Wram) -- kept as a
; literal here, not the equate, matching this file's own established style
; (vm_run.pasm/vm_load.pasm do the same for VmPriv_*/VmLoad_Crc*). ---
VmState_Status      = $7FE090   ; .db -- VMSTAT_*
VmState_Error       = $7FE091   ; .dw -- VMERR_*
VmState_Ip          = $7FE093   ; .dw -- current instruction index
VmState_ErrorIp     = $7FE095   ; .dw -- IP at time of fault
VmState_ErrorOpcode = $7FE097   ; .db -- opcode at time of fault
VmState_Budget      = $7FE098   ; .dw -- opcodes remaining this frame
VmState_FrameTop    = $7FE09A   ; .dw -- call-frame depth (Gate 3). Also
                                 ; doubles as the fault-time frame-depth
                                 ; capture plan_vm.md 3 asks for: nothing
                                 ; mutates it after a fault (Vm_Run__noop
                                 ; early-exits once status >= VMSTAT_DONE), so
                                 ; a dedicated VmState_ErrorFrameTop would be
                                 ; a redundant snapshot of a cell that is
                                 ; already frozen by the time anything reads
                                 ; it.
VmState_TraceHead   = $7FE09C   ; .db -- trace ring write index  (Gate 0)
VmState_InstrCount  = $7FE09D   ; .dw -- copied from header at load
VmState_SlotCount   = $7FE09F   ; .dw -- copied from header at load
VmState_Scratch0    = $7FE0A1   ; .dw
VmState_Scratch1    = $7FE0A3   ; .dw
; --- Gate 1 (plan_vm.md 3): full fault capture also wants the failing
; record's operands, not just its IP/opcode. VmPriv_A/B/C (vm_run.pasm) are
; overwritten by the very next fetch, so a resumed/retried run would lose
; them without this snapshot. ---
VmState_ErrorA      = $7FE0A5   ; .dw -- operand A at time of fault
VmState_ErrorB      = $7FE0A7   ; .dw -- operand B at time of fault
VmState_ErrorC      = $7FE0A9   ; .dw -- operand C at time of fault
VM_STATE_FIRST      = $7FE090
VM_STATE_LAST       = $7FE0AB   ; exclusive -- zero [FIRST,LAST) at boot

; Gate 3/4 reservations -- placed here, well clear of VmPriv_*/VmLoad_Crc*/
; VmArith_* below (which end $7FE0ED, see vm_arith32.pasm's own header), with
; headroom inside the same relocated $7FC000-$7FFFFF block.
VmFrames_Wram   = $7FE100   ; 64 frames x 12 B = 768 B, ends $7FE3FF   (Gate 3)
VmStrPool_Wram  = $7FE400   ; 4096 B string pool, ends $7FF3FF         (Gate 4)

; --- Gate 3 (plan_vm.md §5): call model protocol constants. Frame layout
; matches the bootstrap package's README §7 `BorCallFrame` (12 B, u16 x 6),
; deviation 1 (plain WRAM, not BW-RAM) already noted elsewhere in this repo.
; Callsite record layout matches FORMAT.md's "Callsite table" section (12 B).
; vm_call.pasm's own header has the full field-by-field walkthrough. ---
VM_FRAME_SIZE        = 12
VM_FRAME_MAX         = 64      ; matches VmFrames_Wram's 64-frame reservation
VMFRAME_RETURN_IP    = 0       ; .dw offset within one frame record
VMFRAME_RESULT_SLOT  = 2       ; .dw -- caller_result_slot
VMFRAME_CALLSITE_ID  = 4       ; .dw
VMFRAME_ARG_CURSOR   = 6       ; .dw
VMFRAME_RETURN_SRC   = 8       ; .dw -- $FFFF sentinel until JUMPR stages one
VMFRAME_RESERVED     = 10      ; .dw
VMFRAME_RETURN_SRC_EMPTY = $FFFF

VM_CALLSITE_SIZE      = 12
VM_TARGET_KIND_SCRIPT = 0
VM_TARGET_KIND_IMPORT = 1       ; normalized to an instruction index at
                                 ; export time (FORMAT.md normalization
                                 ; rule 2) -- identical runtime handling to
                                 ; VM_TARGET_KIND_SCRIPT, same precedent as
                                 ; JUMP/PJUMP in vm_run.pasm.
VM_TARGET_KIND_NATIVE = 2

; Native function IDs. Gate 3 scope only (plan_vm.md §5): "a minimal native
; function table with abs, min, max, and a test-logging function." Stable
; and host-generated per the package's own ABI rule -- these four are hand-
; assigned here because no real exporter exists yet (that's Gate 6); a real
; exporter must treat these as already-reserved values, never renumber them
; out from under a module that references them.
VM_NATIVE_ABS = 1
VM_NATIVE_MIN = 2
VM_NATIVE_MAX = 3
VM_NATIVE_LOG = 4
