# Plan: multiple simultaneous on-screen characters

> **START HERE IF YOU ARE PICKING THIS UP NEW.**
> **Phases 0–6 are finished, committed, and verified.** Four characters
> render simultaneously today — one player-controlled, three AI-controlled
> that seek the player and land stunning attacks — over a real converted
> Beats of Rage level backdrop, with a four-bar BG3 health HUD.
>
> Everything from here on lives in **[PART TWO](#part-two--long-horizon-plan-written-2026-08-09-after-phase-4-shipped)**
> near the bottom of this file, specifically **§2.5 (Phase 7, audio
> polish)** — Phases 5 and 6 are done. Part Two is written to be followed
> step-by-step, with exact commands and explicit stop conditions. **Go read
> Part Two now.** Note that §2.5 opens with its own hand-back gate.
>
> Part One (everything between here and Part Two) is the historical
> record of how Phases 0–4 were done. Read it for context on *why* the
> code is shaped the way it is — but it is history, not a to-do list.
> Note that Part One's OBJ tile-budget claim (that N=5 needs OBSEL's
> second bank) is **wrong**; Part Two §2.3 has the corrected arithmetic.
> Three real bugs were found and fixed during Phase 5 that weren't in the
> original 10-step plan (a DMA-queue palette hazard, a live
> `Character_BlankPadding` bug, and a leftover `TestSprite_Init` routine
> that clobbered entity 0's own palette color 1 via a hardcoded CGRAM
> write to palette 0) — see `handoff.md`'s Phase 5 section for the full
> account. All three are fixed and verified; none are open.

## TL;DR

Today exactly one animated character renders (a single 32×64 hardware OAM
sprite, streamed frame-by-frame from `bor.msu`). This plan gets to **two,
then a handful, of independently-animated, simultaneously-visible
characters** — the actual next step toward the original design's "1 player +
N enemies" proof of concept. It does **not** attempt combat polish, levels,
or the full OpenBOR scripting engine — see "Explicitly out of scope."

> **UPDATE (2026-08-16): read this before assuming "levels" means what it
> sounds like.** As of Phase 9/12 this engine renders a real, converted BOR
> level (stage 1A) with real characters (Ralf/JHUN/JOE) and real horizontal
> scrolling. That is **not** the same as "levels work" in the OpenBOR
> sense, and earlier phases of this doc did not draw that line clearly
> enough. See the new "What 'levels' actually means here, and what's
> missing" section right after "Explicitly out of scope" for the honest,
> corrected picture — it covers content coverage (1 of 14 stages, 3 of ~24
> characters converted), the complete absence of enemy spawn-wave/level-
> transition/win-condition logic, and why that logic isn't a small gap:
> real OpenBOR levels are driven by `openborscript`, a genuine embedded
> bytecode-VM scripting language, not declarative data. There is
> already real prior design work toward running that VM on this hardware
> (`openbor4086_sa1_bootstrap.zip`, untracked, in the repo root) — but it
> was never assembled or verified, and it targets a bank layout this
> project's Poppy-toolchain constraints don't allow as-is. **Update
> (still 2026-08-16): the spawn-wave gap is now closed** — Phase 13
> (§2.13) added a convert-time spawn table (no VM needed) that drives real
> enemy waves for stage 1A. Level-transition/win-condition logic is still
> not implemented. Read §2.13 before touching spawn behavior for stage 1A,
> or the "What 'levels' actually means" section above it before scoping a
> *second* level or the OpenBOR VM path.

Work through the phases **in order**. Phase 0 is a bug fix that is a hard
prerequisite — the current code has a real, deterministic data-corruption
bug that only manifests once a second entity starts animating, so it has
never been hit yet. Do not skip to Phase 2 without it.

Every phase ends with a verification gate. Do not start the next phase until
the current one's gate passes. If a gate fails, that is real signal — stop
and re-read the relevant "Ground truth" bullet below before improvising a
fix, since this codebase has a long history of subtle hardware/toolchain
traps that look like something else at first (see "Before you touch
anything").

## Before you touch anything

Read these first, in this order:

1. `CLAUDE.md` (this repo root) — build/test commands, architecture map,
   the Poppy-assembler-bugs summary.
2. Project memory `poppy_assembler_bugs.md` and `build.md`'s "Testing in
   Mesen2" + "Known harness gaps" sections — do not re-derive these from
   scratch, they document real, previously-confirmed silent-miscompile bugs
   and harness gaps.
3. This file, in full, before writing any code — later phases assume
   context established in earlier ones.

Standing rules that **will** bite this specific work if ignored (each has
already cost a real session in this project's history):

- **NMI is non-maskable.** Any WRAM cell a per-vblank NMI-driven routine
  reads must be zeroed/initialized *before* `Core_Nmi_Init` enables NMI at
  boot, not just "early in boot." `sei` does not protect against NMI. (See
  memory `boot_nmi_race_before_oam_init` — this exact bug shipped once
  already.) A new entity table is exactly the kind of new state that can
  re-trip this if it's touched by anything running under NMI before it's
  initialized.
- **Every new branch target or `jsr`/`jml` target needs a `nop` guard**
  before the label, matching the existing convention throughout
  `main.pasm`/`core/*.pasm` (search for `; workaround: Poppy label address
  off-by-one` for examples). Poppy has a confirmed bug where a label can
  resolve 1-2 bytes early relative to the real instruction stream. This has
  bitten both branch targets and `jsr` targets in this project. An entity
  system with N objects × M states will introduce a lot of new labels —
  budget real time for this, it is not optional cleanup.
- **Indexed WRAM (`$7E...`) access always uses `.l`, never `.w`.** `.w` on
  an indexed bank-`$7E` symbol silently drops the bank byte and corrupts
  the instruction stream, no error. Also: **`.l Symbol,y` is invalid and
  Poppy accepts it anyway**, silently emitting a wrong plain
  absolute-,Y instruction — 65816 has no long-indexed-by-Y addressing mode
  at all. Always index long addressing by `x`.
- **Fixed `.org` regions silently truncate on overflow.** After growing any
  code/data in the `$C100`-`$FC00` window (where all of this work lives),
  re-run the three `tools/rom_audit/*.py` scripts (see "Verification
  methodology" below) rather than trusting a clean build. A clean assemble
  is not proof nothing overran.
- **Don't trust one clean Mesen2 run.** This project's Mesen2 MCP harness
  has documented gaps (stale small reads, `read_memory` returning 0 for
  hardware registers, `set_input` being wall-clock/sleep-based rather than
  frame-exact, unreliable exec hooks, and a ~40% false-silent audio-check
  rate). Verify with ≥32-byte reads and majority-of-3 sessions for anything
  load-bearing, matching this project's established practice (see
  `temporal-swinging-hartmanis.md`-style plans in
  `C:\Users\chad\.claude\plans\` for the precedent).
- **`handoff.md` is currently stale** — it still describes a retired
  BG2-tilemap rendering architecture that no longer exists (self-flagged at
  its own top). Don't treat it as ground truth; `README.md`'s "Current
  Status" section is. Do refresh `handoff.md`'s "Recommended next step" at
  the end of each phase below — this project has an established convention
  of deriving each session's work from that field (see
  `curried-jingling-valiant.md` and `groovy-finding-kahn.md` in the plans
  directory above), and leaving it stale defeats that for whoever picks up
  after you.

## Ground truth as of this plan (verified directly against code this session — don't re-derive, but do re-verify anything time-sensitive before depending on it)

**Current rendering architecture.** Exactly one real hardware OAM sprite
exists: `Character_PlayFrame` (`src/main.pasm:3214-3322`), object size mode
6 "large" (32×64 pixels = 4 tiles wide × 8 tiles tall). It already fuses
what used to be three separate things — a decorative test square, a
dpad-driven test sprite, and the animated character — into one entity:
dpad input drives `Player_X`/`Player_Y` (also this sprite's screen
position), and `Anim_Play`/`Msu1_LoadFrame` streams whichever animation
frame is current into this same sprite's OBJ tile slot every time the
animation advances, with hflip driven by `Anim_FacingLeft`. There is
**no second sprite** today — do not plan around one existing.

**Runtime character roster.** Characters stream from `bor.msu` at runtime
(not baked into ROM), format supports up to 8 slots, currently 2 are
packed (`ROSTER_PREFIXES = ["out/ralf", "out/jhun"]` in `build_rom.py`).
The Select button live-cycles which **one** is loaded — never two at once
today. Adding a 3rd/4th roster character is already a solved, cheap,
independent problem: `python tools/bor_converter/convert_character.py
"Beats of Rage Original [v.3.0 Build 4086].pak" "DATA\CHARS\<NAME>\<NAME>.TXT"
out/<name>`, then add `"out/<name>"` to `ROSTER_PREFIXES`, then rebuild. Do
this early (Phase 0 or 1) to have real, distinct roster content ready for
Phase 2's second entity — it's independent of everything else in this plan
and de-risks nothing to defer.

**WRAM layout that already exists** (from `pack_msu_roster`/
`Anim_LoadCharacter`'s implementation — the plan that built it is
`C:\Users\chad\.claude\plans\temporal-swinging-hartmanis.md`, fully executed,
confirmed matching current `main.pasm`):

```
CharSelect_Index       = $7E53B6  ; .db -- current roster slot
CharSelect_RosterCount = $7E53B7  ; .db
CharSelect_Loaded      = $7E53B8  ; .db -- 0 while a (re)load is in progress
Anim_IdleFrameCount    = $7E53B9  ; .db
Anim_WalkFrameCount    = $7E53BA  ; .db
Anim_AttackFrameCount  = $7E53BB  ; .db
Anim_IdleDelay         = $7E53BC  ; .db
Anim_WalkDelay         = $7E53BD  ; .db
Anim_AttackDelay       = $7E53BE  ; .db
Anim_IdleMsuBaseLo     = $7E53BF  ; .dw
Anim_IdleMsuBaseHi     = $7E53C1  ; .db
Anim_WalkMsuBaseLo     = $7E53C2  ; .dw
Anim_WalkMsuBaseHi     = $7E53C4  ; .db
Anim_AttackMsuBaseLo   = $7E53C5  ; .dw
Anim_AttackMsuBaseHi   = $7E53C7  ; .db

AnimFrameStaging   = $7E2000  ; 768B -- one streamed frame, pre-DMA
AnimPaletteStaging = $7E2300  ; 32B
AnimHeaderStaging  = $7E2320  ; 16B  -- raw directory record + Msu1_LoadFrame's own scratch

OamSetSprite_X/Y/Tile/Attr/Hi = $7E53AB-$7E53AF  ; Core_Oam_SetSprite's staging cells
```

All of the above are today's **singleton, global** state — there is one of
each, assuming one character. Multiplying these N times is exactly what
Phase 1 below replaces with `core/oop.pasm` per-instance state instead (see
that phase — don't hand-duplicate these cells).

**ROM margin.** ~8.3KB free in the `$C100`-`$FC00` fixed-`.org` window as of
this build (computed from the highest label address in `src/main.sym`,
`$DAA4`, subtracted from `$FC00`). This is healthy — MSU-1 streaming's
prior implementation freed ~14.6KB by deleting ROM-baked animation blobs.
**Re-verify this yourself before depending on the number** — it will have
moved by the time you reach later phases. Quick recomputation:

```python
import re
labels = {}
with open('src/main.sym', encoding='utf-8', errors='replace') as f:
    for line in f:
        m = re.match(r'^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+(\S+)', line.strip())
        if m:
            labels[m.group(3)] = int(m.group(2), 16)
window = sorted(a for a in labels.values() if 0xC100 <= a < 0xFC00)
print('free bytes before $FC00:', 0xFC00 - window[-1])
```

Note this gives the start of the *last* label, not necessarily the true end
of the last blob (an `.incbin` has no end-label) — add the blob's real size
if the last thing in the window is a binary include, per `handoff.md`'s own
historical note on this same pitfall.

**`core/oop.pasm` is a real, complete, already-wired entity engine — not a
stub.** `Core_Oop_Init` is called from `scpu_boot` (`main.pasm:3790`),
`Core_Oop_Play` is called every frame from `scpu_main_loop`
(`main.pasm:4289`) — this dispatch is **already running today**, it just
has zero registered classes so it's a no-op. It supports 24 simultaneous
objects (`OOP_MAX_OBJECTS`) and 16 registered classes
(`OOP_MAX_CLASSES`), each object getting its own bump-allocated
direct-page window out of a 3072-byte pool (`OOP_OBJ_RAM_SIZE`,
`OopObjRam = $7E0a00`-`$7E15ff`). `Core_Oop_Create(a=init_param,
y=class_id)` allocates an instance and calls its `Init` routine with DP
already switched to that instance's own window; `Core_Oop_Play` calls
every live instance's `Play` routine the same way, once per frame, in
slot order. This is the mechanism Phase 1 below uses — read
`src/core/oop.pasm`'s full header comment and `Core_Oop_Create`/
`Core_Oop_Play` bodies before starting that phase, the handle/DP-window
mechanics matter for getting it right.

**`core/screen.pasm`** (camera follow) is similarly real but has zero
consumers — it queries a "focused" object's position via
`Core_Oop_Call`/`SCREEN_CMD_GET_CAMERA_DATA`, a contract no class
implements yet. Wiring a real player entity into it is a small, cheap
follow-on once Phase 1 exists, but **is not required by anything in this
plan** (the original spec's own proof-of-concept explicitly requires no
scrolling) — don't do it unless asked.

**OBJ tile-space budget for N simultaneous large sprites.** `OBSEL` is set
once at boot to `$C2` (`core/oam.pasm`, `Core_Oam_Init`): base word
address `$4000` (OBJ tile-block 0), size mode 6 (16×32 small / 32×64
large). A real hardware OAM tile fetch for a "large" object indexes tiles
as `(tileRow<<4)|tileColumn` within a 16-tile-wide, 8-tile-tall block
(Mesen2-source-verified — see `main.pasm:2872-2890`'s comment for the
exact citation). Today's one character occupies columns 0-3 of that block
(4 tiles wide), rows 0-7 (8 tall, only 6 carry real pixel data — rows 6-7
are pre-blanked padding). **That leaves columns 4-15 of block 0 free** —
three more 4-column slices, i.e. **N=4 simultaneous 32×64 characters fit
in the already-configured OBJ tile budget with zero new VRAM/OBSEL setup**,
by giving each entity instance its own column-offset (added to each
row's DMA target address: instance column offset `c` (0-3) adds `c*4*16`
words `= c*128` bytes to every row's target byte address). **N=5+ requires
OBSEL's second tile bank** (the "name select" field, currently unused) —
genuinely new, unverified territory; not needed for this plan's milestones,
defer it.

**The DMA queue is the sharp edge here — read this carefully.**
`core/dma.pasm`'s software DMA queue (`Core_Dma_Enqueue`/
`Core_Dma_ProcessQueue`) has exactly **8 slots total**
(`DMA_QUEUE_SLOTS=8`), shared between every DMA consumer in the project.
`Core_Dma_ProcessQueue` drains every contiguously-active slot in one call
(during `Core_Nmi_Play`, once per real vblank) — it is not a
per-frame-budget-limited partial drain. Two facts combine into a real,
deterministic bug, not a theoretical race:

1. One entity's `Msu1_LoadFrame` call (streaming one new animation frame)
   enqueues **6** row-DMAs (`main.pasm:2891-2927`, one per tile-row of the
   sprite) — 6 of the 8 total slots, on any frame that entity's animation
   advances. `Core_Oam_Play`'s own per-frame OAM upload consumes more of
   the same queue on top of that. **There is little to no spare slot
   capacity even with a single entity today** — it has simply never been
   exceeded because there's never been a second consumer.
2. `Msu1_LoadFrame_EnqueueRow` (`main.pasm:2942-2954`) calls
   `Core_Dma_Enqueue` and returns unconditionally — **the carry flag
   `Core_Dma_Enqueue` sets on success / clears on "queue full" is never
   checked.** A dropped enqueue is silent: that tile row's VRAM data is
   simply never updated that frame, leaving stale pixel data with no error
   anywhere.
3. `AnimFrameStaging` (`$7E2000`, 768 bytes) is a **single shared buffer**.
   `Msu1_LoadFrame` fills it synchronously, but the 6 DMAs it queues read
   from it **asynchronously**, at the next `Core_Nmi_Play`. If a second
   entity's `Msu1_LoadFrame` call happens later in the *same* main-loop
   iteration (i.e., before that vblank has fired), it overwrites
   `AnimFrameStaging` with its own frame's bytes before the first entity's
   queued DMAs have executed — so when they finally fire, they copy the
   *second* entity's pixel data into the *first* entity's VRAM tiles. This
   is 100% deterministic given the call ordering, not intermittent.

**This is why Phase 0 exists and is a hard prerequisite** — every later
phase depends on being able to stream more than one entity's frames
without this corruption.

**`Core_Oam_SetSprite` (`core/oam.pasm:480`), by contrast, is already safe
for repeated per-entity calls within one frame.** Its contract ("fill
`OamSetSprite_X/Y/Tile/Attr/Hi`, call once per sprite, `Oam_CurrentSlot`
auto-advances") is synchronous — no async-drain hazard like the DMA-queue
issue above. The one real wiring rule for multiple entities: **exactly one
entity per frame may reset `Oam_CurrentSlot` to 0.** Today
`Character_PlayFrame` does this unconditionally at its own top, because
it's the sole sprite writer. With N entities, only the *first* one called
each frame may do this; the rest must not, or every entity after the first
will silently overwrite sprite slot 0 instead of getting its own OAM slot.
`Core_Oop_Play`'s dispatch order (ascending slot-index) gives you a stable,
deterministic per-frame order to hang this rule on.

**OBJ palette budget.** CGRAM byte `$100` = color 128 = OBJ palette 0's
base (confirmed at `main.pasm:3703`'s existing comment). OBJ has 8 palette
slots of 16 colors (32 bytes) each: palette `N` lives at CGRAM byte
`$100 + N*32`. Today only palette 0 is ever loaded. Two simultaneously
visible *different* characters need *different* palettes (Ralf's and
JHUN's 16-color palettes are unrelated) — assign each entity instance its
own palette slot (0-7) at creation time and set that instance's OAM
attribute byte's palette bits accordingly (today hardcoded to "palette 0"
literals `$30`/`$70` in `Character_PlayFrame` — this needs to become
per-instance).

**Not the path this plan uses** (see next section for why): the SA-1
BW-RAM/CC-DMA software-sprite compositor (a separate, already-proven
subsystem — see memory `sa1_compositor_scaling_limit`) is real hardware
proof of the *original* spec's BG2-canvas enemy-rendering design, but its
pump throughput is ~1 tile/frame — a full N-tile canvas refresh takes
`24*N` frames (~8.4s at N=21), and it isn't wired to real character data
at all. Also not the path: an untracked, unintegrated scaffold for a full
OpenBOR bytecode VM
(`E:\gh\snes-bor\openbor4086_sa1_bootstrap.zip`, main checkout root, not
this worktree, not in git) — ambitious and well-specified, but 0/15 items
checked on its own Gate-0 checklist, and its assumed multi-bank memory
layout (`VM_DEFAULT_CODE_BANK=$C0`, etc.) directly contradicts this
project's established, deliberate bank-0-only convention
(`CLAUDE.md`). Both are explained further below.

## The architecture decision

The original design spec (`SNES-BOR-Engine-Prompt.md`) proposed enemies as
BG2-tilemap software sprites (CC-DMA'd from an SA-1 canvas) specifically to
route around OAM's limits, with only the player as a real OAM sprite. This
project's actual, shipped, verified-fast rendering technique for its one
real character is different: a single large OAM sprite, streamed from
MSU-1. That already-proven technique turns out to have real headroom (see
"OBJ tile-space budget" above — N=4 fits for free) and is not blocked by
the compositor's proven throughput ceiling.

**This plan extends the OAM+MSU-streaming approach to multiple
simultaneous entities, dispatched through `core/oop.pasm`, instead of
building out the BG2/CC-DMA canvas.** Concretely, that means:

- It reuses substantial already-built, already-verified infrastructure
  (`core/oop.pasm`'s dispatch engine, `core/oam.pasm`'s multi-sprite
  primitives, the MSU-1 roster/streaming pipeline) that is otherwise
  sitting completely idle.
- It doesn't hit the compositor's measured throughput ceiling — OAM+DMA
  frame streaming is already running at real 60fps for one character
  today.
- It's a real, deliberate deviation from the letter of the original spec's
  BG2-canvas design, but delivers the spec's actual *goal* (multiple
  simultaneously animated characters on screen) via a technique this
  project already organically proved out and that has documented, adequate
  headroom (N=4 free, N≤8 with more work on the second OBJ tile bank —
  comfortably past the spec's own "4 enemies" PoC target).

This is a deliberate call, not an oversight — if a future need genuinely
exceeds OAM's budget (more than ~8 simultaneous large sprites), the BG2
canvas is a legitimate parallel path to revisit, but only after its pump
rate is re-engineered to drain more than 1 tile/frame; don't reach for it
before that's true.

## Explicitly out of scope

- **The BG2/CC-DMA software-sprite canvas** as a rendering path for the
  entities this plan adds. Its hardware mechanism remains a valid, proven
  proof of concept for something else later, but not for this work — see
  "The architecture decision" above.
- **The OpenBOR bytecode VM bootstrap** (`openbor4086_sa1_bootstrap.zip`,
  untracked, repo root). Real, substantial pre-existing design work — see
  the section immediately below for the full, corrected account of what it
  actually contains and doesn't. If this is ever picked up, treat it as its
  own ground-up project with a real adaptation pass to this project's
  bank-0/WRAM conventions — not a drop-in.
- **Scrolling.** The original spec's own proof-of-concept explicitly
  requires none (single static screen). Don't add camera/scroll logic as
  part of this plan. **(Superseded 2026-08-10, by request — see §2.7,
  Phase 8. The statement above was correct for Part One and is kept as
  the record of why nothing here touches the camera; §2.7 is now the
  live plan for scrolling.)**
- **A character-select menu/UI**, save state, or persisting the roster
  selection across reset. Not asked for, not needed for this plan's goal.
- **Real damage/health/game-state systems.** Phase 4 below stops at "an
  enemy visibly reacts to being hit" — no HP tracking, no death, no win
  condition. Matches the original spec's own PoC scope ("no damage system
  required"). **(Partially superseded 2026-08-16, by request — see §2.11,
  Phase 11. HP tracking and AI soft-kill are now real; player death/game-
  over and any actual win condition remain out of scope — there is still
  no game loop, see the section below.)**
- **Audio content polish** beyond what's already boot-verified, until
  Phase 7 (last, roadmap-level, lowest priority).

## What "levels" actually means here, and what's missing (added 2026-08-16)

Read this before scoping "add a second level," "make enemies spawn," or
"let the player beat the game" — each of those sounds like a small
follow-on to what already works and isn't. This section exists because a
user Q&A session surfaced that this doc's own framing had drifted into
sounding more finished than the engine actually is.

**Content coverage, precisely.** The source `.pak`
(`Beats of Rage Original [v.3.0 Build 4086].pak`, repo root) contains 14
stages (`1A/1B/1C, 2, 3A/3B/3C, 4A/4B, 5A/5B, 6A/6B/6C`) × 3 difficulties,
and roughly two dozen playable/enemy characters (Angel, Biker-K, Billy,
Bink, Crab, Eiji, Heavy, JHUN, JOE, K9999, Kula, K, Lobster, Mary, Maxima,
Mighty, MrBig, Ralf, Ramon, Robert, Rugal, Shermie, Yamazaki, Yashiro).
This engine ships **1 of those 14 stages** (1A, `out/bg_stage1a`) and
**3 of those ~24 characters** (Ralf/JHUN/JOE — Entity #3 reuses JHUN a
second time). Nothing else has been converted; nothing here is blocked
from converting more, it's just not been asked for yet.

**There is no level-transition system, full stop.** Nothing in
`main.pasm` detects "reached the end of this level" or loads a different
one — `BG_SCREENS` in `build_rom.py` is a single hardcoded
`(background, hud)` tuple, period. The camera scrolls within the one
loaded level (Phase 8/9); nothing past its right edge exists to scroll
into.

**There is no win condition or game loop, but there IS now real spawn-wave
logic (Phase 13, §2.13, done 2026-08-16).** `CLAUDE.md` still says "this is
not a playable game... there is still no game loop," and that part remains
true — there's still no "all enemies dead → advance" check, because
there's still nothing to advance TO (no level-transition system, next
paragraph). But the 4 entities are no longer hardcoded-alive-forever the
way they were through Phase 12: a real spawn table (built from stage 1A's
own `spawn`/`at` script blocks) now drives when/where/facing each of the 3
AI slots gets placed, reusing Phase 11's `CHAR_HP==0` soft-kill sentinel as
"unspawned" too. See §2.13 for exactly what is and isn't modeled (position/
timing is faithful; character identity, per-spawn HP overrides, and
non-enemy spawns like the `1up` pickup are not).

**Why that's not a small gap: real OpenBOR levels are driven by a real
bytecode-VM scripting language, not declarative data.** This project's
own `tools/bg_converter/level_parse.py` only reads the purely-scenery
keywords out of a level `.txt` (`background`/`panel`/`frontpanel`/`order`)
— its own docstring says the rest is thrown away: *"spawn/group/wait/at
describe enemy waves and are ignored."* In real OpenBOR
(`DCurrent/openbor` on GitHub — also see `Plombo/beatsofrage`, the
original Beats of Rage engine source OpenBOR descends from, as a
secondary reference), *what happens* in a
level — enemy spawn waves, boss triggers, level-clear/level-transition,
HUD events — is controlled by `openborscript`: a genuine embedded C-like
scripting language with its own bytecode VM
(`engine/source/scriptlib/`: `Lexer.c` → `Parser.c` → `Interpreter.c`,
an `OpCode` enum of 48 values — `LOAD`, `SAVE`, `CALL`, `JUMP`,
`Branch_TRUE`, `ADD`, etc. — plus a typed `ScriptVariant` system and
symbol tables). None of that is implemented here. Not partially, not as
a stub — there is no script interpreter of any kind in this codebase.

**There IS real prior design work toward this — but it never got past
scaffolding.** `openbor4086_sa1_bootstrap.zip` (untracked, sitting in the
repo root right now — `git status` will show it) is a self-contained,
well-researched bootstrap attempt from an earlier session (2026-08-03),
built from the exact `DCurrent/openbor` source paths named above:
- `opcode_manifest.csv` — all 48 opcode values, names, operand shapes, and
  runtime semantics, cross-checked against the real `Instruction.h` enum
  (confirmed accurate when independently re-derived this session).
- `FORMAT.md` — a full binary module format spec (64-byte header, 8-byte
  instruction records, slot/callsite/string tables) meant to be produced
  by an offline Python linker rather than parsing OpenBOR script source on
  the SNES itself — a reasonable scope cut.
- `src/bor_vm_core.pasm` (~800 lines) + `src/bor_vm_opcodes.pasm` — a
  65816/SA-1 interpreter scaffold: direct-page VM state layout, status/
  error codes, fault handling design.
- `tests/gate0_program.json` + `tests/gate0_module.bin` +
  `tests/gate0_expected_slots.bin` — a first correctness milestone
  (sequential IP increment, `ADD`, `EQ`, `Branch_FALSE`, `JUMP`, `ERR`,
  root `RET` — nothing else) with real test fixtures.

**But `IMPLEMENTATION_CHECKLIST.md`'s every box is unchecked.** Gate 0 —
the deliberately tiny first milestone, not the full VM — was never
assembled, run, or verified against its own fixtures. And it isn't a
drop-in even for that: `bor_vm_core.pasm` hardcodes
`VM_DEFAULT_CODE_BANK=$C0`, `VM_DEFAULT_SLOT_BANK=$40`,
`VM_DEFAULT_FRAME_BANK=$41` — a genuine multi-bank layout — while
CLAUDE.md's "Toolchain" section documents Poppy's confirmed bug that
cross-bank `jsl`/`jml`/`lda #` references silently resolve to bank `$00`
instead of the real bank for any label defined under a non-zero
`.bank N`. This project has stayed bank-0-confined specifically because
of that bug (see CLAUDE.md's `src/main.pasm` section). The scaffold
inherited its bank layout from a sibling project
(`astrobleem/supermn-snes`, cited in `SOURCES.md`) that doesn't share
this constraint. Using it here means either re-deriving it for bank 0 or
adopting the numeric-`bank:offset`-literal workaround CLAUDE.md documents
for cross-bank references — a real adaptation pass, not a copy-paste.

**Two realistic paths forward, very different in cost — path 1 is now DONE
(Phase 13, §2.13, 2026-08-16; user-selected: "do the spawn-table route"):**
1. **Convert-time spawn tables (small, tractable, no VM). ✅ DONE.** This
   engine already hardcoded its entities at boot instead of a general
   entity-lookup system; the same shape of shortcut now works for spawn
   data too — the small subset of a level script actually needed (enemy
   position/wave timing) is parsed in Python at convert-time and baked
   into a small fixed table the SA-1 walks through at runtime. No
   interpreter, no bytecode, no VM. Real spawn waves now exist (see
   §2.13); a real "next level" trigger does not (still no level-transition
   system — see above). Does not generalize to levels whose logic is
   actually conditional/scripted (most are not, for a beat-em-up — enemy
   waves are usually just "spawn these N enemies when the player crosses
   X").
2. **Actually run the OpenBOR VM (large, scaffold exists, unverified).**
   Still not started. Finish what `openbor4086_sa1_bootstrap.zip` started:
   get Gate 0 to actually assemble and pass against its own fixtures, on
   this project's real Poppy fork and bank-0 constraint, then extend
   opcode-by-opcode. This is not "the next phase" of this plan — it's
   comparable in scope to everything Phases 0-12 already took, and should
   be scoped as its own plan with its own phase-gate structure if picked
   up, not folded into this file's phase list.

Path 2 is not scheduled. Per this project's "don't start speculative
phases uninvited" norm, that stays true until explicitly asked for.

## Phase 0 — Fix the MSU-streaming serialization hazard  ✅ DONE (`fd9bcdc`)

**Blocks every later phase. Do this first, and prove it under real
two-stream conditions before moving on — not just by reading the fix and
trusting it.**

**Goal:** guarantee at most one entity's `Msu1_LoadFrame` call has
DMA requests in flight (queued-but-not-yet-drained) at any time, and stop
silently dropping overflowed DMA enqueues.

**Recommended mechanism** (matches this project's own established idiom —
`CharSelect_Loaded` already does exactly this shape of thing: "a flag that
gates a routine while related async work is outstanding"):

1. Add a new WRAM flag, e.g. `Msu1_StreamBusy` (`.db`). Pick a free address
   near the existing `AnimHeaderStaging` block (`$7E2320`-`$7E232F`) —
   **grep `main.pasm` and every `core/*.pasm` file for the address you pick
   before using it**, don't assume it's free just because it looks
   unclaimed.
2. In `Msu1_LoadFrame` (`main.pasm:2806`), after the 6 row-DMA enqueues
   succeed, set `Msu1_StreamBusy = 1`.
3. In `Core_Nmi_Play` (`core/nmi.pasm`), clear `Msu1_StreamBusy = 0` — but
   only *after* `Core_Dma_ProcessQueue` has actually run for that vblank
   (read `core/nmi.pasm` to find the right point; the ordering matters —
   clearing it before the drain defeats the whole fix).
4. Wherever an entity's per-tick countdown lives (this logic currently
   lives in `Anim_Play_Idle`/`Walk`/`Attack`, `main.pasm` around lines
   2659-2760 — read the actual current bodies, don't assume the exact
   shape hasn't moved by the time you get here), **check `Msu1_StreamBusy`
   *before* decrementing `Anim_TickCounter`, not after it reaches 0.** If
   `Msu1_StreamBusy` is set, skip this entity's entire per-tick countdown
   for the frame — leave `Anim_TickCounter` untouched, don't call
   `Msu1_LoadFrame`. If it's clear, decrement/process normally.
   **This ordering matters and is not interchangeable with the more
   obvious-looking alternative:** if you instead let the counter reach 0
   and only gate the `Msu1_LoadFrame` call itself (leaving the counter
   pinned at 0 when blocked), every blocked entity re-attempts and
   re-loses the race *every single frame* — with several entities, the
   lowest-slot one wins every time and higher-slot entities can starve
   indefinitely. Pausing the countdown itself (this step, done correctly)
   means a blocked entity's countdown resumes from where it left off next
   frame, so no entity is ever excluded from ever winning the race.
5. **Also add the missing carry check** in `Msu1_LoadFrame_EnqueueRow`
   (`main.pasm:2942-2954`): if `Core_Dma_Enqueue` returns carry clear, stop
   enqueueing the remaining rows for this call and leave state such that
   the same frame is retried next tick (same "don't advance" shape as step
   4). This is defense-in-depth on top of step 4, not a substitute for
   it — step 4 is what actually prevents the cross-entity corruption; this
   catches any other future source of queue pressure (e.g., if OAM upload
   ever needs more slots) from silently corrupting a row instead of
   audibly failing to update it.

**Why a skip-and-retry-next-tick is an acceptable fix, not a hack:**
animation delays in this project are all small (8-10 frames); an entity
that loses a same-tick race waits at most one extra frame before its
frame-advance succeeds — imperceptible, and far simpler than a real
round-robin scheduler for a 2-4 entity roster.

**Verification gate (do not skip):** this bug cannot be observed with only
one entity — you must force the two-entity collision to prove the fix.
Before Phase 1 even exists, you can still test this in isolation: pick two
distinct MSU offsets (e.g., point one "fake" stream request at Ralf's idle
base, another at JHUN's idle base) and, in a throwaway test hook, call
`Msu1_LoadFrame` twice in direct succession within the same main-loop
iteration, once for each base, with the fix in place. **Expect (or force)
the second call to observe `Msu1_StreamBusy` already set** — that's the
fix actually doing something. The correct outcome is the second base's
rows landing on a *later* frame once the flag clears, not both sets of
rows landing together on the same frame; if both land the same frame, the
gate isn't blocking anything and the test hasn't proven what it needs to.
Confirm via Mesen2 (≥32-byte reads, majority-of-3 sessions):
- Both entities' full 6-row VRAM writes land correctly on their intended
  target addresses, matching their respective source data — no
  cross-contamination.
- `Msu1_StreamBusy` is observed to gate the second call (i.e., the second
  call's rows are provably deferred to a later frame, not silently
  corrupted).
- `Nmi_FrameCounter` still advances exactly 1/frame with no stalls (a
  regression here would show up as slow framerate, not corruption —
  diagnose as a budget issue if seen).

Update `handoff.md`'s "Recommended next step" to point at Phase 1 once this
gate passes. Re-run all three `tools/rom_audit/*.py` scripts.

## Phase 1 — Give the current character a real home in `core/oop.pasm`  ✅ DONE (`fd9bcdc`)

**This is a pure refactor. The gate is "renders pixel-identically to
before," not new behavior.** Do not combine this with Phase 2's new entity
in the same change — get this verified alone first.

**Goal:** replace today's singleton global animation/position state (listed
under "WRAM layout that already exists" above) with per-instance state
living in an `core/oop.pasm` object's own direct-page window, and make
today's one character Entity #0 created through that path. Read
`src/core/oop.pasm`'s full header comment first — the handle/DP-window
mechanics (`Core_Oop_Create`, `Core_Oop_Play`, the `phd`/`tcd`/`pld`
DP-switching around each dispatched call) are exactly what make this work,
and getting the calling convention wrong (e.g., forgetting these are
DP-relative offsets, not bank-`$7E` absolute addresses) is the most likely
mistake here.

**1. Register a class.** Fill `OopRegStaging_Flags` (0 — not a singleton,
multiple instances allowed), `OopRegStaging_ZpLen` (see field layout
below), `OopRegStaging_Init`/`Play` (new routines, see below),
`OopRegStaging_Pause`/`OnCommand` (0/stub for now — no pause behavior
needed yet, and no camera consumer yet per "screen.pasm" note above), then
call `Core_Oop_RegisterClass`. Do this once, at boot, from wherever
`Core_Oop_Init` is already called (`main.pasm:3790`) — after it, not
before.

**2. Recommended per-instance DP-window field layout** (offsets from the
object's own DP base; `core/oop.pasm` reserves offsets 0-3 for its own
self-handle header — `OOP_SELF_HEADER_SIZE=4` — start your fields at 4).
This is a starting design, not gospel — adjust as you implement, but it's
sized to fit comfortably (well under 128 bytes) against the 3072-byte
`OopObjRam` pool across several instances:

```
CHAR_POS_X          = 4    ; .dw (2B) -- screen X
CHAR_POS_Y          = 6    ; .dw (2B) -- screen Y
CHAR_FACING_LEFT    = 8    ; .db
CHAR_FRAME_INDEX    = 9    ; .db
CHAR_TICK_COUNTER   = 10   ; .db
CHAR_SELECTED       = 11   ; .db  -- 0=idle/1=walk/2=attack, mirrors today's Anim_Selected enum
CHAR_ROSTER_INDEX   = 12   ; .db  -- which bor.msu slot this instance loaded
CHAR_PALETTE_SLOT   = 13   ; .db  -- 0-7, this instance's OBJ palette (see "OBJ palette budget" above)
CHAR_TILE_COLUMN    = 14   ; .db  -- 0-3, this instance's OBJ tile-block-0 column slice
CHAR_INPUT_DRIVEN   = 15   ; .db  -- nonzero = read dpad; 0 = no movement source yet (Phase 3 adds AI here)
CHAR_IDLE_FCOUNT    = 16   ; .db
CHAR_WALK_FCOUNT    = 17   ; .db
CHAR_ATTACK_FCOUNT  = 18   ; .db
CHAR_IDLE_DELAY     = 19   ; .db
CHAR_WALK_DELAY     = 20   ; .db
CHAR_ATTACK_DELAY   = 21   ; .db
CHAR_IDLE_BASE_LO   = 22   ; .dw
CHAR_IDLE_BASE_HI   = 24   ; .db
CHAR_WALK_BASE_LO   = 25   ; .dw
CHAR_WALK_BASE_HI   = 27   ; .db
CHAR_ATTACK_BASE_LO = 28   ; .dw
CHAR_ATTACK_BASE_HI = 30   ; .db
CHAR_ZP_LEN         = 31   ; total -- pass as OopRegStaging_ZpLen
```

**3. `CharacterEntity_Init(a=roster_index)`:** adapt today's
`Anim_LoadCharacter` (`main.pasm`, search for that label) — same
seek/read/parse logic against `bor.msu`'s directory — but write into the
calling object's own DP-relative fields above instead of the fixed
`CharSelect_*`/`Anim_*` cells, and additionally: store the caller-assigned
`CHAR_PALETTE_SLOT`/`CHAR_TILE_COLUMN` (passed in some way you design —
e.g., a second init parameter, or derived from creation order), and load
this instance's palette into CGRAM at `$100 + CHAR_PALETTE_SLOT*32` (via
`Core_Dma_Enqueue`/`DMA_TYPE_CGRAM`, matching the existing pattern) instead
of always `$100`.

**4. `CharacterEntity_Play()`:** fuse today's `Character_PlayFrame`
(`main.pasm:3214-3322`) and `Anim_Play`/`Msu1_LoadFrame` logic into one
per-instance routine, reading/writing this object's DP-relative fields.
Concretely:
   - Movement: only read dpad input if `CHAR_INPUT_DRIVEN` is set (Entity
     #0/the player, for now — everything else is stationary until Phase 3).
   - Frame streaming: gate on `Msu1_StreamBusy` per Phase 0's fix; add this
     instance's `CHAR_TILE_COLUMN*128` byte offset to every row's DMA
     target address (see "OBJ tile-space budget" above).
   - OAM: set this instance's palette bits from `CHAR_PALETTE_SLOT` in the
     attribute byte (replacing the hardcoded `$30`/`$70` literals). Apply
     the "only the first entity dispatched this frame resets
     `Oam_CurrentSlot`" rule from "Ground truth" above — **do not** use
     `OopObjIndex` (the object system's own slot byte-offset cursor) as an
     "am I first" check: it's a slot *offset*, not dispatch order, and it
     breaks the moment Entity #0 is ever killed — a surviving entity at a
     higher slot would become first-dispatched while `OopObjIndex` no
     longer reads 0 for it, so the reset would never happen and every
     sprite would pile onto whatever slot the cursor happened to hold
     instead. Use an explicit per-frame flag instead: add a WRAM cell
     (e.g. `Oam_CursorResetDone`), clear it once in `scpu_main_loop`
     immediately before the `jsr Core_Oop_Play` call, and have
     `CharacterEntity_Play` check-and-set it — whichever instance sees it
     clear first this frame is the one that resets `Oam_CurrentSlot` to 0;
     every instance after it sees the flag already set and skips the
     reset. This is correct regardless of dispatch order or slot
     compaction from kills. Get this exactly right — it's the one part of
     this phase without a "renders identically" safety net, since it
     doesn't manifest until Phase 2's second entity exists.

**5. Wire creation.** Where `scpu_boot` currently calls the old boot-time
character load directly, instead call `Core_Oop_Create` once (class id
from step 1, `a` = roster index 0) to create Entity #0. Retire the direct
call path once the object-based one is verified equivalent.

**Verification gate:** boot in Mesen2, confirm idle/walk/attack/facing/dpad
movement/live Select-button reselect all behave **identically** to the
pre-refactor build — same screenshots, same WRAM-observable behavior
(adjusted only for the new DP-relative addresses). This is a regression
gate, not a feature gate: if anything looks even subtly different, stop and
find out why before proceeding to Phase 2. Re-run all three
`tools/rom_audit/*.py` scripts. Update `handoff.md`.

## Phase 2 — Second, simultaneous entity  ✅ DONE (`e7d18eb`, `f2f52e0`)

**Goal:** prove two entities render simultaneously, independently, and
without the Phase 0 corruption — the actual milestone this plan exists to
reach.

1. If you haven't already, convert a second/third roster character now
   (see "Runtime character roster" above — independent, cheap, do it if
   still pending).
2. Call `Core_Oop_Create` a second time: a different roster index (e.g.,
   JHUN if Ralf is Entity #0), `CHAR_PALETTE_SLOT=1`, `CHAR_TILE_COLUMN=1`,
   `CHAR_INPUT_DRIVEN=0` (**not** dpad-controlled yet — keep this entity
   fully static in position for this phase, idle-animation-only). This is
   the smallest possible slice that still exercises everything new at
   once: a second `oop.pasm` instance, a second OBJ palette, a second OBJ
   tile-column, a second OAM slot, and — critically — real concurrent MSU
   streaming under the Phase 0 fix, since idle animation still advances
   frames periodically on its own.
3. Place Entity #1 at a fixed position clearly separated on screen from
   Entity #0 (e.g., offset in X) so overlap doesn't confuse the visual
   check.

**Verification gate:**
   - Both characters visible simultaneously in Mesen2, correct and
     distinct palettes, non-overlapping, no visual corruption on either.
   - Run long enough that both entities' idle cycles re-align on the same
     frame at least once (their delays are similar small numbers, so this
     will happen naturally within a few seconds) — this is what actually
     exercises the Phase 0 collision path for real; a short run that never
     hits it proves nothing new.
   - Entity #0 (player) still fully controllable exactly as in Phase 1.
   - Direct WRAM/VRAM byte comparison (not just "looks right") that each
     entity's rendered tile data matches its own source character's known
     baked frame bytes (`out/<name>_idle/frameNN.bin`-derived expectation),
     not the other entity's — this is the specific check that would catch
     a regression of the Phase 0 bug.
   - Majority-of-3 Mesen2 sessions, ≥32-byte reads, per this project's
     established harness-reliability practice.
   - All three `tools/rom_audit/*.py` scripts clean.

Update `handoff.md`. This is a strong, demo-able milestone — consider it a
natural stopping point to check in even if continuing the same session.

## Phase 3 — Minimal AI (the original spec's actual ask)  ✅ DONE (`78f2acb`)

Lighter detail from here on — re-derive specifics against the code as it
exists once you reach this point, don't assume Phase 1/2's exact shape is
unchanged.

**Target behavior** (from `SNES-BOR-Engine-Prompt.md` §6, this project's
own original scope statement — implement exactly this, not more): Entity
#1 (or a new Entity #2, your call) walks toward the player's current
position on both axes when farther than some small threshold, and
triggers its attack animation when within roughly 30 pixels. No damage
yet — Phase 4 is what makes attacks actually do anything.

Concretely, this likely means: give `CharacterEntity_Play` a second
movement-source mode (alongside `CHAR_INPUT_DRIVEN`) — e.g.
`CHAR_INPUT_DRIVEN=2` meaning "seek toward Entity #0's position" — reading
Entity #0's `CHAR_POS_X`/`CHAR_POS_Y` (you'll need a way to reach another
object's DP window; `core/oop.pasm`'s handle mechanism or a simpler
"player is always slot 0" shortcut both work — the latter is fine for this
scope, don't over-engineer a general entity-lookup system for a
single-player game).

**Verification gate:** isolated first (this AI entity alone, no other
enemies), confirm it visibly closes distance on the player and triggers
attack at the right range, in Mesen2. Then re-confirm Phase 2's
simultaneous-rendering gate still holds with movement added (a moving
entity re-computes its OAM position every frame in addition to streaming
animation frames — confirm this didn't reintroduce any DMA-queue pressure
issue).

---

# PART TWO — Long-horizon plan (written 2026-08-09, after Phase 4 shipped)

Everything above this line is history: Phases 0–4 are **done, committed,
and verified**. Everything below is work that has **not** been started.

Part Two is written to be followed **mechanically**. Where Part One says
things like "your call" or "re-derive against the code," Part Two does
not. Every step below states the exact command to run, the exact output
that means success, and the exact condition that means **stop**. If a step
requires you to make a judgment call that is not written down here, that
is a bug in this document — stop and hand back rather than inventing an
answer.

## 2.0 — Where the project actually is

Committed and verified working:

| Phase | What it did | Commit |
|---|---|---|
| 0 | Fixed the MSU-streaming serialization hazard (`Msu1_StreamBusy`) | `fd9bcdc` |
| 1 | Moved the character into `core/oop.pasm` as `CharacterEntity` | `fd9bcdc` |
| 2 | Second simultaneous entity (static NPC) | `e7d18eb`, `f2f52e0` |
| 3 | Minimal AI — Entity #1 seeks the player and attacks in range | `78f2acb` |
| 4 | AABB collision + hit reaction (`CHAR_HIT_STUN`) | `a32d88f` |
| 5 | Scaled to 4 simultaneous entities (1 player + 3 AI) | `4ee28ff` |
| 6 | BG1 static level backdrop + BG3 HP-bar HUD | see §2.4 |
| 7 | TAD audio unblocked — song reaches `PLAYING`, audibly non-silent | see §2.5 |
| 8 | Horizontal scrolling: 16-bit world X, real camera, whole-level BG1 (cheap version — no streaming tile cache) | `5226b59` |

So: **four** characters are on screen at once — one player-controlled,
three AI-controlled that seek the player and attack in range — over a
converted, camera-scrolled Beats of Rage level backdrop with a live BG3
HP-bar HUD and TAD music playing. That is the current end state. The two
things furthest from being real gameplay: no damage system beyond the
`CHAR_HP` value itself, and no SFX wired to attacks/hits (§2.6).

**The other docs were brought in sync when Part Two was written** (same
session), so you can trust them: `README.md`'s "Current Status" is
accurate as of Phase 8, `CLAUDE.md` describes the entity system and the
Poppy checklist, `build.md` carries the OBJ tile-sheet layout, and
`handoff.md`'s older sections are now explicitly banner-marked where they
are known wrong. **Keep them in sync as you go** — each phase gate below
ends with a documentation step for exactly this reason.

## 2.1 — Rules you must follow in every phase below

These are not advice. Every one of them corresponds to a bug that has
already cost this project real debugging time. They are listed here in
full so you never have to go read another file to know them.

### The Poppy assembler checklist

Poppy emits **wrong bytes with no error message**. The build succeeding
proves nothing. Obey all six of these mechanically, every time, even when
they look redundant:

1. **Put `sep #$20` + `.a8` (or `rep #$31` + `.a16` + `.i16`) at the entry
   of every new routine, and at every label that can be reached by a
   branch which jumps over an earlier `rep`/`sep`.** Poppy tracks
   accumulator width by reading the file top-to-bottom and does not
   understand control flow, so it mis-sizes `lda #`/`cmp #` after any
   branch that skips a width change. When the CPU is already in that
   width, the instruction is a runtime no-op — it costs nothing. **This
   bug has occurred six times.** Symptom: `m.disassemble(addr)` shows a
   phantom `BRK #$xx` in the middle of your routine.
2. **Keep every conditional branch's target close — within ~15 lines of
   source.** If the target is farther, invert the condition and use `brl`.
   `bcs`/`bcc`/`beq`/`bne` past ±127 bytes **builds with no error at all**
   and hangs the CPU at runtime. Symptom: `Nmi_FrameCounter` freezes and
   every WRAM read returns the same value forever.
3. **Put a `nop` immediately before every new label.** Poppy can resolve a
   label a byte or two earlier than the real instruction stream.
4. **Never write `.l Symbol,y`** — and never `ldx.l` / `ldy.l` / `stz.l`.
   Poppy accepts them silently and emits garbage. Use `.l` without an
   index, or a bare symbol.
5. **Never reference a constant defined later in the file.** Poppy's
   constant evaluator is single-pass. Symptom: `error: Cannot evaluate
   operand for instruction`. This is the one Poppy bug that *does* error.
6. **After adding code between two fixed `.org` points, confirm nothing
   overran.** `.org` regions silently truncate into each other. The
   automated check in §2.2 does this for you.

### The stop rule

> **If a verification gate fails twice with the same symptom, STOP.**
> Write down exactly what you observed — the command you ran, its full
> output, the memory addresses and values you read — into `handoff.md`,
> and hand back. **Do not improvise a fix.**

The reason is specific to this project: nearly every expensive bug in its
history was a *toolchain trap that looked like a logic bug*. Time spent
"fixing the logic" made things worse. A human or a more capable worker
needs to see the raw symptom, undistorted by your repair attempts.

Corollary: **never write off a failure as "flaky" or "harness noise."**
Multiple past "nondeterministic" symptoms in this codebase turned out to
be 100%-reproducible logic bugs.

### What static tools can and cannot tell you

`tools/rom_audit/*` checks that decoded bytes land on real instruction and
label boundaries. **It does not check that your code does the right
thing.** During Phase 4 it returned byte-identical clean results both
before and after a change that left the ROM completely broken. A clean
audit is necessary, never sufficient. Only Mesen2 behavioral testing can
tell you the code works.

## 2.2 — Build the two tools Phase 5 depends on (do this first)

Both phases below assume these exist. They do not exist yet. Build them
before starting Phase 5. Each is small.

### Tool A — `tools/rom_audit/audit_all.py`

**Problem it solves:** `audit_jumps.py` and `audit_ownership.py` are
normally seeded with the four boot entry points (`FC00 FF20 FF30 8000`).
Those seeds **never reach any code dispatched through `core/oop.pasm`** —
the audit follows `jsr`/`jmp`, and oop dispatches indirectly via
`jsr (ClassPlay,x)`. So `Anim_Play`, `Character_PlayFrame`,
`Character_HitApply`, `CharacterEntity_Init`, `CharacterEntity_Play` — i.e.
**all the code these phases touch** — are audited by nobody unless you
re-seed by hand. Their addresses move on every build, so they must be
looked up by name, not hardcoded.

Write a script that:

1. Parses `src/main.sym` into a `{name: address}` dictionary.
2. Runs `audit_jumps.py` and `audit_ownership.py` twice: once with the
   boot seeds `FC00 FF20 FF30 8000`, and once with the addresses looked up
   **by name** for: `Anim_Play`, `Character_PlayFrame`,
   `Character_HitApply`, `Character_HitApply_VsEntity1`,
   `Character_HitApply_VsPlayer`, `CharacterEntity_Init`,
   `CharacterEntity_Play`. If any name is missing from `main.sym`, print
   which one and exit nonzero.
3. Runs `verify_layout.py`.
4. Parses `src/main.pasm` for `Entity1_Base` and `CHAR_ZP_LEN` and asserts
   `Entity1_Base - $7E0a00 == CHAR_ZP_LEN`. (`Entity1_Base` is a
   hand-maintained literal — see §2.3 step 3. This assert is the only
   thing that will catch it going stale.)
5. Asserts the gap between `scpu_main_loop`'s end and `nmi_handler`'s
   address is still positive, and prints it.
6. Prints `ALL CHECKS PASS` and exits 0, or prints the failures and exits
   nonzero.

Every phase gate below is then one line: `python tools/rom_audit/audit_all.py`.

### Tool B — `tools/verify/` (committed Mesen2 test scripts)

Every phase so far wrote a throwaway test script and deleted it. Stop
doing that. Create `tools/verify/` and commit one script per phase
(`phase5.py`, `phase6.py`, …). Each script must:

- Derive the ROM path from the repo root it lives in — **never** hardcode
  `E:\gh\snes-bor\distribution\bor.sfc`. Inside a git worktree that
  literal path silently tests the *main checkout's* stale ROM. An entire
  session has already been lost to exactly this.
- Read memory in blocks of **32 bytes or more** and slice locally. Reads
  smaller than 32 bytes can silently return stale data in this harness.
- Pass **full `$7Exxxx` addresses** to `read_memory("snesMemory", …)`. A
  bare offset like `0x53B4` silently misreads rather than erroring.
- Run each assertion three times and take the majority. Print each
  assertion's name followed by `PASS` or `FAIL`, and a final
  `PHASE N: PASS` / `PHASE N: FAIL`.

Known harness limits, so you do not waste time on them: `m.trace_log()`
always returns empty here. `m.disassemble()` returns garbage unless you
`m.run_frames(60)` first. `m.set_input(frames=N)` is wall-clock-based, so
`N` is a lower bound, not an exact frame count — assert on direction and
on clamp endpoints, never on `frames × rate` equality.

## 2.3 — Phase 5: scale from 2 entities to 4  ✅ DONE (commit `4ee28ff`; the entity-0 palette bug found during this phase was later root-caused and fixed as a `TestSprite_Init` CGRAM collision — see `handoff.md`)

**Target: exactly 4 entities total — 1 player + 3 AI.** Not "3 or 4."
Four.

### The budget arithmetic, settled

Part One of this document said N=4 was the free limit and N=5 would need
OBSEL's second tile bank. **That was wrong, in a way that matters.** Here
is the real arithmetic, derived from the code:

- OBSEL is `$C2` (set in `src/core/oam.pasm`): OBJ char base = word
  `$4000`, size mode 6, whose "large" size is 32×64 = **4 tiles wide × 8
  tiles tall**.
- Sprite tile fetch indexes an 8-bit tile number as a **16 × 16** sheet:
  `tileIndex = (row << 4) | col`. That is 256 tiles = words
  `$4000`–`$4FFF`.
- The next thing in VRAM above that is the BG2 tilemap at word `$5C00`
  (`$2108`). Words `$5000`–`$5BFF` are unused. So the **entire** 256-tile
  OBJ block is free.
- Each entity consumes 4 columns × 8 rows. 16 columns ÷ 4 = **4 column
  slices**; 16 rows ÷ 8 = **2 row bands**.

**⇒ The hard ceiling is 8 entities, not 4, and no OBSEL change is
needed.** N=4 uses only row band 0 (base tile index 0, exactly the region
already proven working) and only widens the existing per-instance
`CHAR_TILE_BYTE_OFFSET`. Phase 5 therefore does **not** touch VRAM layout
at all. If a later phase wants 5–8 entities, row band 1 lives at base tile
index 128 (word `$4800`, byte offset `+$1000`), and the only new work is
extending `CHAR_TILE_BYTE_OFFSET` to `band*$1000 + col*128` and blanking
rows 6–7 of the new slices in `Character_BlankPadding`.

Two budgets are **not** binding at N=4 — do not spend time checking them:
OBJ palettes (8 available, 4 needed) and oop capacity
(`OOP_MAX_OBJECTS`=24, and `OOP_OBJ_RAM_SIZE`=$0c00 ÷ `CHAR_ZP_LEN`=35 =
87 windows).

**The one budget that *is* binding is the DMA queue.** `DMA_QUEUE_SLOTS`
is 8, one entity's `Msu1_LoadFrame` enqueues 6 row-DMAs, and
`Core_Oam_Play` consumes more. Phase 0's `Msu1_StreamBusy` serializes this
so at most one entity streams per frame. **This is correct and must not be
"fixed."** Its consequence is that with N entities, each entity's
animation advances at most every N frames — at N=4, animation runs at
~15fps per character while the game still runs at 60fps. **That is
expected and acceptable.** Do not try to make all four stream in the same
frame; that reintroduces the exact vblank-overrun bug Phase 0 fixed.

### The asset question, settled

Only two characters exist: `out/ralf` and `out/jhun`
(`ROSTER_PREFIXES` in `build_rom.py`). Four entities will therefore be
**two ralfs and two jhuns.** This needs no new art and no converter work.
**Do not build a converter in this phase.**

**Expect the two ralfs to look identical to each other, and the two jhuns
to look identical to each other. This is correct, not a bug.**
`CHAR_PALETTE_SLOT` is per-instance and each entity's `Anim_LoadCharacter`
streams that character's own palette into its own CGRAM slot
(`$100 + slot*32`) — so slots 0–3 all get properly initialized, but two
entities loading the same character write byte-identical colors. Distinct
*slots* are not distinct *colors*. The PoC spec asks for 4 enemies, not 4
distinct-looking ones, so this is acceptable. **Do not invoke the stop
rule over two identical-looking sprites**, and do not go hunting for a
palette bug — you will find nothing. (If you want them visually distinct,
that is a separate, optional task: convert a third and fourth character
per the recipe in Part One's "Ground truth" section and add them to
`ROSTER_PREFIXES`. It is not required to pass Phase 5's gate.)

### The work: unwind every hardcoded "there are exactly 2 entities"

This is the whole of Phase 5. Each item below is a real site in
`src/main.pasm` that assumes two entities. Work through them in order.

1. **Documentation.** `README.md`'s "Current Status" and "Not built"
   sections both state "2 entities" as the current end state, and
   `CLAUDE.md` says the same. Both become wrong the moment this phase
   lands. Update them at the *end* of this phase, not the start — but note
   it now so it isn't forgotten. `README.md` also carries the
   `Character_BlankPadding` defect as a "Known live defect"; delete that
   note once step 9 fixes it.
2. **`Entity1_Base = $7E0a00 + 35`** and its derived `Entity1_PosX`,
   `Entity1_PosY`, `Entity1_HitStun`. This is the item that genuinely
   cannot survive N=4 — there is no `Entity2_Base`/`Entity3_Base` and
   adding them by hand does not scale. **Replace it with a computed
   base:** a small routine that takes a slot number in a register and
   returns `OopObjRam + slot × CHAR_ZP_LEN`. Delete the `Entity1_*`
   constants once nothing references them. (The literal `35` exists
   because Poppy cannot forward-reference `CHAR_ZP_LEN` — rule 5 above.
   Tool A's assert exists to catch it drifting.)
3. **`PlayerEntity_PosX` / `PlayerEntity_PosY` / `PlayerEntity_HitStun`**
   at fixed `$7E0a00` offsets. **These may stay as they are.** Entity #0
   is created first and never killed, so "the player is always slot 0" is
   a deliberate, endorsed shortcut. Do not build a general entity-lookup
   system for a single-player game.
4. **`Character_HitApply`'s two-way dispatch** — currently
   `CHAR_INPUT_DRIVEN == 1 → VsEntity1`, `== 2 → VsPlayer`. Replace with:
   an attacking *player* (mode 1) loops over AI slots 1..3 and stuns each
   one it overlaps; an attacking *AI* (mode 2) tests only against slot 0.
   Both leaf routines (`Character_HitApply_VsEntity1`,
   `Character_HitApply_VsPlayer`) collapse into one routine parameterized
   by target base address. **Remember rule 1** — put `sep #$20` + `.a8` at
   the entry of the new routine and at every branch target inside the
   loop. This exact routine is where the width bug bit twice already.
5. **`Anim_Play__ai_seek`** reads `PlayerEntity_PosX/Y`. This is correct
   and needs no change — every AI seeks the player.
6. **`Character_PlayFrame__ai_x` / `__ai_y`** likewise read
   `PlayerEntity_PosX/Y`. Also correct, no change.
7. **`CharacterEntity_Init`** has only role-0 and role-1 branches, with
   hardcoded per-role `CHAR_PALETTE_SLOT` and `CHAR_TILE_COLUMN`. Extend
   to roles 0–3. Role 0 = player, roles 1–3 = AI (`CHAR_INPUT_DRIVEN = 2`).
   Assign `CHAR_TILE_COLUMN` = 0, 1, 2, 3 (this field is a **slice index**,
   not a raw hardware tile-column number — the field's own comment says so
   ["0-3, this instance's OBJ tile-block-0 column slice"] and
   `Character_PlayFrame` multiplies it by 4 to get the real base tile.
   `CHAR_TILE_COLUMN = 0, 4, 8, 12` — what an earlier draft of this
   document said — is wrong and would double-apply the ×4) and
   `CHAR_PALETTE_SLOT` = 0, 1, 2, 3. Give roles 1–3 distinct starting X/Y
   so they do not spawn on top of each other, and pick them so no two
   entities' 32×64 boxes overlap **before any of them start moving** — the
   gate below checks distinct positions at spawn, not after they've had
   time to converge on the player.
8. **`msu1_done`** creates exactly two entities via two `Core_Oop_Create`
   calls. Make it four.
9. **`Character_BlankPadding` — THIS IS AN EXISTING BUG, FIX IT.** The art
   is 32×48 (6 tile rows) inside a 32×64 (8 tile row) sprite, so rows 6–7
   must be blanked or they display whatever was last in VRAM. The routine
   currently blanks **column 0 only** — it writes two hardcoded literals,
   `lda #$4600` (tileRow 6, col 0) and `lda #$4700` (tileRow 7, col 0).
   **Entity #1 at tile column 4 already has garbage in the bottom 16
   pixels of its sprite right now, and nobody had noticed.** This is
   confirmed, not inferred — 3/3 fresh Mesen2 sessions reading
   `snesVideoRam` after 180 frames gave Entity #0's padding rows
   (`$8C00`, `$8E00`) as 0/128 nonzero, and Entity #1's (`$8C80`,
   `$8E80`) as 124–128/128 nonzero with different bytes each run.
   Phase 5 triples the problem.
   Rewrite it as a loop over all four tile columns. The addresses are:
   row 6 → word `$4600 + tc*16`, row 7 → word `$4700 + tc*16`, for
   `tc` = 0, 4, 8, 12. (Same `tc*32`-bytes stride as
   `CHAR_TILE_BYTE_OFFSET`.) It runs once at boot under forced blank, so
   it writes `$2116`/`$2118` directly and needs no DMA. **Rule 1 and rule
   3 both apply to the new loop label.**
10. **`CharSelect_Index` (`$7E53B6`) is a single global**, and the Select
    button live-cycles it. With four entities on screen, "which character
    is loaded" is no longer a global fact. **Decision, already made — do
    not re-open it: make Select apply to slot 0 (the player) only.** Roles
    1–3 keep whatever character `CharacterEntity_Init` gave them and
    ignore Select entirely. This is the smallest change and keeps the
    existing demo behavior meaningful.

### Phase 5 gate — all of these must pass, in this order

1. `python build_rom.py` — must complete with no `error:` lines.
2. `python tools/rom_audit/audit_all.py` — must print `ALL CHECKS PASS`.
   **If it reports drifted labels or a negative `scpu_main_loop` margin,
   STOP** — you have hit the `.org` truncation bug and the ROM is
   corrupt regardless of what it does on screen.
3. `python tools/verify/phase5.py` — must print `PHASE 5: PASS`. It must
   assert, at minimum: **shortly after boot** (a few tens of frames, before
   the AI has had time to converge on the player — three of the four AI
   seek the same target and will visibly stack given enough time, which is
   correct behavior, not a bug to gate on) all four entities exist in
   `OopObjRam` with distinct `CHAR_POS_X`/`CHAR_POS_Y`, and all four appear
   in hardware OAM (`snesSpriteRam`) at distinct positions; `Nmi_
   FrameCounter` is still advancing after 700 frames (proves no vblank
   overrun); each AI entity's `CHAR_FRAME_INDEX` changes over a 240-frame
   window (proves streaming is round-robining, not starving anyone); and
   the player's `CHAR_HIT_STUN` goes nonzero when an AI attacks in range.
   It must **also** assert the two things step 9 and the palette note
   above are about:
   - **Padding blanked for every column.** `Character_BlankPadding` blanks
     by tile-column-**slice** (0–3), each slice's padding sitting `slice *
     128` bytes apart. Read `snesVideoRam` at byte `$8C00 + slice*128`
     (tileRow 6) and `$8E00 + slice*128` (tileRow 7) for `slice` = 0, 1, 2,
     3 — 128 bytes at each — and assert every byte is zero. (These are the
     same addresses as `$8C00 + tc*32` for hardware tile column `tc` = 0,
     4, 8, 12, if you prefer to think in raw tile-column numbers instead
     of slices — same 4 byte ranges either way.) Non-zero means step 9 was
     missed or got the stride wrong, and the visible symptom is garbage in
     the bottom 16 pixels of a sprite.
   - **All four CGRAM palette slots written.** Read `snesCgRam` at bytes
     `$100`, `$120`, `$140`, `$160` (32 bytes each) and assert none is
     all-zero. Expect slots 0 and 2 to be **equal** to each other, and 1
     and 3 to be equal to each other — that is the two-ralfs/two-jhuns
     result described above and is a PASS, not a FAIL.
4. Append a Phase 5 section to `handoff.md` recording what you changed,
   every bug you hit, and the gate output.
5. Commit.

## 2.4 — Phase 6: BG1 static backdrop + BG3 HUD  ✅ DONE

**The gate below was answered by designing the converter with the user,
not by guessing.** The three questions this section refused to guess at
were settled as: source format = composite a real BOR level from its
`background`/`panel`/`frontpanel`/`order` declarations at scroll 0; dedup
= exact + H/V flip (the tilemap has flip bits for free); palette = k-means
tile-aware sub-palette assignment via `tiledpalettequant.py`, adapted from
the sibling SNES-SuperMonkeyIsland project rather than written fresh.

Shipped: `tools/bg_converter/` (`level_parse` → `composite_scene` →
`convert_bg`, plus `make_hud_tiles`), `bor.msu` format v2 with a BG
section, `Bg_LoadScene`, `CHAR_HP`, and `Hud_Play`. Gate script
`tools/verify/phase6.py` — 25 assertions, all PASS. See `handoff.md`'s
Phase 6 section for the full account.

**Three things this section got wrong, corrected by building it:**

1. **"A multi-session project in its own right."** It was not. The BOR
   level format is a flat keyword list and the backdrop is static, so
   only one screen at scroll 0 ever needs compositing — no parallax, no
   z-order, no scroll rates. Most of the hard part (flip-aware dedup,
   tile-aware palette k-means, 4bpp packing) already existed in a sibling
   repo and was vendored.
2. **"BG1 tilemap at `$0400`."** BG1 tiles now occupy `$0000`–`$1FFF`, so
   the tilemap moved to word `$6000` and BG3's to `$6400`. Words
   `$6000`–`$7FFF` were free and undocumented in `build.md`'s VRAM table.
3. **BG3's palettes collide with BG1's.** A 2bpp BG3 tile with palette
   field p reads CGRAM `p*4..p*4+3`, overlapping BG1's `p*16..p*16+15`.
   The backdrop therefore quantizes to **7** sub-palettes shifted to slots
   1–7, leaving CGRAM sub-palette 0 to the HUD. Not knowing this would
   have produced a HUD whose colors were silently whatever the backdrop
   put in CGRAM 0–3.

**The DMA warning below was right and was honored:** `Hud_Play` is
dirty-gated (it enqueues nothing on a frame where no `CHAR_HP` changed)
and sends all four bars as one 256-byte DMA rather than four, since the
queue has 8 slots and one entity's `Msu1_LoadFrame` already takes 6.

**Tile budget, for whoever extends this:** BG1 is capped at 512 tiles
because tile N sits at word N*16, so tile 512 lands on word `$2000` where
`scpu_boot` writes BG2's blank tile. Dropping that single write raises the
ceiling to 1024 — which fits every stock BOR level, and is both the 10-bit
tilemap index limit and exactly where OBJ tiles start at `$4000`. BG2 is
not on the main screen, so nothing it points at is visible. Deliberately
not done: the shipped scene fits in 429 tiles. Note that
`Scpu_CcdmaPump` is defined but **never called**, so nothing rewrites
`$2000+` per frame.

## 2.5 — Phase 7: audio polish  ✅ step-1 gate now PASSES

**Gate re-evaluated 2026-08-09 (later the same day), after the user
explicitly authorized debugging the driver: a song DOES play.**
`tools/verify/phase7.py` reports `PHASE 7: PASS` — `TadPrivate_state`
reaches `PLAYING` (`$82`) about 17 frames after reset, the S-DSP leaves
reset (`FLG` = `$00`) at main volume 127/127, and recorded output peaks at
23082 on all three runs. Phases 5 and 6 still pass and `audit_all.py` is
still `ALL CHECKS PASS`.

The earlier reading in this section was accurate but incomplete: the
transfer really did stall, and the cause was **not** the TAD driver's
logic. It was four silent Poppy miscompiles plus one real porting bug:

- Poppy sizes `jsl <label>` 3 bytes during address estimation and emits 4,
  so every label after a `jsl` drifts one byte early, cumulatively. The TAD
  region has three `jsl`s and its 27 broken labels drifted 1 → 2 → 3 in
  exactly that order. Fatal cases: `LoadAudioData`'s success path fell
  through a stray `TXA`; `Tad_LoadSong`'s state guard became dead code, so
  the common audio data was never transferred at all; and
  `TadPrivate_Process_Loading` resolved onto the previous routine's `rtl`,
  making `Tad_FinishLoadingData` spin forever (which also hung the main
  loop). See `tools/rom_audit/check_label_drift.py`.
- Poppy **silently deletes** a branch targeting a dot-local label
  (`bcc .valid`) — no branch, no label, no diagnostic.
- `Tad_DataTable`'s offsets are measured from the ca65 audio *segment*
  base, and upstream `LoadAudioData`'s LoROM math assumes that segment
  starts at `$8000` of a bank. This project's blob is `.incbin`'d mid-bank
  at `$B02B`, so every address landed `$302B` low, in zero padding — TAD
  reported `PLAYING` at full volume while loading pure zeros.

**Remaining work in this phase (small, unstarted, and now unblocked):**
trigger an SFX from the attack animation's start (the same place
`CHAR_SELECTED` transitions to 2). **This needs content before it needs
code** — `soundwork/tad/build/audio-enums.inc` exports only one song
(`s02_coin`) and one placeholder effect (`sfx_stub = 0`), so a punch sound
must be authored in the Terrific Audio Driver project first. Wiring
`sfx_stub` would prove the `Tad_QueueSoundEffect` path but would not
produce a punch.

**One harness warning that still applies:** the Mesen2 audio check has an
observed ~40% false-silent rate on unchanged ROMs, so repeat any audio
assertion at least three times and take the majority. A sharper
discriminator found while fixing this: real playback yields a *different*
`audio_fingerprint` sha256 on every run, while true silence is
byte-identical every time.

**One harness warning specific to this phase:** the Mesen2 audio check in
this harness has an observed ~40% false-silent rate on completely
unchanged ROMs. **A single "silent" reading is not evidence of a
regression.** Repeat any audio assertion at least three times and take the
majority, exactly as §2.2 Tool B requires.

## 2.6 — Known gaps that are deliberately NOT scheduled

These appear in `README.md`'s "Not built" list and belong to no phase
above. They are listed here so nobody assumes they were forgotten. None of
them blocks Phases 5–8.

- **OAM hi-table X-high bit — RESOLVED as far as the engine code goes, but
  still never exercised by real gameplay.** Phase 8 widened world X to 16
  bits and derives the X-high bit fresh from (world X − camera scroll)
  every frame; `phase8.py` confirms the derivation is correct via a forced
  WRAM write (`CHAR_POS_X = 400` on an idle entity), since no entity's
  screen-relative X naturally exceeds 255 in this level with this AI model
  (every AI entity seeks the player, the camera follows the player, so
  they track together). A sprite that wraps to the left edge instead of
  continuing right past X=255 would still be this bug if it ever
  resurfaces — just not reachable to trigger that way today.
- **Roster selection is not persisted across reset.** Cosmetic.
- **The raw BOR `.pak` format has never been ingested directly** — art
  arrives pre-converted in `out/`. Relevant only if new characters are
  needed; Phase 5 explicitly avoids needing any.
- **No player health, no damage numbers, no game-over.** Deliberately out
  of scope per the PoC spec, which calls for hit *reaction* without a
  damage system. Phase 4 satisfies the spec as written.

## 2.7 — Phase 8: horizontal scrolling  ✅ DONE, cheap version (commit `5226b59`, 2026-08-10)

**Shipped the "cheap version" called out below** (§ "The cheap version, if
the full phase is too much"): the boss level's real content is 42 unique
tiles, well under the 512-tile budget even without reclaiming BG2, so it
loads as one static 64×32 whole-level `Bg_LoadScene` at boot — real camera,
16-bit world X, 64-wide tilemap, no BG2 reclaim, **no streaming tile
cache**. The general streaming converter (column recycling, per-frame tile
producer, Step 1's MSU-seek-vs-animation-stream interleave hazard) is
**still unbuilt** — a level whose live content exceeds ~500 unique tiles
would need it. `tools/verify/phase8.py` gates exactly the cheap version and
says so in its own docstring; its OAM X-high-bit check had to use a forced
WRAM write (`CHAR_POS_X = 400`) rather than real gameplay, because with
this AI model (every entity seeks the player, camera follows the player)
no entity's screen-relative X naturally exceeds 255 within this level's
`WORLD_MAX_X=296`.

A genuine, previously-latent WRAM collision in `core/oop.pasm` was found and
fixed during this phase: `OopCall_ResultX`/`OopCall_ResultY`, declared as
the last two fields of the `OopObjRam` bookkeeping enum, resolved to the
same addresses as `OopFlags[0]`/`[1]` — inert until this phase's camera
query became the first real writer. See the fix's comment block in
`oop.pasm` for the full mechanism.

Part One's "Explicitly out of scope" list says *"Don't add camera/scroll
logic as part of this plan."* That was correct for Part One and is now
superseded, by request. This section supersedes it; that bullet is
annotated in place rather than deleted.

**Half of this is already built and unused.** `src/core/screen.pasm` is
576 lines of real camera engine — focus/blur, easing, clamping, playfield
borders, `Core_Screen_ConvertAbsoluteToScreen` — with **zero consumers**.
It is already called every frame (`Core_Screen_Init` at boot,
`Core_Screen_Play` in the main loop); it just has nothing to follow,
because it asks a focused object for `SCREEN_CMD_GET_CAMERA_DATA` and no
class implements that.

### Decisions settled by measurement — do not re-derive

Run `python tools/bg_converter/measure_level_tiles.py` to reproduce any of
this. It is committed for exactly that reason.

| | boss (`6BEASY`) | warehouse (`4BEASY`) |
|---|---|---|
| Level width | 420px (**1.3 screens**) | 6876px (**21.5 screens**) |
| Worst single screen | 447 tiles | **843 tiles** |
| Whole level | 588 tiles | **9,789 tiles** |

The tool walks only scroll positions the camera can reach
(`[0, width - viewport]`) and keeps every sample on one global 8px tile
grid. Both matter: an earlier version that walked to the full width
reported **993** for boss — nearly double — because screens composited
past a short level's end are mostly tiled background.

1. **Streaming is mandatory for wide levels, and the intuition that says
   otherwise is wrong.** A BOR level is `order abcdefabcdef...` — 6 unique
   panels repeated — so it *looks* like tiles should nearly all be reused.
   They are not: every fresh screen adds ~800 new unique tiles and **the
   cumulative curve never flattens**. Panels are 191px wide (not a
   multiple of 8) and `convert_bg.py` resamples 320→256 (0.8 scale), so
   every repeat lands on a different tile phase and reuse is destroyed.
2. **The working set is one screen, not one level** — 843 tiles worst
   case. That **does not fit** the current 512-tile BG1 budget, and does
   fit 1024. So **reclaiming the dead BG2 region (`$2000-$3FFF`) is a
   prerequisite**, and it leaves 181 tiles of headroom — a **floor** of
   ~6 columns of prefetch runway (28 tiles/column, assuming every tile in
   an incoming column is a cache miss). Real columns share tiles with
   resident neighbours, so the effective runway is larger; treat 6 as the
   pessimistic bound, not the expected value. This is still the tightest
   number in the phase.
3. **These counts are ~4% high, not a different order of magnitude.** The
   tool stops before palette quantization (which can only reduce the
   count). Calibration: it reports 447 for boss screen 0 where
   `out/bg_boss/manifest.json` records 429 post-quantization.
4. **There are two ring buffers and only one is SMI's.** *Tilemap column
   recycling* is unconditional for any scroll past ~512px (a 64×32 map
   covers only that) and is cheap — 28 words/column from WRAM. A *VRAM
   tile cache* is needed only because 843 > 512.
5. **MSU-1 has real headroom — an earlier assumption here was wrong.** It
   is not true that 4 entities saturate `Msu1_StreamBusy` every frame.
   Packed animation delays are **7–20 ticks per frame** (walk 8–9, idle
   10–20), so four walking entities occupy roughly *half* of frames. A
   column is 28 × 32B = 896B, needed every 8 frames at 1px/frame.
6. **`CHAR_POS_X` is already `.dw`** (offset 4) and
   `Core_Screen_ConvertAbsoluteToScreen` already takes 16-bit absolute
   coords (`rep #$31`, `cpx`/`cpy`). So widening to world X needs **no
   `CHAR_ZP_LEN` change and no `Entity*_Base` literal change** — only the
   ~24 access sites that currently read/write it 8-bit under `sep #$20`
   (36 textual references; `Entity1_PosX`'s own comment already says "low
   byte valid").

### Step 1 — where do tiles come from — RESOLVED (2026-08-10): MSU-1

**Resolved by structural analysis, not measurement.** Unlike the tile-count
numbers above (measured, reproducible via the committed tool), this is
reasoned from three invariants already on record and grep-confirmed, not
timed on hardware/Mesen2. Re-verify empirically once the streamer exists,
per the gate below — don't treat this as equally settled.

The worry was that a column-stage MSU-1 seek could interleave with an
in-flight animation stream and corrupt it, the way two concurrent
`Msu1_LoadFrame` calls were *confirmed* to collide in Phase 0. It cannot,
for a reason specific to *why* that collision happened:

1. **NMI never touches `$2000-$2007`** (grep-confirmed empty across
   `core/nmi.pasm`/`core/dma.pasm`) — the only writer of MSU-1 track-select
   ($2004-$2007) is one boot-time call, unrelated to the data port. So the
   data port is touched exclusively by synchronous main-loop code; there is
   no ISR that can reseek it mid-sequence.
2. **`Msu1_LoadFrame`'s entire port interaction — seek, busy-poll, all 768
   bytes of `lda $2001`/`sta` — completes synchronously inside one `sei`
   section, before it ever touches the DMA queue.** By the time it returns,
   the port is idle. `Msu1_StreamBusy=1` protects the shared
   `AnimFrameStaging` WRAM buffer and the queued-but-undrained VRAM DMA
   rows that read from it — **not port state**. Phase 0's collision was
   two callers racing to reuse that WRAM buffer, not a port race.
3. Therefore a column streamer that seeks + reads synchronously into **its
   own staging buffer** (never `AnimFrameStaging`) cannot corrupt or be
   corrupted by an animation stream — 65816 has one execution context, and
   neither routine's critical section can be entered while the other's is
   running.

**This does not mean "stream a column any frame you like."** A real
constraint survives, and it's the DMA queue, not the port:
`Msu1_LoadFrame` holds 6 of 8 slots until vblank drains them, leaving only
2 free. A cache-miss tile in a ring buffer can land in any free slot, so
**N scattered misses in one column need N separate VRAM DMA enqueues** —
naively, up to 28 for a full column, which blows the 2-slot budget and
hits `Msu1_LoadFrame_EnqueueRow`'s designed-to-fault queue-full path. The
streamer must do one of:

   - **allocate cache slots in contiguous runs** (not first-free) so a
     column's misses collapse into few DMA regions, or
   - **spread one column's staging across several frames** (a few tiles'
     worth of enqueues each), or
   - **gate column staging on `Msu1_StreamBusy == 0`** (~50% of frames per
     the duty-cycle finding above) and budget up to all 8 slots on those.

Pick the DMA-enqueue policy explicitly when the streamer is designed; it
is the actual open sub-decision Step 1 was gesturing at, not the port.

MSU-1 also keeps levels data-only — no ROM rebuild to add one — which was
the reason to prefer it if it worked. It does.

**Fallback, kept on record in case the empirical gate below contradicts
this reasoning:** put the tileset in ROM instead. ~4MB is free and the
whole warehouse tileset is ~316KB. `build_rom.py` already builds
`rom = bytearray(0x400000)` and writes it whole, so a blob at a fixed
offset is supported *by construction* — Poppy never sees the data, so
every `.bank N` and `.org`-truncation bug is bypassed. Costs a rebuild per
new level; that's the only reason MSU-1 was preferred.

### The work

- **Reclaim dead BG2 tile space (`$2000-$3FFF`) for a 1024-tile BG1
  budget** ✅ DONE (2026-08-10). Removed `scpu_boot`'s one-shot BG2
  blank-tile write (`scpu_bg2_blank`, 16 zero words at word `$2000`) — the
  only thing that ever touched that range, since `Scpu_CcdmaPump` (the
  code that write was protecting against) is dead, never called from
  `scpu_main_loop`. Raised `convert_bg.py`'s `MAX_BG1_TILES` and
  `pack_msu_roster.py`'s independent `BG_MAX_TILES` (a second, easily
  missed cap) from 512 to 1024. Verified with warehouse's screen 0 (761
  tiles — between the old and new caps, so it's the case that would have
  silently corrupted under the old write): built as a throwaway BG source,
  booted in Mesen, and the BG1 tileset **byte-matched `tiles.bin` across
  the entire previously-hazardous region including tile 512's old target
  address**, not just self-consistently rendered. Reverted the build
  config back to boss (unchanged, still ships) and re-ran Phases 5/6/7 —
  all still PASS, `0 DRIFTED` at 496 labels (one fewer than before: the
  removed label). **`$5C00-$5FFF`** (BG2's tilemap, generated at boot but
  never read since BG2 is off `TM`) is NOT reclaimed by this — nothing in
  the 1024-tile budget needed it; leave it for whoever needs that
  specific range.
- **Move BG3's tilemap out of the way** ✅ DONE (2026-08-10): `$6400` →
  `$6800` (`$6800-$7FFF` was free, 6144 words), freeing `$6400-$67FF` for a
  future 64×32 BG1 map. Updated `BG3_TILEMAP_VRAM_WORD`, both literal
  `$2109` writes (boot-time direct + the `Nmi_Bg3TilemapVram` shadow —
  two sites, easy to update only one and leave them disagreeing), and
  every stale comment referencing the old address. Verified via
  `phase6.py`, which reads `BG3_TILEMAP_WORD` from source rather than
  hardcoding it, so it caught the move automatically: `BG3 tilemap
  register = word $6800: PASS`, HUD still tracks live `CHAR_HP`, no
  vblank overrun. Phases 5 and 7 unaffected, `0 DRIFTED`.
  **`$2107`/`BG1SC` is deliberately NOT yet flipped to 64×32 mode** — the
  freed range has no real content until the whole-level converter exists
  (next bullet), and flipping it now would be untestable (scroll stays 0,
  so nothing would visibly differ) as well as premature. Do that flip in
  the same increment as the converter, not before.
- **Whole-level static converter (the "cheap version" case, <=64 tiles
  wide)** ✅ DONE (2026-08-10). `composite_scene.py` gained `composite_level`
  (whole panel strip, no 320px window) and `level_width`. `convert_bg.py`
  gained `convert_level`/`--whole-level`: composites the whole level,
  resamples at the same 0.8 scale as the single-screen path, pads to a
  32- or 64-tile page boundary, and hard-errors above 64 tiles (that case
  needs the streaming converter below, not this path). `snes_tiles.py`
  gained `encode_tilemap_paged` for real SNES 64x32 addressing: two
  horizontally-adjacent 32x32 pages concatenated in VRAM (page B starts
  exactly 1024 words after page A, so page A is padded to a full 32 rows
  even though only 28 are ever visible — getting this wrong shears every
  row of page B). `pack_msu_roster.py`'s BG record already carried
  `width_tiles`/`height_tiles`; only `pack_bg_blob`'s validation was
  hardcoded to exactly 32x28 — loosened to accept 32 or 64
  (`BG_VALID_WIDTHS`), with the expected tilemap byte count now derived
  per-width instead of a fixed 1792 constant. Manifest also records
  `content_width_tiles` (the real unpadded width, 42 for boss) —
  **the eventual camera clamp must use this, not `width_tiles` (64), or
  the black padding region beyond the level's real edge becomes reachable.**
  `Bg_LoadScene` reads `bg_record.width_tiles` at load time and branches
  between the narrow (896-word) and wide (2048-word) tilemap DMA loop, and
  the boot code now derives `Nmi_Bg1TilemapVram` ($60/$61) from that same
  field instead of a hardcoded `$60`. **Found and fixed a real regression
  while wiring this up:** an early attempt set that shadow from inside
  `Bg_LoadScene` itself, which runs *before* `Core_Nmi_Init` — and
  `Core_Nmi_Init` unconditionally zeroes the entire `NmiShadow_Start..End`
  block, silently wiping it back to 0 (this broke BG1SC even for the
  unchanged narrow/`bg_boss` path, caught by `phase6.py`). Fixed by
  re-deriving the SC value from `BgRecordStaging+2` *after* `Core_Nmi_Init`,
  in the same later boot block that already sets `Nmi_Bg3TilemapVram`.
  Verified: both VRAM pages byte-match `out/bg_boss_level`'s `tilemap.bin`
  and `tiles.bin` at frame 120; Mesen's own PPU-state decode reports
  `doubleWidth: True` (not just a byte coincidence); `verify_msu_roster.py`
  round-trips both the narrow and wide directories; `BgRecordStaging+2`
  independently confirmed to still hold the right value at frame 120
  (the assumption "nothing touches that WRAM in between" was measured, not
  just argued); `phase6.py`, `check_label_drift.py` (0 DRIFTED), and
  `audit_all.py` all still pass on the unchanged shipped `out/bg_boss`
  build. `build_rom.py` still ships `out/bg_boss` (narrow) by default —
  `out/bg_boss_level` is a new, committed, but not-yet-wired-in artifact
  for the next (camera) increment to build on.
- **Streaming converter** (for a level's real content wider than 64
  tiles — the general case, e.g. warehouse at ~9800 tiles): emit whole-level
  column-major tilemap + tileset + a per-column tile-ID index (SMI's
  `snes_room_converter.py` has all three; its `encode_tilemap_column_major`
  is the piece Phase 6 deliberately skipped). Extend `bor.msu` to format
  v3, or emit a ROM blob per Step 1. Still entirely unbuilt.
- **Widen X to world coordinates** — the ~24 8-bit access sites above.
  **Sequencing finding (2026-08-10): do this together with the camera
  bullet below, not before it.** `PLAYER_MAX_X = 216`/`PLAYER_MAX_Y = 208`
  clamp every write site to well under 255, so nothing can push
  `CHAR_POS_X` past a byte until the camera exists to let a level be wider
  than the viewport. Widening the storage/arithmetic first has **no gate**
  — `PLAYER_MAX_X` still caps it, so "phase5 still passes" would be
  green regardless of whether the widening is correct, the exact failure
  shape this project has hit repeatedly. Land both in the same commit and
  gate on "an entity's world X exceeds 255 and both the OAM low byte wraps
  and the X-high bit (`OamSetSprite_Hi` bit0) sets correctly" — that is
  the real test, not a synthetic force-write against unchanged OAM code
  (`Core_Oam_SetSprite` already handles the X-high bit correctly; a
  synthetic hook would test that existing path, not the widening).
- **Implement `SCREEN_CMD_GET_CAMERA_DATA` on `CharacterEntity`** and
  `Core_Screen_Focus` entity 0. This is the payoff for screen.pasm.
- **Column streamer**, in the `$C100` region (**7,000 bytes free** — last
  symbol is `Hud_Play__clear` at `$E0A8`). Steal SMI's shape: two-pass
  column staging (pass 1 cache misses, pass 2 tilemap remap), NMI writes
  the staged column, no forced blank.
- **Steal SMI's eviction fix too, rather than rediscovering it:** on
  scroll *reversal* the ring buffer leaves stale tilemap entries. Fix is
  one viewport column re-synced per idle frame (full re-sync in ~32).
- **The OAM X-high bit becomes real here** — see §2.6's bullet, which
  predicted exactly this. A sprite wrapping to the left edge instead of
  passing X=255 is that bug.

**Scope limits, stated so nobody over-builds:** the camera is
**dpad-driven and clamped to `[0, maxScrollX]`** (SMI used the same
testing camera). Encounter-gated scrolling — "clear the enemies to
proceed" — needs a death system that does not exist and is **not** in this
phase. No parallax: `bgspeed`/`scrollspeed` stay unread.

### Phase 8 gate — all of these must pass, in this order

1. `python build_rom.py` — no `error:` lines.
2. `python tools/rom_audit/audit_all.py` — `ALL CHECKS PASS`.
3. `python tools/rom_audit/check_label_drift.py` — `0 DRIFTED`, ROM-wide.
4. `python tools/verify/phase8.py` — `PHASE 8: PASS`. Per the standing
   rule, the central assertion must be **ground truth, not
   self-consistency**: after scrolling N columns, the VRAM slot that a
   given tilemap entry points at must **byte-match the converter's tile
   for that world (x, y)**. Also: `Nmi_FrameCounter` still advancing
   through sustained scrolling (vblank-overrun guard — this phase adds a
   per-frame DMA producer, exactly the class §2.4 warns about); scroll
   clamps at both ends; and a **scroll-reversal** pass, since that is
   where SMI's eviction bug lives. **Also empirically re-verify Step 1**
   here — force a column stage and an animation stream in the same frame
   (same forced-collision technique Phase 0 used) and confirm neither
   corrupts the other; Step 1's resolution above was structural analysis,
   not a measurement, unlike everything else in this section.
5. Append a Phase 8 section to `handoff.md`.
6. Commit.

### Stop conditions

- **Working set >1024 after reclaiming BG2.** Report and pick a narrower
  level; do not silently truncate.
- **`$C100` region exhausted.** 7,000 bytes is generous but the streamer
  plus staging buffers is the largest single addition since Phase 6.
- **Step 1's interleave test is ambiguous.** Take the ROM path; it
  dissolves the question rather than betting on it.

**The cheap version, if the full phase is too much:** boss is **588 tiles
over its whole 1.3 screens** — the entire level loads at once. It still
needs the reclaimed 1024 budget (588 > 512), but nothing else: a real
scrolling demo with **zero streaming** and one static load — camera, world X, 64×32
tilemap and column recycling only. It exercises every part of this phase
except the tile cache.

---

## 2.8 — Phase 9: streaming tile cache ✅ DONE (steps 1–4, commits `315673b`,
`03a8ad7`, `d2c677b`, `1415969`, `cf5332a`, `9bed554`)

This is the "full version" of scrolling that Phase 8 explicitly deferred
(§2.7's "still unbuilt" streaming converter) — a level whose live content
exceeds the ~500-tile static-load budget. **It is built, verified against a
synthetic 13,437-tile test level, and NOT wired into the shipped ROM** —
the shipped boss level (588 tiles) still uses Phase 8's cheap static load,
because it doesn't need streaming. This phase exists so a *future* wider
level can use it; nothing about the current product depends on it working.
Keep that distinction in mind reading `README.md`'s "Current Status" — the
streaming cache being "done" does not mean the shipped ROM streams tiles.

**What was built:**
- `tools/bg_converter/` gained a streaming-format level converter (produces
  a column-major `tilemap.bin` instead of one flat screen) and a synthetic
  stress-test asset, `out/bg_warehouse_stream` (13,437 unique tiles across
  the whole level — deliberately far larger than the 1,022-slot cache can
  hold at once, to force real cache-miss/eviction behavior under test).
- `src/core/stream_cache.pasm`: a ring-buffer VRAM tile-slot allocator,
  `STREAM_CACHE_USABLE = 1022` slots, LRU-ish eviction with a
  `STREAM_CACHE_PROTECT_WINDOW = 16`-slot protection on the most-recently-
  touched slots. `Core_StreamCache_AllocateSlot`'s eviction scan covers the
  *full* 1022-slot ring every call (a prior fix — a narrower scan limit
  used to force-evict slots that didn't need it; see that constant's
  declaration comment before changing it).
- `src/main.pasm`, the `Core_StreamScroll_*` family: the runtime engine.
  `Core_StreamScroll_PickColumn` decides each call whether to extend the
  resident window left/right or run one step of a background repair sweep;
  `Core_StreamScroll_ResolveRows`/`FetchTileToBuffer` do the actual MSU
  seek + cache-slot fetch, budgeted at `STREAM_SCROLL_BUDGET_MAX = 6`
  cache-miss DMAs per call (swept 2/4/6/7/8 against the warehouse asset —
  6 is the highest value that didn't produce tilemap attribute corruption;
  see [[syncscroll_budget_throughput]] before raising it, there's a
  specific re-verification procedure, not just "try a bigger number").
  `Core_StreamScroll_ClampCamera` prevents the camera from outrunning the
  resolver in the first place (holds the visible edge at
  `StreamScroll_StagedLo`/`StagedHi` rather than the raw camera position) —
  this is the *primary* defense against visible garbage tiles under fast
  scrolling. A `Window1`-based 2-column edge mask (`core/nmi.pasm`,
  `Core_Nmi_Init`) is a secondary belt-and-suspenders backstop for the
  separate, lower-severity "stale-but-not-garbage" case below.
- Ad hoc (not committed-gate) verification: `tools/verify/
  phase9_stagecolumn_spotcheck.py` and `phase9_syncscroll_test2.py`. Both
  require temporarily pointing `build_rom.py`'s `BG_SCREENS` at
  `out/bg_warehouse_stream` and reverting it afterward — **always confirm
  `git diff -- build_rom.py` is empty before committing anything**, this
  has bitten prior sessions.

**Bugs found and fixed along the way** (full detail in
[[syncscroll_budget_throughput]] and [[poppy_fork_migration]] memories):
- `TileBuf` double-fetch corruption in the resolver (step 4).
- `CommitColumn` hang + a `WorldMaxX` that needed to become dynamic instead
  of a level-specific constant (step 4).
- A Poppy fork miscompile: `adc #(STREAM_STAGE_VIEWPORT_COLS-1+
  STREAM_SCROLL_PREFETCH)` — a two-term immediate expression — silently
  assembled to zero bytes, so `DesiredHi` was computed 35 columns short of
  intended. Dormant for a long time (unclamped camera movement eventually
  exceeded the wrong `DesiredHi` anyway, just later); the camera-clamp fix
  made that impossible and turned it into a hard permanent freeze. Fixed by
  splitting into two single-term `adc`s — **avoid multi-term immediate
  expressions in `adc`/`sbc` operands in this codebase, split them.**
- `pending_repair` non-convergence (the fix committed as `9bed554`, the
  session immediately before this doc update): the repair-sweep cursor used
  to round-robin across the *entire* retained window
  (`StreamScroll_StagedLo`..`StagedHi`, which grows to the VRAM ring's full
  64-column physical cap), which routinely exceeds the cache's real
  capacity (measured 1,568 distinct tiles over a 64-column span on the
  warehouse asset, vs. a 1,022-slot cache) — mathematically impossible to
  keep resident regardless of eviction policy, so repairing a far,
  no-longer-visible column would evict a currently-visible one, forever.
  Fixed by clamping the repair cursor to `[StreamScroll_DesiredLo,
  StreamScroll_DesiredHi]` (the ~40-column camera-relevant window, provably
  always a subset of `[StagedLo, StagedHi]` at the point it's read) instead
  — this is a *correction* of an earlier, wrong "self-corrects in 1-2s, not
  worth fixing" conclusion reached the same session; see the memory file
  for why that was wrong and how it was re-measured.

**Verified:** `phase9_syncscroll_test2.py` PASS against the warehouse
asset (its "pending repair" metric — entries whose live cache slot has been
reassigned since the tilemap word was written — reads 0 across the entire
visible viewport post-fix); full regression suite (label-drift, audit_all,
phase5/6/7) green on the **shipped boss-level ROM** after every fix in this
phase, most recently re-confirmed 2026-08-15.

**UPDATE (2026-08-16): wired into the shipped ROM for real, against a real
BOR level.** `build_rom.py`'s `BG_SCREENS` now ships `out/bg_stage1a` —
BOR's actual stage 1A (`DATA\EASY\1AEASY.TXT`, converted with
`--streaming`), not the synthetic warehouse asset: 6 screens/1920px wide,
2458 unique tiles level-wide (measured via `measure_level_tiles.py`: 2215
pre-quantization, comfortably past the 512/1024-tile static-load ceiling
that gated `out/bg_boss_level`). This closes the "never rendered real
level content" gap noted below — first-try clean render (see screenshots
from this session), full traversal from world X=0 to 1880 (near the
level's width) with no visible corruption, `StreamScroll_StagedHi`
tracking the camera the whole way. **No `main.pasm`/engine code changes
were needed** — every fix this update required was in the test scripts,
not the engine:
- `phase6.py`'s whole-tileset/whole-tilemap byte-exact checks are
  structurally inapplicable to a streaming BG (VRAM only ever holds the
  cache's ~1022-slot resident subset, never the full converter tileset) —
  now skipped with a clear message when `manifest["streaming"]` is set,
  falling back to `phase9_syncscroll_test2.py`'s Tile2Slot-consistency
  check as real ground truth instead. Also fixed a wrong assumption in the
  BG1SC-width-mode check: streaming mode always uses the full 64-col
  *hardware* tilemap as its ring buffer regardless of the level's logical
  *software* `width_tiles` (192 here, not 64) — those are different
  numbers, conflating them was the bug.
- `phase5.py`'s padding-blank check needed 20 more real frames before its
  sample point — a streaming BG's boot-time viewport load does far more
  real per-tile MSU seeking during `scpu_boot` than a static whole-level
  load, so frame 30 could still be mid-boot (same artifact previously
  characterized against the synthetic warehouse asset, now reproduced for
  real; see [[syncscroll_budget_throughput]]).
- `phase9_syncscroll_test2.py` and `phase9_stagecolumn_spotcheck.py` had
  `out/bg_warehouse_stream` hardcoded — generalized to read
  `build_rom.py`'s own `BG_SCREENS`, matching `phase6.py`'s existing
  convention, so they now test whatever streaming BG actually ships
  instead of only ever the synthetic asset. Both PASS against
  `out/bg_stage1a` (stagecolumn: 896/896 viewport entries byte-exact
  against ground truth; syncscroll: 0 hard mismatches after a full
  cam_col sweep to the level's right edge, 169/616 sampled entries showing
  expected/harmless pending-repair outside the live viewport).
- **`phase8.py` now correctly, cleanly FAILs** with an explicit message
  ("is not a whole-level (--whole-level) conversion") when run against the
  shipped ROM — expected, not a regression: that gate is specifically for
  the static whole-level path, which the shipped BG no longer uses.
  `out/bg_boss_level` (and the old static path itself) remain fully intact
  and buildable for anyone who wants to re-verify Phase 8's own gate
  against that config.

**UPDATE (2026-08-16): both remaining items closed.** See
`tools/verify/phase9.py` (new, committed, routine gate — no `BG_SCREENS`
swap needed, since `out/bg_stage1a` is itself the streaming level now).

Real-play scroll-lag, measured via `m.set_input(m.BTN_RIGHT, ...)` against
the live shipped ROM: `set_input` **does** move the camera correctly —
the prior "camera never advanced" observation was a harness-usage issue,
not a real gap or a broken tool. Root cause: a short hold window (10-frame
`set_input` paired with a 10-frame `run_frames`) produces unreliable
partial presses — roughly half the sample windows showed BOTH
`PlayerEntity_PosX` and `Screen_PosX` completely frozen despite
continuously re-issued held-right input. A longer, comfortably-paired
cadence (30-frame hold / 35-frame run) gives clean, consistent movement.
This is a generalization of [[mesen_set_input_wall_clock]]'s "frames is a
lower bound" note, not a new bug.

With the reliable cadence, real held-right movement surfaced a genuine,
previously-undocumented finding: the camera itself never lags behind the
player (`Screen_PosX` tracks `PlayerEntity_PosX` with a constant ~144px
follow offset, not a growing one), but the **player's own movement
throughput periodically degrades** under sustained rightward travel — from
nominal ~78px per 35-frame window (≈2px/frame, matching `PLAYER_SPEED`)
down to brief near-zero windows, including occasional single-window full
stops, before recovering. This correlates with the streaming cache's
desired window catching up to its resident window (`StreamScroll_CameraCol`
approaching `StreamScroll_StagedHi`) and is consistent with the DMA-queue
budget being shared between column-streaming DMAs and the
one-entity-streams-per-frame animation cap (see CLAUDE.md's entity-system
constraint). Not treated as a bug to fix here — `syncscroll_budget_throughput`
already documents this budget as an actively-tuned tradeoff — but now
`phase9.py` gates that it stays *bounded and recoverable* (no stall run
longer than 2 sample windows, camera lag behind the cache's own
high-water mark stays under one screen-width) rather than being an
unmeasured unknown.

**This engine has now actually rendered in the shipped product** —
`phase9.py` runs against `distribution/bor.sfc` built from the real
`ROSTER_PREFIXES`/`BG_SCREENS` config, not a temporary synthetic-asset
swap.

### Phase 9 gate (for re-verifying, not for shipping — this isn't wired
into the shipped ROM's config)

1. Temporarily set `build_rom.py`'s `BG_SCREENS = [("out/bg_warehouse_stream",
   "out/hud")]`, `python build_rom.py`.
2. `python tools/verify/phase9_stagecolumn_spotcheck.py` — boot-time
   viewport load matches the converter's ground truth.
3. `python tools/verify/phase9_syncscroll_test2.py` — 0 hard mismatches, 0
   (or a documented, understood-small) pending-repair count in the visible
   viewport.
4. Revert `BG_SCREENS` to `[("out/bg_boss_level", "out/hud")]`,
   `python build_rom.py`, confirm `git diff -- build_rom.py` is empty.
5. Full regression suite on the reverted, shipped-config ROM: `audit_all.py`,
   `check_label_drift.py`, `phase5.py`, `phase6.py`, `phase7.py`, `phase8.py`.

## 2.9 — Other candidates (not yet started, not what Phase 10 below is)

Nothing below is committed to or scheduled — pick one, or ask the user
which they'd prefer, per this project's usual "don't start speculative
phases uninvited" norm. These predate and are independent of §2.10's
Phase 10 (which came from a different, later finding — the frontpanel
occlusion bug — and was explicitly chosen by the user over these). In
rough order of how directly they extend what Phase 9 finished vs. how
independent they are:

1. ~~Convert a real (non-synthetic) BOR level and wire it in for real.~~
   **DONE 2026-08-16** — see the "UPDATE" note under §2.8 above (stage 1A,
   `out/bg_stage1a`, shipped in `BG_SCREENS`). Real-play scroll-lag under
   sustained held-dpad input and a self-contained `phase9.py` gate are
   **also DONE 2026-08-16** — see the "Phase 9 gate" section's own UPDATE
   note above. Both follow-ups fully closed; nothing left open here.
2. ~~A damage system.~~ **DONE 2026-08-16** — see §2.11 below. AI entities
   now soft-kill at `CHAR_HP==0` (stop acting, stop taking/dealing hits,
   sprite hides); player death stays out of scope.
3. **SFX wired to gameplay.** Blocked on content, not code — see
   `README.md`'s "Not built" section: `soundwork/tad/build/audio-enums.inc`
   exports one placeholder effect (`sfx_stub = 0`); a real punch/hit sound
   needs to be authored in the Terrific Audio Driver project first, then
   triggered from `Character_HitApply`.
4. **Persist the selected roster slot across a reset**, or ~~expand the
   roster past 2 characters~~. Both are small, self-contained, and don't
   interact with anything above. The roster-expansion half is **DONE
   2026-08-16** — see §2.12 below (a real third character, JOE, converted
   from the BOR pak, added as roster slot 2). Persisting the selection
   across a reset is still open.

Whichever is picked, follow §2.1's rules (Poppy checklist, the stop rule,
what static tools can/can't prove) and this file's per-phase gate pattern:
build a script under `tools/verify/`, verify against ground truth the
engine didn't produce, update `README.md`/`handoff.md`, commit at the phase
boundary.

## 2.10 — Phase 10: frontpanel foreground layer ✅ DONE 2026-08-16 (all of
Steps 1, 2a, 2b, 2c, 3, 4 — converter tooling, cache allocator, boot-time
initial load, runtime scroll resolver, HUD coexistence, and a committed
`tools/verify/phase10_frontpanel.py` gate — verified in Mesen2 and passing
deterministically)

### The problem

BOR's `frontpanel` art (e.g. stage 1A's chain-link fence,
`data\bgs\street\f03.gif`) is documented in this project's own converter
(`tools/bg_converter/level_parse.py`: `frontpanel   ...   # overlay drawn
in front`) as meant to render **in front of** characters. This engine
currently bakes background+panels+frontpanel into one flat static BG1
image, and OBJ sprites (the characters) always render above BG1 here, so
the frontpanel ends up *behind* characters — the opposite of real BOR.
Not new to Phase 9's stage-1A swap — the boss level has a frontpanel too
(`data\bgs\boss\front.gif`) — the fence just makes it visually obvious.
See `README.md`'s "Not built" section and the `scene_scrolled.png`
screenshot for what this looks like uncorrected.

### Two cheaper approaches were considered and ruled out by measurement —
don't re-propose either without new numbers

1. **Static single load.** Deduping the frontpanel across the whole level
   like a normal background gives **846 unique tiles** (measured via a
   one-off script this session, not yet committed as a tool — see "Step 1"
   below for turning it into one) — too many for the ~512-tile VRAM gap
   available without a real relayout, and it's an inflated number anyway
   (see next point), so don't chase a bigger static budget as the fix.
2. **BG3 hardware wraparound scroll at the frontpanel's own repeat
   period.** The idea: give BG3 a small tilemap holding one repeat unit
   and drive its scroll register independently of BG1's, relying on
   hardware tile-grid wraparound for an infinite repeat, needing only the
   unit's own tile count. **This doesn't work**: the repeat unit is 183px
   native, 146.4px after this pipeline's fixed 0.8 scale — not a multiple
   of 8. A hardware tile-addressed layer can only wrap cleanly on 8px
   boundaries, so forcing this to tile via scroll wraparound reproduces
   the same tile-phase-drift problem `measure_level_tiles.py` already
   documents for backgrounds, and the achievable unique-tile count
   collapses back to the same ballpark as the whole-level number above,
   not the small one-repeat-unit number. (Sprites don't have this problem
   — OAM position is per-pixel, not tile-quantized — which is why the
   next approach considered was OBJ-based, and why the ACTUAL fix below
   is BG-based-but-non-periodic, not periodic-BG-based.)
3. **OBJ sprites tiling the fence across the screen.** One repeat unit
   really is small on its own — **89 unique non-blank tiles, 22 colors**
   (measured; this is real content, not inflated by phase drift, because
   sprite positioning is pixel-exact). But the art is nearly full-screen
   height (192px / 24 tile-rows). Built from 32×32 large OBJ blocks, one
   full repeat needs ~30 sprites; with ~2 repeats visible at once that's
   roughly 40 8×8-tile-columns touched per scanline row — over the SNES's
   real 34-tiles-per-scanline hardware limit. That's a hard-wall sprite-
   dropout risk, not a style nitpick, and not something to eyeball around.

### The approach that actually fits the numbers: generalize Phase 9's own
streaming tile cache to a second, independent layer

Phase 9 already solved exactly this class of problem for BG1 — a level
whose real content is too big to hold statically, handled by a per-camera-
window resident cache with eviction/repair, not a whole-level load. The
same shape applies to the frontpanel once you size against the *right*
window, not the whole level:

- **Measured (this session, pre-quantization estimate) worst-case unique
  frontpanel tiles in any 40-column (32 viewport + 2×4 prefetch) window:
  213**, not 846 — the same "don't size against the whole level" lesson
  §2.8's own history already teaches. 213 fits comfortably in a modest
  cache. (Step 1 below later re-measured this from the real, quantized
  converter output: **143**, even smaller — the estimate here was
  deliberately conservative/unquantized and held up fine as a sizing
  bound; use the Step 1 number as current ground truth, not this one.)
- Target layer: **BG3**, 2bpp, using its existing **per-tile priority bit**
  (bit 13 of the tilemap word) — already proven in production by the HUD,
  which uses it to sit above OBJ today. Frontpanel tiles get the same bit
  set; HUD tiles keep using it too — they coexist on the same physical
  layer, not a new one.
- **VRAM budget**: currently free space is `$5000`-`$5FFF` (4096 words,
  minus the HUD's ~12 tiles) plus the fully-unused tail `$6C00`-`$7FFF`
  (5120 words) — roughly 1140 2bpp-tile-equivalent words total if
  consolidated. A ~213-plus-headroom cache (say 300-400 slots, matching
  Phase 9's own "budget above the measured worst case, not exactly at it"
  convention — see `STREAM_CACHE_USABLE`'s own history) fits **without**
  needing the BG1 tilemap or BG3 tilemap to move, since 400 slots × 8
  words = 3200 words fits inside the existing `$5000`-`$5FFF` gap alone.
  Re-verify this arithmetic against the actual build before relying on
  it — VRAM layout has shifted before and will again.
- **CGRAM budget**: measured 22 distinct colors in the frontpanel content,
  which needs either 2 sub-palettes (8 colors, still short) or real
  tile-aware quantization down to ≤15 colors + transparent in one
  4-color... **no** — 2bpp is 4 colors/sub-palette (3 usable + transparent),
  not enough for 22 colors in one sub-palette. This needs multi-sub-palette
  tile-aware assignment (reuse `tiledpalettequant.py`'s existing k-means
  machinery, parameterized for `colors_per_palette=4` instead of BG1's 16)
  across however many of BG3's 8 sub-palette slots aren't already used by
  the HUD (HUD currently uses sub-palette 0 only — 7 free). This is new
  code, not a reuse of the HUD's fixed 2-color bar generator
  (`make_hud_tiles.py`), which was never built to handle organic pixel art.

### Step breakdown (mirrors §2.8/Phase 9's own step 1-4 structure —
each step should get its own commit and gate, not one giant change)

1. **Converter tooling — ✅ DONE (2026-08-16), verified offline, no engine
   code touched.** `tools/bg_converter/convert_frontpanel.py`, run against
   stage 1A (`out/fp_stage1a/`). Mirrors `convert_bg.py`'s
   `convert_streaming()` shape: a new frontpanel-only compositor (keeps
   the transparency mask instead of discarding it, unlike
   `composite_scene.py`'s `_composite`, which flattens background+panels+
   frontpanel together), masked-out pixels baked to BOR's own magenta
   sentinel so they quantize to color index 0 (real transparency, not a
   parallel bookkeeping array), 2bpp tile-aware quantization (reused
   `tiledpalettequant.build_palettes_tileaware` as-is — it was already
   generic on `colors_per_palette`, no new quantization code needed,
   correcting this section's earlier assumption), flip-aware dedup,
   column-major tilemap in the existing `CACHE_ENTRY_BYTES=3` format
   (unchanged — no per-tile priority bit needed there; every frontpanel
   tile needs the BG3 priority bit uniformly, so Step 2/3's engine code
   sets it once when committing to VRAM, not per-tile data here). Also
   added `snes_tiles.decode_2bpp_tile` (the missing inverse of the
   already-existing `encode_2bpp_tile`) for the preview renderer.

   **Real measured results, not estimates**: 535 unique tiles total
   (down from the naive 846 whole-level estimate — quantization collapses
   more than raw flip-aware dedup alone); **worst-case unique tiles in any
   40-col window: 143** (recomputed from the actual emitted tilemap, not
   re-run of the earlier estimate script — down from that section's
   213-tile estimate, both comfortably small either way). At 8 words/tile
   that's ~1144 words resident for a window-sized cache, trivially inside
   the free-VRAM analysis above. CGRAM: exactly 9 usable colors as
   predicted (3 free BG3 sub-palettes × 3 non-transparent colors), of
   which the quantizer actually used 7 distinct real colors (2 slots came
   back as unused duplicate-transparent entries — a minor quantizer
   inefficiency, not a bug, worth revisiting but not blocking). **Visually
   verified** (`out/fp_stage1a/preview.png`, decoded straight from the
   emitted binaries, not the source render): fence mesh, wooden posts,
   "LAP CLAP" signs, and foliage are all clearly readable even at 9 colors
   — the tight budget was a real concern going in and turned out fine in
   practice, not just in theory.
2. **Engine: a second cache instance.**
   **2a (allocator) — ✅ DONE (2026-08-16), verified in Mesen2.**
   `src/core/stream_cache_fp.pasm`, a deliberate near-duplicate of
   `stream_cache.pasm` (not a parameterized/shared version — Poppy has no
   clean way to thread a "which layer" value through indexed banked-symbol
   access without real correctness risk, and this project already prefers
   duplication over that kind of cleverness elsewhere, e.g.
   `Character_HitApply_VsEntity1/2/3`). Sized for the measured 535-tile/
   143-worst-case-window budget: 256 usable slots (2bpp, 8 words/tile —
   2048 words, comfortably inside the free `$5000`-`$5FFF` BG3 gap), tables
   in grep-confirmed-unused `$7FA000`+ (bank $7F, well clear of BG1's own
   tables) and `$7E25A0`+ (bank $7E, the gap right after
   `StreamScroll_FetchBufSel`). `Core_StreamCacheFp_Init` is called from
   `scpu_boot` right after the existing BG1 call; `Core_StreamCacheFp_Test`
   exists but is deliberately NOT called from the boot path, same
   poisoned-cache reason `stream_cache.pasm`'s own `Core_StreamCache_Test`
   isn't. Verified via a temporary boot-time call to the Test routine
   (added, run, confirmed, then removed before committing, matching this
   project's established "temporary hook" pattern — see Phase 0's history
   for the precedent): 8 synthetic tile IDs allocated 8 distinct slots with
   the exact expected stride-97 arithmetic, `Tile2Slot`/`Slot2Tile`
   back-references consistent both directions. Full regression suite
   (label-drift, audit_all, phase5/6/7, phase9_stagecolumn_spotcheck) still
   green on the real shipped stage-1A ROM after this addition.
   **2b (boot-time initial load) — ✅ DONE (2026-08-16), verified in
   Mesen2.** `Bg_LoadSceneFp_Streaming`/`StageColumnFp_FetchTilePixels`
   (main.pasm), a `Bg_LoadScene_Streaming`-equivalent initial-viewport
   loader using dedicated `StreamStageFp_*` scratch cells (NOT the shared
   `StreamStage_*` cells — those are live BG1 per-frame runtime state, not
   boot-only scratch; aliasing them was one of three real bugs found and
   fixed getting this working, see below). Called from `scpu_boot` after
   `scpu_bg3_map`'s unconditional 1024-word BG3 tilemap clear (moving the
   call site there was bug #2 — it was originally invoked from inside
   `Bg_LoadScene` and had every write silently wiped by that later clear).
   Bug #3, found only after the first two were fixed and a screenshot still
   showed the entire backdrop as solid magenta: **the tilemap word's
   character-number field is PPU-relative to `BG3_TILES_VRAM_WORD` ($5000,
   BG3's actual CHR base), not to `FP_TILES_VRAM_WORD` ($5100, where this
   cache's tiles are actually stored)** — writing the bare cache slot
   number as the character field pointed 32 tiles too early, into/before
   the HUD's own 12 tiles, so every frontpanel tile rendered whatever
   uninitialized VRAM happened to sit there. Fixed with a new
   `FP_TILE_INDEX_BASE = 32` constant (`= (FP_TILES_VRAM_WORD -
   BG3_TILES_VRAM_WORD) / 8`) added to the slot number before the
   palette/priority bits are OR'd in. A fourth, independent bug in
   `convert_frontpanel.py` (`tiledpalettequant.build_palettes_tileaware`
   never actually indexes a transparent source pixel to palette slot 0
   despite accepting a `trans_color` param — it only prepends that color
   as slot 0 in the output palette, then nearest-color-matches every real
   pixel including transparent ones against the non-zero slots) was found
   and fixed the same session (`uniq_indexed[unique_raw == trans_bgr] = 0`
   forcing raw-transparent pixels back to index 0 post-quantization);
   `out/fp_stage1a/` was regenerated with the fix (535 tiles / 143
   worst-case window unchanged — same shape, corrected pixel data).
   **Verified**: Mesen2 screenshot after all four fixes shows a clean
   scene — brick-wall BG1 backdrop, HUD bars, and the chain-link fence
   with "LAP CLAP" signage rendering correctly in front of the character
   sprites, no magenta corruption anywhere. Full regression suite
   (`check_label_drift.py`, `audit_all.py`, phase5/6/7) green on the
   rebuilt ROM; phase5.py's padding-row settle-time check was bumped from
   20 to 120 frames (a second boot-time streaming loader legitimately
   pushed the settle point later, confirmed via direct probing, not a
   regression) and phase6.py's CGRAM ground-truth comparison now merges in
   the FP palette's real bytes.
   **2c (runtime resolver/repair-sweep) — ✅ DONE (2026-08-16), verified in
   Mesen2.** `Core_StreamScrollFp_*` (main.pasm: `SeekColumn`,
   `FetchTileToBuffer`, `PickColumn`, `ResolveRows`, `CommitColumn`, `Play`)
   is a twin of BG1's own `Core_StreamScroll_*`, called from
   `scpu_main_loop` right after `Core_StreamScroll_Play` and gated the same
   way (`Msu1_StreamBusy`, no contention with `Msu1_LoadFrame`). **One real
   structural simplification, not just a smaller copy**: BG3's tilemap is a
   single 32×32 map exactly the size of one viewport, so there's no room
   for BG1's prefetch margin — the resolved window is always exactly the
   32 onscreen columns, and only `FP_CONTENT_ROW_COUNT=7` rows (21-27) are
   ever seeked/resolved/committed, never the other 21 blank ones (verified
   this session that rows 0-20 are blank across the FULL 192-column level
   width, not just the boot-time window — the earlier 213/143-tile
   estimates were about tile *content*, not row range, and this insight
   didn't change either of those numbers, just the resolver's scope).
   `STREAM_SCROLLFP_BUDGET_MAX=2` (vs. BG1's 6), deliberately conservative
   given the DMA-queue-contention stop condition below.

   Getting this working found and fixed **three real bugs, all caught by
   direct Mesen2 verification, not assumption**:
   1. **Missing window-width enforcement.** The first version let
      `StreamScrollFp_StagedLo/StagedHi` grow unbounded as the camera moved
      (a scripted 143-column scroll left `StagedLo` pinned at 0 and
      `StagedHi` at 174 — a 175-column "window" against a 32-column
      physical ring). Unlike BG1 (64-column ring vs. a ≤40-column window,
      so some slack exists), FP's ring exactly equals its window size, so
      moving one edge must explicitly pull the opposite edge in by the
      same amount every commit — not something the repair sweep alone
      naturally corrects here. Fixed in `Core_StreamScrollFp_ResolveRows`'s
      commit step.
   2. **A chained-ADC carry bug**, the one that actually produced visible
      corruption (a scripted scroll test showed a garbled fence/backdrop
      past the boot window). `STREAM_FP_TILEMAP_ROW_START*3` (63) was
      being added to the per-column seek address via a second `adc #63`
      chained onto the first `adc TilemapOffLo` with no `clc` between them,
      intending the carry to propagate through to the Hi-byte add. It
      doesn't: chaining two ADCs into the *same* 16-bit word for a 3-term
      sum makes the second ADC's carry-out reflect only its own overflow,
      not the true combined total's — confirmed via a temporary WRAM probe
      comparing the actual computed seek address against a hand-computed
      expected one, which showed the Hi byte silently off by exactly 1 in
      the failing case. Fixed by folding the `+63` into the preserved
      `StreamScrollFp_TilemapOffLo/Hi` base ONCE, at boot capture time (a
      clean single-carry 2-term add), rather than adding it again on every
      `Core_StreamScrollFp_SeekColumn` call.
   3. **DMA-queue-contention cache corruption — the one that made the
      "tested, not yet broken" stop condition below actually fire.**
      `Core_StreamScrollFp_ResolveRows` (and, it turns out,
      `Core_StreamScroll_ResolveRows` too — this bug predates Step 2c and
      is shared by BG1's resolver, not new here) called
      `Core_StreamCache(Fp)_AllocateSlot` — which permanently commits the
      cache's `Tile2Slot`/`Slot2Tile` mapping — *before* confirming
      `Core_Dma_Enqueue` would actually succeed. Found via a targeted pixel
      byte-level check (Mesen2 VRAM reads of a runtime-resolved tilemap
      word's physical tile bytes, compared against the converter's own
      `tiles.bin`/`tilemap.bin` ground truth, column-major-indexed) that
      the earlier screenshot-only verification below could not catch: 1 of
      32 sampled columns had a tilemap word pointing to a slot whose
      physical VRAM content belonged to a completely different source
      tile. Root cause: when `Core_Dma_Enqueue` fails because the shared
      8-slot software DMA queue is full that frame (real contention
      between OAM upload, BG1's budget-6 misses, and FP's budget-2 misses
      all sharing one queue), the resolver bails out early — but the cache
      tables were already updated to claim the tile now lives in that
      slot, even though the DMA that would write its real pixel data
      there never fired. On retry, the next lookup sees a cache *hit* and
      never re-fetches, permanently corrupting that slot's visible content
      until it happens to be evicted again. Fixed by adding
      `Core_Dma_HasFreeSlot` (`src/core/dma.pasm`), a non-mutating queue
      peek, and calling it as a guard immediately before
      `Core_StreamCache(Fp)_AllocateSlot` in both resolvers — bailing out
      (matching the existing "queue full, retry later" pattern) before
      any cache-table state is touched if no slot is actually free.

   **Verified**: a scripted 900-column-right-then-900-column-left scroll
   test (`m.set_input(BTN_RIGHT/BTN_LEFT, 900)`) renders cleanly in both
   directions — screenshots show the fence correctly repositioned in front
   of the characters at every sampled point, `StreamScrollFp_StagedLo/Hi`
   stay exactly 32 apart and track the camera column throughout, and
   `Nmi_FrameCounter` keeps advancing (no vblank overrun) under sustained
   scrolling with both BG1's and FP's resolvers active in the same frames.
   Beyond that, after finding bug 3, a targeted pixel-level check compared
   every non-blank tile across all 7 content rows of the resolved window
   (224 tiles) against the converter's own `tiles.bin` ground truth,
   byte-for-byte — 0 mismatches on the fixed build (was 1/32 before the
   fix, on the same scroll position). A fresh post-fix boot screenshot
   confirms the boot loader (which shares the `+63`-folded
   `StreamScrollFp_TilemapOffLo/Hi` base) still renders correctly too.
   Full regression suite (`check_label_drift.py`, `audit_all.py`,
   phase5/6/7) green on the rebuilt ROM. `scpu_main_loop`-to-`nmi_handler`
   margin is now 23 bytes (down from 34 after Step 2b) — still positive
   and passing `audit_all.py`'s own guard, but tightening; watch this if
   adding more code to `scpu_main_loop` or the pre-`scpu_boot` utility
   region.
3. **BG3 priority + HUD coexistence.** Set the priority bit on frontpanel
   tilemap entries the same way the HUD already does (done as part of Step
   2b/2c — `Core_StreamScrollFp_ResolveRows` sets bit 13 unconditionally,
   same as `Bg_LoadSceneFp_Streaming`'s boot loader); the dedicated Phase 6
   HUD checks (rerun as part of Step 2c's regression pass, not assumed)
   still pass, and the reverse-scroll test above never touched rows 0-3
   (HUD-owned), rows 4-20 (always blank), or produced any visible
   coexistence artifact. Still worth an EXPLICIT dedicated check (e.g. HUD
   changing HP while FP is mid-resolve) before calling this fully closed,
   but nothing found so far suggests a problem.
4. **Verification — DONE.** `tools/verify/phase10_frontpanel.py`, structured
   like `phase9_syncscroll_test2.py` (ground truth = the converter's own
   `tilemap.bin`/`tiles.bin`, Tile2Slot-consistency invariant, not
   self-consistency), checked against the real shipped stage-1A level, not
   a synthetic asset. Two checks: the boot-time viewport (224 non-blank
   entries across the 7 content rows, 0 mismatches) and the runtime
   resolver under a bidirectional-with-reversals scroll sequence (same
   224-entry check against whatever window results, plus `Nmi_FrameCounter`
   advancing every step).

   Writing this test surfaced a real bug: the runtime resolver's `StagedLo`/
   `StagedHi` are bumped synchronously with handing a column off to
   `Core_Nmi_Play`'s forced-blank commit — one real frame BEFORE that commit
   actually writes VRAM (same design BG1's resolver already uses). A
   first-draft version of this test checked tilemap attribute bits BEFORE
   the Tile2Slot-consistency check, so a column at the freshly-extended edge
   that hadn't been physically committed yet (still showing a stale
   leftover word from whatever world column last occupied that ring slot)
   was misclassified as a hard attribute mismatch instead of "pending
   repair." Reordering to check Tile2Slot-consistency first — exactly the
   order `phase9_syncscroll_test2.py` already established for BG1 — fixed
   it; this is a test-methodology bug, not an engine bug (BG1's own gate
   never hit it because its step list is a monotonic forward sweep with
   generous settle time, never the tight reversals this test deliberately
   uses to stress both ring directions).

   The gate is deterministic across repeated runs (checked twice) and
   passes on the full committed build. **Phase 10 is now fully done** —
   all four steps plus Step 3 verified and gated.

### Stop conditions

- **CGRAM quantization can't get frontpanel content under budget** (7 free
  sub-palettes × 4 colors = 28 colors total budget across however many
  distinct frontpanel *tiles* need distinct sub-palettes, not just 22
  colors in the abstract — tile-aware assignment may need more sub-palette
  diversity than flat color count suggests). Report the real number found;
  don't silently drop colors past what quantization can defensibly do.
- **A 40-col window's worst case exceeds the sized cache** on a different
  future level (this session only measured stage 1A). Re-run the
  measurement per-level before assuming 213-ish generalizes.
- **DMA queue contention between the two streaming layers** — this DID fire
  during Step 2c bring-up (see bug 3 above) and is now fixed at the root
  (`Core_Dma_HasFreeSlot` guards both resolvers against committing cache
  state ahead of a DMA enqueue that might fail), not just papered over by
  the conservative budget. `STREAM_SCROLLFP_BUDGET_MAX=2` (vs. BG1's
  `STREAM_SCROLL_BUDGET_MAX=6`) was still chosen conservatively and there's
  no evidence it needs to change. The 900-column bidirectional scroll
  stress test plus the full-window pixel-level VRAM check (224/224 tiles
  byte-exact against converter ground truth) together are stronger
  evidence than screenshots alone, but still NOT the same as Phase 0's own
  deliberate forced-worst-case-collision technique (both layers missing in
  the exact same frame, engineered rather than incidental). A future
  session revisiting either budget (e.g. raising FP's) should still re-run
  that more deliberate test first — the fix makes queue-full *safe*, not
  free of its own opportunity cost (a bailed-out row just retries next
  frame, which is fine, but budget changes should still be measured, not
  assumed).

## 2.11 — Phase 11: damage system ✅ DONE 2026-08-16 (user-selected from
§2.9's candidate list; commit pending)

### The constraint that shaped the design

`CHAR_HP`/`CHAR_HP_MAX`/`CHAR_HP_PER_HIT`/HUD were already real (Phase 6);
the only gap was "nothing reacts at 0" (README's own "Not built" line).
The obvious approach — kill the entity via `core/oop.pasm`'s generic
`Core_Oop_Destroy`/garbage-collect path — is a trap specific to this
codebase: `Entity1_Base`/`Entity2_Base`/`Entity3_Base` (`main.pasm`, e.g.
`Entity1_Base = $7E0a00 + 36`) are compile-time-fixed WRAM literals, NOT
derived at runtime from each entity's `OopDp`. `Core_Oop__ReclaimSlot`
compacts `OopObjRam` and rewrites *surviving* objects' `OopDp` on kill —
if entity 1 were reclaimed, entity 2/3's real DP window would physically
move while every hardcoded `Entity2_Base`/`Entity3_Base` reference
(`Character_HitApply_VsEntity2/3`, the AI-seek/render code, etc.) kept
reading the old address. This is exactly the class of bug CLAUDE.md's
"player is always slot 0... don't build a general entity-lookup system"
note warns against, just for AI slots too, not only the player.

### The design: soft-kill via CHAR_HP==0 itself

No new struct field, no `Core_Oop_Destroy` call, `OopObjRam`/`CHAR_ZP_LEN`
untouched. `CHAR_HP==0` (already the existing clamp floor) IS the dead
condition — a sticky terminal state, since nothing outside the HitApply
leaves' own clamp-at-0 ever writes `CHAR_HP`, and this phase makes those
leaves refuse to touch a target that's already at 0 (see below). Scoped to
AI entities only (`CHAR_INPUT_DRIVEN==2`); the player is exempt —
player death/game-over stays out of scope per "Explicitly out of scope."

Four small, local checks added, all following this file's Poppy-safety
rules (short branches, redundant `sep`/`rep` resyncs at every new
branch target — see §2.1):
1. **`Anim_Play`** (`main.pasm`, right after `Anim_Play__loaded`): a dead
   AI entity `rts`s immediately, before the hit-stun check. This is what
   stops it acting at all — no AI seek/attack dispatch, and critically no
   `Anim_Play_Idle/Walk/Attack` call, so it never reaches `Msu1_LoadFrame`
   again and never spends the shared one-entity-per-frame MSU streaming
   budget (`Msu1_StreamBusy`, CLAUDE.md) on an invisible corpse.
2. **`Character_PlayFrame`** X and Y movement blocks: a dead AI entity
   branches to the existing `__hold`/`__hold_y` freeze targets (same one
   hit-stun already uses), so its position stops updating.
3. **`Character_PlayFrame`**, right before `jsr Core_Oam_SetSprite`: a
   dead AI entity's `OamSetSprite_Y` is overridden to `$F0` — the OAM
   layer's own established "hidden" idiom (see
   `ccdma_validated_nmi_timing_bug` project memory: hardware-OAM "clean"
   means `Y=$F0`, not zeroed), NOT a large/offscreen X — Phase 8 made X a
   real 16-bit world coordinate with AI-seek distance math that assumes
   real positions, so a sentinel X would perturb that.
4. **`Character_HitApply_VsEntity1/2/3`**, at each leaf's `__dy_ok`
   (post-overlap-test, pre-stamp point): if the target's `CHAR_HP` already
   reads 0, `rts` before stamping `HitStun` or touching `Hp` again — a
   dead entity takes no further hits and doesn't re-count as a landed hit
   for the attacker's own `CHAR_HIT_APPLIED` latch (so an attack can still
   land on a second, live target the same cycle). `Character_HitApply`'s
   dispatcher needed no change: a dead AI never re-enters `CHAR_SELECTED==2`
   (item 1 prevents that), so it can never become the attacker either.

### Verified

`tools/verify/phase11_damage.py` (new gate): forces Entity #1's `CHAR_HP`
to 0 via direct WRAM write (safe here — unlike Phase 10's `PosX`, nothing
else races `CHAR_HP`), runs 600 real frames, and confirms against live
Mesen2 state: `CHAR_HP` stays 0, `CHAR_POS_X` frozen, `HitStun` stays 0,
hardware OAM slot 1's Y byte reads `$F0`, and `Nmi_FrameCounter` keeps
advancing (no vblank overrun from the new branches). Controls: entities 0
(player)/2/3 are NOT hidden, entities 2/3's `CHAR_HP` is untouched by
entity 1 dying, and both keep animating (`CHAR_FRAME_INDEX` sampled across
6 ticks) — deliberately NOT a position check for 2/3, since a living AI
entity holds still once within `ANIM_AI_ATTACK_RANGE` regardless of this
feature (`Character_PlayFrame__ai_x`'s own pre-existing behavior), so a
frozen X there is expected and would be a false positive if used as the
"unaffected" signal. Passed deterministically across 2 full runs.
Full regression suite (`audit_all.py`, `check_label_drift.py`, `phase5.py`,
`phase6.py`, `phase7.py`) all still pass after this change.

## 2.12 — Phase 12: expand the roster past 2 characters ✅ DONE 2026-08-16
(user-selected from §2.9's candidate list)

### What changed

`tools/bor_converter/convert_character.py "Beats of Rage Original
[v.3.0 Build 4086].pak" "DATA\CHARS\JOE\JOE.TXT" out/joe` converted a real
third character (JOE) from the local BOR pak, same pipeline already used
for JHUN — idle (10 frames)/walk (7)/attack1 (11), quantized to one shared
16-color palette. Added as roster slot 2 in `build_rom.py`'s
`ROSTER_PREFIXES`. No engine-side roster-count logic needed to change:
`CharSelect_RosterCount` is read from the packed `.msu` file's own header
byte at runtime (`main.pasm`), not a compile-time constant — the format
already supported up to 8 (`pack_msu_roster.py`'s own docstring).

`CharacterEntity_Init`'s Entity #2 now loads roster slot 2 (JOE) instead of
reusing Ralf a second time — the roster composition is now Ralf (player,
selectable)/JHUN (Entity #1)/JOE (Entity #2)/JHUN (Entity #3), replacing
the old "2 Ralfs + 2 JHUNs" duplication. Entity #3 still reuses JHUN; a 4th
distinct character is a separate, still-unscheduled expansion.

### A real bug this exposed (not introduced, exposed)

`CharSelect_Index` is shared, mutable scratch — every entity's own
`CharacterEntity_Init` call reuses it to pass ITS OWN roster slot to
`Anim_LoadCharacter` at boot. After all four entities are created, it's
left holding whichever roster slot was created LAST (Entity #3's, roster
slot 1), not the player's own real slot (0). `Anim_Play__check_reselect`
(player-only) reads this SAME cell as "the player's current index" on the
player's first Select press after boot — so without a reset, the first
press increments from the wrong base. With the old 2-slot roster this was
invisible (index 1 -> wrap -> 0 either way looks the same with only 2
slots to cycle through); with 3 slots it produced a real, confirmed skip:
the first press after boot jumped the player straight from Ralf to JOE,
silently skipping JHUN entirely. **Fixed** with a one-instruction reset
(`lda #0 / sta.l CharSelect_Index`) in `main.pasm`'s boot sequence, added
right after all four entities finish their own boot-time loads (each of
which has already consumed whatever value it needed) and before `Bg_
LoadScene` runs. This is a general fix (any future roster size benefits),
not something specific to 3 slots — found while writing this phase's own
verify gate, which asserted a clean `[0,1,2,0]` Select-cycle sequence and
caught the pre-fix `[1,2,0,1]` (i.e. skip-JHUN) behavior immediately.

### Verified

`tools/verify/phase12_roster.py` (new gate): confirms `CharSelect_
RosterCount` reads 3 (the real packed header value); presses Select three
times from boot and confirms the player's own CGRAM palette snapshot
sequence is `[Ralf, JHUN, JOE, Ralf]` — `CharSelect_Index` reads exactly
`[0,1,2,0]`, all three distinct-character snapshots differ pairwise, and
the wrapped 4th snapshot exactly matches the 1st (same character reloads
identically); `CharSelect_Loaded` stays 1 after every reselect (no failed
load); and confirms Entity #2's own CGRAM palette slot matches the
player's slot-2 (JOE) snapshot, proving Entity #2 really loaded roster
slot 2 at boot, not just that Select cycling works. Passed deterministically
across 2 runs. `phase5.py`'s palette-equality assertion was updated (not
loosened) to match the new composition: the old "slot0==slot2 (two
Ralfs)" check is gone (no longer true — Entity #2 is JOE now), replaced
with "slot2 (JOE) distinct from slot0 (Ralf)"; "slot1==slot3 (two JHUNs)"
is unchanged and still holds. Full regression suite (`audit_all.py`,
`check_label_drift.py`, `phase5.py`, `phase6.py`, `phase7.py`,
`phase11_damage.py`) all still pass.

---

## 2.13 — Phase 13: convert-time spawn table ✅ DONE 2026-08-16
(user-selected: "do the spawn-table route", path 1 of the two listed in
"What 'levels' actually means here")

### What changed

Real enemy spawn waves now exist for stage 1A, sourced from the level's own
`spawn`/`at` script blocks instead of the 4 hardcoded-forever entities
Phase 5 shipped. `tools/bg_converter/spawn_parse.py` (new) parses BOR's
`spawn`/`wait`/`group` block syntax into Python objects — verified against
`DATA\EASY\1AEASY.TXT`'s real 41 events (33 spawn/6 wait/2 group).
`tools/bg_converter/build_spawn_table.py` (new) converts the 33 spawn
events into a flat array of 7-byte records (`trigger_x`, `spawn_x`,
`spawn_y`, `facing_left`, reserved), applying the same 0.8x
(`256/320`) scale `convert_bg.py` uses so spawn positions land in the same
world-pixel space as the already-converted backdrop. Coordinate math is
BOR's actual `SCROLL_RIGHT` formula (`levelpos = advancex`, confirmed
directly against `Plombo/beatsofrage`'s `BOR.C` ~line 4804 — 1AEASY.TXT has
no `direction` line, so BOR's own default applies, NOT the SCROLL_LEFT
far-end-counting-down formula `spawn_parse.py`'s docstring originally
guessed at).

Engine side: `core/spawn.pasm` (new, included into `main.pasm`'s `$C100`
region) is a single global queue — one `Spawn_Index` walks the 33 records
in trigger order. Each frame, `Spawn_Play` (called from `scpu_main_loop`)
checks whether `Screen_PosX` has reached the pending record's `trigger_x`
and at least one AI slot (Entity1/2/3) is free; if so, that slot gets the
record's position/facing and full HP, and the index advances. If not, the
record stays pending and is retried next frame — this reproduces the
source level's real wave clustering (six simultaneous `at=960` spawns fill
all 3 slots, hold the rest pending, drain as kills free slots) without
partitioning events across slots round-robin-style, which would have
scattered a wave into unrelated trickle spawns instead.

"Free slot" reuses the existing Phase 11 soft-kill sentinel: `CharacterEntity_Init`
now boots every AI role at `CHAR_HP=0` (was `CHAR_HP_MAX`) — entities stay
hidden/inert from frame 1 until this table places them, instead of
standing fully alive with nothing to do. The player is unaffected (still
boots at `CHAR_HP_MAX`, still exempt from death per Phase 11's scope).

The table itself ships in `bor.msu`, not the ROM — `pack_msu_roster.py`
gained a `spawn_blob` parameter, appended after the existing BG/FP
sections (`SPAWN_RECORD_SIZE=7`; sidecar reports `spawn_offset`/
`spawn_count`). `Spawn_Init` (boot-time, called once from `main.pasm` right
after the frontpanel boot load) seeks MSU to the spawn section and reads
it sequentially into a WRAM buffer (`$7E5507`, 231 bytes) — the same
seek-then-sequential-read shape `Bg_LoadSceneFp_Streaming`'s own boot load
already uses. `SPAWN_MSU_OFFSET`/`SPAWN_COUNT` in `core/spawn.pasm` are
hand-synced build-time constants (the spawn blob's file offset depends on
every character/BG/FP blob packed before it, which `main.pasm` has no way
to compute) — `build_rom.py`'s new `check_spawn_constants()` cross-checks
them against what `pack_msu_roster.py` actually computed and aborts the
build loudly on mismatch, same accepted-risk pattern as this file's own
RESET/NMI/IRQ vector constants.

### Why not read the table straight from ROM

`CLAUDE.md` documents a confirmed Poppy bug where indexed-long addressing
to a ROM data label computes a wrong base address, and this codebase has
no existing, proven use of indexed ROM reads to build on (every other
`.incbin` blob — TAD driver, character/BG tile data — is DMA'd as a whole
block or read via MSU, never CPU-indexed by a runtime-variable offset).
Rather than be the first place in the project to test that addressing mode
under real hardware timing, the table ships via MSU like everything else
runtime-variable, and every actual runtime access is indexed *WRAM*
access (`.l Label,x`) — the pattern already proven throughout this
codebase (`Hud_Play`'s `HudStaging,x` loop, `EntityN_*` struct field
access).

### A real Poppy bug hit and worked around

A genuine "Branch target out of range" build error surfaced while adding
`core/spawn.pasm`, reported as `src/main.pasm:167` — a location that
turned out to be **spawn.pasm's own line 167**, not a real position in
`main.pasm`: Poppy's `.include` error reporting apparently reuses the
included file's own line number under the main file's name, which cost
real time chasing the wrong branch before this was recognized. The actual
culprit was a `bcc Spawn_Play__not_yet` whose target label was defined at
the very end of the routine — a forward jump spanning the entire rest of
the function (find_slot + all three per-slot blocks), well past the
6502/65816's ±127-byte conditional-branch range. Fixed with this project's
standard workaround: invert the condition to a short `bcs` plus an
unconditional `brl` (±32KB range) for the actual long jump — already a
documented pattern elsewhere in `main.pasm` (`Anim_Play__dispatch`'s own
`brl` sites).

### Deliberate scope cuts (see `build_spawn_table.py`'s and `core/spawn.pasm`'s
own docstrings for the full reasoning)

- `wait`/`group` events are parsed by `spawn_parse.py` but not emitted into
  the table — no scroll-blocking-until-clear, no respawn-pool sizing.
- Every record always spawns at full HP — the source level's per-spawn
  `health` override is not modeled.
- Every record spawns a generic AI-seeking enemy using whichever roster
  character is already wired to the slot it lands in — the source level's
  specific character identity (Shermie, Yashiro, ...) and non-enemy
  spawns (the `1up` pickup, the `trash` breakable prop — this engine has
  no pickup/prop entity class) are not modeled. Position/timing fidelity
  is the goal; character/entity-kind identity is explicitly not.
- No level-end trigger, no "next level," no win condition — still out of
  scope, unchanged from before this phase.

### Verified

`phase5.py`/`phase6.py`/`phase11_damage.py` updated (not loosened) to match
the new boot state: AI entities are expected to read `CHAR_HP==0` until
spawned, not `CHAR_HP_MAX` from frame 1. `phase11_damage.py`'s controls
(entities 2/3, used to prove the dead-check stays scoped to entity 1 only)
now force-write their HP to `CHAR_HP_MAX` at test start, same "direct WRAM
write is safe, nothing else races `CHAR_HP`" reasoning the test already
used for its kill write. Confirmed via a direct Mesen2 read (not just the
gates) that a passive, no-input boot leaves `Screen_PosX` at 0 forever, so
only the one `trigger_x==0` record (entity 1) ever fires — entities 2/3
staying at `CHAR_HP==0` in that scenario is correct, not a bug; entity 1
spawns immediately, walks toward the player, and its `CHAR_HP` visibly
depletes the player over ~900 frames, confirming the whole pipeline
(MSU read → WRAM table → trigger compare → slot claim → AI seek/attack)
end to end. Full regression suite (`audit_all.py`, `check_label_drift.py`,
`phase5.py`, `phase6.py`, `phase7.py`, `phase9.py`, `phase11_damage.py`,
`phase12_roster.py`) passes, including `phase9.py`'s sustained-held-input
run (confirms `Spawn_Play`'s once-per-frame check doesn't introduce a
stall or vblank overrun under real camera movement, which is what
actually exercises `trigger_x > 0` records).

---

**End of Part Two.** The two sections below this line ("Verification
methodology" and "Critical files") are Part One material, but they still
apply as reference — they list the raw audit commands that §2.2's Tool A
wraps, and the file-by-file map of the codebase.

## Verification methodology (apply at every phase gate)

- `python build_rom.py` after every change — no separate incremental step
  exists, don't skip it "since only a comment changed."
- All three of:
  ```bash
  python tools/rom_audit/verify_layout.py src/main.pasm src/main.sym
  python tools/rom_audit/audit_jumps.py src/main.bin FC00 FF20 FF30 8000
  python tools/rom_audit/audit_ownership.py src/main.bin src/main.sym FC00 FF20 FF30 8000
  ```
  (confirm the NMI/IRQ addresses passed match `build_rom.py`'s current
  printed `NMI:`/`IRQ:` line — they've moved before and will likely move
  again as this window grows.)
- Mesen2 verification per `CLAUDE.md`'s testing section, using this
  worktree's own `distribution/bor.sfc` (not the main checkout's — see
  memory `worktree_mesen_rom_path_footgun` for why that's a real, easy
  mistake). ≥32-byte reads, majority-of-3 sessions for anything you intend
  to rely on.
- Update `handoff.md`'s "Recommended next step" at the end of every phase.
- Commit at each phase boundary (not mid-phase) so a failed gate has a
  clean rollback point. Follow this project's established PR convention
  (see recent git history) rather than inventing a new one.

## Critical files

- `src/main.pasm` — `Character_PlayFrame`, `Anim_Play_*`, `Anim_LoadCharacter`,
  `Msu1_LoadFrame`/`Msu1_LoadFrame_EnqueueRow`, `scpu_boot`,
  `scpu_main_loop` — the bulk of every phase's changes.
- `src/core/oop.pasm` — read in full before Phase 1; `Core_Oop_Create`/
  `Core_Oop_Play`/the handle mechanics are load-bearing for that phase and
  everything after it.
- `src/core/oam.pasm` — `Core_Oam_SetSprite`'s contract (safe, synchronous)
  and the `Oam_CurrentSlot`-reset-once rule.
- `src/core/dma.pasm` — read `Core_Dma_Enqueue`/`Core_Dma_ProcessQueue`
  in full before Phase 0; the exact drain semantics matter for getting the
  fix right.
- `src/core/nmi.pasm` — where `Core_Nmi_Play` calls `Core_Dma_ProcessQueue`;
  Phase 0's busy-flag clear must land after that call, not before.
- `tools/bor_converter/convert_character.py`, `pack_msu_roster.py` — roster
  expansion (independent, do early).
- `tools/rom_audit/*.py` — the three verification gates every phase uses.
- `handoff.md`, `README.md` — keep both current; `README.md` is ground
  truth for "what's built," `handoff.md` is ground truth for "what to do
  next."
- `C:\Users\chad\.claude\plans\temporal-swinging-hartmanis.md` — the prior
  plan (MSU-1 runtime character streaming) this one builds directly on top
  of; its WRAM layout and phase-structure conventions are the template
  this document follows.
