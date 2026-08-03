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
- **Two real hardware OAM/OBJ sprites, live and independently moving**:
  sprite 0 is the original 16x16 solid-red test sprite (X=120, Y=100,
  static); sprite 1 is a second instance of the same tile (Y=150, X
  ping-ponging between 8 and 216 at 2px/frame). Both are re-written into
  the shadow buffer **every frame** by `TestSprite_PlayFrame` (`main.pasm`,
  right after `TestSprite_WriteSolidTile`, called from `scpu_main_loop`
  before `Core_Oam_Play`) via the new `Core_Oam_SetSprite` entry point
  (`core/oam.pasm`, right after `Core_Oam_Play`) — proving the OAM
  pipeline end-to-end for live, per-frame-updated sprites, not just a
  one-time boot write. `Core_Oam_SetSprite` takes its 5 fields
  (X/Y/tile/attr/hi) via WRAM staging cells (`OamSetSprite_*`,
  `$7E53AB-$7E53AF`), matching `core/dma.pasm`'s `DmaRequest_*` convention,
  writes one `Oam_Buffer`/`Oam_ExpandedHi` entry at the `Oam_CurrentSlot`
  cursor, and advances it — game code fills the cells and calls it once per
  sprite per frame, then calls `Core_Oam_Play` once.
  Verified in Mesen2: sprite 0's OAM bytes are byte-exact `[120,100,0,48]`
  on every sampled frame across a 10-frame sweep; sprite 1's Y/tile/attr
  stay fixed while X took 10/10 distinct values; the packed hi-table byte
  was exactly `$0A` every sample (both sprites' size bit set, correctly
  packed at bits 1-0 and 3-2); a full-screen screenshot shows both red
  squares on screen with no top-of-frame corruption band (confirms one
  544-byte OAM DMA/frame, now happening every frame instead of once, does
  not reintroduce the old forced-blank/vblank-overrun bug — that bug came
  from an unpaced loop spamming duplicate uploads, not from one legitimate
  upload/frame). `TestSprite_Init`'s one-time write only sets what's on
  screen before the main loop's first iteration now — `TestSprite_PlayFrame`
  is what keeps sprite 0 alive going forward, and it MUST keep re-asserting
  sprite 0 every frame it runs (see that routine's header comment) — the
  shadow-wipe-after-upload trap `TestSprite_Init`'s header used to warn
  about is now actually triggered every frame, not just theoretical.
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

- **Remaining margin before `$FC00`**: ~612 bytes as of this build (was
  ~834 before this session's `Core_Oam_SetSprite` + second-sprite work).
  Don't compute this from the highest label address in `main.sym` alone —
  `.incbin` blobs have no end-label, so that only gives you where the last
  blob *starts*. Add the blob's real size (frame count x `ANIM_FRAME_BYTES`,
  or the `.bin` file's size on disk) to get the true end address before
  subtracting from `$FC00`.

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

- **No player entity.** No input-driven movement, no player state, no
  interaction between the OAM test sprites and Ralf's BG2 animation system.
  `TestSprite_PlayFrame`'s sprite 1 moves on a fixed, input-independent
  ping-pong timer, not in response to controller state.
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

Wire `Core_Oam_SetSprite` to a real input-driven entity — the natural next
step is making sprite 1 (or a new slot) move via `Core_Input_Poll`'s dpad
state instead of the current fixed ping-pong timer, as a step toward an
actual player entity. `Core_Oam_SetSprite`'s calling convention (WRAM
staging cells `OamSetSprite_*`, see `core/oam.pasm`) is generic and ready
for that — no OAM-pipeline changes needed, just a different X/Y source per
frame. ROM budget is getting tight (~612 bytes before `$FC00`) — a real
entity update routine should stay small, or a first look at freeing space
elsewhere in the `$C100`-`$FC00` window may be needed first.

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
