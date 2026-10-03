"""Bounded organic spawn proof for signed bases and extended palette maps."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(HERE), str(ROOT)]
from _harness import open_session, Reporter, pasm_constant_in, pasm_constant, poll_until
import game_bor_startup_select as startup
import build_rom


def c(name):
    return pasm_constant_in('src/core/game_state.pasm', name)


def snapshot(m):
    stride = pasm_constant('CHAR_ZP_LEN')
    actors = m.read_memory('snesMemory', 0x7E0A00, stride * 6)
    meta = m.read_memory('snesMemory', 0x7E550F, stride * 6)
    rows = []
    for slot in range(6):
        a = actors[slot*stride:(slot+1)*stride]
        b = meta[slot*stride:(slot+1)*stride]
        rows.append(dict(slot=slot, model=a[12], selected=a[11], driver=a[15],
                         palette=a[13], tile_column=a[14], y=a[6], map=a[52], hp=a[35],
                         z=int.from_bytes(a[67:69], 'little', signed=True),
                         base=int.from_bytes(b[:4], 'little', signed=True),
                         alias=int.from_bytes(b[4:6], 'little')))
    return dict(actors=rows, camera=m.read_memory('snesMemory', 0x7E1600, 32).hex(),
                queue=m.read_memory('snesMemory', 0x7E5500, 32)[0])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--case', choices=['positive','negative'])
    p.add_argument('--summarize',type=Path,help='compact a completed trace without rerunning the emulator')
    args = p.parse_args()
    if args.summarize:
        raw=args.summarize.read_bytes();trace=json.loads(raw)
        if not trace.get('passed'): raise ValueError('cannot summarize a failed/partial gate as acceptance')
        for name in ('rom','msu'):
            suffix='sfc' if name=='rom' else 'msu'
            if trace[name+'_sha256']!=hashlib.sha256((ROOT/f'distribution/bor.{suffix}').read_bytes()).hexdigest():
                raise ValueError('stale runtime trace')
        compact={k:v for k,v in trace.items() if k!='runs'}
        compact['full_trace_sha256']=hashlib.sha256(raw).hexdigest()
        compact['runs']=[]
        for row in trace['runs']:
            r={k:v for k,v in row.items() if k not in ('samples','metadata_writes','metadata_nonzero','scratch','stage_state')}
            r['sample_count']=len(row['samples'])
            r['metadata_write_count']=len(row['metadata_writes'])
            compact['runs'].append(r)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(compact,indent=2)+'\n')
        print('completed trace and artifact hashes validated');return
    r = Reporter('G15-S4-ENVIRONMENT', kind='GATE')
    evidence = dict(rom_sha256=hashlib.sha256((ROOT/'distribution/bor.sfc').read_bytes()).hexdigest(),
                    msu_sha256=hashlib.sha256((ROOT/'distribution/bor.msu').read_bytes()).hexdigest(), runs=[])
    names = [Path(x).name for x in build_rom.ROSTER_PREFIXES]
    steamer, steam, angel = [names.index(n) for n in ('steamer', 'steam', 'angel')]
    completed=False
    try:
        with open_session(__file__) as m:
            startup.cold_to_title(m, r)
            startup.select_case(m, r, 'KULA')
            for source, previous, value in ((r'DATA\EASY\3CEASY.TXT', 5, 49),
                                             (r'DATA\EASY\5BEASY.TXT', 9, -5)):
                if args.case=='positive' and value<0 or args.case=='negative' and value>0: continue
                physical = next(i for i, cfg in enumerate(build_rom.STAGE_CONFIGS)
                                if cfg['source_level'].upper() == source)
                # Direct-load fixture hygiene: a previous stage's emitter must
                # not remain a live subject in the next case. Do not seed any
                # map, base, selected state, Z, or queue index for new subjects.
                m.pause()
                for slot in range(1,6):
                    entity=0x7E0A00+slot*pasm_constant('CHAR_ZP_LEN')
                    m.write_u8(entity+pasm_constant('CHAR_HP'),0)
                    m.write_u8(entity+pasm_constant('CHAR_INPUT_DRIVEN'),0)
                m.write_u8(c('Game_CampaignId'), startup.BOR)
                m.write_u8(c('Game_CampaignOrdinal'), previous)
                m.write_u8(c('Stage_LoadPending'), 1)
                m.write_u16(c('Game_State'), c('GAME_STATE_STAGECLEAR'))
                reached = poll_until(m, lambda s: s.read_u16(c('Game_StageIndex')) == physical and
                                     s.read_u16(c('Game_State')) == c('GAME_STATE_PLAYING'),
                                     max_frames=900, step=1)
                r.check('normal Stage_Load reaches ' + source, reached)
                trace = m.add_write_hook(0x7E550F,0x7E5833)
                m.drain_notifications()
                row = dict(source=source, physical=physical, samples=[],
                           hygiene='prior NPC HP/driver neutralized before direct Stage_Load; no new subject state seeded')
                evidence['runs'].append(row)
                palette = json.loads((ROOT/'out/angel_moveset.json').read_text())['remap_palettes'][3]
                expected_palette = b''.join(int(x).to_bytes(2, 'little') for x in palette)
                for frame in range(180):
                    sample = snapshot(m)
                    sample['relative_frame'] = frame
                    row['samples'].append(sample)
                    expected_base=round(value*4*65536/5)
                    for a in sample['actors']:
                        if a['model']==steamer and a['driver']==5 and a['hp'] and a['base']==expected_base:
                            oam=m.read_memory('snesSpriteRam',0,544)
                            expected_y=(a['y']-(expected_base>>16))&255
                            matches=[i//4 for i in range(0,512,4) if (oam[i+3]>>1)&7==a['palette']
                                     and oam[i+2]==a['tile_column']*4 and oam[i+1]==expected_y]
                            if matches: row['oam_base_proof']=dict(frame=frame,depth=a['y'],base=expected_base,
                                                                y=expected_y,sprites=matches)
                    if value<0 and sample['queue']>3:
                        for a in sample['actors']:
                            if a['model']==angel and a['hp'] and a['map']==4:
                                actual=m.read_memory('snesCgRam',0x100+a['palette']*32,32)
                                if actual==expected_palette:
                                    row['palette_proof']=dict(frame=frame,slot=a['slot'],map=a['map'],
                                                             actual=actual.hex(),expected=expected_palette.hex())
                    if value < 0:
                        m.set_input(m.BTN_RIGHT, frames=1)
                    else:
                        m.run_frames(1)
                parents = [a for s in row['samples'] if s['queue']>=(2 if value>0 else 3)
                           for a in s['actors'] if a['model'] == steamer and a['driver'] == 5 and a['hp']]
                children = [a for s in row['samples'] for a in s['actors'] if a['model'] == steam and a['driver'] == 6 and a['hp']]
                expected = round(value * 4 * 65536 / 5)
                r.check('organic fixed-base emitter exists', bool(parents))
                r.check('signed source altitude preserved', bool(parents) and all(a['base'] == expected for a in parents))
                r.check('fixed base never becomes jump/throw Z', bool(parents) and all(a['selected'] not in (5,6) and a['z'] == 0 for a in parents))
                r.check('fixed base reaches hardware OAM Y', 'oam_base_proof' in row)
                initialized=[a for a in children if expected<=a['base']<=expected+2*0x15555]
                r.check('organic child inherits and rises from base', bool(initialized) and any(a['base']>expected for a in children))
                r.check('child base does not become jump/throw state', bool(initialized) and all(a['z']==0 and a['selected'] not in (5,6) for a in initialized))
                row['expected_base_q16_16'] = expected
                m.remove_hook(trace)
                row['metadata_writes'] = m.drain_notifications()
                row['emulator'] = m.get_state()
                row['metadata_nonzero'] = [(i,b) for i,b in enumerate(m.read_memory('snesMemory',0x7E550F,798)) if b]
                row['scratch'] = m.read_memory('snesMemory',0x7E5893,64).hex()
                row['stage_state'] = m.read_memory('snesMemory',c('Game_StageIndex'),32).hex()
                if value < 0:
                    maps = [a for s in row['samples'] for a in s['actors'] if a['model'] == angel and a['hp'] and a['map'] == 4]
                    r.check('organic Angel receives authored map 4', bool(maps))
                    r.check('map 4 emitted palette reaches CGRAM', 'palette_proof' in row)
            completed=True
    finally:
        evidence['checks'] = r.results
        evidence['passed'] = completed and args.case is None and bool(r.results) and all(ok for _,ok in r.results)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, indent=2)+'\n')
    r.finish()


if __name__ == '__main__':
    main()
