"""Two sequential generic ASAD streams in one native DSP/ARAM session."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture,REQUEST,INDEX,ERROR
from _harness import Reporter,run_frames_exact
from m4_projectile_audio_fixture import configure
from m4_source_audio_rom_native import ASM
from m4_source_audio_native_verify import verify
from m4_input_controller_native import offset


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['rom','assets','packed','output']:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--sound-index',type=int,default=16);a=p.parse_args()
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    phases=[a.output/'first',a.output/'restart']
    for f in phases:f.mkdir(exist_ok=True)
    source=next(r for r in json.loads((a.assets/'report.json').read_text())['compiled']if r['sound_index']==a.sound_index)['source_path']
    configurations=[configure(f,a.assets.resolve(),source,isolate=True,prefill=True,generic_rom=a.packed.resolve())for f in phases]
    row,audio_transform,audio_before,audio_closeout=configurations[0]
    def transform(raw,sy):
        audio_transform(raw,sy)
        at=offset(sy['Core_Nmi_WaitFrame']);assert raw[at:at+4]==b'\x5c'+sy['Tad_StreamWaitFrame'].to_bytes(3,'little')
        raw[at+1:at+4]=sy['SourceAudioAssetWait'].to_bytes(3,'little')
    def before(m,sy):
        audio_before(m,sy)
        m.write_u16(REQUEST+6,0)
        for n in ['SourceVMRun4086_Ready','SourceVMRun4086_Busy','VmSourceFrame_Pending']:m.write_u16(sy[n],0)
        m.write_u16(sy['Game_State'],3)
    r=Reporter('M4-ASAD-NATIVE-LIFECYCLE',kind='GATE');endpoints=[]
    def endpoint(m,sy):
        return dict(status=int.from_bytes(m.read_memory('SnesMemory',sy['SourceAudio_Status'],2),'little'),active=m.read_memory('SnesMemory',sy['AudioSemantic_FootDieStreamActive'],1)[0],seen=m.read_memory('SnesMemory',sy['SourceAudio_EnvelopeSeen'],1)[0],env=m.read_memory('SnesMemory',0x2142,1)[0],requests=int.from_bytes(m.read_memory('SnesMemory',sy['AudioSemantic_StreamRequestCount'],2),'little'))
    def closeout(m,sy,completed):
        audio_closeout(m,sy,completed)
        first=endpoint(m,sy);endpoints.append(first)
        r.check('first source releases admission after observed DSP END',first['status']==4 and first['active']==0 and first['seen']>0 and first['env']==0)
        if not r.results[-1][1]:return
        # No reset, loader transfer, directory restoration, or voice preemption.
        configurations[1][2](m,sy)
        m.write_u16(INDEX,0);m.write_u16(ERROR,0);m.write_u16(REQUEST,0xb4ad)
        for _ in range(200):
            run_frames_exact(m,1)
            if int.from_bytes(m.read_memory('SnesMemory',INDEX,2),'little')==1 or int.from_bytes(m.read_memory('SnesMemory',ERROR,2),'little'):break
        accepted=int.from_bytes(m.read_memory('SnesMemory',INDEX,2),'little')==1 and int.from_bytes(m.read_memory('SnesMemory',ERROR,2),'little')==0
        r.check('second request admitted by unchanged foreground fixture',accepted)
        configurations[1][3](m,sy,accepted)
        second=endpoint(m,sy);endpoints.append(second)
        r.check('restart reaches actual DSP END and releases admission',second['status']==4 and second['active']==0 and second['seen']>0 and second['env']==0 and second['requests']==first['requests']+1)
    env={'MESEN_VOICE_CAPTURE_PATH':str(a.output/'voice0.raw'),'MESEN_VOICE_CAPTURE_VOICE':'0','MESEN_VOICE_CAPTURE_ARM_FILE':str(phases[0]/'voice0.raw.arm')}
    raw,log=run_fixture(a.rom,a.output,[dict(sound_index=a.sound_index)],'SourceAudioAssetFixture','SourceAudio_Status',0xb4ad,[], '',r,
        append=ASM.replace('ASSETINDEX',str(a.sound_index)).replace('OTHERINDEX',str(0 if a.sound_index else 16)),
        bindings={'STARTSOURCE':'SourceAudio_Start','REALWAIT':'Tad_StreamWaitFrame','SOURCESTATUS':'SourceAudio_Status','SOURCEINDEX':'SourceAudio_Index'},batch_size=1,frame_limit=200,
        rom_transform=transform,before_start=before,closeout=closeout,emulator_env=env)
    proofs=[]
    if len(endpoints)==2:
        metadata=json.loads((a.output/'voice0.raw.json').read_text());cut=metadata['kon_sample'];total=metadata['sample_count']
        assert 0<cut<total and metadata['endx_sample']==total and metadata['koff_sample']is None
        capture=(a.output/'voice0.raw').read_bytes();lines=(a.output/'voice0.raw.trace').read_text().splitlines()
        assert len(lines)==total and len(capture)==total*4
        for f,start,end in [(phases[0],0,cut),(phases[1],cut,total)]:
            (f/'voice0.raw').write_bytes(capture[start*4:end*4])
            (f/'voice0.raw.trace').write_text(''.join(str(i)+','+line.split(',',1)[1]+'\n'for i,line in enumerate(lines[start:end])))
            (f/'voice0.raw.json').write_text(json.dumps(dict(voice=0,sample_rate=32000,sample_count=end-start,kon_sample=0,koff_sample=None,endx_sample=end-start))+'\n')
            proofs.append(verify(f,a.assets.resolve(),require_dsp_trace=True))
        r.check('both DSP traversals match every source BRR block',all(p['status']=='PASS'for p in proofs))
    result=dict(schema='BYOR_ASAD_NATIVE_LIFECYCLE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',checks=r.results,endpoints=endpoints,proofs=proofs,rom_sha256=hashlib.sha256(raw).hexdigest(),no_emulator_reset_between_streams=True,no_directory_restoration=True,no_color_reduction=True,authored_polyphony_proven=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
