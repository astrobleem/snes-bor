# Handoff

Read this before doing anything else, then `CLAUDE.md` (build/test commands,
architecture map) and `build.md` (register tables, CC-DMA mechanism, Mesen2
harness gaps) — this doc doesn't repeat what's already accurate there. This
file is rewritten fresh each session to reflect current state; it is not a
session-by-session log. Deep debugging history (specific Poppy miscompile
bugs, the OBSEL/hi-table bring-up story, harness quirks) lives in this
project's Claude memory files, not here — see the pointers at the bottom of
each section below.

> ## Read this banner before anything else in this file
>
> **Where to go for what:**
> - **What to do next → [`plan.md`](plan.md) "Part Two."** That is the live,
>   step-by-step roadmap for all remaining work. Nothing in *this* file is a
>   to-do list any more.
> - **What currently works → `README.md`'s "Current Status."** That is the
>   authoritative summary. Treat anything in this file that contradicts it
>   as superseded, not as the current architecture.
> - **How it's built and why → `CLAUDE.md`** (build/test commands,
>   architecture map, the entity system, the Poppy bug checklist).
>
> **What this file is:** an append-only debugging record. The most recent and
> most accurate sections are near the bottom — "Phase 2 done and verified"
> through "Phase 9 done and verified," then "Phase 10: frontpanel foreground
> layer" (DONE, all steps 1-4), then "Phase 11: damage system" (DONE) — plus
> "Harness gotchas" and "File inventory." Read those. Everything above them
> is older history, kept for the root-cause detail, and parts of it are
> known wrong.
>
> **As of 2026-08-16, Phase 11 (damage system) is the most recent
> fully-COMPLETED phase — see that section near the bottom.** AI entities
> now soft-kill at `CHAR_HP==0` (stop acting/moving/hitting, sprite hides)
> without ever touching `core/oop.pasm`'s generic kill/GC path, which would
> have broken the codebase's `Entity1_Base`/`Entity2_Base`/`Entity3_Base`
> fixed-address scheme. Built, verified in Mesen2, AND gated by a committed
> regression script (`tools/verify/phase11_damage.py`).
>
> **Phase 10 (frontpanel foreground layer) is DONE** — all of Steps 1
> (converter tooling), 2a (cache allocator), 2b (boot-time initial load),
> 2c (runtime scroll resolver), 3 (HUD coexistence), and 4 (committed
> verify gate) are done, verified in Mesen2, AND gated by
> `tools/verify/phase10_frontpanel.py`: the chain-link fence renders
> correctly in front of the character sprites and correctly tracks the
> camera as it scrolls, in both directions, with no rendering corruption.
> Step 2b's bring-up found and fixed four real bugs (two in `main.pasm`'s
> boot ordering/scratch-cell reuse, one BG3 CHR-base tilemap-addressing
> bug, one converter transparency-quantization bug); Step 2c's found and
> fixed three more (a window-width-tracking bug, a chained-ADC
> carry-propagation bug, and a DMA-queue-contention cache-corruption bug
> shared by BOTH streaming resolvers, not FP-only — see
> `Core_Dma_HasFreeSlot` in `src/core/dma.pasm`); writing Step 4's gate
> found one more, in the TEST not the engine (attr-before-Tile2Slot check
> ordering misclassified a not-yet-committed edge column as a hard
> failure) — see `plan.md` §2.10 Steps 2b/2c/4 for the full list, each
> worth reading before touching this code again since none of the eight
> failure modes are obvious from the symptom alone. `plan.md` §2.9 lists
> other, unrelated candidate next phases.
>
> **Known-wrong sections above, specifically:**
> - The character does **not** render via a BG2 tilemap (the "Ralf's BG2
>   character animation" bullet). It's a single large 32×64 hardware OAM
>   sprite, drawn by `Character_PlayFrame`.
> - There is no separate "second dpad-driven test sprite." That entity and
>   the animated character were merged, then generalized into the
>   `CharacterEntity` object class — every on-screen character is now an
>   instance of one class dispatched through `core/oop.pasm`.
> - **"What's NOT done yet"** and **"Recommended next step"** are both stale
>   — see the note at the head of each.

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

> **HISTORICAL — the title is no longer true.** This section predates the
> entity system. In particular `Player_PlayFrame` and `TestSprite_PlayFrame`
> **no longer exist**: that dpad-driven sprite was merged into the animated
> character and then generalized into the `CharacterEntity` object class, so
> its two-axis movement now lives in `Character_PlayFrame` under
> `CHAR_INPUT_DRIVEN=1`. The root-cause detail below (especially the
> nop-guard/branch-resolution findings) is still accurate and worth reading;
> the architecture description is not. Current state → `README.md`.

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

> **STALE — do not use this list.** It predates the entity system entirely.
> There *is* a real player entity now (`CharacterEntity` with
> `CHAR_INPUT_DRIVEN=1`), multi-character compositing works, and enemy AI
> and collision both exist. For the current not-done list see `README.md`'s
> "Not built" section; for what to do about it see `plan.md` Part Two. Kept
> below only as a record of what was open at the time.

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

> **SUPERSEDED.** This section describes Phases 0 and 1a as they were being
> executed. Phases 0–4 are now all done and committed (`fd9bcdc`, `e7d18eb`,
> `f2f52e0`, `78f2acb`, `a32d88f`) — see the "Phase 2/3/4 done and verified"
> sections lower in this file. **The actual next step is `plan.md` Part
> Two, §2.2 (build the two tooling scripts) followed by §2.3 (Phase 5).**
> Kept below for the Phase 0 root-cause detail, which is still accurate.

**Now executing `plan.md`** (repo root) — a phased plan for multiple
simultaneous on-screen characters, written after a full project review.
Phase 0 (MSU-streaming serialization fix) is **done and verified**:

- `Msu1_StreamBusy` (`$7E2330`, declared in `main.pasm` before the
  `core/*.pasm` `.include` block since `core/nmi.pasm` needs to reference
  it) gates `Anim_Play_Idle`/`Walk`/`Attack`'s per-tick countdown —
  checked *before* the `Anim_TickCounter` decrement, not after it reaches
  0, to avoid starving a blocked entity every frame. Set by `Msu1_LoadFrame`
  once its 6 row-DMAs are queued; cleared by `Core_Nmi_Play`
  (`core/nmi.pasm`) right after `Core_Dma_ProcessQueue` drains that
  vblank.
- `Msu1_LoadFrame_EnqueueRow` now checks `Core_Dma_Enqueue`'s carry and
  faults (`Error_DmaQueueFull`) instead of silently dropping a row on
  queue overflow — defense-in-depth on top of the gate above.
- Verified via a forced two-stream collision test (temporary hook in
  `Anim_Play`, removed after confirming): call A correctly left the gate
  up, call B correctly observed it and was blocked — 3/3 Mesen2 runs.
  Idle/walk/attack regression-checked clean afterward. All three
  `tools/rom_audit/*.py` scripts clean.

**Phase 1a (advisor-recommended split of plan.md's Phase 1, done and
verified):** proved `core/oop.pasm`'s `Core_Oop_Create`/`Core_Oop_Play`
indirect-dispatch path (`jsr (ClassInit,x)` / `jsr (OopCurrent,x)`, each
wrapped in a `phd`/`tcd`/`pld` DP-window switch) actually works with a real
registered class — this project had zero classes registered before now, so
that path had never once executed. A `Character` class is registered at
boot (`scpu_boot`, right after `Core_Screen_Init`) with a thin-shim
`Play`/`Init` (`CharacterEntity_Init`/`CharacterEntity_Play` in `main.pasm`,
just after `Anim_LoadCharacter`'s `rts`) that dispatches unchanged to
`Anim_Play`/`Character_PlayFrame` — no per-instance DP state yet, that's
Phase 1b. `scpu_main_loop`'s direct `jsr Anim_Play`/`jsr Character_PlayFrame`
calls were removed; `Core_Oop_Play` now drives them instead (runs slightly
earlier in the loop, before `Core_Screen_Play`, which is self-contained and
unaffected by the reorder).

Hit and fixed a real, previously-latent Poppy bug doing this: **`LDX`/`LDY`
have no absolute-long addressing mode on real 65816** (only `LDA` does) —
`ldy.l CharacterClassId` silently loaded `Y=0` regardless of the byte's
real value, which fed `Core_Oop_Create` an invalid 0 class id, underflowed
its internal `dec a` to `$FFFF`, and sent every subsequent class-table
array read to a wildly wrong offset — manifesting as a total boot hang with
every WRAM read returning different garbage each session (looked exactly
like harness nondeterminism until traced to ground truth). Fixed via
`lda.l` + `and #$00ff` + `tay` instead. See [[poppy-assembler-bugs]] bug 11.

Verified: all three `tools/rom_audit/*.py` scripts clean; 3/3 Mesen2 runs
showing idle/walk/attack/facing behave identically to pre-Phase-1a
(`Anim_Selected` 0→1 on Right held, back to 0 on release, →2 on Y held;
`OopObjSlotPtr`/`OopObjRamPtr`/`OopCreateCounter` all confirm exactly one
object was created). Also directly confirmed pixel-identical rendering,
not just inferred from WRAM state: the packed OAM shadow buffer
(`Oam_Buffer` $7E5100 512B + `Oam_PackedHi` $7E5300 32B) at frame 120 is
byte-for-byte identical between this commit and the pre-Phase-1a commit
(`3481652`) — worth re-checking, since `Character_PlayFrame` (which writes
that buffer) now runs slightly earlier in the loop, inside `Core_Oop_Play`
rather than directly from `scpu_main_loop`.

**Phase 1b prerequisite, found but deliberately not fixed in 1a (no failing
test attached to it yet, so it stayed out of that commit):**
`Core_Oop_Init`'s `__clear_objs`/`__clear_classes` loops run in `.a8` while
stepping `X` by 2 through 16-bit (`.dw`) array elements — this clears only
each element's low byte, leaving the high byte as boot-time garbage.
Currently harmless because every consumer (`Core_Oop_Play`'s flag check,
etc.) masks with a small constant that discards the high byte anyway. It
stops being harmless once `OopDp` (also cleared this same broken way) is
read before being written for a given slot — `Core_Oop_Play` does
`lda.l OopDp,x` / `tcd` with **no mask**, so a garbage high byte there
means `tcd` switches to a garbage direct page, exactly the class of bug
that cost most of this session (see bug 11 above). Today's single object
survives only because `Core_Oop_Create` always fully (16-bit) overwrites
`OopDp` for the slot it allocates before anything reads it. Fix before
Phase 2 creates a second entity and any code path might read a slot's
state before/without going through `Core_Oop_Create` first: change both
loops to run in `.a16` (drop the `sep #$20`/`rep #$10` split, keep the
`inx`/`inx` stride) so each `sta.l Array,x` clears the full 16-bit element.

**Phase 1b, Step 0 + Step 1 done and verified** (advisor-recommended
incremental split, each step gated on OAM shadow-buffer byte-identity vs.
the Phase 1a baseline):

- **Step 0**: fixed `Core_Oop_Init`'s `__clear_objs`/`__clear_classes` loops
  to run `.a16` instead of `.a8` (was only clearing the low byte of every
  16-bit array element — see Phase 1a's note above). Pure bugfix, OAM
  identity held.
- **Step 1**: moved `Anim_Selected`/`Anim_FrameIndex`/`Anim_TickCounter`/
  `Anim_FacingLeft` and the six `Anim_{Idle,Walk,Attack}{FrameCount,Delay}`
  + three `MsuBase` pairs into the `CharacterEntity` class's per-instance DP
  window (`CHAR_SELECTED`/`CHAR_FRAME_INDEX`/`CHAR_TICK_COUNTER`/
  `CHAR_FACING_LEFT`/`CHAR_IDLE_FCOUNT` etc. — full field layout declared
  near the old `Anim_FrameIndex` declaration in `main.pasm`, `CHAR_ZP_LEN`
  now the registered class's real `ZpLen`). `Anim_Play`/`Anim_Play_Idle/
  Walk/Attack`/`Anim_UpdateFacing`/`Character_PlayFrame`/`Anim_LoadCharacter`
  were edited **in place** (not reimplemented) to use bare, DP-relative
  addressing (no `.l`/`.w`) for exactly these fields — `CharSelect_*`,
  `Player_X/Y`, `AnimHeaderStaging`/palette/frame staging, and the hardcoded
  palette/tile-column/single-entity assumptions are still global, untouched
  until their own later steps. **This forced the boot-time character load
  to move**: `Anim_LoadCharacter`'s writes are only DP-correct when called
  with the object's window already switched in (`phd`/`tcd`, done by
  `Core_Oop_Create`/`Play`), so the old direct `jsr Anim_LoadCharacter` at
  `msu1_done` (right after MSU-1 track-select — a real ordering dependency,
  see that routine's header) is now `jsr Core_Oop_Create` instead, and
  `CharacterEntity_Init` (given the roster index as its init param) does the
  actual `jsr Anim_LoadCharacter` call, correctly DP-switched.
  `Core_Oop_RegisterClass` stays at its original early boot position
  (registration has no ordering dependency); only `Create` moved down.

  Verified two ways beyond the OAM check: raw-byte confirmation that a bare
  small-integer symbol (`CHAR_SELECTED = 11`) assembles as 65816 Direct Page
  mode (`A5 0B`, 2 bytes) and not Absolute — this was unverified territory
  (no prior DP-relative addressing anywhere in this codebase) so it was
  checked directly before doing the 70-site mechanical conversion, not
  assumed; and live walk/attack/facing behavior (Right-held clamps at
  `PLAYER_MAX_X`=216, attribute byte flips `$30`→`$70` on Left-held,
  matching pre-refactor exactly), 3/3 Mesen2 runs.

**Step 2 done and verified** (same incremental split): `Player_X`/`Player_Y`
→ `CHAR_POS_X`/`CHAR_POS_Y` (DP-relative, offsets 4/6, already reserved in
the field layout), and `Character_PlayFrame`'s dpad-read blocks (both X and
Y) now gate on `CHAR_INPUT_DRIVEN` — skip straight to re-storing the current
position unchanged if clear, so a future non-input-driven entity (Phase 2)
stays static without a separate code path. Only one entity exists today so
`CHAR_INPUT_DRIVEN` is hardcoded to 1 in `CharacterEntity_Init` rather than
threaded through the init param yet — Phase 2's second entity is what will
force that parameter to actually exist. The boot-time `Player_X/Y` init
(mid-screen 120/150) had the same DP-window problem as Step 1's character
load and moved the same way: out of `scpu_boot` (which runs with D at its
default, not this object's window) and into `CharacterEntity_Init`, right
after the `Anim_LoadCharacter` call.

Verified: OAM shadow buffer byte-identical to the Phase 1a baseline at
boot (3/3 runs), and held-dpad movement clamps at the same `PLAYER_MAX_X`
(216)/`PLAYER_MAX_Y` (208) values as before on both axes.

**Step 3 done and verified**: `Character_PlayFrame`'s hardcoded `$30`/`$70`
attribute-byte literals are now computed from `CHAR_PALETTE_SLOT`
(`$30 | (CHAR_PALETTE_SLOT<<1)`, then `|$40` if `CHAR_FACING_LEFT`), and the
OBJ base tile is `CHAR_TILE_COLUMN*4` instead of the hardcoded `0`.
`Msu1_LoadFrame` now precomputes `CHAR_TILE_BYTE_OFFSET` (`CHAR_TILE_COLUMN
*128`, new `.dw` field at offset 31, `CHAR_ZP_LEN` now 33) once per call and
adds it to all 6 row-DMA target addresses. `CharacterEntity_Init` explicitly
zeroes `CHAR_PALETTE_SLOT`/`CHAR_TILE_COLUMN` (0/0 reproduces the exact
values these fields replaced) rather than relying on `Core_Oop_Init`'s
object-RAM clear, since both fields are now actually read every frame.

Added the explicit `Oam_CursorResetDone` flag (**not** `OopObjIndex`, per
plan.md's warning): a new global byte, `$7E2332` (free gap next to
`Msu1_StreamBusy`/`CharacterClassId`), cleared once in `scpu_main_loop`
immediately before `jsr Core_Oop_Play`. `Character_PlayFrame` now checks it
at entry — first entity dispatched each frame sees it clear, resets
`Oam_CurrentSlot` to 0 and sets the flag; any later entity that same frame
sees it set and leaves `Oam_CurrentSlot` alone, so it appends into the next
free slot instead of re-stomping slot 0. With only one entity today this is
behaviorally identical to the old unconditional reset, so — as plan.md
warned — the OAM-identity gate proves nothing about whether the flag logic
itself is right; it was checked by inspection against plan.md's exact rule,
not just by the gate passing. Real test of this logic is Phase 2's second
entity.

Verified: build clean (32561 bytes, same fixed `.org` window); all 3
`rom_audit` tools clean (`verify_layout.py`: 417 labels, 0 drifted;
`audit_jumps.py`: 1901 instructions, 249 edges, 0 suspicious;
`audit_ownership.py`: 418 labels, 79 CALL-class edges, 0 violations); OAM
shadow buffer byte-identical to the Phase 1a baseline at boot (3/3 Mesen2
runs) — tile=0/attr=`$30` unchanged since `CHAR_PALETTE_SLOT`/
`CHAR_TILE_COLUMN` are both 0 for this single entity; live behavior
unchanged (Right-held clamps X at 216, Left-held clamps X at 8 with
attribute byte `$70` = priority3|palette0|hflip, confirming the new
`CHAR_PALETTE_SLOT`-derived computation reproduces the old hardcoded value
exactly at slot 0).

Phase 1b is functionally complete for a single entity — every field in the
plan.md layout is live except `CHAR_ROSTER_INDEX` (still reads from the
init param into the global `CharSelect_Index`, not stored per-instance; not
needed until something wants to read back which roster slot a *specific*
entity loaded).

## Phase 2 done and verified: second, simultaneous entity

`CharacterEntity_Init`'s init param is now `(role<<8)|roster_index`: role 0
= player-controlled defaults (Phase 1b's exact single-entity behavior,
unchanged — Entity #0's `lda #0` call site still works since its old high
byte was already 0), role 1 = a static NPC (own palette/tile-column, not
dpad-driven). `msu1_done` now does a second `jsr Core_Oop_Create` right
after the first: `lda #$0101` (role 1, roster slot 1 = JHUN) — Entity #1,
`CHAR_PALETTE_SLOT=1`, `CHAR_TILE_COLUMN=1`, `CHAR_INPUT_DRIVEN=0`, fixed
position X=40/Y=150 (clearly separated from Entity #0's X=120/Y=150, no
32px-sprite overlap).

**Two real bugs found and fixed during this phase's own verification, not
found by any rom_audit tool or by the build succeeding — both only visible
by reading actual WRAM/CGRAM state, not by "it built cleanly":**

1. **CGRAM palette target was still hardcoded to `$0100` (palette 0) in
   `Anim_LoadCharacter`**, unaffected by Phase 1b Step 3's
   `CHAR_PALETTE_SLOT` attribute-byte work — Step 3 only changed which
   palette *number* the OAM attribute byte points at, not where the actual
   16-color palette *data* gets streamed to in CGRAM. Entity #1 would have
   pointed its attribute bits at CGRAM palette 1 ($120) while nothing ever
   wrote real data there (stale/boot CGRAM contents), rendering with a
   garbage palette. Fixed: `Anim_LoadCharacter`'s CGRAM DMA target is now
   `$0100 + CHAR_PALETTE_SLOT*32`, computed from the DP field right before
   the enqueue. Confirmed via direct `snesCgRam` reads (Mesen2 MCP memory
   type — not `cgRam`/`CgRam`/`paletteRam`, none of which exist; only
   `snesCgRam`/`SnesCgRam` work) that palette 0 and palette 1 hold distinct,
   both-non-zero 32-byte blocks after boot.
2. **Ordering bug in the first `CharacterEntity_Init` rewrite**: an `and
   #$00ff` was left in front of the `xba` used to extract the init param's
   role byte, a leftover from an earlier draft's field order — it zeroed
   the roster-index half of the param *before* `xba` could move it out of
   the way, so the recovered "roster index" was always 0 and the role
   check (via a second `and #$00ff`/`xba` round-trip) always evaluated to
   0 regardless of what was actually passed in. Silently produced a
   visually-plausible but wrong result: Entity #1 rendered as a second
   *player-role*, roster-0 (Ralf) copy at the wrong position, not the
   intended static JHUN NPC — caught only by reading `OopObjRam`'s raw
   bytes for both objects' `CHAR_POS_X`/`CHAR_PALETTE_SLOT`/
   `CHAR_TILE_COLUMN`/`CHAR_INPUT_DRIVEN` fields directly and comparing
   against the intended role-1 values, not by the OAM sprite bytes alone
   (which happened to show *some* second sprite, just the wrong one).
   Fixed by saving the full param on the stack (`pha`) before the role
   branch consumes `A`, and `pla`-ing it back afterward (with an explicit
   `rep #$31`/`.a16` re-assert first, since both role branches leave `.a8`
   in effect and `pla` must match `pha`'s original 16-bit width or the
   stack unbalances by a byte).

Verified after both fixes: all 3 `rom_audit` tools clean (419-420 labels,
0 drifted/suspicious/violations); `OopObjRam` raw bytes for both objects'
windows read back with the exact intended field values (Entity #0:
pos=120/150, palette=0, column=0, input_driven=1; Entity #1: pos=40/150,
palette=1, column=1, input_driven=0, and distinct idle/walk/attack delays
+ MSU base offsets confirming JHUN's data loaded, not Ralf's); `snesCgRam`
confirms two distinct non-zero palettes; `snesVideoRam` confirms Entity
#1's OBJ tile-column-1 VRAM bytes ($8080-$80FF) are real, non-zero, and
different from Entity #0's column-0 bytes ($8000-$807F) — the row-DMA
`CHAR_TILE_BYTE_OFFSET` targeting is correct, no cross-entity VRAM
corruption; ran 720 total frames (12s) to let both entities' idle cycles
(delays 10/8/10 vs 20/9/7 ticks) re-align at least once under real
concurrent MSU streaming, `Msu1_StreamBusy` still correctly drained to 0
afterward (no stuck/deadlocked stream gate); Entity #0 remains fully
dpad-controllable (Right-held still clamps at X=216) while Entity #1 stays
fixed; 3/3 Mesen2 runs consistent. Entity #0's own 4 OAM bytes still
exactly match the original Phase 1a baseline (`[120, 150, 0, 48]`).

**Two gaps closed after an advisor review of the above** (all the checks
up to here only read the OAM *shadow buffer*/`OopObjRam`, which cannot by
itself prove either sprite reaches real hardware, or that Entity #1 isn't
silently starved of stream slots by the Phase 0 gate):

- **Hardware OAM, not just the shadow buffer**: `snesSpriteRam` (Mesen2
  MCP memory type — not `snesOam`/`spriteRam`/`oamRam`, none of which
  exist) at offset 0 reads `[120, 150, 0, 48, 40, 150, 4, 50]` — both
  sprites' bytes are genuinely present in hardware OAM, not just staged.
  `Oam_HighWaterSlot` is 8 (grew past the old single-entity value, so the
  upload actually covers both slots), and the hardware hi-table's first
  byte is `$0A` = `0b00001010`, i.e. both sprite 0's and sprite 1's 2-bit
  hi-fields correctly carry the "large" size bit — matches
  `OamSetSprite_Hi=$02` packed for each.
- **Entity #1 isn't stream-starved**: sampled Entity #1's `CHAR_FRAME_INDEX`
  (`$7E0a00 + 33 + 9`, its DP offset 9 inside its own window) every 40
  frames across 320 frames: `[4, 0, 2, 4, 0, 1, 3, 5]` — genuinely cycling
  through its 0-5 idle frame range, not frozen. Confirms it isn't losing
  every arbitration race under the Phase 0 `Msu1_StreamBusy` gate (the
  exact starvation failure mode that gate's own header comment warns
  about for a naive implementation).

**One gate substituted for a weaker check, noted honestly rather than
silently**: plan.md's Phase 2 gate asks for a byte-level comparison of
each entity's rendered VRAM tile data against its *known baked frame
bytes* (`out/<name>_idle/frameNN.bin`). The raw `.bin` files are 1536
bytes, not the 768 `ANIM_FRAME_BYTES` the runtime streams — an unexplained
converter-format difference not reverse-engineered this session. What was
actually verified instead: Entity #1's VRAM bytes are real (non-zero) and
differ from Entity #0's at the correct per-column offset, which rules out
the specific cross-entity-overwrite bug this project has hit before (see
Phase 0), but does **not** independently confirm the bytes are JHUN's
*correct* pixel data byte-for-byte. If that stronger check is ever needed,
start by understanding `tools/bor_converter/convert_character.py`'s output
format before assuming the 768-byte runtime layout applies directly.

## Phase 3 done and verified: minimal AI

Per `SNES-BOR-Engine-Prompt.md` §6.2 ("Enemies walk toward player. When
within 30 pixels, play punch animation. No damage system for PoC.") and
plan.md's Phase 3 section. Repurposed Entity #1 (Phase 2's static NPC)
rather than adding a third entity — plan.md explicitly allowed either.

`CHAR_INPUT_DRIVEN=2` is now a real third mode ("AI seek"), alongside 0
(static) and 1 (player dpad). `CharacterEntity_Init`'s role-1 branch now
sets `CHAR_INPUT_DRIVEN=2` instead of 0 (was "static NPC", is now
"AI-seeking NPC" — same palette/tile-column/starting position as Phase 2,
just no longer idle-only).

- **`Anim_Play`**: `CHAR_INPUT_DRIVEN` is now checked before reading any
  real controller state at all — a real gap Phase 2 left open (nothing
  gated animation-*selection* on the flag, only Character_PlayFrame's
  *position* code did; harmless while Entity #1 was mode 0/idle-only, but
  would have let real player button presses drive a mode-2 AI entity's
  `CHAR_SELECTED` too). Mode 0 forces idle. Mode 1 is the original
  button-driven logic, unchanged (renamed into its own
  `Anim_Play__player_input` block). Mode 2 computes exact per-axis
  unsigned distance to `PlayerEntity_PosX/Y` (`$7E0a00+4/+6` — Entity #0's
  fixed window, "player is always slot 0" per plan.md, since Entity #0 is
  always created first and never deleted) via a compare-then-subtract-the-
  right-way idiom (correct across the full 0-255 range, no two's-
  complement wraparound approximation), and sets `CHAR_SELECTED=2`
  (attack, reusing the same trigger shape as the button-driven path) once
  within `ANIM_AI_ATTACK_RANGE=30` on *both* axes, else routes into the
  existing `Anim_Play__want_got` walk/idle dispatch with want=1.
- **`Character_PlayFrame`**: mode 2's X/Y blocks reuse the existing
  `__left`/`__right`/`__up`/`__down` PLAYER_SPEED-stepped, clamped movement
  labels (no new movement math), branching into them based on which side
  of `PlayerEntity_PosX/Y` this entity is on.

**One real bug found and fixed via live Mesen2 testing, not by any static
check**: the first version gated "hold instead of walking into the player
mid-punch" on `CHAR_SELECTED==2`, read in `Character_PlayFrame` right
after `Anim_Play` runs in the same frame. `Anim_Play_Attack` reverts
`CHAR_SELECTED` to 0 on the exact frame an attack animation finishes,
*before* `Anim_Play`'s own AI-seek logic gets a chance to re-evaluate
distance and re-trigger it back to 2 (that only happens next frame) —
`Character_PlayFrame` running in between saw the transient 0 and let one
frame of movement through per attack cycle. Observed directly: X crept
from 94 toward the player by ~2px every ~40-50 frames over several hundred
frames despite `CHAR_SELECTED` reading 2 at every sampled 30-frame
checkpoint (the leak was faster than the sampling interval could normally
catch — found by sampling frequently enough, not by reasoning about the
code). Fixed by recomputing the same distance check directly in
`Character_PlayFrame` instead of trusting `CHAR_SELECTED`'s momentarily
stale value — no longer racy since it doesn't depend on `Anim_Play`'s
internal state-machine transition timing.

**A second discovery, structural rather than a bug**: the standard
`rom_audit` invocation (`FC00 FF20 FF30 8000`, the four literal-JSR-
reachable boot entries) has **never actually covered any code reached
through `Core_Oop_Play`'s indirect dispatch** — `Anim_Play`,
`Character_PlayFrame`, `CharacterEntity_Init/Play`, `Anim_LoadCharacter`,
`Msu1_LoadFrame`, all of it — because it's only called via `jsr
(OopCurrent,x)`/`jsr (ClassInit,x)`, a runtime-computed indirect jump the
static recursive-descent walker cannot follow (this matches
`audit_jumps.py`'s own documented "indirect forms aren't statically
resolvable" limitation, just not one anyone had noticed applied to
*this much* of the codebase). Confirmed directly: `audit_jumps.py src/
main.bin FC00 FF20 FF30 8000` decoded exactly 1906 instructions/250 edges
both immediately before and immediately after this phase's substantial
new code, unchanged to the byte, because none of the new branches were
ever walked at all — not because they were correct, but because they were
invisible to that specific invocation. **The standard 4-entry-point audit
has been silently vacuous for all Phase 1b/2/3 code this whole time; every
prior phase's "all 3 rom_audit tools clean" claim only ever validated
`scpu_boot`/boot-time code, never the per-frame entity logic.** Real
coverage requires re-seeding both `audit_jumps.py` and
`audit_ownership.py` from the actual indirectly-dispatched routines'
addresses directly, e.g.:
```
python tools/rom_audit/audit_jumps.py src/main.bin <Anim_Play addr> <Character_PlayFrame addr> <CharacterEntity_Init addr> <CharacterEntity_Play addr>
python tools/rom_audit/audit_ownership.py src/main.bin src/main.sym <same four addrs>
```
(addresses come from `src/main.sym`, they move every build). Doing this
for the current build: 441 instructions/92 edges (jumps), 434 labels/441
instructions/92 edges/11 CALL-class edges (ownership), **0 suspicious, 0
violations** — confirms all of Phase 3's new branches are correctly
encoded, not just unreachable-and-therefore-silent. **Use the
Oop-seeded form, not just the standard 4-entry form, for any future
change inside `Core_Oop_Play`-dispatched code** — the standard form isn't
wrong, it's just checking a different, much smaller slice of the ROM than
it looks like it's checking.

Verified: build clean; standard rom_audit (419-434-ish labels, always 0
drifted) *and* the Oop-seeded jumps/ownership audits both clean; isolated
AI behavior in Mesen2 — Entity #1 walks 40→60→80→90 (X) over the first ~40
frames, `CHAR_SELECTED` transitions 0(idle)→1(walk)→2(attack) exactly when
X reaches 90 (30px from the player's default 120), then holds firmly at
90 with no further creep across 300+ sampled frames (3/3 runs); moving the
player away (Right-held to X=216) and re-sampling confirms Entity #1
resumes walking and re-converges to hold exactly 30px away (186) — dynamic
re-engagement works, not just a one-shot initial approach; hardware
`snesSpriteRam` confirms both sprites' bytes correct after 720 frames of
concurrent AI movement + player movement + streaming; `Msu1_StreamBusy`
still correctly drains to 0 (no Phase 0 regression); player remains fully,
independently controllable throughout (Down-held still clamps Y at 208).

All of the above tests moved the player to the right of / away from
Entity #1 (default X=90 vs. player 120/216), which only ever exercises the
`playerge` arm of `Character_PlayFrame__ai_x`/`__ai_y` (the `bcs`-taken
branch). The mirrored arm — player X/Y *less than* the entity's, taken when
the player crosses to the entity's other side — was untested by any of the
above. Closed this gap: held Left until the player clamped at X=8 (entity
still at its converged X=90), then sampled Entity #1's X across 300 frames.
It converges to exactly 38 (8+30, the correct hold distance on the other
side) and holds with zero creep across all 10 sampled checkpoints;
`CHAR_FACING_LEFT` correctly reads 1 (facing the player) throughout. The
untested arm is correct — no swapped operand, no wrong branch target.

**Next**: Phase 4 onward are roadmap-level only in plan.md (damage/health,
more enemies, the rest of the original spec's control scheme). Read
plan.md's "Phase 4 onward" section and re-derive specifics against the
code as it exists by the time you get there — don't assume Phase 1-3's
exact shape carries forward unchanged.

## Phase 4 done and verified: collision + hit reaction

plan.md's Phase 4 ("collision + hit reaction... AABB-only, no HP/damage
tracking", matching SNES-BOR-Engine-Prompt.md's PoC scope). No hit/fall
animation data exists in the MSU roster format (only idle/walk/attack are
converted, confirmed by checking `tools/bor_converter/pack_msu_roster.py`
and `out/jhun_*`/`out/ralf_*` — matches plan.md's explicit "reuse an
existing animation state" allowance), so the visible "hit reaction" is:
force the target back to idle (reusing that animation, same as an attack's
own revert-to-idle) and freeze its movement for `CHAR_HIT_STUN_FRAMES`=24
frames (~0.4s @ 60Hz).

New per-entity DP fields: `CHAR_HIT_STUN` (offset 33, frames remaining,
0=not stunned) and `CHAR_HIT_APPLIED` (offset 34, latches once per attack
cycle so a multi-frame attack animation registers at most one hit).
`CHAR_ZP_LEN` bumped 33->35. Both fields start zeroed for free —
`Core_Oop__ClearObjRam` already zeroes an object's whole window before
`Init` runs, confirmed by reading `core/oop.pasm`.

Hitbox is just each entity's full 32x64 sprite box (no separate, narrower
attack-hitbox data exists — matches "AABB-only, no pixel-perfect"). A hit
registers the instant the attacker's `CHAR_SELECTED` reaches 2, not on some
later "active" sub-frame of the swing (no per-frame hit-window data
exists) — at `ANIM_AI_ATTACK_RANGE`=30 the two 32px boxes already overlap
by 2px the moment the AI decides to attack, so this doesn't need a "walk
closer" phase to look reasonable.

Same "player is always slot 0" shortcut as Phase 3, extended: `Entity1_
Base`/`Entity1_PosX`/`Entity1_PosY`/`Entity1_HitStun` are fixed absolute
addresses at `$7E0a00 + 35` (Entity #1's window immediately follows Entity
#0's — `core/oop.pasm`'s bump allocator places objects back-to-back in
creation order, and `msu1_done` creates Entity #0 then Entity #1) plus
that offset's own field offsets. Written as literal `35`, not a
`CHAR_ZP_LEN` reference — Poppy's constant evaluator is single-pass/
forward-reference-intolerant, confirmed via a real "Cannot evaluate
operand" build error when this first used the symbol (`CHAR_ZP_LEN` isn't
defined until later in the file). **Must be kept in sync by hand if
`CHAR_ZP_LEN` ever changes again.** `Character_HitApply` (called from
`CharacterEntity_Play`, after `Anim_Play`/`Character_PlayFrame` so
`CHAR_SELECTED` reflects this frame's real state) picks which fixed
address to check against via `CHAR_INPUT_DRIVEN` (1=player, other is
Entity #1; 2=AI, other is the player) — fine for exactly 2 entities;
Phase 5 (3-4 entities) will need a real per-attacker "who did I hit" loop
instead of one hardcoded other-entity address per side.

**Two real bugs found and fixed, both via live Mesen2 testing, both the
same underlying Poppy issue (bug #10, already documented elsewhere in this
file for `Anim_Play__loaded`/`Anim_LoadCharacter__msu_ok`) hitting new
code in two different shapes:**

1. First cut of `Character_HitApply` was one long block with `bcs
   <label ~130 bytes away>` branches. Poppy assembled this with **no
   build error** but produced a genuinely wrong jump target at runtime —
   confirmed via Mesen2: the instant the AI's first attack made
   `CHAR_SELECTED` reach 2 and this code ran its overlap test for the
   first time, WRAM state froze completely, including
   `Nmi_FrameCounter` itself (a full CPU hang, not just a stuck game
   loop). Fixed by restructuring into a tiny dispatcher (`Character_
   HitApply`) plus two short leaf routines (`Character_HitApply_
   VsEntity1`/`VsPlayer`, called via `jsr`) so every relative branch is
   local/short — sidesteps the whole class of bug rather than hand-tuning
   one more `brl` distance.
2. Even after that restructuring, the hit never actually registered
   (`CHAR_HIT_APPLIED` stayed 0 forever, `CHAR_HIT_STUN` never got
   stamped) even though positions clearly overlapped. Root cause: `Character_
   HitApply__attacking`'s label is reached via a `beq` that jumps AROUND
   an earlier `rep #$31`/`.a16`/`.i16` — so the CPU is still 8-bit there
   at runtime, but Poppy's linear (non-control-flow-aware) width tracker
   had already "seen" that `rep` textually and mis-sized the following
   `cmp #1` as a 3-byte 16-bit form the real 8-bit CPU only half-consumed,
   producing a phantom `BRK #$F0` and corrupting every byte after it in
   the routine (confirmed via Mesen2's own disassembler showing exactly
   that garbage, and via `Character_HitApply_VsEntity1`'s symbol address
   landing mid-instruction in the real ROM). Exact same bug shape as the
   `Anim_Play__loaded`/`Anim_LoadCharacter__msu_ok` comments already in
   this file describe — just newly triggered by this phase's code. Fixed
   with the same medicine: an explicit (runtime-no-op) `sep #$20`/`.a8`
   re-sync right after the label, plus proactively at the top of both leaf
   routines too (they're textually placed after another `rep #$31` inside
   the dispatcher, so are equally exposed).

**Lesson for future phases**: this is now the *third* independent time
this exact bug shape (branch jumps around a `rep`, Poppy's linear tracker
doesn't know, next immediate gets corrupted) has bitten new code in this
file. Any branch that jumps around a `rep #$31`/`.a16`/`.i16` needs an
explicit re-sync `sep #$20`/`.a8` (or `rep`, if the target context is
16-bit) at its landing label — check for this pattern on sight rather than
waiting to hit it again. `rom_audit`'s tools do **not** catch this class of
bug (confirmed: `audit_jumps.py`/`audit_ownership.py` gave byte-identical
clean results before and after the first, still-broken restructuring —
they only validate that decoded bytes land on real instruction/label
boundaries, not that program logic does the right thing at runtime).

Verified in Mesen2 (majority-of-3+ runs, hardware `snesSpriteRam` + WRAM
reads): both directions of hit-stun work — Entity #1 attacking the
stationary player stuns it (`CHAR_HIT_STUN` jumps to 24, counts down,
`CHAR_HIT_APPLIED` latches to 1 and doesn't re-fire until the attack cycle
ends); walking the player back into Entity #1 and pressing the attack
button stuns Entity #1 the same way; both entities alternate landing hits
repeatedly in sustained close combat without ever re-freezing (confirming
`CHAR_HIT_APPLIED`'s per-cycle reset works over many cycles, not just
once). Stun correctly freezes both animation (forced back to idle) and
movement (position holds), and both resume normal behavior the instant the
countdown reaches 0. Regression-checked: hardware OAM both sprites correct
after 700 concurrent frames, `Msu1_StreamBusy` still drains to 0 (no
Phase 0 regression), player remains independently controllable throughout.

**Next**: Phase 5 — scale to 3-4 total enemies (plan.md). The "player is
always slot 0" and "fixed Entity #1 address" shortcuts above will both
need to become a real per-attacker loop over however many entities exist,
not one hardcoded other-entity address per side — read plan.md's Phase 5
section and re-derive against the code as it exists by then.

## Phase 5 done and verified: scale from 2 to 4 entities

Before starting, built the two tools plan.md Part Two's section 2.2
required first: `tools/rom_audit/audit_all.py` (re-seeds `audit_jumps.py`/
`audit_ownership.py` by name, read from `main.sym`, so oop-dispatched code
is actually covered — the standard 4 boot seeds never reach anything
dispatched through `core/oop.pasm`'s indirect `jsr (ClassPlay,x)`; also
asserts `Entity1/2/3_Base` stay in sync with `CHAR_ZP_LEN` and that
`scpu_main_loop`'s margin before `nmi_handler` stays positive) and
`tools/verify/_harness.py` (shared conventions for committed Mesen2 test
scripts — worktree-safe ROM path, >=32-byte reads, majority-of-3). Both
committed separately before touching any entity code.

**The corrected OBJ tile-sheet arithmetic** (see plan.md §2.3): the sheet
holds 8 of these 32x64 sprites, not 4 — 256 tiles ÷ 32 tiles/sprite, and
the next VRAM occupant (BG2 tilemap) sits well clear at word `$5C00`. This
phase's 4-entity target needed zero VRAM layout changes as a result — no
OBSEL touch, no second tile bank, just widening the existing per-instance
`CHAR_TILE_COLUMN`/`CHAR_PALETTE_SLOT` pattern to slices 0-3.

**Design decision, made explicit before writing any code (confirmed twice
with a second opinion, since the first pass got it wrong): fixed
`EntityN_Base` literals for N=0-3, not a runtime "compute base from slot
number" routine.** `Character_HitApply` never needs to know its own slot —
it always runs inside the dispatched instance's own DP window — only the
*target's* address, and both directions are compile-time-known: the
player (mode 1) always tests against slots 1/2/3, the AI (mode 2) always
tests against slot 0. So `Entity2_Base`/`Entity3_Base` are two more hand-
written literals in the same style `Entity1_Base` already used, generizing
the pattern rather than replacing it — genuinely simpler AND safer than
runtime indexed addressing, which has its own confirmed Poppy traps (the
`.l Symbol,y` ban).

**Ten code changes, in order:**
1. Added `Entity2_Base`/`Entity3_Base` (literals `70`/`105` = `2*CHAR_ZP_LEN`/
   `3*CHAR_ZP_LEN`) alongside the existing `Entity1_Base`. `audit_all.py`'s
   sync check extended to all three.
2. `Character_HitApply`'s dispatcher: mode 1 (player) now calls THREE
   `jsr`'d leaves in sequence (`VsEntity1`/`VsEntity2`/`VsEntity3`), not
   one. Deliberately three separate leaves, not one parameterized-by-
   register routine or three inlined copies — inlining three ~70-byte
   copies risks a shared `__done` branch exceeding ±127 bytes, which
   **assembles with no error and hangs the CPU** (Phase 4's own bug,
   still fresh). `Character_HitApply_VsEntity2`/`VsEntity3` are copy-
   shaped leaves off `VsEntity1`, each with its own `sep #$20`/`.a8`
   re-sync at entry (rule 1 — every one of these leaves is textually
   downstream of an earlier `rep`).
3. `CharacterEntity_Init` extended from a 2-way (`beq`/fallthrough) branch
   to an explicit 4-way `cmp`/`beq` chain for roles 0-3. **Found and fixed
   a documentation bug of my own while writing this**: `CHAR_TILE_COLUMN`
   is a *slice index* (0-3), not a raw hardware tile-column number —
   `Character_PlayFrame` multiplies it by 4 to get the real base tile.
   plan.md's Part Two originally said "assign 0, 4, 8, 12"; that was
   wrong and would have double-applied the ×4. Fixed in plan.md before it
   could mislead anyone executing this later. Roles 1-3 spawn at
   non-overlapping 32x64 boxes (checked by hand and by the gate below).
4. `msu1_done` now creates 4 entities (roles 0-3; role 2 reuses roster 0/
   Ralf, role 3 reuses roster 1/JHUN — only 2 characters exist, so "4
   entities" is necessarily "2 Ralfs + 2 JHUNs").
5. `Character_BlankPadding` — **fixed a live, confirmed bug**, not just
   generalized it. It only ever blanked tile-column-slice 0 (hardcoded
   `$4600`/`$4700`); every other slice's unused rows 6-7 showed whatever
   was last in that VRAM region. Confirmed in Mesen2 BEFORE this fix, 3/3
   fresh sessions: slice 0's padding read 0/128 nonzero, slice 1's read
   124-128/128 nonzero with **different garbage bytes on every run**
   (power-on VRAM randomness, never written) — meaning Entity #1 had been
   shipping with garbage in the bottom 16 pixels of its sprite since
   Phase 2, unnoticed. Fixed by fully unrolling all 4 slices as compile-
   time-constant word addresses (no runtime indexing at all, since this
   is one-shot boot code with no performance requirement — sidesteps this
   project's indexed-addressing Poppy traps entirely).
6. Select-button reselect gated to `CHAR_INPUT_DRIVEN==1` (the player)
   only — `CharSelect_Index` is a single global cell, so letting every AI
   react to Select too would desync all of them together.

**An eleventh change, NOT in the original 10-step plan — found only
because the gate's own assertions caught it**: the CGRAM palette-DMA
queue hazard. `Anim_LoadCharacter` streams each character's palette into
ONE SHARED WRAM buffer (`AnimPaletteStaging`, fixed at `$7E2300`) and only
*enqueues* a DMA request referencing that buffer's address — the real
hardware DMA doesn't fire until `Core_Dma_ProcessQueue` runs. The old code
called `ProcessQueue` exactly once, after all entity creates finished.
With exactly 2 entities (this project's entire history before this
phase), that always looked correct by coincidence: the LAST entity loaded
was always also the one whose real data was still sitting in the shared
buffer when the single flush ran. That coincidence breaks at 3+ entities:
confirmed in Mesen2 that CGRAM slots 1 and 2 (JHUN role-1, Ralf role-2)
both ended up holding role-3's (the *last* load's) palette instead of
their own, while only slot 0 (flushed via a stale assumption that
happened to still hold correct data at the time) looked right. **Fixed**
by moving the `Core_Dma_ProcessQueue` call to run immediately after EACH
entity's `Core_Oop_Create`, not once at the end — confirmed safe since
forced blank is continuously active from before `msu1_done` runs through
the explicit "PPU init" section afterward (nothing re-enables the screen
in between), the same justification the original single end-of-routine
call already relied on. Verified via a direct byte comparison against
`bor.msu`'s own raw palette bytes (ground truth, not just cross-entity
equality) — after the fix, entities 1/2/3's CGRAM colors 2-15 all match
`bor.msu`'s ground-truth bytes exactly.

**A twelfth finding — found real, then root-caused and FIXED (same
session, after a second pass)**: entity 0 (the player)'s own CGRAM color 1
(bytes 2-3 of its 32-byte palette) read wrong, 100% reproducibly, confirmed
against `bor.msu`'s raw bytes as ground truth (observed `$001F`, ground
truth `$537F`). This was **NOT an MSU-1/track-select timing hazard** —
that theory was live for a while (see the now-corrected
`msu-track-select-seek-ordering-risk` project memory) but was wrong. The
actual cause: `TestSprite_Init` (`src/main.pasm`, a leftover one-time OAM
bring-up routine from early Phase 0/1, called from `scpu_boot` after
`Core_Oam_Init`, which runs *after* `msu1_done`'s real `Anim_LoadCharacter`
calls) unconditionally writes CGRAM colors 128/129 with hardcoded
black/red test values via direct `$2121`/`$2122` stores — and colors
128/129 are OBJ palette 0, colors 0/1, which is exactly `CHAR_PALETTE_SLOT
= 0`, the real player entity's palette. `$001F` (pure red) was
`TestSprite_Init`'s own literal test color, not corrupted MSU-1 data —
the "wrong" observed value was a second, later, unrelated write landing on
top of the first, correct one. Only entity 0 was ever affected because no
other entity uses palette 0. **Fixed**: moved `TestSprite_Init`'s CGRAM
writes off palette 0 onto palette 4 (colors 192/193 — unused by any
`CharacterEntity`, which only use palettes 0-3), and updated its OAM
attribute byte from `$30` (palette 0) to `$38` (palette 4) to match.
Re-verified: CGRAM `$100`-`$101` (slot 0, color 1) now reads `$537F`,
byte-exact against `bor.msu` bytes 146-147. `tools/verify/phase5.py`'s
colors-2-15-only carve-out and "KNOWN BUG (not blocking)" check line are
now stale (the bug they worked around no longer exists) but were left in
place as a passing regression check rather than removed, since they cost
nothing and would catch a recurrence.

**Verification, in order**: `python build_rom.py` (clean) →
`python tools/rom_audit/audit_all.py` (both seed sets clean, 0 suspicious
edges, 0 ownership violations, `Entity1/2/3_Base` all in sync,
`scpu_main_loop` margin 126 bytes positive) →
`python tools/verify/phase5.py`, twice, both `PHASE 5: PASS` — asserts,
among other things: all 4 entities have distinct spawn-time positions in
both `OopObjRam` and hardware `snesSpriteRam`; all 4 tile-column slices'
padding rows are confirmed zero (the bug from point 5 above, re-verified
fixed); all 4 CGRAM palette slots are written and pair-equal as expected;
each entity's `CHAR_FRAME_INDEX` varies across a 240-frame, 6-sample
window (proving `Msu1_StreamBusy`'s round-robin doesn't starve any of the
4); `Nmi_FrameCounter` still advances after 700 concurrent frames (no
vblank overrun with 4 entities streaming/moving/colliding at once); the
player's `CHAR_HIT_STUN` goes nonzero from an AI attack, majority-of-3.

**Next**: Phase 6 — done, see the next section.

## Phase 6 done and verified: BG1 backdrop + BG3 HUD

plan.md §2.4's hand-back gate ("no level-tileset converter exists; STOP")
was hit and then **resolved by designing the converter with the user**,
not by guessing at the three things §2.4 refused to specify. The answers:

- **Source format** — composite a real BOR level. Level `.txt` files are a
  flat keyword list (`background`, `panel` ×N, `frontpanel`, `order`)
  laying panels side by side left-to-right. Because the backdrop is static
  and non-scrolling, only the screen at scroll 0 is ever built: no
  parallax rates, no z-order beyond back/panel/front. §2.4's warning that
  this was "a multi-session project in its own right" was wrong.
- **Dedup** — exact match plus H/V flip variants, since the tilemap has
  flip bits for free. Measured 896 → 429 tiles on the shipped scene.
- **Palette** — k-means tile-aware sub-palette assignment. The user
  pointed at `tiledpalettequant.py` in the sibling SNES-SuperMonkeyIsland
  repo, which solved this exact problem; it and four dedup/packing helpers
  from that project's `snes_room_converter.py` were vendored rather than
  rewritten.

**One function was deliberately NOT vendored**: that project's
`encode_tilemap_word` emits a *custom WRAM* format (11-bit tile id,
palette at bits 11–13, no priority bit) which its engine remaps at
VRAM-write time. We write VRAM directly, so ours emits real hardware
layout (10-bit id, palette at 10–12, priority at 13). Copying it verbatim
would have produced a silently garbled tilemap.

**What shipped**: `tools/bg_converter/` (`level_parse` → `composite_scene`
→ `convert_bg`, plus `make_hud_tiles` which generates the 2bpp HUD tiles
procedurally so no new art asset is needed); `bor.msu` format v2 with a BG
section appended after the character blobs (no character `data_offset`
moves); `Bg_LoadScene`; `CHAR_HP`; `Hud_Play`. Shipped scene is 6BEASY,
the boss throne room, 429 tiles.

**Three constraints found by building, all of which would have burned a
future session:**

1. **BG3's 2bpp palettes overlap BG1's 4bpp ones.** A BG3 tile with
   palette field p reads CGRAM `p*4..p*4+3`; BG1 reads `p*16..p*16+15`.
   The backdrop therefore quantizes to **7** sub-palettes shifted to slots
   1–7, reserving CGRAM sub-palette 0 for the HUD. Without this the HUD's
   colors would silently be whatever the backdrop wrote into CGRAM 0–3.
2. **`cpx.l` does not exist.** CPX has no long addressing mode on the
   65816. Poppy assembled it with no error and emitted an encoding that
   desynced the instruction stream and scribbled over CGRAM — the same
   silent-invalid-addressing class as the documented `stz.l` and `.l,y`
   traps. Both streaming loops now count DOWN in X, needing no memory
   operand. **Add this to the list of Poppy addressing modes to never
   trust.**
3. **`$2115` (VMAIN) was still 0 inside `Bg_LoadScene`.** It runs from
   `msu1_done`, earlier in `scpu_boot` than the `$2115` write the rest of
   the boot VRAM code depends on, and the `$2100`–`$213F` clear loop had
   already zeroed it. VRAM addresses advanced on the `$2118` write instead
   of `$2119`, shearing every upload by one byte. Now set locally rather
   than depending on call-site ordering.

Both #2 and #3 presented as "CGRAM is fine but all three VRAM regions
mismatch," and were only visible because the gate byte-compares against
the converter's own output. A check that asked "does VRAM look plausible"
would have passed.

**A claim I made and then had to retract**: the 512-tile BG1 cap is *not*
caused by the SA-1 compositor rewriting `$2000`–`$3F7F` every frame.
`Scpu_CcdmaPump` is defined in `main.pasm` but **never called** — the main
loop dropped it when characters moved to real OAM sprites. The real cause
is that BG1 tile N sits at word N*16, so tile 512 lands on word `$2000`
where `scpu_boot` writes BG2's blank tile. **Dropping that one boot write
raises the ceiling to 1024**, which fits every stock BOR level and is both
the 10-bit tilemap index limit and exactly where OBJ tiles begin at
`$4000`; BG2 is not on the main screen so nothing it points at is visible.
Not done here — the shipped scene fits in 429 tiles and there was no
reason to edit verified boot code for headroom it doesn't need.

**Verification**: `python build_rom.py` clean →
`tools/rom_audit/audit_all.py` ALL CHECKS PASS (the `EntityN_Base` sync
check confirmed the 36/72/108 literals after `CHAR_ZP_LEN` grew) →
`tools/bor_converter/verify_msu_roster.py` all 3 checks pass →
`tools/verify/phase6.py` **PHASE 6: PASS** (25 assertions) →
`tools/verify/phase5.py` **PHASE 5: PASS** (no regression).

**Two brittle assertions in phase5.py were fixed, both of which had been
passing for the wrong reasons:**

- It point-sampled the *oscillating* `CHAR_HIT_STUN` at exactly frame 600.
  Phase 6 shifted boot timing enough to move frame 600 into a
  decayed-to-zero gap and it "failed" while collisions were demonstrably
  still landing. Now samples across a window
  (`[0,20,13,5,0,5,4,20]`) and asserts nonzero at least once.
- It hardcoded the entity bases as `+35/+70/+105` and silently began
  reading entities 1–3 at wrong addresses the moment `CHAR_ZP_LEN` grew to
  36 — the assertions still ran, they just examined the wrong memory.
  `_harness.py` now has `pasm_constant()`, which parses values out of
  `src/main.pasm`. **Verification scripts in this project must never
  hardcode engine layout values.**

**Still open, unchanged**: the OAM hi-table X-high bit is still unexercised
(`PLAYER_MAX_X=216` means nothing crosses X=255).

**Next**: Phase 7 (audio polish) — **gate evaluated, and it FAILS. Phase 7
is blocked.** See the next section.

## Phase 7 gate: RESOLVED — audio plays (see the RESOLUTION section below)

plan.md §2.5's step 1 says to confirm a song actually plays before wiring
a punch SFX, and to STOP and hand back if it does not. It does not.

**What was checked** (2026-08-09, on the Phase 6 ROM):

- `soundwork/tad/build/audio-data.bin` is **4183 bytes** — non-trivial, so
  there is real content. It is `.incbin`'d at `main.pasm:2192`.
- `TadPrivate_state` (`$7E0032`) reads **`$7F`** at frames 120, 300 and 600
  — i.e. steady across ~10 seconds of emulated time. Per `main.pasm`'s own
  `TadState` enum that value is **`LOADING_SONG_DATA_PLAY`**: the driver
  accepted the song and set the play flag, but the load never completes.
  It never reaches `PLAYING` (`$82`). `Tad_flags` = `$40`,
  `TadPrivate_nextSong` = `0`.
- The S-DSP is still in **reset + mute**: `flg` = `$E0` (bit7 reset, bit6
  mute, bit5 echo-disable). All 8 voices read `envelope: 0` and
  `currentOutput: 0`, and their pitch/sampleSrc/adsr registers hold
  incoherent power-on garbage rather than song state. `voicesEnded: 0`.
- The SPC700 *is* executing (PC ~574-578, cycle counter advancing
  4.0M → 10.2M → 20.5M), so this is not a hung CPU — it is sitting in a
  loop waiting for a transfer that never finishes.

**Why the "~40% false-silent" caveat does not apply here.** §2.5 warns
that the Mesen2 *audio-capture* check is unreliable and needs
majority-of-3. This finding does not rest on audio capture at all — it is
direct engine and DSP state, identical across three sample points in one
run. It is also unambiguous in a way a waveform check could not be: the
ROM *does* emit sound via MSU-1 (verified in an earlier phase), so a
non-silent recording would prove nothing about TAD. Reading
`TadPrivate_state` and the DSP `flg`/voice envelopes is what actually
discriminates the two paths.

**Not debugged further, deliberately** — §2.5 explicitly says not to
attempt to author audio content or debug the TAD driver from that
document, and the failure is in the song-load handshake, which is exactly
the driver internals it rules out. Whoever picks this up starts here:
`TadPrivate_state` stuck at `$7F` means `Tad_Process`/
`Tad_FinishLoadingData` (both called every frame from `scpu_main_loop`)
are not driving the song transfer to completion. The boot handshake
itself is fine — reaching `$7F` at all proves `Tad_Init` succeeded and the
loader accepted a song.

### RESOLUTION (same day, after the user explicitly authorized debugging the driver)

`tools/verify/phase7.py` now reports **PHASE 7: PASS**. State reaches
`PLAYING` (`$82`) ~17 frames after reset, `FLG` = `$00` at main volume
127/127, recorded peak amplitude 23082 on 3/3 runs. Phases 5 and 6 still
pass; `audit_all.py` still `ALL CHECKS PASS`.

Everything observed above was accurate. The inference drawn from it --
"the failure is in the song-load handshake, i.e. driver internals" -- was
not. **None of the five bugs were in TAD's logic.** Four were silent Poppy
miscompiles and one was a porting error in this repo's own
`LoadAudioData`:

1. Poppy sizes `jsl <label>` as 3 bytes during address estimation and emits
   4, so every label after a `jsl` resolves one byte early and the error
   accumulates. The TAD region has exactly three `jsl`s, and the drift
   across its 27 broken labels stepped 1 -> 2 -> 3 right after each one.
   Three of those were individually fatal (stray `TXA` corrupting the data
   bank; `Tad_LoadSong`'s state guard reduced to dead code so the common
   audio data never transferred; `TadPrivate_Process_Loading` landing on
   the previous routine's `rtl`, so `Tad_FinishLoadingData` spun forever).
2. Poppy silently deletes a branch whose target is a dot-local label.
3. `Tad_DataTable` offsets are relative to the ca65 audio *segment* base,
   but `LoadAudioData` used upstream's LoROM conversion, which only works
   when that segment starts at `$8000` of a bank. This blob is `.incbin`'d
   mid-bank at `$B02B`, so every address came out `$302B` low and the
   loader transferred **zeros**. Correct base is
   `__Tad_AudioData_0 - 51` (that segment opens with the 51-byte
   `LoadAudioData` callback).

**The lesson worth carrying forward:** the DSP/state readings quoted above
were treated as proof the driver was mid-handshake. They were equally
consistent with a driver that had successfully loaded nothing. Once the
label drift was fixed, TAD reported `PLAYING` with the DSP out of reset at
full volume **and still emitted pure silence** for exactly that reason.
Engine-visible status bytes could not tell those apart; only byte-comparing
the ROM the loader was pointed at against `audio-data.bin` could.

`tools/rom_audit/check_label_drift.py` was added to find bug 1 class
mechanically. Note the pre-existing `rom_audit` checks cannot: they verify
a branch target lands on a valid instruction boundary, and a drifted label
usually does -- just the wrong instruction.

**Recommended next step for Phase 7:** trigger an SFX on attack start. It
needs content first -- `audio-enums.inc` exports only `s02_coin` and a
placeholder `sfx_stub = 0`.

## Phase 8 done and verified: horizontal scrolling (cheap version), commit `5226b59`

Ships the "cheap version" plan.md §2.7 describes as a fallback: the boss
level's real content is 42 unique tiles (well under the 512-tile budget),
so the whole level loads as one static 64x32 `Bg_LoadScene` at boot, with a
real camera panning across it -- no streaming tile cache, no per-frame
column producer. `CHAR_POS_X`/`CHAR_POS_Y` are now real 16-bit world
coordinates everywhere they're read (AI seek, player movement, all four
`Character_HitApply_Vs*` overlap tests, OAM position/X-high derivation).

**The camera itself was mostly dead code before this phase.**
`core/screen.pasm` (576 lines: focus/blur, easing, clamping, playfield
borders) was already called every frame from boot but had zero consumers --
it asks its focused object for `SCREEN_CMD_GET_CAMERA_DATA` via
`Core_Oop_Call` and nothing answered. This phase adds
`CharacterEntity_OnCommand` to answer that, and wires
`Core_Screen_SetPlayfieldBorder` + `Core_Screen_FocusImmediate` on the
player at spawn (`msu1_done`) and a `Screen_PosX -> Nmi_Bg1ScrollX` commit
each frame (`scpu_main_loop`), landing in the real `$210D` (BG1HOFS)
register every vblank via the existing NMI shadow system.

**A genuine WRAM collision bug in `core/oop.pasm` was found and fixed**,
previously latent since nothing had ever written through it:
`OopCall_ResultX`/`OopCall_ResultY`, declared as the last two fields of the
`.enum $7E074A` bookkeeping block, resolved to the exact same addresses as
`OopFlags[0]`/`[1]` (`OopFlags` begins immediately after that enum). The
new camera-query handler writing an entity's position into
`OopCall_ResultX`/`Y` every frame was silently clearing
`OBJ_FLAG_PRESENT` on whichever object occupied slot 1, which
`phase5.py`'s existing frame-index-variance check caught as "entity 0
frozen" (a downstream effect -- slot 1 was the one actually corrupted;
`Core_Oop_Play`'s dispatch loop skipping a non-present slot is what made it
look like slot 0). Fixed by moving both fields to their own addresses in
the unused WRAM gap between `ClassOnCommand`'s array and `OopObjRam`.

**Verified in Mesen2** (`tools/verify/phase8.py`, 12/12 checks, ground
truth = the converter's own `tiles.bin`/`tilemap.bin` and Mesen's own PPU
decode, not engine WRAM shadows): BG1 tileset/tilemap byte-match, BG1SC
really reports 64-wide mode, holding Right ~840 frames clamps world X at
`WORLD_MAX_X` (296) and `Screen_PosX`/`$210D` at `MAX_SCROLL_X` (79),
holding Left reverses cleanly back to 0/0, `Nmi_FrameCounter` keeps
advancing pinned at both clamps (no vblank overrun despite the extra
per-frame `$210D` write), and a forced write
(`CHAR_POS_X = 400` on an idle entity, the same forced-collision technique
Phase 0 used) confirms the OAM X-high bit sets correctly -- not reachable
via real gameplay in this level, since every AI entity seeks the player and
the camera follows the player, so no entity's screen-relative X naturally
exceeds 255 here.

**Not done:** the general streaming tile-cache half of §2.7 (column
recycling, per-frame tile DMA producer, the MSU-seek-vs-animation-stream
interleave re-verification that depends on it existing). Needed only if a
future level's live content exceeds roughly 500 unique tiles.

**Recommended next step:** SUPERSEDED — the streaming tile cache mentioned
below was built next (see "Phase 9" immediately below). A punch SFX is
still open and unblocked.

## Phase 9 done and verified: streaming BG1 tile cache (built, NOT shipped)
commits `315673b`, `03a8ad7`, `d2c677b`, `1415969`, `cf5332a`, `9bed554`

**Read this bold line before anything else in this section**: this engine
is fully built and verified, but **the shipped ROM does not use it** —
`build_rom.py`'s `BG_SCREENS` still points at the static boss level from
Phase 8, because 588 tiles doesn't need streaming. Everything below was
verified against a synthetic 13,437-tile stress-test level
(`out/bg_warehouse_stream`), never against a real converted BOR level. Full
detail and the exact fix commit messages live in `plan.md` §2.8 (added the
same session as this entry) and the `syncscroll_budget_throughput` project
memory — this section is the short version.

**What it is:** the general case Phase 8 deferred — a level too big to fit
its whole tileset in VRAM at once. `src/core/stream_cache.pasm` is a
ring-buffer VRAM tile-slot cache (1,022 usable slots) with LRU-ish
eviction; `Core_StreamScroll_*` in `main.pasm` extends/repairs a
~40-column camera-relevant resident window each call, streaming
individual tiles from `bor.msu` on cache miss (budgeted at
`STREAM_SCROLL_BUDGET_MAX=6` cache-miss DMAs per call — swept and measured,
see the memory before raising it), and `Core_StreamScroll_ClampCamera`
holds the visible edge at the resolved window's boundary so the camera can
never outrun the resolver and show garbage tiles (a 2-column `Window1` edge
mask is a secondary backstop for a separate, lower-severity staleness
case).

**Four real bugs found and fixed, most recent last:**
1. `TileBuf` double-fetch corruption in the resolver.
2. `CommitColumn` hang + `WorldMaxX` needed to become a dynamic value
   instead of a level-specific constant.
3. A Poppy-fork silent miscompile: a two-term `adc #(A+B)` immediate
   expression assembled to **zero bytes**, silently shrinking the resolved
   window by 35 columns. Dormant for a while (unclamped camera eventually
   exceeded the wrong bound anyway); became a hard permanent freeze the
   moment the camera clamp above made that impossible. Fixed by splitting
   into two single-term `adc`s. **Lesson: don't write multi-term immediate
   expressions in `adc`/`sbc` operands in this codebase — split them.**
4. **`pending_repair` never converging** (fixed last, commit `9bed554`,
   this session). The repair-sweep cursor round-robinned across the
   *entire* retained window, which grows to the VRAM ring's full 64-column
   physical cap — a span whose real distinct-tile count (measured 1,568 on
   the warehouse asset) routinely exceeds the 1,022-slot cache, so
   repairing a far, no-longer-visible column would evict a currently-
   visible one, forever. Fixed by clamping the repair cursor to the
   ~40-column `[DesiredLo, DesiredHi]` camera-relevant window instead
   (provably always a subset of the retained window at the point it's
   read). **This corrects an earlier same-session conclusion** ("self-
   corrects within 1-2 seconds, not worth fixing") that a direct 50-second
   idle-dwell measurement proved wrong — the earlier estimate was
   extrapolated from the repair cursor's cycling *rate*, never from
   actually confirming the pending count dropped over time. Verified after
   the fix: the metric went from oscillating 609-752/1792 to a flat, stable
   623/1792, with the entire live viewport reading 0 pending.

**Verified:** `tools/verify/phase9_syncscroll_test2.py` and
`phase9_stagecolumn_spotcheck.py` PASS against `out/bg_warehouse_stream`
(temporary `BG_SCREENS` swap, reverted after — always check `git diff --
build_rom.py` is empty before committing). Full regression suite
(`check_label_drift.py`, `audit_all.py`, `phase5.py`–`phase8.py`) re-run
green on the shipped boss-level ROM after every fix, most recently
2026-08-15.

**Explicitly open, not fixed this phase:**
- Real-play scroll-lag magnitude under the camera clamp is unmeasured —
  only tested via an artificial WRAM teleport of `PlayerEntity_PosX`, not
  sustained realistic held-dpad input (`set_input` wasn't observed to move
  the camera in that attempt; unresolved whether that's a harness gap or
  real).
- No committed `phase9.py` gate script — the two `phase9_*.py` scripts are
  ad hoc and need the manual config swap above, unlike `phase5.py`–
  `phase8.py` which are self-contained.
- Never exercised against a real converted BOR level, only the synthetic
  stress-test asset.

**Recommended next step: SUPERSEDED, done 2026-08-16.** `build_rom.py` now
ships `out/bg_stage1a` (BOR's real stage 1A, 2,458 tiles, streaming mode)
in place of the static boss level — first real (non-synthetic) content
this engine has ever rendered. Verified clean via a full scripted
traversal (screenshots, no corruption) and both `phase9_*.py` scripts
(generalized to track `BG_SCREENS` instead of hardcoding the warehouse
asset — now genuine ground-truth checks, not just synthetic-asset-only).
No `main.pasm` changes were needed; three test scripts (`phase5.py`,
`phase6.py`, both `phase9_*.py`) needed fixes for assumptions that only
held for a static or synthetic BG. Full detail in `plan.md` §2.8's
"UPDATE" note. `phase8.py` now correctly, expectedly FAILs against the
shipped ROM (it gates the static whole-level path specifically) — not a
regression. Still open: real-play scroll-lag under sustained held-dpad
input (only tested via a scripted position sweep), and there's still no
self-contained `phase9.py` gate. See `plan.md` §2.9 for other candidate
next phases (SFX, roster persistence — none started; the damage system
option there is now done, see the Phase 11 section further down).

## Phase 10: frontpanel foreground layer — DONE (Steps 1, 2a, 2b, 2c, 3, 4 all done and gated)

Found while recapturing README screenshots against the newly-shipped stage
1A (see Phase 9 above): the fence in `scene_scrolled.png` renders *behind*
the characters, not in front of them like real BOR. Root cause and full
design are in `plan.md` §2.10 — short version: this converter bakes
background+panels+frontpanel into one flat static BG1 image, and OBJ
sprites always render above BG1 here, so the frontpanel (meant to occlude
characters) can't. Not a regression from this session — the boss level has
this too, just wasn't visually obvious there.

**Two cheaper fixes were measured and ruled out, don't re-propose without
new numbers**: a bigger static tile budget (846 unique tiles level-wide —
too many, and inflated by tile-phase drift, not real content); BG3
hardware wraparound scroll at the frontpanel's own repeat period (doesn't
work — the 183px-native/146.4px-scaled repeat unit isn't a multiple of 8,
so hardware tile-grid wraparound reproduces the same phase-drift inflation
a periodic BG layer always suffers from here). A pure-OBJ approach was also
ruled out — the art is near full-screen-height, and tiling it from large
sprites risks exceeding the real 34-tiles/scanline hardware limit.

**The approach that fits**: generalize Phase 9's own streaming-cache
mechanism to a second, independent layer on BG3 (2bpp, using the priority
bit the HUD already proves works), sized against the real camera-window
worst case — measured this session at **213 unique tiles in a 40-column
window**, not the misleading 846 whole-level number. `plan.md` §2.10 has
the full step breakdown (converter tooling, a second cache instance,
BG3/HUD coexistence, verification) mirroring how Phase 9 itself was built
incrementally. User explicitly chose "go big, full general solution" over
a cheaper scoped-down version (crop to just the bottom rail band) when
asked — that's why the plan is for the general case, not a quick patch.

**Step 1 (converter tooling) is done and verified offline** —
`tools/bg_converter/convert_frontpanel.py`, run against stage 1A into
`out/fp_stage1a/`. Real measured results (not the estimates above, which
were sizing bounds, not final numbers): **535 unique tiles total, 143
worst-case in any 40-column window** (down from the 213 estimate — even
better than hoped). CGRAM: exactly 9 usable colors as predicted (3 free
BG3 sub-palettes × 3 real colors), and **visually verified** in
`out/fp_stage1a/preview.png` (decoded from the emitted binaries, not the
source render) — fence mesh, posts, "LAP CLAP" signs, and foliage are all
clearly readable at that budget. Also added
`snes_tiles.decode_2bpp_tile` (the missing inverse of the pre-existing
`encode_2bpp_tile`).

**Step 2a (cache allocator) is done and verified in Mesen2.**
`src/core/stream_cache_fp.pasm` — a deliberate near-duplicate of
`stream_cache.pasm`, not a parameterized/shared version (see that file's
own header for why duplication was chosen over cleverness here). 256
usable 2bpp slots, tables at `$7FA000`+/`$7E25A0`+ (grep-confirmed unused).
`Core_StreamCacheFp_Init` runs from `scpu_boot` right after the existing
BG1 call; `Core_StreamCacheFp_Test` exists but is NOT called from boot
(same poisoned-cache reason as BG1's own `Core_StreamCache_Test`) — verify
it via a temporary boot-time call, added/run/removed, same pattern used
here this session: 8 synthetic tile IDs got 8 distinct slots with the
exact expected stride-97 arithmetic, `Tile2Slot`/`Slot2Tile` back-
references consistent. Full regression suite (label-drift, audit_all,
phase5/6/7, both `phase9_*` scripts) re-confirmed green on the real
shipped stage-1A ROM after this addition — this cache exists in the build
now but nothing calls `AllocateSlot` from any real per-frame or boot-time
path yet, so it's inert, zero risk to what's shipped.

**Step 2b (boot-time initial load) is done and verified in Mesen2.**
`Bg_LoadSceneFp_Streaming`/`StageColumnFp_FetchTilePixels` (main.pasm), a
`Bg_LoadScene_Streaming`-equivalent boot-time loader for the FP cache,
called from `scpu_boot` after `scpu_bg3_map`'s tilemap clear. Getting this
working end-to-end surfaced and fixed four real bugs, each caught by
direct Mesen2 ground-truth checks, not assumption — worth reading in full
before touching this code again:

1. **Row-offset double-count**: the tilemap write address originally added
   a `STREAM_FP_TILEMAP_ROW_START` offset on top of the row index, but the
   converter's `tilemap.bin` already encodes the full row range including
   blank rows. Fixed by writing `row*32 + col` directly.
2. **Scratch-cell aliasing with live BG1 runtime state**: the FP loader
   initially reused BG1's `StreamStage_*` scratch cells, which are NOT
   boot-only — `Core_StreamScroll_SeekColumn` depends on them holding
   BG1's own state persistently every frame. Fixed by giving the FP loader
   its own `StreamStageFp_*` cell block.
3. **Boot-ordering clobber**: the FP call site was originally inside
   `Bg_LoadScene` itself, but `scpu_bg3_map`'s unconditional 1024-word BG3
   tilemap clear runs LATER in `scpu_boot`, silently wiping every FP write.
   Fixed by moving the call to after that clear loop.
4. **BG3 CHR-base tilemap-addressing bug** (the one that produced the
   full-screen magenta corruption, found last, after the first three
   fixes still left the screen wrong): the tilemap word's character-number
   field is PPU-relative to `BG3_TILES_VRAM_WORD` ($5000, BG3's real CHR
   base), not to `FP_TILES_VRAM_WORD` ($5100, where this cache physically
   stores its tiles) — writing the bare cache-slot number as the character
   field pointed 32 tiles too early, into/before the HUD's own 12 tiles,
   so every frontpanel tile rendered uninitialized VRAM instead of its own
   data. This is exactly why BG1's equivalent loader "just worked" without
   this correction: BG1's cache tiles happen to start at the same address
   as BG1's own CHR base, so slot == character number there by
   coincidence, an assumption that silently didn't survive the port to
   BG3. Fixed with `FP_TILE_INDEX_BASE = 32` (`= (FP_TILES_VRAM_WORD -
   BG3_TILES_VRAM_WORD) / 8`), added to the slot number before building
   the tilemap word.

A fifth, independent bug was found in the *converter* while chasing the
same magenta symptom: `tiledpalettequant.build_palettes_tileaware`
accepts a `trans_color` parameter but never actually indexes a genuinely
transparent source pixel to palette slot 0 — it only prepends that color
as slot 0 in the *output* palette, then nearest-color-matches every real
pixel (transparent ones included) against the non-zero slots, since its
distance calc explicitly excludes index 0 (`dist[:, :, 0] = np.inf`).
Fine for `convert_bg.py`'s opaque-only use case, silently wrong for
`convert_frontpanel.py`'s transparency-dependent one. Fixed in
`convert_frontpanel.py` with `uniq_indexed[unique_raw == trans_bgr] = 0`
after quantization, forcing raw-transparent pixels back to index 0;
`out/fp_stage1a/` was regenerated (535 tiles / 143-tile worst-case window
unchanged — same shape, corrected pixel data).

**Verified**: a Mesen2 screenshot after all five fixes shows a clean
scene — brick-wall BG1 backdrop, HUD bars, and the chain-link fence with
"LAP CLAP" signage rendering correctly in front of the character sprites,
no magenta or garbage-tile corruption anywhere. Full regression suite
(`check_label_drift.py`, `audit_all.py`, phase5/6/7) green on the rebuilt
ROM. `phase5.py`'s padding-row settle-time check was bumped from 20 to
120 frames total (a second boot-time streaming loader legitimately pushed
the settle point later — confirmed via direct probing, not a regression);
`phase6.py`'s CGRAM ground-truth comparison now merges in the FP
palette's real bytes.

**Step 2c (runtime resolver/repair-sweep) is done and verified in
Mesen2.** `Core_StreamScrollFp_*` (main.pasm) is a twin of BG1's own
`Core_StreamScroll_*`, called from `scpu_main_loop` right after it and
gated the same way (`Msu1_StreamBusy`). One real structural
simplification versus a straight copy: BG3's tilemap is a single 32×32
map exactly the size of one viewport, so there's no room for BG1's
prefetch margin — the window is always exactly the 32 onscreen columns,
and only the 7 real-content rows (21-27, confirmed blank everywhere else
across the full 192-column level) are ever seeked/resolved/committed.
`STREAM_SCROLLFP_BUDGET_MAX=2` (vs. BG1's 6), deliberately conservative
given the DMA-queue-contention risk `plan.md` flags.

Getting this working found three real bugs, all via direct Mesen2
verification:
1. **Missing window-width enforcement** — the tracked window grew
   unbounded (a 143-column scroll left it 175 columns wide against a
   32-column physical ring) because, unlike BG1's 64-col-ring-vs-≤40-col-
   window slack, FP's ring exactly equals its window size, so moving one
   edge must explicitly pull the opposite edge in by the same amount
   every commit.
2. **A chained-ADC carry bug** — produced visible corruption (garbled
   fence/backdrop past the boot window in a scripted scroll test). Adding
   `STREAM_FP_TILEMAP_ROW_START*3` (63) via a second `adc #63` chained onto
   `adc TilemapOffLo` with no `clc` between them does NOT correctly
   propagate a combined carry into the Hi-byte add — the second ADC's
   carry-out reflects only its own overflow, not the true 3-term total's.
   Found via a temporary WRAM probe comparing the actual computed seek
   address against a hand-computed expected one (the Hi byte was silently
   off by 1). Fixed by folding `+63` into the preserved base once, at boot
   capture time, instead of re-adding it every call.
3. **DMA-queue-contention cache corruption** — the subtlest of the three,
   invisible to screenshots and only caught by a targeted pixel-level VRAM
   check. `Core_StreamScrollFp_ResolveRows` (and `Core_StreamScroll_
   ResolveRows`, BG1's own twin — this bug predates Step 2c and is shared,
   not FP-only) called `Core_StreamCache(Fp)_AllocateSlot`, which
   permanently commits the cache's Tile2Slot/Slot2Tile mapping, *before*
   confirming `Core_Dma_Enqueue` would succeed. When the shared 8-slot
   software DMA queue is full that frame (real contention between OAM
   upload, BG1's budget-6 misses, and FP's budget-2 misses), the enqueue
   fails and the resolver bails — but the cache already believes the tile
   lives in that slot, even though its real pixel data was never DMA'd
   there. The next lookup sees a cache hit and never re-fetches:
   permanent, silent corruption until that slot happens to be evicted
   again. Confirmed with a Mesen2 VRAM read comparing a runtime-resolved
   tilemap word's actual physical tile bytes against the converter's own
   `tiles.bin`/`tilemap.bin` ground truth (column-major indexed) — 1 of 32
   sampled columns mismatched before the fix, 0 of 32 (then 0 of 224 across
   all 7 content rows) after. Fixed by adding `Core_Dma_HasFreeSlot`
   (`src/core/dma.pasm`), a non-mutating queue-full check, called as a
   guard before `AllocateSlot` in both resolvers.

**Verified**: a scripted 900-column-right-then-900-column-left scroll
test renders cleanly in both directions (fence stays correctly positioned
in front of characters at every sampled point), `StreamScrollFp_StagedLo/
Hi` stay exactly 32 apart and track the camera throughout, and
`Nmi_FrameCounter` keeps advancing with both resolvers active in the same
frames. After bug 3's fix, a targeted pixel-level VRAM check confirmed
every non-blank tile across all 7 content rows of the resolved window
(224 tiles) matches the converter's ground truth byte-for-byte, and a
fresh post-fix boot screenshot confirms the boot loader (sharing the
`+63`-folded base) still renders correctly too. Full regression suite
green. `scpu_main_loop`-to-`nmi_handler` margin is now 23 bytes (down from
34) — still positive, but watch it.

**Step 3 (BG3 priority + HUD coexistence) is also done** — the priority
bit is set unconditionally by `Core_StreamScrollFp_ResolveRows`, same as
the boot loader; Phase 6's own HUD checks still pass, and the scroll test
never showed any coexistence artifact. Not yet an explicit dedicated
"HUD changes while FP mid-resolve" test, but nothing found suggests a
problem.

**Step 4 (committed verify gate) is also done**: `tools/verify/
phase10_frontpanel.py`, structured like `phase9_syncscroll_test2.py`
(ground truth = the converter's own `tilemap.bin`/`tiles.bin`, Tile2Slot-
consistency invariant, not self-consistency). Checks the boot-time
viewport (224 non-blank entries, 0 mismatches) and the runtime resolver
under a bidirectional-with-reversals scroll sequence (same check against
whatever window results, plus `Nmi_FrameCounter` advancing every step).
Writing it surfaced one more thing worth knowing: `StagedLo`/`StagedHi`
are bumped synchronously with handing a column to `Core_Nmi_Play`'s
forced-blank commit, one real frame before that commit actually writes
VRAM (same design BG1 already uses) — a first-draft version of this test
checked tilemap attribute bits before the Tile2Slot-consistency check, so
a freshly-extended-but-not-yet-committed edge column was misclassified as
a hard failure instead of "pending repair." Fixed by matching BG1's own
check order (Tile2Slot-consistency first) — a test-methodology bug, not
an engine bug; BG1's own gate never hit it because its step list is a
monotonic forward sweep, never this test's deliberate reversals. Passes
deterministically (checked twice) on the full committed build.

**Phase 10 is now fully done, all four steps plus Step 3.** See `plan.md`
§2.10's stop conditions for the DMA-queue-contention risk's current status
(the root bug that caused it is now fixed via `Core_Dma_HasFreeSlot`, but
don't raise `STREAM_SCROLLFP_BUDGET_MAX` without re-measuring first —
see that section for why).

## Phase 11: damage system — DONE (see `plan.md` §2.11 for the full writeup)

`CHAR_HP`/the HUD already worked (Phase 6); the only remaining gap was
"nothing reacts at 0." The obvious approach — kill the entity through
`core/oop.pasm`'s generic `Core_Oop_Destroy`/garbage-collect path — turned
out to be a trap specific to this codebase: `Entity1_Base`/`Entity2_Base`/
`Entity3_Base` (`main.pasm`) are compile-time-fixed WRAM literals, not
derived at runtime from each entity's `OopDp`, and `Core_Oop__ReclaimSlot`
compacts `OopObjRam` and rewrites *surviving* objects' `OopDp` on kill — if
entity 1 were reclaimed, entity 2/3's real DP window would physically move
while every hardcoded `EntityN_Base` reference elsewhere in the codebase
(`Character_HitApply_VsEntity2/3`, etc.) kept reading the old address. Same
class of hazard as CLAUDE.md's "player is always slot 0... don't build a
general entity-lookup system" note, just for AI slots too.

**The design instead: soft-kill via `CHAR_HP==0` itself.** No new struct
field, `core/oop.pasm`'s kill/GC path never called, `OopObjRam` untouched.
`CHAR_HP==0` (the existing clamp floor) IS the dead condition — sticky,
since nothing but the `HitApply` leaves' own clamp-at-0 ever writes
`CHAR_HP`, and this phase makes those leaves refuse to re-touch a target
already at 0. Scoped to AI entities only (`CHAR_INPUT_DRIVEN==2`); the
player is exempt — player death/game-over stays out of scope.

Four small, local edits in `main.pasm`, each following this project's
Poppy-safety rules (short branches, redundant `sep`/`rep` resyncs at every
new branch target):
1. `Anim_Play` (right after `Anim_Play__loaded`): a dead AI entity `rts`s
   immediately — no AI seek/attack dispatch, and critically no
   `Anim_Play_Idle/Walk/Attack`, so it never reaches `Msu1_LoadFrame` again
   and never spends the shared one-entity-per-frame MSU streaming budget on
   an invisible corpse.
2. `Character_PlayFrame`'s X and Y movement blocks: a dead AI entity
   branches to the existing `__hold`/`__hold_y` freeze targets (same ones
   hit-stun already uses).
3. `Character_PlayFrame`, right before `jsr Core_Oam_SetSprite`: a dead AI
   entity's `OamSetSprite_Y` is overridden to `$F0` — the OAM layer's own
   "hidden" idiom (see `ccdma_validated_nmi_timing_bug` project memory), not
   a sentinel X (Phase 8 made X a real 16-bit world coordinate with AI-seek
   distance math that assumes real positions).
4. `Character_HitApply_VsEntity1/2/3`'s `__dy_ok` leaves: if the target's
   `CHAR_HP` already reads 0, `rts` before stamping `HitStun`/touching `Hp`
   again — a dead entity takes no further hits, and doesn't consume the
   attacker's `CHAR_HIT_APPLIED` latch (so the same attack can still land
   on a second, live target this cycle). `Character_HitApply`'s dispatcher
   needed no change — a dead AI never re-enters `CHAR_SELECTED==2` (item 1
   prevents that), so it can't become an attacker either.

**Verified**: `tools/verify/phase11_damage.py` forces Entity #1's `CHAR_HP`
to 0 (direct WRAM write is safe here — unlike Phase 10's `PosX`, nothing
else races `CHAR_HP`), runs 600 real frames, and confirms against live
Mesen2 state: `CHAR_HP` stays 0, `CHAR_POS_X` frozen, `HitStun` stays 0,
hardware OAM slot 1's Y byte reads `$F0`, `Nmi_FrameCounter` keeps
advancing (no vblank overrun). Controls: entities 0/2/3 are not hidden,
entities 2/3's HP is untouched, and both keep animating (sampled across 6
ticks — deliberately not a position check, since a living AI entity holds
still once within `ANIM_AI_ATTACK_RANGE` regardless of this feature).
Passed deterministically across 2 runs. Full regression suite
(`audit_all.py`, `check_label_drift.py`, `phase5.py`, `phase6.py`,
`phase7.py`) still passes.

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
