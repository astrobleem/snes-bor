"""Real source-controller bootstrap to retained epoch 16, then exact retry.
Initial scene stays blank until epoch 16. No host snapshot/graphics/ref injection.
"""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_nonblank_component_native import sha,decode_vram,run_frames_exact
from m4_nonblank_batch_native import CONTROL,CONTROL_SHA,observer
from nonblank_batch_rescue import transform as batch
from batch_failure_fixture import transform as faults
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,exact_input_edge
import game_bor_startup_select as startup
from m4_live_ground_owner import REQUEST,SNAPSHOT
from m4_bounded_component_publisher import READY,DISPLAY_EPOCH
from compiler import Source
from m4_live_ground_component_native import scene_from_snapshot
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555


def transform(source):
    a=list(source);old=[' lda.l $7FFB96',' cmp #$B4B8',' bne NbCold',' jmp NbBegin']
    starts=[i for i in range(len(a)) if a[i:i+4]==old]
    if len(starts)!=1:raise ValueError('CAPACITY_DISPATCH_DRIFT')
    i=starts[0];a[i:i+4]=[' lda.l $7FBA90',' cmp #17',' bcc NbCold',' jmp NbBegin']
    i=a.index('OnlineVblank:');j=a.index(' lda #15',i)
    a[j:j]=[' rep #$20','.a16',' lda.l $7FBA90',' cmp #16',' bcs CapacityBootVisible',' jmp CapacityBootReturn','CapacityBootVisible:','.a16','.i16',' sep #$20','.a8']
    j=a.index(' rep #$20',a.index(' lda #15',i));a[j:j]=['CapacityBootReturn:']
    return a


def audit(rom,native):
    base=(CONTROL/'bor.sfc').read_bytes();assert sha(base)==CONTROL_SHA
    wanted=transform(faults(batch((CONTROL/'publisher.pasm').read_text().splitlines())))
    if (native/'publisher.pasm').read_text().splitlines()!=wanted:raise ValueError('CAPACITY_SOURCE_AUDIT')
    sy=symbols(native/'publisher.sym');from m4_rect_map_audit import statements;statements(wanted,sy)
    if sy['NbCodeEnd']>=0x39c000:raise ValueError('CAPACITY_CODE_OVERLAP')
    compiled=(native/'publisher.bin').read_bytes();expected=bytearray(base)
    for begin,end in ((0x398000,0x39a000),(0x39a000,sy['NbCodeEnd'])):expected[offset(begin):offset(end)]=compiled[offset(begin):offset(end)]
    if expected!=rom:raise ValueError('CAPACITY_UNRELATED_ROM_MUTATION')
    return dict(status='PASS',source_owned_boot_epochs=list(range(17)),cold_screen_held_blank=True,kernels_assets_and_other_banks_unchanged=True,host_graphics_player_refcount_injection=False)


def build(folder):
    n=folder/'native';n.mkdir(parents=True,exist_ok=True)
    a=transform(faults(batch((CONTROL/'publisher.pasm').read_text().splitlines())));(n/'publisher.pasm').write_text('\n'.join(a)+'\n')
    p=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(n/'publisher.pasm'),'--output',str(n/'publisher.bin'),'--symbols',str(n/'publisher.sym'),'--no-pansy'],capture_output=True,text=True)
    (n/'publisher-build.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise ValueError('CAPACITY_PUPPY')
    r=bytearray((CONTROL/'bor.sfc').read_bytes());r[57*32768:58*32768]=(n/'publisher.bin').read_bytes()[57*32768:58*32768].ljust(32768,b'\0');audit(r,n);(n/'bor.sfc').write_bytes(r)
    c=json.loads(Path('out/byor-motu-batch-rescue-v1/contract.json').read_text());sy=symbols(n/'publisher.sym');c['native_symbols']={k:v for k,v in sy.items() if k.startswith(('Nb','Online','Astra','Warm','Capacity'))};c['capacity_fixture']=True;(folder/'contract.json').write_text(json.dumps(c,indent=2)+'\n');shutil.copyfile(CONTROL/'callback_owner.lua',n/'callback_owner.lua')
    if not (n/'bor.msu').exists():os.link(CONTROL/'bor.msu',n/'bor.msu')


def run(folder):
    n=folder/'native';contract=json.loads((folder/'contract.json').read_text());script=n/'callback_owner.lua';observer(script,contract)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kw):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kw)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    sy=symbols(Path('src/main.sym'));source=Source(Path('Masters of the Universe [v.3.0 Build 4086].pak'));fields=[]
    with Observed(rom=n/'bor.sfc',mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=n/'mesen.log') as m:
        m.write_u16(READY,0);reporter=Reporter('CAPACITY-BOOT',kind='GATE')
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('CAPACITY_STARTUP')
        run_frames_exact(m,12)
        for key in ('StageWater_Enabled','StageWater_Pending','StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'):m.write_u8(sy[key],0)
        m.write_u16(0x7ffb84,0);m.write_u16(0x7ffb82,0)
        sequence=[0]+[m.BTN_RIGHT]*8+[0]+[m.BTN_UP]*4+[0]+[m.BTN_RIGHT]*2
        for epoch,buttons in enumerate(sequence):
            m.hold_input(buttons,port=0);run_frames_exact(m,2);m.write_u16(REQUEST,0xb4e7 if epoch==0 else 0xb4e8)
            for _ in range(100):
                run_frames_exact(m,1)
                if startup.u16(m,DISPLAY_EPOCH)==epoch and startup.u16(m,READY)==0xb4b8:break
            else:raise ValueError('CAPACITY_BOOT_TIMEOUT')
            run_frames_exact(m,2);raw=m.read_memory('SnesMemory',SNAPSHOT,146);(n/f'world-{epoch:02d}.bin').write_bytes(raw)
            if raw!=Path(f'out/byor-motu-rect-map-v1/native/world-{epoch:02d}.bin').read_bytes():raise ValueError('CAPACITY_SOURCE_BOOT_DRIFT')
        before_vram=m.read_memory('SnesVideoRam',0,65536);before_refs=m.read_memory('SnesMemory',0x42d000,1536);before_map=m.read_memory('SnesMemory',0x42c800,2048)
        for name,data in (('vram',before_vram),('refs',before_refs),('committed',before_map)):(n/f'before-{name}.bin').write_bytes(data)
        image,_=compose_rgb8(source,'DATA/LEVELS/GUILE2.TXT',scene_from_snapshot(raw,source));expected=rgb555(image).astype('<u2');(n/'expected.rgb555').write_bytes(expected.tobytes())
        def field(label):
            run_frames_exact(m,1);shot=m.tool('take_screenshot',{'format':'path'});dest=n/f'field-{len(fields):03d}.png';shutil.copyfile(shot['path'],dest)
            if not np.array_equal(rgb555(np.asarray(Image.open(dest).convert('RGB'))),expected):raise ValueError('CAPACITY_VISIBLE_PIXELS')
            state=m.get_ppu_state()
            if state['brightness']!=15 or state['forcedBlank']:raise ValueError('CAPACITY_BRIGHTNESS')
            v=m.read_memory('SnesVideoRam',0,65536)
            if v!=before_vram or decode_vram(v,m.read_memory('SnesCgRam',0,512)).astype('<u2').tobytes()!=expected.tobytes():raise ValueError('CAPACITY_VRAM_RETENTION')
            fields.append(dict(index=len(fields),label=label,frame=state['frameCount'],brightness=15,mismatches=0,sha256=sha(dest.read_bytes()),vram_sha256=sha(v)))
        field('scene16');m.hold_input(0,port=0);field('release-input');field('release-input');m.write_u16(REQUEST,0xb4e8)
        for _ in range(150):
            field('capacity-retry')
            if startup.u16(m,0x7ffb84)==1:break
        else:raise ValueError('CAPACITY_EXPECTED_SAFE_REJECTION')
        for _ in range(2):field('retained')
        after=m.read_memory('SnesMemory',SNAPSHOT,146);(n/'world-17.bin').write_bytes(after)
        if after!=Path('out/byor-motu-rect-map-v1/native/world-17.bin').read_bytes():raise ValueError('CAPACITY_SOURCE17')
        if m.read_memory('SnesMemory',0x42d000,1536)!=before_refs or m.read_memory('SnesMemory',0x42c800,2048)!=before_map or startup.u16(m,DISPLAY_EPOCH)!=16:raise ValueError('CAPACITY_COMMITTED_RETENTION')
        meta=m.read_memory('SnesMemory',0x42d600,128);(n/'metadata.bin').write_bytes(meta)
        if int.from_bytes(meta[0x60:0x62],'little') or int.from_bytes(meta[0x74:0x76],'little')!=1 or int.from_bytes(meta[6:8],'little')!=32:raise ValueError('CAPACITY_RETRY_QUEUE_GUARD')
    log=(n/'mesen.log').read_text(errors='replace');warm=[line for line in log.splitlines() if 'NB_PACKET|' in line and int(line.split('NB_PACKET|',1)[1].split('|')[3])==17]
    if warm or 'NB_FAULT|' in log:raise ValueError('CAPACITY_UNSAFE_TRANSFER')
    attempts=[line for line in log.splitlines() if 'NB_BATCH|' in line and '|NbBeginRetry|17|' in line]
    if len(attempts)!=2:raise ValueError('CAPACITY_TWO_ATTEMPTS')
    result=dict(classification='NATIVE_EXACT_RETRY_SAFE_RECORD_CAP_REJECTION',rom_sha256=sha((n/'bor.sfc').read_bytes()),candidate=str(n/'bor.sfc'),source_boot_snapshots_identical=17,source17_snapshot_identical=True,native_attempts=2,exact_retry_marker=1,restoration_record_guard=32,required_actual_exact_records=34,required_actual_exact_slots=122,free_tail=124,visible_fields=len(fields),verified_pixels=len(fields)*57344,pixel_mismatches=0,no_dma_after_boot=True,committed_refs_maps_and_vram_unchanged=True,queue_empty=True,fields=fields,audit=audit((n/'bor.sfc').read_bytes(),n))
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['classification'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--run-existing',action='store_true');a=p.parse_args();folder=a.output.resolve()
    if not a.run_existing:build(folder)
    run(folder)
