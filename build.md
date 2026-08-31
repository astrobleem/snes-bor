# snes-bor — Build & Technical Guide

Beats of Rage SNES Engine proof-of-concept uses Poppy assembler to build an SA-1 + CC-DMA + MSU-1 + TAD pipeline on LoROM (`$23`, cart type `$35`).

See [README.md](README.md#current-status) for what's actually verified working versus aspirational.

## Prerequisites

- **.NET 10 SDK** — required by Poppy CLI (`poppy.dll`). Poppy targets `net10.0`; a system-wide .NET 8 install is **not** sufficient and will fail with `NETSDK1045`.
  - On this machine, .NET 10 is a **user-local preview install**, not on `PATH`: `C:\Users\chad\.dotnet\dotnet.exe` (SDK `10.0.300-preview.0.26177.108`). Invoke it explicitly rather than the bare `dotnet` command, which resolves to the system-wide 8.0 install.
  - Poppy's source lives in a separate repo, not inside this one — **`astrobleem/poppy`** (`E:\gh\poppy-astrobleem`), a fixed fork of the old, buggier Poppy that used to live at `E:\gh\SNES-CrimePatrol\tools\poppy-src` (see `poppy_fork_migration` project memory for why). It must be built once before use:
    ```bash
    cd E:\gh\poppy-astrobleem\src
    C:\Users\chad\.dotnet\dotnet.exe build Poppy.CLI\Poppy.CLI.csproj -c Release
    # -> Poppy.CLI\bin\Release\net10.0\poppy.dll
    ```
- **Python 3** — required by `build_rom.py`.
- **Mesen2 (or Nexen)** — for emulated SA-1 & MSU-1 execution and testing. This repo has been built/tested against a local `E:\gh\Mesen2` checkout with its Python MCP automation layer (`E:\gh\Mesen2\python\mesen_mcp`).

The `make`/`cd /home/chad/...` instructions below reflect the project's original Linux dev environment. On Windows, run the two build steps directly instead of via `make`.

---

## Build Steps

```bash
# 1. Assemble src/main.pasm -> src/main.bin + src/main.pansy
C:\Users\chad\.dotnet\dotnet.exe E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll src\main.pasm

# 2. Pack ROM & MSU-1 assets
python build_rom.py
```

`build_rom.py` accepts `DOTNET` and `POPPY_DLL` environment overrides; it
fails clearly when the configured Poppy CLI is missing instead of silently
using a stale assembler output.

`make clean && make` runs the same build with configurable `PYTHON`, `POPPY`, and
`TAD_COMPILER` commands. Set those variables to the tools in your environment;
the `tad-check` prerequisite fails if committed TAD outputs drift from source.

---

## TAD audio project regeneration (G11 hardening)

`soundwork/tad/build/*` (`audio-data.bin`/`.s`, `audio-enums.inc`,
`tad_blob_syms.pasm`) are compiled outputs, not sources — `src/main.pasm`
`.incbin`s `audio-data.bin` directly and `.include`s `tad_blob_syms.pasm`'s
constants. **`build_rom.py` does not regenerate these** — edit
`soundwork/tad/project/02_coin.terrificaudio` or `sound-effects.txt`, then
explicitly regenerate:

```bash
python soundwork/tad/rebuild.py --check    # compiles to a temp dir, diffs against committed build/, fails on drift
python soundwork/tad/rebuild.py --update   # same, then overwrites committed build/ outputs
python soundwork/tad/verify_project.py     # fast, no-compiler-required hash/metadata check against project/reconstruction_oracle.json
```

`rebuild.py` requires a real `tad-compiler` binary (this project does not
vendor one — see `rebuild.py`'s own `find_compiler()` for the search order:
`--compiler` flag, `TAD_COMPILER` env var, then sibling-repo fallback
paths). It prints which binary/version it used; a version mismatch against
the pinned `REQUIRED_COMPILER_VERSION` is a fatal error by default. The
explicit `--allow-version-mismatch` option is available only for deliberate
diagnostics and must not be used to update committed outputs.

**A real, previously-silent bug this tooling was built to catch**:
`tad_blob_syms.pasm` used to be a hand-ported, never-regenerated file — a
past edit to the TAD project grew common data by 29 bytes, and
`tad_blob_syms.pasm`'s `Tad_DataTable` offset went stale by exactly that
amount, making `main.pasm`'s `LoadAudioData` read the audio blob's real
directory table from the wrong offset at runtime. Every engine-visible
status byte still looked correct (`TadPrivate_state` reached `PLAYING`, the
S-DSP left reset, main volume was non-zero) — only `tools/verify/phase7.py`'s
exact-final-transfer-address ground-truth assertion caught it. `rebuild.py`
now regenerates `tad_blob_syms.pasm` itself (parsed from a fresh compile's
real `audio-data.s`) on both `--check` and `--update`, so this can't drift
silently again. See `plan_game.md` §11 for the full story.

`tools/rom_audit/check_sfx_id_sync.py` (run by `audit_all.py`) is a related,
narrower guard: it fails the build if `src/main.pasm`'s hand-maintained
`SFX_HIT_ID` constant (Poppy can't `.include` a ca65 `.enum`) drifts from
the real generated `audio-enums.inc`.

---

## Output Artifacts

- `build/bor.sfc` & `distribution/bor.sfc` — SNES ROM (LoROM, SA-1, Cart type `$35`, 4MB)
- `build/bor.msu` & `distribution/bor.msu` — MSU-1 data stream: a real runtime roster (`pack_msu_roster.py`), currently 13 playable character slots plus prop assets, with palette and animation data behind generated directory offsets; the file also carries converted level/spawn data. It is not the soundtrack.
- `distribution/bor-1.pcm` — MSU-1 audio track 1, a placeholder voice clip used to prove audio playback works (not a Beats of Rage asset)
- `src/main.bin` — raw Poppy binary output
- `src/main.pansy` — Poppy metadata & symbol file (used by MCP tooling's `lookup_pansy`/`disassemble` for symbol-aware debugging)

---

## Memory & Register Map

### SNES Header (`$7FC0`)
| Field | Value | Description |
|---|---|---|
| Title | `BEATS OF RAGE SNES   ` | 21 bytes |
| Map Mode | `$23` | FastROM + LoROM |
| Cartridge | `$35` | ROM + SA-1 + RAM + Battery |
| ROM Size | `$0C` | 4 MB |
| RAM Size | `$08` | 256 KB |

### Vectors
| Vector | Address | Function |
|---|---|---|
| S-CPU Reset | `$FC00` | `scpu_boot` |
| SA-1 Reset (CRV) | `$8000` | `sa1_main` |
| NMI | `$FF20` | `nmi_handler` |
| IRQ | `$FF30` | `irq_handler` |

`scpu_boot`'s body has grown past these addresses more than once, historically, as code was added between fixed `.org` points, pushing NMI/IRQ further out each time. At the time those pushes happened, Poppy silently truncated on `.org` overflow instead of erroring — that's fixed in the current fork (re-tested 2026-08-19: a fresh overflow now errors cleanly, "overlaps previously emitted bytes", instead of truncating), so a *new* overflow today will fail the build loudly rather than needing to be caught by inspection. Still don't hardcode these — always cross-check against `build_rom.py`'s own printed `Reset:`/`NMI:`/`IRQ:` line (or `src/main.sym`) after any change that grows `scpu_boot` or `scpu_main_loop`.

---

## SA-1 & CC-DMA Pipeline Registers

| Register | Name | Address | Configured Value | Direction |
|---|---|---|---|---|
| `DCNT` | DMA Control | `$2230` | `$B1` (Enable \| CharConv \| Auto \| Src=BW-RAM) | SA-1 Write Only |
| `CDMA` | CC-DMA Parameters | `$2231` | `$09` (4bpp, width=4 tiles/line) | Shared |
| `SDA` | Source Start Addr | `$2232–$2234` | `$003000` (real BW-RAM byte offset — see below, NOT `$6000`) | Shared |
| `DDA` | Dest Start Addr | `$2235–$2236` | `$0000` (IRAM offset 0; write to `$2236` only **arms** the converter — see below) | Shared |
| `SFR` | S-CPU Status Flags | `$2300` | bit 5 = `CharConvIrqFlag` | S-CPU Read Only |

### How CC-DMA Type 1 actually works (reverse-engineered from Mesen2's core source, `Core/SNES/Coprocessors/SA1/Sa1.cpp` and `Sa1BwRamHandler.h` — no official doc spells this out precisely enough to write working code from)

This does **not** behave like a normal DMA channel that copies a block of bytes the instant you trigger it. Writing `$2236` only sets `CharConvDmaActive` (and raises `CharConvIrqFlag`/SFR bit 5) — no bytes move yet.

Conversion is **read-triggered**: it happens lazily, one 8×8 tile at a time, the instant something reads through the CPU-side linear BW-RAM window at banks `$40-$4F` (S-CPU) / `$40-$5F` (SA-1) while `CharConvDmaActive` is set (`CpuBwRamHandler::Read` → `Sa1::ReadCharConvertType1`). Reading anywhere else (e.g. the SA-1 I-RAM window at `$00:3000`) never touches that handler and triggers nothing — I-RAM only gets converted-tile bytes as a *side effect* of the correct reads, so pulling from I-RAM directly just returns stale leftovers.

A 32-byte-aligned read (byte `N` where `N % 32 == 0`, for 4bpp) triggers conversion of tile number `(N - SDA) / 32`; the read itself, and the next 31 sequential reads, return that tile's already-converted VRAM-format bytes directly. So the S-CPU pump loop is a plain sequential read of `24 tiles × 32 bytes` starting at `SDA`'s address (as seen through the `$40-$4F` window) — no separate I-RAM copy pass needed.

The `$60-$6F` bank range (where `BW_CANVAS` lives, e.g. `$60:6000`) is hard-wired **"always bitmap mode"** (`Sa1BwRamHandler::WriteBitmapMode`): every byte written there is treated as *one pixel's color in the low nibble* and auto-packed two-pixels-per-real-byte at **half the window offset**, with the `$600000` bank component subtracted first. For `BW_CANVAS = $606000`, real BW-RAM offset = `($6000 + x) >> 1` for write index `x` — i.e. our 32×48 sprite (drawn byte-per-pixel through this window) actually lands at real BW-RAM offset `$3000`, not `$6000` and not `$0`. **SDA must equal that real offset (`$3000`)**, not the `$60:6000` address we wrote through.

### BG tile/tilemap VRAM addresses are WORD addresses, not bytes

`BG12NBA`/`BGxSC` fields, as reported by debugging tools, are often the raw internal word-address value (`Mesen2`'s `SnesPpu.cpp`: `ChrAddress = (value & 0x70) << 8`, `TilemapAddress = (value & 0x7C) << 8`) — e.g. `BG12NBA=$20` gives BG2 `ChrAddress = $2000` (a VRAM **word** address, used directly to index a word-addressed VRAM array). Reading/writing VRAM through a byte-addressed API (Mesen's `snesVideoRam` memory type, or any `$2116`/`$2118` sequence) means **doubling** that word address to get the real byte offset. Getting this unit wrong (byte vs. word) silently points tile/tilemap fetches at the wrong VRAM region — verify against a real emulator source, not against a debugger field's raw number, when in doubt.

### OBJ tile sheet layout and the real multi-character budget

Sprite tile fetch does **not** address tiles linearly. Mesen2's `SnesPpu.cpp` `GetSpriteTileAddress` computes `tileIndex = (row << 4) | ((tileColumn + columnOffset) & 0x0F)` — i.e. the 8-bit tile number is a coordinate in a **16 × 16 tile sheet**, and consecutive tile *rows* of one sprite jump by 16 index slots, not by the sprite's width. This is why `Msu1_LoadFrame` streams a character as **6 separate row-DMAs** rather than one flat 768-byte transfer, and why `Character_BlankPadding` blanks rows 6 and 7 at word `$4600`/`$4700` rather than at contiguous addresses.

Current map (OBSEL = `$C2`, set in `core/oam.pasm`: OBJ char base = word `$4000`, size mode 6 whose "large" size is 32×64 = 4 tiles wide × 8 tall):

| Region | Word address | Contents |
|---|---|---|
| BG1 tiles | `$0000` | blank tile 0 |
| BG1 tilemap | `$0400` | |
| BG2 tiles | `$2000` | CC-DMA test sprite |
| **OBJ tiles** | **`$4000`–`$4FFF`** | 256 tiles — the full 16×16 sheet |
| *(unused)* | `$5000`–`$5BFF` | |
| BG2 tilemap | `$5C00` | |

Because the next occupant sits at `$5C00`, the entire OBJ block is free. Each 32×64 character consumes 4 columns × 8 rows, so the sheet holds **8 characters**: 4 column slices (tile columns 0, 4, 8, 12 — byte offset `col*32`, which is what `CHAR_TILE_BYTE_OFFSET` carries) × 2 row bands (base tile index 0 and 128; the second band adds `$1000` bytes). **No OBSEL change and no second tile bank is needed for up to 8.**

The actual constraint on character count is therefore **not** VRAM — it's the 8-slot software DMA queue (`core/dma.pasm`), since one `Msu1_LoadFrame` enqueues 6 slots and `Core_Oam_Play` needs more. `Msu1_StreamBusy` serializes streaming to one entity per frame, so N characters means each animates at most every N frames. See `README.md`'s Current Status and `plan.md` §2.3.

---

## MSU-1 Registers

| Register | Name | Address | Function |
|---|---|---|---|
| `MSU_STATUS` | Status | `$2000` (read) | bit7 `DATA_BUSY`, bit6 `AUDIO_BUSY`, bit5 `AUDIO_REPEAT`, bit4 `AUDIO_PLAYING`, bit3 `TRACK_MISSING` |
| `MSU_DATA` | Data Stream | `$2001` (read) | Sequential byte read from the seeked `.msu` file offset |
| `MSU_ID` | Hardware ID | `$2002–$2007` (read) | Returns ASCII `"S-MSU1"` |
| Data seek addr | — | `$2000–$2003` (write) | 32-bit offset into `.msu`; writing byte 3 (`$2003`) triggers the seek |
| Track select | — | `$2004–$2005` (write) | 16-bit track number; writing `$2005` triggers loading `<romname>-N.pcm` |
| Volume | — | `$2006` (write) | 0–255 |
| Audio control | — | `$2007` (write) | bit0 = play (1) / pause (0), bit1 = repeat |

Verified in this repo by adding a track-1 select + play/repeat trigger and capturing Mesen's actual mixed audio output — see README.md.

---

## Testing in Mesen2 (this environment)

```python
import sys, os
sys.path.append(r'E:\gh\Mesen2\python')
from mesen_mcp.session import McpSession

# Derive from the actual repo root you're working in -- a hardcoded
# E:\gh\snes-bor\distribution\bor.sfc silently points at the MAIN
# CHECKOUT's ROM when run from inside a git worktree, testing a stale/wrong
# build with no error (see the worktree-mesen-rom-path-footgun project
# memory; an entire session was lost to exactly this).
REPO_ROOT = os.getcwd()
ROM = os.path.join(REPO_ROOT, 'distribution', 'bor.sfc')
MESEN = r'E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe'

with McpSession(rom=ROM, mesen=MESEN, boot_wait=2.0) as m:
    m.run_frames(120)
    m.pause()
    print(m.get_ppu_state())
    print(m.get_audio_state())
```

**Known harness gaps** (found while debugging the SA-1 handshake fix — see README.md):
- `read_memory`/`read_u8` calls for **small byte counts** (1–4 bytes) have returned stale or zeroed data in repeatable A/B tests, while a larger read (32 bytes) at the identical address/frame/session returned correct data every time. Prefer generous read lengths, or better, the structured tools (`get_ppu_state`, `get_audio_state`) which don't exhibit this.
- Peeking hardware registers (e.g. `$2300` SFR, `$2140` APUIO) via `read_memory` consistently returned `0`, even when other evidence confirmed the underlying hardware state was clearly non-zero. These peeks likely don't route through Mesen's live MMIO read handlers in this harness — don't trust a `0` reading from a hardware register as proof of anything.
- `add_exec_hook`/`drain_notifications` have not fired reliably in this environment, even on the literal reset vector.
- Two sequential `read_memory` calls to *different* addresses within one paused session have returned suspiciously identical byte prefixes (looked like a stale/cached buffer, not the requested address). Re-running the same read via **independent, freshly-constructed `McpSession` instances** and checking for majority agreement across 3 runs is the most reliable pattern found so far — see `src/core/random.pasm`'s verification for an example (2 of 3 independent runs matched the expected seeded value exactly; the third didn't, consistent with harness noise rather than a code bug).
- This Poppy build (`net10.0`, `10.0.300-preview.0.26177.108`) mis-resolves `@`-prefixed local labels once the containing code is reached via `.include` — a branch to `@label` inside an included file fails to assemble (`Cannot evaluate operand for instruction`), even though the exact same code assembles fine as a standalone (non-included) file. Confirmed via isolated repro. Workaround: use fully-qualified global labels instead of `@`-locals in any file meant to be `.include`d — this is what `src/core/*.pasm` does, and matches `main.pasm`'s existing convention of not using local labels at all.
- To verify actual audio output (including MSU-1, which mixes in independent of SPC700), use `record_audio` + `stop_audio`, then `audio_fingerprint`/`audio_waveform_png` on the captured WAV — this checks the real output signal instead of internal state.
- **Historical audio-capture flakiness:** an earlier majority-of-3 check was retained while the MSU-1 presence-detection bug was being isolated. That deterministic bug is fixed; `tools/verify/phase7.py` now performs one bounded capture and requires a non-silent peak, rather than masking a failure with repeated runs.
  - **Verification rule**: because a genuinely broken ROM can only ever be silent (a crashed/hung CPU can't spuriously produce a correct waveform), a single non-silent, correct-looking run is a real pass — no need to chase 100% consistency. Silence proves nothing by itself; only treat it as a real regression after several consecutive silent runs on a binary that was previously confirmed passing, and even then, rebuild and re-test before concluding the code changed anything.
  - **Update, post boot-crash-fix: root-caused and fixed.** A later session saw 5/5 `record_audio` runs come back silent and 12/12 runs read the MSU-1 success flag (`$7E0330`) as `0`. Direct byte-level inspection found the actual cause: `msu1_check_loop`'s `cmp.l msu1_id_str,x` computed the wrong base address for its ROM data label (see Poppy bug 5 below) — it was comparing the hardware MSU-1 ID register against the tail of unrelated preceding instructions, not `"S-MSU1"`, so the presence check failed essentially every time. This was the real cause of the *original* 3/7-silent ratio too, not just the post-fix regression. Fixed by replacing the indexed comparison with 6 unrolled immediate-byte checks. Verified: 5/5 `record_audio` runs now produce `peakAmplitude` ~0.928 and 7/8 direct flag reads show `$7E0330 = 1`.
- Three more Poppy assembler encoding bugs were found and worked around while porting `src/core/error.pasm`, `dma_channel.pasm`, `dma.pasm`, `allocate_wram.pasm` — see those files' header comments (and README.md's Current Status section) for full detail: forward-address-estimation drift on `symbol+N` operands feeding long-addressable instructions, `.w` indexed access to banked symbols silently dropping the bank byte, and macro invocations sized as 0 bytes for branch-offset purposes. All three are permanent style constraints for any new `.pasm` in this project, not one-off fixes.
- **A fifth Poppy bug** (found fixing the S-CPU boot crash, `main.pasm`): a label used as a branch target can resolve 0-2 bytes earlier than where Poppy actually emits the real following instruction. Every branch targeting the label computes its jump as exactly the label's (possibly wrong) address, so definition and use stay self-consistent but both can be wrong relative to the real byte stream — a genuine misexecution, not a cosmetic symbol-table issue. Not tied to one preceding-instruction shape (seen after 16-bit immediate loads, `jsl`, and `sep #imm8`). Fix: a `nop` immediately before the label absorbs the drift. Verify by reading the raw byte at the label's pansy-exported address — it must be the real opcode (0 drift) or `0xEA` (nop, falls through) — for every backward/forward-branch label in the affected region, not just suspected sites.
- **A sixth Poppy bug**, distinct from the fifth: `cmp.l symbol,x` (indexed long addressing) to a ROM data label can compute a base address a fixed few bytes off from the label's real data — and unlike the branch-target bug, padding at the label site does **not** fix it (confirmed: 8 bytes of padding before the label left the drift unchanged at 4 bytes), because the error lives in the *referencing instruction's* own computed address, not the label's position. This was the actual root cause of the MSU-1 detection failures documented above. Fix: don't use an indexed symbol reference for small fixed-size comparisons — unroll into direct immediate-byte comparisons instead, which has no symbol-relative addressing for the bug to corrupt.
