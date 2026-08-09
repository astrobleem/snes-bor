#!/usr/bin/env python3
"""Parse a Beats of Rage level .txt into its background-layer declarations.

BOR level files are a flat keyword-per-line format (same general shape as the
character entity .txt files `bor_converter/entity_parse.py` handles). Only the
scenery keywords matter here -- spawn/group/wait/at describe enemy waves and are
ignored.

The scenery model, verified against `DATA\\EASY\\4BEASY.TXT` in the real pak:

    background   data/bgs/warehous/back.gif    # tiling strip drawn behind all
    panel        data/bgs/warehous/p00.gif     # = 'a'  (declaration order
    panel        data/bgs/warehous/p01.gif     # = 'b'   assigns the letters)
    ...
    frontpanel   data/bgs/warehous/front.gif   # overlay drawn in front
    order        abcdefabcdef...               # left-to-right panel sequence

`order` indexes the panels by letter: 'a' is the first `panel` line, 'b' the
second, and so on. The level is that sequence of panels laid side by side.

This module deliberately does NOT model scroll speed, parallax, or z-depth.
snes-bor's Phase 6 backdrop is static and non-scrolling (plan.md 2.4 rules
scrolling out), so only the scene at scroll position 0 is ever built.
"""
import string
import sys


class Level:
    """Scenery declarations from one BOR level file."""

    def __init__(self, name, background, panels, frontpanel, order):
        self.name = name
        self.background = background      # pak path or None
        self.panels = panels              # list of pak paths, declaration order
        self.frontpanel = frontpanel      # pak path or None
        self.order = order                # letter string, e.g. "abcdefabcdef"

    def ordered_panels(self):
        """Resolve `order` into a list of panel pak paths, left to right.

        Unknown letters are skipped rather than raising: some stock BOR levels
        carry letters past the end of their own panel list, and the engine
        simply ignores those.
        """
        out = []
        for ch in self.order:
            idx = string.ascii_lowercase.find(ch.lower())
            if 0 <= idx < len(self.panels):
                out.append(self.panels[idx])
        return out

    def __repr__(self):
        return (f'<Level {self.name!r} background={self.background!r} '
                f'panels={len(self.panels)} frontpanel={self.frontpanel!r} '
                f'order={self.order[:16]!r}...>')


def to_pak_name(path):
    """Convert a level file's forward-slash path to a pak entry name.

    Level files write `data/bgs/warehous/back.gif`; pak entries are
    `DATA\\BGS\\WAREHOUS\\BACK.GIF`. `pak_extract.extract` already matches
    case-insensitively, so only the separator has to change.
    """
    return path.replace('/', '\\').strip()


def parse_level(text, name='level'):
    """Parse level file text (latin1-decoded) into a Level."""
    background = None
    frontpanel = None
    panels = []
    order = ''

    for raw in text.splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        keyword = parts[0].lower()

        if keyword == 'background' and len(parts) > 1:
            background = to_pak_name(parts[1])
        elif keyword == 'panel' and len(parts) > 1:
            panels.append(to_pak_name(parts[1]))
        elif keyword == 'frontpanel' and len(parts) > 1:
            frontpanel = to_pak_name(parts[1])
        elif keyword == 'order' and len(parts) > 1:
            order = parts[1]

    # A level with panels but no explicit `order` means "each panel once, in
    # declaration order" -- BOR's own default.
    if panels and not order:
        order = string.ascii_lowercase[:len(panels)]

    return Level(name, background, panels, frontpanel, order)


def parse_level_from_pak(pak_path, entry_name):
    """Read and parse a level .txt straight out of a BOR .pak."""
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent
                          / 'bor_converter'))
    import pak_extract
    text = pak_extract.extract(pak_path, entry_name).decode('latin1')
    return parse_level(text, name=entry_name)


def main():
    if len(sys.argv) < 3:
        print('usage: level_parse.py <pak_path> <level_txt_entry>', file=sys.stderr)
        raise SystemExit(1)
    level = parse_level_from_pak(sys.argv[1], sys.argv[2])
    print(level)
    print(f'  background: {level.background}')
    for i, p in enumerate(level.panels):
        print(f'  panel {string.ascii_lowercase[i]}: {p}')
    print(f'  frontpanel: {level.frontpanel}')
    print(f'  order: {level.order}')
    print(f'  resolved sequence: {len(level.ordered_panels())} panels')


if __name__ == '__main__':
    main()
