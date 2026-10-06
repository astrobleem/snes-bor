"""Offline hybrid preload windows on scanlines without palette updates.

Only future high-plane tiles whose slots are absent from the displayed map
are considered. VRAM is inaccessible during ordinary HBlank: this hypothetical
plan also requires bounded forced blank and a proof that BG/OBJ fetches survive.
The cost/window assumptions are not hardware admission. Required current-frame
work stays in VBlank.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from bg_component_deadlines import cost


def derive(plan,frames,maps,window=50000,setup=216,allowance=9000,max_hblank_bytes=1024):
    if max_hblank_bytes<0 or max_hblank_bytes%64:raise ValueError('HBLANK_HIGH_TILE_BUDGET')
    starts=plan['source_frame_start_fields'];pending=list(plan['jobs']);fields=[]
    fixed={v['field']:v['mandatory'] for v in plan['fields']};frame=0
    for field in range(starts[-1]+1):
        while frame+1<len(starts) and starts[frame+1]<=field:frame+=1
        palette_rows={v['scanline'] for v in frames[frame]['bg_schedule']['trace']}
        # Separate each transfer by an idle line, including transition away
        # from any palette-writing line. The native proof must measure this
        # gap and per-kind IRQ setup time rather than assuming it is enough.
        available=[]
        for y in range(2,222):
            if {y-1,y,y+1}&palette_rows:continue
            if available and y-available[-1]<2:continue
            available.append(y)
        hblank=[];chunks=[]
        if field:
            current=set(map(int,maps['high'][frame].flat))
            candidates=sorted((j for j in pending if j['plane']=='high' and j['bytes']==64
                and j['release']<=field<j['deadline'] and j['slot'] not in current),
                key=lambda j:(j['deadline'],j['address']))
            limit=min(max_hblank_bytes//64,len(available)//2)
            for j in candidates[:limit]:
                hblank.append(j)
                for half in range(2):
                    chunks.append(dict(scanline=available[len(chunks)],address=j['address']+half*32,
                        bytes=32,tile=j['tile'],tile_byte_offset=half*32,plane='high',
                        slot=j['slot'],deadline=j['deadline']))
        h_ids={id(j) for j in hblank};pending=[j for j in pending if id(j) not in h_ids]
        selected=[];mandatory=fixed.get(field,[])
        for j in sorted((j for j in pending if j['release']<=field),key=lambda j:(j['deadline'],j['address'])):
            if field==0 or cost(mandatory+selected+[j],setup)+allowance<=window:selected.append(j)
        ids={id(j) for j in selected};pending=[j for j in pending if id(j) not in ids]
        missed=[j for j in pending if j['deadline']<=field]
        exceeded=field>0 and cost(mandatory,setup)+allowance>window
        fields.append(dict(field=field,jobs=selected,mandatory=mandatory,hblank_jobs=hblank,
            hblank_chunks=chunks,estimated_master_clocks=cost(mandatory+selected,setup)+(allowance if field else 0),
            missed_deadline_jobs=missed,mandatory_budget_exceeded=exceeded))
        if missed or exceeded:return fields,False
    return fields,not pending


def replay(plan,fields,maps):
    names=('high','low');starts=plan['source_frame_start_fields'];frame=0
    canonical={n:[None]*plan[n]['slot_extent'] for n in names};snapshots=[]
    for index in range(len(starts)):
        for n in names:
            for w in plan[n]['frames'][index]['writes']:canonical[n][w['slot']]=w['tile']
        snapshots.append({n:list(v) for n,v in canonical.items()})
    resident={n:list(snapshots[0][n]) for n in names}
    def current_identity():
        return all(resident[n][slot]==snapshots[frame][n][slot]
            for n in names for slot in set(map(int,maps[n][frame].flat)))
    for row in fields:
        while frame+1<len(starts) and starts[frame+1]<=row['field']:frame+=1
        for j in row['jobs']:resident[j['plane']][j['slot']]=j['tile']
        if not current_identity():return False
        pinned=set(map(int,maps['high'][frame].flat))
        for j in row['hblank_jobs']:
            if j['slot'] in pinned or not j['release']<=row['field']<j['deadline']:return False
            resident[j['plane']][j['slot']]=j['tile']
        if not current_identity():return False
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sequence',type=Path,required=True);p.add_argument('--residency',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--window-master-clocks',type=int,default=50000)
    p.add_argument('--palette-allowance-master-clocks',type=int,default=9000)
    p.add_argument('--packet-setup-master-clocks',type=int,default=216)
    p.add_argument('--hblank-bytes-per-field',type=int,default=1024);a=p.parse_args()
    plan=json.loads((a.residency/'report.json').read_text());count=len(plan['source_frame_start_fields'])
    frames=[json.loads((a.sequence/('frame-%02d'%i)/'report.json').read_text()) for i in range(count)]
    maps={n:[] for n in ('high','low')}
    high_offset=plan['allocation']['high_chr'][0]//64
    for n in maps:
        for i in range(count):
            m=np.fromfile(a.residency/('%02d-%s.map'%(i,n)),dtype='<u2').reshape(32,32)[:28]&0x3ff
            if n=='high':m=m-high_offset
            maps[n].append(m)
    fields,passed=derive(plan,frames,maps,a.window_master_clocks,a.packet_setup_master_clocks,
        a.palette_allowance_master_clocks,a.hblank_bytes_per_field)
    identity=replay(plan,fields,maps) if passed else False
    result=dict(schema='BYOR_HYBRID_HBLANK_PRELOAD_DEADLINES_V1',
        status='OFFLINE_FORCED_BLANK_PRELOAD_HYPOTHESIS' if identity else 'HBLANK_PRELOAD_HEURISTIC_LIMIT',
        fields=fields,source_frame_start_fields=plan['source_frame_start_fields'],resident_identity_replay=identity,
        window_master_clocks=a.window_master_clocks,packet_setup_master_clocks=a.packet_setup_master_clocks,
        palette_allowance_master_clocks=a.palette_allowance_master_clocks,
        max_hblank_bytes_per_field=a.hblank_bytes_per_field,native_hblank_chunk_bytes=32,
        native_hblank_preload_proven=False,no_color_reduction=True,
        required_vram_access='Forced blank; ordinary HBlank writes are ignored',
        forced_blank_fetch_integrity_proven=False,
        hardware_authority='https://snes.nesdev.org/wiki/PPU_registers',
        scope='Offline future-tile liveness only. Forced-blank timing, 32-byte transfers and BG/OBJ fetch integrity are unproven. No production or gameplay admission.')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='fields'}))
    if not identity:print(json.dumps(dict(failed_field=fields[-1]['field'],missed_jobs=len(fields[-1]['missed_deadline_jobs']))))


if __name__=='__main__':main()
