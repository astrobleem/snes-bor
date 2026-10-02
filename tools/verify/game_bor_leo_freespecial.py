"""Packed/control-flow regression for LEO's real freespecial path."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'audio'))
from shipped_content import ROSTER_CONFIGS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
JUMP = os.path.join(ROOT, 'src', 'core', 'jump.pasm')


def main():
    with open(os.path.join(ROOT, 'out', 'leo_moveset.json'), encoding='utf-8') as f:
        moveset = json.load(f)
    role = moveset['roles']['freespecial']
    anim = next(a for a in moveset['animations'] if a['ordinal'] == role)
    frame_count = anim['frames']
    assert role is not None and frame_count > 0

    leo = next(e for e in ROSTER_CONFIGS
               if e.get('source_character', '').upper().endswith('\\LEO'))
    assert leo['converted_prefix'] == 'out/leo'

    source = open(JUMP, encoding='utf-8').read()
    real = re.search(
        r"lda CHAR_FREESPECIAL_FCOUNT\s*\n\s*bne Jump_FreespecialTrigger__real_anim\s*\n"
        r"\s*; BOR\.C.*?\n\s*jsl Jump_MissingFreespecialFallback\s*\n"
        r"\s*rtl\s*\nJump_FreespecialTrigger__real_anim:.*?\n"
        r"\.a8\s*\n\s*lda #9",
        source, re.S)
    assert real, 'FCOUNT dispatch contract missing'
    fallback_start = source.index('Jump_MissingFreespecialFallback:')
    assert 'lda #2' in source[fallback_start:fallback_start + 160]
    assert 'lda #3' in source[fallback_start:fallback_start + 1400]
    assert source.index('Jump_FreespecialTrigger__real_anim:') > source.index(
        'bne Jump_FreespecialTrigger__real_anim')
    print(f'LEO freespecial role={role} packed FCOUNT={frame_count}')
    print('FCOUNT=0 -> dojump(2)/mode 3; FCOUNT>0 -> variant 9')
    print('GATE BOR-LEO-FREESPECIAL: PASS')


if __name__ == '__main__':
    main()
