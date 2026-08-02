# Handoff

Written at the end of a session that added Ralf's **walk** animation and
**input-driven animation switching** on top of the previous session's idle-
animation pipeline. Read this before doing anything else. Also read
`CLAUDE.md` (build/test commands, architecture map) and `build.md`
(register tables, CC-DMA mechanism, Mesen2 harness gaps) — this doc doesn't
repeat what's already accurate there. It only covers what's new/current.

## Current state (verified working)

`distribution/bor.sfc` boots into Ralf's **idle animation** (unchanged from
before) and now **switches to a walk animation while dpad Left or Right is
held**, reverting to idle on release. Both animations play in the same
fixed 4x6-tile BG2 window as before. Verified via Mesen MCP:

- Default boot state: `Anim_Selected == 0` (idle), VRAM matches the baked
  idle frame for whatever `Anim_FrameIndex` currently is.
- Holding Left (or Right) for even a handful of frames: `Anim_Selected`
  flips to 1, `Anim_FrameIndex` resets to 0 and VRAM immediately shows walk
  frame 0 (no waiting a full tick-delay to see the switch take effect —
  deliberate, see `Anim_Play`'s header comment in `main.pasm`).
- Holding Left across many frames: `Anim_FrameIndex` cycles through
  0..5 correctly (sampled 6 consecutive advances, all matched the baked
  walk blob byte-for-byte).
- Releasing input: reverts cleanly to idle, VRAM matches baked idle data
  again.
- Screenshots of the idle vs. walk states show a visibly different leg/arm
  pose, consistent with the byte-level checks.
- Basic PPU sanity (`get_ppu_state` -> `forcedBlank: false`) after
  switching + running normally — nothing hung or got stuck in forced blank.

Reproduce (note: `set_input`'s `frames` argument advances the emulator
*internally* — don't call `run_frames` again right after, or you'll run
extra frames with no input and undo the switch before you read state):

```python
import sys
sys.path.append(r'E:\Mesen2\python')
from mesen_mcp.session import McpSession

ROM = r'E:\gh\snes-bor\distribution\bor.sfc'
MESEN = r'E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe'
idle = open(r'E:\gh\snes-bor\src\assets\anim_ralf_idle.bin', 'rb').read()
walk = open(r'E:\gh\snes-bor\src\assets\anim_ralf_walk.bin', 'rb').read()

with McpSession(rom=ROM, mesen=MESEN, boot_wait=2.0) as m:
    m.pause(); m.reset_emulator(); m.pause()
    m.run_frames(90)
    fidx = m.read_u8(0x7E53B0, mem_type='snesMemory')  # Anim_FrameIndex
    vram = m.read_memory('snesVideoRam', 0x4020, 768)
    print('idle ok:', vram == idle[fidx*768:(fidx+1)*768])

    m.set_input(McpSession.BTN_LEFT, 20)   # advances the emulator itself
    m.pause()
    sel = m.read_u8(0x7E53B2, mem_type='snesMemory')   # Anim_Selected
    fidx = m.read_u8(0x7E53B0, mem_type='snesMemory')
    vram = m.read_memory('snesVideoRam', 0x4020, 768)
    print('sel(expect 1):', sel, 'walk ok:', vram == walk[fidx*768:(fidx+1)*768])
```

**Environment prerequisite, not a code fix**: this session discovered
Mesen's portable `settings.json` (next to `Mesen.exe`) shipped with
`Snes.Port1.Type = "None"` — no virtual controller configured, so
`set_input` silently did nothing (no error, just `Input_press` staying
`0x0000` forever) until this was changed to `"SnesController"`. Already
fixed in this Mesen install for this session; see
[[mesen_controller_not_configured]] if it ever needs redoing (e.g. a fresh
Mesen install/reinstall).

## What happened this session (chronological, condensed)

1. Picked the previous handoff's "depth-first" option (per user's explicit
   choice): wire walk next, then the simplest input-driven switch.
2. Baked `out/ralf_walk/`'s frames via `tools/bor_converter/bake_vram_frames.py`
   (unchanged tool, already validated in the previous session).
3. Wrote `Anim_Selected` WRAM state + a new `Anim_Play` dispatcher (reads
   `Input_press`'s high byte for dpad Left/Right, picks idle vs. walk, force-
   resets to frame -1 on a selection change so the new animation's frame 0
   shows immediately) that calls into renamed `Anim_Play_Idle`/new
   `Anim_Play_Walk` sub-routines — same queued-DMA-per-frame-change design
   as before, same budget discipline.
4. **First build attempt with a full 8-frame walk cycle silently overflowed
   bank 0's fixed `.org $FC00` boundary** — Poppy gave no error, but
   raw-byte diffing `main.bin` against the baked walk blob showed a perfect
   match for 7 of 8 frames, then a hard divergence exactly at the `$FC00`
   file offset into `scpu_boot`'s own opening bytes. Root cause: the
   $C100-$FC00 code+data window (a fixed 15104-byte budget) was already at
   capacity with idle alone; adding a full second 6144-byte blob (plus new
   dispatcher/routine code) didn't fit. **Fixed by trimming the baked walk
   animation to 6 frames** (indices 0,1,3,4,5,7 of the source 8-frame cycle,
   picked for roughly even spacing) — `bake_vram_frames.py` gained an
   optional frame-index-subset argument for this. Leaves ~790 bytes of
   margin before `$FC00`, not zero.
5. **Hit a new, previously-undocumented Poppy bug (#8 in the
   `poppy_assembler_bugs` memory)**: with the two `.incbin` data labels
   (`AnimRalfIdleFrames`, `AnimRalfWalkFrames`) sitting back-to-back with no
   code between them, every arithmetic expression referencing
   `AnimRalfWalkFrames` silently resolved to `AnimRalfIdleFrames`'s address
   instead of its own — confirmed by scanning the whole assembled binary
   for the expected `lda #imm16` immediates: idle's six expected values
   showed up *twice*, walk's six expected values showed up *zero* times.
   The exported symbol table also reported both labels at the identical
   address. **Fixed by never referencing `AnimRalfWalkFrames` in an
   expression at all** — walk's frame addresses are now computed from the
   known-good `AnimRalfIdleFrames` label plus a compile-time-constant byte
   offset (`ANIM_WALK_BASE_OFFSET = ANIM_FRAME_COUNT * ANIM_FRAME_BYTES`)
   instead. Re-verified byte-for-byte after the fix: each blob's own six
   immediates now appear exactly once, not zero or twice.
6. **Hit the Mesen controller-config gap** described above while first
   trying to verify the switch — `Input_press` reading `0x0000` regardless
   of `set_input` calls looked exactly like either a harness limitation or
   a bug in the untouched, previously-never-exercised `Core_Input_Poll`.
   Root-caused via Mesen's own C++ source
   (`SnesDebugger::ProcessInputOverrides`) to a missing virtual controller
   on port 1 in the local Mesen install's settings, not a code bug. Fixed
   the settings, re-verified — `Input_press` immediately started reading
   correct values and the switch logic worked exactly as designed on the
   first real test after that.
7. Consulted `advisor` once, mid-investigation of bug #8, before committing
   to a fix approach (it correctly predicted the "`.incbin` sized as 0
   bytes during estimation" root cause and recommended the
   known-good-label-plus-offset fix used above).

## What's NOT done yet

- **No attack/other animations wired**, only idle + walk. The pattern to
  extend (bake + adapt a new `Anim_Play_<name>` sub-routine + a new branch
  in the top-level `Anim_Play` selector) is now proven twice over, but
  **capacity is tight**: the $C100-$FC00 window has ~790 bytes of margin
  left, not enough for another full animation's worth of frames without
  either trimming further, or restructuring where large data blobs live
  (see below).
- **The walk cycle is a 6-frame subset of the source 8-frame cycle**, not
  the full animation — a visible, deliberate quality compromise made to fit
  ROM space, not a bug. If more bank-0 room frees up later (e.g. by
  shrinking core-module code, or by moving large asset blobs to a different
  `.org` gap with more slack — the audio-blob gap at `$B000`-`$C100` was
  checked this session and only has ~170 bytes free, not enough), consider
  re-baking with more/all frames.
- **Only Left/Right trigger walk; no distinction between the two, no other
  buttons wired to anything.** `Anim_Play`'s selection logic treats
  Left-or-Right identically (`Input_press`'s high byte `& $03 != 0` ->
  walk). Facing direction / sprite flip is not implemented at all.
- **Still only one character, one fixed BG2 tile window.** Multi-enemy
  compositing (the real architectural reason for CC-DMA per
  `SNES-BOR-Engine-Prompt.md`) is unchanged and still not started.
- **No OAM/player rendering path** — unchanged from previous sessions,
  `core/oam.pasm` still wired but nothing populates it.
- **No background/level tileset conversion, no MSU-1 asset streaming tied
  to any of this, no ROM-packing/manifest-loading stage** — unchanged.
- **Cosmetic boot-time "pop"** (static sprite geometry differs from the
  animated frames' geometry until `Anim_TickCounter` first reaches 0) —
  still not fixed, same as previous handoff, still just flagged not
  decided.

## Recommended next step

Two reasonable directions, similar shape to last session's fork:

- **Keep extending animation breadth**: attack animation + a simple state
  machine (idle/walk/attack) driven by button presses (not just held
  dpad). Before doing this, seriously consider the ROM-space problem first
  — either accept further frame-trimming per animation, or spend some time
  finding real slack (candidates: shrinking `ANIM_LABEL_FIXUP`-adjacent nop
  padding, checking actual TAD driver code size vs. its `$8800`-`$AC00`
  budget for slack, or a more ambitious fix like moving large data blobs to
  a `.org` region past `$FF10`'s handlers if there's room before `$FFE4`'s
  native vector table — none of these were investigated this session).
- **Start the real OAM/player rendering path** (per the engine prompt's
  intended split: enemies on BG2 via CC-DMA, player via real OAM sprites).
  Bigger, more architecturally-new chunk of work, same as flagged last
  session.

No strong recommendation between these — flag both and get agreement
before starting.

## Harness gotchas (don't relearn these the hard way)

Everything in previous handoffs' "Harness gotchas" sections still applies
(Mesen run-to-run jitter, `add_write_hook`/`run_until` unreliability, the
~40% false-silent audio check rate, eight pre-existing Poppy
silent-miscompile bugs, the ~1-frame queued-DMA display lag). New this
session:

- **`set_input`'s `frames` parameter advances the emulator itself**
  (internally calls resume -> sleep -> pause, then clears the override) —
  it is not like `run_frames`, which you call separately afterward. Calling
  `run_frames` again right after `set_input` runs *additional* frames with
  no input, which can silently undo whatever the held input just did before
  you get a chance to read state. Read state immediately after `set_input`
  returns (an extra `m.pause()` is harmless/redundant but not needed).
- **A fresh/reset Mesen portable install can have `Snes.Port1.Type =
  "None"`**, silently making every `set_input` call a no-op with no error.
  See [[mesen_controller_not_configured]]. If `Input_press` reads `0x0000`
  no matter what you do, check this before assuming a code bug — especially
  since this project had never exercised controller input at all before
  this session, so a "the ported input code doesn't work" theory was
  initially just as plausible as the harness gap that turned out to be the
  real cause.
- **Poppy bug #8**: two adjacent `.incbin` data labels with no code between
  them — referencing the second one in an expression can silently resolve
  to the first one's address instead (not a small drift, the *wrong blob
  entirely*, with no assembler error). See `poppy_assembler_bugs` memory
  bug #8. Verify any new back-to-back data blob by scanning the assembled
  binary for expected `lda #imm16` immediates, not just by checking the
  first blob is byte-correct — the second one needs its own check.
- **Fixed `.org` overflow can look like a clean build with a subtly wrong
  binary**, not necessarily an obvious corruption — the first walk-animation
  build this session "succeeded" with no error/warning while silently
  dropping 768 bytes of real data. Whenever new code or data grows a
  region between two fixed `.org` points, re-verify total size against the
  budget (`next_org_address - this_org_address`) and/or raw-byte-diff the
  output against known-good source data, don't just trust a clean build.

## File inventory (what's real vs. scratch)

**Real, part of the build / pipeline (new/changed this session marked \*):**
- `src/main.pasm` — the only file `build_rom.py` actually assembles.
  \* Added: `Anim_Selected` WRAM state, new top-level `Anim_Play` dispatcher
  (input read + switch logic), renamed old `Anim_Play` -> `Anim_Play_Idle`,
  new `Anim_Play_Walk`, `AnimRalfWalkFrames` (`.incbin`), `ANIM_WALK_BASE_OFFSET`.
- `src/assets/anim_ralf_walk.bin` \* — 4608 bytes, 6 baked frames (subset of
  the source 8-frame walk cycle) of precomputed VRAM-format tile data.
  Generated by `tools/bor_converter/bake_vram_frames.py out/ralf_walk
  src/assets/anim_ralf_walk.bin 0,1,3,4,5,7`; regenerate the same way if
  `out/ralf_walk/` changes (or to try a different frame subset / full 8 if
  ROM space ever frees up).
- `src/assets/anim_ralf_idle.bin` — unchanged from previous session.
- `tools/bor_converter/bake_vram_frames.py` \* — gained an optional third
  CLI arg (comma-separated frame indices) to bake a subset instead of every
  frame in a manifest; backward compatible (omit it for "all frames", the
  previous behavior).
- `tools/bor_converter/pak_extract.py`, `convert_sprite.py`,
  `entity_parse.py`, `convert_animation.py` — unchanged.
- `Beats of Rage Original [v.3.0 Build 4086].pak` — source asset pack,
  project root.

**Demo/example output, not fully wired into the ROM:**
- `out/ralf_idle/`, `out/ralf_walk/` — both now baked+wired (walk as a
  6-frame subset, not all 8 — see above).

**Environment change, not part of this repo:**
- `E:\gh\Mesen2\bin\win-x64\Release\settings.json` — `Snes.Port1.Type`
  changed from `"None"` to `"SnesController"` so `set_input` actually
  works. Not part of `snes-bor`'s repo/build, but load-bearing for testing
  any future input-driven feature in this Mesen install.

**Scratch, not committed anywhere persistent (session job tmp dir / deleted
before finishing, will not survive):** raw-byte verification scripts, the
Mesen VRAM/DMA/input comparison scripts, two diagnostic screenshots
(idle vs. walk poses, confirmed visually distinct then deleted). Also
regenerated and then deleted `src/main.sym` (a Poppy symbol-file dump used
for raw-byte debugging bug #8) — regenerate with `dotnet poppy.dll
src/main.pasm -s src/main.sym` if needed again, but the symbol *addresses*
it reports for adjacent data-blob labels are exactly the kind of thing bug
#8 makes unreliable — prefer raw-byte scanning of `main.bin` over trusting
`.sym`/`.pansy` addresses for anything like this.

**Already-flagged-as-dead, still true:** `src/sa1/*.pasm`,
`copy_working_test.*`, `exact_copy_test.*`, and friends under `src/` are
scratch/experiment files, not part of the real build. See `CLAUDE.md`.
