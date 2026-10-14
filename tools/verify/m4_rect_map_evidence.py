"""Candidate-specific rectangle map audit, native instrumentation and A/B gate."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import numpy as np
from m4_input_controller_native import offset
from m4_rect_map_audit import audit

BASE=Path('out/byor-motu-direct-pair-v1')
CONTROL=Path(os.environ.get('MOTU_RECT_CONTROL','out/byor-motu-rect-control-v1'))


def audit_rom(rom,contract,native):return audit(rom,native,BASE/'native')


def append_observer(f,fs,rom,rectangle):
    f.write("local rectKind='';local rectStart=0;local rectDma=0;local rectDmaStart=0;local rectEpoch=-1\n")
    def cb(at,body):f.write(f'emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n')
    f.write("local function rectBytes(at,n)local t={};for i=0,n-1 do t[#t+1]=string.format('%02x',emu.read(at+i,emu.memType.snesMemory))end;return table.concat(t)end\n")
    f.write("local function rectMaps(name)local b={};for _,at in ipairs({0x3478,0x347a,0x347c,0x347e})do b[#b+1]=emu.read(at,emu.memType.snesMemory)+256*emu.read(at+1,emu.memType.snesMemory)end;emu.log('ONLINE_RECT_MAPS|'..rectEpoch..'|'..name..'|'..table.concat(b,',')..'|'..rectBytes(0x42c000,2048)..'|'..rectBytes(0x42c800,2048))end\n")
    cb(fs['OnlinePublish'],"rectEpoch=rectEpoch+1")
    def start(name):return f"rectKind='{name}';rectStart=clock();rectDma=0"
    def done(name):return f"local span=clock()-rectStart;emu.log('ONLINE_RECT_COST|'..rectEpoch..'|{name}|'..span..'|'..rectDma);rectKind=''"
    cb(fs['WarmSparseMaps'],start('scan')+";rectMaps('before_scan')")
    for match in re.finditer(re.escape(b'\x20'+(fs['WarmSparseMaps']&65535).to_bytes(2,'little')),rom[57*32768:58*32768]):cb(0x398000+match.start()+3,done('scan'))
    if rectangle:
        cb(fs['WarmCommitMapRect'],start('commit')+";rectMaps('before_commit')")
        for match in re.finditer(re.escape(b'\x20'+(fs['WarmCommitMapRect']&65535).to_bytes(2,'little')),rom[57*32768:58*32768]):cb(0x398000+match.start()+3,done('commit'))
    else:
        # Native control's entire late map-copy block (PHB .. PLB), after flush.
        first=offset(fs['OnlineMapsTransfer']);last=offset(fs['OnlineComplete'])
        section=rom[first:last];needle=bytes.fromhex('8ba9ff07a200c0a000c8544242ab')
        if section.count(needle)!=1:raise ValueError('RECT_CONTROL_COMMIT_BOUNDARY')
        cb(fs['OnlineMapsTransfer']+section.index(needle),start('commit')+";rectMaps('before_commit')")
        cb(fs['OnlineComplete'],done('commit'))
    cb(fs['OnlineComplete'],"rectMaps('after_commit')")
    f.write("emu.addMemoryCallback(function()if rectKind~='' then rectDmaStart=clock()end end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)\n")
    cb(fs['OnlineDmaDone7']+2,"if rectKind=='scan' then rectDma=rectDma+clock()-rectDmaStart end")


def parse(folder):
    costs=[];maps=[]
    for line in (folder/'native/mesen.log').read_text(errors='replace').splitlines():
        if 'ONLINE_RECT_COST|' in line:
            p=line.split('ONLINE_RECT_COST|',1)[1].split('|');costs.append(dict(epoch=int(p[0]),routine=p[1],inclusive_clocks=int(p[2]),dma_clocks=int(p[3]),exclusive_clocks=int(p[2])-int(p[3])))
        if 'ONLINE_RECT_MAPS|' in line:
            p=line.split('ONLINE_RECT_MAPS|',1)[1].split('|');maps.append(dict(epoch=int(p[0]),phase=p[1],rect=list(map(int,p[2].split(','))),pending=p[3],committed=p[4]))
    (folder/'map-probes.json').write_text(json.dumps(dict(costs=costs,maps=maps),indent=2)+'\n')
    return costs,maps


def certify(folder,result):
    old=json.loads((CONTROL/'result.json').read_text());costs,maps=parse(folder);oldcosts,oldmaps=parse(CONTROL)
    if (result['verified_epochs'],result['verified_pixels'],result['pixel_mismatches'],result['unsafe_register_writes'],result['resource_faults'])!=(18,1032192,0,0,0):raise ValueError('RECT_NATIVE_CORRECTNESS')
    audit_rom((folder/'native/bor.sfc').read_bytes(),result['contract'],folder/'native')
    from rect_map_opt import rect_runs
    packets=json.loads((folder/'native/dma-packets.json').read_text());oldpackets=json.loads((CONTROL/'native/dma-packets.json').read_text())
    def blank_times(path):
        times={};epoch=-1;start=None
        for e in json.loads(path.read_text()):
            if e['phase']=='OnlinePublish':epoch+=1;start=None
            elif e['phase']=='INIDISP:128' and start is None:start=e['clock']
            elif e['phase']=='INIDISP:15':times[epoch]=e['clock']-start
        return times
    before_blank=blank_times(CONTROL/'native/timing-events.json');after_blank=blank_times(folder/'native/timing-events.json')
    pairs=[];hz=21477270;previous=None
    written=np.zeros(65536,dtype=bool)
    initial_old=(CONTROL/'native/initial-vram.bin').read_bytes();initial_new=(folder/'native/initial-vram.bin').read_bytes()
    for i,(b,a) in enumerate(zip(old['measured_costs']['epochs'],result['measured_costs']['epochs'],strict=True)):
        for name in ('world','directory','cgram','expected'):
            ext='rgb555' if name=='expected' else 'bin'
            if (folder/f'native/{name}-{i:02d}.{ext}').read_bytes()!=(CONTROL/f'native/{name}-{i:02d}.{ext}').read_bytes():raise ValueError('RECT_CONTROL_DRIFT:'+name)
        pending=(folder/f'native/pending-map-{i:02d}.bin').read_bytes();committed=(folder/f'native/committed-map-{i:02d}.bin').read_bytes()
        if pending!=committed or pending!=(CONTROL/f'native/pending-map-{i:02d}.bin').read_bytes():raise ValueError('RECT_MAP_IDENTITY')
        if previous is not None and pending[28*64:]!=previous[28*64:]:raise ValueError('RECT_UNDRAWN_ROWS_CHANGED')
        for packet in packets:
            if packet['epoch']==i and packet['target']==0x18:written[packet['vram_word']*2:packet['vram_word']*2+packet['bytes']]=True
        av=(CONTROL/f'native/vram-{i:02d}.bin').read_bytes();bv=(folder/f'native/vram-{i:02d}.bin').read_bytes()
        refs=np.frombuffer((folder/f'native/directory-{i:02d}.bin').read_bytes(),dtype='<u2')
        differences=np.flatnonzero(np.frombuffer(av,dtype='u1')!=np.frombuffer(bv,dtype='u1'))
        for at in differences:
            slot=int(at)//64 if at<49152 else (int(at)-49152)//16
            if at>=61440 or written[at] or refs[slot]&0x3fff or av[at]!=initial_old[at] or bv[at]!=initial_new[at]:raise ValueError('RECT_RESIDENT_VRAM_DRIFT')
        noop=bool(a.get('render_noop'))
        if noop!=bool(b.get('render_noop')):raise ValueError('RECT_NOOP_DRIFT')
        probe=[p for p in maps if p['epoch']==i]
        mappackets=[p for p in packets if p['epoch']==i and p['source']>=0x42c000 and p['source']<0x42c800]
        if noop:
            if probe or mappackets or a['dma_bytes'] or any(c['epoch']==i for c in costs):raise ValueError('RECT_NOOP_WORK')
        else:
            phases={p['phase']:p for p in probe}
            if set(phases)!=set(('before_scan','before_commit','after_commit')):raise ValueError('RECT_PROBE_BOUNDARIES')
            start=phases['before_scan'];late=phases['before_commit'];end=phases['after_commit']
            if start['pending']!=late['pending'] or start['committed']!=late['committed']:raise ValueError('RECT_EARLY_COMMIT')
            if previous is not None and bytes.fromhex(start['committed'])!=previous:raise ValueError('RECT_COMMITTED_CHANGED_BEFORE_FENCE')
            if bytes.fromhex(end['pending'])!=pending or end['pending']!=end['committed']:raise ValueError('RECT_LATE_COMMIT_IDENTITY')
            old_words=np.frombuffer(bytes.fromhex(start['committed']),dtype='<u2');new_words=np.frombuffer(pending,dtype='<u2')
            x0,x1,y0,y1=start['rect'];inside=np.zeros(1024,dtype=bool)
            for y in range(y0,y1+1):inside[y*32+x0:y*32+x1+1]=True
            if np.any((old_words!=new_words)&~inside):raise ValueError('RECT_PENDING_CHANGE_OUTSIDE_UNION')
            runs=rect_runs(old_words.tolist(),new_words.tolist(),tuple(start['rect']))
            if len(mappackets)!=2*len(runs):raise ValueError('RECT_MAP_DESCRIPTOR_COUNT')
            for j,(at,n) in enumerate(runs):
                for packet,baseword in zip(mappackets[j*2:j*2+2],(0x7800,0x7c00)):
                    if packet['source']!=0x42c000+at or packet['bytes']!=n or packet['vram_word']!=baseword+at//2 or bytes.fromhex(packet['payload'])!=pending[at:at+n]:raise ValueError('RECT_MAP_DESCRIPTOR_PAYLOAD')
        previous=committed
        # CHR packets must retain direct-pair semantics even if map runs split.
        chrnew=[p for p in packets if p['epoch']==i and p['source'] in (0x42d680,0x42d6c0)]
        chrold=[p for p in oldpackets if p['epoch']==i and p['source'] in (0x42d680,0x42d6c0)]
        if chrnew!=chrold:raise ValueError('RECT_CHR_TRANSFER_DRIFT')
        if result['observations'][i]['dirty_tiles']!=old['observations'][i]['dirty_tiles']:raise ValueError('RECT_ADMISSION_DRIFT')
        def ms(row,blank):
            clocks={k:row.get(k+'_clocks',0) for k in ('preflight_and_allocation','composition','dma','production','publication')};clocks['forced_blank']=blank
            clocks['other_production']=clocks['production']-clocks['preflight_and_allocation']-clocks['composition']-clocks['dma']
            return dict(clocks=clocks,ms={k:v*1000/hz for k,v in clocks.items()},dma_bytes=row['dma_bytes'],dma_descriptors=row['dma_transfers'])
        pairs.append(dict(epoch=i,render_noop=noop,before=ms(b,before_blank.get(i,0)),after=ms(a,after_blank.get(i,0)),map_before=[s for s in oldcosts if s['epoch']==i],map_after=[s for s in costs if s['epoch']==i],map_dma_bytes=sum(p['bytes'] for p in mappackets),map_dma_descriptors=len(mappackets),map_dma_before_bytes=sum(p['bytes'] for p in oldpackets if p['epoch']==i and 0x42c000<=p['source']<0x42c800),map_dma_before_descriptors=sum(1 for p in oldpackets if p['epoch']==i and 0x42c000<=p['source']<0x42c800),map_equality=True))
    if result['negative']!=old['negative']:raise ValueError('RECT_REJECTION_DRIFT')
    if (folder/'native/rejected-committed-map.bin').read_bytes()!=previous:raise ValueError('RECT_REJECTION_CHANGED_COMMITTED')
    warm=[p for p in pairs[1:] if not p['render_noop']]
    before_max={k:max(p['before']['ms'][k] for p in warm) for k in warm[0]['before']['ms']};after_max={k:max(p['after']['ms'][k] for p in warm) for k in warm[0]['after']['ms']}
    passed=after_max['production']<before_max['production']*.98 and all(p['after']['ms']['production']<=p['before']['ms']['production'] for p in warm)
    return dict(status='PASS' if passed else 'NO_SPEEDUP',classification='BYOR_MOTU_RECT_MAP_DIFF_PASS' if passed else 'RECT_MAP_NO_SPEEDUP',paired_epochs=pairs,warm_worst_before_ms=before_max,warm_worst_after_ms=after_max,production_reduction_percent=100*(1-after_max['production']/before_max['production']),independent_map_and_transaction_checks=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare-control',type=Path,required=True);a=p.parse_args()
    if a.prepare_control.exists():raise ValueError('CONTROL_OUTPUT_MUST_BE_NEW')
    native=a.prepare_control/'native';native.mkdir(parents=True)
    for name in ('bor.sfc','publisher.pasm','publisher.sym','publisher.bin','callback_owner.lua'):shutil.copyfile(BASE/'native'/name,native/name)
    os.link(BASE/'native/bor.msu',native/'bor.msu')
    c=json.loads((BASE/'contract.json').read_text());c['map_profile']=True
    (a.prepare_control/'contract.json').write_text(json.dumps(c,indent=2)+'\n')
    shutil.copyfile(BASE/'asset-validation.json',a.prepare_control/'asset-validation.json')
