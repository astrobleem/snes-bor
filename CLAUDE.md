# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A SNES (Super Nintendo) hardware-pipeline proof-of-concept targeting real SA-1 coprocessor hardware, with MSU-1 asset streaming and a ported Terrific Audio Driver (TAD). **This is not a playable game** — four independently-animated characters render simultaneously (all streamed at runtime from an MSU-1 asset roster, `tools/bor_converter/`), one dpad-driven and three AI-driven that seek the player and land stunning attacks, over a converted Beats of Rage level backdrop with a BG3 health-bar HUD (`tools/bg_converter/`) that the camera scrolls horizontally as the player moves. AI entities now soft-kill at 0 HP (stop acting, stop taking/dealing hits, sprite hides — no death animation, since the MSU roster has none, and no respawn); the player is exempt (no game-over) and there is still no game loop. It proves out the low-level hardware plumbing (SA-1 boot, CC-DMA sprite conversion, OAM/NMI frame commit, MSU-1 streaming, TAD audio, camera/scroll) plus a minimal entity layer and asset pipeline on top, so a real game can be built later. See `README.md`'s "Current Status" section for the authoritative, currently-accurate list of what's verified working vs. not built — check it before assuming something works or is missing.

`SNES-BOR-Engine-Prompt.md` is the original design spec for the full engine; much of it is still unbuilt.

**Roadmap (updated 2026-08-16): `plan.md`'s Phases 0–15 are all DONE and that file is now history.** New work starts in one of two places:
- **`plan_game.md` — the critical path to an actual playable game** (font/text renderer, game state machine, player death, win condition, stage transition, menus, score, moveset, items, bosses, ending). Start here unless told otherwise. Its hard prerequisite, phase G1, is a font/text renderer — nothing menu-shaped can start before it, and none exists today.
- **`plan_vm.md` — an OpenBOR `openborscript` bytecode VM.** A compatibility substrate for running real mods. **It is NOT required to ship a game and its first five gates produce zero user-visible change.** Do not restate it as "the way we get levels/menus later."

Both assume `README.md`'s "Current Status" as ground truth. `core/*.pasm` (see Architecture below) is adapted from [SNES-SuperBossGaiden](https://github.com/snesdev0815/SNES-SuperBossGaiden) under the original author's personal permission — adapt freely, it does not need to stay a literal port.

### The entity system

Every on-screen character is an instance of one `core/oop.pasm` class, `CharacterEntity`. Per-instance state (position, facing, frame index, animation selection, roster index, palette slot, tile column, hit stun) lives in that instance's own Direct Page window inside `OopObjRam` — `Core_Oop_Create`/`Play` switch the DP register per instance, so the class body addresses everything as plain DP offsets. `CHAR_INPUT_DRIVEN` selects behavior (0 = static, 1 = dpad player, 2 = AI seek). Per frame, `CharacterEntity_Play` runs `Anim_Play` → `Character_PlayFrame` → `Character_HitApply`.

Two constraints here are load-bearing and easy to break:
- **At most one entity may stream an animation frame per frame** (`Msu1_StreamBusy`). One `Msu1_LoadFrame` enqueues 6 of the 8 total DMA queue slots. Letting two stream in the same frame reintroduces a confirmed vblank-overrun corruption bug. The intended consequence is that with N entities each animates at most every N frames — that is correct, not a performance bug to "fix."
- **"The player is always slot 0"** is a deliberate shortcut: entity 0 is created first, never killed, and reachable at fixed absolute addresses. Don't build a general entity-lookup system for a single-player game.

## Build

Two-step build, both steps run automatically by `build_rom.py`:

```bash
python build_rom.py
```

This assembles `src/main.pasm` with Poppy (producing `src/main.bin` + `src/main.pansy`), then packs the ROM/MSU files into `build/` and `distribution/` (`bor.sfc`, `bor.msu`). **Always rebuild through this script after editing `src/main.pasm` or any `.include`d file under `src/core/`, `src/sa1/`, or `soundwork/tad/`** — there is no separate incremental step to forget.

Prerequisites (see `build.md` for full detail):
- **.NET 10 SDK**, user-local at `C:\Users\chad\.dotnet\dotnet.exe` (the system-wide `dotnet` resolves to 8.0, which fails with `NETSDK1045` against Poppy's `net10.0` target). `build_rom.py` already invokes the correct path.
- Poppy CLI itself lives in a separate repo — **`astrobleem/poppy`** (`E:\gh\poppy-astrobleem`), a fixed fork of the old, buggier Poppy that used to live at `E:\gh\SNES-CrimePatrol\tools\poppy-src`. Must be built once (`dotnet build src\Poppy.CLI\Poppy.CLI.csproj -c Release`) before `build_rom.py` can call `poppy.dll`; `build_rom.py`'s `POPPY_DLL` already points at the fork's output path. See `poppy_fork_migration` project memory for why the switch happened and two real regressions it caught.

There is no lint step and no unit-test framework — see Testing below for how correctness is actually checked.

## Testing

There's no unit-test framework, but each phase's gate is a committed script and all of them currently pass. Run these after any change:

```bash
python build_rom.py                              # no incremental step; always rebuild
python tools/rom_audit/audit_all.py              # static layout/ownership -> ALL CHECKS PASS
python tools/rom_audit/check_label_drift.py      # Poppy jsl label drift; exits nonzero on drift
python tools/rom_audit/check_width_directives.py # poppy#386 guard: .a8/.a16 at branch targets (also run by audit_all)
python tools/verify/phase5.py                    # 4 entities: OAM, palettes, animation, hit stun
python tools/verify/phase6.py                    # BG1 backdrop + BG3 HUD vs. converter output
python tools/verify/phase7.py                    # TAD audio reaches PLAYING and is audibly non-silent
python tools/verify/phase8.py                    # camera/scroll: world X, BG1HOFS, clamps, OAM X-high bit
python tools/verify/phase9.py                     # streaming cache under sustained held-dpad input: throughput bounded, no permanent stall
python tools/verify/phase11_damage.py             # damage system: dead AI stops acting/hitting, sprite hides
python tools/verify/phase12_roster.py             # roster expansion: 4 selectable characters, Select cycles/wraps
```

`tools/verify/phase9_stagecolumn_spotcheck.py` and `phase9_syncscroll_test2.py` (note: distinct from the routine `phase9.py` above) are a separate, non-gate pair of scripts for byte-exact Tile2Slot-vs-VRAM consistency in the streaming tile cache (`plan.md` §2.8) — they track `BG_SCREENS` automatically now (like `phase6.py`) and pass against whatever streaming BG currently ships (as of 2026-08-16, a real level, `out/bg_stage1a`), but each takes real Mesen2 wall-clock time. Don't add them to the routine list above; see `plan.md` §2.8's own gate procedure if you're touching `Core_StreamScroll_*`/`core/stream_cache.pasm`.

`tools/verify/phase10_frontpanel.py` is the same kind of non-routine, real-Mesen2-time gate for the BG3 frontpanel streaming cache (`plan.md` §2.10) — checks both the boot-time viewport load and the runtime scroll resolver (`Core_StreamScrollFp_*`/`core/stream_cache_fp.pasm`) against the frontpanel converter's own `tilemap.bin`/`tiles.bin`, using the same Tile2Slot-consistency invariant as `phase9_syncscroll_test2.py`. Don't add it to the routine list above; run it directly if touching `Core_StreamScrollFp_*`, `core/stream_cache_fp.pasm`, or `Core_Dma_HasFreeSlot`/`Core_Dma_Enqueue` in `core/dma.pasm` (that guard is shared by both BG1's and FP's resolvers — see its header comment).

They share `tools/verify/_harness.py`, which derives the ROM path from the repo root (so they work from a worktree) and enforces this project's read rules. **They deliberately compare against ground truth the engine did not produce** — the converter's own `.bin` files, the packed `bor.msu`, `audio-data.bin` — rather than asking the engine whether it looks happy. Phase 7 is why: TAD reported `PLAYING` with the S-DSP out of reset at full volume for as long as it was loading pure zeros, so every engine-visible status byte read perfect while nothing worked.

Beyond those, correctness is checked by loading `distribution/bor.sfc` in Mesen2 (an accurate SA-1 emulator) via its Python MCP debugging layer:

```python
import sys, os
sys.path.append(r'E:\gh\Mesen2\python')
from mesen_mcp.session import McpSession

# ALWAYS derive this from the actual repo root you're working in, never
# hardcode `E:\gh\snes-bor\distribution\bor.sfc` literally -- if you're in a
# git worktree (`.claude/worktrees/<name>/`), that literal path points at
# the MAIN CHECKOUT's ROM instead, which build_rom.py never touched. Every
# test then silently runs against a stale, unrelated build with no error --
# an entire session was lost to exactly this (see the
# boot-hang-before-player-init memory). Verify with a byte-level
# build-identity check (grep the ROM for a known instruction's encoding)
# before trusting any result if there's any doubt which ROM you're testing.
REPO_ROOT = os.getcwd()  # or wherever this session's worktree/checkout root is
ROM = os.path.join(REPO_ROOT, 'distribution', 'bor.sfc')
MESEN = r'E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe'

with McpSession(rom=ROM, mesen=MESEN, boot_wait=2.0) as m:
    m.run_frames(120)
    m.pause()
    print(m.get_ppu_state())
    print(m.get_audio_state())
```

Before trusting hooks/exec-hooks or small memory reads from this harness, or before believing a "silent audio" or "flaky" result, read `build.md`'s "Testing in Mesen2" section and "Known harness gaps" — there are several real, non-obvious reliability gaps in the debug harness itself (stale small reads, `read_memory` returning `0` for hardware registers, unreliable exec hooks, nondeterministic-looking audio checks that turned out to hide a real deterministic bug). The standing rule in this project: don't accept "probably just flaky/harness noise" without checking ground truth (raw bytes, a from-scratch reimplementation of the expected computation, or a direct engine-state read) first — several past "nondeterminism" symptoms in this codebase turned out to be 100%-reproducible logic bugs.

`m.reset_emulator()` before registering hooks/reading state is often necessary — hooks registered on an already-running paused session sometimes silently fire 0 times.

## Architecture

### Toolchain: Poppy assembler, not WLA-DX/ca65

This project uses the **Poppy** 65816 assembler, not the WLA-DX toolchain the `makefile`/`tools/wla-65816`/`tools/wlalink` binaries suggest (those are leftover from before the switch — ignore them; `build_rom.py` is the real build). Poppy is a from-scratch tool in a sibling repo; this project builds against the **astrobleem fork** at `E:\gh\poppy-astrobleem`, not the older, buggier upstream.

Poppy's defining hazard is that it can emit **wrong bytes with no error at all**. That is still true, but the specific list is much shorter than it used to be.

**Status re-measured 2026-08-18 against fork HEAD `a7a760e` with fresh minimal repros, then five of the six live bugs were fixed in the fork the same day (`272f7ea`, `08fe283`). Most of this project's historical workarounds are now obsolete.** `src/core/*.pasm`'s `nop` guard lines and its avoidance of `.dw` tables are *historical scar tissue* — do not extend those patterns into new code, and do not trust an old file's header comment over the lists below.

**Still live — exactly one, and you must write defensively against it:**

1. **Accumulator-width tracking is linear, not control-flow-aware** ([poppy#386](https://github.com/TheAnsarya/poppy/issues/386)). A label reached by a branch that jumps *over* a `rep`/`sep` gets its following `lda #`/`cmp #` mis-sized, misaligning every byte after it. Measured: `cmp #$02` at such a label assembles as `c9 02 00`, and the trailing `00` decodes as a phantom `BRK` — the classic symptom in `m.disassemble(addr)`. **Workaround: open every routine, and every branch-target label, with an explicit `sep #$20`/`.a8` (or `rep #$31`/`.a16`/`.i16`) directive.** Measured to fix it (`c9 02`), and a runtime no-op when the width already matches, so apply it unconditionally rather than reasoning about whether it is needed. Six recurrences before it was understood. This one was deliberately left unfixed: unlike the others it needs a new analysis pass with a false-positive budget, not a contradiction between two existing passes.

   **The rule is enforced mechanically, not by memory** — `tools/rom_audit/check_width_directives.py` (run by `audit_all.py`) flags any branch/jump-target label that reaches a width-dependent immediate (`lda #`, `cmp #`, `ldx #`, …) with no explicit width directive in between. The 196 sites that predate the check are baselined in `check_width_directives_baseline.txt`; it fails on **new** ones only. If it fires, add the directive — never add a baseline line to silence it. (None of the 196 are currently mis-assembled: `check_label_drift.py` reports 0 drifted, which is what this bug's downstream misalignment would show up as. They are latent — one future `rep`/`sep` placed before any of them flips it.)

**Fixed in the fork — do not write workarounds for these, and treat old in-file comments about them as stale:**

| Historical bug | Status |
|---|---|
| `jsl` sized 3 / emitted 4 → cumulative label drift | **Fixed.** New code needs **no** `nop` guards before labels. |
| `bcs`/`bcc` past ±127 assembling silently, hanging the CPU | **Fixed.** All conditional branches *and* `bra` error now, at the right line. |
| Fixed `.org` regions silently truncating into the next one | **Fixed.** Errors: "overlaps previously emitted bytes". |
| `stz.l`, `ldx.l`/`ldy.l`, `cpx.l`/`cpy.l`, `.l Symbol,y` silently accepted | **Fixed.** All hard errors ("no long form for this mode"). |
| Standalone `.dw` data table resolving to garbage | **Fixed.** Resolves correctly; a real table is usable again. |
| Indexed long addressing to a ROM data label computing a wrong base | **Fixed.** `lda.l RomStr,x` resolves correctly. |
| A branch to a dot-prefixed local label being silently deleted | **Fixed.** Dot-locals work. |
| `.include` errors reported under the top-level filename | **Fixed.** Right file, right line. |
| Cross-bank `jsl` resolving with bank byte `$00` | **Fixed** in codegen and, as of `272f7ea`, in the `.sym` export too. |
| An unknown mnemonic silently ignored (poppy#382) | **Fixed** `272f7ea`. Parse errors were collected and then never checked; now they fail the build, with a message that names the token. This was the most dangerous behaviour in the toolchain and it masked the two below. |
| Macros emitting zero bytes (poppy#383) | **Not a bug — the docs were wrong.** Macros work; invocations are `@Name` (not ASAR's `%Name`) and parameters are bare names (not `\param`). `docs/migration-from-asar.md` fixed in `08fe283`. Macros are usable in this project. |
| `.incbin` sized 0 bytes in the layout pass (poppy#384) | **Fixed** `272f7ea`. Labels after a blob resolve correctly, and the `.org` overlap check can finally see blobs — which immediately caught a real 60-byte collision in this repo's own `main.pasm`. |
| `.w` on an indexed banked symbol truncating a long instruction (poppy#385) | **Fixed** `272f7ea`. `sta.w $7E1234,x` is now a hard error. `.l` or bare is still the right thing to write. |
| `-name` lexed as a label, dropping the subtraction in `#$ffff-SIZE` (poppy#388) | **Fixed** `272f7ea`. `End-Start` length expressions work. This had silently broken a camera clamp in `core/screen.pasm` since the port. |

Two constraints remain true regardless of toolchain, because they are 65816 facts and not bugs: **conditional branches reach only ±127 bytes** (Poppy errors now instead of failing silently, but you still have to structure code so it doesn't happen — invert and `brl`, or split into a `jsr`'d leaf routine), and **long addressing is indexed by `X` only** — there is no `nnnnnn,Y` opcode. Also: **`@`-prefixed local labels mis-resolve once the containing file is reached via `.include`** — use fully-qualified global labels in anything meant to be included (this is why `src/core/*.pasm` never uses local labels).

**`python tools/rom_audit/check_label_drift.py` is still worth running after touching any `.pasm`.** Its original reason (label drift) is fixed, but it is now the regression detector for that fix, and it catches the width-tracking bug's downstream misalignment too: it asserts the byte at each label is an opcode for the mnemonic the source puts there, follows `.include`s, and exits nonzero. Don't narrow it with `--start/--end` except to zoom in on something already found. The other `tools/rom_audit/*` scripts cannot catch any of this — they verify that decoded bytes land on real instruction/label boundaries, never that the logic is right, and returned `ALL CHECKS PASS` for as long as the TAD audio driver was unable to load a single byte.

**If you suspect a silent miscompile that is not on either list above, measure it — don't assume.** A dozen lines (`.snes`, `.bank 0`, `.org $8000`, the suspect construct), assembled with `C:\Users\chad\.dotnet\dotnet.exe E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll t.pasm -s t.sym`, then dump the `.bin` bytes and read the `.sym`. Both lists above were built this way, in about ten minutes. File what you find upstream at https://github.com/TheAnsarya/poppy/issues — poppy#382–388 are the house style (repro, command, observed bytes, expected bytes) — and then fix it in the fork at `E:\gh\poppy-astrobleem`, which this project's owner maintains. Every fix belongs with a regression test in `src/Poppy.Tests/Semantics/SilentMiscompileRegressionTests.cs`.

Separately, and unrelated to Poppy: **`build_rom.py`'s hardcoded `RESET`/`NMI`/`IRQ` vector constants must be kept in sync with `main.pasm`'s actual `.org` addresses by hand.** Nothing enforces that, and a mismatch boots the ROM into the wrong code.

### `src/main.pasm` — everything that actually ships

Single linear `.bank 0` file — historically because Poppy's `.bank N` (N != 0) cross-bank label resolution was broken (a `jsl`/`jml` to a non-zero-bank label resolved with bank byte `$00` instead of the true bank). **Re-measured 2026-08-19 against the current fork: this is fixed.** A fresh minimal repro (two banks, `jsl` calls in both directions, a `.dw` pointer table, and back-and-forth `.bank` switching) assembled with the correct bank byte on every `jsl` and placed every routine's bytes at the correct LoROM file offset (`bank*$8000 + (addr-$8000)`) in every direction tested. This matches the toolchain section below, which already lists "Cross-bank `jsl` resolving with bank byte `$00`" as **Fixed** — this paragraph and `plan_vm.md`'s ROM-budget section were the stale holdouts, not the bug. `main.pasm` itself still lives entirely in bank 0 (no reason to churn a working, shipped file), but **a future module (the VM being the concrete case) is not actually confined to bank 0's ~7KB of remaining space — the other ~4MB of banks are real, usable ROM via ordinary `jsl`/`jml`.** `tools/bank_test_*.pasm`'s repro and workaround, and `poppy_assembler_bugs.md` bug 9 in project memory, describe the now-fixed historical bug; don't treat either as current guidance without re-measuring. Fixed `.org` regions, in order:
- `$8000` — SA-1 entry (`sa1_main`, reached via the hardware-forced Character Reset Vector). Draws the test sprite into BW-RAM and configures/arms CC-DMA.
- `$8800` — TAD (Terrific Audio Driver) SPC700 driver, ported from ca65 to Poppy syntax.
- `$AC00` — `LoadAudioData` LoROM-mapping callback.
- `$B000` — the audio data blob itself (`.incbin`).
- `$C100` — `src/core/*.pasm` utility modules (see below).
- `$FC00` — S-CPU entry (`scpu_boot`, the S-CPU reset vector), boots in emulation mode. PPU/CGRAM/VRAM setup, CC-DMA pump loop, then falls into `scpu_main_loop`.
- `$FF20` / `$FF30` — `nmi_handler` / `irq_handler` (pushed here from earlier addresses as boot code grew, and can move again — see the `.org` truncation note above; always cross-check against `build_rom.py`'s printed `NMI:`/`IRQ:` line or `src/main.sym` rather than trusting a hardcoded address here).

**Everything else under `src/`** (`copy_working_test.*`, `exact_copy_test.*`, `minimal_test.*`, `ultimate_test.*`, `vram_test.*`, `with_nmi_test.*`, etc., and `src/sa1/sa1_boot.pasm`, `sa1_blitter.pasm`, `sa1_ccdma.pasm`) are **scratch/experiment files from earlier debugging, not part of the real build**. `build_rom.py` only ever assembles `src/main.pasm`; `sa1_boot.pasm`'s `.bank 1` code specifically is unreachable from the hardware CRV path and dead. Don't assume these files reflect current behavior — `main.pasm` is the only source of truth. Same caveat applies to the standalone `.pasm`/`.bin`/`.pansy` files scattered in `tools/` (`jml_test`, `org_test`, `sym_test*`, `va`-`vf`) — isolated Poppy-bug repros, not build inputs.

### Dual-CPU split: S-CPU and SA-1

- **SA-1 side** (`sa1_main`, `$8000`): draws a sprite into its BW-RAM canvas, then configures and arms SA-1's Character Conversion DMA (CC-DMA).
- **S-CPU side** (`scpu_boot`, `$FC00`): waits for the CC-DMA arm signal (SFR `$2300` bit 5), then reads the converted tile bytes and writes them into VRAM, sets up CGRAM/tilemaps, and enters `scpu_main_loop`.
- These are genuinely two separate 65816 CPUs sharing memory through specific hardware windows — getting the wrong window (S-CPU's BW-RAM view vs. I-RAM view vs. SA-1's own views) is a recurring class of bug here, not a one-off. **CC-DMA in particular is read-triggered, not a batch-copy DMA** — see `build.md`'s "How CC-DMA Type 1 actually works" section for the full mechanism (reverse-engineered from Mesen2's own C++ core source, since the register-level documentation available online is not precise enough to implement this correctly). If you're touching anything CC-DMA-, BW-RAM-, or VRAM-address-related, read that section first — there are also real word-vs-byte unit traps in `BG12NBA`/`BGxSC` and the CC-DMA source-address registers that have caused multiple real bugs.

### `src/core/*.pasm` — ported engine utility modules

Adapted from SNES-SuperBossGaiden (WLA-DX → Poppy syntax), `.include`d into `main.pasm` at `$C100`, `Init` routines called from `scpu_boot`:
- `random.pasm` — 8-bit PRNG.
- `input.pasm` — controller press/trigger/old-edge detection via hardware auto-joypad-read; `Core_Input_Poll` runs every main-loop iteration.
- `math.pasm` — multiply/divide/min/max/abs helpers.
- `error.pasm` — crash-screen handler for catching bugs under an emulator debugger.
- `dma_channel.pasm` — allocator for the 8 hardware DMA channels.
- `dma.pasm` — software DMA request queue (`Core_Dma_Enqueue`/`ProcessQueue`), drained once per frame from `Core_Nmi_Play`. Fixed to hardware channel 7.
- `allocate_wram.pasm` / `allocate_vram.pasm` / `allocate_cgram.pasm` — fixed-block allocators for their respective memory spaces.
- `oam.pasm` — OAM shadow buffer; `Core_Oam_Play` (called once per main-loop iteration) packs and enqueues the upload, `Core_Nmi_Play` performs the actual DMA.
- `nmi.pasm` — the shadow-register commit system. Every PPU register the game touches is buffered in WRAM and committed to hardware in one pass by `Core_Nmi_Play` (called from `nmi_handler`). **`scpu_main_loop` must call `Core_Nmi_WaitFrame` once per iteration** (a busy-wait on `Nmi_FrameCounter`) to stay paced to real vblank — omitting this lets the loop spam DMA-queue-consuming calls (like `Core_Oam_Play`) far faster than once per frame, which was confirmed to overrun `Core_Nmi_Play`'s forced-blank commit bracket into active display and corrupt the top of every rendered frame. Any new per-frame subsystem that unconditionally enqueues DMA work is a candidate for repeating this same bug.
- `oop.pasm` — class-based object dispatch (`RegisterClass`/`Create`/`Play`/`Kill`/garbage collection). `Core_Oop_Play` runs every main-loop iteration.
- `screen.pasm` — camera/screen/focus-target engine. `Core_Screen_Play` runs every main-loop iteration.

None of these files use Poppy's `@`-local label syntax (see the `.include` bug above) — match that convention in anything new added here.

## Register/memory maps, MSU-1 protocol, CC-DMA mechanism

`build.md` has the full SA-1/CC-DMA register table, the MSU-1 register protocol, and (most importantly) the reverse-engineered explanation of how CC-DMA Type 1 conversion actually works end-to-end — read it before touching anything in that area rather than re-deriving it from register-bit docs, which are not precise enough on their own to get this right.
