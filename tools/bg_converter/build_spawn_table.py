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

One further, deliberate simplification, not an oversight:
  - Every record spawns using whichever roster character is already wired
    to the slot it lands in (JHUN/JOE/JHUN -- see main.pasm's roster). The
    source level's specific character names (Shermie, Yashiro, ...) are NOT
    modeled. Position/timing fidelity is the goal; character identity is
    explicitly not.

## `wait`/`group`/`boss` (2026-08-22, follow-up to "level content" generalization)

**Previously** `wait`/`group` events were parsed by spawn_parse.py but not
emitted into this table at all, and `boss` was dropped even though the
record already carried an unused byte. Real data (verified, not assumed):
BOR's own two shipped stages have 6+2 (`wait`+`group`) events in 1A, 5+2 in
1B, but ZERO `boss` lines in either. TMNT's pak (present in repo root, not
yet converted/buildable) has 6 real `boss 1` spawns and 44 more `wait`
events, but no `group` usage. So `wait`/`group` are implemented against
real, buildable, gate-able BOR data; `boss` is real data plumbing sourced
from spawn_parse.py's already-correct `SpawnEvent.boss` field, but has no
buildable pak to verify it end-to-end today (see core/spawn.pasm's own
header for the same caveat on the runtime side).

Real semantics, read directly from Plombo/beatsofrage's `BOR.C`
(`update_scroller()`, ~line 4749-4786), not assumed: `wait`/`group`/`spawn`
are ONE single ordered queue (this module's `events` list, already in
correct order) walked by a single running index. `group min max` sets
GLOBAL mutable pool-size state (default 100/100 = effectively unlimited,
reset every level load) that gates ALL further queue advancement --
spawning pauses entirely once `count_ents(TYPE_ENEMY) >= groupmin`, and
resumes (refilling up to `groupmax`) once it drops below `groupmin` again.
`wait` blocks camera scroll until zero enemies (not props) remain alive,
then releases. See core/spawn.pasm's own header for the runtime half of
this algorithm.

## Entity kind (plan_game.md G8, first slice)

**CORRECTION, 2026-08-21**: this docstring used to claim non-enemy spawns
(BOR's own `1up` pickup, `trash` breakable prop) were silently ignored "by
design." That was false -- verified against the real, currently-shipped
`out/spawn_stage1a/spawn_table.bin`: it byte-for-byte matches regenerating
this table fresh from the pak, and that table's 33 records genuinely include
`1up`/`trash`/`angel` (a boss) as ordinary full-HP, AI-seeking, attacking
enemies, because this module had no concept of entity *kind* at all -- every
parsed `SpawnEvent` became an identical record regardless of what character
it named.

Fixed by repurposing the record's previously-always-zero `reserved` byte
(+6) as `entity_kind`: 0 = enemy (this table's only value before this
change, so old binary consumers/gates that never inspected byte +6 are
unaffected), 1 = prop/pickup. **Generalized 2026-08-22**: classification
used to be a hardcoded name list (`PROP_CHARACTER_NAMES = {'1up', 'trash',
'table', 'chair'}`, explicitly documented as "BOR-only... a follow-up" for
TMNT). `build_type_lookup()` now reads each spawned character's own real
`type` line from its entity `.TXT` (`obstacle`/`item` = prop, everything
else = enemy) -- the same classification OpenBOR itself uses, works for any
pak's real prop/item roster with zero hardcoded names. A prop's HP is fixed at
`PROP_HP = CHAR_HP_PER_HIT` (see main.pasm) rather than the enemy default,
so a single player hit brings it from alive to exactly 0 HP, not partially
damaged -- `core/spawn.pasm`'s `Spawn_Play` reads both the kind and this HP
value and sets `CHAR_INPUT_DRIVEN`/`CHAR_HP` accordingly for whichever AI
slot the record lands in. See that file's own header for the runtime half
(props never seek/attack, but DO get hit/stunned/soft-killed exactly like
an AI enemy -- `CHAR_INPUT_DRIVEN_PROP` mode 3 in main.pasm).

Deliberately still NOT modeled: real prop/pickup sprite art (a prop renders
using whichever character is already streamed into its slot -- visually
wrong, functionally real, see main.pasm's CHAR_INPUT_DRIVEN_PROP comment),
score/life/item-reveal reward effects (no score system exists yet), and the
`boss` flag (`angel` in stage 1A -- unrelated to this slice, still spawns as
an ordinary full-HP AI enemy).

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

## Per-spawn health override (level-format keyword gap, follow-up to G8)

`spawn_parse.py` already parses each spawn block's own `health <n>` line
into `SpawnEvent.health` (verified against the real pak: stage 1A's values
are `[25, 30, 30, 25, 30, 45, 40, 25, 40, 40, 40, 60, 60, 30, 30, 35, 70, 30,
60, 40, 40, 40, 50, 70, 40, 40, 100]`, stage 1B's are `[90, 60, 65, 30, 40,
40, 70, 60, 70, 90, 40, 60, 80]` -- consistently 0-100, matching BOR's
documented percentage-of-max-health convention). This module used to
discard it entirely: every enemy spawned at a hardcoded `CHAR_HP_MAX`
regardless of what the level author actually specified, so every enemy in
both shipped stages took more hits to kill than intended.

Fixed by adding a `spawn_hp` byte to the record (see "Binary format" below),
scaled from BOR's ~0-100 range to this engine's `0..CHAR_HP_MAX` (64) HUD-bar
range: `spawn_hp = round(health * CHAR_HP_MAX / 100)`, clamped to
`[1, CHAR_HP_MAX]` (never spawn already-dead; never exceed the bar). A spawn
with no `health` line (`event.health is None`) gets `CHAR_HP_MAX`, matching
this module's behavior before this change. `core/spawn.pasm`'s prop path
(`entity_kind == 1`) does NOT read this byte -- a prop's HP is a fixed
engine invariant (`CHAR_HP_PER_HIT`, exactly one hit kills), not something a
level's `health` line should override.

## Binary format

Flat array of 8-byte little-endian records, in trigger order (already
monotonic non-decreasing in the source file -- verified for 1AEASY.TXT).
The record layout is UNCHANGED in size from before the wait/group/boss
slice -- byte +6 (`record_kind`, was `entity_kind`) is generalized to a
5-way discriminator instead of widening the record, specifically to avoid
touching the four hand-synced *8/record-size sites core/spawn.pasm's own
header calls out (Spawn_CountX8, SPAWN_MAX_RECORDS*8, the last-record seek,
Spawn_Play's own shift):

    +0-1  trigger_x   (u16 LE) -- SNES world-px camera position that arms this record
    +2-3  spawn_x     (u16 LE) -- SNES world-px initial position.
                                   record_kind==3 (group) repurposes these
                                   two bytes as group_min (+2) / group_max
                                   (+3) instead (single bytes, real values
                                   are always <=100).
    +4    spawn_y     (u8)     -- SNES px initial Y (clamped 0-255). 0 for
                                   wait/group records.
    +5    facing_left (u8)     -- 0 or 1, CHAR_FACING_LEFT convention. 0 for
                                   wait/group records.
    +6    record_kind (u8)     -- 0 = enemy, 1 = prop/pickup, 2 = wait,
                                   3 = group, 4 = boss enemy (was
                                   `entity_kind`, 0/1 only, before this
                                   slice -- see this module's own "wait/
                                   group/boss" section above)
    +7    spawn_hp    (u8)     -- scaled from the level's own `health` line
                                   (0..CHAR_HP_MAX); ignored for props and
                                   wait/group records.

No header/count prefix -- the record count is threaded through as a
separate build-time constant (see pack_msu_roster.py's spawn section and
build_rom.py's SPAWN_COUNT cross-check), same convention as this project's
other single-instance baked assets.
"""
import ntpath
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bor_converter'))
from pak_extract import read_entries, extract
from entity_parse import parse_entity

SCALE = 256 / 320
RECORD_SIZE = 8
CHAR_HP_MAX = 64   # == main.pasm's CHAR_HP_MAX; hand-copied here since this
                    # module has no access to main.pasm's own constant table
                    # (same pattern PROP_HP below already uses)

PROP_HP = 4   # == main.pasm's CHAR_HP_PER_HIT: one hit takes a prop from
              # alive to exactly 0, never partially damaged.
RECORD_KIND_ENEMY = 0
RECORD_KIND_PROP = 1
RECORD_KIND_WAIT = 2
RECORD_KIND_GROUP = 3
RECORD_KIND_BOSS = 4

# Real OpenBOR entity types that mean "not a fighting enemy" -- everything
# else (enemy, player, or an unset/unusual type) spawns as RECORD_KIND_ENEMY.
PROP_ENTITY_TYPES = {'obstacle', 'item'}


def build_type_lookup(pak_path):
    """Generalized 2026-08-22 (plan_game.md, "level content" follow-up to the
    moveset pipeline generalization -- see moveset_pipeline_generalization
    project memory): entity kind used to be decided by a hardcoded name set
    (`PROP_CHARACTER_NAMES = {'1up', 'trash', 'table', 'chair'}`), explicitly
    documented as "BOR-only... TMNT hasn't been converted at all yet, so its
    own decorative prop names are a follow-up." Real OpenBOR entity files
    already self-declare this via their own `type` line (`enemy`/`player`/
    `obstacle`/`item`/unset) -- measured directly against both available
    paks: BOR has 8 `obstacle` + 6 `item` characters, TMNT has 19 `obstacle`
    + 7 `item`, neither list resembling the other. Reading each spawned
    character's real `type` from its own entity file generalizes this to
    any pak's real prop/item roster with no name list at all.

    Returns {character_name.lower(): type.lower()} for every real character
    `.TXT` under CHARS\\ in the pak, indexed by both its filename (matches
    spawn.character values like "1up", "trash") and its self-declared
    internal `name` field (covers the rare case they differ)."""
    entries = read_entries(pak_path)
    lookup = {}
    for entry in entries:
        if 'CHARS' not in entry.name.upper() or not entry.name.upper().endswith('.TXT'):
            continue
        base = ntpath.basename(entry.name)
        key = base.rsplit('.', 1)[0].lower()
        try:
            entity = parse_entity(extract(pak_path, entry.name).decode('latin1'))
        except Exception:
            continue
        entity_type = str(entity.get('type') or 'enemy').lower()
        lookup[key] = entity_type
        if entity.get('name'):
            lookup.setdefault(str(entity['name']).lower(), entity_type)
    return lookup


def convert_events(events, type_lookup):
    """events: list of spawn_parse.SpawnEvent/WaitEvent/GroupEvent, in
    trigger order (spawn_parse.py already interleaves all three correctly --
    see core/spawn.pasm's own header for why this single ordered queue
    matters: BOR.C's `group`/`wait` markers are walked in the SAME queue as
    spawns, not separate tables). type_lookup: build_type_lookup(pak_path)'s
    result -- entity kind is derived from each spawned character's own real
    `type` field, not a hardcoded name list (see build_type_lookup's
    docstring). A name absent from the lookup (shouldn't happen for a real
    pak's own characters) defaults to RECORD_KIND_ENEMY, matching this
    module's pre-generalization behavior. Returns (record_count,
    packed_bytes)."""
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
    from spawn_parse import SpawnEvent, WaitEvent, GroupEvent

    out = bytearray()
    for e in events:
        if isinstance(e, WaitEvent):
            trigger_x = round(e.at * SCALE)
            out += struct.pack('<HHBBBB', trigger_x & 0xFFFF, 0, 0, 0,
                                RECORD_KIND_WAIT, 0)
            continue
        if isinstance(e, GroupEvent):
            trigger_x = round(e.at * SCALE)
            group_min = max(0, min(255, e.group_min))
            group_max = max(0, min(255, e.group_max))
            out += struct.pack('<HBBBBBB', trigger_x & 0xFFFF, group_min,
                                group_max, 0, 0, RECORD_KIND_GROUP, 0)
            continue

        assert isinstance(e, SpawnEvent)
        trigger_x = round(e.at * SCALE)
        spawn_x = round((e.at + e.coords[0]) * SCALE)
        spawn_y = round(e.coords[1] * SCALE)
        spawn_y = max(0, min(255, spawn_y))
        facing_left = 1 - (e.flip & 1)
        entity_type = type_lookup.get(e.character.lower())
        is_prop = entity_type in PROP_ENTITY_TYPES
        if is_prop:
            record_kind = RECORD_KIND_PROP
        elif e.boss:
            record_kind = RECORD_KIND_BOSS
        else:
            record_kind = RECORD_KIND_ENEMY
        if e.health is None:
            spawn_hp = CHAR_HP_MAX
        else:
            spawn_hp = round(e.health * CHAR_HP_MAX / 100)
            spawn_hp = max(1, min(CHAR_HP_MAX, spawn_hp))
        out += struct.pack('<HHBBBB', trigger_x & 0xFFFF, spawn_x & 0xFFFF,
                            spawn_y, facing_left, record_kind, spawn_hp)
    return len(events), bytes(out)


def build_from_pak(pak_path, entry_name):
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
    from spawn_parse import parse_spawns_from_pak
    events = parse_spawns_from_pak(pak_path, entry_name)
    type_lookup = build_type_lookup(pak_path)
    return convert_events(events, type_lookup)


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
