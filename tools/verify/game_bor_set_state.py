#!/usr/bin/env python3
"""Focused R1 source/generated BOR set-state contract verifier.

This is intentionally a bounded metadata/SRAM-contract gate.  It does not
pretend Normal, Hard, or Bonus are playable content.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'bor_converter'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bor_levels import parse_levels_from_pak  # noqa: E402
from _harness import pasm_constant_in, Reporter  # noqa: E402


PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
GENERATED = os.path.join(ROOT, 'tools', 'audio', 'campaign_config.pasm')


def db_values(text, label):
    match = re.search(rf'{re.escape(label)}:\s*\n\s*\.db\s+([^\n]+)', text)
    if not match:
        raise AssertionError(f'missing generated table {label}')
    values = []
    for token in match.group(1).split(','):
        token = token.strip()
        if token == 'BOR_SET_UNMAPPED':
            values.append(0xFF)
        elif token == 'CAMPAIGN_BOR_ORIGINAL':
            values.append(0)
        else:
            values.append(int(token, 0))
    return values


def main():
    r = Reporter('R1-BOR-SET-STATE', kind='GATE')
    source = parse_levels_from_pak(PAK)
    with open(GENERATED, encoding='ascii') as f:
        generated = f.read()

    r.check('source has four authored sets', len(source) == 4)
    r.check('source set order is preserved', [s.name for s in source] ==
            ['Easy', 'Normal', 'Hard', 'Bonus'])
    source_thresholds = [s.ifcomplete for s in source]
    generated_thresholds = db_values(generated, 'BorSet_IfComplete')
    r.check(f'ifcomplete thresholds match source {source_thresholds}',
            generated_thresholds == source_thresholds)
    r.check('generated positional IDs are 0..3',
            db_values(generated, 'BorSet_Ids') == list(range(4)))
    r.check('only Easy content is available',
            db_values(generated, 'BorSet_ContentAvailable') == [1, 0, 0, 0])
    r.check('only Easy has a mapped campaign',
            db_values(generated, 'BorSet_CampaignMap') == [0, 0xFF, 0xFF, 0xFF])
    r.check('generated set count is four',
            pasm_constant_in('tools/audio/campaign_config.pasm', 'BOR_SET_COUNT') == 4)
    r.check('completion counter is four bytes',
            pasm_constant_in('src/core/options.pasm', 'Bor_TimesCompleted') == 0x7E2904)
    r.check('SRAM format is version 2 with legacy version accepted',
            pasm_constant_in('src/core/options.pasm', 'OPTIONS_VERSION_CURRENT') == 2 and
            pasm_constant_in('src/core/options.pasm', 'OPTIONS_VERSION_LEGACY') == 1)
    r.check('Easy run start is explicit in production path',
            'jsl BorSet_BeginEasyRun' in open(
                os.path.join(ROOT, 'src', 'core', 'ending.pasm'), encoding='ascii').read())
    r.check('completion credit is owned by campaign end',
            'jsl BorSet_CreditCompletion' in open(
                os.path.join(ROOT, 'src', 'core', 'campaign.pasm'), encoding='ascii').read())
    r.finish()


if __name__ == '__main__':
    main()
