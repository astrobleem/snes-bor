# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A SNES (Super Nintendo) hardware-pipeline proof-of-concept targeting real SA-1 coprocessor hardware, with MSU-1 asset streaming and a ported Terrific Audio Driver (TAD). **This is not a playable game** — two independently-animated characters render simultaneously (both streamed at runtime from an MSU-1 asset roster, `tools/bor_converter/`), one dpad-driven and one AI-driven that seeks the player and lands stunning attacks, but there's no level content, no health/damage system, and no game loop. It proves out the low-level hardware plumbing (SA-1 boot, CC-DMA sprite conversion, OAM/NMI frame commit, MSU-1 streaming, TAD audio) plus a minimal entity layer on top, so a real game can be built later. See `README.md`'s "Current Status" section for the authoritative, currently-accurate list of what's verified working vs. not built — check it before assuming something works or is missing.

`SNES-BOR-Engine-Prompt.md` is the original design spec for the full engine; much of it is still unbuilt. **`plan.md` is the live roadmap — its "Part Two" section is the current, step-by-step plan for everything not yet done, and is where you should start if you're picking up new work.** `core/*.pasm` (see Architecture below) is adapted from [SNES-SuperBossGaiden](https://github.com/snesdev0815/SNES-SuperBossGaiden) under the original author's personal permission — adapt freely, it does not need to stay a literal port.

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
- Poppy CLI itself lives in a separate repo, `E:\gh\SNES-CrimePatrol\tools\poppy-src`, and must be built once (`dotnet build Poppy.CLI\Poppy.CLI.csproj -c Release`) before `build_rom.py` can call `poppy.dll`.

There is no lint step and no unit-test framework — see Testing below for how correctness is actually checked.

## Testing

There's no automated test suite. Correctness is checked by loading `distribution/bor.sfc` in Mesen2 (an accurate SA-1 emulator) via its Python MCP debugging layer:

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

This project uses the **Poppy** 65816 assembler (a from-scratch tool in a sibling repo, `net10.0`), not the WLA-DX toolchain the `makefile`/`tools/wla-65816`/`tools/wlalink` binaries suggest (those are leftover from before the switch — ignore them; `build_rom.py` is the real build). Poppy has multiple confirmed silent-miscompile bugs (wrong bytes emitted with no error) that any new `.pasm` code must work around — **read `src/core/dma_channel.pasm`, `dma.pasm`, `allocate_wram.pasm`, `math.pasm`, and `error.pasm`'s header comments, and `main.pasm`'s inline comments, before writing new assembly**, especially around: indexed access to banked (`$7E`) symbols (`.w` silently drops the bank byte — always use `.l` or bare), macro invocations inside branch-skipped code (sized as 0 bytes during address estimation, corrupting the branch offset), branch-target labels that can resolve a couple bytes early relative to the real instruction stream (pad with `nop`), indexed long addressing to ROM data labels computing a wrong base address, and standalone `.dw` data-table blocks resolving to garbage regardless of placement (work around by inlining small tables as immediates instead of a referenced table).

Two more that between them account for most recent lost time, and that any new code must be written defensively against from the start:
- **Accumulator-width tracking is linear, not control-flow-aware** (six recurrences). Poppy sizes immediate operands by reading the file top-to-bottom, so any label reached by a branch that jumps *over* a `rep`/`sep` gets its following `lda #`/`cmp #` mis-sized, misaligning every byte after it. Symptom: `m.disassemble(addr)` shows a phantom `BRK #$xx` mid-routine. **Workaround: open every routine, and every such branch-target label, with a redundant `sep #$20`/`.a8` (or `rep`) re-sync.** It's a runtime no-op when the CPU is already in that width, so apply it unconditionally rather than reasoning about whether it's needed.
- **A conditional branch past ±127 bytes assembles with no error whatsoever** and hangs the CPU at runtime (symptom: `Nmi_FrameCounter` freezes, every WRAM read returns a fixed value). Note this differs from the already-known `bra`-range bug, which *does* error. Keep conditional branch targets within ~15 source lines; if farther, invert the condition and `brl`, or split into a `jsr`'d leaf routine.

Neither is catchable by `tools/rom_audit/*` — those tools verify that decoded bytes land on real instruction/label boundaries, never that the logic is right, and returned byte-identical clean results across a change that left the ROM completely broken. Only live Mesen2 testing plus direct disassembly finds these. Also: `@`-prefixed local labels mis-resolve once the containing file is reached via `.include` — use fully-qualified global labels in anything meant to be included (this is why `src/core/*.pasm` never uses local labels).

**Fixed `.org` directives silently truncate.** Poppy does not error when code between two fixed `.org` points overflows the gap — it silently corrupts whatever runs into the next `.org`. This has already forced the NMI/IRQ vectors in `main.pasm` to be pushed twice as `scpu_boot` grew. After growing any code between fixed `.org` regions, check symbol addresses with Poppy's `.pansy` sidecar file (symbol table) to confirm nothing overran — and keep `build_rom.py`'s hardcoded `RESET`/`NMI`/`IRQ` vector constants in sync with `main.pasm`'s actual `.org` addresses by hand; nothing enforces that automatically.

### `src/main.pasm` — everything that actually ships

Single linear `.bank 0` file (deliberately — Poppy's `.bank N` (N != 0) handling is confirmed broken: a label defined under a non-zero bank has its *bytes* emitted correctly at that bank's real file offset, but any reference to it (`jml`/`jsl`/`lda #`) resolves with bank byte `$00` instead of the true bank — nothing is dropped, but every cross-bank reference silently jumps to the wrong place. See `tools/bank_test_*.pasm` for the isolated repro and a confirmed workaround (an explicit numeric `bank:offset` literal, e.g. `jsl $01:8000`, bypasses the broken label resolution — the offset half is correct, only the bank byte needs a manual fix, same fixup-constant pattern as the other Poppy bugs below). Bank 0 confinement here is a standing caution, not a hard blocker, if a future session wants to use the ROM's ~4MB of otherwise-unused space (see `poppy_assembler_bugs.md` bug 9 in project memory). Fixed `.org` regions, in order:
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
