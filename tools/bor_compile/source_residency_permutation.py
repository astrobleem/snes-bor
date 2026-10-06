"""Relabel tile-cache slots to cluster simultaneous refills without eviction.

The permutation preserves all slot lifetimes, source tile identities and map
priority bits. Weighted refill similarity is a heuristic, not optimality proof.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import numpy as np
from bg_component_cache import sparse_transfers
from bg_component_deadlines import derive_jobs, schedule, replay, cost


def order_slots(slots,masks,weights):
    x=np.array([masks[s] for s in slots],dtype=np.float64)
    weighted=x*weights
    norm=weighted.sum(axis=1)
    distances=norm[:,None]+norm[None,:]-2*weighted@x.T
    current=int(np.argmin(norm));remaining=set(range(len(slots)));order=[]
    while remaining:
        order.append(current);remaining.remove(current)
        if remaining:current=min(remaining,key=lambda j:(distances[current,j],norm[j],slots[j]))
    # Open path 2-opt, with a virtual all-zero slot at each end.
    for _ in range(12):
        changed=False
        for i in range(len(order)-1):
            a=order[i-1] if i else None;b=order[i]
            best=0;chosen=None
            for j in range(i+1,len(order)):
                c=order[j];d=order[j+1] if j+1<len(order) else None
                old=(norm[b] if a is None else distances[a,b])+(norm[c] if d is None else distances[c,d])
                new=(norm[c] if a is None else distances[a,c])+(norm[b] if d is None else distances[b,d])
                if new-old<best-1e-9:best=new-old;chosen=j
            if chosen is not None:order[i:chosen+1]=reversed(order[i:chosen+1]);changed=True
        if not changed:break
    return [slots[v] for v in order]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--residency',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allowance',type=int,default=9000);p.add_argument('--window',type=int,default=50000)
    p.add_argument('--weight-power',type=float,default=3)
    p.add_argument('--packet-setup',type=int,default=216)
    p.add_argument('--refresh-clocks',type=int,default=0)
    p.add_argument('--late-release-first',action='store_true');a=p.parse_args()
    plan=json.loads((a.residency/'report.json').read_text());result=deepcopy(plan)
    if not plan['resident_identity_replay']:raise ValueError('PERMUTATION_REQUIRES_COMPLETE_INPUT')
    a.output.mkdir(parents=True,exist_ok=True);starts=plan['source_frame_start_fields'];last=starts[-1]
    weights=np.ones(last+1)
    for f in plan['fields']:
        if f['field']:weights[f['field']]=(cost(f['jobs']+f['mandatory'],216)/40000)**a.weight_power
    maps={};published={};permutations={}
    for name,base in [('high',4096),('low',49152)]:
        plane=result[name];slots=plane.get('physical_slots',list(range(plane['capacity'])))
        masks={s:[0]*(last+1) for s in slots}
        for f in plan['fields']:
            for j in f['jobs']:
                if j['plane']==name:masks[j['slot']][f['field']]=1
        ordered=order_slots(slots,masks,weights)
        permutation=dict(zip(ordered,sorted(slots)));permutations[name]=permutation
        for frame in plane['frames']:
            for w in frame['writes']:w['slot']=permutation[w['slot']]
        maps[name]=[];published[name]=[]
        offset=base//64 if name=='high' else 0
        for i in range(len(starts)):
            before=np.fromfile(a.residency/('%02d-%s.map'%(i,name)),dtype='<u2').reshape(32,32)
            after=before.copy()
            for y in range(28):
                for x in range(32):
                    old=int(before[y,x]);slot=(old&0x3ff)-offset
                    after[y,x]=(old&0xfc00)|(permutation[slot]+offset)
            published[name].append(after);maps[name].append((after[:28]&0x3ff)-offset)
            (a.output/('%02d-%s.map'%(i,name))).write_bytes(after.tobytes())
        (a.output/(name+'-tiles.chr')).write_bytes((a.residency/(name+'-tiles.chr')).read_bytes())
    for n in ('obj.chr','oam.bin'):(a.output/n).write_bytes((a.residency/n).read_bytes())
    mandatory={};transitions=[]
    for i in range(1,len(starts)):
        transfers=[]
        for name,base in [('high',61440),('low',63488)]:
            transfers+=sparse_transfers(published[name][i-1],published[name][i],base,a.packet_setup)
        mandatory[starts[i]]=[dict(address=v['vram_byte_address'],bytes=v['bytes'],kind='tilemap') for v in transfers]
        t=deepcopy(plan['transitions'][i-1]);t['tilemap_transfers']=transfers;transitions.append(t)
    jobs=derive_jobs(result,maps,starts,bases={'high':4096,'low':49152})
    fields,passed=schedule(jobs,mandatory,last,a.window,a.packet_setup,a.allowance,a.refresh_clocks,a.late_release_first)
    identity=replay(fields,result,maps,starts) if passed else False
    result.update(jobs=jobs,fields=fields,transitions=transitions,resident_identity_replay=identity,
        status='OFFLINE_DEADLINE_CANDIDATE' if identity else 'GREEDY_DEADLINE_HEURISTIC_LIMIT',
        window_master_clocks=a.window,palette_allowance_master_clocks=a.allowance,
        packet_setup_master_clocks=a.packet_setup,refresh_master_clocks_per_line=a.refresh_clocks,
        late_release_first=a.late_release_first,
        slot_permutation={n:{str(k):v for k,v in d.items()} for n,d in permutations.items()},
        source_residency_sha256=hashlib.sha256((a.residency/'report.json').read_bytes()).hexdigest(),
        permutation_policy='Weighted refill-mask nearest neighbor with open-path 2-opt; no optimality claim')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],identity=identity,last_field=fields[-1]['field'],
        missed=len(fields[-1]['missed_deadline_jobs']),peak=max(f['estimated_master_clocks'] for f in fields[1:]))))


if __name__=='__main__':main()
