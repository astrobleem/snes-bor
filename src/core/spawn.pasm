; ============================================================================
; core/spawn.pasm — convert-time spawn table, single global queue
;
; Spawn-table phase (plan.md, 2026-08-16, user instruction "do the spawn-
; table route"): this project's entity system hardcodes exactly 4 entities
; (player + 3 AI, fixed EntityN_Base WRAM addresses -- see main.pasm's own
; "don't build a general entity-lookup system" note), but a real BOR level
; script names far more enemies across its full timeline than that (33
; spawn events in stage 1A alone, tools/bg_converter/spawn_parse.py). The
; chosen design (see this session's advisor consult) is a SINGLE GLOBAL
; QUEUE: one running index (Spawn_Index) walks a flat table of (trigger_x,
; spawn_x, spawn_y, facing) records, in the level's own trigger order. Each
; frame, if the camera (Screen_PosX) has reached the pending record's
; trigger_x AND at least one AI slot is free, that slot is (re)spawned into
; and the index advances; otherwise the record stays pending and is
; retried next frame. This reproduces the source level's wave clustering
; (six simultaneous `at=960` spawns fill all 3 slots, hold the rest
; pending, drain as kills free slots) without partitioning events across
; slots, which would scatter a wave into unrelated trickle spawns.
;
; "Free slot" is CHAR_HP==0 -- this project's existing soft-kill sentinel
; (phase11_damage_system_softkill memory: dead AI stops acting/hitting,
; sprite hides, CHAR_HP==0 is sticky) doubles as "not currently spawned."
; CharacterEntity_Init now boots every AI role at HP=0 for exactly this
; reason (see its own comment) -- entities stay hidden/inert until this
; table places them, instead of standing fully alive from frame 1.
;
; Deliberate scope cuts (see build_spawn_table.py's own docstring for the
; full reasoning): `wait`/`group` events are parsed but not emitted into
; this table (no scroll-blocking-until-clear, no respawn-pool sizing).
; Every record always spawns at full HP (CHAR_HP_MAX) -- the source
; level's per-spawn `health` override is not modeled. Every record spawns
; a generic AI-seeking enemy using whichever roster character is already
; wired to the slot it lands in -- the source level's specific character
; identity (Shermie, Yashiro, ...) and non-enemy spawns (the `1up` pickup,
; the `trash` breakable prop -- this engine has no pickup/prop entity
; class) are not modeled either. Position/timing fidelity is the goal;
; character/entity-kind identity is explicitly not.
;
; The table itself is NOT a ROM .incbin read via indexed addressing --
; CLAUDE.md documents a confirmed Poppy bug where indexed-long addressing
; to a ROM data label computes a wrong base address, and this codebase has
; no existing, proven use of indexed ROM reads to build on. Instead the
; table ships in bor.msu (tools/bor_converter/pack_msu_roster.py's spawn
; section, appended after the BG/FP sections) and Spawn_Init reads it
; sequentially into WRAM at boot, the exact same seek-then-sequential-read
; shape as Bg_LoadSceneFp_Streaming's own boot-time header load. Every
; runtime access after that is indexed WRAM access via `.l Label,x`, the
; pattern already proven throughout this codebase (Hud_Play's HudStaging,x
; loop, EntityN_* struct field access).
;
; SPAWN_MSU_OFFSET/SPAWN_COUNT below are hand-synced build-time constants,
; not computed by this file -- the spawn blob's file offset depends on
; every character/BG/FP blob packed before it in bor.msu, which main.pasm
; has no way to know. build_rom.py's check_spawn_constants() cross-checks
; these against what tools/bor_converter/pack_msu_roster.py actually
; computed and aborts the build loudly on mismatch -- same accepted-risk,
; checked-not-automatic pattern as this file's own RESET/NMI/IRQ vector
; constants.
;
; Uses global (not @-local) labels throughout, same convention as every
; other core/*.pasm file (see core/random.pasm's header for why).
; ============================================================================

SPAWN_MSU_OFFSET = $0270A0   ; from build_rom.py's check_spawn_constants -- must be
                              ; re-synced (rerun the build, copy its reported value)
                              ; any time an earlier roster/BG/FP asset changes size,
                              ; or the shipped level changes (Phase 14).
SPAWN_COUNT      = 28        ; record count from build_spawn_table.py's own printed
                              ; output -- 28 for stage 1B (Phase 14, plan.md 2.14),
                              ; was 33 for stage 1A (Phase 13)

; --- WRAM layout: $7E5500 + SPAWN_COUNT*7 bytes (196 for stage 1B's 28
; records), first free region after Anim_*/CharSelect_*'s $7E53B0-$7E53C9
; block (verified collision-free by grep -- see main.pasm's own $7E53B6 note
; for the same verification convention). ---
Spawn_Index         = $7E5500   ; .db -- next pending record index, 0..SPAWN_COUNT
Spawn_ScratchIdx    = $7E5501   ; .dw -- zero-extended copy of Spawn_Index for the *7 multiply
Spawn_ScratchX      = $7E5503   ; .dw -- captured spawn_x, held across slot search (clobbers X)
Spawn_ScratchY      = $7E5505   ; .db -- captured spawn_y
Spawn_ScratchFacing = $7E5506   ; .db -- captured facing_left
SpawnTable_Wram     = $7E5507   ; SPAWN_COUNT*7 bytes, record layout below

; Record layout (7 bytes, LE), matches build_spawn_table.py exactly:
;   +0-1  trigger_x   (u16) -- SNES world-px camera position that arms this record
;   +2-3  spawn_x     (u16) -- SNES world-px initial position
;   +4    spawn_y     (u8)
;   +5    facing_left (u8)  -- CHAR_FACING_LEFT convention (0=right,1=left)
;   +6    reserved

; Spawn_Init -- call once at boot, after MSU-1 is generally up and after
; Bg_LoadSceneFp_Streaming (mirrors its exact seek+sequential-read shape;
; see main.pasm's boot sequence for the call site). A one-time blocking
; read outside the per-frame Msu1_LoadFrame path, same as that routine --
; does NOT touch Msu1_StreamBusy's one-stream-per-frame budget.
Spawn_Init:
    php
    sei
    sep #$20
.a8
    lda #0
    sta.l Spawn_Index

    lda #<(SPAWN_MSU_OFFSET & $0000FF)
    sta $2000
    lda #<((SPAWN_MSU_OFFSET >> 8) & $0000FF)
    sta $2001
    lda #<((SPAWN_MSU_OFFSET >> 16) & $0000FF)
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Spawn_Init__seek_busy:
    lda $2000
    bmi Spawn_Init__seek_busy

    rep #$31
.a16
.i16
    ldx #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Spawn_Init__read:
    sep #$20
.a8
    lda $2001
    sta.l SpawnTable_Wram,x
    rep #$31
.a16
.i16
    inx
    cpx #(SPAWN_COUNT*7)
    bcc Spawn_Init__read

    plp
    rts

; Spawn_Play -- call once per scpu_main_loop iteration. Walks the single
; global queue: no-ops if the queue is exhausted, if the pending record's
; trigger hasn't been reached, or if no AI slot is currently free (CHAR_HP
; nonzero for all of Entity1/2/3) -- in every no-op case, Spawn_Index does
; NOT advance, so the same record is retried next frame.
Spawn_Play:
    php
    sep #$20
.a8
    lda.l Spawn_Index
    cmp #SPAWN_COUNT
    bcc Spawn_Play__active
    plp
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Spawn_Play__active:
    sep #$20
.a8
    sta.l Spawn_ScratchIdx      ; A already holds the index from the cmp above
    lda #0
    sta.l Spawn_ScratchIdx+1

    rep #$31
.a16
.i16
    lda.l Spawn_ScratchIdx
    asl a
    asl a
    asl a                       ; index*8
    sec
    sbc.l Spawn_ScratchIdx      ; index*8 - index = index*7
    tax                         ; X = this record's base offset, 0..224

    lda Screen_PosX
    cmp.l SpawnTable_Wram,x     ; Screen_PosX - trigger_x
    bcs Spawn_Play__triggered   ; Screen_PosX >= trigger_x: armed, fall through
    brl Spawn_Play__not_yet     ; Screen_PosX < trigger_x: stay pending -- brl,
                                 ; not bcc, since Spawn_Play__not_yet is defined
                                 ; at the very end of this routine, well past
                                 ; find_slot/slot1/slot2/slot3/advance below (a
                                 ; real "Branch target out of range" build error
                                 ; here, reported misleadingly as "main.pasm:167"
                                 ; -- Poppy's .include error reporting uses the
                                 ; included file's own line number under the
                                 ; main.pasm filename, not a location in
                                 ; main.pasm itself; spawn.pasm's own line 167
                                 ; was this exact bcc)
Spawn_Play__triggered:

    ; --- capture spawn_x/spawn_y/facing before X gets reused for slot
    ; search below. Advances X by fixed +1 steps rather than a Symbol+N,x
    ; operand -- this project avoids Symbol+N arithmetic feeding an
    ; instruction operand (main.pasm's CHAR_POS_X_HI note). ---
    inx
    inx                         ; X -> record+2 (spawn_x)
    lda.l SpawnTable_Wram,x
    sta.l Spawn_ScratchX
    inx
    inx                         ; X -> record+4 (spawn_y)
    sep #$20
.a8
    lda.l SpawnTable_Wram,x
    sta.l Spawn_ScratchY
    inx                         ; X -> record+5 (facing_left)
    lda.l SpawnTable_Wram,x
    sta.l Spawn_ScratchFacing

Spawn_Play__find_slot:
    sep #$20
.a8
    lda.l Entity1_Hp
    beq Spawn_Play__slot1
    lda.l Entity2_Hp
    beq Spawn_Play__slot2
    lda.l Entity3_Hp
    beq Spawn_Play__slot3
    plp
    rts                         ; no free slot -- record stays pending
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Spawn_Play__slot1:
    rep #$31
.a16
.i16
    lda.l Spawn_ScratchX
    sta.l Entity1_PosX
    sep #$20
.a8
    lda.l Spawn_ScratchY
    sta.l Entity1_PosY
    lda.l Spawn_ScratchFacing
    sta.l Entity1_FacingLeft
    lda #CHAR_HP_MAX
    sta.l Entity1_Hp
    bra Spawn_Play__advance
    nop
Spawn_Play__slot2:
    rep #$31
.a16
.i16
    lda.l Spawn_ScratchX
    sta.l Entity2_PosX
    sep #$20
.a8
    lda.l Spawn_ScratchY
    sta.l Entity2_PosY
    lda.l Spawn_ScratchFacing
    sta.l Entity2_FacingLeft
    lda #CHAR_HP_MAX
    sta.l Entity2_Hp
    bra Spawn_Play__advance
    nop
Spawn_Play__slot3:
    rep #$31
.a16
.i16
    lda.l Spawn_ScratchX
    sta.l Entity3_PosX
    sep #$20
.a8
    lda.l Spawn_ScratchY
    sta.l Entity3_PosY
    lda.l Spawn_ScratchFacing
    sta.l Entity3_FacingLeft
    lda #CHAR_HP_MAX
    sta.l Entity3_Hp
    nop

Spawn_Play__advance:
    sep #$20
.a8
    lda.l Spawn_Index
    inc a
    sta.l Spawn_Index
    plp
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Spawn_Play__not_yet:
    plp
    rts
