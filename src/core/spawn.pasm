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
; Deliberate scope cut, not an oversight: every record spawns using
; whichever roster character is already wired to the slot it lands in --
; the source level's specific character identity (Shermie, Yashiro, ...) is
; not modeled. Position/timing fidelity is the goal; character identity is
; explicitly not.
;
; **`wait`/`group`/`boss`, 2026-08-22** (follow-up to "level content"
; generalization -- see build_spawn_table.py's own header for the real
; data behind this: BOR's own two shipped stages use `wait`/`group` for
; real, but neither uses `boss`; TMNT, not yet converted/buildable, has 6
; real `boss` spawns and no `group` usage). Real semantics, read directly
; from Plombo/beatsofrage's BOR.C (`update_scroller()`, ~line 4749-4786),
; not assumed:
;
;   - `wait`/`group`/`spawn` are ONE single ordered queue -- exactly this
;     file's existing Spawn_Index design, just with two more record kinds
;     walking the same index.
;   - `group min max` sets GLOBAL mutable pool-size state (Spawn_GroupMin/
;     Max below), default 100/100 (effectively unlimited), reset every
;     stage load. It gates ALL further queue advancement, not just
;     spawns: once `count_ents(TYPE_ENEMY) >= Spawn_GroupMin`, NOTHING
;     in the queue is even looked at (not spawns, not the next wait/group
;     marker) until enough enemies die to drop back under it. This is what
;     makes `group 1-2`/`group 3-3` read as real wave gates.
;   - "enemy count" excludes props, matching BOR.C's own `TYPE_ENEMY`
;     filter -- free here via `EntityN_InputDriven != CHAR_INPUT_DRIVEN_
;     PROP`, no new state needed to track it.
;   - `wait` blocks camera scroll entirely until ZERO enemies (not props)
;     remain alive, then releases. Implemented by reusing the existing G4
;     win-condition hold-clamp on Screen_MaxX (core/game_state.pasm's
;     Stage_ApplyWinClamp) as the single owner of that clamp, rather than
;     adding a second independent scroll-block path -- see Spawn_Play's
;     own wait-handling block below for why.
;   - `boss` is real DATA plumbing only in this slice (record_kind==4,
;     EntityN_IsBoss below) -- no distinct HUD or win-condition behavior
;     reads it yet, since no buildable pak here exercises it end-to-end
;     (see this file's own SPAWN_KIND_BOSS comment and build_spawn_
;     table.py's header for the full caveat).
;
; One record is still processed per Spawn_Play call (per frame), matching
; this file's existing one-record-per-frame grain, rather than BOR.C's own
; same-frame multi-dequeue while-loop -- the smallest change that preserves
; this architecture and stays easy to verify; invisible at 60fps.
;
; **CORRECTION, plan_game.md G8 (2026-08-21)**: this header used to also
; claim non-enemy spawns (BOR's `1up` pickup, `trash` breakable prop) were
; "not modeled" / silently ignored -- that was false, see
; build_spawn_table.py's own "Entity kind" section for the real story (they
; were spawning as ordinary full-HP AI enemies in the shipped ROM). Entity
; *kind* IS now modeled, via the record's `entity_kind` byte (below) and
; `Spawn_Play`'s per-slot `CHAR_INPUT_DRIVEN`/HP write -- see
; `CHAR_INPUT_DRIVEN_PROP` in main.pasm for the runtime behavior (props
; never seek/attack, but get the same soft-kill/hide-at-HP==0 treatment an
; AI enemy does).
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

SPAWN_MAX_RECORDS = 48       ; largest packed stage today is stage 1A's 41
                              ; (33 spawn + 6 wait + 2 group, grown from 33
                              ; spawn-only records by the wait/group/boss
                              ; slice); see this file's header for why this
                              ; isn't tied to any one stage's real count

; --- WRAM layout: $7E5500 + SPAWN_MAX_RECORDS*8 bytes (384 for 48 records,
; grown from 40 by the wait/group/boss slice), first free region after
; Anim_*/CharSelect_*'s $7E53B0-$7E53C9 block (verified collision-free by
; grep -- see main.pasm's own $7E53B6 note for the same verification
; convention). SpawnTable_Wram now ends at $7E568F; Spawn_ScratchKind/
; Spawn_ScratchHp live past that at $7E5690/$7E5691, and the wait/group/
; boss slice's own new cells (Spawn_GroupMin/Max/Waiting/PreClearHoldX,
; Entity1/2/3_IsBoss) immediately after at $7E5692-$7E5699 (grep-verified
; clear of any other module's WRAM through $7E56FF). ---
Spawn_Index         = $7E5500   ; .db -- next pending record index, 0..Spawn_Count
Spawn_Count         = $7E5501   ; .db -- this stage's own record count, read
                                 ; from its bg record by Bg_LoadScene (was a
                                 ; compile-time SPAWN_COUNT constant)
Spawn_CountX8       = $7E5502   ; .dw -- Spawn_Count*8 cached at Init time
                                 ; (was *7 before the health-override slice
                                 ; grew the record to 8 bytes), so Spawn_Play
                                 ; doesn't re-multiply every call
Spawn_MsuOffsetLo   = $7E5504   ; .dw -- this stage's spawn blob's 24-bit MSU
Spawn_MsuOffsetHi   = $7E5506   ; .db    file offset (was SPAWN_MSU_OFFSET),
                                 ; set by Bg_LoadScene before Spawn_Init runs
Spawn_ScratchIdx    = $7E5507   ; .dw -- zero-extended copy of Spawn_Index for the *8 multiply
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
SpawnTable_Wram     = $7E550F   ; SPAWN_MAX_RECORDS*8 bytes, record layout
                                 ; below. Grew from 40*8 to 48*8 records
                                 ; (wait/group/boss slice) -- now ends at
                                 ; $7E550F+$180 = $7E568F, so the scratch/
                                 ; state cells below moved past that (they
                                 ; used to sit at $7E5660, which the smaller
                                 ; table's slack made safe but the grown
                                 ; table does not).
Spawn_ScratchKind   = $7E5690   ; .db -- captured record_kind (record+6, see
                                 ; layout below), plan_game.md G8, relocated
                                 ; by the wait/group/boss slice (was $7E5660
                                 ; -- now inside SpawnTable_Wram's grown
                                 ; range; $7E5690 is safely past it,
                                 ; grep-confirmed no other module claims
                                 ; $7E5650-$7E56FF).
Spawn_ScratchHp     = $7E5691   ; .db -- captured spawn_hp (record+7, see
                                 ; layout below), health-override slice.
Spawn_GroupMin      = $7E5692   ; .db -- BOR.C's global `groupmin`, default
                                 ; 100 (effectively unlimited). Gates ALL
                                 ; queue advancement (spawn/wait/group
                                 ; alike) -- see this file's own header.
Spawn_GroupMax      = $7E5693   ; .db -- BOR.C's global `groupmax`, default 100.
Spawn_Waiting       = $7E5694   ; .db -- BOR.C's `level_waiting`: nonzero
                                 ; while a `wait` record has armed and at
                                 ; least one enemy (not prop) is still alive.
Spawn_PreClearHoldX = $7E5695   ; .dw -- what to restore Screen_MaxX to when
                                 ; a wait releases and the stage isn't
                                 ; cleared yet -- the same value core/
                                 ; game_state.pasm's Stage_ApplyWinClamp
                                 ; already computes (min(Stage_TrueMaxX,
                                 ; Spawn_LastTriggerX)), cached here so
                                 ; Spawn_Play doesn't need to re-derive it.
Entity1_IsBoss      = $7E5697   ; .db -- plan_game.md wait/group/boss slice:
Entity2_IsBoss      = $7E5698   ; .db    sticky per-slot boss flag, set/
Entity3_IsBoss      = $7E5699   ; .db    cleared whenever Spawn_Play (re)uses
                                 ; that slot. Standalone WRAM cells, NOT a
                                 ; CharacterEntity struct field -- see
                                 ; phase_g7_invuln_frames_second_slice
                                 ; project memory: growing CHAR_ZP_LEN broke
                                 ; spawn-slot assignment even with
                                 ; audit_all.py green. Nothing reads these
                                 ; yet (no boss HUD/win-condition logic
                                 ; exists) -- real, sourced, verified data
                                 ; plumbing ahead of a consumer, same pattern
                                 ; moveset_pipeline_generalization's non-role
                                 ; animation ordinals used.
Spawn_ScratchEnemyCount = $7E569A ; .db -- running EnemyCount total (0-3),
                                 ; used by both the wait-release check and
                                 ; the group gate below (kept as a WRAM
                                 ; scratch, not a register, so A stays free
                                 ; for the per-slot Hp/InputDriven checks).
Spawn_ScratchMap    = $7E569B   ; .db -- plan_game.md 8a row 3: decoded
                                 ; map index (0-3), see SPAWN_MAP_SHIFT above.
MapApply_Index          = $7E569C  ; .db -- Anim_ApplyMapPalette's own param
MapApply_PaletteBaseLo  = $7E569D  ; .dw    block, filled by each slot's
MapApply_PaletteBaseHi  = $7E569F  ; .db    spawn dispatch below before the
MapApply_MapBaseLo      = $7E56A0  ; .dw    jsl call.
MapApply_MapBaseHi      = $7E56A2  ; .db
MapApply_PaletteSlot    = $7E56A3  ; .db

; Record layout (8 bytes, LE), matches build_spawn_table.py exactly. Size is
; UNCHANGED by the wait/group/boss slice -- record_kind became a 5-way
; discriminator instead of the record growing, specifically to avoid
; touching the four hand-synced *8/record-size sites this file's header
; already calls out (Spawn_CountX8, SPAWN_MAX_RECORDS*8, the last-record
; seek, Spawn_Play's own shift):
;   +0-1  trigger_x   (u16) -- SNES world-px camera position that arms this
;                              record. Meaningful for every record kind.
;   +2-3  spawn_x     (u16) -- SNES world-px initial position, kind==enemy/
;                              prop/boss only. kind==SPAWN_KIND_GROUP
;                              repurposes these two bytes as group_min (+2)
;                              / group_max (+3), single bytes each (real
;                              values are always <=100). 0 for kind==wait.
;   +4    spawn_y     (u8)  -- 0 for wait/group records.
;   +5    facing_left (u8)  -- CHAR_FACING_LEFT convention (0=right,1=left).
;                              0 for wait/group records.
;   +6    record_kind (u8)  -- SPAWN_KIND_ENEMY (0), SPAWN_KIND_PROP (1),
;                              SPAWN_KIND_WAIT (2), SPAWN_KIND_GROUP (3), or
;                              SPAWN_KIND_BOSS (4) -- was `entity_kind`,
;                              0/1 only, before the wait/group/boss slice
;                              (plan_game.md G8: "reserved, always 0" before
;                              THAT phase -- see build_spawn_table.py's own
;                              "Entity kind" section for that history).
;   +7    spawn_hp    (u8)  -- health-override slice (follow-up to G8): the
;                              level's own `health` line, scaled to
;                              0..CHAR_HP_MAX. Read for enemy/boss slots
;                              only -- a prop's HP is always CHAR_HP_PER_HIT
;                              regardless of this byte, and it's 0/unused
;                              for wait/group records.

; plan_game.md G8: a prop/pickup slot gets CHAR_INPUT_DRIVEN_PROP (main.pasm)
; instead of CHAR_INPUT_DRIVEN_AI, and a fixed low HP (== CHAR_HP_PER_HIT, so
; one hit takes it from alive to exactly 0) instead of CHAR_HP_MAX. Both are
; compile-time constants, not record fields -- every prop today behaves
; identically (one-hit, generic-looking), so there's nothing per-record to
; carry yet.
SPAWN_KIND_ENEMY = 0
SPAWN_KIND_PROP  = 1
SPAWN_KIND_WAIT  = 2   ; wait/group/boss slice: scroll-block-until-clear marker
SPAWN_KIND_GROUP = 3   ; wait/group/boss slice: respawn-pool-size marker
SPAWN_KIND_BOSS  = 4   ; wait/group/boss slice: enemy + sets EntityN_IsBoss

; plan_game.md 8a row 3 (`map`): record_kind's spare high bits (values 0-4
; only need 3 bits) carry the spawn's remap-palette index (0-3), packed by
; build_spawn_table.py as `record_kind |= (map_value << 3)` -- avoids
; growing the fixed 8-byte record, same technique the wait/group/boss slice
; used for group_min/max.
SPAWN_KIND_MASK  = $07
SPAWN_MAP_SHIFT  = 3

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

    ; --- wait/group/boss slice: reset the global group pool state to
    ; BOR.C's own `unload_level()` defaults (groupmin=groupmax=100,
    ; level_waiting=0) every stage load -- a stage that narrowed the pool
    ; (e.g. `group 1-2`) must not leave that narrowing active for the NEXT
    ; stage's own queue. Boss flags reset defensively too, even though a
    ; stale flag on an HP==0 (unspawned) slot is never observed before the
    ; next real spawn corrects it. ---
    lda #100
    sta.l Spawn_GroupMin
    sta.l Spawn_GroupMax
    lda #0
    sta.l Spawn_Waiting
    sta.l Entity1_IsBoss
    sta.l Entity2_IsBoss
    sta.l Entity3_IsBoss

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
    rtl
Spawn_Init__have_records:

    ; --- zero-extend Spawn_Count (a .db) into a 16-bit scratch before the
    ; *8 shift below -- a 16-bit `lda.l Spawn_Count` here would read
    ; Spawn_Count's own byte plus whatever follows it in WRAM (Spawn_CountX8
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
    asl a                       ; count*8 (record size grew to 8 bytes,
                                 ; health-override slice -- was count*8-count
                                 ; when the record was 7 bytes)
    sta.l Spawn_CountX8

    ldx #0
Spawn_Init__read:
    sep #$20
.a8
    lda $2001
    sta.l SpawnTable_Wram,x
    rep #$31
.a16
.i16
    inx
    ; CPX has no long-addressing form (CLAUDE.md) -- Spawn_CountX8 is a
    ; runtime WRAM value now, not a compile-time immediate, so this can't
    ; be `cpx #N` anymore. Copy X to A (which DOES have a long CMP form)
    ; instead of comparing X directly.
    txa
    cmp.l Spawn_CountX8
    bcc Spawn_Init__read

    ; --- cache the last record's trigger_x (Spawn_CountX8 - 8 is its base
    ; offset; records are packed in ascending trigger order, see header) ---
    lda.l Spawn_CountX8
    sec
    sbc #8
    tax
    lda.l SpawnTable_Wram,x
    sta.l Spawn_LastTriggerX

    plp
    rtl

; Spawn_Play -- call once per scpu_main_loop iteration. Walks the single
; global queue: no-ops if the queue is exhausted, if the pending record's
; trigger hasn't been reached, or if no AI slot is currently free (CHAR_HP
; nonzero for all of Entity1/2/3) -- in every no-op case, Spawn_Index does
; NOT advance, so the same record is retried next frame.
;
; wait/group/boss slice: also handles the release side of a `wait` block
; (unconditionally, every call -- see below) and gates ALL queue
; advancement (spawns AND wait/group markers alike) behind Spawn_GroupMin/
; Max, matching BOR.C's real algorithm -- see this file's own header.
Spawn_Play:
    php
    sep #$20
.a8

    ; --- wait-release check: runs every call regardless of queue/group
    ; state, since a wait's release condition (enemy count, not props, hits
    ; zero) must be checked even while the group gate below would otherwise
    ; block further queue processing. Screen_MaxX is the SAME clamp cell
    ; core/game_state.pasm's Stage_ApplyWinClamp/win-check already own (see
    ; this file's header) -- this is the third and last writer, and only
    ; ever restores what Stage_ApplyWinClamp already computed, never a
    ; separately-derived value. ---
    lda.l Spawn_Waiting
    beq Spawn_Play__wait_check_done
    lda #0
    sta.l Spawn_ScratchEnemyCount
    lda.l Entity1_Hp
    beq Spawn_Play__wc_slot2
    lda.l Entity1_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Spawn_Play__wc_slot2
    lda.l Spawn_ScratchEnemyCount
    inc a
    sta.l Spawn_ScratchEnemyCount
Spawn_Play__wc_slot2:
    sep #$20
.a8
    lda.l Entity2_Hp
    beq Spawn_Play__wc_slot3
    lda.l Entity2_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Spawn_Play__wc_slot3
    lda.l Spawn_ScratchEnemyCount
    inc a
    sta.l Spawn_ScratchEnemyCount
Spawn_Play__wc_slot3:
    sep #$20
.a8
    lda.l Entity3_Hp
    beq Spawn_Play__wc_sum_done
    lda.l Entity3_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Spawn_Play__wc_sum_done
    lda.l Spawn_ScratchEnemyCount
    inc a
    sta.l Spawn_ScratchEnemyCount
Spawn_Play__wc_sum_done:
    sep #$20
.a8
    lda.l Spawn_ScratchEnemyCount
    bne Spawn_Play__wait_check_done   ; still >=1 real enemy alive -- stay blocked
    lda #0
    sta.l Spawn_Waiting
    lda.l Stage_Cleared
    bne Spawn_Play__wait_check_done   ; already cleared -- win-check owns Screen_MaxX now
    rep #$31
.a16
.i16
    lda.l Spawn_PreClearHoldX
    sta Screen_MaxX
    sep #$20
.a8
Spawn_Play__wait_check_done:

    lda.l Spawn_Index
    cmp.l Spawn_Count
    bcc Spawn_Play__have_queue
    plp
    rtl
Spawn_Play__have_queue:
    sep #$20
.a8

    ; --- group gate: matches BOR.C's outer `count_ents(TYPE_ENEMY) <
    ; groupmin` check exactly -- blocks ALL further queue advancement
    ; (spawns AND wait/group markers) until enough real enemies (not
    ; props) have died. Same EnemyCount computation as the wait-release
    ; check above, duplicated rather than factored into a shared
    ; subroutine (this file's own calling-convention note: Spawn_Play is
    ; entered via jsl/rtl from a different bank, and 65816_calling_
    ; convention_bugs project memory flags jsl/rtl-vs-jsr/rts mismatches
    ; as a real recurring bug class -- a few duplicated instructions is
    ; cheaper than risking that here). ---
    lda #0
    sta.l Spawn_ScratchEnemyCount
    lda.l Entity1_Hp
    beq Spawn_Play__gc_slot2
    lda.l Entity1_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Spawn_Play__gc_slot2
    lda.l Spawn_ScratchEnemyCount
    inc a
    sta.l Spawn_ScratchEnemyCount
Spawn_Play__gc_slot2:
    sep #$20
.a8
    lda.l Entity2_Hp
    beq Spawn_Play__gc_slot3
    lda.l Entity2_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Spawn_Play__gc_slot3
    lda.l Spawn_ScratchEnemyCount
    inc a
    sta.l Spawn_ScratchEnemyCount
Spawn_Play__gc_slot3:
    sep #$20
.a8
    lda.l Entity3_Hp
    beq Spawn_Play__gc_sum_done
    lda.l Entity3_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Spawn_Play__gc_sum_done
    lda.l Spawn_ScratchEnemyCount
    inc a
    sta.l Spawn_ScratchEnemyCount
Spawn_Play__gc_sum_done:
    lda.l Spawn_ScratchEnemyCount
    cmp.l Spawn_GroupMin
    bcc Spawn_Play__group_ok        ; EnemyCount < GroupMin -- proceed
    plp
    rtl
Spawn_Play__group_ok:
    cmp.l Spawn_GroupMax
    bcc Spawn_Play__active          ; EnemyCount < GroupMax -- proceed
    plp
    rtl
Spawn_Play__active:
    sep #$20
.a8
    lda.l Spawn_Index
    sta.l Spawn_ScratchIdx      ; zero-extend Spawn_Index the same way Spawn_Init does
    lda #0
    sta.l Spawn_ScratchIdx+1

    rep #$31
.a16
.i16
    lda.l Spawn_ScratchIdx
    asl a
    asl a
    asl a                       ; index*8 (record size grew to 8 bytes,
                                 ; health-override slice -- was index*8-index
                                 ; when the record was 7 bytes)
    tax                         ; X = this record's base offset, 0..(SPAWN_MAX_RECORDS-1)*8

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
    inx                         ; X -> record+6 (entity_kind, plan_game.md G8)
    lda.l SpawnTable_Wram,x
    ; plan_game.md 8a row 3 (`map`): the same byte's high bits carry the
    ; map index -- decode it before masking Spawn_ScratchKind down to just
    ; the low 3 (real kind) bits.
    pha
    lsr a
    lsr a
    lsr a
    sta.l Spawn_ScratchMap
    pla
    and #SPAWN_KIND_MASK
    sta.l Spawn_ScratchKind
    inx                         ; X -> record+7 (spawn_hp, health-override slice)
    lda.l SpawnTable_Wram,x
    sta.l Spawn_ScratchHp

    ; --- wait/group/boss slice: wait/group markers dequeue unconditionally
    ; once triggered+group-gated (matching BOR.C -- they don't wait on a
    ; free AI slot, unlike an actual spawn), so dispatch them BEFORE
    ; find_slot below. ---
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_WAIT
    beq Spawn_Play__do_wait
    cmp #SPAWN_KIND_GROUP
    beq Spawn_Play__do_group
    jmp Spawn_Play__find_slot

Spawn_Play__do_wait:
    sep #$20
.a8
    lda #1
    sta.l Spawn_Waiting
    rep #$31
.a16
.i16
    lda Screen_PosX
    sta Screen_MaxX
    sep #$20
.a8
    jmp Spawn_Play__advance

Spawn_Play__do_group:
    ; Spawn_ScratchX's low byte is group_min (record+2), high byte is
    ; group_max (record+3) -- see this file's own record-layout comment.
    lda.l Spawn_ScratchX
    sta.l Spawn_GroupMin
    lda.l Spawn_ScratchX+1
    sta.l Spawn_GroupMax
    jmp Spawn_Play__advance

Spawn_Play__find_slot:
    sep #$20
.a8
    lda.l Entity1_Hp
    bne Spawn_Play__find_slot_check2
    jmp Spawn_Play__slot1
Spawn_Play__find_slot_check2:
    lda.l Entity2_Hp
    bne Spawn_Play__find_slot_check3
    jmp Spawn_Play__slot2
Spawn_Play__find_slot_check3:
    ; plan_game.md G8 grew slot1/slot2's own bodies (kind-conditional
    ; CHAR_INPUT_DRIVEN/HP) past this chain's original beq range -- jmp has
    ; no such limit, same fix as game_state.pasm's own G5 dispatch chain.
    lda.l Entity3_Hp
    bne Spawn_Play__find_slot_none
    jmp Spawn_Play__slot3
Spawn_Play__find_slot_none:
    plp
    rtl                         ; no free slot -- record stays pending
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
    ; plan_game.md G7 knockdown slice: reset this slot's fall/knockdown
    ; state BEFORE the enemy-vs-prop branch below -- a reused slot's
    ; previous occupant may have died parked in the fall machine's terminal
    ; state (CHAR_SELECTED==3, hidden); see Spawn_ResetKnockdownFall's own
    ; header for the full reasoning.
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN
    jsl Spawn_ResetKnockdownFall
    sep #$20
.a8
    ; plan_game.md G8: CHAR_INPUT_DRIVEN and starting HP both now depend on
    ; the record's own record_kind -- a slot that alternates between an
    ; enemy record and a prop record across two different waves must be
    ; re-set correctly every time, not left at whatever the boot default
    ; (CHAR_INPUT_DRIVEN_AI) or a PREVIOUS record here left it. wait/group/
    ; boss slice: also resets/sets Entity1_IsBoss every time, so a slot
    ; that alternates between a boss record and a plain enemy/prop record
    ; doesn't inherit a stale flag from its previous occupant.
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_PROP
    bne Spawn_Play__slot1_not_prop
    lda #CHAR_INPUT_DRIVEN_PROP
    sta.l Entity1_InputDriven
    lda #CHAR_HP_PER_HIT
    sta.l Entity1_Hp
    lda #0
    sta.l Entity1_IsBoss
    jmp Spawn_Play__advance
Spawn_Play__slot1_not_prop:
    sep #$20
.a8
    lda #CHAR_INPUT_DRIVEN_AI
    sta.l Entity1_InputDriven
    lda.l Spawn_ScratchHp       ; health-override slice -- was `lda #CHAR_HP_MAX`
    sta.l Entity1_Hp
    ; plan_game.md 8a row 3 (`map`): apply this spawn's remap palette (0 =
    ; the character's own base palette) -- fill Anim_ApplyMapPalette's param
    ; block from this slot's own struct fields (set once at character load,
    ; see main.pasm's Anim_LoadCharacter) and call it now, every spawn, so a
    ; reused slot's previous palette never lingers.
    lda.l Spawn_ScratchMap
    sta.l MapApply_Index
    rep #$31
.a16
.i16
    lda.l Entity1_PaletteBaseLo
    sta.l MapApply_PaletteBaseLo
    lda.l Entity1_MapBaseLo
    sta.l MapApply_MapBaseLo
    sep #$20
.a8
    lda.l Entity1_PaletteBaseHi
    sta.l MapApply_PaletteBaseHi
    lda.l Entity1_MapBaseHi
    sta.l MapApply_MapBaseHi
    lda.l Entity1_PaletteSlot
    sta.l MapApply_PaletteSlot
    jsl Anim_ApplyMapPalette
    sep #$20
.a8
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_BOSS
    bne Spawn_Play__slot1_not_boss
    lda #1
    sta.l Entity1_IsBoss
    jmp Spawn_Play__advance
Spawn_Play__slot1_not_boss:
    sep #$20
.a8
    lda #0
    sta.l Entity1_IsBoss
    jmp Spawn_Play__advance
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
    ; plan_game.md G7 knockdown slice: see slot1's own comment.
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN*2
    jsl Spawn_ResetKnockdownFall
    sep #$20
.a8
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_PROP
    bne Spawn_Play__slot2_not_prop
    lda #CHAR_INPUT_DRIVEN_PROP
    sta.l Entity2_InputDriven
    lda #CHAR_HP_PER_HIT
    sta.l Entity2_Hp
    lda #0
    sta.l Entity2_IsBoss
    jmp Spawn_Play__advance
Spawn_Play__slot2_not_prop:
    sep #$20
.a8
    lda #CHAR_INPUT_DRIVEN_AI
    sta.l Entity2_InputDriven
    lda.l Spawn_ScratchHp       ; health-override slice -- was `lda #CHAR_HP_MAX`
    sta.l Entity2_Hp
    ; plan_game.md 8a row 3 (`map`): see slot1's own comment.
    lda.l Spawn_ScratchMap
    sta.l MapApply_Index
    rep #$31
.a16
.i16
    lda.l Entity2_PaletteBaseLo
    sta.l MapApply_PaletteBaseLo
    lda.l Entity2_MapBaseLo
    sta.l MapApply_MapBaseLo
    sep #$20
.a8
    lda.l Entity2_PaletteBaseHi
    sta.l MapApply_PaletteBaseHi
    lda.l Entity2_MapBaseHi
    sta.l MapApply_MapBaseHi
    lda.l Entity2_PaletteSlot
    sta.l MapApply_PaletteSlot
    jsl Anim_ApplyMapPalette
    sep #$20
.a8
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_BOSS
    bne Spawn_Play__slot2_not_boss
    lda #1
    sta.l Entity2_IsBoss
    jmp Spawn_Play__advance
Spawn_Play__slot2_not_boss:
    sep #$20
.a8
    lda #0
    sta.l Entity2_IsBoss
    jmp Spawn_Play__advance
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
    ; plan_game.md G7 knockdown slice: see slot1's own comment.
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN*3
    jsl Spawn_ResetKnockdownFall
    sep #$20
.a8
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_PROP
    bne Spawn_Play__slot3_not_prop
    lda #CHAR_INPUT_DRIVEN_PROP
    sta.l Entity3_InputDriven
    lda #CHAR_HP_PER_HIT
    sta.l Entity3_Hp
    lda #0
    sta.l Entity3_IsBoss
    jmp Spawn_Play__advance
Spawn_Play__slot3_not_prop:
    sep #$20
.a8
    lda #CHAR_INPUT_DRIVEN_AI
    sta.l Entity3_InputDriven
    lda.l Spawn_ScratchHp       ; health-override slice -- was `lda #CHAR_HP_MAX`
    sta.l Entity3_Hp
    ; plan_game.md 8a row 3 (`map`): see slot1's own comment.
    lda.l Spawn_ScratchMap
    sta.l MapApply_Index
    rep #$31
.a16
.i16
    lda.l Entity3_PaletteBaseLo
    sta.l MapApply_PaletteBaseLo
    lda.l Entity3_MapBaseLo
    sta.l MapApply_MapBaseLo
    sep #$20
.a8
    lda.l Entity3_PaletteBaseHi
    sta.l MapApply_PaletteBaseHi
    lda.l Entity3_MapBaseHi
    sta.l MapApply_MapBaseHi
    lda.l Entity3_PaletteSlot
    sta.l MapApply_PaletteSlot
    jsl Anim_ApplyMapPalette
    sep #$20
.a8
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_BOSS
    bne Spawn_Play__slot3_not_boss
    lda #1
    sta.l Entity3_IsBoss
    jmp Spawn_Play__advance
Spawn_Play__slot3_not_boss:
    sep #$20
.a8
    lda #0
    sta.l Entity3_IsBoss

Spawn_Play__advance:
    sep #$20
.a8
    lda.l Spawn_Index
    inc a
    sta.l Spawn_Index
    plp
    rtl
Spawn_Play__not_yet:
    plp
    rtl
