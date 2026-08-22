; ============================================================================
; core/spawn.pasm — per-stage spawn table, single global queue
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
; table ships in bor.msu (tools/bor_converter/pack_msu_roster.py's per-stage
; spawn section, hung off each stage's own bg record) and Spawn_Init reads
; it sequentially into WRAM, the exact same seek-then-sequential-read shape
; as Bg_LoadSceneFp_Streaming's own boot-time header load. Every runtime
; access after that is indexed WRAM access via `.l Label,x`, the pattern
; already proven throughout this codebase (Hud_Play's HudStaging,x loop,
; EntityN_* struct field access).
;
; Phase G4 (plan_game.md 4, 2026-08-21): generalized from ONE hand-synced
; global table (SPAWN_MSU_OFFSET/SPAWN_COUNT compile-time constants,
; checked at build time by build_rom.py's now-deleted
; check_spawn_constants()) to a real per-stage table, discovered at
; runtime. A stage transition can't hand-sync a constant per stage the way
; the old single-level build did -- CLAUDE.md's roadmap note and this
; phase's own "watch out" both call this out explicitly. Bg_LoadScene
; (main.pasm) now reads THIS stage's own spawn_offset (u32)/spawn_count
; (u16) straight out of its bg record (pack_msu_roster.py's v6 fields,
; +32/+36) and copies them into Spawn_MsuOffsetLo/Hi/Spawn_Count below,
; every time it loads a stage (at boot for stage 0, and again from
; Stage_Load for every later transition) -- Spawn_Init then just reads
; those WRAM cells instead of a compile-time constant, so it is exactly as
; re-runnable as Bg_LoadScene itself.
;
; SpawnTable_Wram is sized for SPAWN_MAX_RECORDS (40), not any one stage's
; own count -- the largest packed stage today is stage 1A's 33 records;
; 40 leaves headroom for a slightly bigger level without another WRAM-
; layout pass. Grep-verified collision-free against every other WRAM label
; up to $7E5620 (see this file's own WRAM layout comment below).
;
; Uses global (not @-local) labels throughout, same convention as every
; other core/*.pasm file (see core/random.pasm's header for why).
; ============================================================================

SPAWN_MAX_RECORDS = 40       ; largest packed stage today is 33 (stage 1A);
                              ; see this file's header for why this isn't
                              ; tied to any one stage's real count

; --- WRAM layout: $7E5500 + SPAWN_MAX_RECORDS*7 bytes (280 for 40 records),
; first free region after Anim_*/CharSelect_*'s $7E53B0-$7E53C9 block
; (verified collision-free by grep -- see main.pasm's own $7E53B6 note for
; the same verification convention). Ends at $7E561D, well clear of any
; other module's WRAM (grep-verified 2026-08-21: nothing else claims
; $7E5500-$7E5FFF). ---
Spawn_Index         = $7E5500   ; .db -- next pending record index, 0..Spawn_Count
Spawn_Count         = $7E5501   ; .db -- this stage's own record count, read
                                 ; from its bg record by Bg_LoadScene (was a
                                 ; compile-time SPAWN_COUNT constant)
Spawn_CountX7       = $7E5502   ; .dw -- Spawn_Count*7 cached at Init time,
                                 ; so Spawn_Play doesn't re-multiply every call
Spawn_MsuOffsetLo   = $7E5504   ; .dw -- this stage's spawn blob's 24-bit MSU
Spawn_MsuOffsetHi   = $7E5506   ; .db    file offset (was SPAWN_MSU_OFFSET),
                                 ; set by Bg_LoadScene before Spawn_Init runs
Spawn_ScratchIdx    = $7E5507   ; .dw -- zero-extended copy of Spawn_Index for the *7 multiply
Spawn_ScratchX      = $7E5509   ; .dw -- captured spawn_x, held across slot search (clobbers X)
Spawn_ScratchY      = $7E550B   ; .db -- captured spawn_y
Spawn_ScratchFacing = $7E550C   ; .db -- captured facing_left
Spawn_LastTriggerX  = $7E550D   ; .dw -- trigger_x of this stage's LAST record
                                 ; (spawn tables are packed in ascending
                                 ; trigger order -- see this file's header),
                                 ; cached by Spawn_Init. Phase G4's win-
                                 ; condition soft camera-hold reads this
                                 ; (core/game_state.pasm's Stage_Load) --
                                 ; see that file's header for why a hold
                                 ; boundary derived from the level's own
                                 ; data is used instead of a separate
                                 ; hand-authored "combat zone" table.
SpawnTable_Wram     = $7E550F   ; SPAWN_MAX_RECORDS*7 bytes, record layout below

; Record layout (7 bytes, LE), matches build_spawn_table.py exactly:
;   +0-1  trigger_x   (u16) -- SNES world-px camera position that arms this record
;   +2-3  spawn_x     (u16) -- SNES world-px initial position
;   +4    spawn_y     (u8)
;   +5    facing_left (u8)  -- CHAR_FACING_LEFT convention (0=right,1=left)
;   +6    reserved

; Spawn_Init -- call once per stage load (boot AND every Stage_Load
; transition), after Bg_LoadScene has populated Spawn_MsuOffsetLo/Hi/
; Spawn_Count for the stage currently being loaded, and after MSU-1 is
; generally up. Mirrors Bg_LoadSceneFp_Streaming's exact seek+sequential-
; read shape. A one-time blocking read outside the per-frame Msu1_LoadFrame
; path, same as that routine -- does NOT touch Msu1_StreamBusy's one-
; stream-per-frame budget. Re-runnable: always resets Spawn_Index to 0 and
; re-reads Spawn_Count-many records fresh, so a stage with fewer records
; than the previous one leaves no stale tail data live (SpawnTable_Wram
; entries at/past Spawn_Count are simply never indexed by Spawn_Play, which
; loops on Spawn_Count, not SPAWN_MAX_RECORDS).
Spawn_Init:
    php
    sei
    sep #$20
.a8
    lda #0
    sta.l Spawn_Index

    ; --- seek to this stage's spawn blob (Spawn_MsuOffsetLo/Hi, already
    ; populated by Bg_LoadScene) ---
    lda.l Spawn_MsuOffsetLo
    sta $2000
    lda.l Spawn_MsuOffsetLo+1
    sta $2001
    lda.l Spawn_MsuOffsetHi
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Spawn_Init__seek_busy:
    lda $2000
    bmi Spawn_Init__seek_busy

    ; --- Spawn_Count == 0 -> this stage packs no spawn table at all; leave
    ; the queue permanently exhausted (Spawn_Index == Spawn_Count == 0) so
    ; Spawn_Play no-ops forever and the win condition's "queue exhausted"
    ; check reads true immediately. Also zero Spawn_LastTriggerX so the
    ; win-condition camera hold (Stage_Load) doesn't hold on a stale value
    ; from the previous stage. ---
    lda.l Spawn_Count
    bne Spawn_Init__have_records
    rep #$31
.a16
.i16
    lda #0
    sta.l Spawn_LastTriggerX
    plp
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Spawn_Init__have_records:

    ; --- zero-extend Spawn_Count (a .db) into a 16-bit scratch before the
    ; *7 shift-sub below -- a 16-bit `lda.l Spawn_Count` here would read
    ; Spawn_Count's own byte plus whatever follows it in WRAM (Spawn_CountX7
    ; itself), not a zero-extended value. Same pattern Spawn_Play__active
    ; already uses for Spawn_Index. ---
    sep #$20
.a8
    lda.l Spawn_Count
    sta.l Spawn_ScratchIdx
    lda #0
    sta.l Spawn_ScratchIdx+1

    rep #$31
.a16
.i16
    lda.l Spawn_ScratchIdx
    asl a
    asl a
    asl a                       ; count*8
    sec
    sbc.l Spawn_ScratchIdx      ; count*8 - count = count*7
    sta.l Spawn_CountX7

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
    ; CPX has no long-addressing form (CLAUDE.md) -- Spawn_CountX7 is a
    ; runtime WRAM value now, not a compile-time immediate, so this can't
    ; be `cpx #N` anymore. Copy X to A (which DOES have a long CMP form)
    ; instead of comparing X directly.
    txa
    cmp.l Spawn_CountX7
    bcc Spawn_Init__read

    ; --- cache the last record's trigger_x (Spawn_CountX7 - 7 is its base
    ; offset; records are packed in ascending trigger order, see header) ---
    lda.l Spawn_CountX7
    sec
    sbc #7
    tax
    lda.l SpawnTable_Wram,x
    sta.l Spawn_LastTriggerX

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
    cmp.l Spawn_Count
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
    tax                         ; X = this record's base offset, 0..(SPAWN_MAX_RECORDS-1)*7

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
