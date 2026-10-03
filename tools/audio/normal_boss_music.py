"""Source/code receipt for Normal-only ordinary-biker boss-music exclusion.

The bounded instruction evaluator checks this branch predicate, not native audio.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/audio'), str(ROOT / 'tools/bor_compile')]


def gate(source):
    start = source.index('Spawn_Play__environment_done:')
    start = source.index('    lda.l Spawn_ScratchKind', start)
    finish = source.index('Spawn_Play__advance_index:', start)
    return source[start:finish]


def selects_boss(code, kind, subtype, campaign):
    constants = dict(SPAWN_KIND_BOSS=4, SPAWN_KIND_BOSS_IDENTIFIED=5,
                     SPAWN_SUBTYPE_BIKER=1, SPAWN_SUBTYPE_IDENTIFIED_ENEMY=2,
                     CAMPAIGN_BOR_NORMAL_DEV=3)
    values = dict(Spawn_ScratchKind=kind, Spawn_ScratchSubtype=subtype, Game_CampaignId=campaign)
    accumulator = None
    equal = None
    for line in code.splitlines():
        line = line.split(';', 1)[0].strip()
        if not line or line == 'Spawn_Play__advance_boss_music:':
            continue
        if line.startswith('lda.l '):
            accumulator = values[line[6:]]
        elif line.startswith('cmp #'):
            equal = accumulator == constants[line[5:]]
        elif line.startswith(('beq ', 'bne ')):
            op, target = line.split()
            if equal is None:
                raise ValueError('boss-music branch without comparison')
            if equal == (op == 'beq'):
                if target == 'Spawn_Play__advance_index':
                    return False
                if target == 'Spawn_Play__advance_boss_music':
                    return True
                raise ValueError('unknown boss-music branch target: ' + target)
        elif line == 'jsl Music_SelectBossTrack_Long':
            return True
        else:
            raise ValueError('unsupported boss-music predicate instruction: ' + line)
    raise ValueError('boss-music predicate has no terminal')


def receipt():
    from compiler import Source, stage
    import shipped_content as shipped
    code = gate((ROOT / 'src/core/spawn.pasm').read_text())
    # Exact profile boundary, including Easy and foreign compatibility behavior.
    for campaign in range(4):
        for kind in range(7):
            for subtype in range(4):
                expected = kind == 4 or (kind == 5 and subtype != 2
                                        and not (campaign == 3 and subtype == 1))
                if selects_boss(code, kind, subtype, campaign) != expected:
                    raise ValueError(f'boss-music policy drift: {campaign=} {kind=} {subtype=}')
    text = (ROOT / 'tools/audio/audio_music_ids.pasm').read_text()
    def table(label):
        return [int(v) for v in re.search(label + r':\s*\.db ([^\r\n]+)', text)[1].split(',')]
    tracks, bosses = table('Music_StageTracks'), table('Music_StageBossTracks')
    catalog = json.loads((ROOT / 'tools/audio/music_catalog.json').read_text())
    ids = {t['track_key'].replace('\\', '/').casefold(): t['track_id'] for t in catalog['tracks']}
    rows = []
    for slot, cfg in enumerate(shipped.STAGE_CONFIGS):
        if cfg['family'] != 'bor-original' or cfg.get('source_set_id') != 1:
            continue
        source = Source(cfg['pak'])
        ir = stage(source, cfg['source_level'])
        key = 'bor-original:' + (ir.bossmusic or '').replace('\\', '/').casefold()
        expected = ids[key] if ir.bossmusic else 0
        if bosses[slot] != expected:
            raise ValueError('source boss-track mismatch: ' + cfg['source_level'])
        bikers = [dict(queue_index=i, at=e.at, boss=e.boss, model=e.character)
                  for i, e in enumerate(ir.queue) if e.character and 'biker' in e.character.casefold()]
        rows.append(dict(slot=slot, source=cfg['source_level'],
                         source_sha256=hashlib.sha256(source.read(cfg['source_level'])).hexdigest(),
                         source_bossmusic=ir.bossmusic, stage_track=tracks[slot], boss_track=expected,
                         biker_events=bikers,
                         impact='PREMATURE_CUE_PREVENTED' if bikers and expected else 'NO_BIKER_CUE_EFFECT',
                         authored_boss_events=[dict(queue_index=i, at=e.at, model=e.character)
                                               for i, e in enumerate(ir.queue) if e.boss]))
    return dict(classification='NEW_NORMAL_REQUIRED_BEHAVIOR', status='PASS',
                event='ordinary-biker must not start stage bossmusic',
                predicate_sha256=hashlib.sha256(code.encode()).hexdigest(),
                policy_cases_checked=112, stages=rows,
                compatibility='Easy/foreign cue policy unchanged; identified-enemy exclusion and real-boss cue retained',
                nonclaims=['source/branch-predicate evidence only; no native execution or audible acceptance',
                           'current generated queues may predate the new Normal model-binding policy'])


if __name__ == '__main__':
    print(json.dumps(receipt(), indent=2))
