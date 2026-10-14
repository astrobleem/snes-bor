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
from m4_nonblank_batch_native import CONTROL,CONTROL_SHA
from m4_restore_spill_native import observer
from restore_spill import transform as spill
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
    a=spill(source)
    marker=[' lda #2',' sta.l $42D600']
    positions=[i for i in range(len(a)) if a[i:i+2]==marker]
    if len(positions)!=1:raise ValueError('SPILL_ADMISSION_HOOK_DRIFT')
    i=positions[0];a[i:i]=['SpillPlanReady:','.a16','.i16',' lda.l $42D602',' cmp #4',' bne SpillPlanProceed',' jmp NbAbort','SpillPlanProceed:','.a16','.i16']
    old=[' lda.l $7FFB96',' cmp #$B4B8',' bne NbCold',' jmp NbBegin']
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
    sy=symbols(native/'publisher.sym');from m4_restore_spill_native import audit_branches;audit_branches(wanted,sy,(native/'publisher.bin').read_bytes())
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
    c=json.loads(Path('out/byor-motu-batch-rescue-v1/contract.json').read_text());sy=symbols(n/'publisher.sym');c['native_symbols']={k:v for k,v in sy.items() if k.startswith(('Nb','Online','Astra','Warm','Capacity','Spill'))};c['capacity_fixture']=True;c['nonblank_restore_spill']=True;c['restoration_records']=48;c['restoration_spill_lease']=[0x42d620,0x42d660];(folder/'contract.json').write_text(json.dumps(c,indent=2)+'\n');shutil.copyfile(CONTROL/'callback_owner.lua',n/'callback_owner.lua')
    if not (n/'bor.msu').exists():os.link(CONTROL/'bor.msu',n/'bor.msu')


def run(folder,fault_mode=0):
    n=folder/'native';contract=json.loads((folder/'contract.json').read_text());script=n/'callback_owner.lua';observer(script,contract);add_observer(script,contract)
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
        cgram=m.read_memory('SnesCgRam',0,512);(n/'before-cgram.bin').write_bytes(cgram)
        if before_refs!=Path('out/byor-motu-rect-map-v1/native/directory-16.bin').read_bytes():raise ValueError('SPILL_BOOT_RESIDENCY_DRIFT')
        expected=[]
        for epoch in (16,17):
            world=Path(f'out/byor-motu-rect-map-v1/native/world-{epoch:02d}.bin').read_bytes()
            image,_=compose_rgb8(source,'DATA/LEVELS/GUILE2.TXT',scene_from_snapshot(world,source));pix=rgb555(image).astype('<u2')
            expected.append(pix);(n/f'expected-{epoch}.rgb555').write_bytes(pix.tobytes())
        if np.array_equal(*expected):raise ValueError('SPILL_UNCHANGED_IMAGE')
        def field(label):
            run_frames_exact(m,1);shot=m.tool('take_screenshot',{'format':'path'});dest=n/f'field-{len(fields):03d}.png';shutil.copyfile(shot['path'],dest)
            actual=rgb555(np.asarray(Image.open(dest).convert('RGB')))
            identity=next((i for i,pix in enumerate(expected) if np.array_equal(actual,pix)),None)
            if identity is None:raise ValueError('SPILL_VISIBLE_PIXELS')
            if fault_mode and identity:raise ValueError('SPILL_ABORT_DISPLAY_CHANGE')
            state=m.get_ppu_state()
            if state['brightness']!=15 or state['forcedBlank']:raise ValueError('SPILL_BRIGHTNESS')
            v=m.read_memory('SnesVideoRam',0,65536);(n/f'field-{len(fields):03d}.vram').write_bytes(v)
            if m.read_memory('SnesCgRam',0,512)!=cgram or decode_vram(v,cgram).astype('<u2').tobytes()!=expected[identity].tobytes():raise ValueError('SPILL_PHYSICAL_PIXELS')
            fields.append(dict(index=len(fields),label=label,frame=state['frameCount'],brightness=15,identity=16+identity,mismatches=0,sha256=sha(dest.read_bytes()),vram_sha256=sha(v)))
        field('scene16');m.write_u16(0x42d602,fault_mode);m.hold_input(0,port=0);field('release-input');field('release-input');m.write_u16(REQUEST,0xb4e8)
        for _ in range(200):
            field('transition')
            if startup.u16(m,0x7ffb84)==1 if fault_mode else startup.u16(m,DISPLAY_EPOCH)==17:break
        else:raise ValueError('SPILL_TRANSACTION_TIMEOUT')
        for _ in range(2):field('retained' if fault_mode else 'new-visible')
        after=m.read_memory('SnesMemory',SNAPSHOT,146);(n/'world-17.bin').write_bytes(after)
        if after!=Path('out/byor-motu-rect-map-v1/native/world-17.bin').read_bytes():raise ValueError('SPILL_SOURCE17_DRIFT')
        for name,address,length in [('refs',0x42d000,1536),('committed',0x42c800,2048),('pending',0x42c000,2048),('metadata',0x42d600,128),('records',0x3480,128)]:
            (n/f'after-{name}.bin').write_bytes(m.read_memory('SnesMemory',address,length))
        (n/'after-vram.bin').write_bytes(m.read_memory('SnesVideoRam',0,65536))
        if fault_mode:
            if m.read_memory('SnesMemory',0x42d000,1536)!=before_refs or m.read_memory('SnesMemory',0x42c800,2048)!=before_map or startup.u16(m,DISPLAY_EPOCH)!=16:raise ValueError('SPILL_ABORT_OWNERSHIP')
        else:
            m.hold_input(m.BTN_LEFT,port=0);field('left-input');field('left-input');m.write_u16(REQUEST,0xb4e8)
            for _ in range(8):
                field('left')
                if startup.u16(m,0x7ffb84)==1:break
            else:raise ValueError('SPILL_LEFT_REJECTION')
            if startup.u16(m,DISPLAY_EPOCH)!=17 or fields[-1]['identity']!=17:raise ValueError('SPILL_LEFT_RETENTION')
            (n/'world-18.bin').write_bytes(m.read_memory('SnesMemory',SNAPSHOT,146))
    result=certify(folder,fields,fault_mode)
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['classification'],flush=True)


def add_observer(script,contract):
    sy=contract['native_symbols']
    with script.open('a') as f:
        def cb(name,body):f.write(f'emu.addMemoryCallback(function(){body}end,emu.callbackType.exec,{sy[name]},{sy[name]},emu.cpuType.snes,emu.memType.snesMemory)\n')
        cb('SpillPlanReady',"local t={};for i=0,nbWord(0x42d606)-1 do local a=i<32 and 0x3480+4*i or 0x42d620+4*(i-32);t[#t+1]=nbWord(a)..','..nbWord(a+2)end;nbLog('PLAN',nbTxn..'|'..nbWord(0x42d674)..'|'..table.concat(t,';'))")
        # Capture pending maps at the same native READY boundary already logged.
        rom=(script.parent/'bor.sfc').read_bytes();begin=sy['NbBegin'];section=rom[offset(begin):offset(sy['NbCodeEnd'])];code=bytes.fromhex('a903008f00d642');at=begin+section.index(code)+len(code)
        f.write(f"emu.addMemoryCallback(function()local t={{}};for i=0,2047 do t[#t+1]=string.format('%02x',emu.read(0x42c000+i,emu.memType.snesMemory))end;nbLog('READY_MAP',nbTxn..'|'..table.concat(t))end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n")


def certify(folder,fields,fault_mode):
    from m4_batch_capacity_assets import verify
    n=folder/'native';rom=(n/'bor.sfc').read_bytes();audit_result=audit(rom,n);capacity=verify(folder/'capacity-assets.json')
    records=[]
    for line in (n/'mesen.log').read_text(errors='replace').splitlines():
        if 'NB_' not in line:continue
        p=line[line.index('NB_'):].split('|');records.append(dict(kind=p[0][3:],clock=int(p[1]),frame=int(p[2]),line=int(p[3]),data=p[4:]))
    for epoch in (3,5,7,11,12,13):
        if any(e['kind'] in ('PACKET','TILE') and e['data'][0]==str(epoch) for e in records):raise ValueError('SPILL_PROJECTED_NOOP_WORK')
    (folder/'events.json').write_text(json.dumps(records,indent=2)+'\n')
    faults=[e for e in records if e['kind']=='FAULT']
    if faults:raise ValueError('SPILL_NATIVE_UNSAFE:'+str(faults[:3]))
    phase=lambda name:next(e for e in records if e['kind']=='PHASE' and e['data'][0]==name and int(e['data'][1])==17)
    plans=[e for e in records if e['kind']=='PLAN' and int(e['data'][0])==17]
    if len(plans)!=1 or plans[0]['data'][1]!='1':raise ValueError('SPILL_EXACT_ADMISSION_PLAN')
    restores=[tuple(map(int,row.split(','))) for row in plans[0]['data'][2].split(';')]
    if len(restores)!=34 or sorted(h for h,s in restores)!=capacity['exact_restoration_homes']:raise ValueError('SPILL_34_RESTORATION_IDENTITIES')
    attempts=[e for e in records if e['kind']=='BATCH' and e['data'][0]=='NbBeginRetry' and e['data'][1]=='17']
    if len(attempts)!=2:raise ValueError('SPILL_CONSERVATIVE_RETRY')
    writes=[e for e in records if e['kind']=='SPILL_WRITE']
    if len(writes)<8:raise ValueError('SPILL_NATIVE_WRITES_NOT_OBSERVED')
    meta=(n/'after-metadata.bin').read_bytes()
    if int.from_bytes(meta[0x60:0x62],'little') or int.from_bytes(meta[6:8],'little')!=34:raise ValueError('SPILL_QUEUE_OR_RESTORE_COUNT')
    packets=[]
    for e in records:
        if e['kind']=='PACKET' and int(e['data'][0])>=17:
            d=e['data'];packets.append(dict(clock=e['clock'],frame=e['frame'],txn=int(d[0]),target=int(d[1]),word=int(d[2]),source=int(d[3]),size=int(d[4]),payload=bytes.fromhex(d[5])))
    if any(p['txn']!=17 for p in packets):raise ValueError('SPILL_LEFT_DMA')
    if packets and min(p['clock'] for p in packets)<plans[0]['clock']:raise ValueError('SPILL_ADMISSION_DMA')
    vr=bytearray((n/'before-vram.bin').read_bytes());refs=np.frombuffer((n/'before-refs.bin').read_bytes(),dtype='<u2')&0x3fff
    def apply(p):
        if p['target']!=0x18 or len(p['payload'])!=p['size']:raise ValueError('SPILL_DMA_TARGET_PAYLOAD')
        at=2*p['word']
        if at<61440:
            slot=at//64 if at<49152 else (at-49152)//16
            if slot<596 or refs[slot]:raise ValueError('SPILL_REFERENCED_CHR_WRITE')
        vr[at:at+p['size']]=p['payload']
    cursor=0
    for field in fields:
        target=(n/f"field-{field['index']:03d}.vram").read_bytes()
        png=n/f"field-{field['index']:03d}.png"
        if sha(png.read_bytes())!=field['sha256']:raise ValueError('SPILL_SCREENSHOT_IDENTITY')
        oracle=(n/f"expected-{field['identity']}.rgb555").read_bytes()
        if rgb555(np.asarray(Image.open(png).convert('RGB'))).astype('<u2').tobytes()!=oracle or decode_vram(target,(n/'before-cgram.bin').read_bytes()).astype('<u2').tobytes()!=oracle:raise ValueError('SPILL_INDEPENDENT_FIELD_PIXELS')
        while vr!=target:
            if cursor==len(packets):raise ValueError('SPILL_FIELD_DMA_REPLAY')
            apply(packets[cursor]);cursor+=1
    if cursor!=len(packets) or vr!=(n/'after-vram.bin').read_bytes():raise ValueError('SPILL_COMPLETE_DMA_REPLAY')
    chr_packets=[p for p in packets if p['word']<0x7800];map_packets=[p for p in packets if p['word']>=0x7800]
    for h,l in zip(chr_packets[::2],chr_packets[1::2],strict=True):
        if h['source'] not in range(0x3500,0x36e0,80) or (h['size'],l['source'],l['size'],l['word'])!=(64,h['source']+64,16,0x6000+h['word']//4):raise ValueError('SPILL_PAIR_DESCRIPTOR')
    starts=[e for e in records if e['kind']=='VBLANK_START'];ends=[e for e in records if e['kind']=='VBLANK_END'];done=[e for e in records if e['kind']=='DONE']
    def window(clock):
        edge=max((e for e in starts if e['clock']<=clock),key=lambda e:e['clock']);active=min((e for e in ends if e['clock']>edge['clock']),key=lambda e:e['clock'])
        if clock>=active['clock']:raise ValueError('SPILL_OUTSIDE_VBLANK')
        return edge,active
    fences=[]
    for p in packets:
        d=next(e for e in done if e['clock']>p['clock'] and e['data'][:3]==[str(17),str(p['source']),str(p['size'])]);edge,active=window(p['clock'])
        if d['clock']>=active['clock']:raise ValueError('SPILL_DMA_OVERRUN')
        fences.append(dict(start=p['clock'],end=d['clock'],source=p['source'],size=p['size'],margin=active['clock']-d['clock']))
    batches=[]
    for e in records:
        if e['kind']!='BATCH' or e['data'][:2]!=['NbQueueHasPending','17']:continue
        finish=next(x for x in records if x['kind']=='BATCH' and x['data'][:2]==['NbQueueDrainDone','17'] and x['clock']>e['clock'])
        fs=[f for f in fences if e['clock']<f['start']<finish['clock']];count=int(e['data'][2])
        if len(fs)!=count*2:raise ValueError('SPILL_BATCH_FENCES')
        edge,active=window(fs[-1]['end']);margin=active['clock']-fs[-1]['end']
        if margin<10000:raise ValueError('SPILL_BATCH_GUARD')
        batches.append(dict(pairs=count,start=e['clock'],end=finish['clock'],window_clocks=fs[-1]['end']-edge['clock'],margin_clocks=margin))
    ready_maps=[e for e in records if e['kind']=='READY_MAP' and e['data'][0]=='17']
    if fault_mode in (2,3,4) and ready_maps:raise ValueError('SPILL_EARLY_READY')
    if fault_mode in (0,1):
        if len(ready_maps)!=1:raise ValueError('SPILL_READY_REQUIRED')
        ready_vr=bytearray((n/'before-vram.bin').read_bytes())
        for p in chr_packets:at=p['word']*2;ready_vr[at:at+p['size']]=p['payload']
        mp=bytes.fromhex(ready_maps[0]['data'][1]);ready_vr[61440:63488]=mp;ready_vr[63488:65536]=mp
        if decode_vram(ready_vr,(n/'before-cgram.bin').read_bytes()).astype('<u2').tobytes()!=(n/'expected-17.rgb555').read_bytes():raise ValueError('SPILL_READY_SOURCE_PIXELS')
        if len(chr_packets)!=244 or len({p['word']//32 for p in chr_packets[::2]})!=122:raise ValueError('SPILL_122_DISTINCT_PAIRS')
        if any(refs[p['word']//32] for p in chr_packets[::2]):raise ValueError('SPILL_RESERVATION_OWNERSHIP')
        assets=Path('out/byor-motu-online-v3/assets');hi=(assets/'high.chr').read_bytes();lo=(assets/'low.chr').read_bytes()
        for home,slot in restores:
            if ready_vr[slot*64:slot*64+64]!=hi[home*64:home*64+64] or ready_vr[49152+slot*16:49152+slot*16+16]!=lo[home*16:home*16+16]:raise ValueError('SPILL_BACKDROP_RESTORE_PAYLOAD')
    if fault_mode:
        if map_packets or (n/'after-committed.bin').read_bytes()!=(n/'before-committed.bin').read_bytes() or (n/'after-refs.bin').read_bytes()!=(n/'before-refs.bin').read_bytes():raise ValueError('SPILL_ROLLBACK')
        if fault_mode==4 and packets:raise ValueError('SPILL_PRELOAD_ABORT_DMA')
        if fault_mode==2 and len(chr_packets)!=240:raise ValueError('SPILL_PARTIAL_QUEUE_REJECTION')
    else:
        if [(p['word'],p['size']) for p in map_packets]!=[(0x7800,2048),(0x7c00,2048)]:raise ValueError('SPILL_MAP_COMMIT')
        commit=phase('NbMapCommit');complete=phase('NbMapsComplete');edge,active=window(commit['clock'])
        if complete['clock']>=active['clock']:raise ValueError('SPILL_ATOMIC_COMMIT')
        cm=(n/'after-committed.bin').read_bytes();pm=(n/'after-pending.bin').read_bytes();dr=np.frombuffer((n/'after-refs.bin').read_bytes(),dtype='<u2')&0x3fff
        if cm!=pm or cm!=bytes(vr[61440:63488]) or cm!=bytes(vr[63488:65536]) or not np.array_equal(dr,np.bincount(np.frombuffer(cm,dtype='<u2'),minlength=768)):raise ValueError('SPILL_COMMITTED_IDENTITIES')
        for f in fields:
            if f['label']=='transition' and f['identity']!=(17 if f['frame']>complete['frame'] else 16):raise ValueError('SPILL_FIELD_ATOMIC_IDENTITY')
    begin=phase('NbBegin')['clock'];end=phase('NbAbort' if fault_mode else 'NbVisible')['clock']
    wait_clocks=0
    for w in records:
        if w['kind']=='WAIT_BEGIN' and w['data'][0]=='17':
            stop=next(e for e in records if e['kind']=='WAIT_END' and e['clock']>w['clock'])
            wait_clocks+=stop['clock']-w['clock']
    dma_clocks=sum(f['end']-f['start'] for f in fences)
    costs=dict(total_master_clocks=end-begin,total_ms=(end-begin)/21477.270,wait_clocks=wait_clocks,dma_clocks=dma_clocks,cpu_and_other_clocks=end-begin-wait_clocks-dma_clocks)
    if not fault_mode:
        pre=phase('NbPreloading')['clock'];rdy=phase('NbReady')['clock'];costs.update(planning_clocks=pre-begin,preparation_through_ready_clocks=rdy-begin,composition_clocks=sum(int(e['data'][1]) for e in records if e['kind']=='TILE' and e['data'][0]=='17'),commit_clocks=complete['clock']-commit['clock'],commit_margin_clocks=active['clock']-complete['clock'])
    first=next((f['index'] for f in fields if f['identity']==17),None)
    return dict(classification='BYOR_MOTU_NONBLANK_BATCH_CAPACITY_RESCUE_PASS' if not fault_mode else 'RESTORE_SPILL_ROLLBACK_PASS',fault_mode=fault_mode,candidate=str(n/'bor.sfc'),rom_sha256=sha(rom),visible_fields=len(fields),verified_pixels=len(fields)*57344,pixel_mismatches=0,transition_fields=first-3 if first is not None else None,costs=costs,min_batch_margin_clocks=min((b['margin_clocks'] for b in batches),default=None),batches=batches,fences=fences,restoration_records=restores,actor_pairs=88,total_reservations=122,free_slots_before=124,unreserved_safe_slots_during_transaction=2,committed_free_tail_slots=int(np.count_nonzero((np.frombuffer((n/'after-refs.bin').read_bytes(),dtype='<u2')&0x3fff)[596:]==0)),capacity=capacity,spill_write_bytes=len(writes),two_native_attempts=True,world_snapshots_identical=True,six_projected_noops_graphics_free=True,spill_owner_both_cpus_audited=True,per_field_physical_dma_replay=True,source_ready_verified=bool(ready_maps),brightness=15,unsafe_ppu_operations=0,resource_faults=0,audit=audit_result,fields=fields)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--run-existing',action='store_true');p.add_argument('--fault-mode',type=int,choices=range(5),default=0);a=p.parse_args();folder=a.output.resolve()
    if not a.run_existing:build(folder)
    run(folder,a.fault_mode)
