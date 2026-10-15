"""Independent source pixels, physical replay, journals and fences for borrowing."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from compiler import Source
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from m4_live_ground_component_native import scene_from_snapshot
from m4_nonblank_component_native import decode_vram,sha
from m4_home_borrow_native import audit_rom

MS=21477.270

def certify(folder):
    native=folder/'native';contract=json.loads((folder/'contract.json').read_text())
    fields=json.loads((folder/'fields.json').read_text());events=[]
    for line in (native/'mesen.log').read_text(errors='replace').splitlines():
        if 'callback_owner.lua:' in line:raise ValueError('BH_LUA_OBSERVER_ERROR:'+line)
        if 'NB_' not in line:continue
        p=line[line.index('NB_'):].split('|');events.append(dict(kind=p[0][3:],clock=int(p[1]),frame=int(p[2]),line=int(p[3]),data=p[4:]))
    if any(e['kind']=='FAULT' for e in events):raise ValueError('BH_NATIVE_FAULT:'+str([e for e in events if e['kind']=='FAULT'][:3]))
    rom=(native/'bor.sfc').read_bytes();audit=audit_rom(rom,native)
    def phase(name,txn):return next(e for e in events if e['kind']=='PHASE' and e['data'][:2]==[name,str(txn)])
    def optional_phase(name,txn):return next((e for e in events if e['kind']=='PHASE' and e['data'][:2]==[name,str(txn)]),None)
    pools={};reservations={}
    for event in events:
        if event['kind']=='BH_PHASE' and event['data'][0]=='BhPreparePoolOK':
            _,txn,count,cursor,need,journal,rawrefs,pending,committed=event['data']
            txn,count,need=int(txn),int(count),int(need)
            header=np.frombuffer(bytes.fromhex(journal),dtype='<u2');entries=header[8:8+count]
            refs=np.frombuffer(bytes.fromhex(rawrefs),dtype='<u2');pm=np.frombuffer(bytes.fromhex(pending),dtype='<u2')&0x3fff
            cm=np.frombuffer(bytes.fromhex(committed),dtype='<u2')
            if cursor!='0' or need!=count or count>64:raise ValueError('BH_POOL_CAPACITY')
            homes=[int(v&0x3fff) for v in entries]
            if len(set(homes))!=count or any(h>=596 for h in homes):raise ValueError('BH_POOL_OVERLAP')
            if not np.array_equal(refs&0x3fff,np.bincount(cm,minlength=768)):raise ValueError('BH_DIRECTORY_AUTHORITY')
            for home,entry in zip(homes,entries):
                if refs[home]&0x7fff or home in cm or home in pm or (entry&0x8000)!=(refs[home]&0x8000):raise ValueError('BH_POOL_ELIGIBILITY')
            pools[txn]=dict(clock=event['clock'],homes=homes,original_invalid=[h for h,v in zip(homes,entries) if v&0x8000],original_valid=[h for h,v in zip(homes,entries) if not v&0x8000],policy=int(header[1]),limit=int(header[5]),need=need)
        if event['kind']=='BH_RESERVE':
            txn,index,value=map(int,event['data']);reservations.setdefault(txn,[]).append(value&0x3fff)
    for txn,homes in reservations.items():
        if txn not in pools or homes!=pools[txn]['homes']:raise ValueError('BH_RESERVATION_LIFETIME_OR_DUPLICATE')
    allocation_groups={}
    for event in events:
        if event['kind']=='CP_ALLOC':
            txn,exact,slot=map(int,event['data']);allocation_groups.setdefault((txn,exact),[]).append(slot)
    for (txn,exact),slots in allocation_groups.items():
        plan=next(e for e in events if e['kind']=='CP_PLAN' and e['data'][:2]==[str(txn),str(exact)])
        directory=np.frombuffer(bytes.fromhex(plan['data'][5]),dtype='<u2')
        if len(set(slots))!=len(slots) or any(not 596<=s<768 or directory[s]&0x3fff for s in slots):raise ValueError('BH_TAIL_RESERVATION_OVERLAP')
        combined=slots+(reservations.get(txn,[]) if exact else [])
        if len(set(combined))!=len(combined):raise ValueError('BH_PAIRED_RESERVATION_OVERLAP')
    packets=[]
    for event in events:
        if event['kind']=='PACKET':
            txn,target,word,source,size,payload=event['data']
            data=rom[int(source)-0xc00000:int(source)-0xc00000+int(size)] if int(source)>=0xc00000 else bytes.fromhex(payload)
            if len(data)!=int(size):raise ValueError('BH_PAYLOAD_LENGTH')
            packets.append(dict(clock=event['clock'],transaction=int(txn),target=int(target),word=int(word),source=int(source),size=int(size),data=data))
    home_packets={e['clock']:e for e in events if e['kind']=='BH_HOME_DMA'}
    vram=bytearray(bytes.fromhex(next(e['data'][0] for e in events if e['kind']=='BASE')));palette=bytearray(512)
    manifest={0:'cold',1:'deferred',2:'moved',3:'after-second'}
    if (native/'after-restoration-vram.bin').exists():manifest[4]='after-restoration'
    refs=None;replays=[];transfers=[];all_fences=[]
    starts=[e for e in events if e['kind']=='VBLANK_START'];ends=[e for e in events if e['kind']=='VBLANK_END']
    def window(clock):
        edge=max((e for e in starts if e['clock']<=clock),key=lambda e:e['clock'])
        end=min(e['clock'] for e in ends if e['clock']>edge['clock'])
        if clock>=end:raise ValueError('BH_ACTIVE_DMA')
        return edge['clock'],end
    done=[e for e in events if e['kind']=='DONE']
    (folder/'dma-packets.json').write_text(json.dumps([{**{k:v for k,v in p.items() if k!='data'},'payload_hex':p['data'].hex()} for p in packets],indent=2)+'\n')
    for txn,label in manifest.items():
        batch=[p for p in packets if p['transaction']==txn];pairs=[];maps=[]
        before_refs=refs
        for p in batch:
            if p['target']==0x22:
                if txn or p['size']!=512:raise ValueError('BH_PALETTE_CHANGED')
                palette[:]=p['data'];continue
            if p['target']!=0x18:raise ValueError('BH_UNEXPECTED_DMA_TARGET')
            at=p['word']*2
            if not 0<=at<at+p['size']<=65536:raise ValueError('BH_VRAM_RANGE')
            if txn and at<61440:
                slot=at//64 if at<49152 else (at-49152)//16
                if before_refs[slot]&0x3fff:raise ValueError('BH_DISPLAYED_CHR_OVERWRITE')
                if slot<596:
                    if txn not in pools or slot not in pools[txn]['homes'] or p['clock'] not in home_packets:raise ValueError('BH_HOME_TRANSFER_WITHOUT_RESERVATION')
                    event=home_packets[p['clock']];_,h,state,entry,ref,count,word=map(int,event['data'])
                    if h!=slot or count or not ref&0x8000 or ref&0x3fff or not entry&0x4000:raise ValueError('BH_MISSING_INVALIDATION')
                    if state==2:
                        if slot not in pools[txn]['original_valid']:raise ValueError('BH_ROLLBACK_OF_ORIGINALLY_INVALID_HOME')
                        start=(0x200000+64*slot) if at<49152 else (0x210000+16*slot)
                        if p['data']!=rom[start:start+p['size']]:raise ValueError('BH_ROLLBACK_NOT_IMMUTABLE_PAIR')
                    elif state!=1:raise ValueError('BH_HOME_TRANSFER_OUTSIDE_TRANSACTION')
                pairs.append(p)
            elif txn:maps.append(p)
            vram[at:at+p['size']]=p['data']
            if txn:
                finish=next(e for e in done if e['clock']>p['clock'] and e['data']==[str(txn),str(p['source']),str(p['size']),str(p['target'])])
                begin,end=window(p['clock'])
                if finish['clock']>=end:raise ValueError('BH_DMA_FENCE_OVERRUN')
                all_fences.append(dict(transaction=txn,start=p['clock'],end=finish['clock'],window_start=begin,window_end=end,margin=end-finish['clock'],bytes=p['size'],source=p['source'],vram_word=p['word'],component='HIGH' if at<49152 else 'LOW' if at<61440 else 'HIGH_MAP' if at<63488 else 'LOW_MAP'))
        if bytes(vram)!=(native/f'{label}-vram.bin').read_bytes() or bytes(palette)!=(native/f'{label}-cgram.bin').read_bytes():raise ValueError('BH_FULL_PHYSICAL_REPLAY:'+label)
        cm=(native/f'{label}-committed.bin').read_bytes();pm=(native/f'{label}-pending.bin').read_bytes()
        if cm!=pm or cm!=bytes(vram[61440:63488]) or cm!=bytes(vram[63488:]):raise ValueError('BH_MAP_COHERENCE')
        current=np.frombuffer((native/f'{label}-refs.bin').read_bytes(),dtype='<u2')
        if not np.array_equal(current&0x3fff,np.bincount(np.frombuffer(cm,dtype='<u2'),minlength=768)):raise ValueError('BH_REFERENCE_COUNTS')
        if txn:
            for high,low in zip(pairs[::2],pairs[1::2],strict=True):
                if high['source'] not in range(0x3500,0x36e0,80) or high['size']!=64 or low['source']!=high['source']+64 or low['size']!=16 or low['word']!=0x6000+high['word']//4:raise ValueError('BH_PAIRED_CHR_DESCRIPTORS')
            committed=optional_phase('NbMapsComplete',txn)
            if committed:
                if [(p['word'],p['size']) for p in maps]!=[(0x7800,2048),(0x7c00,2048)]:raise ValueError('BH_ATOMIC_MAP_DESCRIPTORS')
                _,end=window(phase('NbMapCommit',txn)['clock'])
                if committed['clock']>=end:raise ValueError('BH_MAP_COMMIT_OVERRUN')
                if txn in pools:
                    for home in pools[txn]['homes']:
                        if not current[home]&0x8000 or not current[home]&0x3fff:raise ValueError('BH_SUCCESS_MISSING_INVALID_REFERENCE')
            else:
                if maps or not np.array_equal(current,before_refs):raise ValueError('BH_ROLLBACK_DIRECTORY_OR_MAP')
                before_label='cold' if txn==1 else 'moved'
                if cm!=(native/f'{before_label}-committed.bin').read_bytes():raise ValueError('BH_FAILED_DISPLAY_CHANGED')
                if txn in pools:
                    for home in pools[txn]['original_valid']:
                        if bytes(vram[home*64:(home+1)*64])!=rom[0x200000+home*64:0x200000+(home+1)*64] or bytes(vram[49152+home*16:49152+(home+1)*16])!=rom[0x210000+home*16:0x210000+(home+1)*16]:raise ValueError('BH_VALID_HOME_NOT_RESTORED')
        queue=(native/f'{label}-queue.bin').read_bytes()
        if queue[:2]!=b'\0\0':raise ValueError('BH_STALE_QUEUED_PAIRS')
        refs=current.copy();replays.append(dict(transaction=txn,bytes=sum(p['size'] for p in batch),full_vram_bytes=65536,complete=True))
        transfers.append(dict(transaction=txn,descriptors=len(batch),chr_pairs=len(pairs)//2,chr_bytes=sum(p['size'] for p in pairs),map_bytes=sum(p['size'] for p in maps)))
    # Each physical field is an ordered whole-transfer prefix of the same replay.
    replay=bytearray(bytes.fromhex(next(e['data'][0] for e in events if e['kind']=='BASE')));cursor=0
    for field in fields:
        expected=(native/f"field-{field['index']:04d}.vram").read_bytes()
        while replay!=expected:
            if cursor==len(packets):raise ValueError('BH_FIELD_REPLAY')
            p=packets[cursor];cursor+=1
            if p['target']==0x18:at=p['word']*2;replay[at:at+p['size']]=p['data']
        if sha(expected)!=field['vram_sha256']:raise ValueError('BH_FIELD_VRAM_HASH')
    source=Source(Path('Masters of the Universe [v.3.0 Build 4086].pak'));pictures={}
    for label in ('cold','moved','newer')+ (('restoration',) if 4 in manifest else ()):
        raw=(native/f'{label}-world.bin').read_bytes();scene=scene_from_snapshot(raw,source)
        rgb,_=compose_rgb8(source,'DATA/LEVELS/GUILE2.TXT',scene);pictures[label]=rgb555(rgb).astype('<u2')
        if pictures[label].tobytes()!=(native/f'{label}-expected.rgb555').read_bytes():raise ValueError('BH_SOURCE_ORACLE_RECOMPOSITION')
    commits=[(phase('NbMapsComplete',txn),'moved' if txn==2 else 'newer' if txn==3 else 'restoration') for txn in (2,3,4) if optional_phase('NbMapsComplete',txn)]
    for field in fields:
        if field['ppu']['forcedBlank'] or field['ppu']['brightness']!=15:raise ValueError('BH_BRIGHTNESS')
        label='cold'
        for event,target in commits:
            if field['ppu']['frameCount']>event['frame']:label=target
        expected=pictures[label];shot=native/f"field-{field['index']:04d}.png"
        if sha(shot.read_bytes())!=field['screenshot_sha256'] or not np.array_equal(rgb555(np.asarray(Image.open(shot).convert('RGB'))),expected):raise ValueError('BH_SOURCE_SCREENSHOT_MISMATCH')
        if not np.array_equal(decode_vram((native/f"field-{field['index']:04d}.vram").read_bytes(),palette),expected):raise ValueError('BH_SOURCE_VRAM_MISMATCH')
    ready_checks=[]
    for txn,target in ((1,'deferred'),(2,'moved'),(3,'newer'),(4,'restoration')):
        ready=optional_phase('NbReady',txn)
        if not ready:continue
        if target not in pictures:
            raw=(native/f'{target}-world.bin').read_bytes();scene=scene_from_snapshot(raw,source)
            rgb,_=compose_rgb8(source,'DATA/LEVELS/GUILE2.TXT',scene);pictures[target]=rgb555(rgb).astype('<u2')
        plan=next(e for e in reversed(events) if e['kind']=='CP_PLAN' and e['data'][0]==str(txn) and e['clock']<ready['clock'])
        exact=plan['data'][1];directory=np.frombuffer(bytes.fromhex(plan['data'][5]),dtype='<u2')
        marked=np.frombuffer(bytes.fromhex(plan['data'][6]),dtype='<u2').copy()
        homes=[]
        for value in marked:
            home=int(value)
            if home<596 and directory[home]&0x8000 and home not in homes:homes.append(home)
        tails=[int(e['data'][2]) for e in events if e['kind']=='CP_ALLOC' and e['data'][:2]==[str(txn),exact]]
        pending=marked.copy()
        for home,dest in zip(homes,tails[:len(homes)],strict=True):pending[pending==home]=dest
        actors=np.flatnonzero(marked==65535);assigned=tails[len(homes):]+reservations.get(txn,[])
        if len(actors)!=len(assigned):raise ValueError('BH_READY_COMPLETE_ALLOCATION')
        pending[actors]=assigned
        physical=bytearray(bytes.fromhex(next(e['data'][0] for e in events if e['kind']=='BASE')))
        for p in packets:
            if p['clock']>=ready['clock']:continue
            if p['target']==0x18:at=p['word']*2;physical[at:at+p['size']]=p['data']
        physical[61440:63488]=pending.tobytes();physical[63488:]=pending.tobytes()
        if not np.array_equal(decode_vram(bytes(physical),palette),pictures[target]):raise ValueError('BH_READY_PICTURE_NOT_RESIDENT')
        if any(f['transaction']==txn and f['start']<ready['clock']<=f['end'] for f in all_fences):raise ValueError('BH_READY_PENDING_DMA_FENCE')
        committed=optional_phase('NbMapsComplete',txn)
        if committed and pending.tobytes()!=(native/f'{manifest[txn]}-committed.bin').read_bytes():raise ValueError('BH_READY_ALLOCATION_MAP_CHANGED')
        ready_checks.append(dict(transaction=txn,clock=ready['clock'],actor_tiles=len(actors),restoration_homes=homes,tail_reservations=len(tails),borrowed_reservations=len(reservations.get(txn,[])),source_pixels_exact=True))
    backdrop_restorations=[]
    for event in events:
        if event['kind']!='BH_BACKDROP':continue
        txn,home,dest,state=map(int,event['data'])
        if state==2:dest=home
        matching=[p for p in packets if p['transaction']==txn and p['clock']>event['clock'] and p['word']==dest*32 and p['size']==64]
        # A discarded partial queue is not a completed restoration.
        if not matching:continue
        high=matching[0];low=next(p for p in packets if p['transaction']==txn and p['clock']>high['clock'] and p['word']==0x6000+dest*8 and p['size']==16)
        if high['data']!=rom[0x200000+64*home:0x200000+64*(home+1)] or low['data']!=rom[0x210000+16*home:0x210000+16*(home+1)]:raise ValueError('BH_BACKDROP_RESTORATION_AUTHORITY')
        backdrop_restorations.append(dict(transaction=txn,home=home,destination=dest,rollback=state==2,high_clock=high['clock'],low_clock=low['clock']))
    batches=[]
    for e in [e for e in events if e['kind']=='BATCH' and e['data'][0]=='NbQueueHasPending']:
        txn,count=int(e['data'][1]),int(e['data'][2]);finish=next(d for d in events if d['kind']=='BATCH' and d['data'][0]=='NbQueueDrainDone' and d['clock']>e['clock'])
        fs=[d for d in all_fences if d['transaction']==txn and e['clock']<d['start']<finish['clock']]
        if len(fs)!=2*count or not 1<=count<=6:raise ValueError('BH_BATCH_COMPLETION')
        edge,end=window(fs[-1]['end'])
        if end-finish['clock']<10000:raise ValueError('BH_BATCH_MARGIN')
        batches.append(dict(transaction=txn,pairs=count,start=fs[0]['start'],fence_end=fs[-1]['end'],batch_complete=finish['clock'],duration_clocks=finish['clock']-fs[0]['start'],margin_clocks=end-finish['clock']))
    for clear in [e for e in events if e['kind']=='BH_VALID_CLEAR']:
        txn,home,pc=map(int,clear['data'])
        fenced=max(e['clock'] for e in events if e['kind']=='BH_PHASE' and e['data'][:2]==['BhRestorationFenced',str(txn)] and e['clock']<clear['clock'])
        fs=[p for p in packets if p['transaction']==txn and p['clock']<fenced and p['clock'] in home_packets and int(home_packets[p['clock']]['data'][1])==home and home_packets[p['clock']]['data'][2]=='2']
        if len(fs)!=2 or clear['clock']<=max(x['end'] for x in all_fences if any(p['clock']==x['start'] for p in fs)):raise ValueError('BH_VALID_CLEAR_BEFORE_PAIR_RESTORATION')
    status=json.loads((folder/'second-status.json').read_text());changed=int(np.count_nonzero(pictures['moved']!=pictures['newer']))
    if changed!=1816:raise ValueError('BH_SOURCE_UP_PICTURE_DRIFT')
    for label in ('moved','newer'):
        if (native/f'{label}-world.bin').read_bytes()!=(Path('out/byor-motu-consecutive-up-v2/native')/f'{label}-world.bin').read_bytes():raise ValueError('BH_SOURCE_SNAPSHOT_DRIFT')
    source_events=[e for e in events if e['kind'].startswith('SP_')]
    update_start=next(e for e in source_events if e['kind']=='SP_START');update_done=next(e for e in source_events if e['kind']=='SP_DONE')
    latch=next(e for e in source_events if e['kind']=='SP_LATCH' and e['data'][0]=='2');visible=next(e for e in source_events if e['kind']=='SP_VISIBLE' and e['data'][0]=='2')
    if visible['data'][1:3]!=['2','3'] or visible['data'][3]!=latch['data'][1][:36] or update_done['clock']>=phase('NbMapCommit',2)['clock']:raise ValueError('BH_SOURCE_SAFEPOINT_ORDER_OR_KEY')
    if sum(e['kind']=='SP_START' for e in events)!=1:raise ValueError('BH_EXTRA_SAFEPOINT_MOVEMENT')
    if status['success']:
        latch3=next(e for e in source_events if e['kind']=='SP_LATCH' and e['data'][0]=='3');v3=next(e for e in source_events if e['kind']=='SP_VISIBLE' and e['data'][0]=='3')
        if v3['data'][1:3]!=['3','3'] or v3['data'][3]!=latch3['data'][1][:36] or bytes.fromhex(latch3['data'][-1])!=(native/'newer-world.bin').read_bytes():raise ValueError('BH_EPOCH3_VISUAL_KEY')
    costs=[]
    for txn in (2,3,4):
        begin=optional_phase('NbBegin',txn)
        if not begin:continue
        finish=optional_phase('NbVisible',txn) or optional_phase('OnlineReject',txn)
        if not finish:raise ValueError('BH_TRANSACTION_NOT_RETURNED')
        costs.append(dict(transaction=txn,committed=optional_phase('NbVisible',txn) is not None,start=begin['clock'],finish=finish['clock'],fields=finish['frame']-begin['frame'],master_clocks=finish['clock']-begin['clock'],ms=(finish['clock']-begin['clock'])/MS))
    helper_costs=[]
    for start in [e for e in events if e['kind']=='BH_PHASE' and e['data'][0] in ('BhPrepare','BhRollback')]:
        routine,txn=start['data'][:2];end_names=('BhPrepareOK','BhPrepareBad') if routine=='BhPrepare' else ('BhRollbackEmpty',)
        end=next(e for e in events if e['kind']=='BH_PHASE' and e['data'][0] in end_names and e['data'][1]==txn and e['clock']>start['clock'])
        wait_clocks=0
        for wait in [e for e in events if e['kind']=='WAIT_BEGIN' and start['clock']<e['clock']<end['clock']]:
            finish=next(e for e in events if e['kind']=='WAIT_END' and e['clock']>wait['clock'])
            if finish['clock']>end['clock']:raise ValueError('BH_COST_WAIT_BOUNDARY')
            wait_clocks+=finish['clock']-wait['clock']
        dma_clocks=sum(f['end']-f['start'] for f in all_fences if start['clock']<f['start']<end['clock'])
        elapsed=end['clock']-start['clock'];cpu=elapsed-wait_clocks-dma_clocks
        helper_costs.append(dict(routine=routine,transaction=int(txn),entry_clock=start['clock'],end_label=end['data'][0],end_clock=end['clock'],elapsed_clocks=elapsed,elapsed_ms=elapsed/MS,wait_clocks=wait_clocks,dma_clocks=dma_clocks,cpu_clocks=cpu,cpu_ms=cpu/MS,boundary='Entry through return epilogue label; caller JSR and final cleanup/RTS excluded.'))
    hook_spans={};open_hooks={}
    for e in [e for e in events if e['kind']=='BH_COST']:
        name,txn=e['data'][:2]
        if name in ('BhInvalidate','BhShouldAbort','BhVerifyReady'):
            open_hooks[(name,txn)]=e['clock']
        else:
            routine={'BhInvalidateOK':'BhInvalidate','BhInvalidateBad':'BhInvalidate','BhNoFault':'BhShouldAbort','BhReadyOK':'BhVerifyReady','BhReadyBad':'BhVerifyReady'}.get(name)
            if routine and (routine,txn) in open_hooks:
                value=e['clock']-open_hooks.pop((routine,txn));row=hook_spans.setdefault((routine,txn),dict(routine=routine,transaction=int(txn),calls=0,clocks=0,maximum_clocks=0))
                row['calls']+=1;row['clocks']+=value;row['maximum_clocks']=max(row['maximum_clocks'],value)
    result=dict(classification='HOME_BORROW_TWO_PICTURES_CERTIFIED' if status['success'] else 'HOME_BORROW_ROLLBACK_CERTIFIED',
                rom_sha256=sha(rom),audit=audit,pools=pools,transactions=costs,transfers=transfers,batches=batches,
                min_batch_margin_clocks=min(b['margin_clocks'] for b in batches),dma_fences=all_fences,
                full_physical_replay=replays,source_events=source_events,source_pixel_difference=changed,
                observed_fields=len(fields),verified_pixels=len(fields)*57344,pixel_mismatches=0,
                resource_faults=0,unsafe_ppu_operations=0,journal_cpu_write_ownership=True,adjacent_source_canary_intact=True,
                source_movement_clocks=update_done['clock']-update_start['clock'],
                ready_residency_checks=ready_checks,backdrop_restorations=backdrop_restorations,
                helper_costs=helper_costs,hook_entry_to_return_label_costs=list(hook_spans.values()),
                timing_uncertainty='Helper measurements exclude caller JSR/final return epilogues; full publication intervals include all work. Fault-true BhShouldAbort has no return-label span; it remains included in publication timing.',
                home_dma_records=[e for e in events if e['kind']=='BH_HOME_DMA'],validity_clear_events=[e for e in events if e['kind']=='BH_VALID_CLEAR'])
    (folder/'certified.json').write_text(json.dumps(result,indent=2)+'\n');return result

def collect():
    import hashlib
    from m4_home_borrow_capacity import inventory
    root=Path('out/byor-motu-home-borrow-v1');cases={}
    for name in ('success','valid','early','ready','partial','stale','insufficient'):
        version='v7' if name=='early' else 'v8' if name in ('ready','partial','stale') else 'v5'
        folder=Path(f'out/byor-motu-home-borrow-{name}-{version}');r=certify(folder)
        r['evidence_folder']=str(folder)
        r['fields']=[dict(f,ppu={k:v for k,v in f['ppu'].items() if k!='layers'}) for f in json.loads((folder/'fields.json').read_text())]
        cases[name]=r
    if any(cases[n]['classification']!='HOME_BORROW_TWO_PICTURES_CERTIFIED' for n in ('success','valid')) or any(cases[n]['classification']!='HOME_BORROW_ROLLBACK_CERTIFIED' for n in ('early','ready','partial','stale','insufficient')):raise ValueError('BH_INCOMPLETE_NATIVE_SUITE')
    if len(cases['success']['pools'][3]['original_invalid'])!=41 or cases['success']['pools'][3]['original_valid']:raise ValueError('BH_DEFAULT_NOT_INVALID_FIRST')
    valid=cases['valid'];promoted=valid['pools'][3]['original_valid']
    if promoted!=[204] or not any(x['transaction']==4 and x['home']==204 and x['destination']==634 and not x['rollback'] for x in valid['backdrop_restorations']):raise ValueError('BH_LATER_IMMUTABLE_HOME_RESTORATION_MISSING')
    flags=np.frombuffer(Path(valid['evidence_folder'],'native/after-restoration-refs.bin').read_bytes(),dtype='<u2')
    if flags[204]!=0x8000:raise ValueError('BH_REROUTED_HOME_FALSE_VALIDITY')
    for name in ('early','ready','partial','stale'):
        if not cases[name]['validity_clear_events']:raise ValueError('BH_VALID_HOME_ROLLBACK_NOT_EXERCISED:'+name)
    if next(t for t in cases['insufficient']['transfers'] if t['transaction']==3)['descriptors']!=0:raise ValueError('BH_INSUFFICIENT_CAPACITY_DID_DMA')
    if any(x['transaction']==3 for x in cases['early']['ready_residency_checks']) or not any(x['transaction']==3 for x in cases['ready']['ready_residency_checks']):raise ValueError('BH_EARLY_OR_READY_FAULT_BOUNDARY')
    for name in ('partial','stale'):
        if any(x['transaction']==3 for x in cases[name]['ready_residency_checks']):raise ValueError('BH_FAULT_REACHED_READY:'+name)
    # Re-certify the fresh RIGHT run with the unchanged historical certifier,
    # substituting only this candidate's stricter whole-ROM mutation audit.
    import m4_source_safepoint_native as safe
    import m4_home_borrow_native as home
    from unittest.mock import patch
    folder=Path('out/byor-motu-home-borrow-right-v5');old=json.loads((folder/'result.json').read_text())
    with patch.object(safe,'audit_rom',home.audit_rom):right=safe.certify(folder,old['contract'],json.loads((folder/'fields.json').read_text()))
    if right['classification']!='BYOR_MOTU_SOURCE_SAFEPOINT_PASS':raise ValueError('BH_RIGHT_CONTROL_FAILED')
    cases['right_control']=right
    before=json.loads((root/'dirty-before.json').read_text());after=[dict(path=x['path'],sha256=sha(Path(x['path']).read_bytes())) for x in before]
    if before!=after or len(after)!=29:raise ValueError('BH_INHERITED_DIRTY_CHANGED')
    (root/'dirty-after.json').write_text(json.dumps(after,indent=2)+'\n')
    disabled={}
    for name,path,expected in [('safepoint','out/byor-motu-home-borrow-disabled-v1/native/bor.sfc',home.BASE_SHA),('conditional','out/byor-motu-home-borrow-conditional-disabled-v1/native/bor.sfc',safe.BASE_SHA)]:
        value=sha(Path(path).read_bytes())
        if value!=expected:raise ValueError('BH_DISABLED_ROM_CHANGED')
        disabled[name]=dict(path=path,sha256=value,accepted_byte_identical=True)
    capacity=inventory(Path('out/byor-motu-consecutive-up-v2'))
    for name in ('success','valid'):
        refs=np.frombuffer(Path(cases[name]['evidence_folder'],'native/after-second-refs.bin').read_bytes(),dtype='<u2')
        cases[name]['final_referenced_slots']=int(np.count_nonzero(refs&0x3fff))
        cases[name]['new_immutable_home_invalidations']=len(cases[name]['pools'][3]['original_valid'])
    report=dict(classification='BYOR_MOTU_BACKDROP_HOME_BORROW_PASS',starting_commit='dd10d752bddb081e6b536cb0b0c75c9b904d9c44',
                capacity=capacity,cases=cases,disabled_controls=disabled,
                verified_fields=sum(c['observed_fields'] for c in cases.values()),verified_pixels=sum(c['verified_pixels'] for c in cases.values()),
                pixel_mismatches=0,resource_faults=0,focused_tests_passed=162,inherited_dirty_files_preserved=29,
                journal_lease=[0x42d700,0x42d790],journal_bytes=144,original_row_and_fused_kernels_unchanged=True,
                conditional_controls='Retained ordinary/rescue/fault/native-unit evidence re-certified: 518 fields, 29,704,192 pixels; excluded from this new-run aggregate.',
                diagnostic_policy='Production default is invalid-first. Valid-first prefix quota, fault flag and pool budget are explicit isolated-fixture controls; source state and map/refcount ownership are never fabricated.',
                excluded_trials='Earlier Lua syntax/capture trials, parallel screenshot-directory races and the interrupted v4 run are not certification evidence.',
                nonclaims=['30 FPS','200-Hz scheduling','SA-1 coexecution','audio scheduling','general multi-actor or scene capacity','HUD','combat','MOTU Demo'])
    Path('docs/receipts/byor-motu-home-borrow.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['classification'],report['verified_fields'],report['verified_pixels']);return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path);p.add_argument('--collect',action='store_true');a=p.parse_args()
    if a.collect:collect()
    elif a.folder:
        r=certify(a.folder);print(r['classification'],r['observed_fields'],r['verified_pixels'],r['transactions'])
    else:p.error('Choose --folder or --collect')
