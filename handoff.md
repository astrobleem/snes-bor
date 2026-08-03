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
- **A real hardware OAM/OBJ sprite**: a 16x16 solid-red test sprite (X=120,
  Y=100), proving the full OAM pipeline end-to-end — VRAM tile data, CGRAM
  OBJ palette, `Oam_Buffer`/`Oam_ExpandedHi` shadow tables, `Core_Oam_Play`'s
  hi-table packing (`Core_Oam_TransformHiOam`), and the queued-DMA upload
  through `Core_Nmi_Play`. Both the low table (X/Y/tile/attr) and the real
  hardware hi-table (size bit) are byte-exact against expected values; a
  PPU-composited screenshot's red-pixel bounding box measures exactly 16x16
  pixels. **The sprite persists on screen by accident, not by design** — see
  `TestSprite_Init`'s header comment in `main.pasm` before adding a second
  sprite or any per-frame OAM write (the DMA fires once at boot; the next
  `Core_Oam_Play` call with a nonzero `Oam_CurrentSlot` will stomp this
  sprite's real-OAM slot with the shadow's cleared state unless it's
  re-written into the shadow buffer first).
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

- **Remaining margin before `$FC00`**: ~834 bytes as of this build. Don't
  compute this from the highest label address in `main.sym` alone — `.incbin`
  blobs have no end-label, so that only gives you where the last blob
  *starts*. Add the blob's real size (frame count x `ANIM_FRAME_BYTES`, or
  the `.bin` file's size on disk) to get the true end address before
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
    print('OAM hi byte0 & 3:', m.read_memory('snesSpriteRam', 512, 1)[0] & 3)
    print('Anim_Selected:', m.read_u8(0x7E53B2, mem_type='snesMemory'))
```

## What's NOT done yet

- **No player entity.** No input-driven movement, no player state, no
  interaction between the OAM test sprite and Ralf's BG2 animation system.
- **No `Core_Oam_SetSprite`-style per-frame entry point.** The OAM shadow
  buffer is only ever written once, at boot. Adding one is the natural next
  step but will immediately hit the "sprite persists by accident" trap
  above — plan for it, don't rediscover it.
- **No multi-sprite testing.** Only OAM slot 0 has ever been written with
  real data.
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

Add a per-frame `Core_Oam_SetSprite` entry point and prove a second,
independently-moving sprite works — extends the OAM pipeline from "one
static sprite" to "N sprites, updated live," which is what a real
player/enemy entity will need. The hi-table fix is verified for both size
values now, so the new sprite can freely be 8x8 or 16x16.

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
