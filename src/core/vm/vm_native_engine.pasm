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
; so the byte offset entity_index*CHAR_ZP_LEN is looked up from a 4-entry table
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
VmNativeEng_EntityOff = $7FF4FC   ; .dw -- entity_index*CHAR_ZP_LEN, computed once per native
VmNativeEng_ScanIndex = $7FF4FE   ; .dw -- SPAWN's free-slot scan cursor, 1..3

; plan_game.md G7 knockdown slice: Character_HitApply__ApplyDamage's own
; scratch, placed directly after the above ($7FF500, grep-confirmed free
; 2026-08-22). Holds the entity's byte offset (CHAR_ZP_LEN*1/2/3) across the
; several X-indexed field accesses that routine needs, since X itself gets
; reused (with CHAR_* added in) for each individual field address.
HitApply_EntityBase = $7FF500     ; .dw
HitApply_TargetIndex = $7FF50C    ; .db -- actor index 1..5 for invulnerability table

; plan_game.md 7 (grab mutual-lock slice): Character_HitApply__ApplyGrab's
; own scratch, placed directly after HitApply_EntityBase ($7FF502,
; grep-confirmed free). All 16-bit -- CHAR_POS_X is world X (Phase 8).
GrabScratch_SelfX    = $7FF502   ; .dw
GrabScratch_OtherX   = $7FF504   ; .dw
GrabScratch_Mid      = $7FF506   ; .dw
GrabScratch_NewOtherX = $7FF508  ; .dw
GrabScratch_SelfBase = $7FF50A   ; .dw -- notjustfreespecial.txt item 3:
                                   ; the real attacking entity's own byte
                                   ; offset (0/CHAR_ZP_LEN/*2/*3), only the
                                   ; low byte is ever meaningful

; G7 throw slice: THROW_KNOCK_DIST is the only new scratch this slice
; needs beyond the grab cells above -- reuses GrabScratch_OtherX/
; NewOtherX (same free-once-computed shape, no lifetime overlap with the
; grab-init use since throw only ever runs after a grab is already fully
; established). $7FF50A, directly after GrabScratch_NewOtherX.
THROW_KNOCK_DIST = 24  ; px, instant horizontal displacement away from the
                         ; thrower. This project has no ballistic X-velocity
                         ; model for ANY airborne entity -- jump.pasm's own
                         ; header documents the identical simplification for
                         ; the PLAYER's own horizontal movement while
                         ; jumping (continuous dpad-read walk code reused
                         ; instead of a one-shot velocity); an instant kick
                         ; is the same simplification applied to a thrown
                         ; victim (who has no controller driving it at all
                         ; while airborne) instead of inventing a new
                         ; velocity system this project has nowhere else.

Vm_NativeEntityByteOff:
    .dw 0, CHAR_ZP_LEN, CHAR_ZP_LEN*2, CHAR_ZP_LEN*3

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
; out: VmNativeEng_EntityOff = entity_index*CHAR_ZP_LEN. Clobbers X.
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
    lda.l Vm_NativeEntityByteOff,x       ; entity_index*CHAR_ZP_LEN -- X-indexed, never ,y
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

; ============================================================================
; plan_game.md G7 knockdown slice: fall_base/rise_base offset computation,
; relocated here from Anim_LoadCharacter (bank 0, main.pasm) purely to free
; bank 0's $C100-$FC00 module-region ROM budget -- this is pure WRAM
; arithmetic (no MSU register access), so a cross-bank jsl/rtl round trip is
; safe (unlike Msu1_LoadFrame, which vm_native_engine.pasm's own header
; explains can't be jsr'd across banks). D (Direct Page) is unchanged across
; jsl, so bare CHAR_* DP-relative addressing below addresses the same
; instance Anim_LoadCharacter (bank 0) already switched to. Entered/exited
; in .a8, matching Anim_LoadCharacter's call-site width at both points; the
; caller re-asserts .a8 immediately after the call regardless (same paranoid
; re-sync convention as every other leaf in this file), so this routine's
; own internal .a16 excursions never leak.
; ============================================================================

; --- fall_base (24-bit) = attack_base + attack_frame_count*768 ---
AnimBase_ComputeFallBase:
.a8
    lda CHAR_ATTACK_FCOUNT
    rep #$31
.a16
.i16
    and #$00FF
    sta.l AnimHeaderStaging+12
    asl a
    clc
    adc.l AnimHeaderStaging+12
    sta.l AnimHeaderStaging+14

    sep #$20
.a8
    lda #0
    sta.l AnimHeaderStaging+12
    lda.l AnimHeaderStaging+14
    sta.l AnimHeaderStaging+13

    rep #$31
.a16
.i16
    lda CHAR_ATTACK_BASE_LO
    clc
    adc.l AnimHeaderStaging+12
    sta CHAR_FALL_BASE_LO
    sep #$20
.a8
    lda CHAR_ATTACK_BASE_HI
    adc.l AnimHeaderStaging+15
    sta CHAR_FALL_BASE_HI
    rtl

; --- rise_base (24-bit) = fall_base + fall_frame_count*768 ---
AnimBase_ComputeRiseBase:
.a8
    lda CHAR_FALL_FCOUNT
    rep #$31
.a16
.i16
    and #$00FF
    sta.l AnimHeaderStaging+12
    asl a
    clc
    adc.l AnimHeaderStaging+12
    sta.l AnimHeaderStaging+14

    sep #$20
.a8
    lda #0
    sta.l AnimHeaderStaging+12
    lda.l AnimHeaderStaging+14
    sta.l AnimHeaderStaging+13

    rep #$31
.a16
.i16
    lda CHAR_FALL_BASE_LO
    clc
    adc.l AnimHeaderStaging+12
    sta CHAR_RISE_BASE_LO
    sep #$20
.a8
    lda CHAR_FALL_BASE_HI
    adc.l AnimHeaderStaging+15
    sta CHAR_RISE_BASE_HI
    rtl

; ============================================================================
; AnimBlink_ShouldHide -- plan_game.md G7 knockdown slice. Relocated from
; Character_PlayFrame (bank 0, main.pasm) purely for bank-0 ROM budget, same
; reasoning as AnimBase_ComputeFallBase/ComputeRiseBase above. Cannot reuse
; Core_Math_Div (bank 0, jsr/rts-only leaf) from here -- a jsr from bank-1
; code resolves within bank 1's own space (see this file's own header), and
; Core_Math_Div doesn't rtl -- so the modulo is reimplemented locally via
; plain repeated subtraction (divisor is the compile-time constant
; DEATH_BLINK_PERIOD=6; input is bounded 1..DEATH_BLINK_FRAMES=120, so at
; most 20 iterations, and this only runs while a dead entity is mid-blink).
;
;   in:  A(8-bit) = CHAR_FALL_STATE_TIMER (1..DEATH_BLINK_FRAMES)
;   out: A(8-bit) = 1 if hidden this frame, 0 if visible
;
; Real formula: borTime % (GAME_SPEED/10) < GAME_SPEED/20, i.e. a 6-frame
; cycle (at 60fps), hidden for the first 3 -- see that slice's plan for the
; full NTSC-frame derivation. (timer-1) is used, not timer, so the cycle
; starts counting from the first held fall-frame, matching borTime's own
; free-running (not reset-per-state) semantics closely enough for a fixed-
; length window.
; ============================================================================
AnimBlink_ShouldHide:
.a8
    dec a
AnimBlink_ShouldHide__mod_loop:
.a8
    cmp #DEATH_BLINK_PERIOD
    bcc AnimBlink_ShouldHide__mod_done
    sec
    sbc #DEATH_BLINK_PERIOD
    bra AnimBlink_ShouldHide__mod_loop
AnimBlink_ShouldHide__mod_done:
.a8
    cmp #DEATH_BLINK_HIDDEN_FRAMES
    bcs AnimBlink_ShouldHide__visible
    lda #1
    rtl
AnimBlink_ShouldHide__visible:
.a8
    lda #0
    rtl

; ============================================================================
; Character_HitApply__ApplyDamage -- plan_game.md G7 knockdown slice. Shared
; knockdown-counter/HP-clamp/fall-vs-stun decision.
;
; plan_game.md 7 (grab mutual-lock slice): NO LONGER called directly from
; bank 0 -- Character_HitApply_VsEntity1/2/3 now reach this exclusively
; through Character_HitApply__TryGrab's own `__no` path (same bank,
; jsr/rts), which merges the grab decision and the damage fallback into a
; single jsl round trip for bank-0 ROM budget. This routine's own exits are
; `rts`, not `rtl` -- do NOT add a jsl caller back without changing them
; (see 65816_calling_convention_bugs project memory: jsr into an
; rtl-terminated routine, or jsl into an rts-terminated one, corrupts the
; return address on the stack).
;
; Deliberately does NOT call Game_Score_Award (bank 0, jsr/rts-only leaf) --
; same cross-bank constraint as Core_Math_Div above. Instead returns whether
; this hit was a kill and lets the bank-0 caller do the scoring itself,
; exactly matching that caller's pre-slice shape.
;
;   in:  X(16-bit) = entity byte offset (CHAR_ZP_LEN, *2, or *3 -- i.e.
;        Vm_NativeEntityByteOff's own values for entity 1/2/3)
;        Caller has ALREADY stamped EntityN_InvulnFrames -- this routine
;        only decides the reaction (stun vs fall) and applies damage.
;   out: A(8-bit) = 1 if this hit brought HP to exactly 0 (a kill), else 0.
;
; Real OpenBOR order (checkdamagedrop, then the main hit dispatcher's
; `if (drop || health<=0)`): knockdown-timer regen-if-expired, THEN
; decrement by this hit's drop force, THEN the fall-vs-stun branch is
; decided using the HP value AFTER this hit's damage is applied (not
; before) -- see that slice's plan for the sourced derivation.
; ============================================================================
Character_HitApply__ApplyDamage:
.a16
.i16
    txa
    sta.l HitApply_EntityBase

    ; --- 1: regen-if-expired, then decrement by this hit's drop force ---
    txa
    clc
    adc #CHAR_KNOCKDOWN_TIMER
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    bne Character_HitApply__ApplyDamage__no_regen
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_KNOCKDOWN_COUNT
    tax
    sep #$20
.a8
    lda #CHAR_KNOCKDOWN_MAX
    sta.l $7E0a00,x
Character_HitApply__ApplyDamage__no_regen:
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_KNOCKDOWN_TIMER
    tax
    sep #$20
.a8
    lda #KNOCKDOWN_REGEN_FRAMES
    sta.l $7E0a00,x

    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_KNOCKDOWN_COUNT
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    sec
    sbc #CHAR_ATTACK_DROP
    sta.l $7E0a00,x         ; sta doesn't touch flags -- N below still reflects this value

    ; --- 2: damage/HP subtract, clamped at 0 ---
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_HP
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    sec
    sbc #CHAR_HP_PER_HIT
    bcs Character_HitApply__ApplyDamage__hp_ok
    lda #0
Character_HitApply__ApplyDamage__hp_ok:
.a8
    sta.l $7E0a00,x         ; sta doesn't touch flags, but nothing below relies on that here

    ; --- 3: props (CHAR_INPUT_DRIVEN_PROP) never take the fall/knockdown
    ; reaction -- real OpenBOR obstacles have their own death handling, and
    ; this port's props share the loaded roster character's fall/rise
    ; assets (no distinct prop art), so falling would visibly play a
    ; person's knockdown animation on a broken table/chair. Always take the
    ; ordinary stun reaction instead, matching this project's pre-existing
    ; prop-death behavior (instant hide via Character_PlayFrame's generic
    ; dead-entity gate) exactly. ---
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_INPUT_DRIVEN
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Character_HitApply__ApplyDamage__stun

    ; --- 4: not a prop -- fall if hp==0 or knockdown_count<0 ---
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_HP
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    beq Character_HitApply__ApplyDamage__fall

    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_KNOCKDOWN_COUNT
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    bmi Character_HitApply__ApplyDamage__fall
    bra Character_HitApply__ApplyDamage__stun

Character_HitApply__ApplyDamage__fall:
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_SELECTED
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    cmp #CHAR_SELECTED_FALL
    beq Character_HitApply__ApplyDamage__fall_already_active
Character_HitApply__ApplyDamage__fall_already_active:
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda #CHAR_SELECTED_FALL
    sta.l $7E0a00,x
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_FRAME_INDEX
    tax
    sep #$20
.a8
    lda #$FF
    sta.l $7E0a00,x
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_TICK_COUNTER
    tax
    sep #$20
.a8
    lda #1
    sta.l $7E0a00,x
    bra Character_HitApply__ApplyDamage__reaction_done

Character_HitApply__ApplyDamage__stun:
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_HIT_STUN
    tax
    sep #$20
.a8
    lda #CHAR_HIT_STUN_FRAMES
    sta.l $7E0a00,x
    jsl AudioSemantic_EmitPainSound

Character_HitApply__ApplyDamage__reaction_done:
    ; --- 4: return whether this hit was a kill ---
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_HP
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    bne Character_HitApply__ApplyDamage__not_kill
    jsl AudioSemantic_EmitDiesound
    lda #1
    rts
Character_HitApply__ApplyDamage__not_kill:
.a8
    lda #0
    rts

; ============================================================================
; Spawn_ResetKnockdownFall -- plan_game.md G7 knockdown slice. Called from
; core/spawn.pasm (bank 0) via jsl, once per slot per Spawn_Play call,
; BEFORE that slot's enemy-vs-prop branch (so it applies regardless of which
; kind ends up occupying the slot). A slot is reused across waves the moment
; its previous occupant's CHAR_HP reaches 0 -- exactly a corpse parked in
; the fall machine's terminal state (CHAR_SELECTED==3, CHAR_FALL_STATE_
; TIMER==$FF). Without this reset, the next occupant would spawn already
; hidden (Character_PlayFrame's terminal blink-hide check) and never enter
; Anim_Play's normal idle dispatch. Also zeroes the knockdown counter/timer
; so stale garbage (or a still-decaying regen window) from the previous
; occupant can't produce a spurious immediate knockdown on the new
; occupant's first landed hit -- the user's explicit requirement was that
; only real accumulated drop force triggers a fall, never leftover state.
;
;   in: X(16-bit) = entity byte offset (CHAR_ZP_LEN, *2, or *3)
;   out: none. Clobbers A/X.
; ============================================================================
Spawn_ResetKnockdownFall:
.a16
.i16
    ; X (16-bit) does not have a `.l` long-addressing store form (CLAUDE.md's
    ; toolchain notes) -- route through A, same as Character_HitApply__
    ; ApplyDamage's own entry.
    txa
    sta.l HitApply_EntityBase

    lda.l HitApply_EntityBase
    clc
    adc #CHAR_SELECTED
    tax
    sep #$20
.a8
    lda #0
    sta.l $7E0a00,x

    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_FALL_STATE_TIMER
    tax
    sep #$20
.a8
    lda #0
    sta.l $7E0a00,x

    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_KNOCKDOWN_COUNT
    tax
    sep #$20
.a8
    lda #CHAR_KNOCKDOWN_MAX
    sta.l $7E0a00,x

    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_KNOCKDOWN_TIMER
    tax
    sep #$20
.a8
    lda #0
    sta.l $7E0a00,x

    ; plan_game.md 7 (grab mutual-lock slice): same reasoning as the fields
    ; above -- a respawned slot must not inherit a stale grab link from
    ; its previous occupant (e.g. killed by other means while linked, an
    ; edge case this slice's own gating tries to prevent but shouldn't be
    ; relied on alone). $FF is the "none" sentinel (never a real byte
    ; offset). Does not touch CHAR_GRAB_TARGET -- an AI entity is never a
    ; grabber in this slice, so it's always already $FF; only the player
    ; could stay stuck "holding" a despawned slot, which CHAR_GRABBED_BY's
    ; own reset here can't fix from this side -- acceptable for this
    ; slice's scope (respawn only ever happens to a dead, never-grabbed,
    ; AI slot; a grabbed AI slot's CHAR_HP never reaches 0 while linked).
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_GRABBED_BY
    tax
    sep #$20
.a8
    lda #$FF
    sta.l $7E0a00,x

    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_GRAB_TIMER
    tax
    sep #$20
.a8
    lda #0
    sta.l $7E0a00,x

    ; G7 throw slice: same "no stale state" reasoning as the grab fields
    ; above -- a respawned slot's CHAR_SELECTED is already reset to 0 at
    ; the top of this routine (so a stale THROWN value alone could never
    ; make Jump_ApplyOamYOffset misfire), but zeroing the Z cells too keeps
    ; a freshly-spawned entity's state genuinely clean rather than relying
    ; on that ordering alone.
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_THROW_ZPOS
    tax
    lda #0
    sta.l $7E0a00,x

    lda.l HitApply_EntityBase
    clc
    adc #CHAR_THROW_ZVEL
    tax
    lda #0
    sta.l $7E0a00,x
    rtl

; ============================================================================
; Anim_Play__AiSelectAttackVariant -- notjustfreespecial.txt item 3 decision
; logic, relocated here from main.pasm for bank-0 ROM budget. DP-local (self)
; addressing only, same as Character_Grab_Play -- caller (Anim_Play__
; ai_attack) runs with Core_Oop_Play's DP window already set to the acting
; entity. A in = a real random byte (from Core_Random_Get, called by the
; bank-0 caller since it ends in rts and can't be reached via jsl -- see the
; caller's own comment). Sets CHAR_ATTACK_VARIANT to 0 or 1. Always .a8 in,
; .a8 out.
; ============================================================================
Anim_Play__AiSelectAttackVariant:
.a8
    pha
    lda CHAR_ATTACK2_FCOUNT
    bne Anim_Play__AiSelectAttackVariant__have2
    pla
    lda #0
    sta CHAR_ATTACK_VARIANT
    rtl
Anim_Play__AiSelectAttackVariant__have2:
.a8
    pla
    cmp #AI_ATTACK2_CHANCE
    bcs Anim_Play__AiSelectAttackVariant__no
    lda #1
    sta CHAR_ATTACK_VARIANT
    rtl
Anim_Play__AiSelectAttackVariant__no:
.a8
    lda #0
    sta CHAR_ATTACK_VARIANT
    rtl

; ============================================================================
; Character_HitApply__TryGrab -- plan_game.md 7 (grab mutual-lock slice,
; first real slice; see project memory for the BOR.C derivation). Called
; by Character_HitApply_VsEntity1/2/3 (bank 0) via jsl -- now the ONLY
; entry point those leaves use; ApplyDamage is no longer called from bank 0
; directly (see its own header). Merges three things that used to cost
; separate ROM: a ShouldGrab check, an ApplyGrab action, AND (on the `__no`
; path, real conditions not met) a same-bank jsr straight into
; ApplyDamage's own body before rtl'ing back -- so every bank-0 leaf pays
; for exactly one width-switch/jsl round trip regardless of which path is
; taken. The tight C100-FC00 window overflowed repeatedly before this
; final shape landed (first with two separate jsl's, then with a jsl-per-
; leaf-and-ApplyDamage-jsl'd-separately-again split) -- see this slice's
; own project memory for the ROM-budget history. Real semantics
; (adjust_grabposition, grabin==0 path, DCurrent/openbor's engine/
; openbor.c): only when the attacker (self -- always the player here; AI
; never grabs, see Character_HitApply's own player-vs-AI/AI-vs-player
; split) has CHAR_ATTACK2_IS_GRAB set, attack2 is the active move, and
; neither side is already linked, snap both entities' X to the AVERAGE of
; their current positions, then separate by a fixed distance around that
; midpoint -- computed ONCE here. The ongoing per-frame rigid follow-drag
; is Character_Grab_Play's job (bank 0, self-only DP-local addressing, no
; cross-entity access needed there).
;
; This project has no per-model grabdistance/stalltime config (real
; BOR.C's are per-model-configurable); GRAB_HALF_DIST/GRAB_HOLD_FRAMES
; below are single fixed values instead, documented as the simplification
; they are.
;
;   in:  X(16-bit) = target entity's byte offset (CHAR_ZP_LEN, *2, or *3)
;   out: carry SET if a grab happened (caller should skip its own damage
;        path -- the hit is fully handled), CLEAR if the conditions
;        weren't met (caller should fall through to its normal
;        ApplyDamage path unchanged). Clobbers A/X either way. Caller
;        re-asserts its own width after jsl, same convention as
;        Character_HitApply__ApplyDamage's caller.
; ============================================================================
GRAB_HALF_DIST = 8     ; px each side of the midpoint -- comfortably inside
                        ; CHAR_HITBOX_W(32)'s already-passed overlap check
GRAB_HOLD_FRAMES = 240  ; ~4s @ 60fps before auto-release -- bumped from
                         ; 90 (~1.5s) when game_g7_grab.py's own held-
                         ; state check showed the timer occasionally
                         ; expiring mid-check under the Mesen2 harness's
                         ; real per-call wall-clock overhead (dozens of
                         ; real MCP round trips between grab-init and

; ============================================================================
; Grab-link representation helpers.  CHAR_GRAB_TARGET and CHAR_GRABBED_BY
; contain actor slot IDs (0..CHARACTER_ACTOR_COUNT-1), not byte offsets.  The
; old offset representation fit slots 0/1 only; higher offsets were silently
; truncated by the one-byte fields.  $FF remains the none sentinel.
Character_Grab_OffsetToSlot:
.a16
.i16
    cmp #0
    beq Character_Grab_OffsetToSlot__0
    cmp #CHAR_ZP_LEN
    beq Character_Grab_OffsetToSlot__1
    cmp #CHAR_ZP_LEN*2
    beq Character_Grab_OffsetToSlot__2
    cmp #CHAR_ZP_LEN*3
    beq Character_Grab_OffsetToSlot__3
    cmp #CHAR_ZP_LEN*4
    beq Character_Grab_OffsetToSlot__4
    cmp #CHAR_ZP_LEN*5
    beq Character_Grab_OffsetToSlot__5
    sep #$20
.a8
    lda #$FF
    clc
    rts
Character_Grab_OffsetToSlot__0:
.a16
    lda #0
    bra Character_Grab_OffsetToSlot__done
Character_Grab_OffsetToSlot__1:
.a16
    lda #1
    bra Character_Grab_OffsetToSlot__done
Character_Grab_OffsetToSlot__2:
.a16
    lda #2
    bra Character_Grab_OffsetToSlot__done
Character_Grab_OffsetToSlot__3:
.a16
    lda #3
    bra Character_Grab_OffsetToSlot__done
Character_Grab_OffsetToSlot__4:
.a16
    lda #4
    bra Character_Grab_OffsetToSlot__done
Character_Grab_OffsetToSlot__5:
.a16
    lda #5
Character_Grab_OffsetToSlot__done:
    sep #$20
.a8
    sec
    rts

Character_Grab_SlotToOffset:
.a8
    cmp #CHARACTER_ACTOR_COUNT
    bcs Character_Grab_SlotToOffset__invalid
    rep #$30
.a16
.i16
    and #$00FF
    asl a
    tax
    lda.l EntityOffsetTable,x
    sec
    rts
Character_Grab_SlotToOffset__invalid:
.a8
    lda #0
    rep #$20
.a16
    clc
    rts

; ============================================================================
; Character_HitApply__TryGrabVsPlayer -- AI-vs-player grab-establish check.
; notjustfreespecial.txt item 3 (AI grab/throw reachability): the AI-vs-
; player hit path (Character_HitApply_VsPlayer) previously never called any
; grab-check at all -- an entirely separate hardcoded gap from item 2's
; player-side link. X = attacker's byte offset (the AI entity landing the
; hit) on entry. Target is always the player (offset 0), matching
; Character_HitApply_VsPlayer's own fixed caller context.
;
; Unlike Character_HitApply__TryGrab (player-vs-AI), this does NOT fall
; back into ApplyDamage on decline -- VsPlayer already has its own simpler
; existing damage block (no knockdown-counter fall reaction), and that path
; is left completely untouched here. Returns carry SET (and control never
; returns here -- falls through into the shared __do block, which itself
; rtl's) if a grab was established; carry CLEAR (.a8) if not, so the caller
; runs its own ordinary damage block.
; ============================================================================
Character_HitApply__TryGrabVsPlayer:
.a16
.i16
    txa
    sta.l HitApply_EntityBase
    sep #$20
.a8
    lda CHAR_ATTACK2_IS_GRAB
    beq Character_HitApply__TryGrabVsPlayer__no
    lda CHAR_ATTACK_VARIANT
    cmp #1
    bne Character_HitApply__TryGrabVsPlayer__no
    lda CHAR_GRAB_TARGET
    cmp #$FF
    bne Character_HitApply__TryGrabVsPlayer__no
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_GRABBED_BY
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    cmp #$FF
    beq Character_HitApply__TryGrabVsPlayer__go
Character_HitApply__TryGrabVsPlayer__no:
.a8
    clc
    rtl
Character_HitApply__TryGrabVsPlayer__go:
.a8
    jmp Character_HitApply__TryGrab__do
                         ; the gate's own explicit forced-release step)

Character_HitApply__TryGrab:
.a16
.i16
    txa
    sta.l HitApply_EntityBase

    ; --- conditions (formerly a separate ShouldGrab routine) ---
    ; notjustfreespecial.txt item 2: two real move-slot shapes both qualify
    ; as a grab-establishing hit now -- JOE's original attack2_is_grab
    ; mutual lock (variant 1), and LEO's real, separate `grab` role
    ; (CHAR_GRABMOVE_FCOUNT, variant 5 -- see main.pasm's own struct
    ; comment on why it's a distinct field from CHAR_ATTACK2_IS_GRAB).
    ; Previously LEO's grab only ever played as a plain one-shot attack
    ; through the ordinary damage path -- this reuses the exact same
    ; mutual-lock machinery JOE already has, no new hit-detection call
    ; site needed (every player-vs-AI landed hit already jsl's here).
    sep #$20
.a8
    lda CHAR_ATTACK_VARIANT
    cmp #1
    beq Character_HitApply__TryGrab__check_joe
    cmp #5
    beq Character_HitApply__TryGrab__check_leo
    bra Character_HitApply__TryGrab__no
Character_HitApply__TryGrab__check_joe:
.a8
    lda CHAR_ATTACK2_IS_GRAB
    beq Character_HitApply__TryGrab__no
    bra Character_HitApply__TryGrab__cond_ok
Character_HitApply__TryGrab__check_leo:
.a8
    lda CHAR_GRABMOVE_FCOUNT
    beq Character_HitApply__TryGrab__no
Character_HitApply__TryGrab__cond_ok:
.a8
    lda CHAR_GRAB_TARGET
    cmp #$FF
    bne Character_HitApply__TryGrab__no
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_GRABBED_BY
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    cmp #$FF
    beq Character_HitApply__TryGrab__do
Character_HitApply__TryGrab__no:
.a8
    ; ROM budget (main.pasm's C100-FC00 window): rather than making every
    ; bank-0 leaf pay for a second width-switch/ldx/jsl round trip to reach
    ; ApplyDamage, reach it from here instead via a same-bank jsr/rts (NOT
    ; jsl/rtl -- ApplyDamage's own two exits are `rts` now, precisely so
    ; this call is same-bank-safe; see 65816_calling_convention_bugs
    ; project memory on why jsr-into-an-rtl-terminated-routine corrupts the
    ; stack). X was clobbered by the CHAR_GRABBED_BY probe above --
    ; restore it from HitApply_EntityBase (this leaf's own saved copy) so
    ; ApplyDamage's entry sees the same entity offset TryGrab was called
    ; with.
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    tax
    jsr Character_HitApply__ApplyDamage   ; both its own exits are real .a8
                                            ; (see its own trailing `rts`
                                            ; sites) -- re-assert here too so
                                            ; this path's `rtl` genuinely
                                            ; matches the __do path's real
                                            ; .a8 exit width, not just the
                                            ; textual/Poppy-tracked one. REAL
                                            ; BUG found the hard way: this
                                            ; exit used to fall straight from
                                            ; the rep #$31/.a16/.i16 above
                                            ; into `clc`/`rtl` with NO sep,
                                            ; so the CPU was actually still
                                            ; 16-bit here even though every
                                            ; caller (Character_HitApply_
                                            ; VsEntity1/2/3) assumed .a8
                                            ; immediately after the jsl --
                                            ; silently desyncing every
                                            ; ordinary (non-grab) landed hit,
                                            ; corrupting execution until
                                            ; CharacterEntity_Play's return
                                            ; value came back garbled and
                                            ; the OOP dispatcher misread it
                                            ; as OBJR_KILL, deleting all 4
                                            ; entities in the same frame.
    sep #$20
.a8
    clc
    rtl
Character_HitApply__TryGrab__do:
.a8
    rep #$31
.a16
.i16
    ; notjustfreespecial.txt item 3 (AI grab/throw reachability): self's OWN
    ; byte offset, needed below so CHAR_GRABBED_BY records the REAL
    ; attacker (grabber may now be an AI entity, not always the player --
    ; see this slice's own header note). D is already switched to self's
    ; DP window (Core_Oop_Play's phd/tcd, same as every bare CHAR_* read in
    ; this routine relies on) -- `tdc` reads it directly, and D always
    ; equals one of the 4 fixed per-entity DpBase constants (PlayerEntity_
    ; DpBase + N*CHAR_ZP_LEN), so subtracting PlayerEntity_DpBase recovers
    ; the same N*CHAR_ZP_LEN byte-offset convention HitApply_EntityBase
    ; already uses for the target.
    tdc
    sec
    sbc #PlayerEntity_DpBase
    sta.l GrabScratch_SelfBase

    ; self.CHAR_POS_X (DP-local, player -- D is still the player's OopDp
    ; window here, same as the caller's own dx computation already relies
    ; on for bare CHAR_POS_X reads)
    lda CHAR_POS_X
    sta.l GrabScratch_SelfX

    ; target.CHAR_POS_X
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_POS_X
    tax
    lda.l $7E0a00,x
    sta.l GrabScratch_OtherX

    ; midpoint = (self_x + other_x) / 2, unsigned
    lda.l GrabScratch_SelfX
    clc
    adc.l GrabScratch_OtherX
    lsr a
    sta.l GrabScratch_Mid

    ; side decision (real adjust_grabposition): self_x >= other_x -> self
    ; gets the +half side, other gets -half; else swapped.
    lda.l GrabScratch_SelfX
    cmp.l GrabScratch_OtherX
    bcs Character_HitApply__ApplyGrab__self_ge
.a16
.i16
    lda.l GrabScratch_Mid
    sec
    sbc #GRAB_HALF_DIST
    sta CHAR_POS_X
    lda.l GrabScratch_Mid
    clc
    adc #GRAB_HALF_DIST
    sta.l GrabScratch_NewOtherX
    bra Character_HitApply__ApplyGrab__sides_done
.a16
.i16
Character_HitApply__ApplyGrab__self_ge:
.a16
.i16
    lda.l GrabScratch_Mid
    clc
    adc #GRAB_HALF_DIST
    sta CHAR_POS_X
    lda.l GrabScratch_Mid
    sec
    sbc #GRAB_HALF_DIST
    sta.l GrabScratch_NewOtherX
Character_HitApply__ApplyGrab__sides_done:
.a16
.i16
    ; write target's new X
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_POS_X
    tax
    lda.l GrabScratch_NewOtherX
    sta.l $7E0a00,x

    ; target.CHAR_GRABBED_BY = the REAL attacker's bounded actor slot ID --
    ; notjustfreespecial.txt item 3: this used to be a hardcoded literal 0
    ; ("grabber is always the player"), which was harmless while attack2/
    ; grab was structurally unreachable for AI (Anim_Play__ai_attack never
    ; sets CHAR_ATTACK_VARIANT, always leaving it at 0/attack1) but would
    ; have silently mis-attributed the grab to the player the moment AI
    ; attack-move selection existed. Fixed now that it does (see Anim_
    ; Play__ai_attack's own AI_ATTACK2_CHANCE roll).
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_GRABBED_BY
    tax
    sep #$20
.a8
    rep #$20
.a16
    lda.l GrabScratch_SelfBase
    jsr Character_Grab_OffsetToSlot
    sep #$20
.a8
    sta.l $7E0a00,x

    ; target.CHAR_GRAB_TIMER = GRAB_HOLD_FRAMES
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_GRAB_TIMER
    tax
    sep #$20
.a8
    lda #GRAB_HOLD_FRAMES
    sta.l $7E0a00,x

    ; target.CHAR_GRAB_OFFSET = new_other_x - self's new X (CHAR_POS_X was
    ; already overwritten with self's new X above) -- signed, small range
    ; (|GRAB_HALF_DIST*2|), fits one byte.
    rep #$31
.a16
.i16
    lda.l GrabScratch_NewOtherX
    sec
    sbc CHAR_POS_X
    sta.l GrabScratch_Mid          ; reuse as scratch, no longer needed
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_GRAB_OFFSET
    tax
    sep #$20
.a8
    lda.l GrabScratch_Mid
    sta.l $7E0a00,x

    ; self.CHAR_GRAB_TARGET = target's bounded actor slot ID.
    rep #$20
.a16
    lda.l HitApply_EntityBase
    jsr Character_Grab_OffsetToSlot
    sep #$20
.a8
    sta CHAR_GRAB_TARGET

    ; latch this attack cycle, same as a landed normal hit
    lda #1
    sta CHAR_HIT_APPLIED

    sec
    rtl

; Character_HitApply_VsEntityGeneric -- bounded target traversal helper.
; X is the target's CharacterEntity byte offset.  It performs the same AABB,
; invulnerability, grab, and damage decision used by the former fixed
; Entity1/2/3 leaves, but reads the target through the existing object-RAM
; offset convention.  Carry clear means no damage/grab was applied; carry set
; means a normal damage hit was applied (A is the kill result).  A grab is
; deliberately reported as carry clear because the existing caller must not
; award score or run pickup resolution for a grab lock.
Character_HitApply_VsEntityGeneric:
.a16
.i16
    txa
    sta.l HitApply_EntityBase
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_POS_X
    tax
    lda.l PlayerEntity_PosX
    cmp.l $7E0a00,x
    bcs Character_HitApply_VsEntityGeneric__dx_otherge
    lda.l $7E0a00,x
    sec
    sbc.l PlayerEntity_PosX
    bra Character_HitApply_VsEntityGeneric__dx_have
Character_HitApply_VsEntityGeneric__dx_otherge:
    sec
    sbc.l $7E0a00,x
Character_HitApply_VsEntityGeneric__dx_have:
    cmp #CHAR_HITBOX_W
    bcs Character_HitApply_VsEntityGeneric__no

    lda.l HitApply_EntityBase
    clc
    adc #CHAR_POS_Y
    tax
    sep #$20
.a8
    lda.l PlayerEntity_PosY
    cmp.l $7E0a00,x
    bcs Character_HitApply_VsEntityGeneric__dy_otherge
    lda.l $7E0a00,x
    sec
    sbc.l PlayerEntity_PosY
    bra Character_HitApply_VsEntityGeneric__dy_have
Character_HitApply_VsEntityGeneric__dy_otherge:
    sec
    sbc.l $7E0a00,x
Character_HitApply_VsEntityGeneric__dy_have:
    cmp #CHAR_HITBOX_H
    bcs Character_HitApply_VsEntityGeneric__no

    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_HP
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    beq Character_HitApply_VsEntityGeneric__no
    rep #$31
.a16
.i16
    lda.l HitApply_TargetIndex
    tax
    sep #$20
.a8
    lda.l Actor_InvulnFrames,x
    bne Character_HitApply_VsEntityGeneric__no
    lda #AI_POST_HIT_INVULN_FRAMES
    sta.l Actor_InvulnFrames,x

    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    tax
    jsl Character_HitApply__TryGrab
.a8
    bcs Character_HitApply_VsEntityGeneric__grabbed
    sec
    rtl
Character_HitApply_VsEntityGeneric__grabbed:
    clc
    rtl
Character_HitApply_VsEntityGeneric__no:
    clc
    rtl

; Complete bounded player-target traversal. The actor table and count live in
; main.pasm; this bank owns the loop so the bank-0 collision arena does not
; grow when the bounded count grows. Target order is table order (Entity1,
; Entity2, Entity3, then any later actor slots).
Character_HitApply_VsAllGeneric:
    php
    rep #$31
.a16
.i16
    lda #0
    sta.l VmNativeEng_ScanIndex
Character_HitApply_VsAllGeneric__loop:
    lda.l VmNativeEng_ScanIndex
    tax
    txa
    lsr a
    inc a
    sta.l HitApply_TargetIndex
    lda.l Character_ActorTargetOffsets,x
    tax
    jsl Character_HitApply_VsEntityGeneric
.a8
    bcc Character_HitApply_VsAllGeneric__next
    jsl Character_HitApply__ScoreAndFinish_Long
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_HP
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    bne Character_HitApply_VsAllGeneric__next
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    tax
    jsl Character_HitApply__RevealOrPickup
Character_HitApply_VsAllGeneric__next:
    rep #$31
.a16
.i16
    lda.l VmNativeEng_ScanIndex
    inc a
    inc a
    sta.l VmNativeEng_ScanIndex
    cmp #(CHARACTER_ACTOR_COUNT-1)*2
    bcc Character_HitApply_VsAllGeneric__loop
    plp
    rtl

; ============================================================================
; Character_Grab_Throw -- G7 throw slice. Real common_throw()/toss()
; semantics (DCurrent/openbor, engine/openbor.c, same fetch this project's
; jump slice already sourced from): release the mutual link immediately,
; apply the victim's damage through the SAME Character_HitApply__
; ApplyDamage leaf every other landed hit uses (real HP clamp/knockdown-
; counter/kill decision, not a parallel damage rule), then -- UNLESS that
; hit was a kill -- override ApplyDamage's own stun-vs-fall pick with
; CHAR_SELECTED_THROWN: real toss() always results in an airborne launch,
; never a mere stun, regardless of the knockdown counter ApplyDamage just
; consulted for an ordinary hit. A killing throw needs no airborne Z at
; all -- the existing CHAR_HP==0 sticky dead-hide (Anim_Play's/Character_
; RenderFrame's own gate, G8-generalized to >=2) already takes over
; instantly, same as any other kill.
;
; Called from Anim_Play__player_input (bank 0) via jsl -- grabber is always
; the player (self, DP-local), matching every other grab routine's own
; documented restriction (AI never grabs).
;
;   in:  X(16-bit) = victim's resolved CharacterEntity byte offset
;   out: none. Clobbers A/X.
; ============================================================================
Character_Grab_Throw:
.a16
.i16
    txa
    sta.l HitApply_EntityBase

    ; --- release both link fields immediately (real common_throw clears
    ; the link before toss() runs) ---
    sep #$20
.a8
    lda #$FF
    sta CHAR_GRAB_TARGET      ; self (player, DP-local)
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_GRABBED_BY
    tax
    sep #$20
.a8
    lda #$FF
    sta.l $7E0a00,x

    ; --- knockback direction: away from the thrower, same side-decision
    ; idiom Character_HitApply__ApplyGrab already uses at grab-init
    ; (self_x >= other_x -> push other further away on the low side, else
    ; the high side). ---
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_POS_X
    tax
    lda.l $7E0a00,x
    sta.l GrabScratch_OtherX
    lda CHAR_POS_X             ; self (player)
    cmp.l GrabScratch_OtherX
    bcs Character_Grab_Throw__self_ge
    lda.l GrabScratch_OtherX   ; self < other -- push other further right
    clc
    adc #THROW_KNOCK_DIST
    bra Character_Grab_Throw__knock_have
Character_Grab_Throw__self_ge:
.a16
    lda.l GrabScratch_OtherX   ; self >= other -- push other further left
    sec
    sbc #THROW_KNOCK_DIST
Character_Grab_Throw__knock_have:
.a16
    sta.l GrabScratch_NewOtherX
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_POS_X
    tax
    lda.l GrabScratch_NewOtherX
    sta.l $7E0a00,x

    ; --- apply real damage/knockdown-counter/HP-clamp/kill decision via
    ; the shared leaf every other landed hit uses (same-bank jsr/rts --
    ; ApplyDamage's own two exits are rts, see its header). ---
    lda.l HitApply_EntityBase
    tax
    jsr Character_HitApply__ApplyDamage
.a8
    cmp #1
    beq Character_Grab_Throw__done   ; killed -- dead-hide path (elsewhere)
                                       ; takes over, no airborne Z needed

    ; --- not killed: override ApplyDamage's stun-or-fall pick with real
    ; throw semantics -- always airborne. REAL BUG found the hard way:
    ; ApplyDamage's own stun branch may have just stamped this victim's
    ; CHAR_HIT_STUN nonzero (Character_HitApply__ApplyDamage__stun) --
    ; Anim_Play's hit-stun check runs BEFORE this slice's own THROWN gate
    ; (Anim_Play__not_attacking, further down that dispatch chain) and
    ; unconditionally resets CHAR_SELECTED back to 0 the moment CHAR_
    ; HIT_STUN is nonzero, on the victim's very next Anim_Play call --
    ; silently wiping the CHAR_SELECTED_THROWN write below within a frame,
    ; confirmed via a standalone debug trace showing entity1.CHAR_SELECTED
    ; going 0/0/0 (stunned, decaying) then straight to 1/2 (AI resumed)
    ; with THROWN never once observed. Toss() always supersedes any stun
    ; reaction in real BOR too (the victim's movement is now driven
    ; entirely by the airborne Z tick, not a stun timer) -- clear CHAR_
    ; HIT_STUN here so the THROWN state actually survives to the next
    ; frame's dispatch. ---
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_HIT_STUN
    tax
    sep #$20
.a8
    lda #0
    sta.l $7E0a00,x

    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_SELECTED
    tax
    sep #$20
.a8
    lda #CHAR_SELECTED_THROWN
    sta.l $7E0a00,x

    ; --- ZPos=0, ZVel=JUMP_INITIAL_VEL (identical real toss()-sourced
    ; Q8.8 magnitude jump.pasm's own CHAR_THROW_ZVEL use uses -- toss()'s
    ; physics don't change based on who's airborne). Single 16-bit store
    ; each, matching ApplyGrab's own $7E0a00,x .a16 store convention. ---
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_THROW_ZPOS
    tax
    lda #0
    sta.l $7E0a00,x

    lda.l HitApply_EntityBase
    clc
    adc #CHAR_THROW_ZVEL
    tax
    lda #JUMP_INITIAL_VEL
    sta.l $7E0a00,x
    sep #$20
.a8
Character_Grab_Throw__done:
.a8
    rtl
Character_Grab_Throw__invalid:
.a8
    rtl

AI_THROW_CHANCE = 8   ; 8/256 per frame -- notjustfreespecial.txt item 3: a
                       ; flat per-frame chance for an AI grabber to execute
                       ; a real throw while holding, same simplification
                       ; class as Anim_Play__ai_attack's own AI_ATTACK2_
                       ; CHANCE roll. ~once every 32 frames on average
                       ; (well inside GRAB_HOLD_FRAMES=240's own auto-
                       ; release window, so a real throw is reachable
                       ; before the hold ever times out on its own).

; ============================================================================
; Anim_Play__AiGrabHoldDecide -- notjustfreespecial.txt item 3 (AI throw
; reachability). Called once per frame for an AI entity that is the
; GRABBER (self.CHAR_GRAB_TARGET != $FF) instead of letting Anim_Play__
; ai_seek re-decide its CHAR_SELECTED (see main.pasm's Anim_Play__ai_seek_
; gate). A in = a real random byte (Core_Random_Get, called by the bank-0
; caller for the same reason Anim_Play__AiSelectAttackVariant's own caller
; does). Below AI_THROW_CHANCE: throws (X = self.CHAR_GRAB_TARGET, the real
; byte offset of whoever is being held -- Character_Grab_Throw is fully
; generic on its grabber, DP-local self, same as Character_Grab_Play; no
; player-only restriction). Otherwise a no-op -- the hold just continues
; (Character_Grab_Play's own per-frame drag still runs regardless, and the
; GRAB_HOLD_FRAMES timer still auto-releases if this never rolls a throw).
; Always .a8 in, .a8 out.
; ============================================================================
Anim_Play__AiGrabHoldDecide:
.a8
    cmp #AI_THROW_CHANCE
    bcs Anim_Play__AiGrabHoldDecide__no
    rep #$30
.a16
.i16
    lda CHAR_GRAB_TARGET
    jsr Character_Grab_SlotToOffset
    bcc Anim_Play__AiGrabHoldDecide__invalid
    tax
    jsl Character_Grab_Throw
    sep #$20
.a8
Anim_Play__AiGrabHoldDecide__invalid:
    sep #$20
.a8
Anim_Play__AiGrabHoldDecide__no:
.a8
    rtl

; ============================================================================
; Character_Special_ReleaseGrab -- G7 special slice. Real BOR.C
; player_check_special() calls dograb-release before triggering (a special
; move ends any active grab the SAME frame it fires -- sourced from
; DCurrent/openbor engine/openbor.c). Only ever called on the player today
; (LEO is the only roster member with real `special` data) -- generic on
; its grabber, DP-local self, same as Character_Grab_Throw/Character_Grab_
; Play; nothing here is actually player-only, it's simply unreached by an
; AI entity because no AI character has real special data yet. Called when
; CHAR_GRAB_TARGET != $FF; a no-op call would silently write $FF into a
; real held target's own CHAR_GRABBED_BY at a garbage
; offset, so the caller MUST check first -- not re-checked here (bank-0 call
; site already gates on it, same "trust the one caller" convention as
; Character_Grab_Throw's own X-in precondition).
;
;   in:  self.CHAR_GRAB_TARGET = victim's slot ID (already valid, non-
;        $FF -- caller's precondition, matches Character_Grab_Throw's own X
;        precondition one level up).
;   out: none. Clobbers A/X.
; ============================================================================
Character_Special_ReleaseGrab:
.a8
    rep #$30
.a16
.i16
    lda CHAR_GRAB_TARGET
    jsr Character_Grab_SlotToOffset
    bcc Character_Special_ReleaseGrab__invalid
    clc
    adc #CHAR_GRABBED_BY
    tax
    sep #$20
.a8
    lda #$FF
    sta.l $7E0a00,x
    sta CHAR_GRAB_TARGET      ; self (player, DP-local)
    rtl
Character_Special_ReleaseGrab__invalid:
.a16
.i16
    sep #$20
.a8
    rtl

; ============================================================================
; Character_Grab_Play -- plan_game.md 7 (grab mutual-lock slice). Called
; from CharacterEntity_Play (bank 0) via jsl once per entity's own turn,
; DP-local (self) addressing only -- unlike Character_HitApply__TryGrab
; above, this never needs to know WHICH entity it's playing, and D is
; preserved across jsl (same reasoning every other routine in this file
; already relies on). Relocated here purely for bank 0 ROM budget
; (main.pasm's C100-FC00 window overflowed once this slice's other
; additions landed), same as ApplyDamage/ApplyGrab before it -- not a
; cross-entity routine, so no X-indexing needed, just a plain jsl/rtl leaf.
;
; A no-op for any entity whose own CHAR_GRABBED_BY is $FF (every entity,
; every frame, except a currently-held one). Real check_link_move
; semantics: rigid offset-follow every frame, NOT re-averaged -- the
; offset itself was frozen once at grab-init (CHAR_GRAB_OFFSET,
; Character_HitApply__ApplyGrab above). notjustfreespecial.txt item 3: the
; grabber is no longer assumed to always be the player -- CHAR_GRABBED_BY
; already stores the real grabber's own byte offset (its comment always
; documented this generic shape; only the code was hardcoded), so "follow
; the grabber" now does a real lookup through that offset instead of a
; hardcoded PlayerEntity_PosX read.
;
;   in:  none (DP-local self).
;   out: none. Clobbers A/X.
; ============================================================================
Character_Grab_Play:
    ; Defensive real sep here (not just the .a8 directive) -- this is
    ; called via jsl from CharacterEntity_Play once per entity per frame,
    ; and Poppy's linear width tracker has no way to verify the caller's
    ; real runtime width actually matches what's assumed textually at this
    ; label (a jsl target is invisible to poppy#386's own diagnostic, same
    ; class of gap that let Character_HitApply__TryGrab's __no path ship
    ; with a genuinely mismatched exit width). Forcing it here makes this
    ; routine correct regardless of what the caller's own real state is.
    sep #$20
.a8
    lda CHAR_GRABBED_BY
    cmp #$FF
    beq Character_Grab_Play__done

    ; --- sign-extend CHAR_GRAB_OFFSET into GrabDragOffset (.dw) ---
    lda CHAR_GRAB_OFFSET
    sta.l GrabDragOffset
    bpl Character_Grab_Play__off_pos
    lda #$FF
    bra Character_Grab_Play__off_hi_set
Character_Grab_Play__off_pos:
.a8
    lda #$00
Character_Grab_Play__off_hi_set:
.a8
    sta.l GrabDragOffsetHi

    ; --- self.CHAR_POS_X = grabber.CHAR_POS_X + GrabDragOffset -- real
    ; lookup through CHAR_GRABBED_BY's own actor slot ID now (was a hardcoded
    ; PlayerEntity_PosX read; see this routine's own header). ---
    rep #$31
.a16
.i16
    lda CHAR_GRABBED_BY
    jsr Character_Grab_SlotToOffset
    bcc Character_Grab_Play__release_invalid
    clc
    adc #CHAR_POS_X
    tax
    lda.l $7E0a00,x
    clc
    adc.l GrabDragOffset
    sta CHAR_POS_X

    ; --- decrement hold timer; release both sides at 0 ---
    sep #$20
.a8
    lda CHAR_GRAB_TIMER
    beq Character_Grab_Play__release   ; already expired (shouldn't happen
                                         ; given the -1-then-check order
                                         ; below, but a defensive check
                                         ; costs nothing)
    dec a
    sta CHAR_GRAB_TIMER
    bne Character_Grab_Play__done
Character_Grab_Play__release:
.a8
    ; Clear the grabber's own CHAR_GRAB_TARGET (real lookup through CHAR_
    ; GRABBED_BY, same reasoning as the follow-drag above -- was a
    ; hardcoded PlayerEntity_GrabTarget write, wrong once the grabber can
    ; be an AI entity).
    rep #$31
.a16
.i16
    lda CHAR_GRABBED_BY
    jsr Character_Grab_SlotToOffset
    bcc Character_Grab_Play__release_invalid
    clc
    adc #CHAR_GRAB_TARGET
    tax
    sep #$20
.a8
    lda #$FF
    sta.l $7E0a00,x
    sta CHAR_GRABBED_BY
    rtl
Character_Grab_Play__done:
.a8
    rtl
Character_Grab_Play__release_invalid:
.a8
    lda #$FF
    sta CHAR_GRABBED_BY
    rtl

; ============================================================================
; Character_Throw_Play -- G7 throw slice. Called from CharacterEntity_Play
; (bank 0) via jsl once per entity's own turn, right alongside Character_
; Grab_Play (same call site, DP-local self-addressing, D preserved across
; jsl) -- a no-op for any entity whose own CHAR_SELECTED isn't THROWN.
;
; Real check_gravity() semantics (DCurrent/openbor, engine/openbor.c) --
; IDENTICAL integration to Jump_PlayerTick__airborne (core/jump.pasm):
; position += velocity, velocity += gravity, every tick; land when
; position<=0 AND velocity<=0 (not position==0 alone). The only difference
; from jump's own copy is WHERE the state lives (CHAR_THROW_ZPOS/ZVEL,
; per-instance DP fields, vs. jump's player-only global cells) and what
; happens on landing: jump returns to idle/walk, a thrown victim lands
; into CHAR_SELECTED_FALL -- real BOR lands a tossed entity into the same
; knockdown reaction a landed hit would, reusing the existing fall/rise
; pipeline (Anim_Play_Fall, CHAR_FALL_STATE_TIMER machine) unchanged.
;
;   in:  none (DP-local self).
;   out: none. Clobbers A.
; ============================================================================
Character_Throw_Play:
    ; Same defensive real sep as Character_Grab_Play's own entry -- a jsl
    ; target is invisible to poppy#386's own diagnostic, so this routine
    ; must be correct regardless of the caller's actual real width.
    sep #$20
.a8
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_THROWN
    bne Character_Throw_Play__done

    rep #$31
.a16
.i16
    lda CHAR_THROW_ZPOS
    clc
    adc CHAR_THROW_ZVEL
    sta CHAR_THROW_ZPOS
    lda CHAR_THROW_ZVEL
    clc
    adc #JUMP_GRAVITY
    sta CHAR_THROW_ZVEL

    ; --- land check: position<=0 AND velocity<=0 ---
    lda CHAR_THROW_ZPOS
    beq Character_Throw_Play__zpos_le0
    bmi Character_Throw_Play__zpos_le0
    bra Character_Throw_Play__still_air
Character_Throw_Play__zpos_le0:
.a16
    lda CHAR_THROW_ZVEL
    beq Character_Throw_Play__land
    bmi Character_Throw_Play__land
Character_Throw_Play__still_air:
.a16
    sep #$20
.a8
    rtl
Character_Throw_Play__land:
.a16
    lda #0
    sta CHAR_THROW_ZPOS
    sta CHAR_THROW_ZVEL
    sep #$20
.a8
    ; notjustfreespecial.txt item 7 (land/autoland re-audit): real BOR.C
    ; doland() (engine/openbor.c) -- common_fall()'s own doland() trigger
    ; needs BLAST_TOSS (dothrow() always sets it) plus either autoland==1
    ; (neither shipped pak's MODELS.TXT sets this global -- confirmed
    ; absent, stays real default 0) OR damage_on_landing.attack_force==
    ; ATTACK_FORCE_LAND_COMMAND, which player_fall_check() (player-only,
    ; keys-based) sets every frame the PLAYER holds UP+JUMP while falling.
    ; So the one real, currently-reachable path in this project's shipped
    ; content is: the PLAYER, while THROWN (now reachable both ways since
    ; item 3's AI-throw), holding UP+A at the moment of landing. doland()'s
    ; own body (both its validanim and its no-anim-data branches) always
    ; ends in a SAFE landing -- straight to idle, skipping the ordinary
    ; knockdown/fall reaction common_fall() would otherwise give it. LEO
    ; is the only roster character with real `anim land` data (a single
    ; frame reusing his own rise01.gif sprite, `loop 0`) -- this project
    ; deliberately reuses the existing idle transition rather than
    ; building a new one-shot streaming/dispatch pathway for a single
    ; reused-art frame, same class of "no unique art, reuses an existing
    ; pathway" simplification already established for jumpattack2/throw's
    ; own swing art. The real, gameplay-relevant difference (a safe
    ; landing with no knockdown-vulnerability window, vs. an ordinary
    ; FALL landing) is preserved; the unique cosmetic frame is not
    ; rendered.
    lda CHAR_INPUT_DRIVEN
    cmp #1
    bne Character_Throw_Play__ordinary_land
    lda.l Input_press+1
    and #$08                        ; Up held
    beq Character_Throw_Play__ordinary_land
    lda.l Input_press
    and #$80                        ; A (jump) held
    beq Character_Throw_Play__ordinary_land
    lda #0
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    rtl
Character_Throw_Play__ordinary_land:
.a8
    ; OpenBOR's FALL sample is emitted by the ground-bounce path, not by
    ; damage entering the knockdown state. This ordinary thrown landing is
    ; the existing SNES equivalent; safe UP+A landings intentionally bypass
    ; it. Character_Throw_Play runs with D set to this entity's DP window,
    ; so recover the same byte-offset convention used by ApplyDamage before
    ; entering the bank-1 semantic helper.
    rep #$31
.a16
.i16
    tdc
    sec
    sbc #PlayerEntity_DpBase
    sta.l HitApply_EntityBase
    sep #$20
.a8
    jsl AudioSemantic_EmitFall
    lda #CHAR_SELECTED_FALL
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    rtl
Character_Throw_Play__done:
.a8
    rtl


; Audio-content pass: source-semantic diesound request emission. The
; generated roster/source tables and authored frame records are included by
; main.pasm immediately after this file; keeping them generated prevents the
; runtime dispatch from drifting from the measured Batch-B inventory. AudioSemantic_EntityRoster = $7E0A00 + CHAR_ROSTER_INDEX
AudioSemantic_EntityRoster = $7E0A00 + CHAR_ROSTER_INDEX

; Emit the source-backed FALL semantic at the documented SNES adaptation of
; the source bounce-impact event. This is the resident short-SFX backend; it does not
; use the long voice-0 stream. HitApply_EntityBase is set by the caller
; before this bank-1 helper is entered.
AudioSemantic_EmitFall:
    php
    rep #$30
.a16
.i16
    phx
    phy
    sep #$20
.a8
    rep #$20
.a16
    lda.l HitApply_EntityBase
    cmp #CHAR_ZP_LEN
    beq AudioSemantic_EmitFall__slot1
    cmp #CHAR_ZP_LEN*2
    beq AudioSemantic_EmitFall__slot2
    cmp #CHAR_ZP_LEN*3
    beq AudioSemantic_EmitFall__slot3
    sep #$20
.a8
    lda #0
    bra AudioSemantic_EmitFall__slot_store
AudioSemantic_EmitFall__slot1:
    sep #$20
.a8
    lda #1
    bra AudioSemantic_EmitFall__slot_store
AudioSemantic_EmitFall__slot2:
    sep #$20
.a8
    lda #2
    bra AudioSemantic_EmitFall__slot_store
AudioSemantic_EmitFall__slot3:
    sep #$20
.a8
    lda #3
AudioSemantic_EmitFall__slot_store:
    sta.l AudioSemantic_CurrentActorSlot
    rep #$20
.a16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_ROSTER_INDEX
    tax
    sep #$20
.a8
    lda.l $7E0a00,x
    sta.l AudioSemantic_CurrentRoster
    lda #AUDIO_SEMANTIC_FALL
    sta.l AudioSemantic_CurrentId
    rep #$20
.a16
    lda.l AudioSemantic_FallRequestCount
    inc
    sta.l AudioSemantic_FallRequestCount
    lda.l AudioSemantic_RequestCount
    inc
    sta.l AudioSemantic_RequestCount
    lda.l Nmi_FrameCounter
    cmp.l AudioSemantic_LastFrame
    beq AudioSemantic_EmitFall__same_frame
    sta.l AudioSemantic_LastFrame
    sep #$20
.a8
    lda #0
    sta.l AudioSemantic_FrameSequence
    bra AudioSemantic_EmitFall__record
AudioSemantic_EmitFall__same_frame:
    sep #$20
.a8
    lda.l AudioSemantic_FrameSequence
    inc
    sta.l AudioSemantic_FrameSequence
AudioSemantic_EmitFall__record:
    rep #$30
.a16
.i16
    lda.l AudioSemantic_TraceWriteIndex
    cmp #AudioSemantic_TraceCapacity
    bcs AudioSemantic_EmitFall__overflow
    and #$000F
    asl
    asl
    asl
    tax
    lda.l AudioSemantic_LastFrame
    sta.l AudioSemantic_TraceBase,x
    sep #$20
.a8
    lda.l AudioSemantic_FrameSequence
    sta.l AudioSemantic_TraceBaseSeq,x
    lda.l AudioSemantic_CurrentId
    sta.l AudioSemantic_TraceBaseId,x
    lda.l AudioSemantic_CurrentActorSlot
    sta.l AudioSemantic_TraceBaseSlot,x
    lda.l AudioSemantic_CurrentRoster
    sta.l AudioSemantic_TraceBaseRoster,x
    lda #AudioSemantic_EventFall
    sta.l AudioSemantic_TraceBaseEvent,x
    lda.l AudioSemantic_TraceWriteIndex
    inc
    sta.l AudioSemantic_TraceWriteIndex
    bra AudioSemantic_EmitFall__queue
AudioSemantic_EmitFall__overflow:
    sep #$20
.a8
AudioSemantic_EmitFall__queue:
    ; Tad_sfxQueue_sfx is a zero-page TAD queue. Bracket D=$0000 locally,
    ; preserving the bank-1 JSL/RTL boundary and the normal lower-ID priority.
    phd
    pea $0000
    pld
    lda #SFX_FALL_ID
    cmp Tad_sfxQueue_sfx
    bcs AudioSemantic_EmitFall__queue_done
    sta Tad_sfxQueue_sfx
    lda #TAD_CENTER_PAN
    sta Tad_sfxQueue_pan
AudioSemantic_EmitFall__queue_done:
    pld
    ply
    plx
    plp
    rtl

; Generic resident semantic/audio choke point for banked gameplay and menu
; callers. Entry is .a8 with A = stable semantic ID and X = generated local
; resident SFX ID. This bank-1 helper duplicates only the tiny queue operation
; instead of calling the bank-0 RTS routine across a bank boundary. The D=0
; bracket is required because entity callers may have a different direct-page
; window; the normal Tad_Process queue and lower-ID priority remain unchanged.
Audio_QueueResidentSemantic:
    php
    sep #$20
.a8
    sta.l AudioSemantic_CurrentId
    lda.l AudioSemantic_RequestCount
    inc
    sta.l AudioSemantic_RequestCount
    txa
    phd
    pea $0000
    pld
    cmp Tad_sfxQueue_sfx
    bcs Audio_QueueResidentSemantic__done
    sta Tad_sfxQueue_sfx
    lda #TAD_CENTER_PAN
    sta Tad_sfxQueue_pan
Audio_QueueResidentSemantic__done:
    pld
    plp
    rtl

; Queue the resident pickup sound for the real collection/reward edge.  Entry
; is .a8 with A = PICKUP_TYPE_*; A is restored so the caller can immediately
; pass the same type to Character_HitApply__ApplyPickup.
Audio_EmitPickup:
    php
    sep #$20
.a8
    pha
    cmp #PICKUP_TYPE_APPLE
    beq Audio_EmitPickup__get
    cmp #PICKUP_TYPE_MEAT
    beq Audio_EmitPickup__get
    cmp #PICKUP_TYPE_MONEY
    beq Audio_EmitPickup__money
    cmp #PICKUP_TYPE_GOLD
    beq Audio_EmitPickup__money
    cmp #PICKUP_TYPE_ONEUP
    beq Audio_EmitPickup__oneup
    bra Audio_EmitPickup__restore
Audio_EmitPickup__get:
    lda #AUDIO_SEMANTIC_GET
    ldx #SFX_GET_ID
    jsl Audio_QueueResidentSemantic
    bra Audio_EmitPickup__restore
Audio_EmitPickup__money:
    lda #AUDIO_SEMANTIC_MONEY
    ldx #SFX_MONEY_ID
    jsl Audio_QueueResidentSemantic
    bra Audio_EmitPickup__restore
Audio_EmitPickup__oneup:
    lda #AUDIO_SEMANTIC_ONEUP
    ldx #SFX_ONEUP_ID
    jsl Audio_QueueResidentSemantic
Audio_EmitPickup__restore:
    pla
    plp
    rtl

Audio_EmitPunch:
    sep #$20
.a8
    lda CHAR_SELECTED
    cmp #2
    bne Audio_EmitPunch__done
    lda CHAR_ATTACK_VARIANT
    cmp #GET_MOVE_VARIANT          ; GET shares the attack animation state
    beq Audio_EmitPunch__done      ; but is not an attack swing
    cmp #6                         ; slide is an accepted ground movement
    beq Audio_EmitPunch__done      ; edge with authored DASH frame audio
    lda CHAR_FRAME_INDEX
    cmp #$FF
    bne Audio_EmitPunch__done
    lda #AUDIO_SEMANTIC_PUNCH
    ldx #SFX_PUNCH_ID
    jsl Audio_QueueResidentSemantic
Audio_EmitPunch__done:
    rtl

; JSL/RTL. HitApply_EntityBase identifies the dying entity. Preserves A/X/Y
; and processor width.
AudioSemantic_EmitDiesound:
    php
    rep #$30
.a16
.i16
    phx
    phy
    sep #$20
.a8
    ; Derive the fixed physical target slot from the offset saved by
    ; Character_HitApply__ApplyDamage. This avoids relying on D across the
    ; bank-1 TryGrab/ApplyDamage call chain.
    rep #$20
.a16
    lda.l HitApply_EntityBase
    cmp #CHAR_ZP_LEN
    beq AudioSemantic_EmitDiesound__slot1
    cmp #CHAR_ZP_LEN*2
    beq AudioSemantic_EmitDiesound__slot2
    cmp #CHAR_ZP_LEN*3
    beq AudioSemantic_EmitDiesound__slot3
    sep #$20
.a8
    lda #0
    bra AudioSemantic_EmitDiesound__slot_store
AudioSemantic_EmitDiesound__slot1:
    sep #$20
.a8
    lda #1
    bra AudioSemantic_EmitDiesound__slot_store
AudioSemantic_EmitDiesound__slot2:
    sep #$20
.a8
    lda #2
    bra AudioSemantic_EmitDiesound__slot_store
AudioSemantic_EmitDiesound__slot3:
    sep #$20
.a8
    lda #3
AudioSemantic_EmitDiesound__slot_store:
    sta.l AudioSemantic_CurrentActorSlot
    rep #$20
.a16
    lda.l HitApply_EntityBase
    ldx #0
    tax
    sep #$20
.a8
    lda.l AudioSemantic_EntityRoster,x
    cmp #21
    bcc AudioSemantic_EmitDiesound__roster_ok
    jmp AudioSemantic_EmitDiesound__done
AudioSemantic_EmitDiesound__roster_ok:
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    sta.l AudioSemantic_CurrentRoster
    lda.l AudioSemantic_DiesoundByRoster,x
    cmp #AUDIO_SEMANTIC_NONE
    bne AudioSemantic_EmitDiesound__identity_ok
    jmp AudioSemantic_EmitDiesound__done
AudioSemantic_EmitDiesound__identity_ok:
    .a8
    sta.l AudioSemantic_CurrentId
    cmp #AUDIO_SEMANTIC_FOOTDIE
    bne AudioSemantic_EmitDiesound__not_foot
    lda.l AudioSemantic_FootDieRequestCount
    inc
    sta.l AudioSemantic_FootDieRequestCount
AudioSemantic_EmitDiesound__not_foot:
    lda.l AudioSemantic_DiesoundSourceByRoster,x
    sta.l AudioStream_SourceId
    cmp #AUDIO_STREAM_SOURCE_NONE
    beq AudioSemantic_EmitDiesound__no_stream
    jsr AudioSemantic_StreamBackendPolicy
AudioSemantic_EmitDiesound__no_stream:
    lda.l AudioSemantic_RequestCount
    inc
    sta.l AudioSemantic_RequestCount
    rep #$20
.a16
    lda.l Nmi_FrameCounter
    cmp.l AudioSemantic_LastFrame
    beq AudioSemantic_EmitDiesound__same_frame
    sta.l AudioSemantic_LastFrame
    sep #$20
.a8
    lda #0
    sta.l AudioSemantic_FrameSequence
    bra AudioSemantic_EmitDiesound__record
AudioSemantic_EmitDiesound__same_frame:
    sep #$20
.a8
    lda.l AudioSemantic_FrameSequence
    inc
    sta.l AudioSemantic_FrameSequence
AudioSemantic_EmitDiesound__record:
    rep #$30
    .a16
    .i16
    lda.l AudioSemantic_TraceWriteIndex
    cmp #AudioSemantic_TraceCapacity
    bcs AudioSemantic_EmitDiesound__overflow
    and #$000F
    asl
    asl
    asl
    tax
    lda.l AudioSemantic_LastFrame
    sta.l AudioSemantic_TraceBase,x
    sep #$20
.a8
    lda.l AudioSemantic_FrameSequence
    sta.l AudioSemantic_TraceBaseSeq,x
    lda.l AudioSemantic_CurrentId
    sta.l AudioSemantic_TraceBaseId,x
    lda.l AudioSemantic_CurrentActorSlot
    sta.l AudioSemantic_TraceBaseSlot,x
    lda.l AudioSemantic_CurrentRoster
    sta.l AudioSemantic_TraceBaseRoster,x
    lda #AudioSemantic_EventDiesound
    sta.l AudioSemantic_TraceBaseEvent,x
    lda.l AudioSemantic_TraceWriteIndex
    inc
    sta.l AudioSemantic_TraceWriteIndex
    bra AudioSemantic_EmitDiesound__done
AudioSemantic_EmitDiesound__overflow:
    lda.l AudioSemantic_TraceOverflow
    inc
    sta.l AudioSemantic_TraceOverflow
AudioSemantic_EmitDiesound__done:
    ply
    plx
    plp
    rtl

; Shared stream backend policy for diesounds and authored frame sounds. The
; source ID is already in AudioStream_SourceId. The existing one-voice
; transport remains serialized: same-frame requests coalesce and requests
; arriving while voice 0 is active are counted as suppressed.
AudioSemantic_StreamBackendPolicy:
    php
    rep #$30
.a16
.i16
    lda.l Nmi_FrameCounter
    cmp.l AudioSemantic_FootDieStreamFrame
    beq AudioSemantic_StreamBackendPolicy__same_frame
    sep #$20
.a8
    lda.l AudioSemantic_FootDieStreamActive
    bne AudioSemantic_StreamBackendPolicy__suppressed
    rep #$20
.a16
    lda.l Nmi_FrameCounter
    sta.l AudioSemantic_FootDieStreamFrame
    sep #$20
.a8
    lda #1
    sta.l AudioSemantic_FootDieStreamActive
    lda.l AudioStream_Enable
    beq AudioSemantic_StreamBackendPolicy__count_start
    ; Tad_StreamStartSource takes A=source ID.  The enable check above leaves
    ; A=1, which otherwise aliases every authored stream to source 1.
    lda.l AudioStream_SourceId
    jsr Tad_StreamStartSource
    lda.l AudioStream_Enable
    beq AudioSemantic_StreamBackendPolicy__count_start
    jsl Tad_StreamSendFootdieFrame
AudioSemantic_StreamBackendPolicy__count_start:
    rep #$20
.a16
    lda.l AudioSemantic_StreamRequestCount
    inc
    sta.l AudioSemantic_StreamRequestCount
    sep #$20
.a8
    lda.l AudioStream_SourceId
    bne AudioSemantic_StreamBackendPolicy__done
    rep #$20
.a16
    lda.l AudioSemantic_FootDieStreamStartCount
    inc
    sta.l AudioSemantic_FootDieStreamStartCount
    bra AudioSemantic_StreamBackendPolicy__done
AudioSemantic_StreamBackendPolicy__same_frame:
    sep #$20
.a8
    rep #$20
.a16
    lda.l AudioSemantic_StreamSuppressedCount
    inc
    sta.l AudioSemantic_StreamSuppressedCount
    sep #$20
.a8
    lda.l AudioStream_SourceId
    bne AudioSemantic_StreamBackendPolicy__done
    rep #$20
.a16
    lda.l AudioSemantic_FootDieSameFrameCoalescedCount
    inc
    sta.l AudioSemantic_FootDieSameFrameCoalescedCount
    bra AudioSemantic_StreamBackendPolicy__done
AudioSemantic_StreamBackendPolicy__suppressed:
    rep #$20
.a16
    lda.l AudioSemantic_StreamSuppressedCount
    inc
    sta.l AudioSemantic_StreamSuppressedCount
    sep #$20
.a8
    lda.l AudioStream_SourceId
    bne AudioSemantic_StreamBackendPolicy__done
    rep #$20
.a16
    lda.l AudioSemantic_FootDieWhileActiveSuppressedCount
    inc
    sta.l AudioSemantic_FootDieWhileActiveSuppressedCount
AudioSemantic_StreamBackendPolicy__done:
    plp
    rts

; Compatibility name retained for existing FOOTDIE diagnostics. New callers
; use the generic policy above; this alias does not create a second backend.
AudioSemantic_FootDieBackendPolicy = AudioSemantic_StreamBackendPolicy

; JSL/RTL. LEO's shipped THROW.WAV belongs to source throw-animation frames,
; but the documented SNES throw adaptation intentionally has no unique throw
; art.  Its accepted toss edge is therefore the one production audio edge.
AudioSemantic_EmitThrow:
    php
    sep #$20
.a8
    lda #AUDIO_SEMANTIC_THROW
    sta.l AudioSemantic_CurrentId
    lda #13                         ; generated Batch-B THROW stream source
    sta.l AudioStream_SourceId
    rep #$20
.a16
    lda.l AudioSemantic_FrameSoundRequestCount
    inc
    sta.l AudioSemantic_FrameSoundRequestCount
    lda.l AudioSemantic_RequestCount
    inc
    sta.l AudioSemantic_RequestCount
    sep #$20
.a8
    jsr AudioSemantic_StreamBackendPolicy
    plp
    rtl

; JSL/RTL. Generic roster-indexed authored pain sound at the accepted
; nonlethal pain transition. A $FF generated row is a deliberate no-op.
AudioSemantic_EmitPainSound:
    php
    rep #$30
.a16
.i16
    lda.l HitApply_EntityBase
    clc
    adc #CHAR_ROSTER_INDEX
    tax
    sep #$20
.a8
    lda.l $7E0A00,x
    tax
    lda.l AudioSemantic_PainByRoster,x
    cmp #$FF
    beq AudioSemantic_EmitPainSound__done
    sta.l AudioSemantic_CurrentId
    lda.l AudioSemantic_PainSourceByRoster,x
    sta.l AudioStream_SourceId
    rep #$20
.a16
    lda.l AudioSemantic_FrameSoundRequestCount
    inc
    sta.l AudioSemantic_FrameSoundRequestCount
    lda.l AudioSemantic_RequestCount
    inc
    sta.l AudioSemantic_RequestCount
    sep #$20
.a8
    jsr AudioSemantic_StreamBackendPolicy
AudioSemantic_EmitPainSound__done:
    plp
    rtl

; Generic authored animation-frame sound dispatch. Msu1_LoadFrame calls this
; once after the frame DMA rows are queued. Generated records carry the exact
; roster/selected/variant/jump-mode/frame condition plus either a resident
; local ID or a stream source ID. A record is emitted at most once per NMI
; frame, preventing repeated frame-loader calls from duplicating one event.
Audio_FrameSoundDispatch:
    php
    rep #$30
.a16
.i16
    phx
    phy
    phd
    lda.l AudioSemantic_FrameSoundEntityBase
    tcd
    sep #$20
.a8
    ldx #0
Audio_FrameSoundDispatch__scan:
    rep #$20
.a16
    cpx #(AUDIO_FRAME_SOUND_RECORD_COUNT * AUDIO_FRAME_SOUND_RECORD_SIZE)
    bcc Audio_FrameSoundDispatch__scan_continue
    brl Audio_FrameSoundDispatch__done
Audio_FrameSoundDispatch__scan_continue:
    sep #$20
.a8
    lda CHAR_ROSTER_INDEX
    cmp.l Audio_FrameSoundRecords,x
    beq Audio_FrameSoundDispatch__roster_ok
    brl Audio_FrameSoundDispatch__next
Audio_FrameSoundDispatch__roster_ok:
    inx
    lda.l Audio_FrameSoundRecords,x
    dex
    cmp CHAR_SELECTED
    beq Audio_FrameSoundDispatch__selected_ok
    brl Audio_FrameSoundDispatch__next
Audio_FrameSoundDispatch__selected_ok:
    inx
    inx
    lda.l Audio_FrameSoundRecords,x
    dex
    dex
    cmp #$FF
    beq Audio_FrameSoundDispatch__variant_ok
    cmp CHAR_ATTACK_VARIANT
    beq Audio_FrameSoundDispatch__variant_ok
    brl Audio_FrameSoundDispatch__next
Audio_FrameSoundDispatch__variant_ok:
    inx
    inx
    inx
    lda.l Audio_FrameSoundRecords,x
    dex
    dex
    dex
    cmp #$FF
    beq Audio_FrameSoundDispatch__jump_mode_ok
    cmp.l Player_JumpAnimMode
    beq Audio_FrameSoundDispatch__jump_mode_ok
    brl Audio_FrameSoundDispatch__next
Audio_FrameSoundDispatch__jump_mode_ok:
    inx
    inx
    inx
    inx
    lda.l Audio_FrameSoundRecords,x
    dex
    dex
    dex
    dex
    cmp CHAR_FRAME_INDEX
    beq Audio_FrameSoundDispatch__frame_ok
    brl Audio_FrameSoundDispatch__next
Audio_FrameSoundDispatch__frame_ok:

    ; Deduplicate only the same record in the same NMI frame. Different
    ; authored sound records may legitimately share one frame.
    rep #$20
.a16
    lda.l Nmi_FrameCounter
    cmp.l AudioSemantic_FrameSoundLastFrame
    beq Audio_FrameSoundDispatch__same_frame
    sta.l AudioSemantic_FrameSoundLastFrame
    ; LastKey is scoped to LastFrame.  A matching record must be eligible
    ; again as soon as a later NMI begins.
    sep #$20
.a8
    lda #$FF
    sta.l AudioSemantic_FrameSoundLastKey
    rep #$20
.a16
Audio_FrameSoundDispatch__same_frame:
    txa
    lsr
    lsr
    lsr
    sep #$20
.a8
    cmp.l AudioSemantic_FrameSoundLastKey
    bne Audio_FrameSoundDispatch__emit
    brl Audio_FrameSoundDispatch__done
Audio_FrameSoundDispatch__emit:
    sta.l AudioSemantic_FrameSoundLastKey
    rep #$20
.a16
    lda.l AudioSemantic_FrameSoundRequestCount
    inc
    sta.l AudioSemantic_FrameSoundRequestCount
    sep #$20
.a8
    inx
    inx
    inx
    inx
    inx
    lda.l Audio_FrameSoundRecords,x
    dex
    dex
    dex
    dex
    dex
    ; DEX restores the record offset but also overwrites Z.  Re-test the
    ; generated backend byte after restoring X: 0 is resident, 1 is stream.
    cmp #0
    bne Audio_FrameSoundDispatch__stream
    brl Audio_FrameSoundDispatch__resident

    ; Stream record: set the stable semantic/source identity, count the
    ; semantic request, then use the same serialized stream policy as death.
Audio_FrameSoundDispatch__stream:
    inx
    inx
    inx
    inx
    inx
    inx
    inx
    lda.l Audio_FrameSoundRecords,x
    dex
    dex
    dex
    dex
    dex
    dex
    dex
    sta.l AudioSemantic_CurrentId
    lda.l AudioStream_SourceId
    inx
    inx
    inx
    inx
    inx
    inx
    lda.l Audio_FrameSoundRecords,x
    dex
    dex
    dex
    dex
    dex
    dex
    sta.l AudioStream_SourceId
    rep #$20
.a16
    lda.l AudioSemantic_RequestCount
    inc
    sta.l AudioSemantic_RequestCount
    sep #$20
.a8
    jsr AudioSemantic_StreamBackendPolicy
    bra Audio_FrameSoundDispatch__done

Audio_FrameSoundDispatch__resident:
    ; Save the record offset in Y while X is replaced with the generated
    ; local resident ID for Audio_QueueResidentSemantic.
    phx
    inx
    inx
    inx
    inx
    inx
    inx
    inx
    lda.l Audio_FrameSoundRecords,x
    dex
    dex
    dex
    dex
    dex
    dex
    dex
    pha
    inx
    inx
    inx
    inx
    inx
    inx
    lda.l Audio_FrameSoundRecords,x
    dex
    dex
    dex
    dex
    dex
    dex
    tax
    pla
    jsl Audio_QueueResidentSemantic
    plx
    bra Audio_FrameSoundDispatch__done

Audio_FrameSoundDispatch__next:
    rep #$20
.a16
    txa
    clc
    adc #AUDIO_FRAME_SOUND_RECORD_SIZE
    tax
    brl Audio_FrameSoundDispatch__scan
Audio_FrameSoundDispatch__done:
    pld
    ply
    plx
    plp
    rtl

; Extra bounded actor timer maintenance lives in this bank to keep the
; bank-0 gameplay loop within its fixed NMI header window. This is the same
; per-frame decrement policy used by slots 1-3; only slots 4/5 are handled
; here because the established four-actor path remains unchanged.
Game_State_TickExtraActorTimers:
    php
    sep #$20
.a8
    lda.l Entity4_InvulnFrames
    beq Game_State_TickExtraActorTimers__i4
    dec a
    sta.l Entity4_InvulnFrames
Game_State_TickExtraActorTimers__i4:
    lda.l Entity5_InvulnFrames
    beq Game_State_TickExtraActorTimers__k4
    dec a
    sta.l Entity5_InvulnFrames
Game_State_TickExtraActorTimers__k4:
    lda.l Entity4_KnockdownTimer
    beq Game_State_TickExtraActorTimers__k5
    dec a
    sta.l Entity4_KnockdownTimer
Game_State_TickExtraActorTimers__k5:
    lda.l Entity5_KnockdownTimer
    beq Game_State_TickExtraActorTimers__done
    dec a
    sta.l Entity5_KnockdownTimer
Game_State_TickExtraActorTimers__done:
    plp
    rtl

Game_State_AnyActorAlive:
    sep #$20
.a8
    lda #$A5
    sta.l G12_StageTrace_Entry
    lda.l $7E0AA8
    sta.l G12_StageTrace_Hp1
    bne Game_State_AnyActorAlive__some
    lda.l $7E0B2D
    sta.l G12_StageTrace_Hp2
    bne Game_State_AnyActorAlive__some
    lda.l $7E0BB2
    sta.l G12_StageTrace_Hp3
    bne Game_State_AnyActorAlive__some
    lda.l $7E0C37
    sta.l G12_StageTrace_Hp4
    bne Game_State_AnyActorAlive__some
    lda.l $7E0CBC
    sta.l G12_StageTrace_Hp5
    beq Game_State_AnyActorAlive__none
Game_State_AnyActorAlive__some:
    lda #$01
    sta.l G12_StageTrace_Carry
    sec
    rtl
Game_State_AnyActorAlive__none:
    lda #$00
    sta.l G12_StageTrace_Carry
    clc
    rtl
