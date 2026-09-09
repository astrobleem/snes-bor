#!/usr/bin/env python3
"""Regression: a source player may omit ANI_ATTACK1 entirely."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pack_msu_roster as packer  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as root:
        def anim(name):
            path = os.path.join(root, name)
            os.makedirs(path)
            with open(os.path.join(path, 'manifest.json'), 'w', encoding='utf-8') as f:
                json.dump({'frames': [{'delay': 1, 'bin': 'frame00.bin'}]}, f)
            with open(os.path.join(path, 'frame00.bin'), 'wb') as f:
                f.write(bytes(1536))
            with open(os.path.join(path, 'palette.txt'), 'w', encoding='ascii') as f:
                f.write(''.join('lda #$0000\n' for _ in range(16)))
            return path

        prefix = os.path.join(root, 'synthetic')
        roles = {key: None for key in ('idle', 'walk', 'fall', 'rise')}
        roles.update({'idle': 0, 'walk': 1, 'fall': 2, 'rise': 3,
                      'attack': None, 'attack2': None,
                      'attack2_is_grab': False})
        dirs = [anim(name) for name in ('idle', 'walk', 'fall', 'rise')]
        moveset = {
            'entity': 'SyntheticNoAttack',
            'animations': [{'ordinal': i, 'name': name, 'dir': d}
                           for i, (name, d) in enumerate(zip(('idle', 'walk', 'fall', 'rise'), dirs))],
            'roles': roles,
            'atchain': [],
        }
        with open(prefix + '_moveset.json', 'w', encoding='utf-8') as f:
            json.dump(moveset, f)
        blob, info = packer.pack_character_blob(prefix)
        assert info['attack_frame_count'] == 0
        assert info['attack_delay'] == 0
        assert len(blob) == packer.PALETTE_BYTES + (1 + 1 + 1 + 1) * packer.ANIM_FRAME_BYTES
    print('PASS: missing attack packs as zero count with empty bytes')


if __name__ == '__main__':
    main()
