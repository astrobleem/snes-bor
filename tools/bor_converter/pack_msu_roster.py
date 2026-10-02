#!/usr/bin/env python3
"""Packs up to 15 characters' idle/walk/attack animation data into a single
bor.msu file for runtime selection over MSU-1 (see the plan at
`temporal-swinging-hartmanis.md`), replacing the old flow of baking exactly
one character's data into the ROM at build time via gen_pasm_animset.py +
.incbin.

Reuses (imports, does not duplicate) gen_pasm_animset.py's manifest/palette
loading and bake_vram_frames.py's convert_frame_to_vram -- the same
byte-validated CC-DMA-format converter already shipped and proven correct
against real Mesen2 VRAM output.

File format (see the plan for the authoritative spec):

    0x00-0x07  magic "BORMSU1\0"
    0x08       format_version = 4               [was 2 -- see BG record v3/v4 below]
    0x09       roster_count (1-255, a real u8) -- MAX_CHARACTERS below is a
               soft Python-side sanity cap only (see its own comment for
               why the OLD 15-as-hardware-ceiling story is stale)
    0x0A       bg_count (0-MAX_BGS, a plain runtime byte -- MAX_BGS is this
               module's own soft Python-side sanity cap, bumped as real
               content grows, not a format limit like roster_count's 1-15)   [v2]
    0x0B       playable_count (1-roster_count) -- real prop/pickup slice:
               props (e.g. out/apple, added via convert_prop.py) are real
               roster members for Spawn_DoRosterReassign's purposes but
               MUST NOT be player-selectable at char-select (a 1-frame
               idle/walk/attack prop has no real playable moveset). Slots
               playable_count..roster_count-1 are reachable by index for
               reassignment but char-select's own Left/Right wrap only
               cycles 0..playable_count-1. Defaults to roster_count
               (formerly this byte's whole purpose -- "reserved", always 0
               -- which is why a real bug shipped once: apple became
               index 13 and was silently player-selectable via char-select
               wrap until game_g5_menus.py's full-roster wrap check caught
               it). Requires prefixes[0:playable_count] to be the real
               fighters and prefixes[playable_count:] to be props, in that
               order -- build_rom.py's ROSTER_PREFIXES already lists props
               last for this exact reason.
    0x0C-0x0F  bg_directory_offset (u32 LE, 0 when bg_count == 0)   [v2]

    0x10       directory: roster_count records x RECORD_SIZE (currently 50 bytes)
               (0x10-0x10E) [grew 16->17 in the grab mutual-lock slice, see
               +16 below; grew 8->15 *records* in the roster-growth slice --
               main.pasm's seek math (index*17+0x10) is unaffected, since it
               was already per-record, not directory-length-dependent; only
               this packer's own HEADER_SIZE/blob-start offset moves]
      record N at 0x10 + N*17:
        +0  idle_frame_count   (u8)
        +1  walk_frame_count   (u8)
        +2  attack_frame_count (u8)
        +3  idle_delay         (u8)
        +4  walk_delay         (u8)
        +5  attack_delay       (u8)
        +6  fall_frame_count   (u8)   [plan_game.md G7 knockdown slice --
        +7  fall_delay         (u8)    fits the record's own pre-existing
                                        +6/+7 padding, no data_offset ripple]
        +8-11 data_offset (u32 LE) -- absolute byte offset of this
              character's blob from the start of the file
        +12 attack2_frame_count (u8)  [plan_game.md 7, G7 remaining --
        +13 attack2_delay       (u8)   0 if this character has no real
                                        second attack move (YASHIRO);
                                        fits the record's own last
                                        remaining +12/+13 padding]
        +14 rise_frame_count   (u8)   [plan_game.md G7 knockdown slice --
        +15 rise_delay         (u8)    fits the record's own pre-existing
                                        +12-15 padding]
        +16 attack2_is_grab    (u8)   [grab mutual-lock slice -- 1 if this
                                        character's real attack2 anim is
                                        literally named `grab` (JOE), else
                                        0. First real RECORD_SIZE growth
                                        (16->17); all prior second-move
                                        work fit inside existing padding]
        +17 jump_frame_count       (u8)  [real jump slice -- 0 for every
        +18 jump_delay             (u8)   character without a real `jump`
        +19 jumpattack_frame_count (u8)   anim (12 of 13 roster members
        +20 jumpattack_delay       (u8)   today; only LEO has real jump/
        +21 jumpattack2_frame_count(u8)   jumpattack/jumpattack2 content).
        +22 jumpattack2_delay      (u8)   Second real RECORD_SIZE growth
                                           (17->23) -- forced the engine-side
                                           directory-seek arithmetic to stop
                                           being 8-bit-only, see MAX_CHARACTERS'
                                           own comment above.]
        +23 special_frame_count    (u8)  [G7 special slice -- 0 for every
        +24 special_delay          (u8)   character without a real `special`
                                           anim (only LEO today). Third real
                                           RECORD_SIZE growth (23->25).]
        +25..44 -- 6 generic move slots + atchain + chainlength (see
                   NEW_MOVE_SLOT_NAMES; RECORD_SIZE 25->44)
        +45 freespecial_frame_count/delay (RECORD_SIZE 44->46)
        +46 waiting_frame_count    (u8)  [notjustfreespecial.txt G5 slice --
        +47 waiting_delay          (u8)   real ANI_SELECT/char-select
                                           portrait. 0 for every character
                                           without real `waiting` data (only
                                           LEO today). RECORD_SIZE 46->48.]

    HEADER_SIZE+  character blobs, packed sequentially (HEADER_SIZE = 0x10 +
               MAX_CHARACTERS*23 = 0x159 today; was 0x10F before this slice
               bumped RECORD_SIZE 17->23 -- always computed from
               MAX_CHARACTERS*RECORD_SIZE, never a hardcoded literal):
      +0..31   palette: 16 x BGR555 LE
      +32..    idle_frame_count * 768 bytes
      next     walk_frame_count * 768 bytes
      next     attack_frame_count * 768 bytes
      next     fall_frame_count * 768 bytes    [G7 knockdown slice]
      next     rise_frame_count * 768 bytes    [G7 knockdown slice]
      next     attack2_frame_count * 768 bytes [G7 remaining, "attack2" --
      next     jump_frame_count * 768 bytes         [real jump slice -- 0
      next     jumpattack_frame_count * 768 bytes    bytes for every
      next     jumpattack2_frame_count * 768 bytes   character without the
                                                       real anim, LEO only
                                                       today; appended right
                                                       after attack2, before
                                                       the remap section]
                                                 0 bytes if this character
                                                 has no second move]
      next     0-3 alt palettes, 32 bytes each [plan_game.md 8a row 3, `map`
                                                 -- see pack_character_blob's
                                                 own comment for why this
                                                 exact position is load-
                                                 bearing, not cosmetic]

    then       BG directory (only when bg_count > 0): 4 records x 32 bytes,
               located at bg_directory_offset. Bumped 16->20 in v3 to fit a
               streaming level's real width (up to 688 tiles for warehouse --
               doesn't fit a u8) and tile count (up to 65535, doesn't fit the
               old implicit <=1024 VRAM-fit assumption). Bumped again 20->32
               in v4 to add three precomputed absolute region offsets
               (tilemap_offset/tiles_offset/hud_tiles_offset) -- these are
               `data_offset + 256`, `+ tilemap_bytes`, `+ bg_tile_count*32`
               respectively, and could be derived by the engine at runtime,
               but the streaming loader needs to re-seek to each region
               independently (see StageColumn's header comment for why: its
               per-tile pixel fetches interleave with the tilemap read and
               break MSU-1's auto-increment sequential position, unlike the
               static loader's single unbroken burst). Computing them in
               Python once, here, avoids a 16x16->32-bit multiply-with-carry
               on the 65816 side for values that are already known and fixed
               at pack time -- this project's standing preference (see
               CLAUDE.md) is to keep computed-offset arithmetic off the
               65816 wherever a build-time constant will do.
      record N:
        +0     mode            (u8, BG_MODE_STATIC=0 or BG_MODE_STREAMING=1)
        +1     reserved
        +2-3   width_tiles     (u16 LE)
               STATIC:    32 or 64 (see BG_VALID_WIDTHS_STATIC; 64 means the
                          tilemap blob is two concatenated 32x32 pages)
               STREAMING: the level's real content width in tiles, no cap
                          beyond the u16 field (688 for warehouse) -- this is
                          also the level's real scroll-clamp width; there is
                          no separate padded/unpadded distinction the way
                          Phase 8's whole-level static mode needed, because
                          streaming never pads to a page boundary.
        +4     height_tiles    (u8, 28 -- real visible rows; always 28, even
               when a static width_tiles==64 stores 32 padding rows/page)
        +5     hud_tile_count  (u8)
        +6-7   reserved
        +8-9   bg_tile_count   (u16 LE) -- unique tile count. STATIC: <=1024
               (VRAM-fit budget). STREAMING: <=65535 (no VRAM-fit ceiling;
               see bg_converter/convert_bg.py's MAX_STREAMING_TILES).
        +10-11 reserved
        +12-15 data_offset       (u32 LE) -- absolute byte offset of this
               screen's blob (the CGRAM region's start) from the start of
               the file. Both modes use this for the initial seek.
        +16-19 tilemap_offset    (u32 LE) -- data_offset + 256. STREAMING
               only; the static loader never re-seeks mid-blob.
        +20-23 tiles_offset      (u32 LE) -- tilemap_offset + tilemap_bytes.
               STREAMING only.
        +24-27 hud_tiles_offset  (u32 LE) -- tiles_offset + bg_tile_count*32.
               STREAMING only.
        +28-31 reserved

    then       BG blobs, packed sequentially. One blob is everything the engine
               needs to stand up one screen, in the order it uploads them:
      +0..255       CGRAM image: 8 sub-palettes x 16 BGR555 LE. Sub-palette 0
                    holds the BG3 HUD colors (see bg_converter/convert_bg.py's
                    PALETTE_OFFSET note on why BG1 only uses slots 1-7);
                    slots 1-7 are the backdrop.
      +256..        BG1 tilemap.
               STATIC:    real-SNES tilemap words (2 bytes/tile), row-major.
                          1792 bytes (32x28) if width_tiles==32; 4096 bytes
                          (two concatenated 32x32 pages) if width_tiles==64 --
                          see _expected_tilemap_bytes().
               STREAMING: cache-format entries (3 bytes/tile -- u16 tile_id +
                          u8 attribute, see bg_converter/snes_tiles.
                          encode_tilemap_cache_entry), COLUMN-major (not
                          row-major): column 0 top-to-bottom, then column 1,
                          etc. width_tiles*height_tiles*3 bytes total. The
                          engine's column streamer seeks directly to
                          column_index * height_tiles * 3 within this region,
                          not through a separate index.
      next          BG1 tiles: bg_tile_count * 32 bytes (4bpp planar)
      next          BG3 HUD tiles: hud_tile_count * 16 bytes (2bpp planar)

The BG section is appended AFTER the character blobs so that adding it does not
move any character data_offset -- a v1-era reader that ignores the new header
fields still finds every character exactly where it used to be.

Directory storage contains exactly roster_count records. Runtime admission
checks the header count; unused IDs do not reserve phantom payload bytes.

data_offset is a full 32-bit field even though realistic rosters stay under
16MB, because a real multi-character roster can push it past 65536 well
before all 15 slots are full -- every WRAM quantity derived from it in
Anim_LoadCharacter must be handled as 24-bit (lo16+hi8) with explicit carry
propagation, not a bare 16-bit add. This packer itself has no 16-bit
limitation (Python ints are arbitrary precision), so verify_msu_roster.py's
synthetic oversized-roster test only proves the *file format* round-trips a
>65536 offset correctly -- it cannot exercise, and is not a substitute for,
the real 65816 carry-add logic Phase 2 has to write and test on real
hardware/emulation.

Usage:
    python pack_msu_roster.py <out_msu_path> <prefix1> [<prefix2> ... up to 15]

Each <prefixN> must have a <prefixN>_moveset.json (convert_character.py's
generic per-character manifest -- see _resolve_role_dirs) resolving its
idle/walk/attack/fall/rise roles to real converted animation directories;
the character's real animation names/count no longer need to match any
fixed convention (generalized 2026-08-22, plan_game.md 7). Emits
<out_msu_path>.manifest.json alongside the .msu file: per-slot name, frame
counts, delays, and computed data_offset -- the independent ground truth
verify_msu_roster.py (and any future Mesen2 verification) checks packed
WRAM/file state against.
"""
import json
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from queue_abi import RECORD_SIZE as QUEUE_RECORD_SIZE, packed_count, plan_build
from stage_environment_abi import encode_palettes
from actor_media_abi import check_actor_media_extent

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pasm_animset
import bake_vram_frames

MAGIC = b"BORMSU1\x00"
FORMAT_VERSION = 4

# Optional append-only scene-video extension. Existing BORMSU1 readers stop
# before this section and remain byte-compatible until a later runtime slice
# adds a reader.
SCENE_VIDEO_MAGIC = b"BORVID1\x00"
SCENE_VIDEO_VERSION = 1
SCENE_VIDEO_HEADER_SIZE = 16
SCENE_VIDEO_ENTRY_SIZE = 24
# Bumped 8->15 (roster-growth slice): NOT an arbitrary round number -- 15 is
# Real jump slice (plan_game.md 7): Anim_LoadCharacter's directory-seek
# arithmetic was an 8-bit-only `offset = index*17 + 0x10` with no carry --
# the comment that used to live here documented index=14 (254) as the real
# wall, index=15 wrapping mod 256 to 15 (silently wrong, not a crash). That
# was already dangerously close: this slice grows RECORD_SIZE 17->23 for
# real jump/jumpattack/jumpattack2 fields, which would have dropped the safe
# ceiling to index=10 (11*23+16=269 wraps) -- below the 13 real roster
# members already shipped (indices 0-12, LEO among them). Rather than ship
# a record growth that immediately breaks the just-added LEO slot, the
# engine side's seek got rewritten to a real 16-bit accumulate-by-repeated-
# add loop (see main.pasm's Anim_LoadCharacter_SeekRecord) -- no more 8-bit
# ceiling at all. The compiler now reserves the actual linked directory;
# the only catalog-count ceiling here is the runtime's unsigned byte.
# Actor media offsets/extents retain their separate checked addressing bound.
MAX_CHARACTERS = 255  # Actual unsigned-byte roster-count ABI; not catalog size.
RECORD_SIZE = 50  # claude_close_g7_g8_before_g10.md Part 2: +2 bytes --
                   # get_frame_count/get_delay, the 8th generic move slot
                   # (NEW_MOVE_SLOT_NAMES' own comment), packed generically
                   # right alongside attack3..freespecial (BEFORE atchain/
                   # chainlength, unlike waiting which stays LAST) -- 0/0
                   # for every roster member except LEO. Was 48 (notjustfreespecial.txt G5 slice: +2 bytes -- waiting_
                   # frame_count/waiting_delay appended LAST (+46/+47), 0/0
                   # for every roster member without real `waiting` data
                   # (only LEO today). Was 46 (G7 reopened-again slice: +2 bytes -- `freespecial` added
                   # as a 7th generic move slot (fcount/delay only, no
                   # atchain steps needed) after being wrongly classified
                   # "AI-exclusive" in the prior content-audit slice; see
                   # NEW_MOVE_SLOT_NAMES' own comment for the real sourcing.
                   # Was 25->44 (G7 content-audit slice): +19 bytes -- a generic 6-slot
                   # move-descriptor table (NEW_MOVE_SLOT_NAMES: attack3/
                   # attack4/grab/slide/riseattack/grabattack, 2 bytes each
                   # = 12 bytes) plus a real BOR.C `atchain` array (6 bytes,
                   # max real chain length in this roster -- LEO's own
                   # `atchain 1 2 3 1 2 4`) and chainlength (1 byte). See
                   # build_record's own comment for the exact layout and
                   # why this is a generic, loop-driven table rather than
                   # more one-hardcoded-field-per-move growth: a real
                   # source-content audit (plan_game.md 7, "no reachable
                   # content stays inert" pass) found 6 more real, baked-
                   # but-previously-unwired moves across the roster (LEO
                   # alone: attack3/attack4/grab/slide/grabattack; BEBOP/
                   # ROCK/LEATHER: riseattack) plus a real combo-chain
                   # mechanic (LEO/FOOT01/FOOT02) with no representation at
                   # all in the old fixed-field record scheme. Was 25 (G7
                   # throw+special slice: +2 bytes -- special_frame_count/
                   # delay (+23..+24). 0/0 for every character without real
                   # special content (only LEO has a real `special` anim
                   # today, see convert_character.py's OPTIONAL_ROLE_NAMES).
                   # Was 23 (real jump slice: +6 bytes -- jump_frame_count/
                   # delay, jumpattack_frame_count/delay, jumpattack2_
                   # frame_count/delay, +17..+22). Was 17 before that (grab
                   # mutual-lock slice: +1 byte, +16 attack2_is_grab (u8)).
DIRECTORY_BASE = 0x10
# Directory storage follows the linked roster, not a hand-maintained maximum.
def roster_header_size(count):
    if not isinstance(count, int) or not 1 <= count <= MAX_CHARACTERS:
        raise ValueError(f'roster count must be 1-{MAX_CHARACTERS}, got {count}')
    return DIRECTORY_BASE + count * RECORD_SIZE

PALETTE_BYTES = 32  # 16 BGR555 colors, 2 bytes each
ANIM_FRAME_BYTES = 768

# --- BG section (v2 static, v3 adds streaming) ---
MAX_BGS = 32  # G15-R11: append verifier-only BOR Normal 5A catalog record.
              # bumped 5->9 adding the real 4-level TMNT main campaign
              # (sewer0/streets/streets2/sewer) alongside the 3 standalone
              # TMNT boss stages and the 2 original BOR levels, then 9->10
              # for foot.txt (the last standalone TMNT level) -- directory
              # table grows by more BG_RECORD_SIZE (40B) entries, no format
              # version bump (bg_count is a runtime byte read off the file
              # header, main.pasm has no MAX_BGS-shaped hardcode to update)
BG_RECORD_SIZE = 40         # bumped 16->20 in v3, 20->32 in v4, 32->40 in v6 -- see module docstring

SPAWN_RECORD_SIZE = QUEUE_RECORD_SIZE  # ten-byte queue ABI v1
                             # 9->10 (split object_roster_idx/item_roster_idx)
                             # -- see build_spawn_table.py's module docstring
                             # for the full record layout
                             # (grew from 7 to 8 -- health-override slice added
                             # a spawn_hp byte, follow-up to plan_game.md G8;
                             # 8 to 9 -- roster-growth slice added a dedicated
                             # roster_idx byte)
BG_CGRAM_BYTES = 256        # 8 sub-palettes x 16 colors x 2 bytes
BG_WIDTH_TILES = 32         # historical Phase 6 single-screen width
BG_HEIGHT_TILES = 28
# Phase 8 (plan.md 2.7): a whole-level static BG can also be 64 tiles wide (a
# real BG1SC 64x32 map, two horizontally-adjacent 32x32 pages -- see
# bg_converter/snes_tiles.encode_tilemap_paged and convert_bg.py's
# convert_level()). Only 32 and 64 are valid widths for a single static load.
BG_VALID_WIDTHS_STATIC = (32, 64)

BG_MODE_STATIC = 0
BG_MODE_STREAMING = 1

CACHE_ENTRY_BYTES = 3       # Phase 9: u16 tile_id + u8 attribute (streaming)


def _expected_tilemap_bytes(mode, width_tiles, height_tiles=BG_HEIGHT_TILES):
    """Bytes convert_bg.py emits for a given tilemap mode/width.

    STATIC width=32 is the historical single-page format: only the 28 real
    rows are stored (1792B). width=64 is two FULL 32x32 pages (4096B) --
    page B must start exactly 1024 words after page A regardless of how many
    rows are visible, so rows 28-31 of each page are stored (zero-padded)
    even though they're never displayed.

    STREAMING has no page concept: exactly width_tiles*height_tiles entries,
    column-major, 3 bytes each (see snes_tiles.encode_tilemap_cache_entry).
    """
    if mode == BG_MODE_STREAMING:
        return width_tiles * height_tiles * CACHE_ENTRY_BYTES
    if width_tiles == 32:
        return BG_WIDTH_TILES * height_tiles * 2
    if width_tiles == 64:
        return 64 * 32 * 2
    raise ValueError(f"unsupported static tilemap width_tiles={width_tiles} "
                      f"(expected one of {BG_VALID_WIDTHS_STATIC})")


BG_BYTES_PER_TILE = 32      # 4bpp
HUD_BYTES_PER_TILE = 16     # 2bpp
# BG1 char data must fit VRAM words $0000-$3FFF (1024 tiles); see
# bg_converter/convert_bg.py's docstring -- Phase 8 (plan.md 2.7) removed the
# boot-time BG2 blank-tile write that used to cap this at 512. Streaming
# (Phase 9) is exempt -- its whole point is a distinct-tile count that
# exceeds this, cached into VRAM at runtime rather than loaded whole.
BG_MAX_TILES_STATIC = 1024
BG_MAX_TILES_STREAMING = 65535  # u16 field ceiling, not a VRAM budget


def bake_anim_bytes(anim_dir):
    """Like bake_vram_frames.bake(), but returns bytes in-memory instead of
    writing a separate .bin file -- this packer emits one combined .msu
    blob per character, not per-animation asset files."""
    manifest_path = os.path.join(anim_dir, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    blob = bytearray()
    for frame in manifest["frames"]:
        bin_path = os.path.join(anim_dir, frame["bin"])
        with open(bin_path, "rb") as f:
            pixels = f.read()
        blob += bake_vram_frames.convert_frame_to_vram(pixels)
    return bytes(blob)


ENGINE_ROLES = ("idle", "walk", "attack", "fall", "rise")

# plan_game.md 7 (G7 remaining: a real second attack move). Optional --
# unlike ENGINE_ROLES, a character may legitimately have no second move
# (YASHIRO, real data). Resolved separately so pack_character_blob can
# tolerate its absence instead of raising like a missing required role.
OPTIONAL_ROLE_ATTACK2 = "attack2"

# Real jump slice (plan_game.md 7): jump/jumpattack/jumpattack2 are real
# OpenBOR anim names (exact-match, same convention idle/walk/pain/fall/rise
# already use -- see convert_character.py's ROLE_NAMES), all optional like
# attack2 -- only LEO (TMNT) has real data for any of them today; every
# other roster member packs 0/0 for all three.
OPTIONAL_ROLE_JUMP = "jump"
OPTIONAL_ROLE_JUMPATTACK = "jumpattack"
OPTIONAL_ROLE_JUMPATTACK2 = "jumpattack2"

# G7 throw+special slice: 'special' is a real, unambiguous OpenBOR anim name
# (confirmed in LEO's real .TXT data -- no other roster member declares it),
# same exact-name-match convention as jump/jumpattack/jumpattack2. Sourced
# from DCurrent/openbor engine/openbor.c's check_special(): LEO's own
# `special` anim has no declared `energycost`, so real BOR.C's cost-
# deduction step (self->energy_state.health_current -= ...cost) is a real
# no-op for LEO specifically -- genuinely free, not an invented
# simplification. `freespecial`/`grabattack`/`throw` (LEO also has real data
# for these) are separate real OpenBOR mechanics -- freespecial needs the
# full input-sequence command parser (special_command_parse_sequence, a
# categorically larger subsystem), grabattack is a move performed while
# already grabbing (this project's grab is player-only, so an AI-side
# grabattack has no real caller here), and throw is LEO's own thrower-swing
# ANIMATION (distinct from this project's already-shipped generic thrown-
# victim system, which deliberately reuses no unique swing art) -- none of
# the three are in scope for this slice, only the plain `special` role.
OPTIONAL_ROLE_SPECIAL = "special"

# notjustfreespecial.txt G5 finding: real OpenBOR ANI_SELECT/char-select
# portrait pose. Only LEO ships real data (1 frame, `select.gif`, `loop 1`,
# `delay 130`) -- fcount 0 for the other 12 roster members. Appended LAST
# in the record/blob (after every existing NEW_MOVE_SLOT_NAMES/atchain/
# chainlength field), not woven into the generic move-slot table above,
# because it isn't a combat move (no CHAR_ATTACK_VARIANT dispatch, no
# atchain reachability) -- it needs its own fcount/delay/base chain hop,
# same 2-field shape as OPTIONAL_ROLE_SPECIAL, just positioned at the very
# end so it doesn't perturb any existing offset.
OPTIONAL_ROLE_WAITING = "waiting"

# G7 content-audit slice: a real, source-content-driven audit (every real
# character .TXT in both shipped paks, re-read directly, not assumed from
# the previously-known role set) found 6 more real, buildable, previously-
# unconverted-to-any-role moves: LEO alone has attack3/attack4/grab/slide/
# grabattack (all real, baked frame data, real `attack` hitbox lines where
# applicable), and BEBOP/ROCK/LEATHER each have a real `riseattack`. Packed
# as a generic, loop-driven table (NOT six more hand-named RECORD_SIZE
# fields, one per move, the way attack2/special were each added before --
# see RECORD_SIZE's own comment) since six is enough that the old
# one-field-set-per-move pattern would have meant six more copies of the
# same fcount/delay/append/chain-hop boilerplate for no real benefit; a
# fixed-order array plus a generic engine-side loop (main.pasm's
# Anim_LoadCharacter/Jump_ComputeBases) does the same job in far less code
# either side of the record. Order is fixed and matches
# main.pasm's own CHAR_ATTACK_VARIANT encoding: variant 3=attack3,
# 4=attack4, 5=grab, 6=slide, 7=riseattack, 8=grabattack (variants 0-2 stay
# attack1/attack2/special, unchanged from before this slice).
#
# claude_close_g7_g8_before_g10.md Part 2: 'get' appended LAST (variant
# 10) -- real OpenBOR ANI_GET (DCurrent/openbor engine/openbor.c's
# common_pickupitem/player think ANI_GET block), reached at real pickup
# collision, not a button/atchain input. Reuses this SAME generic move-
# descriptor table/frame-advance machinery (Jump_PlayMoveSlotAdvance) as
# attack3-freespecial since it's the identical one-shot-anim-then-revert-
# to-idle shape, but it is NOT a combat move: Character_HitApply's own
# entry point explicitly skips hit-application for this one variant (see
# GET_MOVE_VARIANT below / main.pasm) so playing it can never accidentally
# deal damage. Only LEO ships real `get` data (DATA\CHARS\LEO\LEO.TXT: 1
# frame, `still01.gif`, `loop 0`, `delay 1`) -- fcount 0 for the other 12
# roster members, same "collapses to zero, content-inapplicable"
# discipline as every other optional/move-slot role.
NEW_MOVE_SLOT_NAMES = ["attack3", "attack4", "grab", "slide", "riseattack", "grabattack", "freespecial", "get"]
NEW_MOVE_SLOT_FIRST_VARIANT = 3  # variant = NEW_MOVE_SLOT_FIRST_VARIANT + index
GET_MOVE_VARIANT = NEW_MOVE_SLOT_FIRST_VARIANT + NEW_MOVE_SLOT_NAMES.index("get")  # 10
# G7 reopened-again slice: `freespecial` was WRONGLY classified as
# "AI-exclusive, content-inapplicable" in the prior content-audit slice --
# that check only scanned player_check_special()/check_special() for a
# direct animspecials[] reference and found none, but real freespecial
# reachability is a SEPARATE mechanism entirely: model_init_defaultreadme()
# (DCurrent/openbor engine/openbor.c, ~line 21039) auto-installs a default
# 3-step command (forward,forward,attack -> ANI_FREESPECIAL) into every
# character's own model->special[] array whenever it declares that anim
# without an explicit `special` command override, and that array IS
# consumed for the real player via player_preinput()->check_combo()
# (called from player_think(), before player_check_special() even runs).
# LEO is the only roster member with real `freespecial` data (5 frames,
# real attack hitbox, PAK-verified) -- everyone else's fcount is 0.

# Real BOR.C `atchain` (engine/openbor.c's perform_atchain()) declares raw
# 1-based ATTACK NUMBERS (1=attack1, 2=attack2, 3=attack3, 4=attack4), not
# CHAR_ATTACK_VARIANT values or move-slot-table indices -- this packer, not
# main.pasm, owns translating each raw value into the ready-to-use variant
# byte the engine actually dispatches on, so the 65816 side never needs to
# know this mapping exists. 'special' (variant 2) is never reachable via a
# real atchain (real BOR.C's perform_atchain() only ever indexes
# animattacks[], the attack1-4 family) so it has no entry here.
ATCHAIN_RAW_TO_VARIANT = {
    1: 0,                                     # attack1
    2: 1,                                     # attack2
    3: NEW_MOVE_SLOT_FIRST_VARIANT + 0,       # attack3 -> variant 3
    4: NEW_MOVE_SLOT_FIRST_VARIANT + 1,       # attack4 -> variant 4
}
ATCHAIN_MAX_STEPS = 6  # LEO's own real `atchain 1 2 3 1 2 4` -- the longest
                        # real chain in either shipped pak, PAK-verified
                        # across all 13 currently-converted roster members.


def _resolve_role_dirs(prefix):
    """Reads <prefix>_moveset.json (convert_character.py's per-character
    manifest -- generic ordinal-indexed animation list + a role table
    resolved by NAME once, in Python, at convert time) and returns a dict
    {role: anim_dir} for the 5 roles this engine's hand-written state
    machine currently has distinct behavior for (idle/walk/attack/fall/
    rise -- see main.pasm's Anim_Play__dispatch/CHAR_SELECTED constants).

    Generalized 2026-08-22 (plan_game.md 7, "generalize the moveset
    pipeline" slice) -- replaces the old fixed `<prefix>_{idle,walk,attack,
    fall,rise}` directory-name assumption. A character's real animation
    names/count/ordering no longer matter here; only which ordinal each
    known role resolved to (by convert_character.py's own name matching)
    does. Animations beyond these 5 roles (a second real attack move, a
    distinct `pain` anim, anything else the raw pak declares) are real,
    converted, and listed in the moveset manifest, but intentionally NOT
    included in the packed blob below -- nothing downstream reads them yet
    (multi-move dispatch is deferred, see plan_game.md 7's role-table
    design note), and shipping their frame bytes would only grow the MSU
    file for data nothing uses. Raises KeyError with the character's real
    name if a required role is genuinely absent (no BOR roster character
    is missing one today, but a future pak's character legitimately might
    be -- e.g. no `pain` anim -- and this must fail loudly, not silently
    substitute a wrong directory, since main.pasm has no per-instance
    "role absent" handling yet)."""
    moveset_path = f"{prefix}_moveset.json"
    with open(moveset_path, "r", encoding="utf-8") as f:
        moveset = json.load(f)
    anims_by_ordinal = {a["ordinal"]: a for a in moveset["animations"]}
    roles = moveset["roles"]
    resolved = {}
    for role in ENGINE_ROLES:
        ordinal = roles.get(role)
        if ordinal is None:
            # Original BOR deliberately permits a player model without
            # ANI_ATTACK1 (Mighty).  The packed record represents that real
            # absence with a zero count and no bytes; do not substitute an
            # unrelated animation or make the character un-packable.
            if role == "attack":
                resolved[role] = None
                continue
            # Some source entities are intentionally sparse.  In particular
            # BOR's biker subtype has only idle/pain; its movement is a
            # subtype state machine, not a request for fabricated walk/fall
            # frames.  A zero role is therefore an honest packed absence.
            resolved[role] = None
            continue
        resolved[role] = anims_by_ordinal[ordinal]["dir"]

    # Optional: a real second attack move (plan_game.md 7, G7 remaining).
    # None (not KeyError) if this character has none -- real data (YASHIRO).
    attack2_ordinal = roles.get(OPTIONAL_ROLE_ATTACK2)
    resolved[OPTIONAL_ROLE_ATTACK2] = (
        anims_by_ordinal[attack2_ordinal]["dir"] if attack2_ordinal is not None else None)
    # plan_game.md 7 (grab mutual-lock slice): real, converter-derived --
    # never hardcoded by character name here either.
    resolved["attack2_is_grab"] = bool(roles.get("attack2_is_grab", False))

    # Real jump slice: same optional-role shape as attack2. None for every
    # character without real jump/jumpattack/jumpattack2 content (12 of 13
    # roster members today).
    for role in (OPTIONAL_ROLE_JUMP, OPTIONAL_ROLE_JUMPATTACK, OPTIONAL_ROLE_JUMPATTACK2,
                 OPTIONAL_ROLE_SPECIAL, OPTIONAL_ROLE_WAITING):
        ordinal = roles.get(role)
        resolved[role] = anims_by_ordinal[ordinal]["dir"] if ordinal is not None else None

    # G7 content-audit slice: the 6 new generic move-descriptor roles --
    # same optional-role shape, None for any roster member without real
    # data for that specific move (most of them, most of the time).
    for role in NEW_MOVE_SLOT_NAMES:
        ordinal = roles.get(role)
        resolved[role] = anims_by_ordinal[ordinal]["dir"] if ordinal is not None else None

    # Real BOR.C `atchain` -- raw 1-4 values straight from convert_character.py's
    # own moveset.json, translated to ready-to-use CHAR_ATTACK_VARIANT bytes
    # here (see ATCHAIN_RAW_TO_VARIANT's own comment for why this is a
    # packing-format detail, not something the converter should know about).
    raw_atchain = moveset.get("atchain") or []
    if len(raw_atchain) > ATCHAIN_MAX_STEPS:
        raise ValueError(
            f"{moveset['entity']!r} ({prefix}): real atchain has "
            f"{len(raw_atchain)} steps, more than this packer's "
            f"ATCHAIN_MAX_STEPS={ATCHAIN_MAX_STEPS} (LEO's own real chain, "
            f"the longest currently known) can hold -- raise it")
    resolved["atchain_variants"] = [ATCHAIN_RAW_TO_VARIANT[v] for v in raw_atchain]
    return resolved


def pack_character_blob(prefix, *, extended_maps=False):
    """Returns (blob_bytes, info_dict) for one character's palette + baked
    idle/walk/attack/fall/rise frames, resolved generically via
    <prefix>_moveset.json's role table (see _resolve_role_dirs) rather than
    a fixed directory-name convention. Blob layout and field order are
    UNCHANGED from before this generalization (idle, walk, attack, fall,
    rise, in that fixed sequence) -- main.pasm's Anim_LoadCharacter chains
    CHAR_WALK_BASE/CHAR_ATTACK_BASE/CHAR_FALL_BASE/CHAR_RISE_BASE off of
    each other in exactly this order, so this packer must keep producing
    that order regardless of a character's real anim declaration order.
    The palette is shared across all of a character's dirs by construction
    (convert_character.py quantizes every real animation together, not
    just the 5 known roles) -- reading idle's copy is correct either way."""
    role_dirs = _resolve_role_dirs(prefix)
    idle_dir = role_dirs["idle"]
    walk_dir = role_dirs["walk"]
    attack_dir = role_dirs["attack"]
    fall_dir = role_dirs["fall"]
    rise_dir = role_dirs["rise"]
    attack2_dir = role_dirs[OPTIONAL_ROLE_ATTACK2]
    attack2_is_grab = role_dirs["attack2_is_grab"]
    jump_dir = role_dirs[OPTIONAL_ROLE_JUMP]
    jumpattack_dir = role_dirs[OPTIONAL_ROLE_JUMPATTACK]
    jumpattack2_dir = role_dirs[OPTIONAL_ROLE_JUMPATTACK2]
    special_dir = role_dirs[OPTIONAL_ROLE_SPECIAL]
    waiting_dir = role_dirs[OPTIONAL_ROLE_WAITING]

    idle_count, idle_delay = gen_pasm_animset.load_manifest(idle_dir)
    def load_optional_anim(anim_dir):
        return gen_pasm_animset.load_manifest(anim_dir) if anim_dir is not None else (0, 0)

    walk_count, walk_delay = load_optional_anim(walk_dir)
    if attack_dir is None:
        attack_count, attack_delay = 0, 0
    else:
        attack_count, attack_delay = gen_pasm_animset.load_manifest(attack_dir)
    fall_count, fall_delay = load_optional_anim(fall_dir)
    rise_count, rise_delay = load_optional_anim(rise_dir)
    if attack2_dir is not None:
        attack2_count, attack2_delay = gen_pasm_animset.load_manifest(attack2_dir)
    else:
        attack2_count, attack2_delay = 0, 0
    if jump_dir is not None:
        jump_count, jump_delay = gen_pasm_animset.load_manifest(jump_dir)
    else:
        jump_count, jump_delay = 0, 0
    if jumpattack_dir is not None:
        jumpattack_count, jumpattack_delay = gen_pasm_animset.load_manifest(jumpattack_dir)
    else:
        jumpattack_count, jumpattack_delay = 0, 0
    if jumpattack2_dir is not None:
        jumpattack2_count, jumpattack2_delay = gen_pasm_animset.load_manifest(jumpattack2_dir)
    else:
        jumpattack2_count, jumpattack2_delay = 0, 0
    if special_dir is not None:
        special_count, special_delay = gen_pasm_animset.load_manifest(special_dir)
    else:
        special_count, special_delay = 0, 0
    if waiting_dir is not None:
        waiting_count, waiting_delay = gen_pasm_animset.load_manifest(waiting_dir)
    else:
        waiting_count, waiting_delay = 0, 0

    # G7 content-audit slice: the 6 new generic move-descriptor slots --
    # loop-driven (see NEW_MOVE_SLOT_NAMES' own comment for why), 0/0 for
    # any slot this character has no real data for.
    new_slot_dirs = [role_dirs[role] for role in NEW_MOVE_SLOT_NAMES]
    new_slot_counts_delays = [
        gen_pasm_animset.load_manifest(d) if d is not None else (0, 0)
        for d in new_slot_dirs
    ]

    palette = gen_pasm_animset.load_palette(idle_dir)

    counts = ([(idle_count, "idle"), (walk_count, "walk"), (attack_count, "attack"),
              (fall_count, "fall"), (rise_count, "rise"), (attack2_count, "attack2"),
              (jump_count, "jump"), (jumpattack_count, "jumpattack"),
              (jumpattack2_count, "jumpattack2"), (special_count, "special"),
              (waiting_count, "waiting")]
              + [(c, role) for role, (c, _) in zip(NEW_MOVE_SLOT_NAMES, new_slot_counts_delays)])
    for count, name in counts:
        if not (0 <= count <= 255):
            raise ValueError(f"{prefix}: {name}_frame_count {count} out of u8 range (0-255)")
    # The established runtime record stores one delay per role as u8.  Some
    # original BOR optional animation manifests use long authoring delays
    # (notably grab/jumpattack); preserve the real frame data and saturate only
    # this pre-existing SNES timing field rather than rejecting an otherwise
    # valid source player.  Absent attack remains the distinct 0/0 case above.
    delays = ([(idle_delay, "idle"), (walk_delay, "walk"), (attack_delay, "attack"),
              (fall_delay, "fall"), (rise_delay, "rise"), (attack2_delay, "attack2"),
              (jump_delay, "jump"), (jumpattack_delay, "jumpattack"),
              (jumpattack2_delay, "jumpattack2"), (special_delay, "special"),
              (waiting_delay, "waiting")]
              + [(d, role) for role, (_, d) in zip(NEW_MOVE_SLOT_NAMES, new_slot_counts_delays)])
    for delay, name in delays:
        if delay < 0:
            raise ValueError(f"{prefix}: {name}_delay {delay} is negative")
    idle_delay = min(idle_delay, 255)
    walk_delay = min(walk_delay, 255)
    attack_delay = min(attack_delay, 255)
    fall_delay = min(fall_delay, 255)
    rise_delay = min(rise_delay, 255)
    attack2_delay = min(attack2_delay, 255)
    jump_delay = min(jump_delay, 255)
    jumpattack_delay = min(jumpattack_delay, 255)
    jumpattack2_delay = min(jumpattack2_delay, 255)
    special_delay = min(special_delay, 255)
    waiting_delay = min(waiting_delay, 255)
    new_slot_counts_delays = [
        (count, min(delay, 255)) for count, delay in new_slot_counts_delays
    ]

    palette_bytes = b"".join(struct.pack("<H", v) for v in palette)
    assert len(palette_bytes) == PALETTE_BYTES

    idle_bytes = bake_anim_bytes(idle_dir)
    walk_bytes = bake_anim_bytes(walk_dir) if walk_dir is not None else b""
    attack_bytes = bake_anim_bytes(attack_dir) if attack_dir is not None else b""
    fall_bytes = bake_anim_bytes(fall_dir) if fall_dir is not None else b""
    rise_bytes = bake_anim_bytes(rise_dir) if rise_dir is not None else b""
    attack2_bytes = bake_anim_bytes(attack2_dir) if attack2_dir is not None else b""
    jump_bytes = bake_anim_bytes(jump_dir) if jump_dir is not None else b""
    jumpattack_bytes = bake_anim_bytes(jumpattack_dir) if jumpattack_dir is not None else b""
    jumpattack2_bytes = bake_anim_bytes(jumpattack2_dir) if jumpattack2_dir is not None else b""
    special_bytes = bake_anim_bytes(special_dir) if special_dir is not None else b""
    waiting_bytes = bake_anim_bytes(waiting_dir) if waiting_dir is not None else b""
    new_slot_bytes = [
        bake_anim_bytes(d) if d is not None else b""
        for d in new_slot_dirs
    ]
    assert len(idle_bytes) == idle_count * ANIM_FRAME_BYTES
    assert len(walk_bytes) == walk_count * ANIM_FRAME_BYTES
    assert len(attack_bytes) == attack_count * ANIM_FRAME_BYTES
    assert len(fall_bytes) == fall_count * ANIM_FRAME_BYTES
    assert len(rise_bytes) == rise_count * ANIM_FRAME_BYTES
    assert len(attack2_bytes) == attack2_count * ANIM_FRAME_BYTES
    assert len(jump_bytes) == jump_count * ANIM_FRAME_BYTES
    assert len(jumpattack_bytes) == jumpattack_count * ANIM_FRAME_BYTES
    assert len(jumpattack2_bytes) == jumpattack2_count * ANIM_FRAME_BYTES
    assert len(special_bytes) == special_count * ANIM_FRAME_BYTES
    assert len(waiting_bytes) == waiting_count * ANIM_FRAME_BYTES
    for role, sbytes, (scount, _) in zip(NEW_MOVE_SLOT_NAMES, new_slot_bytes, new_slot_counts_delays):
        assert len(sbytes) == scount * ANIM_FRAME_BYTES, \
            f"{prefix}: {role} baked {len(sbytes)}B, expected {scount * ANIM_FRAME_BYTES}B"

    # plan_game.md 7 (G7 remaining, "attack2"): 0 or 1 real second attack
    # move, appended right after the rise frames and BEFORE the remap
    # section below -- main.pasm's Anim_LoadCharacter now derives
    # attack2_base the same way map_base always has (rise_base +
    # rise_frame_count*768), and map_base itself becomes one more hop
    # (attack2_base + attack2_frame_count*768). This ordering is what lets
    # attack2 slot in WITHOUT growing RECORD_SIZE or moving any existing
    # absolute offset -- see build_record's own comment.

    # plan_game.md 8a row 3 (`map`): 0-3 extra 32-byte alt palettes, appended
    # right after the rise+attack2 frames -- main.pasm's Anim_LoadCharacter
    # derives this exact same offset (attack2_base + attack2_frame_count*768,
    # collapsing to rise_base + rise_frame_count*768 when attack2_count==0)
    # at load time, so this packer's own ordering is load-bearing, not cosmetic.
    # Real remap counts confirmed across all 4 shipped roster characters
    # (RALF/JOE/YASHIRO=3, JHUN=2), sourced from convert_character.py's
    # <prefix>_moveset.json (its own remap_palettes field, [] if the
    # character has no `remap` lines).
    moveset_path = f"{prefix}_moveset.json"
    with open(moveset_path, "r", encoding="utf-8") as f:
        moveset = json.load(f)
    remap_palettes = moveset.get("remap_palettes", [])
    if len(remap_palettes) > 3 and not extended_maps:
        # Explicit pre-S4 binary-reproduction mode only. The environment-v1
        # production emitter opts into all palettes; do not use this legacy
        # oracle to certify higher authored maps.
        remap_palettes = remap_palettes[:3]
    remap_bytes = encode_palettes(remap_palettes)
    assert len(remap_bytes) == len(remap_palettes) * PALETTE_BYTES

    # Real jump slice: jump/jumpattack/jumpattack2 appended right after
    # attack2, BEFORE remap -- main.pasm's map_base now chains off
    # jumpattack2_base (attack2_base+attack2_count*768, then +jump_count*768,
    # +jumpattack_count*768, +jumpattack2_count*768), collapsing back to the
    # old attack2_base+attack2_count*768 when all three counts are 0 (every
    # roster member except LEO). Same "append before remap" discipline
    # attack2 itself established.
    #
    # G7 special slice: special appended right after jumpattack2, BEFORE
    # remap -- same discipline, one more hop (map_base = jumpattack2_base +
    # jumpattack2_count*768, then + special_count*768), collapsing back to
    # the pre-special value when special_count==0 (every roster member
    # except LEO).
    #
    # G7 content-audit slice: the 6 new generic move slots appended right
    # after special, BEFORE remap, in NEW_MOVE_SLOT_NAMES' own fixed order
    # -- same discipline, 6 more chained hops (map_base keeps chaining, one
    # hop per slot, collapsing back to the pre-this-slice value when every
    # new slot's count is 0, which is every roster member except LEO/
    # BEBOP/ROCK/LEATHER/FOOT01/FOOT02).
    # notjustfreespecial.txt G5 slice: waiting (char-select portrait)
    # appended right after the 6 new generic move slots, BEFORE remap --
    # same discipline as every prior hop (map_base = new-slots' own final
    # base + last slot's frame_count*768, then + waiting_count*768,
    # collapsing back to the pre-this-slice value when waiting_count==0,
    # every roster member except LEO).
    blob = (palette_bytes + idle_bytes + walk_bytes + attack_bytes
            + fall_bytes + rise_bytes + attack2_bytes
            + jump_bytes + jumpattack_bytes + jumpattack2_bytes
            + special_bytes + b"".join(new_slot_bytes) + waiting_bytes + remap_bytes)

    info = {
        "prefix": prefix,
        "idle_frame_count": idle_count,
        "walk_frame_count": walk_count,
        "attack_frame_count": attack_count,
        "fall_frame_count": fall_count,
        "rise_frame_count": rise_count,
        "attack2_frame_count": attack2_count,
        "idle_delay": idle_delay,
        "walk_delay": walk_delay,
        "attack_delay": attack_delay,
        "fall_delay": fall_delay,
        "rise_delay": rise_delay,
        "attack2_delay": attack2_delay,
        "attack2_is_grab": attack2_is_grab,
        "jump_frame_count": jump_count,
        "jump_delay": jump_delay,
        "jumpattack_frame_count": jumpattack_count,
        "jumpattack_delay": jumpattack_delay,
        "jumpattack2_frame_count": jumpattack2_count,
        "jumpattack2_delay": jumpattack2_delay,
        "special_frame_count": special_count,
        "special_delay": special_delay,
        "waiting_frame_count": waiting_count,
        "waiting_delay": waiting_delay,
        "blob_size": len(blob),
    }
    for role, (scount, sdelay) in zip(NEW_MOVE_SLOT_NAMES, new_slot_counts_delays):
        info[f"{role}_frame_count"] = scount
        info[f"{role}_delay"] = sdelay
    raw_atchain = role_dirs["atchain_variants"]
    padded_atchain = (raw_atchain + [0] * ATCHAIN_MAX_STEPS)[:ATCHAIN_MAX_STEPS]
    info["atchain_variants"] = padded_atchain
    info["chainlength"] = len(raw_atchain)
    return blob, info


def build_record(info, data_offset):
    # Real jump slice: RECORD_SIZE grows 17->23, +17..+22 jump_frame_count/
    # jump_delay/jumpattack_frame_count/jumpattack_delay/jumpattack2_
    # frame_count/jumpattack2_delay (all u8, 0/0/0/0/0/0 for every roster
    # member except LEO). This grows HEADER_SIZE (0x10F->0x159); main.pasm
    # reads bg_directory_offset/data_offset from the file's own header
    # fields rather than recomputing them from RECORD_SIZE, so nothing else
    # needs manual resync there EXCEPT Anim_LoadCharacter's own directory-
    # seek arithmetic -- which, unlike the two prior RECORD_SIZE growths
    # (16->17, this one 17->23), is no longer a hand-adjusted `index*N+0x10`
    # immediate-multiply at all: it's a real 16-bit accumulate-by-repeated-
    # add loop now (Anim_LoadCharacter_SeekRecord), so it needs no resync
    # for this or any future RECORD_SIZE change.
    # G7 content-audit slice: RECORD_SIZE grows 25->44, +25..+43: 12 bytes of
    # fcount/delay pairs for the 6 new generic move slots (attack3/attack4/
    # grab/slide/riseattack/grabattack, NEW_MOVE_SLOT_NAMES' own order), then
    # 6 bytes of atchain_variants (padded to ATCHAIN_MAX_STEPS with 0), then
    # 1 byte chainlength. All 0 for every roster member without the real
    # source content (everyone except LEO/BEBOP/ROCK/LEATHER/FOOT01/FOOT02).
    new_slot_fields = []
    for role in NEW_MOVE_SLOT_NAMES:
        new_slot_fields.append(info[f"{role}_frame_count"])
        new_slot_fields.append(info[f"{role}_delay"])
    record = struct.pack(
        "<BBBBBBBBIBBBBBBBBBBBBB" + "B" * len(new_slot_fields) + "B" * ATCHAIN_MAX_STEPS + "B" + "BB",
        info["idle_frame_count"],
        info["walk_frame_count"],
        info["attack_frame_count"],
        info["idle_delay"],
        info["walk_delay"],
        info["attack_delay"],
        info["fall_frame_count"],
        info["fall_delay"],
        data_offset,
        info["attack2_frame_count"],
        info["attack2_delay"],
        info["rise_frame_count"],
        info["rise_delay"],
        1 if info["attack2_is_grab"] else 0,
        info["jump_frame_count"],
        info["jump_delay"],
        info["jumpattack_frame_count"],
        info["jumpattack_delay"],
        info["jumpattack2_frame_count"],
        info["jumpattack2_delay"],
        info["special_frame_count"],
        info["special_delay"],
        *new_slot_fields,
        *info["atchain_variants"],
        info["chainlength"],
        info["waiting_frame_count"],
        info["waiting_delay"],
    )
    assert len(record) == RECORD_SIZE
    return record


def pack_bg_blob(bg_dir, hud_dir):
    """Returns (blob_bytes, info_dict) for one screen: CGRAM image + BG1
    tilemap + BG1 tiles + BG3 HUD tiles.

    `bg_dir` is a tools/bg_converter/convert_bg.py output directory (static
    convert()/convert_level(), or Phase 9 convert_streaming() -- selected by
    the presence of manifest.json's "streaming" key), `hud_dir` a
    make_hud_tiles.py output directory. The HUD's 16-color sub-palette is
    merged over CGRAM slot 0, which convert_bg.py deliberately leaves zeroed
    for exactly this purpose -- so the engine can upload one contiguous
    256-byte CGRAM image rather than two separate transfers.
    """
    with open(os.path.join(bg_dir, "manifest.json"), "r", encoding="utf-8") as f:
        bg_manifest = json.load(f)
    with open(os.path.join(hud_dir, "manifest.json"), "r", encoding="utf-8") as f:
        hud_manifest = json.load(f)

    def _read(d, name):
        with open(os.path.join(d, name), "rb") as f:
            return f.read()

    palette = bytearray(_read(bg_dir, "palette.bin"))
    tilemap = _read(bg_dir, "tilemap.bin")
    tiles = _read(bg_dir, "tiles.bin")
    hud_palette = _read(hud_dir, "hud_palette.bin")
    hud_tiles = _read(hud_dir, "hud_tiles.bin")

    mode = BG_MODE_STREAMING if bg_manifest.get("streaming") else BG_MODE_STATIC
    width_tiles = bg_manifest["width_tiles"]
    height_tiles = bg_manifest["height_tiles"]
    if mode == BG_MODE_STREAMING and height_tiles != BG_HEIGHT_TILES:
        raise ValueError(f"{bg_dir}: streaming height_tiles={height_tiles}, expected {BG_HEIGHT_TILES}")
    if mode == BG_MODE_STATIC and height_tiles not in (BG_HEIGHT_TILES, 32):
        raise ValueError(f"{bg_dir}: static height_tiles={height_tiles}, expected 28 or 32")

    tile_count = bg_manifest["unique_tiles"]
    max_tiles = BG_MAX_TILES_STREAMING if mode == BG_MODE_STREAMING else BG_MAX_TILES_STATIC

    if mode == BG_MODE_STATIC and width_tiles not in BG_VALID_WIDTHS_STATIC:
        raise ValueError(f"{bg_dir}: width_tiles={width_tiles}, expected one of "
                         f"{BG_VALID_WIDTHS_STATIC}")
    if not (0 <= width_tiles <= 0xFFFF):
        raise ValueError(f"{bg_dir}: width_tiles={width_tiles} out of u16 range")

    expected_tilemap_bytes = _expected_tilemap_bytes(mode, width_tiles, height_tiles)
    if len(palette) != BG_CGRAM_BYTES:
        raise ValueError(f"{bg_dir}: palette.bin is {len(palette)}B, expected {BG_CGRAM_BYTES}")
    if len(tilemap) != expected_tilemap_bytes:
        raise ValueError(f"{bg_dir}: tilemap.bin is {len(tilemap)}B, expected "
                         f"{expected_tilemap_bytes} for mode={mode} width_tiles={width_tiles}")
    if len(hud_palette) != PALETTE_BYTES:
        raise ValueError(f"{hud_dir}: hud_palette.bin is {len(hud_palette)}B, "
                         f"expected {PALETTE_BYTES}")

    if len(tiles) != tile_count * BG_BYTES_PER_TILE:
        raise ValueError(f"{bg_dir}: tiles.bin is {len(tiles)}B, expected "
                         f"{tile_count * BG_BYTES_PER_TILE}")
    if tile_count > max_tiles:
        raise ValueError(f"{bg_dir}: {tile_count} tiles exceeds the {max_tiles}-tile "
                         f"budget for mode={mode}")

    hud_tile_count = hud_manifest["tile_count"]
    if len(hud_tiles) != hud_tile_count * HUD_BYTES_PER_TILE:
        raise ValueError(f"{hud_dir}: hud_tiles.bin is {len(hud_tiles)}B, expected "
                         f"{hud_tile_count * HUD_BYTES_PER_TILE}")
    if not (0 <= hud_tile_count <= 255):
        raise ValueError(f"{hud_dir}: hud_tile_count {hud_tile_count} out of u8 range")

    # Merge the HUD's sub-palette over CGRAM slot 0.
    if any(palette[:PALETTE_BYTES]):
        raise ValueError(f"{bg_dir}: CGRAM sub-palette 0 is not zeroed; it is "
                         f"reserved for the BG3 HUD (see convert_bg.py PALETTE_OFFSET)")
    palette[:PALETTE_BYTES] = hud_palette

    blob = bytes(palette) + tilemap + tiles + hud_tiles
    info = {
        "bg_dir": bg_dir,
        "hud_dir": hud_dir,
        "level_entry": bg_manifest.get("level_entry"),
        "mode": mode,
        "bg_tile_count": tile_count,
        "width_tiles": width_tiles,
        "height_tiles": height_tiles,
        "hud_tile_count": hud_tile_count,
        "tilemap_bytes": len(tilemap),
        "blob_size": len(blob),
    }
    return blob, info


def build_bg_record(info, data_offset, fp_offset=0, spawn_offset=0, spawn_count=0):
    tilemap_offset = data_offset + BG_CGRAM_BYTES
    tiles_offset = tilemap_offset + info["tilemap_bytes"]
    hud_tiles_offset = tiles_offset + info["bg_tile_count"] * BG_BYTES_PER_TILE
    # Last 4 bytes were reserved padding through v4; v5 (Phase 10, plan.md
    # 2.10) repurposes them for fp_offset -- the absolute byte offset of this
    # BG's optional frontpanel blob (see pack_fp_blob/FP_RECORD_SIZE below),
    # or 0 if this BG has none. Deliberately NOT a new top-level directory
    # (the primary 16-byte header has no spare bytes to grow into without
    # shifting every existing absolute offset in the file) -- a frontpanel
    # is level-specific 1:1 with the BG it overlays, so hanging it off the
    # BG record it belongs to is the honest structure, not a workaround.
    #
    # v6 (Phase G4, plan_game.md 4): appends spawn_offset (u32, absolute file
    # offset of this stage's own spawn-table blob) + spawn_count (u16, record
    # count) + 2 reserved bytes. Same reasoning as fp_offset above: a stage's
    # spawn queue is 1:1 with the BG it belongs to, so hanging it off this
    # record (rather than a hand-synced SPAWN_MSU_OFFSET/SPAWN_COUNT constant
    # in src/core/spawn.pasm, which cannot scale past one level -- see
    # CLAUDE.md's roadmap note and plan_game.md 4's own "watch out") is the
    # generalization this phase requires. spawn_count is 0 when this stage
    # packs no spawn table at all (an empty/no-enemy stage).
    record = struct.pack(
        "<BxHBB2xH2xIIIIIIH2x",
        info["mode"],
        info["width_tiles"],
        info["height_tiles"],
        info["hud_tile_count"],
        info["bg_tile_count"],
        data_offset,
        tilemap_offset,
        tiles_offset,
        hud_tiles_offset,
        fp_offset,
        spawn_offset,
        spawn_count,
    )
    assert len(record) == BG_RECORD_SIZE
    return record


# --- Frontpanel (FP) section (v5, Phase 10, plan.md 2.10): a second,
# independent streaming tile source for BG3, hung off a BG record via its
# now-repurposed reserved bytes (see build_bg_record above). Always
# streaming-mode (no static frontpanel path exists) and always 2bpp (BG3 in
# Mode 1) -- unlike the BG section, there is no mode/bpp field, because
# there is only one shape this data can take.
#
# Blob layout, self-describing (an inline 16-byte record prefix, not a
# separate directory -- see build_bg_record's comment for why):
#   +0-1   width_tiles   (u16 LE) -- MUST equal the owning BG's width_tiles;
#          both layers share one camera-column index, see
#          convert_frontpanel.py's own docstring on this constraint.
#   +2     height_tiles  (u8, always 28)
#   +3     reserved
#   +4-5   tile_count    (u16 LE)
#   +6-7   reserved
#   +8-11  tilemap_offset (u32 LE, absolute) -- precomputed here (Python),
#          not derived from a multiply on the 65816, matching BG record v4's
#          own precedent.
#   +12-15 tiles_offset   (u32 LE, absolute)
#   +16..  palette: 4 sub-palettes x 4 colors x 2 bytes = 32 bytes (BG3's
#          real usable ID range in this engine -- see
#          convert_frontpanel.py's CGRAM budget note. Sub-palette 0 stays
#          zeroed, same HUD-reservation convention as the BG section.)
#   next   tilemap: width_tiles*height_tiles*CACHE_ENTRY_BYTES(3) bytes,
#          column-major (identical format to the BG streaming tilemap).
#   next   tiles: tile_count * FP_BYTES_PER_TILE(16) bytes, 2bpp planar.
FP_RECORD_SIZE = 16
FP_PALETTE_BYTES = 32       # 4 sub-palettes x 4 colors x 2 bytes
FP_BYTES_PER_TILE = 16      # 2bpp
FP_MAX_TILES = 65535        # u16 field ceiling, not a real expected limit


def build_fp_blob(fp_dir, expected_width_tiles, data_offset):
    """Returns (blob_bytes, info_dict) for one frontpanel layer, with its
    self-describing 16-byte header already correctly filled in. Needs
    `data_offset` (where this blob will land in the final file) up front,
    unlike pack_bg_blob/build_bg_record's split -- this blob's own bytes
    (the header) depend on that offset, since there's no external directory
    record for it (see build_bg_record's comment for why)."""
    with open(os.path.join(fp_dir, "manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)

    def _read(name):
        with open(os.path.join(fp_dir, name), "rb") as f:
            return f.read()

    palette = _read("palette.bin")
    tilemap = _read("tilemap.bin")
    tiles = _read("tiles.bin")

    if not manifest.get("streaming"):
        raise ValueError(f"{fp_dir}: not a streaming conversion (frontpanel "
                         f"has no static path)")
    width_tiles = manifest["width_tiles"]
    height_tiles = manifest["height_tiles"]
    tile_count = manifest["unique_tiles"]

    if width_tiles != expected_width_tiles:
        raise ValueError(f"{fp_dir}: width_tiles={width_tiles} does not match "
                         f"the owning BG's width_tiles={expected_width_tiles} "
                         f"-- both layers must share one camera-column index")
    if len(palette) != FP_PALETTE_BYTES:
        raise ValueError(f"{fp_dir}: palette.bin is {len(palette)}B, expected "
                         f"{FP_PALETTE_BYTES}")
    expected_tilemap_bytes = width_tiles * height_tiles * CACHE_ENTRY_BYTES
    if len(tilemap) != expected_tilemap_bytes:
        raise ValueError(f"{fp_dir}: tilemap.bin is {len(tilemap)}B, expected "
                         f"{expected_tilemap_bytes}")
    if len(tiles) != tile_count * FP_BYTES_PER_TILE:
        raise ValueError(f"{fp_dir}: tiles.bin is {len(tiles)}B, expected "
                         f"{tile_count * FP_BYTES_PER_TILE}")
    if tile_count > FP_MAX_TILES:
        raise ValueError(f"{fp_dir}: {tile_count} tiles exceeds the "
                         f"{FP_MAX_TILES}-tile field ceiling")

    tilemap_offset = data_offset + FP_RECORD_SIZE + FP_PALETTE_BYTES
    tiles_offset = tilemap_offset + len(tilemap)
    header = struct.pack(
        "<HBxH2xII",
        width_tiles, height_tiles, tile_count,
        tilemap_offset, tiles_offset,
    )
    assert len(header) == FP_RECORD_SIZE
    blob = header + palette + tilemap + tiles

    info = {
        "fp_dir": fp_dir,
        "width_tiles": width_tiles,
        "height_tiles": height_tiles,
        "tile_count": tile_count,
        "tilemap_offset": tilemap_offset,
        "tiles_offset": tiles_offset,
        "blob_size": len(blob),
    }
    return blob, info


def append_scene_video_section(msu_bytes, entries):
    """Append a fixed-format BORVID1 section to a finished BORMSU1 image."""
    if not entries:
        return msu_bytes, []
    if len(entries) > 0xFFFF:
        raise ValueError("too many BORVID1 scene entries")

    directory_size = SCENE_VIDEO_ENTRY_SIZE * len(entries)
    section_start = len(msu_bytes)
    next_payload = section_start + SCENE_VIDEO_HEADER_SIZE + directory_size
    directory = bytearray()
    payloads = []
    metadata = []
    for entry in entries:
        payload = bytes(entry["payload"])
        values = (
            int(entry["scene_id"]), int(entry.get("flags", 0)),
            int(entry["width"]), int(entry["height"]),
            int(entry["fps_num"]), int(entry["fps_den"]),
            int(entry["frame_count"]), next_payload, len(payload),
        )
        if not 0 <= values[0] <= 0xFFFF or not 0 <= values[1] <= 0xFFFF:
            raise ValueError("BORVID1 scene id/flags do not fit u16")
        if not 0 < values[2] <= 0xFFFF or not 0 < values[3] <= 0xFFFF:
            raise ValueError("BORVID1 dimensions must be positive u16 values")
        if not 0 < values[4] <= 0xFFFF or not 0 < values[5] <= 0xFFFF:
            raise ValueError("BORVID1 timing must be positive u16 values")
        if not 0 <= values[6] <= 0xFFFFFFFF:
            raise ValueError("BORVID1 frame count does not fit u32")
        if not 0 <= values[7] <= 0xFFFFFFFF or not 0 <= values[8] <= 0xFFFFFFFF:
            raise ValueError("BORVID1 payload range does not fit u32")
        directory += struct.pack("<HHHHHHIII", *values)
        payloads.append(payload)
        metadata.append({
            "scene_id": values[0], "flags": values[1],
            "width": values[2], "height": values[3],
            "fps_num": values[4], "fps_den": values[5],
            "frame_count": values[6], "payload_offset": values[7],
            "payload_size": values[8],
        })
        next_payload += len(payload)

    section = (struct.pack("<8sHHI", SCENE_VIDEO_MAGIC,
                           SCENE_VIDEO_VERSION, len(entries), directory_size)
               + bytes(directory) + b"".join(payloads))
    return msu_bytes + section, metadata


def scene_video_metadata_pasm(entries):
    """Render generated 65816 metadata from finalized BORVID1 records."""
    lines = [
        "; GENERATED by pack_msu_roster.py; do not edit.",
        "; Scene records are the finalized BORVID1 directory records.",
        "",
        f"SceneVideo_Count = {len(entries)}",
        f"SceneVideo_EntrySize = {SCENE_VIDEO_ENTRY_SIZE}",
    ]
    for index, entry in enumerate(entries):
        prefix = f"SceneVideo_Record{index}_"
        lines.extend([
            f"{prefix}SceneId = {entry['scene_id']}",
            f"{prefix}Flags = {entry['flags']}",
            f"{prefix}Width = {entry['width']}",
            f"{prefix}Height = {entry['height']}",
            f"{prefix}FpsNum = {entry['fps_num']}",
            f"{prefix}FpsDen = {entry['fps_den']}",
            f"{prefix}FrameCount = {entry['frame_count']}",
            f"{prefix}PayloadOffset = {entry['payload_offset']}",
            f"{prefix}PayloadSize = {entry['payload_size']}",
        ])
    lines.extend([
        "",
        "; Indexed tables generated from the finalized BORVID records.",
        "SceneVideo_RecordIds:",
        "    .db " + ", ".join(str(entry['scene_id']) for entry in entries),
        "SceneVideo_RecordWidths:",
        "    .dw " + ", ".join(str(entry['width']) for entry in entries),
        "SceneVideo_RecordHeights:",
        "    .dw " + ", ".join(str(entry['height']) for entry in entries),
        "SceneVideo_RecordFpsNums:",
        "    .dw " + ", ".join(str(entry['fps_num']) for entry in entries),
        "SceneVideo_RecordFpsDens:",
        "    .dw " + ", ".join(str(entry['fps_den']) for entry in entries),
        "SceneVideo_RecordFrameDurationMs:",
        "    .dw " + ", ".join(str((1000 * entry['fps_den']) // entry['fps_num']) for entry in entries),
        "SceneVideo_RecordFrameCountsLo:",
        "    .dw " + ", ".join(str(entry['frame_count'] & 0xffff) for entry in entries),
        "SceneVideo_RecordFrameCountsHi:",
        "    .dw " + ", ".join(str((entry['frame_count'] >> 16) & 0xffff) for entry in entries),
        "SceneVideo_RecordPayloadOffsetsLo:",
        "    .dw " + ", ".join(str(entry['payload_offset'] & 0xffff) for entry in entries),
        "SceneVideo_RecordPayloadOffsetsHi:",
        "    .dw " + ", ".join(str((entry['payload_offset'] >> 16) & 0xffff) for entry in entries),
        "SceneVideo_RecordPayloadSizesLo:",
        "    .dw " + ", ".join(str(entry['payload_size'] & 0xffff) for entry in entries),
        "SceneVideo_RecordPayloadSizesHi:",
        "    .dw " + ", ".join(str((entry['payload_size'] >> 16) & 0xffff) for entry in entries),
        "SceneVideo_RecordFlags:",
        "    .dw " + ", ".join(str(entry['flags']) for entry in entries),
        "SceneVideo_RecordPayloadOffsetBytes:",
        "    .db " + ", ".join(str(byte) for entry in entries for byte in int(entry['payload_offset']).to_bytes(4, 'little')),
        "SceneVideo_RecordPayloadSizeBytes:",
        "    .db " + ", ".join(str(byte) for entry in entries for byte in int(entry['payload_size']).to_bytes(4, 'little')),
    ])
    for index, entry in enumerate(entries):
        if entry['scene_id'] == 1:
            lines.append("SceneVideo_Rugal = SceneVideo_Record%d_SceneId" % index)
            break
    return "\n".join(lines) + "\n"


def write_scene_video_metadata(path, entries):
    """Write generated ROM-side metadata for finalized scene records."""
    with open(path, "w", encoding="ascii", newline="\n") as output:
        output.write(scene_video_metadata_pasm(entries))
    # Poppy's ROM data path is authoritative for executable consumption.  Keep
    # the human-readable include as the generated contract, while supplying
    # the exact bytes through incbin so numeric directive parsing cannot turn
    # the table into zero-filled reservation space.
    raw_path = os.path.splitext(path)[0] + ".bin"
    with open(raw_path, "wb") as output:
        for entry in entries:
            output.write(struct.pack(
                "<HHHHHHIII", entry["scene_id"], entry["flags"],
                entry["width"], entry["height"], entry["fps_num"],
                entry["fps_den"], entry["frame_count"],
                entry["payload_offset"], entry["payload_size"]))


def pack_roster(prefixes, bgs=None, fps=None, spawns=None, vm_blob=None,
                playable_count=None, scene_video_entries=None, extended_maps=False):
    """Returns (msu_bytes, manifest_sidecar_dict).

    `prefixes` is a list of 1-15 out/<name> character prefixes; unused
    directory slots stay zeroed. `bgs` is an optional list of
    (bg_dir, hud_dir) pairs, appended as the v2 BG section after the
    character blobs so no character data_offset moves. `fps` (v5, Phase 10,
    plan.md 2.10) is an optional list the SAME LENGTH as `bgs` -- fps[i] is
    either an out/<name> convert_frontpanel.py output dir for bgs[i], or
    None if that BG has no frontpanel layer. Each present frontpanel is
    packed immediately after its owning BG's own blob (see build_fp_blob),
    with its offset threaded into that BG's record (build_bg_record).

    `spawns` (Phase G4, plan_game.md 4 -- was `spawn_blob`, one hand-synced
    global blob, through Phase 14) is an optional list the SAME LENGTH as
    `bgs` -- spawns[i] is stage i's own raw spawn_table.bin bytes (or b""/
    None for a stage with no spawn queue). Generalizing this from a single
    blob to one per stage is what lets a real multi-stage `bor.msu` exist at
    all: CLAUDE.md's roadmap note and plan_game.md 4's own "watch out" both
    call for killing the hand-synced SPAWN_MSU_OFFSET/SPAWN_COUNT constants
    in src/core/spawn.pasm before anything else, since the moment a second
    stage's spawn blob is packed, both would shift AND become stage-
    dependent -- two things a single build-time constant can't express.
    Each stage's spawn blob is appended after ALL bg (+fp) blobs, in stage
    order, and its absolute file offset + record count (spawn_table.bin is a
    flat array of 8-byte records) are threaded into THAT STAGE's OWN bg
    record (build_bg_record's v6 spawn_offset/spawn_count fields) -- same
    "hang it off the record it belongs to" pattern v5 already used for
    fp_offset, and it means the engine discovers a stage's spawn data the
    exact same way it already discovers bg_count/bg_directory_offset: by
    reading the file at runtime, never by trusting a compile-time constant.

    `vm_blob` (Gate 0a, plan_vm.md 1) is the script VM's bytecode module,
    appended after every stage's spawn blob and therefore at the very end of
    the file -- nothing that already has a hardcoded offset can move. Its
    absolute file offset and byte length are returned in the sidecar so
    build_rom.py's check_vm_constants() can cross-check them against
    vm_load.pasm's hand-synced VM_MSU_OFFSET/VM_MODULE_SIZE -- the VM module
    is not (yet) per-stage, so this one hand-synced pair is deliberately
    still in place; see plan_game.md 4's scope note.
    """
    if not (1 <= len(prefixes) <= MAX_CHARACTERS):
        raise ValueError(f"roster must have 1-{MAX_CHARACTERS} characters, got {len(prefixes)}")
    if playable_count is None:
        playable_count = len(prefixes)
    if not (1 <= playable_count <= len(prefixes)):
        raise ValueError(f"playable_count must be 1-{len(prefixes)}, got {playable_count}")
    bgs = bgs or []
    if len(bgs) > MAX_BGS:
        raise ValueError(f"at most {MAX_BGS} BG screens, got {len(bgs)}")
    fps = fps or ([None] * len(bgs))
    if len(fps) != len(bgs):
        raise ValueError(f"fps must be the same length as bgs ({len(bgs)}), got {len(fps)}")
    spawns = spawns or ([b""] * len(bgs))
    if len(spawns) != len(bgs):
        raise ValueError(f"spawns must be the same length as bgs ({len(bgs)}), got {len(spawns)}")

    header_size = roster_header_size(len(prefixes))
    directory = bytearray(RECORD_SIZE * len(prefixes))
    blobs = []
    sidecar_characters = []

    data_offset = header_size
    for slot, prefix in enumerate(prefixes):
        blob, info = pack_character_blob(prefix, extended_maps=extended_maps)
        check_actor_media_extent(data_offset,len(blob),model=str(prefix))
        record = build_record(info, data_offset)
        directory[slot * RECORD_SIZE:(slot + 1) * RECORD_SIZE] = record

        sidecar_characters.append({"slot": slot, "data_offset": data_offset, **info})

        blobs.append(blob)
        data_offset += len(blob)

    # --- v2 BG section, appended after every character blob ---
    bg_directory = b""
    bg_blobs = []
    sidecar_bgs = []
    bg_directory_offset = 0

    spawn_blobs = []

    if bgs:
        # data_offset currently points just past the last character blob.
        bg_directory_offset = data_offset
        bg_dir_bytes = bytearray(BG_RECORD_SIZE * MAX_BGS)
        bg_data_offset = bg_directory_offset + BG_RECORD_SIZE * MAX_BGS

        per_stage = []
        for slot, (bg_dir, hud_dir) in enumerate(bgs):
            blob, info = pack_bg_blob(bg_dir, hud_dir)
            this_bg_data_offset = bg_data_offset
            bg_blobs.append(blob)
            bg_data_offset += len(blob)

            fp_offset = 0
            fp_info = None
            fp_dir = fps[slot]
            if fp_dir is not None:
                fp_offset = bg_data_offset
                fp_blob, fp_info = build_fp_blob(fp_dir, info["width_tiles"], fp_offset)
                bg_blobs.append(fp_blob)
                bg_data_offset += len(fp_blob)

            per_stage.append({
                "info": info, "data_offset": this_bg_data_offset,
                "fp_offset": fp_offset, "fp_info": fp_info,
            })

        # --- spawn blobs: appended after ALL bg(+fp) blobs, in stage order,
        # so no stage's own bg_data_offset above had to account for them.
        # Each stage's own bg record (built below) gets THIS section's
        # per-stage offset/count threaded in -- see pack_roster's own
        # docstring on why this replaced the single hand-synced spawn_blob. ---
        running_offset = bg_data_offset
        spawn_info = []
        for slot in range(len(bgs)):
            sblob = spawns[slot] or b""
            if sblob:
                assert len(sblob) % SPAWN_RECORD_SIZE == 0, \
                    f"stage {slot} spawn blob is {len(sblob)}B, not a multiple of {SPAWN_RECORD_SIZE}"
                count=packed_count(sblob,project='linked-build',set_name='selected catalog',
                                   stage=slot,source_path=str(bgs[slot][0]))
                spawn_info.append((running_offset, count))
                spawn_blobs.append(sblob)
                running_offset += len(sblob)
            else:
                spawn_info.append((0, 0))

        for slot, ps in enumerate(per_stage):
            spawn_offset, spawn_count = spawn_info[slot]
            bg_dir_bytes[slot * BG_RECORD_SIZE:(slot + 1) * BG_RECORD_SIZE] = \
                build_bg_record(ps["info"], ps["data_offset"], ps["fp_offset"],
                                 spawn_offset, spawn_count)
            sidecar_bg = {"slot": slot, "data_offset": ps["data_offset"], **ps["info"],
                          "spawn_offset": spawn_offset, "spawn_count": spawn_count}
            if ps["fp_info"] is not None:
                sidecar_bg["fp"] = {"data_offset": ps["fp_offset"], **ps["fp_info"]}
            sidecar_bgs.append(sidecar_bg)

        bg_directory = bytes(bg_dir_bytes)

    header = struct.pack("<8sBBBBI", MAGIC, FORMAT_VERSION, len(prefixes),
                         len(bgs), playable_count, bg_directory_offset)
    assert len(header) == DIRECTORY_BASE

    msu_bytes = (header + bytes(directory) + b"".join(blobs)
                 + bg_directory + b"".join(bg_blobs) + b"".join(spawn_blobs))

    vm_offset = 0
    vm_size = 0
    if vm_blob:
        vm_offset = len(msu_bytes)
        vm_size = len(vm_blob)
        msu_bytes = msu_bytes + vm_blob

    msu_bytes, scene_video = append_scene_video_section(
        msu_bytes, scene_video_entries or [])

    sidecar = {
        "queue_abi": plan_build([dict(project='linked-build',set='selected catalog',stage=i,
            source_path=str(bgs[i][0]),packed_records=packed_count(blob or b'',project='linked-build',
            set_name='selected catalog',stage=i,source_path=str(bgs[i][0]))) for i,blob in enumerate(spawns)]),
        "format_version": FORMAT_VERSION,
        "roster_count": len(prefixes),
        "playable_count": playable_count,
        "header_size": header_size,
        "total_size": len(msu_bytes),
        "characters": sidecar_characters,
        "bg_count": len(bgs),
        "bg_directory_offset": bg_directory_offset,
        "bgs": sidecar_bgs,
        "vm_offset": vm_offset,
        "vm_size": vm_size,
        "scene_video": scene_video,
    }
    return msu_bytes, sidecar


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    out_msu_path = sys.argv[1]
    prefixes = sys.argv[2:]

    msu_bytes, sidecar = pack_roster(prefixes)

    os.makedirs(os.path.dirname(out_msu_path) or ".", exist_ok=True)
    with open(out_msu_path, "wb") as f:
        f.write(msu_bytes)

    manifest_path = out_msu_path + ".manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, indent=2)

    print(f"wrote {out_msu_path}: {len(msu_bytes)} bytes, {len(prefixes)} character(s)")
    for c in sidecar["characters"]:
        print(f"  slot {c['slot']}: {c['prefix']} @ offset {c['data_offset']} "
              f"({c['blob_size']} bytes; idle={c['idle_frame_count']} "
              f"walk={c['walk_frame_count']} attack={c['attack_frame_count']})")
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
