# Handoff

Read this before doing anything else, then `CLAUDE.md` (build/test commands,
architecture map) and `build.md` (register tables, CC-DMA mechanism, Mesen2
harness gaps) — this doc doesn't repeat what's already accurate there. This
file is rewritten fresh each session to reflect current state; it is not a
session-by-session log. Deep debugging history (specific Poppy miscompile
bugs, the OBSEL/hi-table bring-up story, harness quirks) lives in this
project's Claude memory files, not here — see the pointers at the bottom of
each section below.

> **Stale since ~`fae4642` (this file wasn't refreshed for several sessions'
> worth of work):** the character no longer renders via a BG2 tilemap — see
> the "Ralf's BG2 character animation" bullet below, which is now wrong.
> `Character_PlayFrame` (`main.pasm`) draws it as a single large (32×64) real
> OAM sprite instead, same pipeline as the player-controlled second sprite
> described below. Also missing: the OAM high-water-mark/full-table-push
> robustness fixes, the hi-table nop-guard fix, and a boot-time NMI race that
> was found and fixed corrupting the loaded character's state. **README.md's
> "Current Status" section is the currently-accurate summary** — treat
> anything below that contradicts it as superseded, not as the current
> architecture. This file could use a real refresh; that wasn't in scope for
> the session that added this note.

## MSU-1 runtime character-select: Phases 0-2 all complete

The full plan (streaming characters from `bor.msu` at runtime instead of
baking exactly one into the ROM at build time) is now implemented and
verified end-to-end, across PR #3 (merged, Phase 0 de-risk + Phase 1 roster
packer + Phase 2 step 1) and this session's branch
`phase2-palette-cgram-streaming` (Phase 2 steps 2-4):

- **`pack_msu_roster.py`** (Phase 1): packs up to 8 characters' palette +
  idle/walk/attack data into a single `.msu` file with a directory of frame
  counts/delays/byte offsets. `build_rom.py` packs Ralf+JHUN into `bor.msu`.
- **`Anim_LoadCharacter`**: boot-time (and now live-reselect) MSU-1 roster
  header/directory-record seek+read+parse, 24-bit idle/walk/attack MSU
  base-offset computation, **32-byte palette stream + `DMA_TYPE_CGRAM`
  enqueue**, and `CharSelect_Loaded=1` + a force-immediate-frame-0-render
  trick on success. Called from `scpu_boot` at boot (flushed synchronously
  via `Core_Dma_ProcessQueue` right after, replacing the old 16-immediate
  `$2122` boot block) and from `Anim_Play` on live Select-button reselect.
- **`Msu1_LoadFrame`** (replaces the old `Anim_CommitFrame`): streams one
  768-byte frame from a runtime-computed MSU offset (`base +
  frame_index*768`, same shift-add idiom `Anim_LoadCharacter` uses for
  walk/attack base math) into `AnimFrameStaging`, then enqueues a
  WRAM($7E)-sourced VRAM DMA. `Anim_Play_Idle/Walk/Attack`'s old 19 unrolled
  per-frame-index compare-chain blocks (a workaround for indexed *ROM* data
  access, which stopped applying once the source became a runtime WRAM
  value) collapsed into WRAM-driven logic reading `Anim_{Idle,Walk,Attack}
  FrameCount/Delay/MsuBase`. This deleted `AnimCharIdleFrames`/
  `AnimCharAttackFrames` (8448 bytes) and walk's ROM blob (6144 bytes) —
  ~14.6KB freed across the `$C100`-`$FC00` and TAD-gap windows, now that a
  character's pixel data streams from `bor.msu` instead of being baked in
  at build time.
- **Live reselect**: `Anim_Play` checks the Select button (edge-triggered)
  before its `CharSelect_Loaded` gate, advances `CharSelect_Index` modulo
  `CharSelect_RosterCount`, and calls `Anim_LoadCharacter` — costs zero
  bytes in the tight `$FC00`-`$FF20` `scpu_main_loop` window since
  `Anim_Play` already lives in the roomy `$C100`-`$FC00` window.
- **Two real bugs found and fixed along the way** (both via Mesen2's trace
  disassembler / raw-byte comparison, not guessing): a 5th recurrence of
  Poppy bug #10 (a new guard clause at `Anim_Play`'s top reached its
  "loaded" label via a branch skipping a `rep`/`sep`, mis-sizing the next
  `cmp #2`) — see [[poppy_assembler_bugs]]; and a previously-undocumented
  class of bug, `nmi_handler` not saving/restoring A/X/Y so NMI landing
  mid-loop during `Msu1_LoadFrame`'s 768-byte read corrupted unrelated
  WRAM — see the new [[nmi_handler_no_register_save_reentrancy]] memory.
  Fixed both `Msu1_LoadFrame` and (proactively, before it could bite live
  reselect) `Anim_LoadCharacter` with `php`/`sei`-at-entry,
  `plp`-before-`rts`, matching `Core_Dma_Enqueue`'s own established
  convention.
- **Verified in Mesen2, byte-exact against the packed `bor.msu`**: CGRAM
  palette (both slots), streamed VRAM frames (idle/walk/attack, both
  slots), live reselect swapping Ralf ↔ JHUN and back (palette + frame 0
  each time), idle cycling, walk/attack/facing all still correct
  post-reselect, OAM sprites unaffected. All three `tools/rom_audit/*.py`
  tools clean throughout (0 drift, 0 ownership violations, 0 suspicious
  jump edges).
- **Not yet done**: a second, truly *simultaneous* rendered character (BG2
  compositing) — reselect swaps which single character is loaded/rendered,
  it doesn't render two at once. Boot always loads slot 0; nothing yet
  persists the last-selected slot across a reset.

## Current state (verified working, as of the session before the above)

`distribution/bor.sfc` boots and runs the following, all verified byte-level
and visually in Mesen2:

- **Ralf's BG2 character animation**: idle (boots into this), walk (dpad
  Left/Right held, full 8-frame cycle), attack (Y-button edge trigger, 5
  frames, reverts to idle on completion), all in a fixed 4x6-tile BG2
  window. Facing flip (Left vs Right) swaps the live tilemap between two
  precomputed 6-row blocks.
- **Two real hardware OAM/OBJ sprites, live and updated every frame** —
  one static, one dpad-driven on **both axes**: sprite 0 is the original
  16x16 solid-red test sprite (X=120, Y=100, static); sprite 1 is a second
  instance of the same tile whose X moves left/right and Y moves up/down
  while the dpad is held, each axis independently clamped (not bounced) —
  X at 8/216, Y at 8/208 — holding position on either axis when nothing on
  that axis is held. Both sprites are re-written into the shadow buffer
  **every frame** by `TestSprite_PlayFrame` (`main.pasm`, right after
  `TestSprite_WriteSolidTile`, called from `scpu_main_loop` before
  `Core_Oam_Play`) via the `Core_Oam_SetSprite` entry point (`core/oam.pasm`,
  right after `Core_Oam_Play`) — proving the OAM pipeline end-to-end for
  live, per-frame-updated, **input-driven** sprites, not just a one-time
  boot write or an autonomous animation. `Core_Oam_SetSprite` takes its 5
  fields (X/Y/tile/attr/hi) via WRAM staging cells (`OamSetSprite_*`,
  `$7E53AB-$7E53AF`), matching `core/dma.pasm`'s `DmaRequest_*` convention,
  writes one `Oam_Buffer`/`Oam_ExpandedHi` entry at the `Oam_CurrentSlot`
  cursor, and advances it — game code fills the cells and calls it once per
  sprite per frame, then calls `Core_Oam_Play` once.
  Sprite 1 reads `Input_press+1` via **two independent masks**, one per
  axis (X: `and #$03`, Y: `and #$0C`) — deliberately not threaded through a
  shared accumulator across both axes' branches, to avoid the
  accumulator/stack class of bug this project has hit before (see
  [[65816-calling-convention-bugs]]). X uses the exact same bit-check
  convention as `Anim_UpdateFacing` (bit0=Right, bit1=Left, Left wins on
  both held) so sprite 1's X movement and Ralf's BG2 facing flip always
  agree on the same frame's input. Y mirrors that convention (bit2=Down,
  bit3=Up, Up wins on both held — same "higher bit wins" rule as X, not an
  arbitrary second rule) but with `sbc`/`adc` swapped relative to X, since Y
  grows downward on screen while X's Left is the *decreasing* direction.
  Verified in Mesen2, both axes: holding a direction moves sprite 1's real
  OAM byte in the correct direction (confirmed explicitly, not just
  "changed by a multiple of speed" — Up decreases Y, Down increases Y,
  Left decreases X, Right increases X); each axis clamps at **exactly** its
  MIN/MAX (X: 8/216, Y: 8/208, not off-by-one); each axis holds position
  independently with no input on that axis; holding Left+Up together moves
  both axes in the same frame, and holding Left+Right together (X only)
  still moves left with `Anim_FacingLeft` reading 1 on the same sample,
  confirming X and Ralf's facing subsystem still agree; sprite 0's OAM
  bytes stay byte-exact `[120,100,0,48]`, sprite 1's tile/attr stay fixed
  at `0/$30`, and the packed hi-table byte stays exactly `$0A` throughout.
  Full-screen screenshots during idle, walk, and attack all show Ralf's BG2
  animation rendering correctly (no corruption) alongside both red OAM
  squares — this specifically confirms the code insertion didn't disturb
  `AnimCharIdleFrames`/`AnimCharAttackFrames`, which sit immediately after
  this routine and are governed by a hand-measured Poppy-off-by-one
  workaround (`ANIM_LABEL_FIXUP`) sensitive to exactly this kind of
  preceding-code-size change.
  `TestSprite_Init`'s one-time write only sets what's on screen before the
  main loop's first iteration — `TestSprite_PlayFrame` is what keeps
  sprite 0 alive going forward, and it MUST keep re-asserting sprite 0
  every frame it runs (see that routine's header comment) — the
  shadow-wipe-after-upload trap `TestSprite_Init`'s header used to warn
  about is triggered every frame now, not just theoretical.
  **Harness note for anyone testing input-driven code here**: Mesen's MCP
  `set_input` tool is wall-clock/sleep-based, not frame-stepped exactly —
  its C# handler (`UI/Utilities/Mcp/McpTools.cs`) resumes the emulator,
  sleeps roughly `frames * (1000/60) * 1.2 + 20ms`, then pauses, so the
  actual number of real frames that elapse can meaningfully overrun the
  requested `frames` count (observed ~144% of requested in one run) — and a
  read taken *immediately* after a `set_input` call can still reflect 1-2
  frames of bleed even with no further `run_frames` call (reproduced
  identically on both the X and Y axes: an idle check right after a hold
  showed ~1 extra step of movement; settling with a `run_frames` first,
  then comparing two subsequent idle reads, is stable). Assert
  direction/clamp-endpoint/relative-change, not an exact pixel value
  computed from `frames * speed`, unless the value is saturated at a known
  clamp — and don't treat an immediate post-hold read as "settled."
- **The BOR character-animation pipeline is now pak-agnostic for a single
  shipped character** (still only one character in ROM at a time — see
  below for why two can't coexist). New script
  `tools/bor_converter/gen_pasm_animset.py` takes a character's three
  `convert_animation.py` output dirs (idle/walk/attack, i.e. `manifest.json`
  + `frameNN.bin` + `palette.txt` each) and emits the same hand-tuned Poppy
  source shape `main.pasm` already hand-writes for Ralf: the
  `ANIM_FRAME_COUNT`/`WALK_FRAME_COUNT`/`ATTACK_FRAME_COUNT` + `*_DELAY`
  constants (delay = **median** of the manifest's per-frame delays, not
  mean — confirmed to reproduce Ralf's existing 10/8/10 exactly, including
  attack's non-uniform `[7,7,20,10,10]` case), the unrolled `cmp #N/beq`
  frame-dispatch chains for `Anim_Play_Idle`/`Walk`/`Attack` (every
  Poppy nop-padding/`brl`/label-fixup workaround reproduced, not just the
  logic), the `AnimCharIdleFrames`/`AnimCharAttackFrames` `.incbin` lines,
  and the 16-color CGRAM palette-load block, read from the character's
  **idle** `palette.txt` by convention — as of this session that file is
  identical across idle/walk/attack (see the palette-unification bullet
  below), so reading idle's copy is now actually correct, not just
  convenient. This exists because Poppy cannot assemble a runtime-indexed
  data table here (confirmed again
  this session — see `main.pasm`'s own comments near `ANIM_FRAME_COUNT`),
  so "generic" has to mean "the *generator* is generic," not "the shipped
  code reads a table."
  **Validated two ways**: (1) run against Ralf's own existing
  `out/ralf_{idle,walk,attack}/manifest.json` + `palette.txt`, the emitted
  fragment is semantically identical (diffed with comments/whitespace
  stripped) to the current hand-written `main.pasm` — as of this session
  the shipped labels are literally `AnimCharIdleFrames`/
  `AnimCharAttackFrames` too (see the rename bullet below), so this is now
  an exact text match, not "identical modulo a deliberate rename." (2) A
  second real character, JHUN
  (`DATA\CHARS\JHUN\JHUN.TXT` in the project's local BOR pak — chosen
  because `entity_parse.py` confirmed its idle/walk/attack1 frame counts
  are 6/8/5, **exactly** Ralf's, so the swap needed zero ROM-layout change)
  was converted end-to-end (`convert_animation.py` ×3 →
  `bake_vram_frames.py` ×3 → this generator), spliced into `main.pasm` in
  place of Ralf's data, built, all three audit tools passed clean, and
  verified in Mesen2: idle boots, walk triggers and cycles on held
  Left/Right, facing flip works, attack triggers on Y-button edge and
  reverts to idle on completion, screenshots show a correctly-rendered
  (not garbled) character matching JHUN's actual palette throughout. The
  JHUN swap was then **reverted** (`git checkout -- src/main.pasm` back to
  Ralf's hand-written source, matching the plan's "don't ship a character
  swap as a unilateral product decision" call) and rebuilt —
  `src/main.bin`/`main.pansy`/`main.sym` came back **byte-identical** to
  the already-committed Ralf build (`git diff` empty), the strongest
  available confirmation of no regression. JHUN's converted assets
  (`out/jhun_{idle,walk,attack}/`, `src/assets/anim_jhun_*.bin`) are kept
  committed as a real, re-usable proof-of-concept — regenerating the swap
  is just re-running the generator + re-doing the same splice (see
  `gen_pasm_animset.py`'s own docstring for the exact commands and which
  `main.pasm` lines to touch: the 3 delay constants near
  `ANIM_FRAME_DELAY`, the `.incbin` filenames at the `AnimCharIdleFrames`/
  `AnimCharAttackFrames` labels and the `.org $8C00` walk line, and the 16
  palette immediates — no code-shape changes needed when frame counts
  match, since the dispatch-chain text itself is then identical between
  characters).
  **Explicitly NOT done, and not a small remaining step**: a second
  simultaneous character in ROM (blocked by budget: one character's data
  is already 14,688 bytes against ~2,500 bytes total slack), pak-roster
  auto-discovery (`models.txt`), runtime character selection.
- **CGRAM palette is now unified across idle/walk/attack** (this session —
  was last session's "Recommended next step"). Previously only idle's
  16-color palette was ever loaded into CGRAM (`convert_animation.py`
  quantized each animation's frames independently, so walk/attack rendered
  through whatever colors idle happened to pick — confirmed wrong with
  both Ralf and JHUN). New script `tools/bor_converter/convert_character.py`
  fixes this at the source, not at runtime: it runs
  `convert_animation.py`'s existing per-frame load/scale/place logic
  (`_load_anim_frames`, now factored out and reused, not duplicated) for
  all three of a character's animations, then does **one**
  `Image.quantize` pass (`_quantize_shared`, also factored out) across all
  of idle+walk+attack's frames combined, before slicing the result back
  into three `_write_anim_outputs` calls that all receive the same
  palette. Result: `palette.txt` is byte-identical across
  `<prefix>_idle/_walk/_attack`. Per-animation scale/placement (legitimately
  different per animation — a walk stride needs different framing than an
  idle stance) is untouched. `gen_pasm_animset.py` needed **zero** code
  changes — it already only reads idle's `palette.txt`, which is now
  correct by construction. `convert_animation.py`'s own single-anim CLI is
  unchanged in behavior (regression-checked: byte-identical `frame*.bin`/
  `palette.txt`/`manifest.json` output against the previously-committed
  `out/ralf_idle/` before this session's tool changes).
  **Applied to Ralf's shipped data**: regenerated `out/ralf_*` +
  `src/assets/anim_ralf_*.bin` via the new tool, regenerated the Poppy
  fragment via `gen_pasm_animset.py`, diffed it against `main.pasm` —
  confirmed **only** the 16 palette immediate values differed (everything
  else, including frame counts/delays/dispatch-chain text, identical,
  since same source data/geometry), hand-edited just those 16 lines into
  `main.pasm`, rebuilt, all three `tools/rom_audit/*.py` tools clean,
  verified in Mesen2 (idle/walk/attack all still trigger/cycle/revert
  correctly, sprite 0/1 OAM byte-exact, facing flip unaffected, no
  corruption) with before/after screenshots confirming walk now renders in
  its own (shared, not idle's leftover) colors. Accepted tradeoff: 16
  colors now split across ~3x more visual content than idle-only
  quantization had, so any single animation may look marginally less rich
  than before — visually confirmed still coherent, not degraded to the
  point of looking broken.
  **Also refreshed JHUN's proof-of-concept data** (`out/jhun_*`,
  `src/assets/anim_jhun_*.bin`) through the same new tool for consistency
  with the current pipeline — not re-spliced into `main.pasm` or
  re-verified via a full Mesen splice (that splice mechanism was already
  proven working last session and doesn't depend on which palette
  algorithm produced the source data).
- **`TestSprite_PlayFrame` is now split into a sprite-0-owning routine and a
  new `Player_PlayFrame` for sprite 1** (this session — was the prior
  session's deferred cleanup item). `TestSprite_PlayFrame` now does only
  what its name says: zero `Oam_CurrentSlot`, re-assert sprite 0's static
  literals, `jsr Core_Oam_SetSprite`, `rts`. `Player_PlayFrame`, called
  right after it from `scpu_main_loop`, owns the dpad X/Y movement logic
  verbatim (only the branch labels lost their now-redundant `sprite1_`
  prefix: `Player_PlayFrame__right`/`__left`/`__hold`/`__store_x`/`__down`/
  `__up`/`__hold_y`/`__store_y`). `Player_PlayFrame` does **not** reset
  `Oam_CurrentSlot` itself — it depends on `TestSprite_PlayFrame` having
  already zeroed and advanced it (0 → 4) this frame, documented explicitly
  in both routines' headers now that the dependency is no longer visible
  from one shared function body.
  **Hit and fixed a real Poppy miscompile in the process** (raw-byte
  confirmed, not just a hunch): with no padding before it, `Player_PlayFrame`'s
  label resolved 1 byte early and landed on `TestSprite_PlayFrame`'s
  preceding `rts` opcode instead of the routine's real first instruction —
  so every `jsr Player_PlayFrame` immediately hit that stray `rts` and
  returned without running the body (silently, no crash, no hang — confirmed
  via a hex dump of the assembled bytes at the label's address, and via
  Mesen2 showing `Player_X`/`Player_Y`/`Oam_CurrentSlot` frozen forever
  while the rest of `scpu_main_loop`, e.g. `Anim_Play`, kept running
  normally every frame). This is the same label-resolves-early class of bug
  already documented for branch targets in this project (see
  [[poppy-assembler-bugs]]), just newly confirmed to also affect a `jsr`
  target, not only branch targets. Fixed with the same nop-padding
  convention already used before `TestSprite_Init`/`TestSprite_PlayFrame`.
  Verified post-fix both ways: a raw hex dump showing the label now lands on
  a harmless `nop` (not the dangerous `rts`), and Mesen2 showing sprite 1
  moving/clamping identically to the pre-split baseline on both axes.
  Costs 5 bytes net against the `$C100`-`$FC00` budget (549 → 544 free) —
  the `jsr`/`rts` pair plus the new padding.
- **Two prior sessions' deferred renames are done** (both byte-neutral):
  `AnimRalfIdleFrames`/`AnimRalfAttackFrames` → the character-independent
  `AnimCharIdleFrames`/`AnimCharAttackFrames` that `gen_pasm_animset.py`
  already emitted (see the pak-agnostic-pipeline bullet above for why that
  closes a validation gap, not just cosmetics); and sprite 1's dpad-movement
  WRAM state/constants — `TestSprite2_X`/`TestSprite2_Y` → `Player_X`/
  `Player_Y`, `TESTSPRITE2_MIN_X`/`MAX_X`/`MIN_Y`/`MAX_Y`/`SPEED` →
  `PLAYER_MIN_X`/`MAX_X`/`MIN_Y`/`MAX_Y`/`SPEED` — matching how "What's NOT
  done yet" already described sprite 1 (functionally closer to a player
  entity than a test sprite). `TestSprite_Init`/`TestSprite_WriteSolidTile`
  kept their names then (still true — see the split bullet above for why
  the old `TestSprite_PlayFrame__sprite1_*` branch labels no longer exist
  either, now `Player_PlayFrame__*`). Verified byte-neutral the strong way
  at the time: `src/main.bin` came back **byte-identical** to the
  previously-committed build after the rename + rebuild (`git diff` on
  `main.bin` empty; only `main.sym`/`main.pansy` differed, as expected for a
  pure symbol-name change) — the same confirmation-of-no-regression pattern
  the JHUN swap-and-revert used the session before that.
- **Three ROM-layout audit tools** (`tools/rom_audit/`) — run after any
  change that grows code/data in the `$C100`-`$FC00` fixed-`.org` window:

  ```bash
  python tools/rom_audit/verify_layout.py src/main.pasm src/main.sym
  python tools/rom_audit/audit_jumps.py src/main.bin FC00 FF00 FF10 8000
  python tools/rom_audit/audit_ownership.py src/main.bin src/main.sym FC00 FF00 FF10 8000
  ```

  All three report clean on the current build (one benign drifted-but-
  unreferenced label, now `AnimCharAttackFrames` post-rename (was
  `AnimRalfAttackFrames`), is expected — see `verify_layout.py`'s own
  docstring for why that specific pattern is safe).

- **Remaining margin before `$FC00`**: ~544 bytes as of this build (was 549
  before this session's `TestSprite_PlayFrame`/`Player_PlayFrame` split —
  see above; the rename work in the same window was byte-neutral by design/
  verification). History: ~607 before the prior session's
  Y-axis addition (the 2nd-axis dpad block cost 58 bytes, close to the
  ~80-byte estimate going in), ~612 before that session's X-axis/clamp
  work, ~834 before the `Core_Oam_SetSprite` + second-sprite session before
  that. Don't compute this from the highest label address in `main.sym`
  alone — `.incbin` blobs have no end-label, so that only gives you where
  the last blob *starts*. Add the blob's real size (frame count x
  `ANIM_FRAME_BYTES`, or the `.bin` file's size on disk) to get the true
  end address before subtracting from `$FC00`.
  **The `$C100`-`$FC00` window isn't the only place code could live** —
  this session confirmed (raw bytes + Mesen2 behavioral test, see
  [[poppy-assembler-bugs]] bug 9 and `tools/bank_test_*.pasm`) that the
  project's long-standing "multi-bank Poppy assembly has dropped code"
  caution is imprecise: nothing gets dropped, cross-bank *references*
  (`jml`/`jsl` to a non-zero-bank label) just silently resolve to bank
  `$00` instead of the real bank, while the referenced code's bytes land
  correctly. A verified workaround (an explicit `bank:offset` literal
  constant instead of the bare label) makes a second bank usable for
  genuinely-isolated code. `bor.sfc` is 4MB and >99% unused, so this is a
  real option once `$C100`-`$FC00` stops having room — not attempted for
  real feature code yet, only proven in isolated `tools/` repros.

Basic Mesen2 reproduction (adjust ROM path if working from a worktree):

```python
import sys
sys.path.append(r'E:\gh\Mesen2\python')
from mesen_mcp.session import McpSession

ROM = r'E:\gh\snes-bor\distribution\bor.sfc'
MESEN = r'E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe'

with McpSession(rom=ROM, mesen=MESEN, boot_wait=2.0) as m:
    m.pause(); m.reset_emulator(); m.pause()
    m.run_frames(90)
    print('OAM sprite0:', list(m.read_memory('snesSpriteRam', 0, 4)))
    print('OAM sprite1:', list(m.read_memory('snesSpriteRam', 4, 4)))
    print('OAM hi byte0:', hex(m.read_memory('snesSpriteRam', 512, 1)[0]))  # expect 0x0A
    print('Anim_Selected:', m.read_u8(0x7E53B2, mem_type='snesMemory'))
```

## What's NOT done yet

- **No real player entity yet.** Sprite 1 now responds to the dpad on both
  X and Y, its WRAM state/constants are named `Player_X`/`Player_Y`/
  `PLAYER_*`, and (as of this session) it has its own accurately-named
  driver routine (`Player_PlayFrame`, separate from `TestSprite_PlayFrame`
  — see "Current state" above), but there's still no player state (health,
  animation, hitboxes), and no interaction between it and Ralf's BG2
  animation system — it's still a second solid-red 16x16 square, not a
  character. `TestSprite_PlayFrame` itself keeps that name (it only
  re-asserts sprite 0, a genuinely static test sprite, now that the split
  is done).
- **Only 2 of 128 OAM slots ever exercised.** `Core_Oam_SetSprite` itself
  is generic (any slot, any X/Y/tile/attr/hi), but nothing has called it
  with a 3rd+ sprite or tested behavior near `OAM_SLOTS` (128).
- **The hi-table's X-high bit is unexercised by any real shipped sprite**
  (only by a synthetic WRAM test) — unverified if a sprite ever needs X >=
  256.
- **No multi-enemy BG2 compositing** (only one character renders at a
  time — Select swaps which one, doesn't add a second) **and no
  background/level tileset conversion.** MSU-1 asset streaming itself
  (palette + all three animations, live reselect) is now done — see
  "MSU-1 runtime character-select" above. Matches the project's stated
  "not a playable game yet" scope otherwise.
- **Cosmetic boot-time "pop"** (static sprite geometry differs briefly from
  animated frames' geometry until `Anim_TickCounter` first reaches 0) — not
  fixed, not decided. Somewhat mitigated for the BG2 character specifically
  by `Anim_LoadCharacter`'s force-immediate-frame-0-render trick (added
  this session), which didn't exist when this was last written.
- **Boot always loads roster slot 0.** Nothing persists a previously-
  selected slot across a reset (no save state/SRAM involved anywhere yet).

## Recommended next step

MSU-1 runtime character-select (palette streaming, frame-playback rewrite,
live reselect) is now fully done — see the section above. Sprite 1 is
fully 2-axis dpad-driven; the BOR animation pipeline is pak-agnostic and
now MSU-1-native rather than ROM-baked. No small, independent cleanup item
remains queued. The `$C100`-`$FC00` window has substantially more slack
now than at any point in this project's history (Phase 2's deletion of the
ROM-baked animation blobs freed ~14.6KB) — re-measure via `main.sym` before
assuming a specific number, but ROM budget is no longer the binding
constraint it was. The next session's options:

- **Real player entity/state**: give sprite 1 health/hitbox/animation
  state and actually connect it to the BG2 character animation system
  (today they're driven by the same input bits but are otherwise unrelated
  — a solid-red OAM square moving independently of the animated BG2
  character). This is the most natural "move past hardware-plumbing
  proofs" step but is a real design decision (what owns position — OAM,
  BG2 scroll, or both; how hitboxes interact with `core/oop.pasm`'s
  class-based object system), not a mechanical change — plan it
  separately rather than starting mid-session.
- Multi-enemy BG2 compositing, background/level tileset conversion — both
  still fully unstarted, matching the project's "not a playable game yet"
  scope.
- Persisting/restoring `CharSelect_Index` across a reset, if a "remembers
  your last pick" boot experience is ever wanted (not asked for yet).

## Harness gotchas (Mesen2 / build)

Full detail lives in project memory ([[mesen-audio-check-nondeterministic]],
[[mesen-mcp-hook-reliability-gap]], [[mesen-controller-not-configured]],
[[poppy-assembler-bugs]], [[ccdma-validated-nmi-timing-bug]],
[[65816-calling-convention-bugs]], [[oam-sprite-bringup]],
[[nmi-handler-no-register-save-reentrancy]]) — read those before spending
time rediscovering a harness quirk or Poppy miscompile.
Quick-reference list of what's easy to trip over fresh:

- `set_input`'s `frames` argument advances the emulator itself — don't
  `run_frames` again right after, you'll run extra frames with no input.
- A read taken *immediately* after `set_input` returns can still reflect
  1-2 frames of input bleed past the call boundary (wall-clock/sleep-based,
  confirmed identically on two independent axes this session) — settle
  with a `run_frames` call first before treating a position as "at rest."
- A fresh/reset Mesen portable install can ship with `Snes.Port1.Type =
  "None"`, silently no-op'ing every `set_input` call.
- `snesCgRam` (not `cgram`/`snesCGRam`/`paletteRam`) is the correct memory
  type string for CGRAM reads.
- `crop_screenshot`'s default `format='path'` returns a dict with a `'path'`
  key (a PNG on disk), not raw bytes.
- The BG2 facing-flip tilemap lives at VRAM byte `$B800` (word `$5C00`) with
  a `$40`-byte row stride — not address 0.
- Fixed `.org` overflow can silently corrupt a clean-looking build. After
  growing code/data in the `$C100`-`$FC00` window, always re-run the three
  audit tools above rather than trusting a successful build.
- Mesen's own audio-silence heuristic has a ~40% false-positive rate on
  unchanged ROMs — don't treat one flagged run as a regression without
  replicating it.

## File inventory (what's real vs. scratch)

**Real, part of the build/pipeline:**
- `src/main.pasm` — the only file `build_rom.py` actually assembles.
- `src/core/*.pasm` — ported engine utility modules, `.include`d into
  `main.pasm`.
- `src/assets/*.bin` — baked VRAM-format animation/tilemap data.
- `tools/bor_converter/*` — asset pipeline (pak extraction, sprite/animation
  conversion, VRAM-frame baking).
- `tools/rom_audit/*` — the three layout/jump/ownership audit tools above.

**Demo/example output, not fully wired into the ROM:** `out/ralf_idle/`,
`out/ralf_walk/`, `out/ralf_attack/` — baked+wired source frame data.
`out/jhun_idle/`, `out/jhun_walk/`, `out/jhun_attack/` and
`src/assets/anim_jhun_*.bin` — this session's second-character
pipeline-genericity proof (see "Current state" above); real converted/baked
data, not currently referenced by `main.pasm` (which ships Ralf).

**Already-flagged-as-dead:** `src/sa1/*.pasm`, `copy_working_test.*`,
`exact_copy_test.*`, and similar files under `src/` are scratch/experiment
files from earlier debugging, not part of the real build. See `CLAUDE.md`.
