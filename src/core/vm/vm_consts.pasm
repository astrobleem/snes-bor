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

; Gate 6 (plan_vm.md §8): the 6 real engine-facing natives SPAWN000.C uses,
; specialized to one stable ID per (function, compile-time property-string)
; pair by the exporter (tools/bor_converter/openbor_script/natives.py) --
; see that file's module docstring and core/vm/vm_native_engine.pasm's own
; header for why. IDs start at 100 to leave headroom below Gate 3's 1-4
; range for any future hand-assigned test native.
VM_NATIVE_GETLOCALVAR_SELF        = 100
VM_NATIVE_GETENTITYPROP_X         = 101
VM_NATIVE_GETENTITYPROP_A         = 102
VM_NATIVE_GETENTITYPROP_Z         = 103
VM_NATIVE_GETENTITYPROP_DIRECTION = 104
VM_NATIVE_CLEARSPAWNENTRY         = 105
VM_NATIVE_SETSPAWNENTRY_NAME      = 106
VM_NATIVE_SPAWN                   = 107
VM_NATIVE_CHANGEENTITYPROP_POSITION = 108

; --- Gate 4 (plan_vm.md §6): dynamic string pool layout. Fixed-size slab
; carved out of VmStrPool_Wram (4096 B, above): 64 objects x 64 bytes.
; Object layout, relative to VmStrPool_Wram + index*VMSTRPOOL_OBJ_SIZE:
;   +0  .db refcount   -- 0 means the object is free (Vm_Str_Alloc scans for
;                          this; reaching 0 via release is what frees it --
;                          no separate free-list, no data wipe needed)
;   +1  .db length      -- 0..VMSTRPOOL_MAX_LEN
;   +2  .. data bytes, up to VMSTRPOOL_MAX_LEN
; A STR slot's value field (vm_slots.pasm's 8-byte record, +4 u32) is a
; handle: high word bit15 SET means the low word is a VmStrPool_Wram object
; index (a dynamic string); bit15 CLEAR means the low word is an index into
; the module's own interned-string table (FORMAT.md "Interned strings"), a
; ROM string. This mirrors FORMAT.md's own handle rule (bit31 of the full
; 32-bit value) split across this project's Lo/Hi-word convention. ---
VMSTRPOOL_OBJ_SIZE  = 64
VMSTRPOOL_OBJ_COUNT = 64      ; 64 x 64 = 4096 = VmStrPool_Wram's full reservation
VMSTRPOOL_MAX_LEN   = 62      ; OBJ_SIZE minus the 2-byte refcount/length header
VMSTR_DYNAMIC_HI    = $8000   ; value high word when the low word is a pool index

; --- Gate 5 (plan_vm.md §7): Q16.16 decimals. New WRAM scratch region --
; grep-confirmed free 2026-08-20 (nothing under src/ references $7FF4A1 or
; higher; vm_string.pasm's own scratch is the highest prior user, ending
; $7FF4A1 exactly -- see that file's header). Kept entirely separate from
; vm_arith32.pasm's VmArith_* cells (which stay INTEGER-only, Gate 2) rather
; than reused, since Vm_Dec_Q16Mul/Q16DivSigned below are bank-1 routines
; (see the note on VM_DEC_BANK) with their OWN self-contained 16x16->32
; multiply / restoring-division primitives -- reusing Core_Math_Mul or
; Vm_DivMod32Unsigned from bank 1 would require converting those routines'
; `rts` to `rtl` (breaking their existing same-bank `jsr` callers' stack
; balance), which is out of scope for this gate; duplicating the small
; primitives locally in bank 1 avoids that risk entirely. ---
VmDec_ResultIsDec = $7FF4A1   ; .db -- 0 = pure-INTEGER path (Vm_LoadBinaryNumeric
                                ; left both operand values untouched), 1 = at
                                ; least one operand was DECIMAL (both operand
                                ; values are now Q16.16-promoted); consumed by
                                ; Vm_StoreNumericResult to pick the result's
                                ; VT_* tag.
VmDec_LLhi        = $7FF4A2   ; .dw -- Vm_Dec_Q16Mul partial-product scratch:
                                ; high word of loA*loB
VmDec_LHlo        = $7FF4A4   ; .dw -- low word of loA*hiB
VmDec_LHhi        = $7FF4A6   ; .dw -- high word of loA*hiB
VmDec_HLlo        = $7FF4A8   ; .dw -- low word of hiA*loB
VmDec_HLhi        = $7FF4AA   ; .dw -- high word of hiA*loB
VmDec_HHlo        = $7FF4AC   ; .dw -- low word of hiA*hiB (its high word is
                                ; bits 48-63 of the full 64-bit product, never
                                ; needed -- Q16 multiply only keeps bits 16-47)
VmDec_MulWord1    = $7FF4AE   ; .dw -- combined bits 16-31 of the product
VmDec_MulWord2    = $7FF4B0   ; .dw -- combined bits 32-47 of the product
                                ; (== the Q16.16 magnitude result, pre-sign)
VmDec_MulCarry    = $7FF4B2   ; .dw -- carry-accumulation scratch shared by
                                ; both combine steps above
VmDec_MagALo      = $7FF4B4   ; .dw -- Q16Mul/Q16Div shared: abs(left), low
VmDec_MagAHi      = $7FF4B6   ; .dw -- abs(left), high
VmDec_MagBLo      = $7FF4B8   ; .dw -- abs(right), low
VmDec_MagBHi      = $7FF4BA   ; .dw -- abs(right), high
VmDec_SignA       = $7FF4BC   ; .dw -- $8000 or $0000, left operand's original sign
VmDec_SignB       = $7FF4BE   ; .dw -- right operand's original sign
VmDec_DivQLo      = $7FF4C0   ; .dw -- Vm_Dec_DivModNUnsigned quotient, low
VmDec_DivQHi      = $7FF4C2   ; .dw -- quotient, high (seeded with the
                                ; dividend before the call -- same
                                ; shift-the-dividend-into-itself trick
                                ; vm_arith32.pasm's Vm_DivMod32Unsigned uses)
VmDec_DivRLo      = $7FF4C4   ; .dw -- remainder, low
VmDec_DivRHi      = $7FF4C6   ; .dw -- remainder, high
VmDec_DivDLo      = $7FF4C8   ; .dw -- divisor, low
VmDec_DivDHi      = $7FF4CA   ; .dw -- divisor, high
VmDec_FormatBuf   = $7FF4CC   ; 16 B -- Vm_Dec_FormatSlot's ASCII output
                                ; staging area (max real use: 11 bytes, a
                                ; sign + 10 digits for INT_MIN, or a sign +
                                ; 5 int digits + '.' + 4 frac digits for a
                                ; DECIMAL -- both well under 16)
VmDec_FormatLen   = $7FF4DC   ; .dw -- length actually written to FormatBuf
; --- Vm_Dec_ConcatCoerce (vm_dec16.pasm) parameter cells -- ADD's STR+
; numeric coercion path, populated by vm_run.pasm's Vm_Op_Add before it
; `jsr`s there. ---
VmDec_NumSideSlot = $7FF4DE   ; .dw -- slot index of the INTEGER/DECIMAL operand
VmDec_StrSideSlot = $7FF4E0   ; .dw -- slot index of the BOR_VT_STR operand
VmDec_NumSideIsA  = $7FF4E2   ; .dw -- 1 if the numeric operand is ADD's LEFT
                                ; (VmPriv_B) operand, 0 if it's the RIGHT
                                ; (VmPriv_C) operand
; --- bank-1 (vm_dec16_heavy.pasm) internal scratch -- Vm_Dec_Mul16x16's
; own 16x16->32 shift-add staging (self-contained, does NOT reuse
; core/math.pasm's Core_Math_Mul or its low16-alias cells -- see
; vm_consts.pasm's own VM_DEC_BANK note on why). ---
VmDec_MulTmpMultiplicand = $7FF4E4   ; .dw
VmDec_MulTmpMultiplier   = $7FF4E6   ; .dw
VmDec_MulTmpProdLo       = $7FF4E8   ; .dw
VmDec_MulTmpProdHi       = $7FF4EA   ; .dw
; --- Vm_Dec_FormatSlot / Vm_Dec_FormatInt32 (bank 1) scratch. ---
VmDec_FmtFracLo    = $7FF4EC   ; .dw -- fractional-digit generator's 32-bit
                                 ; running value, low word
VmDec_FmtFracHi    = $7FF4EE   ; .dw -- high word (holds the just-produced
                                 ; digit 0-9 between Vm_Dec_FracDigit calls)
VmDec_FmtDigitCount = $7FF4F0  ; .dw -- Vm_Dec_FormatInt32's collected
                                 ; integer-part digit count
VmDec_DigitStack   = $7FF4F2   ; 10 B -- one decimal digit (0-9) per byte,
                                 ; ones place at index 0, filled upward;
                                 ; 10 bytes covers uint32's max 10 digits
; Ends $7FF4FC.

; Q16.16 layout: same 4-byte Lo/Hi slot value field as INTEGER, reinterpreted
; as a signed 32-bit fixed-point number with the binary point between bit 15
; and bit 16 (Hi = signed 16-bit integer part, Lo = unsigned 16-bit fraction,
; 1/65536 per count). INTEGER->DECIMAL promotion is `raw << 16` mod 2^32 --
; i.e. newHi=oldLo, newLo=0 -- so only integers in -32768..32767 promote
; exactly; anything outside that range wraps, the same mod-2^32 wrap
; convention Gate 2 already uses everywhere else (a documented decision, not
; a guess -- plan_vm.md §7 only mandates truncate-toward-zero on the way
; DOWN, promotion's own overflow rule is this gate's to pick). DECIMAL-
; >INTEGER truncation (used by MOD/SHL/SHR/BIT_OR/XOR/BIT_AND, which
; "integer-convert" a DECIMAL operand per opcode_manifest.csv) truncates
; toward zero: nonnegative values take Hi as-is (already floor==trunc for
; nonnegative numbers); negative values with a nonzero fraction take Hi+1
; (since Hi alone is floor(value), one closer to zero); the 16-bit Hi (or
; Hi+1) is then sign-extended to the full 32-bit INTEGER result.
;
; Cartridge-defined decimal/integer->string format (plan_vm.md §7 -- no
; historical printf reference exists to match, so this project defines its
; own and fixtures it): INTEGER formats as a bare signed decimal ("-42",
; "0", "2147483647"). DECIMAL formats as signed-integer-part + "." + exactly
; 4 fractional digits, each digit truncated (not rounded) from repeated
; `frac *= 10; digit = frac >> 16; frac &= $FFFF` steps (e.g. 3.5 ->
; "3.5000", -2.25 -> "-2.2500"; note the sign is attached once, to the whole
; value, not to the integer part alone -- -0.5 formats "-0.5000", never
; "0.-5000" or a bare "-.5000").
; Vm_Dec_Q16Mul/Q16DivSigned/FormatSlot live in bank 1 (appended after the
; TAD audio blob inside main.pasm's existing `.bank 1` section), reached via
; plain `jsl Label` -- CLAUDE.md's Architecture section reconfirms cross-bank
; `jsl` resolves the correct bank byte automatically (fixed, unlike the
; separate and still-`^`-operator-specific poppy#389 workaround, which this
; code never needs since it never uses `^`). Not confined to bank 0's
; ~7168-byte VM window the way vm_run.pasm/vm_arith32.pasm/vm_string.pasm
; are -- that's the whole point of putting the heavy Q16 primitives there
; (plan_vm.md 0.3's ROM-budget note).
