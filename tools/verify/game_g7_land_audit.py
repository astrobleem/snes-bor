#!/usr/bin/env python3
"""notjustfreespecial.txt item 7: exact `land`/autoland re-audit.

Static-only (no Mesen2 needed) -- finding-reporter, not a pure gate. Earlier
in the G7 audit this project claimed "zero forcedirection/projectile/blast/
autoland/ATTACK_FORCE config anywhere" and classified `land` as
content-inapplicable outright. That claim was WRONG: JHUN ships a
commented-out `#anim land` (genuinely inapplicable, disabled data) but LEO
ships a real, uncommented `anim land` entry (1 frame, reuses rise01.gif).

Real BOR.C (DCurrent/openbor, engine/openbor.c) normally gates `doland()`/
ANI_LAND on BLAST_TOSS-family attack-force configuration (forcedirection,
projectile, blast, autoland, ATTACK_FORCE). But `player_fall_check()` is a
SEPARATE, player-only trigger: any player holding UP+JUMP while
CHAR_SELECTED_THROWN lands via ANI_LAND instead of the ordinary FALL
reaction, gated only on the global `autoland != 2` (real default: 0, i.e.
enabled) -- independent of any per-model/per-attack flag. LEO's real anim
data makes this reachable for at least one shipped roster member.

This project's engine now implements that real mechanic
(Character_Throw_Play__land in vm_native_engine.pasm) and it is covered by
a live Mesen2 gate (game_g7_throw.py section 9). This script's own job is
narrower: keep re-confirming the RAW SOURCE finding itself (which
characters declare which keywords, real vs. commented) across both paks
this project builds from, so the finding can't silently drift stale again
the way it did before this audit caught it. It reports the finding; it does
not re-assert the runtime behavior (that's game_g7_throw.py's job).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bor_converter'))
from pak_extract import extract  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import playable_roster as _roster  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PAKS = {
    'bor': 'Beats of Rage Original [v.3.0 Build 4086].pak',
    'tmnt': 'Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak',
}

# build_rom.py's own printed PLAYABLE roster order (single authoritative
# source, gate/test hygiene per notjustfreespecial.txt), split into its two
# source paks -- the first 4 slots are BOR-original characters, the rest
# TMNT; that split point is a fact about this project's own roster
# composition, not something ROSTER_PREFIXES itself encodes, so it is
# recorded here explicitly rather than re-derived. Uses playable_roster(),
# not the full roster() -- real prop/pickup roster members (out/apple,
# convert_prop.py) live at `DATA\CHARS\MISC\<name>.TXT` in the BOR pak, not
# `DATA\CHARS\<NAME>\<NAME>.TXT` in either pak this script's own extract()
# path assumes, AND structurally cannot declare `land`/`autoland` at all
# (convert_prop.py's own docstring: real MISC items declare exactly one
# `idle` anim, nothing else) -- out of scope for this audit either way.
_BOR_ORIGINAL_COUNT = 4
_full_roster = [name.upper() for name in _roster()]
ROSTER = {
    'bor': _full_roster[:_BOR_ORIGINAL_COUNT],
    'tmnt': _full_roster[_BOR_ORIGINAL_COUNT:],
}

# Every real BOR.C keyword that can gate doland()/ANI_LAND, plus the
# animation declaration itself.
LAND_KEYWORDS = ('land', 'autoland', 'forcedirection', 'blast',
                  'attack_force', 'projectile', 'toss')


# Known, already-investigated, already-handled real (uncommented) hits.
# LEO's real `anim land` is the item-7 finding itself -- now implemented by
# Character_Throw_Play__land and covered live by game_g7_throw.py section 9.
# Anything real (uncommented) NOT in this set is a genuinely NEW finding
# this script hasn't been taught about yet, and should still fail loudly
# rather than being silently swallowed.
KNOWN_REAL_HITS = {
    ('LEO', 'land'),
}


def main():
    total_checked = 0
    commented_hits = []
    real_hits = []
    unexpected_hits = []
    for pak_key, chars in ROSTER.items():
        pak_path = os.path.join(ROOT, PAKS[pak_key])
        if not os.path.isfile(pak_path):
            print(f'FAIL: pak not found: {pak_path}')
            sys.exit(1)
        for c in chars:
            entry = r'DATA\CHARS\%s\%s.TXT' % (c, c)
            data = extract(pak_path, entry)
            text = data.decode('latin-1', errors='replace')
            total_checked += 1
            for i, line in enumerate(text.splitlines()):
                stripped = line.strip().lower()
                for kw in LAND_KEYWORDS:
                    if stripped.startswith(kw) or f' {kw}' in stripped or f'\t{kw}' in stripped:
                        is_commented = stripped.startswith('#') or stripped.startswith(';')
                        entry_tuple = (c, i, line.strip(), kw)
                        if is_commented:
                            commented_hits.append(entry_tuple)
                        else:
                            real_hits.append(entry_tuple)
                            if (c, kw) not in KNOWN_REAL_HITS:
                                unexpected_hits.append(entry_tuple)

    print(f'{total_checked} roster characters checked across {len(ROSTER)} paks, '
          f'every real BOR.C doland()/ANI_LAND keyword: {LAND_KEYWORDS}')

    if commented_hits:
        print(f'{len(commented_hits)} commented-out/disabled hit(s) (genuinely '
              f'inapplicable, dead data):')
        for c, i, line, kw in commented_hits:
            print(f'  {c}: line {i} (matched `{kw}`, commented): {line}')

    if real_hits:
        print(f'{len(real_hits)} real (uncommented) hit(s):')
        for c, i, line, kw in real_hits:
            known = (c, kw) in KNOWN_REAL_HITS
            print(f'  {c}: line {i} (matched `{kw}`{"" if known else ", UNEXPECTED"}): {line}')

    if unexpected_hits:
        print(f'FAIL: {len(unexpected_hits)} real hit(s) not in KNOWN_REAL_HITS -- '
              f'a NEW land/autoland finding exists that this project has not yet '
              f'investigated/implemented:')
        for c, i, line, kw in unexpected_hits:
            print(f'  {c}: line {i} (matched `{kw}`): {line}')
        sys.exit(1)

    print('GATE G7-LAND-AUDIT: PASS')
    print('  All real (uncommented) hits are the known LEO `anim land` finding, '
          'already implemented by Character_Throw_Play__land and covered live '
          'by game_g7_throw.py section 9. All other keyword occurrences are '
          'commented-out/disabled data (JHUN\'s `#anim land`), genuinely '
          'content-inapplicable. No new undiscovered land/autoland reachability '
          'exists in either pak this project builds from.')


if __name__ == '__main__':
    main()
