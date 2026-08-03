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
  one static, one dpad-driven: sprite 0 is the original 16x16 solid-red
  test sprite (X=120, Y=100, static); sprite 1 is a second instance of the
  same tile (Y=150, fixed) whose X now moves left/right while the dpad is
  held, clamped (not bounced) at X=8/X=216, holding position when nothing
  is held. Both are re-written into the shadow buffer **every frame** by
  `TestSprite_PlayFrame` (`main.pasm`, right after
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
  Sprite 1 reads `Input_press+1` directly, using the exact same bit-check
  convention as `Anim_UpdateFacing` (bit0=Right, bit1=Left) and the same
  Left-wins tie-break when both are held simultaneously — so sprite 1's
  movement direction and Ralf's BG2 facing flip always agree on the same
  frame's input, never disagree due to two different readings of
  `Input_press`.
  Verified in Mesen2: holding Right/Left moves sprite 1's real OAM X byte
  in the correct direction and by a multiple of `TESTSPRITE2_SPEED` (2);
  it clamps at **exactly** 216 and **exactly** 8 (not off-by-one); it holds
  position with no input; holding Left+Right together moves it left and
  `Anim_FacingLeft` reads 1 on the same sample, confirming both subsystems
  agree; sprite 0's OAM bytes stay byte-exact `[120,100,0,48]`, sprite 1's
  Y/tile/attr stay fixed at `150/0/$30`, and the packed hi-table byte stays
  exactly `$0A` throughout. A full-screen screenshot mid-movement shows
  both red squares on screen with no top-of-frame corruption band.
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
  requested `frames` count (observed ~144% of requested in one run).
  Assert direction/clamp-endpoint/relative-change, not an exact pixel
  value computed from `frames * speed`, unless the value is saturated at a
  known clamp.
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

- **Remaining margin before `$FC00`**: ~607 bytes as of this build (was
  ~612 before this session's dpad-driven sprite-1 movement, ~834 before
  the `Core_Oam_SetSprite` + second-sprite session before that — trading
  the autonomous ping-pong bounce for dpad-driven clamped movement was
  close to a wash, as expected). Don't compute this from the highest label
  address in `main.sym` alone — `.incbin` blobs have no end-label, so that
  only gives you where the last blob *starts*. Add the blob's real size
  (frame count x `ANIM_FRAME_BYTES`, or the `.bin` file's size on disk) to
  get the true end address before subtracting from `$FC00`.

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

- **No real player entity yet.** Sprite 1's X now responds to the dpad,
  but there's still no player state (health, animation, hitboxes), no
  interaction between it and Ralf's BG2 animation system, and Y is still
  hardcoded at 150 (X-only was a deliberate scope decision — see
  `TestSprite_PlayFrame`'s header — to avoid building a one-off Y clamp
  that a real 2-axis entity-update routine would just replace).
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

Sprite 1's X axis is now dpad-driven and clamped; Y is still hardcoded at
150. The natural next step is generalizing `TestSprite_PlayFrame`'s
sprite-1 block into a real 2-axis entity-update routine (reading all four
dpad bits from `Input_press+1` in one pass, moving both X and Y, with
independent clamp bounds per axis) — at that point it's honestly closer to
"the first player entity" than "a test sprite," so it may be worth
renaming/moving it out of the `TestSprite_*` family rather than continuing
to grow it in place. ROM budget is getting tight (~607 bytes before
`$FC00`) — a real entity update routine should stay small, or a first look
at freeing space elsewhere in the `$C100`-`$FC00` window may be needed
first (candidates: the `AnimRalfAttackFrames`/`AnimRalfIdleFrames` blobs
are the largest single consumers of this window by far).

## Harness gotchas (Mesen2 / build)

Full detail lives in project memory ([[mesen-audio-check-nondeterministic]],
[[mesen-mcp-hook-reliability-gap]], [[mesen-controller-not-configured]],
[[poppy-assembler-bugs]], [[ccdma-validated-nmi-timing-bug]],
[[65816-calling-convention-bugs]], [[oam-sprite-bringup]]) — read those
before spending time rediscovering a harness quirk or Poppy miscompile.
Quick-reference list of what's easy to trip over fresh:

- `set_input`'s `frames` argument advances the emulator itself — don't
  `run_frames` again right after, you'll run extra frames with no input.
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
