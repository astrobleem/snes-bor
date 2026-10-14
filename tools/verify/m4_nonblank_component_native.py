"""Build audit and exhaustive per-field native nonblank proof."""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_rect_map_audit import statements,BRANCHES
from nonblank_slice import transform,STATE,MODE,COLD_DISPATCH
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,exact_input_edge
import game_bor_startup_select as startup
from m4_live_ground_owner import REQUEST,SNAPSHOT
from m4_bounded_component_publisher import READY,DISPLAY_EPOCH
from m4_live_ground_component_native import scene_from_snapshot
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
BASE=Path('out/byor-motu-rect-map-v1/native')
BASE_SHA='52872d1546c26d2d9a0be438aaae32bb4ac764c74dc2a6b5a3632f90d4a179c0'


def sha(b):return hashlib.sha256(b).hexdigest()


def audit_rom(rom,native):
    old=(BASE/'bor.sfc').read_bytes();assert sha(old)==BASE_SHA
    before=(BASE/'publisher.pasm').read_text().splitlines();after=(native/'publisher.pasm').read_text().splitlines()
    if after!=transform(before):raise ValueError('NB_EXACT_SOURCE_TRANSFORM')
    oldsy=symbols(BASE/'publisher.sym');sy=symbols(native/'publisher.sym')
    oi=statements(before,oldsy);ni=statements(after,sy)
    if not 0x39a000==sy['NbBegin']<sy['NbCodeEnd']<=0x39c000:raise ValueError('NB_CODE_LEASE')
    if any(old[offset(sy['NbBegin']):offset(sy['NbCodeEnd'])]):raise ValueError('NB_NONZERO_ROM_LEASE')
    # Two insertions only, plus required label relocations in the preserved code.
    pre=before.index('OnlinePreflight:')+3;newpre=after.index('OnlinePreflight:')+3
    end=before.index('.org $C000');newend=after.index('.org $C000');added=len(COLD_DISPATCH)
    mapping=[(0,pre,0),(pre,end,newpre+added),(end,len(before),newend)]
    expected=bytearray(old);expected[offset(0x398000):offset(0x39c000)]=bytes(0x4000)
    covered=set();relocations=0
    for start,stop,newstart in mapping:
        for i in range(start,stop):
            j=newstart+i-start
            if before[i]!=after[j]:raise ValueError('NB_CONTROL_STATEMENT')
            if i not in oi:continue
            pc,n,s=oi[i];npc,nn,_=ni[j]
            if n!=nn:raise ValueError('NB_INSTRUCTION_SIZE')
            data=bytearray(old[offset(pc):offset(pc)+n]);op,_,arg=s.partition(' ')
            if arg in oldsy and op in BRANCHES|{'brl','jsr','jmp','jsl','jml'}:
                dst=sy[arg]
                data[1:]=(dst-npc-n).to_bytes(n-1,'little',signed=True) if op in BRANCHES|{'brl'} else (dst&((1<<(8*(n-1)))-1)).to_bytes(n-1,'little')
                relocations+=int(data!=old[offset(pc):offset(pc)+n])
            if rom[offset(npc):offset(npc)+n]!=data:raise ValueError('NB_PRESERVED_BYTES:'+s)
            expected[offset(npc):offset(npc)+n]=data;covered.add(j)
    compiled=(native/'publisher.bin').read_bytes()
    for j,(pc,n,s) in ni.items():
        if j in covered:continue
        if not (newpre<=j<newpre+added or after.index('.org $A000')<j<newend):raise ValueError('NB_UNAUTHORIZED_ADDITION')
        data=compiled[offset(pc):offset(pc)+n]
        if rom[offset(pc):offset(pc)+n]!=data:raise ValueError('NB_POPPY_BYTES')
        expected[offset(pc):offset(pc)+n]=data
    if expected!=rom:raise ValueError('NB_UNRELATED_ROM_BYTES')
    return dict(status='PASS',start=sy['NbBegin'],end=sy['NbCodeEnd'],code_bytes=sy['NbCodeEnd']-sy['NbBegin'],preserved_statements=len(covered),relocations=relocations,all_assets_kernels_and_other_banks_unchanged=True,chunk_header_lease=[0x42d600,0x42d680],no_additional_vram_or_bwram=True)


def observer(script,contract):
    fs=contract['native_symbols'];original=script.read_text().split('-- ONLINE_OBSERVER_BEGIN',1)[0].split('-- NONBLANK_OBSERVER_BEGIN',1)[0]
    with script.open('w') as f:
        f.write(original+"\n-- NONBLANK_OBSERVER_BEGIN\n")
        f.write("local nbLive=false;local nbColdDone=false;local nbOwned=false;local nbBlank=true;local nbTxn=-1;local nbVram=0;local nbActive=false;local nbSource=0;local nbSize=0;local nbTarget=0;local nbTileStart=0\n")
        f.write("local function nbWord(at)return emu.read(at,emu.memType.snesMemory)+256*emu.read(at+1,emu.memType.snesMemory)end\n")
        f.write("local function nbLog(kind,extra)local s=emu.getState();emu.log('NB_'..kind..'|'..s['masterClock']..'|'..s['ppu.frameCount']..'|'..s['ppu.scanline']..'|'..(extra or ''))end\n")
        def cb(at,body):f.write(f'emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n')
        for name in ('OnlinePublish','OnlineBlank','OnlineComplete','OnlineReject','NbBegin','NbActorProduceStart','NbMapCommit','NbMapsComplete','NbVisible','NbAbort','NbWindowStart','NbPairBegin','NbPairComplete'):
            cb(fs[name],("nbTxn=nbTxn+1;" if name=='OnlinePublish' else "nbColdDone=true;" if name=='OnlineComplete' else "nbOwned=true;local bytes={};for i=0,65535 do bytes[#bytes+1]=string.format('%02x',emu.read(i,emu.memType.snesVideoRam))end;nbLog('BASE',table.concat(bytes));" if name=='OnlineBlank' else '')+f"nbLog('PHASE','{name}|'..nbTxn..'|'..nbWord(0x42d600)..'|'..nbWord(0x42d604)..'|'..nbWord(0x7ffb98))")
        for code,name in ((bytes.fromhex('a902008f00d642'),'NbPreloading'),(bytes.fromhex('a903008f00d642'),'NbReady')):
            rom=(script.parent/'bor.sfc').read_bytes();start=offset(fs['NbBegin']);end=offset(fs['NbCodeEnd']);section=rom[start:end]
            if section.count(code)!=1:raise ValueError('NB_PHASE_BOUNDARY')
            cb(fs['NbBegin']+section.index(code)+len(code),f"nbLog('PHASE','{name}|'..nbTxn..'|'..nbWord(0x42d600)..'|'..nbWord(0x42d604)..'|'..nbWord(0x7ffb98))")
        cb(fs['NbFreshVblank'],"nbLog('WAIT_BEGIN',nbTxn)")
        cb(fs['NbWindowStart'],"nbLog('WAIT_END',nbTxn)")
        cb(fs['AstraOpaqueTile'],"if nbTxn>0 then nbTileStart=emu.getState()['masterClock']end")
        cb(fs['AstraTileDone'],"if nbTxn>0 then nbLog('TILE',nbTxn..'|'..(emu.getState()['masterClock']-nbTileStart))end")
        for name,at in fs.items():
            if name.startswith('OnlineDmaDone'):
                cb(at+2,"if nbActive then nbLog('DONE',nbTxn..'|'..nbSource..'|'..nbSize..'|'..nbTarget);nbActive=false end")
        f.write("emu.addEventCallback(function()if nbLive then nbLog('VBLANK_START',nbTxn)end end,emu.eventType.endFrame)\n")
        f.write("emu.addEventCallback(function()if nbLive then nbLog('VBLANK_END',nbTxn)end end,emu.eventType.startFrame)\n")
        f.write("""
emu.addMemoryCallback(function(a,v)
 if a==0x2116 then nbVram=(nbVram&0xff00)|v elseif a==0x2117 then nbVram=(nbVram&0xff)|(v<<8)end
 if nbTxn<0 then return end
 if a==0x2100 then nbBlank=(v&128)~=0;nbLog('INIDISP',v);if v==15 and nbColdDone then nbLive=true end end
 if nbLive and (nbBlank or a==0x2100 and v~=15)then nbLog('FAULT','BRIGHTNESS')end
 if nbLive and not nbBlank and emu.getState()['ppu.scanline']<225 then nbLog('FAULT','ACTIVE_PPU_WRITE:'..a)end
end,emu.callbackType.write,0x2100,0x2133,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if nbLive and not nbBlank and emu.getState()['ppu.scanline']<225 then nbLog('FAULT','ACTIVE_VRAM_READ:'..a)end
end,emu.callbackType.read,0x2139,0x213a,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 nbLog('SERVICE',a..'|'..v)
end,emu.callbackType.write,0x4200,0x4200,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if not nbOwned then return end
 local mt=emu.memType.snesMemory
 nbSource=nbWord(0x4372)+65536*emu.read(0x4374,mt);nbSize=nbWord(0x4375);nbTarget=emu.read(0x4371,mt);nbActive=true
 local payload={};if nbSource<0xc00000 then for i=0,nbSize-1 do payload[#payload+1]=string.format('%02x',emu.read(nbSource+i,mt))end end
 nbVram=emu.getState()['ppu.vramAddress']
 nbLog('PACKET',nbTxn..'|'..nbTarget..'|'..nbVram..'|'..nbSource..'|'..nbSize..'|'..table.concat(payload))
 if nbLive and (nbBlank or emu.getState()['ppu.scanline']<225)then nbLog('FAULT','UNSAFE_DMA')end
end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
""")


def run_frames_exact(m,count):
    remaining=count;last=None;attempts=0
    while remaining:
        r=m.run_frames(remaining);advanced=r.get("framesAdvanced",-1)
        if not 0<=advanced<=remaining or (last is not None and r["startFrame"]!=last):raise ValueError("NB_EXACT_FRAME_DRIFT")
        remaining-=advanced;last=r["endFrame"]
        if remaining:
            attempts+=1
            if not r.get("timedOut") or attempts>8:raise ValueError("NB_FRAME_TOOL_STALL")


def run(folder,source,sy,contract):
    analyze_retained(folder)
    native=folder/'native';script=native/'callback_owner.lua';observer(script,contract)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kw):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kw)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    fields=[];current=None;next_image=None;switched=False
    with Observed(rom=native/'bor.sfc',mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=native/'mesen.log') as m:
        m.write_u16(READY,0)
        reporter=Reporter('MOTU-NONBLANK',kind='GATE')
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('NB_BOOTSTRAP')
        run_frames_exact(m,12)
        for name in ('StageWater_Enabled','StageWater_Pending','StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'):m.write_u8(sy[name],0)
        m.write_u16(0x7ffb84,0);m.write_u16(0x7ffb82,0)
        (native/'initial-vram.bin').write_bytes(m.read_memory('SnesVideoRam',0,65536))
        m.hold_input(0,port=0);run_frames_exact(m,2);m.write_u16(REQUEST,0xb4e7)
        for i in range(100):
            run_frames_exact(m,1)
            if startup.u16(m,READY)==0xb4b8:break
        else:raise ValueError('NB_COLD_TIMEOUT')
        run_frames_exact(m,2)
        def capture(name):
            raw=m.read_memory('SnesMemory',SNAPSHOT,146);scene=scene_from_snapshot(raw,source)
            image,_=compose_rgb8(source,'DATA/LEVELS/GUILE2.TXT',scene);image=rgb555(image).astype('<u2')
            (native/f'{name}-world.bin').write_bytes(raw);(native/f'{name}-expected.rgb555').write_bytes(image.tobytes())
            return image,raw
        current,cold=capture('cold')
        def save_checkpoint(name):
            for kind,at,n,label in [('SnesVideoRam',0,65536,'vram'),('SnesCgRam',0,512,'cgram'),('SnesMemory',0x42c000,2048,'pending'),('SnesMemory',0x42c800,2048,'committed'),('SnesMemory',0x42d000,1536,'refs')]:
                (native/f'{name}-{label}.bin').write_bytes(m.read_memory(kind,at,n))
        save_checkpoint('cold')
        def field(label,allow_new=False):
            nonlocal switched
            run_frames_exact(m,1)
            shot=m.tool('take_screenshot',{'format':'path'});dest=native/f'field-{len(fields):04d}.png';shutil.copyfile(shot['path'],dest)
            actual=rgb555(np.asarray(Image.open(dest).convert('RGB')))
            old_ok=actual.shape==current.shape and np.array_equal(actual,current)
            new_ok=allow_new and next_image is not None and actual.shape==next_image.shape and np.array_equal(actual,next_image)
            if not old_ok and not new_ok:raise ValueError('NB_VISIBLE_FIELD_MISMATCH:'+str(len(fields)))
            if switched and not new_ok:raise ValueError('NB_VISIBLE_REGRESSION')
            if new_ok:switched=True
            vram=m.read_memory('SnesVideoRam',0,65536);cgram=m.read_memory('SnesCgRam',0,512)
            (native/f'field-{len(fields):04d}.vram').write_bytes(vram)
            decoded=decode_vram(vram,cgram)
            if not np.array_equal(decoded,current) and not (allow_new and next_image is not None and np.array_equal(decoded,next_image)):raise ValueError('NB_FIELD_VRAM_DECODE')
            if cgram!=(native/'cold-cgram.bin').read_bytes():raise ValueError('NB_PALETTE_DRIFT')
            state=m.get_ppu_state()
            if state['forcedBlank'] or state['brightness']!=15:raise ValueError('NB_VISIBLE_BRIGHTNESS')
            header=m.read_memory('SnesMemory',STATE,32)
            fields.append(dict(index=len(fields),label=label,identity='new' if new_ok else 'old',pixels=57344,mismatches=0,screenshot_sha256=sha(dest.read_bytes()),vram_sha256=sha(vram),vram_identity='old' if np.array_equal(decoded,current) else 'new',header=header.hex(),ppu=state,displayed_epoch=startup.u16(m,DISPLAY_EPOCH)))
            (folder/'fields.json').write_text(json.dumps(fields,indent=2)+'\n')
        field('cold-visible')
        # Fail a completely preloaded, controller-owned picture at READY.
        m.write_u16(MODE,1);m.hold_input(m.BTN_RIGHT,port=0)
        field('defer-input');field('defer-input');m.write_u16(REQUEST,0xb4e8)
        for i in range(350):
            field('deferred')
            if startup.u16(m,0x7ffb84)==1:break
        else:raise ValueError('NB_DEFER_TIMEOUT')
        save_checkpoint('deferred');deferred_image,deferred=capture('deferred')
        if not np.array_equal(current,rgb555(np.asarray(Image.open(native/f'field-{len(fields)-1:04d}.png').convert('RGB')))):raise ValueError('NB_DEFER_DISPLAY')
        # Source RIGHT again advances the same persistent actor to x=81.
        m.write_u16(MODE,0);m.hold_input(m.BTN_RIGHT,port=0)
        field('move-input');field('move-input');m.write_u16(REQUEST,0xb4e8)
        # Sealing precedes PREPARING. Sample before independently making the
        # oracle; no host graphics writes, only controller and request words.
        for seal_wait in range(10):
            field('move-seal')
            if startup.u16(m,SNAPSHOT+144)==2:break
        else:raise ValueError('NB_SEALED_SNAPSHOT_TIMEOUT')
        next_image,moved=capture('moved')
        if np.array_equal(current,next_image):raise ValueError('NB_UNCHANGED_SUCCESS')
        for i in range(350):
            field('movement',True)
            if startup.u16(m,DISPLAY_EPOCH)==2 and startup.u16(m,0x7ffb84)==0:break
        else:raise ValueError('NB_MOVEMENT_TIMEOUT')
        field('new-visible',True);field('new-visible',True);save_checkpoint('moved')
        if not switched:raise ValueError('NB_NO_VISIBLE_COMMIT')
        current=next_image;next_image=None;switched=False
        m.hold_input(m.BTN_LEFT,port=0);field('left-input');field('left-input');m.write_u16(REQUEST,0xb4e8)
        for i in range(5):field('left-rejected')
        save_checkpoint('left')
        if startup.u16(m,0x7ffb84)!=1 or startup.u16(m,DISPLAY_EPOCH)!=2:raise ValueError('NB_LEFT_REJECTION')
        capture('left');m.release_input(port=0)
    result=certify(folder,contract,fields)
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['classification'],flush=True)



def decode_vram(vram,cgram):
    """Independent planar decoding and exact additive component reconstruction."""
    def tiles(data,bpp):
        raw=np.frombuffer(data,dtype='u1').reshape(-1,8*bpp);pixels=np.zeros((len(raw),8,8),dtype=np.uint16)
        for plane in range(bpp):
            rows=raw[:,(plane//2)*16+np.arange(8)*2+plane%2]
            pixels|=np.unpackbits(rows[:,:,None],axis=2).astype(np.uint16)<<plane
        return pixels
    high=tiles(vram[:49152],8);low=tiles(vram[49152:61440],2)
    hm=np.frombuffer(vram[61440:63488],dtype='<u2').reshape(32,32);lm=np.frombuffer(vram[63488:],dtype='<u2').reshape(32,32)
    if not np.array_equal(hm,lm) or np.any(hm>=768):raise ValueError('NB_PAIRED_MAP_IDENTITY')
    palette=np.frombuffer(cgram,dtype='<u2')
    def canvas(ts,mp):return ts[mp[:28]].transpose(0,2,1,3).reshape(224,256)
    return palette[canvas(high,hm)]+palette[canvas(low,lm)]


def certify(folder,contract,fields):
    native=folder/'native';rom=(native/'bor.sfc').read_bytes();audit=audit_rom(rom,native)
    records=[]
    for line in (native/'mesen.log').read_text(errors='replace').splitlines():
        if 'NB_' not in line:continue
        line=line[line.index('NB_'):];p=line.split('|');records.append(dict(kind=p[0][3:],clock=int(p[1]),frame=int(p[2]),line=int(p[3]),data=p[4:]))
    (folder/'native-events.json').write_text(json.dumps(records,indent=2)+'\n')
    faults=[x for x in records if x['kind']=='FAULT']
    if faults:raise ValueError('NB_NATIVE_SAFETY:'+str(faults[:3]))
    packets=[]
    for e in records:
        if e['kind']=='PACKET':
            d=e['data'];packets.append(dict(**{k:e[k] for k in ('clock','frame','line')},transaction=int(d[0]),target=int(d[1]),vram_word=int(d[2]),source=int(d[3]),bytes=int(d[4]),payload=d[5]))
    (folder/'dma-packets.json').write_text(json.dumps(packets,indent=2)+'\n')
    bases=[e for e in records if e['kind']=='BASE']
    if len(bases)!=1:raise ValueError('NB_VRAM_HANDOFF_CAPTURE')
    handoff=bytes.fromhex(bases[0]['data'][0]);(native/'handoff-vram.bin').write_bytes(handoff)
    if len(handoff)!=65536:raise ValueError('NB_VRAM_HANDOFF_SIZE')
    vram=bytearray(handoff);palette=bytearray(512);refs=None;replay=[];warm=[]
    checkpoints={0:'cold',1:'deferred',2:'moved',3:'left'}
    def payload(p):
        data=rom[p['source']-0xc00000:p['source']-0xc00000+p['bytes']] if p['source']>=0xc00000 else bytes.fromhex(p['payload'])
        if len(data)!=p['bytes']:raise ValueError('NB_DMA_PAYLOAD_LENGTH')
        return data
    # Replay includes safe rejected preload writes, not only successful epochs.
    for txn,name in checkpoints.items():
        batch=[p for p in packets if p['transaction']==txn]
        if txn==0:
            pass
        elif txn==3 and batch:raise ValueError('NB_LEFT_DMA')
        map_packets=[];pair_packets=[]
        for p in batch:
            data=payload(p)
            if p['target']==0x22:
                if txn or len(data)!=512:raise ValueError('NB_PALETTE_DMA');
                palette[:]=data
            elif p['target']==0x18:
                at=2*p['vram_word']
                if at+len(data)>65536:raise ValueError('NB_VRAM_RANGE')
                if txn and at<61440:
                    slot=at//64 if at<49152 else (at-49152)//16
                    if slot<596 or refs[slot]:raise ValueError('NB_REFERENCED_CHR_OVERWRITE')
                    pair_packets.append(p)
                elif txn:map_packets.append(p)
                vram[at:at+len(data)]=data
            else:raise ValueError('NB_DMA_TARGET')
        if vram!=(native/f'{name}-vram.bin').read_bytes():raise ValueError('NB_FULL_DMA_REPLAY:'+name)
        if palette!=(native/f'{name}-cgram.bin').read_bytes():raise ValueError('NB_CGRAM_REPLAY')
        cm=(native/f'{name}-committed.bin').read_bytes();pm=(native/f'{name}-pending.bin').read_bytes();dr=np.frombuffer((native/f'{name}-refs.bin').read_bytes(),dtype='<u2')
        mp=np.frombuffer(bytes(vram[61440:63488]),dtype='<u2')
        if cm!=pm or cm!=bytes(vram[61440:63488]) or not np.array_equal(dr&0x3fff,np.bincount(mp,minlength=768)):raise ValueError('NB_COMMITTED_OWNERSHIP:'+name)
        if txn in (1,3):
            previous='cold' if txn==1 else 'moved'
            if cm!=(native/f'{previous}-committed.bin').read_bytes() or (native/f'{name}-refs.bin').read_bytes()!=(native/f'{previous}-refs.bin').read_bytes():raise ValueError('NB_REJECTED_OWNERSHIP')
        if txn:
            for h,l in zip(pair_packets[::2],pair_packets[1::2],strict=True):
                if (h['source'],h['bytes'],l['source'],l['bytes'])!=(0x42d680,64,0x42d6c0,16) or l['vram_word']!=0x6000+h['vram_word']//4:raise ValueError('NB_PAIR_DESCRIPTORS')
            if txn==2:
                if [(p['vram_word'],p['bytes']) for p in map_packets]!=[(0x7800,2048),(0x7c00,2048)]:raise ValueError('NB_ATOMIC_MAP_DESCRIPTORS')
            elif map_packets:raise ValueError('NB_FAILED_MAP_COMMIT')
            warm.append(dict(transaction=txn,pairs=len(pair_packets)//2,chr_bytes=sum(p['bytes'] for p in pair_packets),map_bytes=sum(p['bytes'] for p in map_packets),descriptors=len(batch)))
        refs=np.bincount(mp,minlength=768)
        replay.append(dict(transaction=txn,checkpoint=name,bytes=sum(p['bytes'] for p in batch),full_vram_bytes=65536,complete_replay=True))
    # Every per-field physical capture must equal an ordered whole-transfer
    # prefix of the independent replay, not merely decode plausibly.
    vr=bytearray(handoff);cursor=0
    for field in fields:
        target=(native/f"field-{field['index']:04d}.vram").read_bytes()
        while vr!=target:
            if cursor>=len(packets):raise ValueError('NB_FIELD_DMA_REPLAY')
            p=packets[cursor];cursor+=1
            if p['target']==0x18:at=2*p['vram_word'];vr[at:at+p['bytes']]=payload(p)
        if sha(vr)!=field['vram_sha256']:raise ValueError('NB_FIELD_HASH')
    # Native fences and measured emulator VBlank edges, no assumed bandwidth.
    starts=[e for e in records if e['kind']=='VBLANK_START'];ends=[e for e in records if e['kind']=='VBLANK_END']
    def window(clock):
        start=max((e for e in starts if e['clock']<=clock),key=lambda e:e['clock'])
        end=min((e for e in ends if e['clock']>start['clock']),key=lambda e:e['clock'])
        if not clock<end['clock']:raise ValueError('NB_OUTSIDE_VBLANK')
        return start,end
    done=[e for e in records if e['kind']=='DONE']
    fence_rows=[]
    for p in [p for p in packets if p['transaction']>0]:
        candidates=[e for e in done if e['clock']>p['clock'] and int(e['data'][0])==p['transaction'] and int(e['data'][1])==p['source'] and int(e['data'][2])==p['bytes']]
        if not candidates:raise ValueError('NB_MISSING_DMA_FENCE')
        end=min(candidates,key=lambda e:e['clock']);start_edge,end_edge=window(p['clock'])
        if end['clock']>=end_edge['clock']:raise ValueError('NB_DMA_VBLANK_OVERRUN')
        fence_rows.append(dict(transaction=p['transaction'],source=p['source'],bytes=p['bytes'],start=p['clock'],end=end['clock'],window_start=start_edge['clock'],window_end=end_edge['clock'],margin=end_edge['clock']-end['clock']))
    phases=[e for e in records if e['kind']=='PHASE']
    def phase(name,txn):return next(e for e in phases if e['data'][0]==name and int(e['data'][1])==txn)
    commit=phase('NbMapCommit',2);complete=phase('NbMapsComplete',2);vs,ve=window(commit['clock'])
    if complete['clock']>=ve['clock']:raise ValueError('NB_COMMIT_BUDGET')
    cold=(native/'cold-expected.rgb555').read_bytes();moved=(native/'moved-expected.rgb555').read_bytes()
    ready=phase('NbReady',2)['clock'];rv=bytearray(handoff)
    for p in packets:
        if p['clock']>=ready:continue
        if p['target']==0x18:at=p['vram_word']*2;rv[at:at+p['bytes']]=payload(p)
    pending=(native/'moved-pending.bin').read_bytes();rv[61440:63488]=pending;rv[63488:]=pending
    if decode_vram(bytes(rv),bytes(palette)).astype('<u2').tobytes()!=moved:raise ValueError('NB_READY_RESIDENCY_ORACLE')
    if any(p['transaction']==2 and p['vram_word']<0x7800 and p['clock']>=ready for p in packets):raise ValueError('NB_CHR_AFTER_READY')
    if any(e['transaction']==2 and e['source'] in (0x42d680,0x42d6c0) and e['end']>=ready for e in fence_rows):raise ValueError('NB_READY_BEFORE_PAIR_FENCES')
    if cold==moved:raise ValueError('NB_NO_CHANGED_PIXELS')
    for name,reference in [('cold','world-00.bin'),('deferred','world-01.bin'),('moved','world-02.bin')]:
        if (native/f'{name}-world.bin').read_bytes()!=(BASE/reference).read_bytes():raise ValueError('NB_SOURCE_WORLD_DRIFT:'+name)
    for f in fields:
        if f['ppu']['forcedBlank'] or f['ppu']['brightness']!=15:raise ValueError('NB_BRIGHTNESS_CERTIFICATION')
        if f['label']=='movement':
            expected_identity='new' if f['ppu']['frameCount']>complete['frame'] else 'old'
            if f['identity']!=expected_identity:raise ValueError('NB_FIELD_COMMIT_ORDER')
    costs=[]
    for txn in (1,2):
        begin=phase('NbBegin',txn)['clock'];preloading=phase('NbPreloading',txn)['clock'];ready=phase('NbReady',txn)['clock'];visible=phase('NbAbort' if txn==1 else 'NbVisible',txn)['clock']
        waits=[e for e in records if e['kind']=='WAIT_BEGIN' and int(e['data'][0])==txn and e['clock']<ready]
        wait_clocks=0
        for w in waits:
            end=min(e['clock'] for e in records if e['kind']=='WAIT_END' and e['clock']>w['clock'])
            wait_clocks+=end-w['clock']
        dma=sum(e['end']-e['start'] for e in fence_rows if e['transaction']==txn and e['start']<ready)
        composition=sum(int(e['data'][1]) for e in records if e['kind']=='TILE' and int(e['data'][0])==txn)
        costs.append(dict(transaction=txn,planning_clocks=preloading-begin,composition_clocks=composition,preparing_through_ready_clocks=ready-begin,wait_clocks=wait_clocks,chr_dma_clocks=dma,cpu_preparation_clocks=ready-begin-wait_clocks-dma,total_clocks=visible-begin))
    first_new=next(x['index'] for x in fields if x['label']=='movement' and x['identity']=='new')
    first_move=next(x['index'] for x in fields if x['label']=='move-seal')
    return dict(status='PASS',classification='BYOR_MOTU_NONBLANK_PRESENTATION_SLICE_PASS',candidate=str(native/'bor.sfc'),rom_sha256=sha(rom),contract=contract,audit=audit,observed_fields=len(fields),verified_pixels=len(fields)*57344,pixel_mismatches=0,changed_pixels=int(np.count_nonzero(np.frombuffer(cold,dtype='<u2')!=np.frombuffer(moved,dtype='<u2'))),transition_fields=first_new-first_move,transaction_costs=costs,commit=dict(start=commit['clock'],end=complete['clock'],clocks=complete['clock']-commit['clock'],vblank_start=vs['clock'],vblank_end=ve['clock'],budget_clocks=ve['clock']-commit['clock'],margin_clocks=ve['clock']-complete['clock']),warm_transfers=warm,dma_fences=fence_rows,full_dma_replay=replay,per_field_vram_replay=True,ready_residency_source_oracle=True,unsafe_ppu_operations=0,resource_faults=0,deferred_at_ready_retained=True,left_rejected_retained=True,source_snapshots_identical=True,fields_receipt=str(folder/'fields.json'),services='Legacy NMI/audio/video service is withdrawn by the retained isolated source fixture. Minimal owned NMI services only $4210; NMI disabled during native preparation/preload/commit, auto-JOY restored when idle. No audio timing claim.',nonclaims=['30 FPS','general consecutive-frame capacity','full-world traversal','authored audio scheduling','MOTU Demo'])


def analyze_retained(folder):
    base=BASE;assets=Path('out/byor-motu-online-v3/assets')
    backdrop=np.frombuffer((assets/'0-high.map').read_bytes(),dtype='<u2')
    rows=[]
    for old_epoch,new_epoch in [(i-1,i) for i in range(1,18)]+[(0,2)]:
        old=(base/f'vram-{old_epoch:02d}.bin').read_bytes();new=(base/f'vram-{new_epoch:02d}.bin').read_bytes()
        om=np.frombuffer(old[61440:63488],dtype='<u2');nm=np.frombuffer(new[61440:63488],dtype='<u2')
        od=np.frombuffer((base/f'directory-{old_epoch:02d}.bin').read_bytes(),dtype='<u2');nd=np.frombuffer((base/f'directory-{new_epoch:02d}.bin').read_bytes(),dtype='<u2')
        refs=set(map(int,om));free=set(range(768))-refs
        def tile(v,i):return v[i*64:i*64+64]+v[49152+i*16:49152+i*16+16]
        resident={tile(old,i) for i in refs};needed={tile(new,int(i)) for i in nm};fresh=needed-resident
        actor=(nd[nm]&0x4000)!=0
        restores=set(map(int,backdrop[(~actor)&((od[backdrop]&0x8000)!=0)]))
        conservative=int(np.count_nonzero(actor))+len(restores);tail=sorted(free&set(range(596,768)))
        rows.append(dict(old_epoch=old_epoch,next_epoch=new_epoch,displayed_slots=sorted(refs),unreferenced_slots=sorted(free),safe_tail_slots=tail,reused_identity_sha256=sorted(sha(b) for b in needed&resident),new_identity_sha256=sorted(sha(b) for b in fresh),exact_new_pairs=len(fresh),minimum_chr_bytes=len(fresh)*80,backdrop_restoration_homes=sorted(restores),conservative_actor_pairs=int(np.count_nonzero(actor)),conservative_required_pairs=conservative,conservative_chr_bytes=conservative*80,conservative_deficit=max(0,conservative-len(tail)),map_word_changes=int(np.count_nonzero(om!=nm)),nonblank_commit_bytes=4096,nonblank_commit_descriptors=2))
    (folder/'residency-analysis.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows
