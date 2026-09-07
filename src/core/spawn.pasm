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
; Deliberate scope cut, ORIGINALLY: every record spawned using whichever
; roster character was already wired to the slot it landed in -- the source
; level's specific character identity was not modeled, position/timing
; fidelity was the goal, character identity was not.
;
; **Real spawn-driven roster reassignment, real user instruction, same
; day as the TMNT campaign**: that cut is now closed for records the build
; pipeline can actually identify against the shipped roster --
; `SPAWN_KIND_BOSS_IDENTIFIED` (below) carries a real roster index in the
; record's own spare bits, and `Spawn_Play` re-runs `Anim_LoadCharacter`
; (see `Spawn_DoRosterReassign` at the bottom of this file) so that slot
; actually streams and renders as ITS OWN real converted character, not a
; reskin. Still cut, and still deliberate: a spawn whose character was
; never added to the roster (most ordinary enemies -- the roster format
; caps at 8 total slots, `pack_msu_roster.py`) still falls back to the
; original behavior (`SPAWN_KIND_BOSS`, no identity, or plain
; `SPAWN_KIND_ENEMY`/`SPAWN_KIND_PROP`) -- there was never a way to give
; every possible spawned name its own roster slot without a fundamentally
; different (unbounded) roster design, which stays out of scope.
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
; SpawnTable_Wram is sized for SPAWN_MAX_RECORDS, not any one stage's own
; count -- see this file's header for why this isn't tied to any one
; stage's real count.
;
; Uses global (not @-local) labels throughout, same convention as every
; other core/*.pasm file (see core/random.pasm's header for why).
; ============================================================================

SPAWN_MAX_RECORDS = 90       ; roster-growth slice, REAL BUG found and fixed
                              ; while regenerating every stage's spawn table
                              ; for the RECORD_SIZE 8->9 change below: this
                              ; was still 48 ("largest packed stage today is
                              ; stage 1A's 41"), a stale claim left over from
                              ; before the TMNT campaign slice shipped --
                              ; stage7streets2 alone real-packs 86 records
                              ; (63/67/46 for sewer0/streets/sewer, also all
                              ; >48). Spawn_Init's boot-time read loop walks
                              ; Spawn_Count (the stage's OWN real count, read
                              ; from its bg record, not clamped to
                              ; SPAWN_MAX_RECORDS), so every one of those 4
                              ; stages was silently overrunning
                              ; SpawnTable_Wram's WRAM allocation by hundreds
                              ; of bytes into whatever followed it -- real,
                              ; live corruption, not a hypothetical. 90 covers
                              ; the real max (86) with small headroom -- if a
                              ; future stage exceeds it, re-measure and bump
                              ; again rather than trusting a round number.

; --- WRAM layout: $7E5500 + SPAWN_MAX_RECORDS*9 bytes (810 for 90 records --
; roster-growth slice grew RECORD_SIZE 8->9 AND SPAWN_MAX_RECORDS 48->90,
; see that constant's own comment for why both), first free region after
; Anim_*/CharSelect_*'s $7E53B0-$7E53C9 block (verified collision-free by
; grep -- see main.pasm's own $7E53B6 note for the same verification
; convention). SpawnTable_Wram now ends at $7E5892 (was $7E5838 before the
; claude_close_g7_g8_before_g10.md Part 2/3 RECORD_SIZE 9->10 growth, $7E568F
; slice); every scratch/state cell below moved to $7E5893+ to stay clear of
; the grown table -- same relocation this file has done twice before as the
; table grew (they used to sit at $7E5660, then $7E5690). Freshly grep-
; verified clear of any other module's WRAM through at least $7E58AA (the
; new highest cell, Spawn_ScratchRosterIdx, is $7E58A7) -- this is NEW
; territory past the old $7E56FF-verified range, not a reuse of the old
; "already checked" claim. ---
Spawn_Index         = $7E5500   ; .db -- next pending record index, 0..Spawn_Count
Spawn_Count         = $7E5501   ; .db -- this stage's own record count, read
                                 ; from its bg record by Bg_LoadScene (was a
                                 ; compile-time SPAWN_COUNT constant)
Spawn_CountX8       = $7E5502   ; .dw -- Spawn_Count*9 cached at Init time
                                 ; (name kept from when the record was 8
                                 ; bytes -- see build_rom.py-style precedent
                                 ; of not renaming a stable symbol for a
                                 ; math-only change; was *7 before the
                                 ; health-override slice, *8 before the
                                 ; roster-growth slice), so Spawn_Play
                                 ; doesn't re-multiply every call
Spawn_MsuOffsetLo   = $7E5504   ; .dw -- this stage's spawn blob's 24-bit MSU
Spawn_MsuOffsetHi   = $7E5506   ; .db    file offset (was SPAWN_MSU_OFFSET),
                                 ; set by Bg_LoadScene before Spawn_Init runs
Spawn_ScratchIdx    = $7E5507   ; .dw -- zero-extended copy of Spawn_Index for the *9 multiply
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
SpawnTable_Wram     = $7E550F   ; SPAWN_MAX_RECORDS*10 = 900 bytes, record
                                 ; layout below. Grew from 48*8=384 to
                                 ; 90*9=810 (roster-growth slice: +1 byte/
                                 ; record for a dedicated roster_idx field,
                                 ; AND SPAWN_MAX_RECORDS 48->90 to fix the
                                 ; real overrun bug that constant's own
                                 ; comment documents), then 90*9=810 ->
                                 ; 90*10=900 (claude_close_g7_g8_before_g10.md
                                 ; Part 2/3: split the old conflated +8
                                 ; roster_idx byte into separate object/item
                                 ; identity bytes) -- now ends at
                                 ; $7E550F+$384 = $7E5893, so the scratch/
                                 ; state cells below all moved well past
                                 ; their previous ($7E5690-$7E56A4, then
                                 ; $7E56C0-$7E56D4, then $7E5839-$7E5850)
                                 ; addresses.
Spawn_ScratchKind   = $7E5893   ; .db -- captured record_kind (record+6, see
                                 ; layout below), plan_game.md G8, relocated
                                 ; twice before (wait/group/boss slice, then
                                 ; the RECORD_SIZE 8->9 roster-growth change)
                                 ; and again here by the SPAWN_MAX_RECORDS
                                 ; 48->90 fix (grep-confirmed no other module
                                 ; claims through at least $7E58AA).
Spawn_ScratchHp     = $7E5894   ; .db -- captured spawn_hp (record+7, see
                                 ; layout below), health-override slice.
Spawn_GroupMin      = $7E5895   ; .db -- BOR.C's global `groupmin`, default
                                 ; 100 (effectively unlimited). Gates ALL
                                 ; queue advancement (spawn/wait/group
                                 ; alike) -- see this file's own header.
Spawn_GroupMax      = $7E5896   ; .db -- BOR.C's global `groupmax`, default 100.
Spawn_Waiting       = $7E5897   ; .db -- BOR.C's `level_waiting`: nonzero
                                 ; while a `wait` record has armed and at
                                 ; least one enemy (not prop) is still alive.
Spawn_PreClearHoldX = $7E5898   ; .dw -- what to restore Screen_MaxX to when
                                 ; a wait releases and the stage isn't
                                 ; cleared yet -- the same value core/
                                 ; game_state.pasm's Stage_ApplyWinClamp
                                 ; already computes (min(Stage_TrueMaxX,
                                 ; Spawn_LastTriggerX)), cached here so
                                 ; Spawn_Play doesn't need to re-derive it.
Entity1_IsBoss      = $7E589A   ; .db -- plan_game.md wait/group/boss slice:
Entity2_IsBoss      = $7E589B   ; .db    sticky per-slot boss flag, set/
Entity3_IsBoss      = $7E589C   ; .db    cleared whenever Spawn_Play (re)uses
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
Spawn_ScratchEnemyCount = $7E589D ; .db -- running EnemyCount total (0-3),
                                 ; used by both the wait-release check and
                                 ; the group gate below (kept as a WRAM
                                 ; scratch, not a register, so A stays free
                                 ; for the per-slot Hp/InputDriven checks).
Spawn_ScratchMap    = $7E589E   ; .db -- plan_game.md 8a row 3: decoded
                                 ; map index (0-3), see SPAWN_MAP_SHIFT above.
MapApply_Index          = $7E589F  ; .db -- Anim_ApplyMapPalette's own param
MapApply_PaletteBaseLo  = $7E58A0  ; .dw    block, filled by each slot's
MapApply_PaletteBaseHi  = $7E58A2  ; .db    spawn dispatch below before the
MapApply_MapBaseLo      = $7E58A3  ; .dw    jsl call.
MapApply_MapBaseHi      = $7E58A5  ; .db
MapApply_PaletteSlot    = $7E58A6  ; .db
Spawn_ScratchRosterIdx  = $7E58A7  ; .db -- roster-reassignment slice:
                                   ; captured record's dedicated +8
                                   ; roster_idx byte (see layout below), real
                                   ; when Spawn_ScratchKind==SPAWN_KIND_
                                   ; BOSS_IDENTIFIED, OR (real prop/pickup
                                   ; sprite art follow-up) when Spawn_
                                   ; ScratchKind==SPAWN_KIND_PROP and this
                                   ; item's own converted sprite has a real
                                   ; roster slot -- 0 ("no reassign") for
                                   ; every prop without one yet. Grep-
                                   ; confirmed clear of any other module's
                                   ; WRAM through at least $7E58AA.
Spawn_ScratchPickupType = $7E58A8 ; .db -- G8 item/pickup slice: decoded
                                   ; record_kind bits 5-7 (SPAWN_PICKUP_
                                   ; SHIFT/MASK below), real only when
                                   ; Spawn_ScratchKind==SPAWN_KIND_PROP.
                                   ; Written to the landing slot's own
                                   ; CHAR_PICKUP_TYPE (main.pasm) by slot1/
                                   ; slot2/slot3 below, same pattern as
                                   ; Spawn_ScratchMap/MapApply_*.
Spawn_ScratchPrevWasProp = $7E58A9 ; .db -- slot-reuse art-leak fix
                                   ; (finish_g8_with_runtime_asset_swapping.md):
                                   ; captured at the very top of each slotN
                                   ; body, BEFORE that slot's own CHAR_
                                   ; INPUT_DRIVEN is overwritten -- 1 if the
                                   ; entity THIS RECORD IS ABOUT TO OVERWRITE
                                   ; was a CHAR_INPUT_DRIVEN_PROP (a real
                                   ; prop's art -- 1-frame idle/walk/attack,
                                   ; its own tiny palette -- resident in this
                                   ; slot's struct fields/CGRAM), 0 otherwise.
                                   ; An ordinary (non-identified) enemy record
                                   ; landing in such a slot does NOT normally
                                   ; call Anim_LoadCharacter at all (ordinary
                                   ; enemies intentionally render as a reskin
                                   ; of whatever's already resident -- see
                                   ; build_rom.py's ROSTER_PREFIXES comment),
                                   ; so without this flag a real bug ships: an
                                   ; "enemy" silently keeps a broken 1-frame
                                   ; prop moveset and CGRAM colors. Consumed
                                   ; by each slotN_not_boss branch below to
                                   ; force one real Spawn_DoRosterReassign
                                   ; back to that slot's own natural boot
                                   ; default character (CharacterEntity_Init's
                                   ; role1/2/3 roster index: JHUN=1/JOE=2/
                                   ; YASHIRO=3) before ordinary AI dispatch
                                   ; runs, restoring a real playable moveset
                                   ; instead of leaving prop art in place.
Spawn_SavedCharSelectIndex = $7E58AA ; .db -- real bug found+fixed
                                   ; (finish_g8_with_runtime_asset_swapping.md):
                                   ; Spawn_DoRosterReassign writes its target
                                   ; roster index into the SAME shared
                                   ; CharSelect_Index cell Anim_LoadCharacter
                                   ; always reads its "which slot to load"
                                   ; parameter from -- the only mechanism it
                                   ; has. That cell doubles as the PLAYER's
                                   ; own persistent char-select/Select-button
                                   ; reselect state (main.pasm), so ANY spawn-
                                   ; driven reassignment (boss OR the new
                                   ; slot-restore path above) used to leave
                                   ; it clobbered at whatever roster index it
                                   ; last loaded -- invisible until this
                                   ; slice made it reachable from a stage's
                                   ; own BOOT-time spawn queue (stage 1B's
                                   ; own real Money record, trigger_x=8, now
                                   ; carries a real roster_idx now that MONEY
                                   ; is a real roster member), corrupting the
                                   ; player's own char-select state before
                                   ; the player ever touches Select. Spawn_
                                   ; DoRosterReassign now saves/restores
                                   ; CharSelect_Index around its own write,
                                   ; so no spawn-driven reassignment can ever
                                   ; observably disturb it again.

; claude_close_g7_g8_before_g10.md Part 2: a breakable object's contained
; item's roster index (this record's own +8 item_roster_idx byte, see the
; record layout below), captured here by Spawn_Play at spawn time and held
; per-slot until the object's HP reaches 0 -- the break->reveal transition
; (main.pasm's Character_HitApply__ApplyPickup dispatch) reads it to know
; which real roster slot to reassign the AI slot to. Standalone cells, NOT a
; new CharacterEntity struct field -- growing CHAR_ZP_LEN is real-bug-
; verified dangerous (game_state.pasm's own EntityN_InvulnFrames precedent,
; same reasoning). Grep-confirmed free at $7E58AB+ (right after Spawn_
; SavedCharSelectIndex above, the previous highest cell in this file).
Spawn_SavedCharSelectLoaded = $7E58BA ; .db -- preserved player load gate
Spawn_SavedCharSelectCount  = $7E58BB ; .db -- preserved player wrap bound
Spawn_RosterLoadResult      = $7E58BC ; .db -- target loader result
Entity1_ItemRosterIdx = $7E58AB  ; .db
Entity2_ItemRosterIdx = $7E58AC  ; .db
Entity3_ItemRosterIdx = $7E58AD  ; .db
Spawn_ScratchSlotOfs = $7E58AF   ; .dw -- selected actor byte offset
Spawn_ScratchItemRosterIdx = $7E58AE ; .db -- captured record+8 (item_roster_
                                   ; idx), this record's own decode scratch,
                                   ; parallel to Spawn_ScratchRosterIdx below
                                   ; (which now captures record+9,
                                   ; object_roster_idx, consumed AT SPAWN --
                                   ; this one is stashed into the target
                                   ; slot's own EntityN_ItemRosterIdx instead,
                                   ; for later, see slot1/2/3 bodies).

; Record layout (10 bytes, LE), matches build_spawn_table.py exactly. Size
; was UNCHANGED by the wait/group/boss slice -- record_kind became a 5-way
; discriminator instead of the record growing, specifically to avoid
; touching the hand-synced *9/record-size sites this file's header already
; calls out (Spawn_CountX8, SPAWN_MAX_RECORDS*9, the last-record seek,
; Spawn_Play's own shift). Roster-growth slice grew this from 8 to 9 bytes
; (a single +8 roster_idx). claude_close_g7_g8_before_g10.md Part 2/3 grew
; it again, 9 to 10 bytes: the old single +8 roster_idx conflated an
; obstacle's OWN identity with its CONTAINED item's identity (a real,
; currently-shipping bug -- see SpawnTable_Wram's own comment above), split
; into +8 item_roster_idx (consumed on break) and +9 object_roster_idx
; (consumed at spawn). All four hand-synced sites updated to the shift-and-
; add index*10 idiom:
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
;   +6    record_kind (u8)  -- low 3 bits: SPAWN_KIND_ENEMY (0),
;                              SPAWN_KIND_PROP (1), SPAWN_KIND_WAIT (2),
;                              SPAWN_KIND_GROUP (3), SPAWN_KIND_BOSS (4), or
;                              SPAWN_KIND_BOSS_IDENTIFIED (5) -- was
;                              `entity_kind`, 0/1 only, before the wait/
;                              group/boss slice (plan_game.md G8: "reserved,
;                              always 0" before THAT phase -- see
;                              build_spawn_table.py's own "Entity kind"
;                              section for that history). Bits 3-4: map
;                              index (0-3, SPAWN_MAP_SHIFT/SPAWN_MAP_MASK).
;                              Bits 5-7 no longer used (was a 3-bit roster
;                              index, 0-7 -- moved to its own +8 byte by the
;                              roster-growth slice once the roster cap grew
;                              past 8 and needed a 4th bit).
;   +7    spawn_hp    (u8)  -- health-override slice (follow-up to G8): the
;                              level's own `health` line, scaled to
;                              0..CHAR_HP_MAX. Read for enemy/boss slots
;                              only -- a prop's HP is always CHAR_HP_PER_HIT
;                              regardless of this byte, and it's 0/unused
;                              for wait/group records.
;   +8    item_roster_idx (u8) -- claude_close_g7_g8_before_g10.md Part 2/3:
;                              real only when record_kind==SPAWN_KIND_PROP
;                              AND this is an obstacle+item record (a
;                              breakable containing a real, roster-converted
;                              item) -- the CONTAINED item's roster slot,
;                              consumed by Spawn_Play only once the object's
;                              HP reaches 0 (break->reveal), never at spawn.
;                              0/unused for every other record kind.
;   +9    object_roster_idx (u8) -- roster-growth slice: real roster slot
;                              index (0-19), real when record_kind ==
;                              SPAWN_KIND_BOSS_IDENTIFIED (the identified
;                              boss's own slot, unchanged meaning from the
;                              old +8) OR record_kind==SPAWN_KIND_PROP (the
;                              SPAWNED character's own slot -- a standalone
;                              item's own sprite, or a breakable object's
;                              own sprite e.g. Chair/Table/Trash), else 0.
;                              Consumed AT SPAWN TIME, unlike +8 above.

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
SPAWN_KIND_BOSS_IDENTIFIED = 5   ; spawn-driven roster-reassignment slice:
                              ; same as SPAWN_KIND_BOSS (sets EntityN_IsBoss)
                              ; PLUS the record's dedicated +9
                              ; object_roster_idx byte carries a real roster
                              ; index for a
                              ; character build_spawn_table.py found in the
                              ; actual shipped roster -- this slot's
                              ; Anim_LoadCharacter gets re-run so the entity
                              ; actually renders as ITS OWN character instead
                              ; of whatever the slot already had loaded (the
                              ; previous, deliberate "identity not modeled"
                              ; shortcut this file's header used to document
                              ; -- see Spawn_DoRosterReassign below for the
                              ; real mechanism and its real per-frame
                              ; streaming-budget guard).

; plan_game.md 8a row 3 (`map`): record_kind's spare high bits carry the
; spawn's remap-palette index (0-3), packed by build_spawn_table.py as
; `record_kind |= (map_value << 3)` -- avoids growing the record further for
; this field, same technique the wait/group/boss slice used for
; group_min/max. Bits 5-7 are unused today (the roster-growth slice moved
; roster_idx to its own +8 byte once it needed a 4th bit, see that field's
; own comment above) -- SPAWN_MAP_MASK is still applied after the shift as
; defensive practice even though those bits are now provably always 0.
SPAWN_KIND_MASK   = $07
SPAWN_MAP_SHIFT   = 3
SPAWN_MAP_MASK    = $03   ; explicit mask AFTER the >>3 shift
SPAWN_PICKUP_SHIFT = 5    ; G8 item/pickup slice: record_kind bits 5-7 (3
                          ; bits, 0-7, PICKUP_TYPE_* in main.pasm only use
                          ; 0-4) -- real only when kind==SPAWN_KIND_PROP.
SPAWN_PICKUP_MASK  = $07  ; explicit mask AFTER the >>5 shift

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
    sta.l Entity4_IsBoss
    sta.l Entity5_IsBoss

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
    asl a                       ; count*8
    sta.l Spawn_CountX8         ; store *8 directly into the final dest --
                                 ; Spawn_ScratchIdx itself (source) is
                                 ; untouched, so it can be re-read below for
                                 ; the *2 term. Avoids both a new WRAM scratch
                                 ; cell (which would ripple every hand-synced
                                 ; address after it -- see this file's own
                                 ; header on that cost) and stack-relative
                                 ; addressing (unverified Poppy support).
    lda.l Spawn_ScratchIdx
    asl a                       ; count*2
    clc
    adc.l Spawn_CountX8         ; count*2 + count*8 = count*10
                                 ; (claude_close_g7_g8_before_g10.md Part 2/3:
                                 ; record size grew 9->10, still not a power
                                 ; of 2 -- same shift-and-add idiom main.pasm's
                                 ; own *17 seek already uses)
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

    ; --- cache the last record's trigger_x (Spawn_CountX8 - 10 is its base
    ; offset; records are packed in ascending trigger order, see header) ---
    lda.l Spawn_CountX8
    sec
    sbc #10
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
    bne Spawn_Play__wait_release_active
    brl Spawn_Play__wait_check_done
Spawn_Play__wait_release_active:
    lda #0
    sta.l Spawn_ScratchEnemyCount
    lda.l G13_TwoPlayerEnabled
    bne Spawn_Play__wc_slot2
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
    lda.l Entity4_Hp
    beq Spawn_Play__wc_slot5
    lda.l Entity4_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Spawn_Play__wc_slot5
    lda.l Spawn_ScratchEnemyCount
    inc a
    sta.l Spawn_ScratchEnemyCount
Spawn_Play__wc_slot5:
    lda.l Entity5_Hp
    beq Spawn_Play__wc_sum_done6
    lda.l Entity5_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Spawn_Play__wc_sum_done6
    lda.l Spawn_ScratchEnemyCount
    inc a
    sta.l Spawn_ScratchEnemyCount
Spawn_Play__wc_sum_done6:
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
    lda.l G13_TwoPlayerEnabled
    bne Spawn_Play__gc_slot2
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
    lda.l Entity4_Hp
    beq Spawn_Play__gc_slot5
    lda.l Entity4_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Spawn_Play__gc_slot5
    lda.l Spawn_ScratchEnemyCount
    inc a
    sta.l Spawn_ScratchEnemyCount
Spawn_Play__gc_slot5:
    lda.l Entity5_Hp
    beq Spawn_Play__gc_sum_done6
    lda.l Entity5_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq Spawn_Play__gc_sum_done6
    lda.l Spawn_ScratchEnemyCount
    inc a
    sta.l Spawn_ScratchEnemyCount
Spawn_Play__gc_sum_done6:
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
    asl a                       ; index*8
    sta.l Spawn_ScratchX        ; temp: index*8 (Spawn_ScratchX is captured
                                 ; fresh by this same routine below, well
                                 ; after X is derived here -- safe reuse, not
                                 ; a new WRAM cell, see Spawn_Init's own note
                                 ; on why that ripple is avoided)
    lda.l Spawn_ScratchIdx
    asl a                       ; index*2
    clc
    adc.l Spawn_ScratchX        ; index*2 + index*8 = index*10
                                 ; (claude_close_g7_g8_before_g10.md Part 2/3:
                                 ; record size grew 9->10)
    tax                         ; X = this record's base offset, 0..(SPAWN_MAX_RECORDS-1)*10

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
    ; plan_game.md 8a row 3 (`map`): this byte packs TWO fields (kind: bits
    ; 0-2, map: bits 3-4) -- decode each with its own shift+mask. Roster
    ; index moved to its own +8 byte (roster-growth slice), read separately
    ; below.
    pha
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    and #SPAWN_PICKUP_MASK
    sta.l Spawn_ScratchPickupType
    pla
    pha
    lsr a
    lsr a
    lsr a
    and #SPAWN_MAP_MASK
    sta.l Spawn_ScratchMap
    pla
    and #SPAWN_KIND_MASK
    sta.l Spawn_ScratchKind
    inx                         ; X -> record+7 (spawn_hp, health-override slice)
    lda.l SpawnTable_Wram,x
    sta.l Spawn_ScratchHp
    inx                         ; X -> record+8 (item_roster_idx, claude_
                                 ; close_g7_g8_before_g10.md Part 2/3)
    lda.l SpawnTable_Wram,x
    sta.l Spawn_ScratchItemRosterIdx
    inx                         ; X -> record+9 (object_roster_idx)
    lda.l SpawnTable_Wram,x
    sta.l Spawn_ScratchRosterIdx

    ; --- wait/group/boss slice: wait/group markers dequeue unconditionally
    ; once triggered+group-gated (matching BOR.C -- they don't wait on a
    ; free AI slot, unlike an actual spawn), so dispatch them BEFORE
    ; find_slot below. ---
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_WAIT
    beq Spawn_Play__do_wait
    cmp #SPAWN_KIND_GROUP
    beq Spawn_Play__do_group
    cmp #SPAWN_KIND_BOSS_IDENTIFIED
    beq Spawn_Play__gate_stream
    ; Real prop/pickup sprite art (notjustfreespecial.txt follow-up): a
    ; SPAWN_KIND_PROP record with a real +8 roster_idx (build_spawn_table.py
    ; found this item's own real converted sprite in the actual shipped
    ; roster) needs the exact same Msu1_StreamBusy gate as a boss
    ; reassignment, for the exact same reason -- Spawn_DoRosterReassign
    ; streams a frame. roster_idx==0 (no matching converted prop slot yet)
    ; skips this gate entirely, unchanged pre-existing behavior.
    cmp #SPAWN_KIND_PROP
    bne Spawn_Play__find_slot
    lda.l Spawn_ScratchRosterIdx
    beq Spawn_Play__find_slot
Spawn_Play__gate_stream:
    ; --- roster-reassignment slice: gate the WHOLE record (not just the
    ; reassignment step below) on Msu1_StreamBusy, BEFORE find_slot runs
    ; and BEFORE any of this record's HP/position/palette writes touch a
    ; slot. If this deferred instead, after find_slot had already picked a
    ; slot and slot1/2/3's body had already set that slot's HP nonzero, a
    ; retry next frame would see the target slot as "occupied" (Hp!=0) and
    ; misroute to a DIFFERENT free slot -- or spuriously report "no free
    ; slot" if none else is free -- rather than finishing this same
    ; record's placement. Deferring here instead, before ANY state
    ; mutation, keeps the retry byte-for-byte identical to this frame's
    ; attempt (matches this file's existing "stay pending" convention for
    ; trigger-not-reached/no-free-slot). ---
    lda.l Msu1_StreamBusy
    beq Spawn_Play__find_slot
    plp
    rtl

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
    lda.l G13_TwoPlayerEnabled
    bne Spawn_Play__find_slot_check2
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
    bne Spawn_Play__find_slot_check4
    jmp Spawn_Play__slot3
Spawn_Play__find_slot_check4:
    lda.l Entity4_Hp
    bne Spawn_Play__find_slot_check5
    rep #$30
.a16
.i16
    lda #CHAR_ZP_LEN*4
    tax
    jmp Spawn_Play__slot45
Spawn_Play__find_slot_check5:
    lda.l Entity5_Hp
    bne Spawn_Play__find_slot_none
    rep #$30
.a16
.i16
    lda #CHAR_ZP_LEN*5
    tax
    jmp Spawn_Play__slot45
Spawn_Play__find_slot_none:
    plp
    rtl                         ; no free slot -- record stays pending
Spawn_Play__slot1:
    ; Capture BEFORE anything below overwrites Entity1_InputDriven -- see
    ; Spawn_ScratchPrevWasProp's own header comment.
    sep #$20
.a8
    lda #0
    sta.l Spawn_ScratchPrevWasProp
    lda.l Entity1_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Spawn_Play__slot1_prevflag_not_prop
    lda #1
    sta.l Spawn_ScratchPrevWasProp
Spawn_Play__slot1_prevflag_not_prop:
    ; Real bug found regression-testing the slot-reuse restore fix
    ; (finish_g8_with_runtime_asset_swapping.md): this gate used to fire
    ; ONLY when the outgoing occupant was a real prop (guarding the
    ; restore-to-default-character reassignment in the not_boss branch
    ; below). But the not_prop/enemy branch further down ALSO does real,
    ; unconditional raw MSU-1 hardware I/O every single spawn -- Anim_
    ; ApplyMapPalette's own seek+read of $2000-$2003, called for every
    ; enemy/boss record regardless of map value (0 still seeks the
    ; character's own base palette). That call had NO busy gate at all.
    ; Landing it while another entity's per-frame stream still has a
    ; queued CC-DMA transfer in flight (Msu1_StreamBusy!=0) collides two
    ; independent readers of the single MSU-1 data port ($2001) -- exactly
    ; the corruption CLAUDE.md's one-stream-per-frame rule exists to
    ; prevent. Confirmed via live WRAM polling: CharSelect_RosterCount
    ; (main.pasm's Anim_LoadCharacter, unrelated call) came back reading
    ; garbage bytes off the MSU port a couple frames after this branch
    ; started firing every spawn once MONEY/MEAT/1UP made non-prop records
    ; interleave with prop records much more often. Made this check
    ; unconditional -- nothing has mutated yet at this point (same "gate
    ; before touching anything" discipline as the top-level SPAWN_KIND_
    ; BOSS_IDENTIFIED/PROP dispatch gate above), so bailing is a clean
    ; no-op retry next frame -- Spawn_Index hasn't advanced.
    lda.l Msu1_StreamBusy
    beq Spawn_Play__slot1_prevflag_done
    plp
    rtl
Spawn_Play__slot1_prevflag_done:
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
    lda.l Spawn_ScratchPickupType   ; G8 item/pickup slice
    sta.l Entity1_PickupType
    lda.l Spawn_ScratchItemRosterIdx   ; claude_close_g7_g8_before_g10.md Part 2
    sta.l Entity1_ItemRosterIdx
    ; Real prop/pickup sprite art: Msu1_StreamBusy already confirmed clear
    ; by the dispatch-time gate above (before find_slot ran) whenever
    ; Spawn_ScratchRosterIdx != 0 -- safe to stream now, same reasoning as
    ; Spawn_Play__slot1_boss_identified below.
    lda.l Spawn_ScratchRosterIdx
    beq Spawn_Play__slot1_prop_no_reassign
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
Spawn_Play__slot1_prop_no_reassign:
    jmp Spawn_Play__advance
Spawn_Play__slot1_not_prop:
    sep #$20
.a8
    lda #CHAR_INPUT_DRIVEN_AI
    sta.l Entity1_InputDriven
    lda.l Spawn_ScratchHp       ; health-override slice -- was `lda #CHAR_HP_MAX`
    sta.l Entity1_Hp
    ; G8 item/pickup slice: an enemy record never carries a real pickup
    ; effect -- clear a previous prop occupant's stale CHAR_PICKUP_TYPE so
    ; this slot can't re-trigger it later.
    lda #0
    sta.l Entity1_PickupType
    sta.l Entity1_ItemRosterIdx   ; claude_close_g7_g8_before_g10.md Part 2:
                                   ; same stale-state guard for the reveal target
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
    cmp #SPAWN_KIND_BOSS_IDENTIFIED
    beq Spawn_Play__slot1_boss_identified
    cmp #SPAWN_KIND_BOSS
    beq Spawn_Play__slot1_is_boss
    ; claude_close_g7_g8_before_g10.md Part 6: the map-palette-reapply
    ; block above pushed Spawn_Play__slot1_not_boss out of bne's +-127
    ; range -- CLAUDE.md's own documented workaround (invert + brl).
    brl Spawn_Play__slot1_not_boss
Spawn_Play__slot1_is_boss:
.a8
    lda #1
    sta.l Entity1_IsBoss
    ; An unidentified SPAWN_KIND_BOSS record is just as real-art-silent as
    ; an ordinary enemy record (no Spawn_DoRosterReassign call otherwise)
    ; -- same slot1_not_boss restore-if-prev-was-prop logic applies here
    ; too, not just the plain-enemy path.
    lda.l Spawn_ScratchPrevWasProp
    beq Spawn_Play__slot1_boss_no_restore
    lda #1
    sta.l Spawn_ScratchRosterIdx
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
    ; claude_close_g7_g8_before_g10.md Part 6: re-apply this record's own
    ; map palette AFTER Spawn_DoRosterReassign, not just before -- Anim_
    ; LoadCharacter (called by DoRosterReassign) unconditionally reloads
    ; this slot's TRUE base palette, silently clobbering the map-index
    ; write the earlier unconditional Anim_ApplyMapPalette call (above,
    ; shared by every kind) already made using the PRE-reassignment
    ; (stale, possibly a totally different character's) MapBase/
    ; PaletteSlot fields. Real bug found live via game_map_remap.py (JOE
    ; map=3 landed on JOE's own base palette instead of remap[2] -- masked
    ; until this closure task's own G2 fix made entity2 a real boot-time
    ; prop, so no earlier record had ever reassigned identity while also
    ; requesting a nonzero map). MapApply_Index still holds Spawn_
    ; ScratchMap from this dispatch's earlier fill -- only the
    ; PaletteBase/MapBase/PaletteSlot fields need re-reading, now that
    ; DoRosterReassign has updated them to the NEW identity's real values.
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
Spawn_Play__slot1_boss_no_restore:
    jmp Spawn_Play__advance
Spawn_Play__slot1_boss_identified:
.a8
    ; roster-reassignment slice: Msu1_StreamBusy already confirmed clear
    ; by the dispatch-time gate above, before find_slot even ran -- safe
    ; to stream now, nothing else can have set it since (single-threaded).
    lda #1
    sta.l Entity1_IsBoss
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
    ; Re-apply the map palette after reassignment -- see the boss-restore
    ; branch's own comment above for the real bug this closes.
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
    jmp Spawn_Play__advance
Spawn_Play__slot1_not_boss:
    sep #$20
.a8
    lda #0
    sta.l Entity1_IsBoss
    ; Slot-reuse art-leak fix (finish_g8_with_runtime_asset_swapping.md):
    ; an ordinary (non-identified) enemy record never calls Anim_
    ; LoadCharacter on its own -- restore this slot's own natural boot
    ; default character (JHUN, roster index 1 -- see CharacterEntity_
    ; Init's role-1 branch) first if the entity being overwritten was a
    ; real prop. Msu1_StreamBusy already confirmed clear by the prevflag
    ; block above, before any of this record's own writes landed.
    lda.l Spawn_ScratchPrevWasProp
    beq Spawn_Play__slot1_no_restore
    lda #1
    sta.l Spawn_ScratchRosterIdx
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
    ; Re-apply the map palette after reassignment -- see slot1_boss's own
    ; comment above for the real bug this closes.
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
Spawn_Play__slot1_no_restore:
    jmp Spawn_Play__advance
Spawn_Play__slot2:
    ; See slot1's own identical comment/pattern (unconditional Msu1_
    ; StreamBusy gate -- Anim_ApplyMapPalette below fires every spawn,
    ; not just a prop restore; see slot1's full explanation).
    sep #$20
.a8
    lda #0
    sta.l Spawn_ScratchPrevWasProp
    lda.l Entity2_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Spawn_Play__slot2_prevflag_not_prop
    lda #1
    sta.l Spawn_ScratchPrevWasProp
Spawn_Play__slot2_prevflag_not_prop:
    lda.l Msu1_StreamBusy
    beq Spawn_Play__slot2_prevflag_done
    plp
    rtl
Spawn_Play__slot2_prevflag_done:
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
    lda.l Spawn_ScratchPickupType   ; G8 item/pickup slice
    sta.l Entity2_PickupType
    lda.l Spawn_ScratchItemRosterIdx   ; claude_close_g7_g8_before_g10.md Part 2
    sta.l Entity2_ItemRosterIdx
    ; Real prop/pickup sprite art -- see slot1's own identical comment.
    lda.l Spawn_ScratchRosterIdx
    beq Spawn_Play__slot2_prop_no_reassign
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN*2
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
Spawn_Play__slot2_prop_no_reassign:
    jmp Spawn_Play__advance
Spawn_Play__slot2_not_prop:
    sep #$20
.a8
    lda #CHAR_INPUT_DRIVEN_AI
    sta.l Entity2_InputDriven
    lda.l Spawn_ScratchHp       ; health-override slice -- was `lda #CHAR_HP_MAX`
    sta.l Entity2_Hp
    lda #0                      ; G8 item/pickup slice -- see slot1's own comment
    sta.l Entity2_PickupType
    sta.l Entity2_ItemRosterIdx  ; claude_close_g7_g8_before_g10.md Part 2
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
    cmp #SPAWN_KIND_BOSS_IDENTIFIED
    beq Spawn_Play__slot2_boss_identified
    cmp #SPAWN_KIND_BOSS
    beq Spawn_Play__slot2_is_boss
    ; See slot1's identical branch-range workaround comment.
    brl Spawn_Play__slot2_not_boss
Spawn_Play__slot2_is_boss:
.a8
    lda #1
    sta.l Entity2_IsBoss
    ; See slot1's identical unidentified-boss restore comment.
    lda.l Spawn_ScratchPrevWasProp
    beq Spawn_Play__slot2_boss_no_restore
    lda #2
    sta.l Spawn_ScratchRosterIdx
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN*2
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
    ; Re-apply the map palette after reassignment -- see slot1's own
    ; comment (Spawn_Play__slot1_boss_identified's own reassign block) for
    ; the real bug this closes.
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
Spawn_Play__slot2_boss_no_restore:
    jmp Spawn_Play__advance
Spawn_Play__slot2_boss_identified:
.a8
    lda #1
    sta.l Entity2_IsBoss
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN*2
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
    ; Re-apply the map palette after reassignment -- see slot1's own
    ; comment for the real bug this closes.
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
    jmp Spawn_Play__advance
Spawn_Play__slot2_not_boss:
    sep #$20
.a8
    lda #0
    sta.l Entity2_IsBoss
    ; See slot1_not_boss's own identical comment -- restores JOE (roster
    ; index 2, this slot's own natural boot default).
    lda.l Spawn_ScratchPrevWasProp
    beq Spawn_Play__slot2_no_restore
    lda #2
    sta.l Spawn_ScratchRosterIdx
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN*2
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
    ; Re-apply the map palette after reassignment -- see slot1's own
    ; comment for the real bug this closes.
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
Spawn_Play__slot2_no_restore:
    jmp Spawn_Play__advance
Spawn_Play__slot3:
    ; See slot1's own identical comment/pattern (unconditional Msu1_
    ; StreamBusy gate -- Anim_ApplyMapPalette below fires every spawn,
    ; not just a prop restore; see slot1's full explanation).
    sep #$20
.a8
    lda #0
    sta.l Spawn_ScratchPrevWasProp
    lda.l Entity3_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Spawn_Play__slot3_prevflag_not_prop
    lda #1
    sta.l Spawn_ScratchPrevWasProp
Spawn_Play__slot3_prevflag_not_prop:
    lda.l Msu1_StreamBusy
    beq Spawn_Play__slot3_prevflag_done
    plp
    rtl
Spawn_Play__slot3_prevflag_done:
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
    lda.l Spawn_ScratchPickupType   ; G8 item/pickup slice
    sta.l Entity3_PickupType
    lda.l Spawn_ScratchItemRosterIdx   ; claude_close_g7_g8_before_g10.md Part 2
    sta.l Entity3_ItemRosterIdx
    ; Real prop/pickup sprite art -- see slot1's own identical comment.
    lda.l Spawn_ScratchRosterIdx
    beq Spawn_Play__slot3_prop_no_reassign
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN*3
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
Spawn_Play__slot3_prop_no_reassign:
    jmp Spawn_Play__advance
Spawn_Play__slot3_not_prop:
    sep #$20
.a8
    lda #CHAR_INPUT_DRIVEN_AI
    sta.l Entity3_InputDriven
    lda.l Spawn_ScratchHp       ; health-override slice -- was `lda #CHAR_HP_MAX`
    sta.l Entity3_Hp
    lda #0                      ; G8 item/pickup slice -- see slot1's own comment
    sta.l Entity3_PickupType
    sta.l Entity3_ItemRosterIdx  ; claude_close_g7_g8_before_g10.md Part 2
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
    cmp #SPAWN_KIND_BOSS_IDENTIFIED
    beq Spawn_Play__slot3_boss_identified
    cmp #SPAWN_KIND_BOSS
    beq Spawn_Play__slot3_is_boss
    ; See slot1's identical branch-range workaround comment.
    brl Spawn_Play__slot3_not_boss
Spawn_Play__slot3_is_boss:
.a8
    lda #1
    sta.l Entity3_IsBoss
    ; See slot1's identical unidentified-boss restore comment.
    lda.l Spawn_ScratchPrevWasProp
    beq Spawn_Play__slot3_boss_no_restore
    lda #3
    sta.l Spawn_ScratchRosterIdx
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN*3
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
    ; Re-apply the map palette after reassignment -- see slot1's own
    ; comment (Spawn_Play__slot1_boss_identified's own reassign block) for
    ; the real bug this closes.
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
Spawn_Play__slot3_boss_no_restore:
    jmp Spawn_Play__advance
Spawn_Play__slot3_boss_identified:
.a8
    lda #1
    sta.l Entity3_IsBoss
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN*3
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
    ; Re-apply the map palette after reassignment -- see slot1's own
    ; comment for the real bug this closes.
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
    jmp Spawn_Play__advance
Spawn_Play__slot3_not_boss:
    sep #$20
.a8
    lda #0
    sta.l Entity3_IsBoss
    ; See slot1_not_boss's own identical comment -- restores YASHIRO
    ; (roster index 3, this slot's own natural boot default).
    lda.l Spawn_ScratchPrevWasProp
    beq Spawn_Play__slot3_no_restore
    lda #3
    sta.l Spawn_ScratchRosterIdx
    rep #$30
.a16
.i16
    ldx #CHAR_ZP_LEN*3
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
    ; Re-apply the map palette after reassignment -- see slot1's own
    ; comment for the real bug this closes.
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
Spawn_Play__slot3_no_restore:
    jmp Spawn_Play__advance

; Slots 4 and 5 share this indexed spawn path. It deliberately writes the
; common CharacterEntity fields through the selected object's DP window and
; keeps slot/roster/OAM/VRAM identity separate. The older slot-specific
; routines remain the four-actor compatibility path while this bounded path
; proves the added slots use the same spawn kinds and map application.
Spawn_Play__slot45:
    rep #$31
.a16
.i16
    txa
    sta.l Spawn_ScratchSlotOfs
    phd
    phb
    sep #$20
.a8
    lda #$7E
    pha
    plb
    rep #$31
.a16
.i16
    lda.l Spawn_ScratchSlotOfs
    clc
    adc #$0A00
    tcd
    lda.l Spawn_ScratchSlotOfs
    tax
    sep #$20
.a8
    jsl Spawn_ResetKnockdownFall
    rep #$20
.a16
    lda.l Spawn_ScratchX
    sta CHAR_POS_X
    sep #$20
.a8
    lda.l Spawn_ScratchY
    sta CHAR_POS_Y
    lda.l Spawn_ScratchFacing
    sta CHAR_FACING_LEFT
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_PROP
    beq Spawn_Play__slot45_prop
    lda #CHAR_INPUT_DRIVEN_AI
    sta CHAR_INPUT_DRIVEN
    lda.l Spawn_ScratchHp
    sta CHAR_HP
    stz CHAR_PICKUP_TYPE
    rep #$30
.a16
.i16
    lda.l Spawn_ScratchSlotOfs
    cmp #CHAR_ZP_LEN*4
    bne Spawn_Play__slot45_clear_item5
    sep #$20
.a8
    lda #0
    sta.l Entity4_ItemRosterIdx
    bra Spawn_Play__slot45_common
Spawn_Play__slot45_clear_item5:
    sep #$20
.a8
    lda #0
    sta.l Entity5_ItemRosterIdx
    bra Spawn_Play__slot45_common
Spawn_Play__slot45_prop:
    sep #$20
.a8
    lda #CHAR_INPUT_DRIVEN_PROP
    sta CHAR_INPUT_DRIVEN
    lda #CHAR_HP_PER_HIT
    sta CHAR_HP
    lda.l Spawn_ScratchPickupType
    sta CHAR_PICKUP_TYPE
    ; The contained item identity is per actor slot, not the loaded roster
    ; identity. Keep it in the same standalone metadata cells used by slots
    ; 1-3 so reveal/slot reuse cannot leak it.
    rep #$30
.a16
.i16
    lda.l Spawn_ScratchSlotOfs
    tax
    sep #$20
.a8
    lda.l Spawn_ScratchItemRosterIdx
    cpx #CHAR_ZP_LEN*4
    bne Spawn_Play__slot45_item5
    sta.l Entity4_ItemRosterIdx
    bra Spawn_Play__slot45_common
Spawn_Play__slot45_item5:
    sta.l Entity5_ItemRosterIdx
Spawn_Play__slot45_common:
    sep #$20
.a8
    lda.l Spawn_ScratchSlotOfs
    cmp #CHAR_ZP_LEN*4
    bne Spawn_Play__slot45_boss5
    lda #0
    sta.l Entity4_IsBoss
    bra Spawn_Play__slot45_boss_done
Spawn_Play__slot45_boss5:
    lda #0
    sta.l Entity5_IsBoss
Spawn_Play__slot45_boss_done:
    sep #$20
.a8
    lda #$FF
    sta CHAR_GRAB_TARGET
    sta CHAR_GRABBED_BY
    stz CHAR_GRAB_TIMER
    stz CHAR_GRAB_OFFSET
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_BOSS
    beq Spawn_Play__slot45_mark_boss
    cmp #SPAWN_KIND_BOSS_IDENTIFIED
    bne Spawn_Play__slot45_boss_mark_done
Spawn_Play__slot45_mark_boss:
    lda.l Spawn_ScratchSlotOfs
    cmp #CHAR_ZP_LEN*4
    bne Spawn_Play__slot45_mark_boss5
    lda #1
    sta.l Entity4_IsBoss
    bra Spawn_Play__slot45_boss_mark_done
Spawn_Play__slot45_mark_boss5:
    lda #1
    sta.l Entity5_IsBoss
Spawn_Play__slot45_boss_mark_done:
    ; A slot-4/5 ordinary spawn retains its initialized roster art. Props
    ; and bosses use the established gated reassignment helper.
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_PROP
    beq Spawn_Play__slot45_reassign
    cmp #SPAWN_KIND_BOSS
    beq Spawn_Play__slot45_reassign
    cmp #SPAWN_KIND_BOSS_IDENTIFIED
    bne Spawn_Play__slot45_done
Spawn_Play__slot45_reassign:
    rep #$30
.a16
.i16
    lda.l Spawn_ScratchSlotOfs
    tax
    jsr Spawn_DoRosterReassign
    sep #$20
.a8
Spawn_Play__slot45_done:
    plb
    pld
    jmp Spawn_Play__advance

Spawn_Play__advance:
    sep #$20
.a8
    ; OpenBOR switches to level bossmusic when the real boss entity is
    ; spawned.  This remains a data-driven stage lookup; non-boss records
    ; and stages without an authored bossmusic directive are no-ops.
    lda.l Spawn_ScratchKind
    cmp #SPAWN_KIND_BOSS
    beq Spawn_Play__advance_boss_music
    cmp #SPAWN_KIND_BOSS_IDENTIFIED
    bne Spawn_Play__advance_index
Spawn_Play__advance_boss_music:
    jsl Music_SelectBossTrack_Long
Spawn_Play__advance_index:
    lda.l Spawn_Index
    inc a
    sta.l Spawn_Index
    plp
    rtl
Spawn_Play__not_yet:
    plp
    rtl

; ============================================================================
; Spawn_DoRosterReassign -- roster-reassignment slice (real, user-requested
; follow-up to the "deliberate scope cut" this file's header used to
; document: every spawn used to render using whichever roster character was
; already wired to its slot, never its own real converted character).
;
; Switches the Direct Page register (phd/tcd/pld) to the AI entity at byte
; offset X within OopObjRam ($7E0A00 + X), sets the global CharSelect_Index
; to Spawn_ScratchRosterIdx, and re-runs Anim_LoadCharacter (main.pasm,
; reached here via its existing Anim_LoadCharacter_Long bank-0 jsl
; trampoline -- added earlier for core/charselect.pasm's own identical
; cross-bank need). This is NOT new streaming machinery: it is the exact
; same live mid-game character (re)load Anim_Play already runs for the
; player's own Select-button reselect (main.pasm ~6796, `sta.l
; CharSelect_Index` then `jsr Anim_LoadCharacter`) -- already proven safe to
; call mid-gameplay, with NMI active, competing with other entities' normal
; per-frame animation streaming. This routine is DP-targeted at whichever
; AI slot the caller names instead of always slot 0.
;
; Why phd/tcd is safe here even though Anim_LoadCharacter's body uses bare
; (DP-relative) CHAR_* addressing throughout: WRAM $7E0000-$7E1FFF is
; mirrored at bank $00 $0000-$1FFF (standard LoROM shadow-WRAM mapping), and
; $7E0A00+X falls inside that mirrored window for every real entity offset
; (X = CHAR_ZP_LEN, *2, or *3) -- so D = $0A00+X makes every subsequent bare
; DP-relative write inside Anim_LoadCharacter land on the exact same
; physical byte core/oop.pasm's own Core_Oop_Play would reach for that slot
; via its OopDp table (same value, computed directly here from the byte
; offset the caller already has, instead of re-reading OopDp).
;
;   in:  X (16-bit) = entity byte offset (CHAR_ZP_LEN, *2, or *3)
;        Spawn_ScratchRosterIdx = target roster slot (0-14, roster-growth slice)
;   out: none. Clobbers A/X. D is saved/restored (phd/pld) -- caller's own D
;        is unaffected.
;
; Caller's responsibility, not this routine's: confirm Msu1_StreamBusy==0
; before calling (CLAUDE.md: at most one entity may stream an animation
; frame per frame -- Anim_LoadCharacter's own blocking seek+read+CGRAM-DMA-
; enqueue is exactly that per-frame streaming-budget-consuming work). See
; Spawn_Play's SPAWN_KIND_BOSS_IDENTIFIED dispatch above for the real
; gate/defer logic -- gated once, before find_slot even runs, not here.
; ============================================================================
Spawn_DoRosterReassign:
.a16
.i16
    phd
    ; Anim_LoadCharacter's $2000-$2003 accesses are absolute hardware
    ; registers, so this helper must not inherit the caller's WRAM DBR
    ; (slot45 deliberately uses DBR=$7E for its actor window). Preserve the
    ; caller bank and establish DBR=$00 only for the loader call path.
    phb
    sep #$20
.a8
    lda #$00
    pha
    plb
    sep #$20
.a8
    lda.l CharSelect_Loaded
    sta.l Spawn_SavedCharSelectLoaded
    lda.l CharSelect_RosterCount
    sta.l Spawn_SavedCharSelectCount
    rep #$31
.a16
.i16
    txa
    clc
    adc #$0A00
    tcd
    sep #$20
.a8
    ; Save/restore CharSelect_Index around this write -- see Spawn_
    ; SavedCharSelectIndex's own header comment for the real bug this
    ; closes (a spawn-driven reassignment must never observably disturb
    ; the player's own persistent char-select/Select-button state).
    lda.l CharSelect_Index
    sta.l Spawn_SavedCharSelectIndex
    lda.l Spawn_ScratchRosterIdx
    sta.l CharSelect_Index
    sta CHAR_ROSTER_INDEX
    jsl Anim_LoadCharacter_Long
    sep #$20
.a8
    lda.l CharSelect_Loaded
    sta.l Spawn_RosterLoadResult
    ; ROOT CAUSE (animheaderstaging_shared_scratch_collision investigation,
    ; corrected): Anim_LoadCharacter's every exit path re-asserts .a16/.i16
    ; before its own rts (matches its "caller must be in .a16/.i16" header
    ; contract) -- so control returns here with M=0 (16-bit A), NOT the M=1
    ; this routine's own `sep #$20`/.a8 above set before the call. Without
    ; re-asserting 8-bit here, the two lines below silently became a single
    ; 16-bit lda.l/sta.l: `lda.l Spawn_SavedCharSelectIndex` pulled in BOTH
    ; Spawn_SavedCharSelectIndex (low byte, e.g. 0 for the player) AND
    ; whatever byte happens to follow it in WRAM as the high byte (not
    ; itself the bug -- just whatever was adjacent), then `sta.l
    ; CharSelect_Index` wrote BOTH bytes of that 16-bit
    ; value across CharSelect_Index ($7E53B6, low) AND the very next byte,
    ; CharSelect_RosterCount ($7E53B7, high) -- confirmed via live write-hook
    ; evidence: CharSelect_Index/RosterCount corrupted to 0/0 in lockstep,
    ; every time, deterministically, immediately after a live
    ; Spawn_DoRosterReassign call (not a race -- 100% reproducible once this
    ; width state is traced). This single missing directive is the entire
    ; bug; the previously-committed shared-AnimHeaderStaging-scratch theory
    ; in plan_game.md/project memory did not hold up under live tracing and
    ; has been corrected.
    sep #$20
.a8
    lda.l Spawn_SavedCharSelectIndex
    sta.l CharSelect_Index
    sep #$20
.a8
    lda.l Spawn_SavedCharSelectLoaded
    sta.l CharSelect_Loaded
    lda.l Spawn_SavedCharSelectCount
    sta.l CharSelect_RosterCount
    rep #$31
.a16
.i16
    plb
    pld
    lda.l Spawn_RosterLoadResult
    beq Spawn_DoRosterReassign__failed
    sec
    rts
Spawn_DoRosterReassign__failed:
    clc
    rts

; ============================================================================
; Spawn_RevealPendingItems -- claude_close_g7_g8_before_g10.md Part 2. Called
; once per frame (core/game_state.pasm's Game_State_Play, right after
; Spawn_Play) via jsl/rtl. A real breakable object (Chair/Table/Trash) that
; just broke in combat this frame was left at CHAR_HP==1 (a "broken, pending
; reveal" sentinel -- see main.pasm's Character_HitApply_VsEntity1/2/3, the
; only place that ever writes this exact value) with its EntityN_
; ItemRosterIdx still set to its contained item's real roster slot. This
; routine finds that slot and, ONLY if Msu1_StreamBusy==0 (the same one-
; stream-per-frame budget Spawn_Play's own SPAWN_KIND_PROP/BOSS_IDENTIFIED
; dispatch already respects), reassigns it to the item's own real converted
; sprite via the exact same Spawn_DoRosterReassign this file already uses
; for spawn-time identity -- then clears ItemRosterIdx so this slot won't
; re-trigger a reveal again. If Msu1_StreamBusy is busy (another entity
; streamed this same frame), this is a clean no-op retry: nothing here
; mutates any state before the busy check, so next frame tries again with
; byte-for-byte the same inputs. At most ONE reveal happens per frame, same
; discipline as everything else touching Msu1_StreamBusy in this project.
;
; No caller-convention assumed on entry (jsl/rtl). Clobbers A/X. Exits
; .a16/.i16 (matches Spawn_Play's own jsl/rtl exit convention, which this
; routine's caller runs immediately after).
; ============================================================================
Spawn_RevealPendingItems:
    php
    sep #$20
.a8
    lda.l Entity1_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Spawn_RevealPendingItems__check2
    lda.l Entity1_Hp
    cmp #1
    bne Spawn_RevealPendingItems__check2
    lda.l Entity1_ItemRosterIdx
    beq Spawn_RevealPendingItems__check2
    ldx #CHAR_ZP_LEN
    jsr Spawn_RevealPendingItems__do
    bra Spawn_RevealPendingItems__done
Spawn_RevealPendingItems__check2:
.a8
    lda.l Entity2_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Spawn_RevealPendingItems__check3
    lda.l Entity2_Hp
    cmp #1
    bne Spawn_RevealPendingItems__check3
    lda.l Entity2_ItemRosterIdx
    beq Spawn_RevealPendingItems__check3
    ldx #CHAR_ZP_LEN*2
    jsr Spawn_RevealPendingItems__do
    bra Spawn_RevealPendingItems__done
Spawn_RevealPendingItems__check3:
.a8
    lda.l Entity3_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Spawn_RevealPendingItems__check4
    lda.l Entity3_Hp
    cmp #1
    bne Spawn_RevealPendingItems__check4
    lda.l Entity3_ItemRosterIdx
    beq Spawn_RevealPendingItems__check4
    ldx #CHAR_ZP_LEN*3
    jsr Spawn_RevealPendingItems__do
    bra Spawn_RevealPendingItems__done
Spawn_RevealPendingItems__check4:
    sep #$20
.a8
    lda.l Entity4_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Spawn_RevealPendingItems__check5
    lda.l Entity4_Hp
    cmp #1
    bne Spawn_RevealPendingItems__check5
    lda.l Entity4_ItemRosterIdx
    beq Spawn_RevealPendingItems__check5
    ldx #CHAR_ZP_LEN*4
    jsr Spawn_RevealPendingItems__do
    bra Spawn_RevealPendingItems__done
Spawn_RevealPendingItems__check5:
    sep #$20
.a8
    lda.l Entity5_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Spawn_RevealPendingItems__done
    lda.l Entity5_Hp
    cmp #1
    bne Spawn_RevealPendingItems__done
    lda.l Entity5_ItemRosterIdx
    beq Spawn_RevealPendingItems__done
    ldx #CHAR_ZP_LEN*5
    jsr Spawn_RevealPendingItems__do
Spawn_RevealPendingItems__done:
    plp
    rep #$31
.a16
.i16
    rtl

; Leaf: X (8-bit-range value, still whatever width the caller's `ldx`
; left it in -- always .i8 range 0..CHAR_ZP_LEN*3 here) selects which
; EntityN_* set the calling branch above already resolved; A (still .a8,
; the just-loaded nonzero ItemRosterIdx) is this reveal's real target
; roster slot. Gates on Msu1_StreamBusy BEFORE touching anything, same
; "no mutation before the gate" discipline as Spawn_Play__gate_stream.
Spawn_RevealPendingItems__do:
    pha
    lda.l Msu1_StreamBusy
    bne Spawn_RevealPendingItems__do__busy
    pla
    sta.l Spawn_ScratchRosterIdx
    rep #$30
.a16
.i16
    phx                          ; REAL BUG found live-tracing this: Spawn_
                                  ; DoRosterReassign's own header says
                                  ; "Clobbers A/X" (its internal jsl Anim_
                                  ; LoadCharacter_Long call touches X) --
                                  ; the stale comment this replaces claimed
                                  ; the opposite ("preserves X, only
                                  ; clobbers A and D"), so the cpx dispatch
                                  ; below was comparing X against GARBAGE
                                  ; after the call, always falling through
                                  ; to the Entity3 branch regardless of
                                  ; which slot was really being revealed --
                                  ; the art reassignment itself worked, but
                                  ; the WRONG EntityN_ItemRosterIdx got
                                  ; cleared (or the right one, by
                                  ; coincidence, only when X happened to
                                  ; equal CHAR_ZP_LEN*3 already), so the
                                  ; real target's flag stayed stuck forever,
                                  ; confirmed via live WRAM polling (100%
                                  ; reproducible, not a race). Saved/
                                  ; restored across the call instead.
    jsr Spawn_DoRosterReassign
    bcc Spawn_RevealPendingItems__do__load_failed
    plx
    sep #$20
.a8
    ; Clear the SPECIFIC slot's own ItemRosterIdx -- X restored above.
    ; Three-way dispatch on X's value, same idiom this file's record-kind
    ; checks already use elsewhere.
    cpx #CHAR_ZP_LEN
    bne Spawn_RevealPendingItems__do__not1
    lda #0
    sta.l Entity1_ItemRosterIdx
    rts
Spawn_RevealPendingItems__do__not1:
.i16
    cpx #CHAR_ZP_LEN*2
    bne Spawn_RevealPendingItems__do__not2
.a8
    lda #0
    sta.l Entity2_ItemRosterIdx
    rts
Spawn_RevealPendingItems__do__not2:
.a8
    cpx #CHAR_ZP_LEN*3
    bne Spawn_RevealPendingItems__do__not3
    lda #0
    sta.l Entity3_ItemRosterIdx
    rts
Spawn_RevealPendingItems__do__not3:
.a8
    cpx #CHAR_ZP_LEN*4
    bne Spawn_RevealPendingItems__do__not4
    lda #0
    sta.l Entity4_ItemRosterIdx
    rts
Spawn_RevealPendingItems__do__not4:
    rep #$30
.a16
.i16
    cpx #CHAR_ZP_LEN*5
    bne Spawn_RevealPendingItems__do__not5
    lda #0
    sta.l Entity5_ItemRosterIdx
    rts
Spawn_RevealPendingItems__do__not5:
    ; Invalid target offsets are rejected. Never clear another actor's
    ; metadata as a fallback for a corrupted/stale dispatch value.
    rts
Spawn_RevealPendingItems__do__load_failed:
    plx
    rts
Spawn_RevealPendingItems__do__busy:
    pla
    rts
