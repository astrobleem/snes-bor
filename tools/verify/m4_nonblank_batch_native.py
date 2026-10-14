"""Candidate-specific six-pair nonblank ROM audit, observer and certifier.
The certified one-pair auditor/certifier remain untouched.
"""
import json,inspect,re
from pathlib import Path
from unittest.mock import patch
import numpy as np
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_nonblank_component_native import sha,decode_vram,BASE
import m4_nonblank_component_native as control
from nonblank_batch_rescue import transform as batch_transform
from batch_failure_fixture import transform as faults
original_observer=control.observer
CONTROL=Path('out/byor-motu-nonblank-v5/native')
CONTROL_SHA='9f85b14626405c06295536e65b6f73a229849a6b6bebf0b99862792035f6130f'


def audit_rom(rom,native):
    old=(CONTROL/'bor.sfc').read_bytes()
    if sha(old)!=CONTROL_SHA:raise ValueError('BATCH_CONTROL_SHA')
    before=(CONTROL/'publisher.pasm').read_text().splitlines();after=(native/'publisher.pasm').read_text().splitlines()
    if after!=faults(batch_transform(before)):raise ValueError('BATCH_EXACT_SOURCE_TRANSFORM')
    sy=symbols(native/'publisher.sym')
    from m4_rect_map_audit import statements
    statements(after,sy)
    if not 0x39a000==sy['NbBegin']<sy['NbCodeEnd']<=0x39c000:raise ValueError('BATCH_CODE_LEASE')
    end=offset(sy['NbCodeEnd']);start=offset(sy['NbBegin']);oldend=offset(symbols(CONTROL/'publisher.sym')['NbCodeEnd'])
    if any(old[oldend:end]):raise ValueError('BATCH_NEW_CODE_NONZERO_LEASE')
    compiled=(native/'publisher.bin').read_bytes();expected=bytearray(old);expected[start:end]=compiled[start:end]
    if rom!=expected:raise ValueError('BATCH_UNRELATED_ROM_MUTATION')
    return dict(status='PASS',start=sy['NbBegin'],end=sy['NbCodeEnd'],bytes=end-start,exact_source_splice=True,all_other_rom_bytes_identical=True,kernels_assets_source_services_and_control_paths_unchanged=True,iram_records=[0x3480,0x3500],iram_queue=[0x3500,0x36e0],metadata=[0x42d660,0x42d66e],exact_marker=[0x42d674,0x42d676])


def observer(script,contract):
    original_observer(script,contract);sy=contract['native_symbols']
    with script.open('a') as f:
        def cb(at,body):f.write(f'emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n')
        for name in ('NbQueueHasPending','NbQueueDrainDone','NbBeginRetry','NbExactExhausted'):
            cb(sy[name],f"nbLog('BATCH','{name}|'..nbTxn..'|'..nbWord(0x42d660)..'|'..nbWord(0x42d674)..'|'..nbWord(0x42d606))")
        f.write('local batchGuard=false;local guardBytes=nil\n')
        cb(sy['NbBegin'],"if not batchGuard then batchGuard=true;guardBytes={};for i=0x6e0,0x7ff do guardBytes[#guardBytes+1]=emu.read(i,emu.memType.sa1InternalRam)end end")
        for cpu in ('snes','sa1'):
            f.write("emu.addMemoryCallback(function(a,v)if batchGuard then local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];if '"+cpu+"'~='snes' or pc<"+str(sy['NbBegin'])+" or pc>="+str(sy['NbCodeEnd'])+" then nbLog('FAULT','QUEUE_OWNER:"+cpu+"|'..a)end end end,emu.callbackType.write,0x480,0x6df,emu.cpuType."+cpu+",emu.memType.sa1InternalRam)\n")
            f.write("emu.addMemoryCallback(function(a,v)if batchGuard then nbLog('FAULT','CC_STACK_WRITE:"+cpu+"|'..a)end end,emu.callbackType.write,0x6e0,0x7ff,emu.cpuType."+cpu+",emu.memType.sa1InternalRam)\n")
        f.write("emu.addEventCallback(function()if batchGuard then for i=0x6e0,0x7ff do if emu.read(i,emu.memType.sa1InternalRam)~=guardBytes[i-0x6e0+1] then nbLog('FAULT','CC_STACK_CANARY');break end end end end,emu.eventType.endFrame)\n")


def run(folder,source,sy,contract,fault_mode=1):
    contract=dict(contract,injected_fault_mode=fault_mode)
    from _harness import McpSession
    read=McpSession.read_memory
    def captured(self,kind,address,length,*args,**kwargs):
        data=read(self,kind,address,length,*args,**kwargs)
        if kind=='SnesMemory' and address==0x42d000 and length==1536:
            raw=read(self,'SnesMemory',0x7fba00,146);epoch=int.from_bytes(raw[144:146],'little')
            name={0:'cold',1:'deferred',2:'moved',3:'noop',4:'left'}.get(epoch)
            if name:(folder/'native'/f'{name}-queue.bin').write_bytes(read(self,'SnesMemory',0x42d660,32))
        return data
    write=McpSession.write_u16
    def injected(self,address,value,*args,**kwargs):
        if address==0x42d602 and value==1:value=fault_mode
        return write(self,address,value,*args,**kwargs)
    with patch.object(control,'observer',observer),patch.object(control,'certify',certify),patch.object(McpSession,'write_u16',injected),patch.object(McpSession,'read_memory',captured):
        namespace=dict(control.__dict__)
        body=inspect.getsource(control.run).replace('def run(folder,source,sy,contract):','def execute_slice(folder,source,sy,contract):')
        needle="        m.hold_input(m.BTN_LEFT,port=0);field('left-input')"
        replacement="        m.hold_input(m.BTN_RIGHT,port=0);field('noop-input');field('noop-input');m.write_u16(REQUEST,0xb4e8)\n        for i in range(10):\n            field('noop')\n            if startup.u16(m,DISPLAY_EPOCH)==3:break\n        else:raise ValueError('BATCH_NOOP_TIMEOUT')\n        save_checkpoint('noop');capture('noop')\n"+needle
        if needle not in body:raise ValueError('BATCH_CONTROLLER_DRIVER_DRIFT')
        body=body.replace(needle,replacement).replace("startup.u16(m,DISPLAY_EPOCH)!=2","startup.u16(m,DISPLAY_EPOCH)!=3")
        exec(body,namespace);namespace['execute_slice'](folder,source,sy,contract)


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
    checkpoints={0:'cold',1:'deferred',2:'moved',3:'noop',4:'left'}
    def payload(p):
        data=rom[p['source']-0xc00000:p['source']-0xc00000+p['bytes']] if p['source']>=0xc00000 else bytes.fromhex(p['payload'])
        if len(data)!=p['bytes']:raise ValueError('NB_DMA_PAYLOAD_LENGTH')
        return data
    # Replay includes safe rejected preload writes, not only successful epochs.
    for txn,name in checkpoints.items():
        batch=[p for p in packets if p['transaction']==txn]
        if txn==0:
            pass
        elif txn in (3,4) and batch:raise ValueError('NB_LEFT_DMA')
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
        if txn in (1,3,4):
            previous='cold' if txn==1 else 'moved'
            if cm!=(native/f'{previous}-committed.bin').read_bytes() or (native/f'{name}-refs.bin').read_bytes()!=(native/f'{previous}-refs.bin').read_bytes():raise ValueError('NB_REJECTED_OWNERSHIP')
        if txn:
            for h,l in zip(pair_packets[::2],pair_packets[1::2],strict=True):
                if h['source'] not in range(0x3500,0x36e0,80) or (h['bytes'],l['source'],l['bytes'])!=(64,h['source']+64,16) or l['vram_word']!=0x6000+h['vram_word']//4:raise ValueError('NB_PAIR_DESCRIPTORS')
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
    if any(e['transaction']==2 and 0x3500<=e['source']<0x36e0 and e['end']>=ready for e in fence_rows):raise ValueError('NB_READY_BEFORE_PAIR_FENCES')
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
        begin=phase('NbBegin',txn)['clock'];preloading=phase('NbPreloading',txn)['clock'];ready=next((e['clock'] for e in phases if e['data'][0]=='NbReady' and int(e['data'][1])==txn),phase('NbAbort',txn)['clock'] if txn==1 else phase('NbVisible',txn)['clock']);visible=phase('NbAbort' if txn==1 else 'NbVisible',txn)['clock']
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
    batches=[]
    events=[e for e in records if e['kind']=='BATCH']
    for entry in [e for e in events if e['data'][0]=='NbQueueHasPending']:
        txn=int(entry['data'][1]);count=int(entry['data'][2]);finish=next(e for e in events if e['data'][0]=='NbQueueDrainDone' and e['clock']>entry['clock'])
        last=max(e['end'] for e in fence_rows if e['transaction']==txn and entry['clock']<e['start']<finish['clock'])
        edge,active=window(last);margin=active['clock']-last
        if margin<10000:raise ValueError('BATCH_10000_CLOCK_MARGIN')
        batch_packets=[p for p in packets if p['transaction']==txn and entry['clock']<p['clock']<finish['clock']]
        if len(batch_packets)!=2*count:raise ValueError('BATCH_DESCRIPTOR_COUNT')
        for i,(h,l) in enumerate(zip(batch_packets[::2],batch_packets[1::2],strict=True)):
            if (h['source'],l['source'])!=(0x3500+80*i,0x3540+80*i):raise ValueError('BATCH_SOURCE_SEQUENCE')
        batches.append(dict(transaction=txn,pairs=count,start=entry['clock'],first_dma=batch_packets[0]['clock'],last_low_fence=last,vblank_start=edge['clock'],vblank_end=active['clock'],window_clocks=last-edge['clock'],margin_clocks=margin))
    if first_new-first_move>=120:raise ValueError('BATCH_NO_LATENCY_IMPROVEMENT')
    for name in ('deferred','moved','noop','left'):
        header=(native/f'{name}-queue.bin').read_bytes()
        if int.from_bytes(header[:2],'little'):raise ValueError('BATCH_STALE_QUEUE')
    fault=contract.get('injected_fault_mode',1)
    reached_ready=any(e['data'][0]=='NbReady' and int(e['data'][1])==1 for e in phases)
    produced=sum(e['kind']=='TILE' and int(e['data'][0])==1 for e in records)
    first=next(x for x in warm if x['transaction']==1)
    if fault==2 and (reached_ready or produced!=103 or first['pairs']!=108):raise ValueError('BATCH_INCOMPLETE_DEFERRAL_NOT_EXERCISED')
    if fault==3 and (reached_ready or first['pairs']!=111):raise ValueError('BATCH_STALE_REJECTION_NOT_EXERCISED')
    if fault==1 and not reached_ready:raise ValueError('BATCH_READY_ROLLBACK_NOT_EXERCISED')
    return dict(status='PASS',classification='NONBLANK_BATCH_PASS_CAPACITY_PENDING',batches=batches,min_batch_margin_clocks=min(b['margin_clocks'] for b in batches),capacity_admission='Pending: real epoch-17 exact pass needs 34 restoration records, supplied bound is 32',candidate=str(native/'bor.sfc'),rom_sha256=sha(rom),contract=contract,audit=audit,observed_fields=len(fields),verified_pixels=len(fields)*57344,pixel_mismatches=0,changed_pixels=int(np.count_nonzero(np.frombuffer(cold,dtype='<u2')!=np.frombuffer(moved,dtype='<u2'))),transition_fields=first_new-first_move,transaction_costs=costs,commit=dict(start=commit['clock'],end=complete['clock'],clocks=complete['clock']-commit['clock'],vblank_start=vs['clock'],vblank_end=ve['clock'],budget_clocks=ve['clock']-commit['clock'],margin_clocks=ve['clock']-complete['clock']),warm_transfers=warm,dma_fences=fence_rows,full_dma_replay=replay,per_field_vram_replay=True,ready_residency_source_oracle=True,unsafe_ppu_operations=0,resource_faults=0,deferred_at_ready_retained=any(e['data'][0]=='NbReady' and int(e['data'][1])==1 for e in phases),incomplete_queue_deferral=contract.get('injected_fault_mode',1)==2,stale_epoch_rejection=contract.get('injected_fault_mode',1)==3,left_rejected_retained=True,source_snapshots_identical=True,fields_receipt=str(folder/'fields.json'),services='Legacy NMI/audio/video service is withdrawn by the retained isolated source fixture. Minimal owned NMI services only $4210; NMI disabled during native preparation/preload/commit, auto-JOY restored when idle. No audio timing claim.',nonclaims=['30 FPS','general consecutive-frame capacity','full-world traversal','authored audio scheduling','MOTU Demo'])
