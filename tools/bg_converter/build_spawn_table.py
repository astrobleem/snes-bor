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
    +6    record_kind (u8)     -- low 3 bits: 0 = enemy, 1 = prop/pickup,
                                   2 = wait, 3 = group, 4 = boss enemy (was
                                   `entity_kind`, 0/1 only, before the wait/
                                   group/boss slice -- see this module's own
                                   "wait/group/boss" section above). Bits
                                   3-4 (plan_game.md 8a row 3, `map`): the
                                   spawn's remap-palette index (0-3, clamped
                                   from the level's own `map` line), same
                                   spare-bits technique used for group's
                                   min/max -- see core/spawn.pasm's
                                   SPAWN_KIND_MASK/SPAWN_MAP_SHIFT. Bits 5-7
                                   (G8 item/pickup slice): PICKUP_TYPE_*
                                   (0-5), or 7 for the non-reward Steamer
                                   driver, real only when kind==RECORD_KIND_
                                   PROP -- see classify_pickup's own
                                   docstring and core/spawn.pasm's
                                   SPAWN_PICKUP_SHIFT/MASK. All 8 bits of
                                   this byte are now in use.
    +7    spawn_hp    (u8)     -- scaled from the level's own `health` line
                                   (0..CHAR_HP_MAX); ignored for props and
                                   wait/group records. Bit 7 is the preserved
                                   `2pitem` contained-item flag; prop health
                                   is <= CHAR_HP_MAX and therefore uses only
                                   the low 7 bits.
    +8    item_roster_idx (u8) -- claude_close_g7_g8_before_g10.md Part 2/3:
                                   real only when record_kind==RECORD_KIND_
                                   PROP AND this is an `obstacle`+`item`
                                   record (a breakable containing a real,
                                   roster-converted item) -- the CONTAINED
                                   item's roster index, consumed by
                                   core/spawn.pasm only once the object's HP
                                   reaches 0 (the break->reveal transition),
                                   never at spawn time. 0 for every other
                                   record (roster slot 0 is RALF, never a
                                   real contained-item slot).
    +9    object_roster_idx (u8) -- the record's OWN real roster index, used
                                   at spawn time: for RECORD_KIND_BOSS_
                                   IDENTIFIED, the identified boss's slot
                                   (unchanged from the old +8 boss behavior);
                                   for RECORD_KIND_PROP, the SPAWNED
                                   character's own roster slot if it has a
                                   real converted sprite (an `item`-type
                                   standalone pickup's own slot, or an
                                   `obstacle`-type breakable's own slot,
                                   e.g. Chair/Table/Trash) -- 0 if unidentified
                                   (keeps the pre-existing borrowed-sprite
                                   reskin fallback, unchanged).

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
RECORD_SIZE = 10  # grew 9->10, claude_close_g7_g8_before_g10.md Part 2/3:
                  # the existing +8 roster_idx byte conflated TWO distinct
                  # identities for an `obstacle`+`item` prop (e.g. `spawn
                  # Chair` / `item Money`) -- the OBJECT's own real sprite
                  # (Chair) and the CONTAINED ITEM's real sprite (Money).
                  # Before this slice +8 held the ITEM's roster index and
                  # Spawn_Play reassigned to it AT SPAWN TIME -- meaning a
                  # not-yet-broken Chair rendered as a floating Money icon
                  # from the moment it spawned (verified: apple/money/meat
                  # were already real roster members, so this was a live,
                  # currently-shipping bug, not a hypothetical). Fixed by
                  # giving each identity its own byte: +8 stays the
                  # CONTAINED item's roster index (now consumed only on
                  # BREAK, not spawn -- see core/spawn.pasm's Spawn_Play);
                  # +9 (new) is the OBJECT's OWN real roster index (Chair/
                  # Table/Trash's own converted sprite -- see
                  # tools/bor_converter/convert_prop.py), used at spawn
                  # time so the object renders as itself before breaking.
                  # A standalone item (`spawn Apple`, entity_type=='item',
                  # no wrapping object) has no separate "before" state --
                  # +9 carries that same roster index directly (renders
                  # immediately, matching pre-existing standalone-item
                  # behavior) and +8 is 0 (nothing to reveal on break,
                  # there's no object phase to break out of).
                  # roster index used to be packed into record_kind's spare
                  # bits 5-7 (3 bits, 0-7) -- that byte is now fully packed
                  # (3 kind + 2 map + 3 roster = 8/8, zero bits left), and the
                  # roster cap grew 8->15 (pack_msu_roster.py, MAX_CHARACTERS),
                  # which needs 4 bits. Rather than steal map's bits (map and
                  # boss-identity are independent, real levels can want both),
                  # +8 is a new, dedicated roster_idx byte -- same
                  # spawn-record-growth pattern already used for entity_kind
                  # (+6) and health (+7). 0 when unused (every non-
                  # RECORD_KIND_BOSS_IDENTIFIED record); core/spawn.pasm only
                  # reads it when record_kind == RECORD_KIND_BOSS_IDENTIFIED.
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
RECORD_KIND_BOSS_IDENTIFIED = 5   # real spawn-driven roster-reassignment
                                  # slice: same as RECORD_KIND_BOSS, but the
                                  # spawned character name was found in the
                                  # ACTUAL shipped roster (--roster) -- the
                                  # real roster index (0-14, roster-growth
                                  # slice) is carried in the record's
                                  # dedicated +8 roster_idx byte (see
                                  # RECORD_SIZE's own comment -- used to be
                                  # 3 spare bits in this byte, outgrew that
                                  # when MAX_CHARACTERS went 8->15), and
                                  # core/spawn.pasm's Spawn_Play re-streams
                                  # that slot's own real character instead
                                  # of leaving it as a reskin.
RECORD_KIND_HOLE = 6              # source hole marker; never consumes an actor slot
SUBTYPE_SHIFT = 5
SUBTYPE_MASK = 0x03
SUBTYPE_NONE = 0
SUBTYPE_BIKER = 1
# Appended runtime-only source enemy identities use the same reassign stream
# as identified bosses, but remain ordinary AI actors.  This preserves the
# fixed record format while allowing later imported levels to retain their
# authored model identity.
SUBTYPE_IDENTIFIED_ENEMY = 2

MAP_SHIFT = 3
PICKUP_SHIFT = 5   # G8 item/pickup slice: record_kind bits 5-7 (spare --
                   # kind uses 0-2, map uses 3-4). See core/spawn.pasm's
                   # SPAWN_PICKUP_SHIFT/MASK and main.pasm's PICKUP_TYPE_*.
PICKUP_TYPE_STEAMER = 7  # Reserved non-reward prop driver; pickup values end at 5.

# Real OpenBOR entity types that mean "not a fighting enemy" -- everything
# else (enemy, player, or an unset/unusual type) spawns as RECORD_KIND_ENEMY.
PROP_ENTITY_TYPES = {'obstacle', 'item', 'none', 'steamer'}

# G8 item/pickup slice (notjustfreespecial.txt): real values sourced
# straight from each pak's own DATA\CHARS\MISC .TXT files, matching
# main.pasm's PICKUP_TYPE_*/PICKUP_HEAL_*/PICKUP_SCORE_* constants exactly
# (health=30 -> APPLE-equivalent heal, health=100 -> MEAT-equivalent full
# heal, score=1000 -> MONEY-equivalent score; "1up" is real OpenBOR's own
# name-based special case for an extra life, not a generic item stat).
#
# VALUE-matched, not name-matched (generalized 2026-08-29,
# notjustfreespecial.txt reopening audit): matching by real health/score
# VALUE instead of a per-pak item name list means this covers any pak's own
# differently-named item sharing the same real stat, with zero new
# hardcoding -- verified against BOTH shipped paks' full level rosters
# (BOR: all 29 level files; TMNT: all 10, including the 2 not currently
# converted) via a direct spawn-data scan: BOR only ever spawns apple/meat/
# money/1up; TMNT ALSO spawns a real, differently-named `Pizza` (data/CHARS/
# MISC/PIZZA.TXT: `type item`, `health 100`, `subtype touch`) in 3 of its
# own levels (streets.txt, streets2.txt, streets3.txt) -- same real heal
# value as MEAT, so it correctly falls out of this value match with no
# TMNT-specific code. TIME/STAR/KNIFE/ORANGE are real MISC entities in one
# or both paks but are spawned by NO level in either pak. GOLD WAS
# incorrectly claimed here as unused too -- re-audited
# (claude_close_g7_g8_before_g10.md Part 3) via a direct pak scan of the
# real shipped level text, not the stale claim: DATA\EASY\1BEASY.TXT's own
# `item gold` line (a Table record, line ~186) is real, shipped, buildable
# content this engine had never converted. GOLD.TXT: `score 5000`, a value
# distinct from MONEY's 1000 -- its own PICKUP_TYPE_GOLD, not folded into
# PICKUP_TYPE_MONEY, so the real 5000-point reward isn't silently
# undercounted to 1000. See plan_game.md G8 for the full accounting.
PICKUP_TYPE_NONE = 0
PICKUP_TYPE_APPLE = 1
PICKUP_TYPE_MEAT = 2
PICKUP_TYPE_MONEY = 3
PICKUP_TYPE_ONEUP = 4
PICKUP_TYPE_GOLD = 5

# RAW (unscaled) real pak values matched against each item's own parsed
# `health`/`score` field -- distinct from main.pasm's own PICKUP_HEAL_*
# constants, which are the ENGINE-side value already scaled by
# health*CHAR_HP_MAX/100 (same scale build_record's spawn_hp uses). These
# three are the real numbers read straight out of APPLE.TXT/MEAT.TXT/
# MONEY.TXT (and TMNT's own PIZZA.TXT, which shares MEAT's raw value).
PICKUP_HEAL_APPLE_RAW = 30
PICKUP_HEAL_MEAT = 100
PICKUP_SCORE_MONEY = 1000
PICKUP_SCORE_GOLD = 5000


def classify_pickup(name, entity_type_lookup_entry):
    """entity_type_lookup_entry: the raw parsed entity dict for `name`
    (from build_pickup_lookup below), or None if `name` isn't a real
    character in this pak. Returns one of the PICKUP_TYPE_* constants
    above, derived from the SAME real fields OpenBOR itself uses for an
    item pickup (name=="1up" special case; else health=heal amount,
    score=score amount) -- matched by real VALUE, not by this project's own
    name list, so any pak's differently-named item sharing a real stat
    (e.g. TMNT's Pizza, health=100, same as MEAT) is covered automatically."""
    if entity_type_lookup_entry is None:
        return PICKUP_TYPE_NONE
    entity = entity_type_lookup_entry
    real_name = str(entity.get('name') or name).strip().lower()
    if real_name == '1up':
        return PICKUP_TYPE_ONEUP
    score = entity.get('score') or 0
    health = entity.get('health') or 0
    if score == PICKUP_SCORE_GOLD:
        return PICKUP_TYPE_GOLD
    if score == PICKUP_SCORE_MONEY:
        return PICKUP_TYPE_MONEY
    if health == PICKUP_HEAL_MEAT:
        return PICKUP_TYPE_MEAT
    if health == PICKUP_HEAL_APPLE_RAW:
        return PICKUP_TYPE_APPLE
    return PICKUP_TYPE_NONE


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


def build_entity_lookup(pak_path):
    """Same traversal as build_type_lookup, but keeps each character's full
    parsed entity dict (not just its `type` string) -- G8 item/pickup slice
    needs `health`/`score`/`name` too, to classify a real pickup effect
    (see classify_pickup above)."""
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
        lookup[key] = entity
        if entity.get('name'):
            lookup.setdefault(str(entity['name']).lower(), entity)
    return lookup


def convert_events(events, type_lookup, roster_lookup=None, entity_lookup=None, holes=None,
                   direction='right', level_width=0):
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
    def roster_index(name):
        if not roster_lookup or not name:
            return None
        key = name.lower()
        value = roster_lookup.get(key)
        if value is not None:
            return value
        # Source Biker-K' is named biker_k in the converted roster prefix.
        return roster_lookup.get(key.replace("-", "_").replace("'", ""))
    # Holes are level data, not spawnable actors.  They are emitted as
    # zero-trigger records so Spawn_Play installs the authored hazard set
    # before the ordinary queue begins.  The fixed record format is retained.
    for hole_x in holes or []:
        out += struct.pack('<HHBBBBBB', 0, round(hole_x * SCALE), 0, 0,
                           RECORD_KIND_HOLE, 0, 0, 0)
    for e in events:
        if isinstance(e, WaitEvent):
            trigger_x = round(e.at * SCALE)
            out += struct.pack('<HHBBBBBB', trigger_x & 0xFFFF, 0, 0, 0,
                                RECORD_KIND_WAIT, 0, 0, 0)
            continue
        if isinstance(e, GroupEvent):
            trigger_x = round(e.at * SCALE)
            group_min = max(0, min(255, e.group_min))
            group_max = max(0, min(255, e.group_max))
            out += struct.pack('<HBBBBBBBB', trigger_x & 0xFFFF, group_min,
                                group_max, 0, 0, RECORD_KIND_GROUP, 0, 0, 0)
            continue

        assert isinstance(e, SpawnEvent)
        trigger_x = round(e.at * SCALE)
        # BOR's vertical scrollers leave advancex unchanged: the authored X
        # coordinate is already world-horizontal, while `at` belongs to the
        # vertical levelpos progression. Horizontal stages retain the legacy
        # at+coords transformation.
        if direction == 'down':
            spawn_x = round(e.coords[0] * SCALE)
        elif direction == 'left':
            # BOR smartspawn stores authored X relative to the camera at the
            # logical trigger.  For SCROLL_LEFT the camera begins at the
            # rightmost extent, so convert that authored local coordinate to
            # the fixed SNES world coordinate without reversing the event.
            if not level_width:
                raise ValueError('SCROLL_LEFT conversion requires source level width')
            spawn_x = round((level_width - 320 - e.at + e.coords[0]) * SCALE)
        else:
            spawn_x = round((e.at + e.coords[0]) * SCALE)
        spawn_y = round(e.coords[1] * SCALE)
        spawn_y = max(0, min(255, spawn_y))
        facing_left = 1 - (e.flip & 1)
        entity_type = type_lookup.get(e.character.lower())
        is_prop = entity_type in PROP_ENTITY_TYPES
        # object_roster_idx (+9): the SPAWNED character's own real roster
        # slot, used at spawn time (renders the record as ITSELF -- a boss's
        # own identity, a standalone item's own sprite, or a breakable
        # object's own sprite). item_roster_idx (+8): claude_close_g7_g8_
        # before_g10.md Part 2/3 -- an `obstacle`+`item` prop's CONTAINED
        # item's own roster slot, consumed only on break (core/spawn.pasm),
        # never at spawn. These were a single conflated byte before this
        # slice -- see RECORD_SIZE's own comment for the real bug that fixed.
        object_roster_idx = (roster_lookup or {}).get(e.character.lower()) if e.boss else None
        item_roster_idx = None
        if is_prop:
            record_kind = RECORD_KIND_PROP
            # Real prop/pickup sprite art (notjustfreespecial.txt follow-up
            # to the G8 "deliberately still not done" item): reuses the
            # EXACT SAME roster-reassignment mechanism already built for
            # SPAWN_KIND_BOSS_IDENTIFIED (core/spawn.pasm's Spawn_Do
            # RosterReassign) rather than inventing a parallel one. If this
            # prop's OWN name (a standalone `spawn <item>`, or a real
            # converted breakable object like Chair/Table/Trash) is in the
            # actual shipped --roster list, object_roster_idx carries that
            # slot so it renders as itself from spawn. If it's an
            # `obstacle`+`item` record AND the CONTAINED item's name is
            # separately in the roster, item_roster_idx carries THAT slot
            # for core/spawn.pasm to reveal only once the object breaks.
            # 0/None for anything not covered by a converted roster slot
            # yet -- same honest partial-coverage pattern classify_pickup
            # already uses; falls back to today's pre-existing borrowed-
            # sprite reskin, unchanged.
            if roster_lookup:
                object_roster_idx = roster_lookup.get(e.character.lower())
                if entity_type == 'obstacle' and e.item:
                    item_roster_idx = roster_lookup.get(e.item.lower())
        elif str((entity_lookup or {}).get(e.character.lower(), {}).get('subtype') or '').lower() == 'biker':
            # A biker is a real source subtype.  Reuse the existing
            # identified-roster streaming path for its source model; the
            # runtime subtype bits below keep it out of ordinary AI logic.
            record_kind = RECORD_KIND_BOSS_IDENTIFIED
            object_roster_idx = roster_index(e.character)
        elif e.boss and object_roster_idx is not None:
            # A source boss remains a boss even when its real model is an
            # appended runtime-only identity. The identified-boss subtype
            # stays zero so Spawn_Do preserves boss status.
            record_kind = RECORD_KIND_BOSS_IDENTIFIED
        elif (roster_index(e.character) is not None
              and roster_index(e.character) >= 29):
            # The original runtime roster through Biker-K' is already part
            # of accepted content.  Newly appended source enemy identities
            # are identified records with an ordinary-enemy subtype, so the
            # shared loader can select their real model without making them
            # bosses or selectable players.
            record_kind = RECORD_KIND_BOSS_IDENTIFIED
            object_roster_idx = roster_index(e.character)
        elif e.boss:
            record_kind = RECORD_KIND_BOSS
        else:
            record_kind = RECORD_KIND_ENEMY
        # plan_game.md 8a row 3 (`map`): pack into record_kind's spare high
        # bits (values 0-4 only need 3), same technique used for group's
        # min/max -- see core/spawn.pasm's SPAWN_KIND_MASK/SPAWN_MAP_SHIFT.
        is_boss_identified = (record_kind == RECORD_KIND_BOSS_IDENTIFIED)
        map_value = max(0, min(3, e.map))
        record_kind |= (map_value << MAP_SHIFT)
        if not is_prop:
            entity = (entity_lookup or {}).get(e.character.lower()) or {}
            if str(entity.get('subtype') or '').lower() == 'biker':
                record_kind |= (SUBTYPE_BIKER << SUBTYPE_SHIFT)
            elif ((record_kind & 0x07) == RECORD_KIND_BOSS_IDENTIFIED
                  and object_roster_idx >= 29 and not e.boss):
                record_kind |= (SUBTYPE_IDENTIFIED_ENEMY << SUBTYPE_SHIFT)
        # object_roster_idx==0 always means "no reassign, keep whatever
        # generic character already happened to be loaded" (roster slot 0 is
        # RALF -- never a real boss/prop identity in practice).
        object_roster_idx_byte = (object_roster_idx & 0xFF) if (
            is_boss_identified or (is_prop and object_roster_idx is not None)) else 0
        item_roster_idx_byte = (item_roster_idx & 0xFF) if (
            is_prop and item_roster_idx is not None) else 0

        # G8 item/pickup slice: a prop record's real contained/standalone
        # item EFFECT, packed into record_kind's remaining bits (5-7).
        # Two real sources, both verified against the shipped/buildable pak
        # data: (a) an `obstacle`-type prop's own `item <name>` line
        # (Table->Apple, Chair->Money -- DATA\EASY\1BEASY.TXT); (b) an
        # `item`-type character spawned directly, standalone (`spawn 1up`
        # -- DATA\EASY\1AEASY.TXT). Zero for every non-prop record. This is
        # the reward VALUE (independent of whether a converted roster sprite
        # exists for it) -- item_roster_idx above is the reveal SPRITE, only
        # populated when one was actually converted.
        pickup_type = PICKUP_TYPE_NONE
        if is_prop and entity_lookup is not None:
            if entity_type == 'item':
                pickup_type = classify_pickup(e.character, entity_lookup.get(e.character.lower()))
            elif entity_type == 'obstacle' and e.item:
                pickup_type = classify_pickup(e.item, entity_lookup.get(e.item.lower()))
        if entity_type == 'steamer':
            # Values 0-5 are real pickup effects. Seven is the reserved
            # non-reward prop-driver sentinel, so it cannot alias MONEY (3)
            # or any other authored pickup when the subtype/pickup fields
            # share this packed byte.
            pickup_type = PICKUP_TYPE_STEAMER
        record_kind |= (pickup_type << PICKUP_SHIFT)
        if e.health is None:
            spawn_hp = CHAR_HP_MAX
        else:
            spawn_hp = round(e.health * CHAR_HP_MAX / 100)
            spawn_hp = max(1, min(CHAR_HP_MAX, spawn_hp))
        if is_prop and e.if2p:
            spawn_hp |= 0x80
        out += struct.pack('<HHBBBBBB', trigger_x & 0xFFFF, spawn_x & 0xFFFF,
                            spawn_y, facing_left, record_kind, spawn_hp,
                            item_roster_idx_byte, object_roster_idx_byte)
    return len(events) + len(holes or []), bytes(out)


def build_from_pak(pak_path, entry_name, roster_lookup=None):
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
    from spawn_parse import parse_spawns_from_pak
    from level_parse import parse_level
    from composite_scene import PakIndex, level_width
    events = parse_spawns_from_pak(pak_path, entry_name)
    text = extract(pak_path, entry_name).decode('latin1')
    level = parse_level(text, name=entry_name)
    source_width = level_width(PakIndex(pak_path), level)
    direction = 'right'
    for raw in text.splitlines():
        parts = raw.strip().split()
        if len(parts) >= 2 and parts[0].lower() == 'direction':
            direction = parts[1].lower()
            break
    holes = [int(parts[1]) for line in text.splitlines()
             for parts in [line.strip().split()]
             if len(parts) >= 2 and parts[0].lower() == 'hole']
    type_lookup = build_type_lookup(pak_path)
    entity_lookup = build_entity_lookup(pak_path)
    return convert_events(events, type_lookup, roster_lookup, entity_lookup, holes,
                          direction=direction, level_width=source_width)


def main():
    if len(sys.argv) < 4:
        print('usage: build_spawn_table.py <pak_path> <level_txt_entry> <out.bin> '
              '[--roster name1,name2,...]', file=sys.stderr)
        print('  --roster: the ACTUAL shipped roster order (build_rom.py\'s '
              'ROSTER_PREFIXES basenames, e.g. ralf,jhun,joe,yashiro,mouser,'
              'foot01,rock,leather) -- lets a boss spawn whose character is '
              'really in that list carry a real roster index (record_kind '
              '== RECORD_KIND_BOSS_IDENTIFIED) instead of falling back to '
              'the plain no-identity RECORD_KIND_BOSS. Omit for a level '
              'with no identified bosses -- same output as before this '
              'flag existed.', file=sys.stderr)
        raise SystemExit(1)
    roster_lookup = None
    if len(sys.argv) >= 6 and sys.argv[4] == '--roster':
        names = sys.argv[5].split(',')
        roster_lookup = {name.strip().lower(): i for i, name in enumerate(names)}
    count, blob = build_from_pak(sys.argv[1], sys.argv[2], roster_lookup)
    with open(sys.argv[3], 'wb') as f:
        f.write(blob)
    print(f'{count} spawn records, {len(blob)} bytes -> {sys.argv[3]}')
    print(f'SPAWN_COUNT = {count}')


if __name__ == '__main__':
    main()
