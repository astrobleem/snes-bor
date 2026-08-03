# Handoff

Read this before doing anything else, then `CLAUDE.md` (build/test commands,
architecture map) and `build.md` (register tables, CC-DMA mechanism, Mesen2
harness gaps) — this doc doesn't repeat what's already accurate there. This
file is rewritten fresh each session to reflect current state; it is not a
session-by-session log. Deep debugging history (specific Poppy miscompile
bugs, the OBSEL/hi-table bring-up story, harness quirks) lives in this
project's Claude memory files, not here — see the pointers at the bottom of
each section below.

## Current state (verified working)

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
  `AnimRalfIdleFrames`/`AnimRalfAttackFrames`, which sit immediately after
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
- **Three ROM-layout audit tools** (`tools/rom_audit/`) — run after any
  change that grows code/data in the `$C100`-`$FC00` fixed-`.org` window:

  ```bash
  python tools/rom_audit/verify_layout.py src/main.pasm src/main.sym
  python tools/rom_audit/audit_jumps.py src/main.bin FC00 FF00 FF10 8000
  python tools/rom_audit/audit_ownership.py src/main.bin src/main.sym FC00 FF00 FF10 8000
  ```

  All three report clean on the current build (one benign drifted-but-
  unreferenced label, `AnimRalfAttackFrames`, is expected — see
  `verify_layout.py`'s own docstring for why that specific pattern is safe).

- **Remaining margin before `$FC00`**: ~549 bytes as of this build (was
  ~607 before this session's Y-axis addition — the 2nd-axis dpad block cost
  58 bytes, close to the ~80-byte estimate going in; ~612 before that
  session's X-axis/clamp work, ~834 before the `Core_Oam_SetSprite` +
  second-sprite session before that). Don't compute this from the highest
  label address in `main.sym` alone — `.incbin` blobs have no end-label, so
  that only gives you where the last blob *starts*. Add the blob's real
  size (frame count x `ANIM_FRAME_BYTES`, or the `.bin` file's size on
  disk) to get the true end address before subtracting from `$FC00`.

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
  X and Y, but there's still no player state (health, animation,
  hitboxes), and no interaction between it and Ralf's BG2 animation
  system — it's still a second solid-red 16x16 square, not a character.
  The `TestSprite_*` naming was deliberately kept this session (see
  `handoff.md`'s prior "Recommended next step" and the routine's own
  comments) — a pure rename out of that family is a separate, byte-neutral
  follow-up, not done yet.
- **Only 2 of 128 OAM slots ever exercised.** `Core_Oam_SetSprite` itself
  is generic (any slot, any X/Y/tile/attr/hi), but nothing has called it
  with a 3rd+ sprite or tested behavior near `OAM_SLOTS` (128).
- **The hi-table's X-high bit is unexercised by any real shipped sprite**
  (only by a synthetic WRAM test) — unverified if a sprite ever needs X >=
  256.
- **No multi-enemy BG2 compositing, no background/level tileset conversion,
  no MSU-1 asset streaming tied to any of this, no ROM-packing/manifest
  stage.** Matches the project's stated "not a playable game yet" scope.
- **Cosmetic boot-time "pop"** (static sprite geometry differs briefly from
  animated frames' geometry until `Anim_TickCounter` first reaches 0) — not
  fixed, not decided.

## Recommended next step

Sprite 1 is now fully 2-axis dpad-driven and clamped (see "Current state"
above) — the entity-movement groundwork from the last two sessions is
done. The next task is **generalizing the BOR character-pak pipeline**:
`AnimRalfIdleFrames`/`AnimRalfAttackFrames` and their frame-count constants
(`ANIM_FRAME_COUNT`, `WALK_FRAME_COUNT`, `ATTACK_FRAME_COUNT`,
`ANIM_FRAME_BYTES`, the `ANIM_TILEMAP_*_BASE` offsets) are all hardcoded to
one character (Ralf) today — there's no character-selection layer. Using a
different Beats of Rage pak means hand-editing these compile-time
constants and re-baking, not swapping a data file. This is a real
architectural addition, not a tweak:
- A data-driven per-character animation descriptor (frame counts/offsets/
  tile bases per character, likely indexed rather than a pile of `=`
  constants) replacing today's hardcoded labels in `main.pasm`.
- Extending `tools/bor_converter` (the pak-extraction/animation-baking
  pipeline) to bake arbitrary paks against that descriptor format, not
  just Ralf's.
- Land this carefully against the ROM budget (~549 bytes before `$FC00`
  as of this build) — a generic descriptor scheme should be evaluated for
  its own byte cost before committing to a design, and the
  `AnimRalfAttackFrames`/`AnimRalfIdleFrames` blobs remain the largest
  single consumers of the `$C100`-`$FC00` window if space needs to be
  freed alongside this.

Smaller, independent, available any time: renaming `TestSprite_PlayFrame`'s
sprite-1 state/routine out of the `TestSprite_*` family (it's functionally
closer to "the first player entity" than "a test sprite" now) — deferred
this session as a pure, byte-neutral cleanup that doesn't need to block or
be blocked by the pak-genericity work.

## Harness gotchas (Mesen2 / build)

Full detail lives in project memory ([[mesen-audio-check-nondeterministic]],
[[mesen-mcp-hook-reliability-gap]], [[mesen-controller-not-configured]],
[[poppy-assembler-bugs]], [[ccdma-validated-nmi-timing-bug]],
[[65816-calling-convention-bugs]], [[oam-sprite-bringup]]) — read those
before spending time rediscovering a harness quirk or Poppy miscompile.
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

**Already-flagged-as-dead:** `src/sa1/*.pasm`, `copy_working_test.*`,
`exact_copy_test.*`, and similar files under `src/` are scratch/experiment
files from earlier debugging, not part of the real build. See `CLAUDE.md`.
