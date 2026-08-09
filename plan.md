# Plan: multiple simultaneous on-screen characters

## TL;DR

Today exactly one animated character renders (a single 32×64 hardware OAM
sprite, streamed frame-by-frame from `bor.msu`). This plan gets to **two,
then a handful, of independently-animated, simultaneously-visible
characters** — the actual next step toward the original design's "1 player +
N enemies" proof of concept. It does **not** attempt combat polish, levels,
or the full OpenBOR scripting engine — see "Explicitly out of scope."

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
- **The OpenBOR bytecode VM bootstrap** (`openbor4086_sa1_bootstrap.zip`).
  Real, substantial pre-existing design work, but 0% implemented, untracked,
  targets a memory layout this project doesn't use, and depends on
  concepts from a sibling project not present here. If this is ever picked
  up, treat it as its own ground-up project with a real adaptation pass to
  this project's bank-0/WRAM conventions — not a drop-in.
- **Scrolling.** The original spec's own proof-of-concept explicitly
  requires none (single static screen). Don't add camera/scroll logic as
  part of this plan.
- **A character-select menu/UI**, save state, or persisting the roster
  selection across reset. Not asked for, not needed for this plan's goal.
- **Real damage/health/game-state systems.** Phase 4 below stops at "an
  enemy visibly reacts to being hit" — no HP tracking, no death, no win
  condition. Matches the original spec's own PoC scope ("no damage system
  required").
- **Audio content polish** beyond what's already boot-verified, until
  Phase 7 (last, roadmap-level, lowest priority).

## Phase 0 — Fix the MSU-streaming serialization hazard

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

## Phase 1 — Give the current character a real home in `core/oop.pasm`

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

## Phase 2 — Second, simultaneous entity

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

## Phase 3 — Minimal AI (the original spec's actual ask)

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

## Phase 4 onward — roadmap level only, re-verify against then-current code

Do not implement these from this document's detail alone — re-read the
actual code once you arrive, the same way earlier phases told you to. This
section exists to keep the sequence and scope intentions visible, not to
be a spec.

- **Phase 4 — collision + hit reaction.** AABB overlap check between the
  attacking entity's hitbox and the target's bounding box (matches
  original spec's explicitly-stated "AABB-only collision" PoC
  constraint). On overlap during an attack, target plays a "hit" reaction
  — reuse an existing animation state or add a minimal new one. Explicitly
  no HP/damage tracking (matches spec's "no damage system required for
  PoC").
- **Phase 5 — scale to 3-4 total enemies.** Repeat Phase 2/3/4's pattern
  for more instances, up to the original spec's "4 enemies" PoC target
  (comfortably within the N=4-free OBJ tile-column budget documented
  above). Re-verify OBJ/DMA budgets hold under the worst case — all
  entities' animations advancing on the same tick — don't assume Phase
  0's fix generalizes past 2 concurrent streamers without checking; the
  "skip and retry next frame" design should degrade gracefully (more
  entities just each wait slightly longer for their turn), but confirm
  this rather than assuming it.
- **Phase 6 — BG1 static backdrop + BG3 HUD.** Non-scrolling (matches the
  spec's explicit no-scrolling PoC constraint) background content and a
  minimal health/HUD bar layer. No level-tileset converter exists yet
  (confirmed gap versus the original spec's §5 asset pipeline) — building
  one is part of this phase, not a prerequisite someone else has done.
- **Phase 7 — audio polish.** TAD's boot handshake is verified; real
  song/SFX playback content is not (confirmed gap — check
  `soundwork/tad/` and README's "Not built" list for current status before
  starting, it may have changed). Wire a punch SFX trigger to the attack
  animation once real audio content is confirmed playing.

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
