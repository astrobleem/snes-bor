#!/usr/bin/env python3
"""Parser for OpenBOR entity definition files (e.g. DATA\\CHARS\\RALF\\RALF.TXT).

Tab/whitespace-delimited, line-oriented format. Top-level scalar directives
(name, health, speed, type, shadow, icon, diesound) and repeatable `remap`
lines, followed by one or more `anim <name>` blocks. Inside an anim block,
`loop`/`delay`/`offset`/`bbox`/`attack`/`move`/`sound`/`range` directives set
"current" state that applies to every `frame` line until overridden --
e.g. RALF.TXT's `pain` anim sets `delay 12`, one `frame`, then `delay 50`,
another `frame`, then `delay 12` again: each `frame` line snapshots
whatever state directives preceded it, not just the block's opening values.

This does not attempt to replicate OpenBOR's full runtime semantics (attack
hitbox activation windows, move's exact interaction with physics, range's
AI-targeting meaning) -- it only extracts the per-frame data this project's
asset pipeline actually needs: which GIF, how long to hold it, and where its
hotspot/bbox are, so a future multi-frame converter can position frames
consistently and a future in-engine animation player can drive playback.
"""
import sys


def _tokenize(line):
    return line.split()


def parse_entity(text):
    lines = text.splitlines()
    entity = {
        'name': None, 'health': None, 'speed': None, 'type': None,
        'subtype': None,
        'shadow': None, 'icon': None, 'diesound': None, 'score': None,
        'remaps': [], 'animations': {},
        # G7 content-audit slice: real BOR.C `atchain <n1> <n2> ...` --
        # each value is a 1-based index into the real attack-number family
        # (1=attack1, 2=attack2, 3=attack3, 4=attack4); perform_atchain()
        # (engine/openbor.c) cycles the player's own attack button through
        # this sequence on repeated presses within a combo window. Empty if
        # the character declares no `atchain` line (most of this project's
        # roster) -- real per-character data, not invented.
        'atchain': [],
    }

    SCALAR_KEYS = {'name', 'health', 'speed', 'type', 'subtype', 'shadow', 'icon', 'diesound', 'score'}

    cur_anim = None
    cur_anim_name = None
    # "pending" state, sticky across frame lines within one anim block
    pending = {'delay': None, 'offset': None, 'bbox': None, 'attack': None,
               'move': None, 'sound': None}

    for raw in lines:
        toks = _tokenize(raw)
        if not toks:
            continue
        key = toks[0].lower()
        args = toks[1:]

        if key == 'anim':
            cur_anim_name = args[0]
            cur_anim = {
                'loop': 0, 'range': None, 'delay': None, 'offset': None, 'bbox': None,
                'frames': [],
            }
            entity['animations'][cur_anim_name] = cur_anim
            pending = {'delay': None, 'offset': None, 'bbox': None, 'attack': None,
                       'move': None, 'sound': None}
            continue

        if cur_anim is None:
            if key in SCALAR_KEYS:
                entity[key] = int(args[0]) if args and args[0].lstrip('-').isdigit() else (args[0] if args else None)
            elif key == 'remap':
                entity['remaps'].append((args[0], args[1]))
            elif key == 'atchain':
                entity['atchain'] = [int(a) for a in args if a.lstrip('-').isdigit()]
            continue

        # inside an anim block
        if key == 'loop':
            cur_anim['loop'] = int(args[0])
        elif key == 'range':
            cur_anim['range'] = tuple(int(a) for a in args)
        elif key == 'delay':
            pending['delay'] = int(args[0])
            if cur_anim['delay'] is None:
                cur_anim['delay'] = pending['delay']
        elif key == 'offset':
            pending['offset'] = (int(args[0]), int(args[1]))
            if cur_anim['offset'] is None:
                cur_anim['offset'] = pending['offset']
        elif key == 'bbox':
            pending['bbox'] = tuple(int(a) for a in args)
            if cur_anim['bbox'] is None:
                cur_anim['bbox'] = pending['bbox']
        elif key == 'attack':
            pending['attack'] = tuple(int(a) for a in args)
        elif key == 'move':
            pending['move'] = int(args[0])
        elif key == 'sound':
            pending['sound'] = args[0] if args else None
        elif key == 'frame':
            cur_anim['frames'].append({
                'gif': args[0],
                'delay': pending['delay'],
                'offset': pending['offset'],
                'bbox': pending['bbox'],
                'attack': pending['attack'],
                'move': pending['move'],
                'sound': pending['sound'],
            })
        # unrecognized directives inside an anim block (rare/model-specific) are ignored

    return entity


def parse_entity_file(pak_path, entry_name):
    sys.path.append(__import__('os').path.dirname(__file__))
    from pak_extract import extract
    data = extract(pak_path, entry_name)
    return parse_entity(data.decode('latin1'))


def main():
    if len(sys.argv) != 3:
        print('usage: entity_parse.py <pak_path> <entry_name>')
        raise SystemExit(1)
    entity = parse_entity_file(sys.argv[1], sys.argv[2])
    print(f"name={entity['name']} health={entity['health']} speed={entity['speed']} type={entity['type']}")
    for anim_name, anim in entity['animations'].items():
        print(f"anim {anim_name}: loop={anim['loop']} delay={anim['delay']} offset={anim['offset']} "
              f"bbox={anim['bbox']} frames={len(anim['frames'])}")
        for f in anim['frames']:
            print(f"    {f['gif']}  delay={f['delay']} offset={f['offset']} bbox={f['bbox']} "
                  f"attack={f['attack']} move={f['move']}")


if __name__ == '__main__':
    main()
