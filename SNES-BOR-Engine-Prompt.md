# Prompt: SNES Beats of Rage Engine — Proof-of-Concept

**Prepared for:** Kimi Coding Agent  
**Author:** astrobleem  
**Date:** 2026-07-29  
**Target Game:** Beats of Rage Original (`Beats of Rage Original [v.3.0 Build 4086].pak`, 59.8M)

> **This is the original design spec, not a status report.** It describes the full intended engine (player, enemies, AI, scrolling, asset converter, etc.). As of 2026-07-30, only a small slice of §3 (the SA-1 canvas + CC-DMA pipeline, the TAD boot handshake, and MSU-1 audio playback) has any implementation, and even that slice has open verification gaps. Everything in §4 onward (game loop, entities, the asset converter in §5, and the full deliverable list in §8) is unbuilt. See [README.md](README.md#current-status) for what's actually true right now.

---

## 1. Mission

Design and implement a minimal, working proof-of-concept beat-'em-up game engine for the Super Nintendo Entertainment System with SA-1 enhancement chip. The engine must use **software rendering into a BW-RAM framebuffer** combined with **SA-1 Character Conversion DMA** to display animated characters on a background layer, bypassing the SNES's 128-sprite / 32-sprite-per-scanline hardware limitation.

The goal is to prove that a *Streets of Rage*-style crowd brawler with 4+ large enemies on screen is achievable on real SA-1 hardware.

Use **Beats of Rage (BOR)** assets (sprite sheets, palettes, animation metadata) as the reference art pipeline. Do not attempt to port the BOR engine itself; instead, build an SNES-native engine that can ingest and display BOR-format assets within SNES/SA-1 constraints.

**All assembly source must be written as `.pasm` for the Poppy compiler.** The build pipeline is Poppy → Game Garden roundtrip verification. This is non-negotiable.

---

## 2. Existing Toolchain — Do Not Rebuild, Reuse

The following repositories contain working patterns. Reference them directly. Do not reinvent.

| Pattern | Source Repository | What to Reuse |
|---|---|---|
| **Build system & assembler** | `supermn-snes` | **Poppy compiler** (`.pasm` → ROM). Game Garden roundtrip verification. Build scripts and `make` workflow already configured on host. |
| **SA-1 bringup & CC DMA** | `supermn-snes` | SA-1 BW-RAM address mapping (`$2225`), CC DMA control registers, IRAM mailbox protocol, non-blocking SA-1/S-CPU pipeline. All proven in Poppy assembly. |
| **MSU-1 streaming** | `SNES-SuperDragonsLairArcade` | "Tile-cache-from-a-fast-store" model: MSU-1 SD card as live cache, DMA channel 7 NMI tile transfer. |
| **Audio** | `supermn-snes` | **Terrific Audio Driver already ported to Poppy.** Reuse TAD project structure, MML syntax, and `tad-compiler.exe` invocation exactly as wired in Superman. |
| **Poppy / Game Garden** | `supermn-snes` | Assembly source is `.pasm`. Roundtrip byte-identical rebuild verification via Game Garden. Do not deviate from this pipeline. |
| **MCP Debugging** | `Mesen2` (mcp-server branch) | Nexen MCP server for live debugging, state inspection, screenshot capture. `mesen_inproc_bridge.py` and `smi_workflow_server.py` patterns. |
| **Python asset pipeline** | `SNES-SuperMonkeyIsland/tools/` | `snes_costume_converter.py`, `snes_room_converter.py`, `rom_pack_data.py` — these are the **model** for the BOR offline converter, but they emit Poppy-compatible `.inc` files. |
| **FXPAK Pro deployment** | `SNES-SuperMonkeyIsland/tools/` | `fxpak_push.py`, `fxpak_debug.py` for hardware testing. |

**Critical constraint:** All 65816 assembly must be written as `.pasm` source for the Poppy compiler. The build command is the Poppy/Game Garden roundtrip, not WLA-DX. The TAD audio integration must match the Superman project's Poppy-native TAD wiring exactly.

---

## 3. Core Architecture

### 3.1 Dual-CPU Division of Labor

- **S-CPU (main 65816 @ ~3.58 MHz):** Handles game loop, controller input, PPU register updates, HDMA, audio (SPC700 driver), and BG tilemap updates. Does NOT touch sprite data directly.
- **SA-1 (10.74 MHz):** Handles all software rendering. Composites enemy frames into a BW-RAM framebuffer, runs animation state machines, collision box math, and triggers Character Conversion DMA during VBlank.

### 3.2 The Software Sprite Canvas

Maintain a rectangular pixel buffer in SA-1 BW-RAM (2 Mbit / 256 KB total, shared with S-CPU via bank switching).

- **Canvas Size:** `128 pixels wide × 96 pixels tall` (12,288 bytes at 4bpp).
- **Bit Depth:** 4bpp (16 colors per 8×8 tile).
- **Coordinate System:** Canvas anchored to a fixed screen position (e.g., centered horizontally, lower third of screen). All software-sprite enemies render into this window.
- **Sub-Tile Positioning:** Enemies may be positioned at pixel granularity. The SA-1 must handle unaligned blits that touch up to four adjacent 8×8 tiles per sprite pixel row.

### 3.3 SA-1 Character Conversion DMA Pipeline

The SA-1's Character Conversion DMA (CC-DMA) is the critical hardware feature. It converts linear bitmap data in BW-RAM into SNES-native 4bpp bitplane format and transfers it to VRAM autonomously.

- **Source:** BW-RAM canvas buffer (linear format: 4 bits per pixel, packed as bytes).
- **Destination:** VRAM address `0x2000` (or user-defined), mapped to **BG2** tiles.
- **Tile Dimensions:** 32×32 tiles (1024 pixels = 512 bytes at 4bpp). CC-DMA supports 16×16, 32×32, and 64×64 source sizes.
- **Format Conversion:** CC-DMA automatically performs the bitplane interleave (planes 0+1, then 2+3). The SA-1 CPU only writes linear pixels.
- **Trigger:** SA-1 sets `CCDMA` control registers during VBlank, then the SA-1 DMA unit handles the transfer. The S-CPU must not access BW-RAM during this window.

**VRAM Budget Math:**
- 128×96 canvas = 16 tiles wide × 12 tiles tall = **192 tiles**.
- 192 tiles × 32 bytes (4bpp) = **6,144 bytes** of VRAM per frame.
- At 60 Hz, you have ~5.5 KB of safe DMA bandwidth per VBlank. At 30 Hz (update every other frame), you have ~11 KB. **Target 30 Hz canvas updates** to stay within safe limits while allowing ~6KB payload. This is acceptable for enemy animations.

### 3.4 BG Layer Assignment

- **BG1:** Level background (parallax capable, Mode 1). Standard tilemap, 8×8 or 16×16 tiles.
- **BG2:** The **software sprite layer**. A 16×12 tilemap window (256×192 screen pixels, though only 128×96 are active canvas). The remaining tilemap entries are set to transparent (tile 0).
- **BG3:** HUD, health bars, score, names. 2bpp mode, fixed position, high priority.
- **OAM Sprites (hardware):** Reserved exclusively for player characters, projectiles, weapon pickups, and transient particle effects. These need true per-pixel positioning and fast movement.

### 3.5 Palette Management

Each 8×8 tile in the BG2 tilemap carries a 3-bit palette selector in the tilemap attributes. This means the 128×96 canvas can use up to **8 different 16-color palettes simultaneously**, assigned per-tile.

- **Palette 0:** Transparent (color 0 = transparent for all tiles).
- **Palettes 1–7:** One per enemy type, or split between enemy + effects.
- **Constraint:** Each 8×8 tile can only reference one 16-color palette. Large enemies must be authored such that any 8×8 region fits within 15 colors + transparency. BOR assets may need palette quantization or tile-level palette assignment preprocessing.

### 3.6 Priority System (Depth Sorting)

BG2 has its own priority bit in the tilemap. You can make software-sprite enemies walk behind fence posts on BG1 simply by flipping priority bits, something that costs you an entire sprite layer in hardware-sprite engines.

**Player vs. Enemy depth:** Each 8×8 tile in BG2 carries a priority bit. When the player (OAM sprite) is "behind" an enemy, set the enemy's BG2 tile priority low so the OAM sprite renders on top. When the player is "in front," set priority high. This gives true depth sorting between OAM player and software-sprite enemies.

### 3.7 MSU-1 as Live Asset Cache

Following the Super Dragon's Lair pattern:
- **Music streams** from MSU-1 PCM tracks.
- **Animation frames for inactive enemies** live on the MSU-1 SD card. When an enemy spawns or changes animation, the SA-1 DMAs the frame data from MSU-1 → BW-RAM → VRAM. This effectively gives unlimited animation storage; only active frames occupy BW-RAM.
- **Level tile data** streams from MSU-1 during horizontal scrolling, using the tile-cache-from-a-fast-store model.

### 3.8 S-CPU ↔ SA-1 Communication Protocol

Reuse the Monkey Island mailbox pattern:
- **IRAM (2 KB shared):** Command mailbox.
  - S-CPU writes: `PLAYER_X`, `PLAYER_Y`, `PLAYER_STATE`, `SPAWN_ENEMY_CMD`, `SCROLL_X`.
  - SA-1 writes: `CANVAS_READY_FLAG`, `ENEMY_POSITIONS[]` (for collision / priority logic).
- **BW-RAM:** Canvas buffer, entity frame caches, animation state machines.
- **Synchronization:** S-CPU sets `RENDER_START` flag; SA-1 clears it when CC-DMA completes.

---

## 4. Assembly Source Structure (Poppy `.pasm`)

Organize the engine as Poppy modules:

| Module | File | Responsibility |
|---|---|---|
| `main.pasm` | `src/main.pasm` | S-CPU reset vector, NMI/IRQ handlers, game loop, controller polling |
| `sa1_boot.pasm` | `src/sa1/sa1_boot.pasm` | SA-1 initialization, BW-RAM mapping, CC-DMA setup |
| `sa1_blitter.pasm` | `src/sa1/sa1_blitter.pasm` | Pixel-granularity frame blitter into BW-RAM canvas, Y-sort, painters algorithm |
| `sa1_ccdma.pasm` | `src/sa1/sa1_ccdma.pasm` | Character Conversion DMA trigger during VBlank |
| `oam_player.pasm` | `src/ppu/oam_player.pasm` | Player hardware sprite DMA, animation state machine |
| `bg_scroll.pasm` | `src/ppu/bg_scroll.pasm` | BG1 parallax scrolling, BG2 tilemap priority management |
| `hud.pasm` | `src/ppu/hud.pasm` | BG3 HUD rendering, health bars |
| `msu1_stream.pasm` | `src/io/msu1_stream.pasm` | MSU-1 data streaming, track switching, PCM music playback |
| `tad_driver.pasm` | `src/audio/tad_driver.pasm` | Terrific Audio Driver SPC700 interface (reuse from Superman) |
| `entity_ai.pasm` | `src/game/entity_ai.pasm` | Enemy spawn, walk-toward-player, punch-when-close logic |
| `collision.pasm` | `src/game/collision.pasm` | Axis-aligned bounding box checks between player and enemies |

---

## 5. Offline Asset Converter (`tools/bor_converter/`)

Write a Python pipeline that ingests an extracted OpenBOR PAK and emits SNES-native asset blobs. The converter is a **preprocessing tool** that runs on the host PC, not on the SNES.

### 5.1 Step 1: PAK Extraction (`extract_pak.py`)

- Accept a `.pak` file path. Use the `borpak` algorithm (or shell out to the `borpak` binary from the OpenBOR repo) to extract the encrypted archive into a `DATA/` folder tree.
- Expected structure: `BGS/`, `CHARS/`, `LEVELS/`, `MUSIC/`, `SCENES/`, `SOUNDS/`, `SPRITES/`, plus `models.txt`, `levels.txt`, `lifebar.txt`, `video.txt`, `pal.act`.

### 5.2 Step 2: Entity Conversion (`convert_entities.py`)

- Parse each character's `.txt` entity file (e.g., `data/chars/donovan/donovan.txt`).
- Extract animation definitions: `anim idle`, `anim walk`, `anim attack1`, etc.
- For each `frame` command, locate the referenced `.gif` sprite.
- Convert each `.gif` frame to SNES 4bpp indexed format:
  - Quantize to 16 colors per 8×8 tile (15 colors + transparency).
  - Assign an optimal palette index (1–7) per tile to minimize color error.
  - Output linear 4bpp pixel data ready for SA-1 BW-RAM blitting.
- Generate per-frame metadata: width, height, hotspot (offset), attack boxes, body boxes, frame duration.
- Generate animation state tables: frame index sequences, durations, loop flags, next-state transitions.

### 5.3 Step 3: Background Conversion (`convert_backgrounds.py`)

- Parse `levels.txt` and level definitions.
- Convert `BGS/` background images to SNES Mode 1 tilesets + tilemaps.
- For parallax layers, split into independent tilemaps and scrolling metadata.
- Output: `bg_tiles.bin`, `bg_tilemaps.bin`, `bg_palettes.bin`.

### 5.4 Step 4: Audio Conversion (`convert_audio.py`)

- Music: Convert `MUSIC/` tracks to MSU-1 PCM format (44.1kHz stereo, 16-bit, raw PCM in `.pcm` files with MSU-1 header). Fallback: convert to TAD MML if the track must fit in ROM.
- SFX: Convert `SOUNDS/` WAV files to BRR via TAD compiler. Register in TAD project.
- Output: `music_msu1/` directory, `sfx_brr.bin`, `tad_project.xml`.

### 5.5 Step 5: ROM Packing (`rom_pack_bor.py`)

- Inspired by `rom_pack_data.py` from Monkey Island.
- Ingest all converted assets and pack them into the 4MB HiROM image's superfree sections.
- Output: `bor_assets.inc` (Poppy-compatible assembly includes for asset addresses), `bor_assets.bin` (binary blobs linked into ROM).

### 5.6 Step 6: Manifest (`bor_manifest.json`)

- JSON file mapping entity names → ROM bank addresses, animation table offsets, palette indices.
- Used by the engine at runtime to locate assets.

---

## 6. Proof-of-Concept Scope

### 6.1 Scene

Level 1 of Beats of Rage Original — the street stage with the brick wall background.

### 6.2 Actors

- **1 player** (Donovan or Jack, hardware OAM sprite, 32×48, fully controllable).
- **4 enemies** (thugs, software sprites on BG2 canvas, 32×48, BOR original sprites).
- **Simple AI:** Enemies walk toward player. When within 30 pixels, play punch animation. No damage system for PoC.
- **Animation:** Idle, walk, punch1, punch2, hit, fall. 4–6 frames per animation at 8 fps.

### 6.3 Controls

| SNES Button | Action |
|---|---|
| D-pad | Move player |
| B | Punch |
| Y | Jump |
| Select | Spawn additional enemy (up to 4 max) |
| Start | Pause |

### 6.4 Visual Requirements

- All 4 enemies must be visible simultaneously, no flicker.
- Player passes in front of and behind enemies using BG2 priority bits.
- 30 Hz canvas update, 60 Hz game logic, stable frame rate.

---

## 7. Build & Test

### 7.1 Build Commands

```bash
# 1. Extract and convert BOR assets
python3 tools/bor_converter/extract_pak.py "Beats of Rage Original.pak" --output assets/
python3 tools/bor_converter/convert_all.py assets/ --output snes_assets/

# 2. Pack assets into Poppy-compatible includes
python3 tools/bor_converter/gen_poppy_assets.py snes_assets/ --output src/assets/

# 3. Build with Poppy (reuse supermn-snes Makefile pattern)
make clean && make
# Output: build/bor.sfc

# 4. Verify roundtrip
# game-garden verify build/bor.sfc
```

### 7.2 Test Harness

- **Primary:** Nexen MCP server (`mesen_inproc_bridge.py`) for automated screenshot comparison and state inspection.
- **Secondary:** FXPAK Pro hardware via `fxpak_push.py`.

### 7.3 Success Criteria

The proof-of-concept is successful if:
1. The ROM boots on accurate SA-1 emulation (bsnes/higan) and shows 4 animated enemies + 1 player simultaneously.
2. Frame rate is stable at 60 Hz game logic / 30 Hz canvas update without dropped frames.
3. No sprite flicker, no VRAM corruption, and no visible tearing during CC-DMA.
4. Player can walk in front of and behind enemies using the priority system.
5. Enemy count can be toggled (1–4) in real-time to demonstrate scalability.

---

## 8. Deliverables (In Order)

1. **Offline converter** (`tools/bor_converter/`) — Extract, convert, and pack BOR Original assets into SNES-native format.
2. **SA-1 blitter + CC-DMA driver** — BW-RAM canvas composite and VBlank upload. Validate with a single static frame first.
3. **S-CPU game loop + controller input** — Player movement, OAM sprite, BG scrolling.
4. **Enemy AI + animation state machine** — 4 enemies walking, punching, sorting by Y.
5. **Priority system** — Player in front/behind enemy using BG2 tile priority.
6. **Audio integration** — TAD SFX + MSU-1 music for Level 1.
7. **End-to-end integration** — Full Level 1 playable demo.

---

## 9. Why Beats of Rage Original?

This is the canonical reference mod. The asset structure is the most documented in the BOR community, the sprite sizes are known and manageable, and it has exactly the right complexity for proving the engine: 3 playable characters, a tight enemy roster, and 5 distinct levels. If the SA-1 software-sprite canvas can handle four thugs on a brick-wall street, it can handle anything in the collection.

**Crisis Evil I** and **Golden Axe Legend** are the obvious follow-ups once the pipeline is proven.

---

## 10. Reference Documentation

- **SA-1 Register Map:** `0x2200–0x222F` (S-CPU side), `0x2200–0x2225` (SA-1 side). Pay special attention to:
  - `$2225` (BW-RAM address mapping)
  - `$2231` / `$2232` (CC-DMA control / source start address)
  - `$2235–$2238` (CC-DMA destination and size)
- **SNES Mode 1:** BG1 = 8bpp (256 colors), BG2 = 4bpp (16 colors), BG3 = 2bpp (4 colors). This is the recommended mode for this engine.
- **SNES VRAM Layout:** Allocate BG1 tiles at `0x0000`, BG2 tiles at `0x2000`, BG3 tiles at `0x4000`. Tilemaps at `0x5800` (BG1), `0x5C00` (BG2), `0x6000` (BG3).
- **Poppy Compiler:** See `supermn-snes` build system for `.pasm` syntax and Game Garden verification workflow.
- **TAD Integration:** See `supermn-snes` audio pipeline for Poppy-native TAD driver wiring.

---

## 11. Constraints & Non-Goals

- **No Mode 7.** This is a traditional 2D beat-'em-up, not a pseudo-3D experiment.
- **No MSU-1 required for PoC.** All assets fit in ROM. MSU-1 streaming is a future optimization for larger rosters/levels.
- **No sound required for PoC.** SPC700 silence is acceptable. A simple punch SFX can be added as a stretch goal.
- **No scrolling.** Single static screen for PoC. Horizontal scrolling is a Phase 2 problem.
- **Collision detection:** Axis-aligned bounding boxes only. No pixel-perfect collision required.
- **No WLA-DX.** All assembly is Poppy `.pasm`. Do not use ca65, ld65, or WLA-DX.

---

*Begin by scaffolding the SA-1 blitter and CC-DMA driver. The BW-RAM canvas buffer and the CC-DMA transfer are the riskiest, unproven pieces; everything else is standard SNES development. Validate the CC-DMA path with a single static frame before adding animation, AI, or multiple enemies.*
