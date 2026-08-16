#!/usr/bin/env python3
"""Convert `spawn_parse.py`'s BOR-native spawn events into this engine's
fixed-format runtime spawn table.

Scope (see plan.md's spawn-table phase for the full writeup): this project's
entity system hardcodes exactly 4 entities (player + 3 AI, `EntityN_Base`
fixed WRAM addresses, CLAUDE.md's own "don't build a general entity-lookup
system" rule) but a real level script can name far more than 3 enemies
across its full timeline (33 spawn events in stage 1A alone). The chosen
compromise is a SINGLE GLOBAL QUEUE: one running index walks the table in
trigger order: when the camera's world X reaches a pending record's
trigger_x AND at least one of the 3 AI slots is free (CHAR_HP==0, this
project's existing soft-kill/unspawned sentinel -- see
phase11_damage_system_softkill memory), that slot gets the record's
position/facing/HP and the index advances. If no slot is free, the record
stays pending and is retried next frame -- this reproduces the game's
"waves" (BOR.C's cluster of 6 `at=960` spawns in this level fills all 3
slots, holds the rest pending, and drains them as kills free slots) without
partitioning events across slots, which would scatter a wave into
unrelated trickle spawns (see this session's advisor consult).

Two further, deliberate simplifications, not oversights:
  - `wait`/`group` events are parsed by spawn_parse.py but NOT emitted into
    this table -- this phase does not implement scroll-blocking-until-clear
    or respawn-pool sizing.
  - Every record spawns as a generic AI-seeking enemy using whichever
    roster character is already wired to the slot it lands in (JHUN/JOE/
    JHUN -- see main.pasm's roster). The source level's specific character
    names (Shermie, Yashiro, ...), the `health` override, and non-enemy
    spawns (the `1up` pickup, `trash` breakable prop) are NOT modeled --
    this engine has no pickup/prop entity class, only CharacterEntity, and
    building one is out of scope here. Every record always spawns at full
    HP (CHAR_HP_MAX). Position/timing fidelity is the goal; character/
    entity-kind identity is explicitly not.

## Coordinate conversion

BOR.C (confirmed by direct source read, ~line 4804): 1AEASY.TXT has no
`direction` line, so BOR's own default (`SCROLL_RIGHT`) applies, and for
that direction `levelpos = advancex` -- a straightforward camera-left-edge
world-X distance from level start, NOT the far-end-counting-down formula
the SCROLL_LEFT branch uses (spawn_parse.py's docstring's caveat about which
formula applies is resolved: it's the plain one here).

So, in BOR-native (320px-screen) units:
    trigger_x_bor = event.at
    spawn_x_bor   = event.at + event.coords[0]   (coords.x is camera-left-
                                                    edge-relative at trigger)
    spawn_y_bor   = event.coords[1]

`convert_bg.py` downscales BOR's 320px-wide screens to this engine's 256px
SNES frame with `scale = 256/320 = 0.8`; the exact same factor must be
applied here for spawned entities to land in the same world-pixel space as
the already-converted backdrop:

    trigger_x_snes = round(trigger_x_bor * 0.8)
    spawn_x_snes   = round(spawn_x_bor * 0.8)
    spawn_y_snes   = round(spawn_y_bor * 0.8)

`flip` (BOR: 0=face left, 1=face right) maps to this engine's
CHAR_FACING_LEFT convention (0=face right, 1=face left) by simple
inversion: facing_left = 1 - flip.

## Binary format

Flat array of 7-byte little-endian records, in trigger order (already
monotonic non-decreasing in the source file -- verified for 1AEASY.TXT):

    +0-1  trigger_x   (u16 LE) -- SNES world-px camera position that arms this record
    +2-3  spawn_x     (u16 LE) -- SNES world-px initial position
    +4    spawn_y     (u8)     -- SNES px initial Y (clamped 0-255)
    +5    facing_left (u8)     -- 0 or 1, CHAR_FACING_LEFT convention
    +6    reserved    (u8, always 0)

No header/count prefix -- the record count is threaded through as a
separate build-time constant (see pack_msu_roster.py's spawn section and
build_rom.py's SPAWN_COUNT cross-check), same convention as this project's
other single-instance baked assets.
"""
import struct
import sys

SCALE = 256 / 320
RECORD_SIZE = 7


def convert_events(spawns):
    """spawns: list of spawn_parse.SpawnEvent, in trigger order.
    Returns (record_count, packed_bytes)."""
    out = bytearray()
    for e in spawns:
        trigger_x = round(e.at * SCALE)
        spawn_x = round((e.at + e.coords[0]) * SCALE)
        spawn_y = round(e.coords[1] * SCALE)
        spawn_y = max(0, min(255, spawn_y))
        facing_left = 1 - (e.flip & 1)
        out += struct.pack('<HHBBB', trigger_x & 0xFFFF, spawn_x & 0xFFFF,
                            spawn_y, facing_left, 0)
    return len(spawns), bytes(out)


def build_from_pak(pak_path, entry_name):
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
    from spawn_parse import parse_spawns_from_pak, SpawnEvent
    events = parse_spawns_from_pak(pak_path, entry_name)
    spawns = [e for e in events if isinstance(e, SpawnEvent)]
    return convert_events(spawns)


def main():
    if len(sys.argv) < 4:
        print('usage: build_spawn_table.py <pak_path> <level_txt_entry> <out.bin>',
              file=sys.stderr)
        raise SystemExit(1)
    count, blob = build_from_pak(sys.argv[1], sys.argv[2])
    with open(sys.argv[3], 'wb') as f:
        f.write(blob)
    print(f'{count} spawn records, {len(blob)} bytes -> {sys.argv[3]}')
    print(f'SPAWN_COUNT = {count}')


if __name__ == '__main__':
    main()
