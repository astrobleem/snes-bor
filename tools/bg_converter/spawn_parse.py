#!/usr/bin/env python3
"""Parse a Beats of Rage level .txt into its SPAWN/WAVE declarations.

`level_parse.py` deliberately ignores this content (its own docstring says
so) -- it only ever needed the scenery keywords for a static/streaming BG
render. This module is the other half: `spawn`/`group`/`wait` blocks,
which describe *what happens* in a level (enemy waves, level-clear gates),
as opposed to what it looks like.

Verified against `DATA\\EASY\\1AEASY.TXT` in the real pak (see that file's
own instructional comment block for the format as BOR's author documented
it) and against Plombo/beatsofrage's `BOR.C` (~line 2000-2040) for the
exact keyword set and block-termination rule actually implemented.

## Block format

Every block is a flat run of `keyword value...` lines, always terminated
by exactly one `at <levelpos>` line (confirmed: no stock block in
1AEASY.TXT lacks a trailing `at`, and `BOR.C`'s parser commits the pending
spawn/wait/group entry specifically on the `at` line). Three block kinds,
distinguished by their opening keyword:

    spawn   <character>          # enemy/obstacle/pickup to place
      alias   <name>             # display name override (cosmetic, unused here)
      map     <0-3>               # colormap/palette variant (unused here -- no
                                   #   per-instance recolor system in this engine)
      health  <n>                 # starting HP
      item    <id>                # obstacles only: what it drops (unused here --
                                   #   no obstacle/pickup entity class in this engine)
      boss    <0/1>               # boss flag (unused here -- no boss handling)
      flip    <0/1>                # 0 = face left, 1 = face right
      coords  <x> <y>              # position, relative to camera scroll at trigger time
      at      <levelpos>           # BLOCK END: triggers when levelpos is reached

    wait
      at      <levelpos>           # BLOCK END: blocks scrolling until all enemies
                                    #   defeated, THEN resumes once levelpos is reached

    group   <min> <max>            # respawn-pool sizing (unused here -- no
                                    #   respawn-pool system in this engine)
      at      <levelpos>           # BLOCK END

## Coordinate system, precisely (this is the part worth getting right)

`levelpos` is NOT a raw scroll pixel count -- `BOR.C` computes
`levelpos = (level->width - 320) - advancex` for a `SCROLL_LEFT`-direction
level (this project's own dumped stock levels are all this direction; the
formula is why `at` values start near 0 and increase as you'd read the
file top-to-bottom even though the player is moving forward through the
level -- `advancex` is scroll distance FROM THE START, `levelpos` counts
down from the far end). And `level->width = numpanels_in_order *
max_panel_bitmap_width` -- NOT the sum of each panel's own (possibly
different) width; see `level_parse.py`'s multi-`order`-line append fix,
which this exact formula depends on getting the panel count right for.

`coords x y` is relative to the camera's LEFT EDGE at the moment of the
trigger, in BOR's native 320-wide screen space -- values outside [0,320]
(`coords 350 160`, `coords -30 210`) are deliberate: that's how a stock
level scripts an enemy walking onto/off of frame from the screen edge
rather than a comment-syntax typo.

This module returns `levelpos`/`coords` UNCONVERTED (BOR's native pixel
units) -- resolving them into this engine's own SNES world-pixel
coordinate space (which needs the SAME 0.8x horizontal scale
`convert_bg.py` already applies to the backdrop, so entities and
background stay spatially aligned) is `build_spawn_table.py`'s job, not
this parser's -- keep "what the level file says" and "what our engine
does with it" in separate, individually-inspectable layers.
"""
import sys


SPAWN_KEYS = {'alias', 'map', 'health', 'item', 'boss', 'flip', 'coords'}


class SpawnEvent:
    """One `spawn` block: an enemy/obstacle/pickup placed at a trigger."""

    def __init__(self, character, at):
        self.character = character
        self.at = at
        self.alias = None
        self.map = 0
        self.health = None
        self.item = None
        self.boss = False
        self.flip = 0
        self.coords = (0, 0)

    def __repr__(self):
        return (f'<Spawn {self.character!r} at={self.at} coords={self.coords} '
                f'health={self.health} flip={self.flip}'
                f'{" boss" if self.boss else ""}'
                f'{f" item={self.item}" if self.item else ""}>')


class WaitEvent:
    """A `wait` block: scrolling blocks until all live enemies are defeated,
    then resumes and the next trigger is checked against `at`."""

    def __init__(self, at):
        self.at = at

    def __repr__(self):
        return f'<Wait at={self.at}>'


class GroupEvent:
    """A `group min max` block: sizes the enemy respawn pool from `at`
    onward (BOR.C: fewer than `min` alive triggers more spawns from the
    upcoming queue, never more than `max` alive at once)."""

    def __init__(self, group_min, group_max, at):
        self.group_min = group_min
        self.group_max = group_max
        self.at = at

    def __repr__(self):
        return f'<Group {self.group_min}-{self.group_max} at={self.at}>'


def parse_spawns(text):
    """Parse level file text (latin1-decoded) into a list of spawn/wait/group
    events, level-file order (== trigger order: 1AEASY.TXT's `at` values are
    monotonically non-decreasing, matching BOR.C's `current_spawn` walking
    the array forward with no re-sort)."""
    events = []
    pending = None  # 'spawn' SpawnEvent, or ('wait',) / ('group', min, max) tuple

    for raw in text.splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        keyword = parts[0].lower()

        if keyword == 'spawn' and len(parts) > 1:
            pending = SpawnEvent(character=parts[1], at=None)
        elif keyword == 'wait':
            pending = ('wait',)
        elif keyword == 'group' and len(parts) > 2:
            pending = ('group', int(parts[1]), int(parts[2]))
        elif pending is not None and keyword in SPAWN_KEYS and isinstance(pending, SpawnEvent):
            if keyword == 'alias':
                pending.alias = parts[1] if len(parts) > 1 else None
            elif keyword == 'map':
                pending.map = int(parts[1])
            elif keyword == 'health':
                pending.health = int(parts[1])
            elif keyword == 'item':
                pending.item = parts[1] if len(parts) > 1 else None
            elif keyword == 'boss':
                pending.boss = bool(int(parts[1]))
            elif keyword == 'flip':
                pending.flip = int(parts[1])
            elif keyword == 'coords':
                pending.coords = (int(parts[1]), int(parts[2]))
        elif keyword == 'at' and len(parts) > 1 and pending is not None:
            at = int(parts[1])
            if isinstance(pending, SpawnEvent):
                pending.at = at
                events.append(pending)
            elif pending[0] == 'wait':
                events.append(WaitEvent(at=at))
            elif pending[0] == 'group':
                events.append(GroupEvent(group_min=pending[1], group_max=pending[2], at=at))
            pending = None

    return events


def parse_spawns_from_pak(pak_path, entry_name):
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent
                          / 'bor_converter'))
    import pak_extract
    text = pak_extract.extract(pak_path, entry_name).decode('latin1')
    return parse_spawns(text)


def main():
    if len(sys.argv) < 3:
        print('usage: spawn_parse.py <pak_path> <level_txt_entry>', file=sys.stderr)
        raise SystemExit(1)
    events = parse_spawns_from_pak(sys.argv[1], sys.argv[2])
    spawns = [e for e in events if isinstance(e, SpawnEvent)]
    waits = [e for e in events if isinstance(e, WaitEvent)]
    groups = [e for e in events if isinstance(e, GroupEvent)]
    print(f'{len(events)} events: {len(spawns)} spawn, {len(waits)} wait, {len(groups)} group')
    for e in events:
        print(' ', e)
    names = sorted({e.character.lower() for e in spawns})
    print(f'\ndistinct character names used: {names}')


if __name__ == '__main__':
    main()
