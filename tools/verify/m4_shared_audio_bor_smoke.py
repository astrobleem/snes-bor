"""Focused original BOR cold selector / first-stage static source smoke."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from actor_s5_entity_fixture import symbols
from _harness import McpSession,MESEN_EXE,Reporter,_free_tcp_port,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.rom=a.rom.resolve();a.output=a.output.resolve()
    a.output.mkdir(parents=True,exist_ok=True)
    sy=symbols(Path('src/main.sym'));r=Reporter('M4-SHARED-AUDIO-BOR-SMOKE',kind='GATE')
    observations=[]
    with McpSession(rom=a.rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        startup.cold_to_title(m,r);startup.title_to_charselect(m)
        entries=startup.normal_player_entries('bor-original')
        ordinal,runtime=next((i,index)for i,(index,entry)in enumerate(entries)if startup.entry_name(entry).upper()=='KULA')
        for _ in range(ordinal):exact_input_edge(m,m.BTN_RIGHT,1,port=0)
        exact_input_edge(m,m.BTN_START,1,port=0)
        assert startup.wait_state(m,startup.PLAYING,300)
        selected=startup.u8(m,sy['BorSet_Selected'])
        expected_campaign=m.read_memory('SnesMemory',sy['BorSet_CampaignMap']+selected,32)[0]
        r.check('source KULA selection and generated selected-set campaign entry zero',startup.u8(m,startup.P1+startup.CHAR_ROSTER_INDEX)==runtime and startup.u8(m,startup.CAMPAIGN_ID)==expected_campaign and startup.u8(m,startup.CAMPAIGN_ORDINAL)==0)
        for field in range(480):
            run_frames_exact(m,1)
            trace=m.read_memory('SnesMemory',sy['SourceVisual_DebugTrace'],48)
            observations.append(dict(field=field,state=startup.u16(m,startup.STATE),
                source_calls=startup.u16(m,sy['SourceVisual_CallCount']),
                source_error=startup.u8(m,sy['SourceVisual_DebugLastError']),
                actor_errors=[int.from_bytes(trace[i+6:i+8],'little')for i in range(0,48,8)],
                committed_nmi=startup.u16(m,sy['Nmi_FrameCounter']),
                stream_active=startup.u8(m,sy['AudioSemantic_FootDieStreamActive'])))
            if field>=143:
                probe=m.read_memory('snesSpriteRam',0,544)
                if any(probe[i*4+1]!=0xe0 for i in range(128)):break
        oam=m.read_memory('snesSpriteRam',0,544)
        visible=sum(oam[i*4+1]!=0xe0 for i in range(128))
        r.check('first stage remains PLAYING through bounded native observation',len(observations)>=144 and all(o['state']==startup.PLAYING for o in observations))
        # $27 is the existing owned-DMA/palette/block busy retry, explicitly
        # admitted by actor_s7_production_runtime's source visual smoke.
        r.check('ordinary static source presentation becomes visible with no hard source admission errors',visible>0 and observations[-1]['source_calls']>observations[0]['source_calls'] and all(o['source_error']in(0,39) and all(v in(0,39)for v in o['actor_errors'])for o in observations))
        r.check('idle stream remains unclaimed',all(o['stream_active']==0 for o in observations))
        shot=m.take_screenshot()
        shutil.copyfile(shot['path'],a.output/'first-stage.png')
        (a.output/'wram-final.bin').write_bytes(m.read_memory('SnesMemory',0x7e0000,65536))
    result=dict(schema='BYOR_SHARED_AUDIO_BOR_SMOKE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',
        rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),checks=r.results,
        observations=observations,player='KULA',selected_set=selected,campaign_id=expected_campaign,
        visible_oam_entries=visible,busy_retry_observations=sum(o['source_error']==39 for o in observations),source_presentation='existing static OBJ',
        full_campaign_regression_run=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
