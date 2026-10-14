"""Native A/B evidence for direct pair DMA, including independent full replay."""
import hashlib
import json
from pathlib import Path
import re
import numpy as np
from m4_input_controller_native import offset

BASE=Path('out/byor-motu-tile-fusion-v2')
BASE_SHA='01b757d34ec1ad568758d325678b63bb96ad2f5b87badedae4ee65e1ac711977'


def audit_rom(rom,contract):
    old=(BASE/'native/bor.sfc').read_bytes();sy=contract['native_symbols']
    if hashlib.sha256(old).hexdigest()!=BASE_SHA:raise ValueError('DIRECT_CONTROL_IDENTITY')
    start=sy['WarmDirectPair'];end=sy['OnlineDmaDone9']+3
    if start!=0x39d400 or not start<sy['OnlineDmaDone8']<sy['OnlineDmaDone9']<end<=0x39e000:raise ValueError('DIRECT_CODE_PLACEMENT')
    a,b=offset(start),offset(end)
    if any(old[a:b]):raise ValueError('DIRECT_CODE_LEASE_OCCUPIED')
    oldcall=bytes.fromhex('2050d0');newcall=b'\x20'+(start&65535).to_bytes(2,'little')
    bank=57*32768;sites=[bank+m.start() for m in re.finditer(re.escape(oldcall),old[bank:bank+32768])]
    if len(sites)!=2:raise ValueError('DIRECT_CALLSITE_IDENTITY')
    expected=bytearray(old);expected[a:b]=rom[a:b]
    for at in sites:
        if rom[at:at+3]!=newcall:raise ValueError('DIRECT_CALLSITE_PATCH')
        expected[at:at+3]=newcall
    if rom!=expected:raise ValueError('DIRECT_UNRELATED_ROM_CHANGE')
    return dict(start=start,end=end,bytes=end-start,baseline_lease_zero=True,changed_calls=sites,
                all_other_rom_bytes_identical=True,reference_row_kernel_unchanged=True,fused_tile_kernel_unchanged=True,
                sha256=hashlib.sha256(rom[a:b]).hexdigest())


def append_observer(f,fs,rom):
    f.write('local directActive=false;local directStart=0;local directCalls=0;local directClocks=0;local directDma=0;local directDmaStart=0;local stageCalls=0;local flushCalls=0\n')
    def callback(at,body):f.write(f'emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n')
    callback(fs['WarmDirectPair'],'directActive=true;directStart=clock()')
    callback(fs['WarmStage'],'stageCalls=stageCalls+1')
    callback(fs['WarmFlush'],'flushCalls=flushCalls+1')
    needle=b'\x20'+(fs['WarmDirectPair']&65535).to_bytes(2,'little')
    for match in re.finditer(re.escape(needle),rom[57*32768:58*32768]):
        callback(0x398000+match.start()+3,'if directActive then directClocks=directClocks+clock()-directStart;directCalls=directCalls+1;directActive=false end')
    f.write("emu.addMemoryCallback(function()if directActive then directDmaStart=clock()end end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)\n")
    for name in ('OnlineDmaDone8','OnlineDmaDone9'):
        callback(fs[name]+2,'if directActive then directDma=directDma+clock()-directDmaStart end')
    for name in ('OnlineComplete','OnlineNoopComplete'):
        callback(fs[name],"emu.log('ONLINE_DIRECT|'..directCalls..'|'..directClocks..'|'..directDma..'|'..stageCalls..'|'..flushCalls);directCalls=0;directClocks=0;directDma=0;stageCalls=0;flushCalls=0")


def certify(folder,result):
    old=json.loads((BASE/'result.json').read_text());pairs=[]
    if (result['verified_epochs'],result['verified_pixels'],result['pixel_mismatches'],result['unsafe_register_writes'],result['resource_faults'])!=(18,1032192,0,0,0):raise ValueError('DIRECT_NATIVE_CORRECTNESS')
    audit_rom((folder/'native/bor.sfc').read_bytes(),result['contract'])
    def blanks(path):
        times={};epoch=-1;start=None
        for e in json.loads(path.read_text()):
            if e['phase']=='OnlinePublish':epoch+=1;start=None
            elif e['phase']=='INIDISP:128' and start is None:start=e['clock']
            elif e['phase']=='INIDISP:15':times[epoch]=e['clock']-start
        return times
    before_blank=blanks(BASE/'native/timing-events.json');after_blank=blanks(folder/'native/timing-events.json')
    initial_old=(BASE/'native/initial-vram.bin').read_bytes();initial_new=(folder/'native/initial-vram.bin').read_bytes()
    packets=json.loads((folder/'native/dma-packets.json').read_text());written=np.zeros(65536,dtype=bool);hz=21477270
    for i,(before,after) in enumerate(zip(old['measured_costs']['epochs'],result['measured_costs']['epochs'],strict=True)):
        for name in ('world','directory','cgram','expected'):
            ext='rgb555' if name=='expected' else 'bin'
            if (folder/f'native/{name}-{i:02d}.{ext}').read_bytes()!=(BASE/f'native/{name}-{i:02d}.{ext}').read_bytes():raise ValueError('DIRECT_CONTROL_DRIFT:'+name)
        batch=[p for p in packets if p['epoch']==i]
        for p in batch:
            if p['target']==0x18:written[p['vram_word']*2:p['vram_word']*2+p['bytes']]=True
        av=(BASE/f'native/vram-{i:02d}.bin').read_bytes();bv=(folder/f'native/vram-{i:02d}.bin').read_bytes()
        refs=np.frombuffer((folder/f'native/directory-{i:02d}.bin').read_bytes(),dtype='<u2')
        differences=np.flatnonzero(np.frombuffer(av,dtype='u1')!=np.frombuffer(bv,dtype='u1'))
        for at in differences:
            slot=int(at)//64 if at<49152 else (int(at)-49152)//16
            if at>=61440 or written[at] or refs[slot]&0x3fff or av[at]!=initial_old[at] or bv[at]!=initial_new[at]:raise ValueError('DIRECT_RESIDENT_VRAM_DRIFT')
        if result['observations'][i]['dirty_tiles']!=old['observations'][i]['dirty_tiles']:raise ValueError('DIRECT_ADMISSION_DRIFT')
        d=result['direct_measurements'][i];noop=bool(after.get('render_noop'))
        direct=[p for p in batch if p['source'] in (0x42d680,0x42d6c0)]
        if d['stage_calls'] or len(direct)!=2*d['calls']:raise ValueError('DIRECT_STAGE_OR_FENCE_COUNTS')
        for high,low in zip(direct[::2],direct[1::2],strict=True):
            if (high['source'],high['bytes'],low['source'],low['bytes'])!=(0x42d680,64,0x42d6c0,16) or low['vram_word']!=0x6000+high['vram_word']//4:raise ValueError('DIRECT_PAIR_DESCRIPTOR')
        if any(p['source'] in (0x42c800,0x42cc00) for p in batch):raise ValueError('DIRECT_STAGING_TRANSFER')
        if after['dma_bytes']!=before['dma_bytes']:raise ValueError('DIRECT_BYTE_COUNT_DRIFT')
        if bool(before.get('render_noop'))!=noop or (noop and (d['calls'] or d['flush_calls'] or after['dma_bytes'] or i in after_blank)):raise ValueError('DIRECT_NOOP_WORK')
        def measurements(c,blank):
            clocks={k:c.get(k+'_clocks',0) for k in ('composition','production','publication','dma','preflight_and_allocation')}
            clocks['other_production']=clocks['production']-clocks['composition']-clocks['dma']-clocks['preflight_and_allocation'];clocks['forced_blank']=blank
            return dict(clocks=clocks,ms={k:v*1000/hz for k,v in clocks.items()},dma_bytes=c['dma_bytes'],dma_descriptors=c['dma_transfers'])
        pairs.append(dict(epoch=i,render_noop=noop,before=measurements(before,before_blank.get(i,0)),after=measurements(after,after_blank.get(i,0)),direct=d,untouched_unreferenced_boot_bytes=len(differences)))
    if result['negative']!=old['negative']:raise ValueError('DIRECT_REJECTION_DRIFT')
    warm=[p for p in pairs[1:] if not p['render_noop']]
    before_max={k:max(p['before']['ms'][k] for p in warm) for k in warm[0]['before']['ms']};after_max={k:max(p['after']['ms'][k] for p in warm) for k in warm[0]['after']['ms']}
    faster=after_max['production']<before_max['production']*.95 and after_max['publication']<before_max['publication'] and all(p['after']['ms']['production']<p['before']['ms']['production'] for p in warm)
    return dict(status='PASS' if faster else 'NO_SPEEDUP',classification='BYOR_MOTU_DIRECT_PAIR_DMA_PASS' if faster else 'DIRECT_PAIR_DMA_NO_SPEEDUP',
                paired_epochs=pairs,warm_worst_before_ms=before_max,warm_worst_after_ms=after_max,
                publication_reduction_percent=100*(1-after_max['publication']/before_max['publication']),
                meaningful_gate='At least 5% lower worst warm production, lower worst publication, and faster production in every changing warm epoch',
                boundaries='Direct routine entry through actual caller return fetch. Exclusive CPU/bus-active = inclusive minus its two DMA fence intervals; no nested callees, NMI disabled. DMA fence includes first post-DMA instruction, consistent with the retained control.')
