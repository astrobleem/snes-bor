"""Bounded real Stage_Load queue copy proof; no stage gameplay sweep."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sys.path[:0]=[str(HERE),str(ROOT)]
from _harness import open_session, Reporter, pasm_constant_in, poll_until
import game_bor_startup_select as startup
import build_rom


def state_constant(name): return pasm_constant_in('src/core/game_state.pasm',name)


def summarize(path):
    raw=Path(path).read_bytes();report=json.loads(raw)
    result=dict(mode=report['mode'],rom_sha256=report['rom_sha256'],trace_sha256=hashlib.sha256(raw).hexdigest(),rows=[])
    for row in report['rows']:
        cfg=next(c for c in build_rom.STAGE_CONFIGS if c['source_level'].upper()==row['source'])
        blob=(ROOT/cfg['spawn']).read_bytes()
        assert hashlib.sha256(blob).hexdigest()==row['expected_sha256']
        writes=[e['params'] for e in row['events'] if e.get('params',{}).get('kind')=='Write']
        start=next(i for i,e in enumerate(writes) if e['address']==row['queue_base'])
        copy=writes[start:start+len(blob)]
        assert len(copy)==len(blob) and all(e['address']==row['queue_base']+i and e['value']==blob[i] for i,e in enumerate(copy))
        compact={k:v for k,v in row.items() if k!='events'}
        compact.update(exact_copy_trace=True,copy_write_count=len(copy),copy_first_frame=copy[0]['frame'],copy_last_frame=copy[-1]['frame'])
        if report['mode']=='after': assert compact['guard_intact'] and compact['loaded_sha256']==compact['expected_sha256']
        result['rows'].append(compact)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--before',action='store_true')
    p.add_argument('--summarize',nargs='+',type=Path,help='validate existing full traces and emit compact evidence without rerunning')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.summarize:
        evidence=dict(runs=[summarize(path) for path in args.summarize],
            msu_sha256=hashlib.sha256((ROOT/'distribution/bor.msu').read_bytes()).hexdigest())
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(evidence,indent=2)+'\n')
        print('full copy traces validated; compact evidence written');return
    if args.before: base,capacity,size=0x7E550F,90,10
    else:
        abi=json.loads((ROOT/'src/generated/queue_abi.json').read_text())
        base,capacity,size=abi['buffer_base'],abi['capacity'],abi['record_size']
    guard=base+capacity*size
    r=Reporter('G15-S3-QUEUE',kind='GATE');rows=[]
    with open_session(__file__) as m:
        startup.cold_to_title(m,r);startup.select_case(m,r,'KULA');m.run_frames(10)
        for source,previous in ((r'DATA\EASY\6AEASY.TXT',10),(r'DATA\EASY\1BEASY.TXT',0)):
            if args.before and previous==0: continue
            physical,cfg=next((i,c) for i,c in enumerate(build_rom.STAGE_CONFIGS) if c['source_level'].upper()==source)
            blob=(ROOT/cfg['spawn']).read_bytes()
            m.pause()
            marker=bytes(range(0xA0,0xC0))
            m.write_hex(guard,marker.hex())
            before=m.read_memory('snesMemory',guard,32)
            hook=m.add_write_hook(base,guard+31)
            m.drain_notifications()
            m.write_u8(state_constant('Game_CampaignId'),startup.BOR)
            m.write_u8(state_constant('Game_CampaignOrdinal'),previous)
            m.write_u8(state_constant('Stage_LoadPending'),1)
            m.write_u16(state_constant('Game_State'),state_constant('GAME_STATE_STAGECLEAR'))
            reached=poll_until(m,lambda s:s.read_u16(state_constant('Game_StageIndex'))==physical and
                s.read_u16(state_constant('Game_State'))==state_constant('GAME_STATE_PLAYING'),max_frames=900,step=1)
            m.pause();m.remove_hook(hook)
            events=m.drain_notifications()
            writes=[e['params'] for e in events if e.get('method')=='notifications/mesen/hookFired'
                    and e.get('params',{}).get('kind')=='Write']
            start=next((i for i,e in enumerate(writes) if e['address']==base),None)
            copy=writes[start:start+len(blob)] if start is not None else []
            exact_copy=len(copy)==len(blob) and all(e['address']==base+i and e['value']==blob[i] for i,e in enumerate(copy))
            loaded=m.read_memory('snesMemory',base,max(32,len(blob)))
            after=m.read_memory('snesMemory',guard,32)
            row=dict(source=source,physical=physical,queue_base=base,capacity=capacity,guard=guard,
                count=m.read_memory('snesMemory',0x7E5500,32)[1],
                copy_bytes=int.from_bytes(m.read_memory('snesMemory',0x7E5500,32)[2:4],'little'),
                before=before.hex(),after=after.hex(),guard_intact=before==after,
                expected_sha256=hashlib.sha256(blob).hexdigest(),loaded_sha256=hashlib.sha256(loaded).hexdigest(),
                expected_overflow=blob[capacity*size:].hex(),reached_playing=reached,exact_copy_trace=exact_copy,events=events)
            rows.append(row)
            r.check('real Stage_Load reaches requested stage',reached)
            r.check('stage count and copy bytes are exact',row['count']==len(blob)//size and row['copy_bytes']==len(blob))
            r.check('write trace covers every byte in order',exact_copy)
            if args.before: r.check('old allocation sentinel changes',before!=after)
            else:
                r.check('all packed records copied byte-for-byte',loaded==blob)
                r.check('post-buffer sentinel intact',before==after)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(dict(rom_sha256=hashlib.sha256((ROOT/'distribution/bor.sfc').read_bytes()).hexdigest(),
        mode='before' if args.before else 'after',rows=rows),indent=2)+'\n')
    r.finish()


if __name__=='__main__': main()
