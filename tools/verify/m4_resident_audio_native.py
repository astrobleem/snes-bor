"""Bounded resident TAD voice regression; queue inputs are instrumented."""
import argparse,hashlib,json
from pathlib import Path
from _harness import McpSession,MESEN_EXE,Reporter,_free_tcp_port,run_frames_exact
from actor_s5_entity_fixture import symbols
import game_bor_startup_select as startup


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();a.rom=a.rom.resolve();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    sy=symbols(Path('src/main.sym'));rows=[];r=Reporter('M4-SPC-RESIDENT-VOICES',kind='GATE')
    with McpSession(rom=a.rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log')as m:
        startup.cold_to_title(m,r);observed=set()
        # Distinct effects exercise both channels. Repeating the same effect
        # intentionally reuses a channel under TAD's one-channel-per-ID policy.
        for request,name in enumerate(['SFX_JUMP_ID','SFX_MONEY_ID']):
            effect=sy[name]
            m.write_memory('SnesMemory',0x7e0000+sy['Tad_sfxQueue_sfx'],f'{effect:02x}')
            target=7-request
            for field in range(32):
                run_frames_exact(m,1);state=m.get_audio_state();voices={v['voice']:v for v in state['voices']}
                rows.append(dict(request=request,effect_id=effect,field=field,voices=[voices[6],voices[7]],voice0=voices[0]))
                if voices[target]['envelope']>0:observed.add(target);break
        r.check('resident effects execute on physical voices7 and6',observed=={6,7})
        r.check('both ordinary SFX voices overlap',any(all(v['envelope']>0 for v in row['voices'])for row in rows))
        r.check('resident queue does not claim reserved stream voice0',all(row['voice0']['envelope']==0 for row in rows))
    result=dict(status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),
        checks=r.results,queue_input_instrumented=True,observations=rows,authored_gameplay_event_proven=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
