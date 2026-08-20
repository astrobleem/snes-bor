; ============================================================================
; core/vm/vm_native_engine.pasm -- Gate 6 (plan_vm.md §8): the 6 real
; engine-facing natives SPAWN000.C actually calls, specialized per
; tools/bor_converter/openbor_script/natives.py's own module docstring:
; getentityproperty/changeentityproperty are dispatched on a string argument
; in real OpenBOR; since the exporter controls codegen for a script it
; compiles ahead of time, each (function, compile-time-constant property
; string) pair the target script uses gets its own stable native ID here
; instead -- a flat compare-and-branch chain in vm_call.pasm, exactly like
; Gate 3's abs/min/max/log dispatcher, not a runtime string comparator. The
; host oracle (oracle.py) applies the identical specialization so trace
; comparison stays meaningful.
;
; Lives in bank 1, appended directly after vm_dec16_heavy.pasm (still
; `.bank 1`, no new `.org` -- same "Fixed" resume-in-place shape that file's
; own header documents, now provably safe post-poppy#390). Bank 0's
; $9000-$AC00 VM window is full (this file's dispatch chain alone overlapped
; it into the LoadAudioData region on first attempt -- see build error
; history in the commit that added this file). Reached from vm_call.pasm
; (bank 0) via a SINGLE `jsl` to Vm_NativeEng_Dispatch below, which does the
; 9-way native-ID dispatch itself and `rtl`s back exactly once -- vm_call.pasm
; only knows "target_id >= 100 -> jsl here", not which of the nine natives it
; is; the alternative (nine separate `jsl` targets, one per native, matching
; abs/min/max/log's own shape) needed nine cmp/beq/jsl/brl blocks in bank 0
; and didn't fit. Every routine below except Dispatch itself is a same-bank
; `jsr`/`rts` helper, called only from Dispatch or from each other.
; **Entirely self-contained**, same constraint vm_dec16_heavy.pasm's own
; header already establishes: no `jsr` to any bank-0 routine (Gate 3's
; Vm_CallArgSlot included) -- a `jsr` from bank-1 code resolves its target
; within bank 1's own address space, not bank 0's, since `jsr` never touches
; PBR; the only cross-bank primitive that works here is `jsl`/`rtl`.
; Vm_CallArgSlot's own tiny arg-slot lookup is duplicated locally
; (Vm_NativeEng_ArgSlot) rather than cross-called, matching this project's
; established "duplicate a small primitive across a bank boundary rather
; than call across it" precedent.
;
; `self` always resolves to the player (entity 0) -- this project has no
; per-entity script attachment (oop.pasm's own "don't build a general
; entity-lookup system for a single-player game" constraint).
;
; Entity handles (self, vSpawn) are plain VT_INTEGER slot values (the
; entity index, 0-3), not a distinct VT_PTR encoding -- nothing in
; vm_run.pasm/vm_slots.pasm gives VT_PTR any behavior LOAD/SAVE doesn't
; already give a plain integer, so a dedicated pointer representation would
; be unused machinery. Every native below that "returns EMPTY" in the real
; OpenBOR sense (clearspawnentry, setspawnentry, changeentityproperty, and
; spawn's no-free-slot case) instead returns VT_INTEGER 0, because
; Vm_StoreIntResult (vm_arith32.pasm, bank 0, reused unmodified from Gate
; 2/3) always tags its destination slot VT_INTEGER -- SPAWN000.C's own
; control flow never reads any of these results, so the difference is
; unobservable for this script; documented here rather than silently
; diverging from FORMAT.md's EMPTY type without saying so.
;
; Struct field access: every entity's CharacterEntity fields
; (main.pasm CHAR_POS_X/CHAR_POS_Y/CHAR_FACING_LEFT/CHAR_HP) live at
; $7E0a00 + entity_index*CHAR_ZP_LEN (CHAR_ZP_LEN=36), matching
; Entity1_Base/Entity2_Base/Entity3_Base's own stride and PlayerEntity_*'s
; base ($7E0a00, entity 0) already established in main.pasm. Entity index
; is always 0..3 here (this project's fixed 4-entity model -- CLAUDE.md),
; so the byte offset entity_index*36 is looked up from a 4-entry table
; (Vm_NativeEntityByteOff) rather than synthesized with shifts/adds: no
; MUL instruction exists on 65816, and a fixed 4-entry table is simpler and
; cheaper than either for a bound this small. Long-indexed addressing is
; X-only throughout (CLAUDE.md: no `nnnnnn,y` opcode exists; Poppy silently
; accepts it and drops the bank byte if written -- never write it).
;
; Global (not @-local) labels; explicit width directive after every label
; (poppy#386, still live); no nop guards (that bug is fixed).
; ============================================================================

; --- Scratch. NOT placed at $7FF40E -- that collides with vm_string.pasm's
; VmStr_StringsOff/VmStr_ScratchA (Gate 4's string-pool cells start exactly
; there; see that file's header). Placed instead at $7FF4FC, directly after
; vm_dec16_heavy.pasm's own VmDec_DigitStack ($7FF4F2, 10 B, ends $7FF4FC --
; grep-confirmed free 2026-08-20, nothing under src/ references $7FF4FC+).
; Ends $7FF500. ---
VmNativeEng_EntityOff = $7FF4FC   ; .dw -- entity_index*36, computed once per native
VmNativeEng_ScanIndex = $7FF4FE   ; .dw -- SPAWN's free-slot scan cursor, 1..3

Vm_NativeEntityByteOff:
    .dw 0, 36, 72, 108

; ============================================================================
; Vm_NativeEng_Dispatch -- the ONE `jsl` entry point vm_call.pasm reaches
; (Vm_Op_Call__native_engine, for any target_id >= 100). Dispatches on
; VmCall_TargetId itself and `jsr`/`rts`s to the matching routine below
; (same-bank, safe), then `rtl`s back to bank 0 once -- see this file's
; header for why the nine dispatch cases collapsed into this one jsl
; instead of each routine being its own jsl target (bank 0 ran out of room
; for nine separate cmp/beq/jsl/brl blocks).
; ============================================================================
Vm_NativeEng_Dispatch:
.a16
.i16
    lda.l VmCall_TargetId
    cmp #VM_NATIVE_GETLOCALVAR_SELF
    beq Vm_NativeEng_Dispatch__getlocalvar_self
    cmp #VM_NATIVE_GETENTITYPROP_X
    beq Vm_NativeEng_Dispatch__getprop_x
    cmp #VM_NATIVE_GETENTITYPROP_A
    beq Vm_NativeEng_Dispatch__getprop_a
    cmp #VM_NATIVE_GETENTITYPROP_Z
    beq Vm_NativeEng_Dispatch__getprop_z
    cmp #VM_NATIVE_GETENTITYPROP_DIRECTION
    beq Vm_NativeEng_Dispatch__getprop_dir
    cmp #VM_NATIVE_CLEARSPAWNENTRY
    beq Vm_NativeEng_Dispatch__clearspawn
    cmp #VM_NATIVE_SETSPAWNENTRY_NAME
    beq Vm_NativeEng_Dispatch__setspawnname
    cmp #VM_NATIVE_SPAWN
    beq Vm_NativeEng_Dispatch__spawn
    cmp #VM_NATIVE_CHANGEENTITYPROP_POSITION
    beq Vm_NativeEng_Dispatch__changeprop_pos
    sec
    lda #VMERR_BAD_NATIVE
    rtl

Vm_NativeEng_Dispatch__getlocalvar_self:
.a16
    jsr Vm_NativeEng_GetLocalVarSelf
    rtl
Vm_NativeEng_Dispatch__getprop_x:
.a16
    jsr Vm_NativeEng_GetPropX
    rtl
Vm_NativeEng_Dispatch__getprop_a:
.a16
    jsr Vm_NativeEng_GetPropA
    rtl
Vm_NativeEng_Dispatch__getprop_z:
.a16
    jsr Vm_NativeEng_GetPropZ
    rtl
Vm_NativeEng_Dispatch__getprop_dir:
.a16
    jsr Vm_NativeEng_GetPropDirection
    rtl
Vm_NativeEng_Dispatch__clearspawn:
.a16
    jsr Vm_NativeEng_ClearSpawnEntry
    rtl
Vm_NativeEng_Dispatch__setspawnname:
.a16
    jsr Vm_NativeEng_SetSpawnEntryName
    rtl
Vm_NativeEng_Dispatch__spawn:
.a16
    jsr Vm_NativeEng_Spawn
    rtl
Vm_NativeEng_Dispatch__changeprop_pos:
.a16
    jsr Vm_NativeEng_ChangePropPosition
    rtl

; ============================================================================
; Vm_NativeEng_ArgSlot -- in: A(.a16) = zero-based argument index n. Uses
; VmCall_ArgListIndex/ArgSlotsOff (vm_call.pasm's own WRAM cells -- plain
; $7Fxxxx cells, readable from any bank's code same as always; only CODE
; can't be reached across banks via jsr, data always can via `.l`).
; out: X = byte offset of argument n's slot within VmSlots_Wram. Local
; duplicate of vm_call.pasm's Vm_CallArgSlot -- see file header for why.
; ============================================================================
Vm_NativeEng_ArgSlot:
.a16
.i16
    clc
    adc.l VmCall_ArgListIndex
    asl a
    clc
    adc.l VmCall_ArgSlotsOff
    tax
    lda.l VmCode_Wram,x
    asl a
    asl a
    asl a
    tax
    rts

; ============================================================================
; Vm_NativeEng_ArgEntity -- in: A(.a16) = argument index n. Reads arg n's
; slot as an entity index (low byte of its INTEGER value, masked to 0-3 by
; construction -- see natives.py; not separately bounds-checked here, same
; trust-the-compiler-output stance vm_call.pasm's own Vm_CallArgSlot takes).
; out: VmNativeEng_EntityOff = entity_index*36. Clobbers X.
; ============================================================================
Vm_NativeEng_ArgEntity:
.a16
.i16
    jsr Vm_NativeEng_ArgSlot
    lda.l VmSlots_Wram+4,x
    and #$0003
    asl a
    tax
    lda.l Vm_NativeEntityByteOff,x
    sta.l VmNativeEng_EntityOff
    rts

; --- GETLOCALVAR_SELF: argc=0. Always the player, entity 0. ---
Vm_NativeEng_GetLocalVarSelf:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #0
    beq Vm_NativeEng_GetLocalVarSelf__ok
    sec
    lda #VMERR_BAD_NATIVE
    rts
Vm_NativeEng_GetLocalVarSelf__ok:
.a16
    lda #0
    sta.l VmPriv_LeftLo
    sta.l VmPriv_LeftHi
    clc
    rts

; --- Shared body for the four GETENTITYPROP_* natives: argc=1, arg0 must
; be VT_INTEGER (the entity handle). Sets VmNativeEng_EntityOff on success;
; on failure, A(.a16) holds a VMERR_* code and carry is set (jsr/rts, only
; reached from within this file -- callers propagate straight to rtl). ---
Vm_NativeEng_GetEntityProp__common:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #1
    beq Vm_NativeEng_GetEntityProp__argc_ok
    sec
    lda #VMERR_BAD_NATIVE
    rts
Vm_NativeEng_GetEntityProp__argc_ok:
.a16
    lda #0
    jsr Vm_NativeEng_ArgSlot
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_INTEGER
    beq Vm_NativeEng_GetEntityProp__type_ok
    rep #$31
.a16
.i16
    sec
    lda #VMERR_BAD_TYPE
    rts
Vm_NativeEng_GetEntityProp__type_ok:
.a8
    rep #$31
.a16
.i16
    lda #0
    jsr Vm_NativeEng_ArgEntity
    clc
    rts

Vm_NativeEng_GetPropX:
.a16
.i16
    jsr Vm_NativeEng_GetEntityProp__common
    bcs Vm_NativeEng_GetPropX__fail
    lda.l VmNativeEng_EntityOff
    clc
    adc #CHAR_POS_X
    tax
    lda.l $7E0a00,x
    and #$FFFF
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    clc
    rts
Vm_NativeEng_GetPropX__fail:
.a16
    rts

Vm_NativeEng_GetPropA:
.a16
.i16
    jsr Vm_NativeEng_GetEntityProp__common
    bcs Vm_NativeEng_GetPropA__fail
    lda #0
    sta.l VmPriv_LeftLo
    sta.l VmPriv_LeftHi
    clc
    rts
Vm_NativeEng_GetPropA__fail:
.a16
    rts

Vm_NativeEng_GetPropZ:
.a16
.i16
    jsr Vm_NativeEng_GetEntityProp__common
    bcs Vm_NativeEng_GetPropZ__fail
    lda.l VmNativeEng_EntityOff
    clc
    adc #CHAR_POS_Y
    tax
    lda.l $7E0a00,x
    and #$FFFF
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    clc
    rts
Vm_NativeEng_GetPropZ__fail:
.a16
    rts

Vm_NativeEng_GetPropDirection:
.a16
.i16
    jsr Vm_NativeEng_GetEntityProp__common
    bcs Vm_NativeEng_GetPropDirection__fail
    lda.l VmNativeEng_EntityOff
    clc
    adc #CHAR_FACING_LEFT
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    and #$FF
    rep #$31
.a16
.i16
    and #$00FF
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    clc
    rts
Vm_NativeEng_GetPropDirection__fail:
.a16
    rts

; --- CLEARSPAWNENTRY: argc=0, no-op (this project's spawn model has no
; runtime-selectable roster identity -- see this file's header). ---
Vm_NativeEng_ClearSpawnEntry:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #0
    beq Vm_NativeEng_ClearSpawnEntry__ok
    sec
    lda #VMERR_BAD_NATIVE
    rts
Vm_NativeEng_ClearSpawnEntry__ok:
.a16
    lda #0
    sta.l VmPriv_LeftLo
    sta.l VmPriv_LeftHi
    clc
    rts

; --- SETSPAWNENTRY_NAME: argc=1 (the vName string, ignored -- no-op). ---
Vm_NativeEng_SetSpawnEntryName:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #1
    beq Vm_NativeEng_SetSpawnEntryName__ok
    sec
    lda #VMERR_BAD_NATIVE
    rts
Vm_NativeEng_SetSpawnEntryName__ok:
.a16
    lda #0
    sta.l VmPriv_LeftLo
    sta.l VmPriv_LeftHi
    clc
    rts

; --- SPAWN: argc=0. Scans AI slots 1..3 for the free-slot sentinel
; (CHAR_HP==0, this project's existing soft-kill/never-spawned convention
; -- core/spawn.pasm's own header), fills the first free one at
; CHAR_HP_MAX (position/facing left at whatever they last were -- SPAWN000.C
; always follows with its own changeentityproperty(...,"position",...) call,
; matching real spawn()'s "caller positions explicitly" behavior), and
; returns its entity index. No free slot -- returns 0 (see this file's
; header for why 0 rather than EMPTY). ---
Vm_NativeEng_Spawn:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #0
    beq Vm_NativeEng_Spawn__ok
    sec
    lda #VMERR_BAD_NATIVE
    rts
Vm_NativeEng_Spawn__ok:
.a16
    lda #1
    sta.l VmNativeEng_ScanIndex
Vm_NativeEng_Spawn__scan:
.a16
.i16
    lda.l VmNativeEng_ScanIndex
    asl a
    tax
    lda.l Vm_NativeEntityByteOff,x       ; entity_index*36 -- X-indexed, never ,y
    clc
    adc #CHAR_HP
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    beq Vm_NativeEng_Spawn__found
    rep #$31
.a16
.i16
    lda.l VmNativeEng_ScanIndex
    inc a
    sta.l VmNativeEng_ScanIndex
    cmp #4
    bcc Vm_NativeEng_Spawn__scan
    lda #0
    sta.l VmPriv_LeftLo
    sta.l VmPriv_LeftHi
    clc
    rts

Vm_NativeEng_Spawn__found:
.a8
    lda #CHAR_HP_MAX
    sta.l $7E0a00,x                      ; X still entity_byte_offset+CHAR_HP
    rep #$31
.a16
.i16
    lda.l VmNativeEng_ScanIndex
    sta.l VmPriv_LeftLo
    lda #0
    sta.l VmPriv_LeftHi
    clc
    rts

; --- CHANGEENTITYPROP_POSITION: argc=4 (entity, x, z, y). x/z are the
; only axes this project has (world X, screen Y); y (altitude) is read and
; discarded, matching GETENTITYPROP_A always returning 0. Values arrive as
; Q16.16 DECIMAL (the script always computes them via float arithmetic) or
; plain INTEGER; either way only the integer part is stored, matching
; real OpenBOR's own position fields being integer pixel coordinates
; (SPAWN000.C's own values are always non-negative, so the Q16.16 integer
; part is simply the value's high 16-bit word -- no rounding/truncation
; direction subtlety to resolve here). ---
Vm_NativeEng_ChangePropPosition:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #4
    beq Vm_NativeEng_ChangePropPosition__ok
    sec
    lda #VMERR_BAD_NATIVE
    rts
Vm_NativeEng_ChangePropPosition__ok:
.a16
    lda #0
    jsr Vm_NativeEng_ArgEntity        ; arg0 = entity
    lda.l VmNativeEng_EntityOff
    pha                                ; save entity byte-offset across the two field writes

    lda #1
    jsr Vm_NativeEng_ArgSlot           ; arg1 = x (Q16.16 or INTEGER)
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_DECIMAL
    beq Vm_NativeEng_ChangePropPosition__x_dec
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    bra Vm_NativeEng_ChangePropPosition__x_have
Vm_NativeEng_ChangePropPosition__x_dec:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+6,x             ; Q16.16 high word == integer part
Vm_NativeEng_ChangePropPosition__x_have:
.a16
    tay
    pla
    clc
    adc #CHAR_POS_X
    tax
    tya
    sta.l $7E0a00,x
    lda.l VmNativeEng_EntityOff
    pha

    lda #2
    jsr Vm_NativeEng_ArgSlot           ; arg2 = z (this project's Y axis)
    sep #$20
.a8
    lda.l VmSlots_Wram+0,x
    cmp #BOR_VT_DECIMAL
    beq Vm_NativeEng_ChangePropPosition__z_dec
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+4,x
    bra Vm_NativeEng_ChangePropPosition__z_have
Vm_NativeEng_ChangePropPosition__z_dec:
.a8
    rep #$31
.a16
.i16
    lda.l VmSlots_Wram+6,x
Vm_NativeEng_ChangePropPosition__z_have:
.a16
    tay
    pla
    clc
    adc #CHAR_POS_Y
    tax
    tya
    sta.l $7E0a00,x

    lda #0
    sta.l VmPriv_LeftLo
    sta.l VmPriv_LeftHi
    clc
    rts
