"""Source-delay transfer liveness over a specified display clock.

The cost model selects an offline candidate. It is not measured runtime
admission. A failed greedy schedule is explicitly a heuristic limit.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def derive_jobs(plan, maps, starts):
    jobs=[]
    for name,base in [('high',0),('low',49152)]:
        plane=plan[name];size=plane['bpp']*8
        used=[set(map(int,m.flat)) for m in maps[name]]
        births={w['slot']:0 for w in plane['frames'][0]['writes']}
        for index,frame in enumerate(plane['frames'][1:],1):
            for w in frame['writes']:
                slot=w['slot'];release=0
                if w['old_tile'] is not None:
                    previous=births[slot]
                    last=next(j for j in range(index-1,previous-1,-1) if slot in used[j])
                    release=starts[last+1]
                jobs.append(dict(plane=name,slot=slot,tile=w['tile'],bytes=size,
                                 address=base+slot*size,release=release,deadline=starts[index],source_frame=index))
                births[slot]=index
    return jobs


def cost(items):
    ordered=sorted(items,key=lambda j:j['address']);runs=0;end=-1
    for item in ordered:
        if item['address']!=end:runs+=1
        end=item['address']+item['bytes']
    return sum(j['bytes'] for j in ordered)*8+runs*336


def schedule(jobs, mandatory, last, budget):
    pending=list(jobs);fields=[]
    for field in range(last+1):
        selected=[];fixed=mandatory.get(field,[])
        candidates=sorted((j for j in pending if j['release']<=field),key=lambda j:(j['deadline'],j['address']))
        # Startup can fill otherwise unoccupied slots before the clock starts.
        ceiling=None if field==0 else budget-5000
        for job in candidates:
            if ceiling is None or cost(fixed+selected+[job])<=ceiling:selected.append(job)
        selected_ids={id(j) for j in selected}
        pending=[j for j in pending if id(j) not in selected_ids]
        missed=[j for j in pending if j['deadline']<=field]
        fields.append(dict(field=field,jobs=selected,mandatory=fixed,
                           estimated_master_clocks=cost(fixed+selected)+(0 if field==0 else 5000),
                           missed_deadline_jobs=missed,
                           mandatory_budget_exceeded=ceiling is not None and cost(fixed)>ceiling))
        if missed or fields[-1]['mandatory_budget_exceeded']:return fields,False
    return fields,not pending


def replay(fields, plan, maps, starts):
    residents={name:[None]*plan[name]['capacity'] for name in ('high','low')}
    for name in residents:
        for w in plan[name]['frames'][0]['writes']:residents[name][w['slot']]=w['tile']
    expected=[]
    for index in range(len(starts)):
        state={name:{} for name in residents}
        for name in residents:
            for w in plan[name]['frames'][index]['writes']:state[name][w['slot']]=w['tile']
        expected.append(state)
    canonical={name:[None]*len(residents[name]) for name in residents};snapshots=[]
    for changes in expected:
        for name in canonical:
            for slot,tile in changes[name].items():canonical[name][slot]=tile
        snapshots.append({name:list(rows) for name,rows in canonical.items()})
    frame=0
    for row in fields:
        for job in row['jobs']:residents[job['plane']][job['slot']]=job['tile']
        while frame+1<len(starts) and starts[frame+1]<=row['field']:frame+=1
        for name in residents:
            for slot in set(map(int,maps[name][frame].flat)):
                if residents[name][slot]!=snapshots[frame][name][slot]:return False
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sequence',type=Path,required=True)
    p.add_argument('--residency',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-ticks-per-second',type=int,default=200);p.add_argument('--fields-per-second',type=int,default=60)
    p.add_argument('--window-master-clocks',type=int,default=45000);a=p.parse_args()
    seq=json.loads((a.sequence/'report.json').read_text());plan=json.loads((a.residency/'report.json').read_text())
    starts=[];tick=0
    for frame in seq['frames']:
        starts.append((tick*a.fields_per_second+a.source_ticks_per_second-1)//a.source_ticks_per_second)
        tick+=json.loads(Path(frame['report']).read_text())['source_delay_ticks']
    if any(b<=a for a,b in zip(starts,starts[1:])):raise ValueError('MULTIPLE_SOURCE_POSES_PER_FIELD_NOT_ADMITTED')
    maps={name:[np.fromfile(a.residency/f'{i:02d}-{name}.map',dtype='<u2').reshape(32,32)[:28] for i in range(len(starts))] for name in ('high','low')}
    jobs=derive_jobs(plan,maps,starts);mandatory={}
    for t in plan['transitions']:
        mandatory[starts[t['to_frame']]]=[dict(address=x['vram_byte_address'],bytes=x['bytes'],kind='tilemap') for x in t['tilemap_transfers']]
    fields,passed=schedule(jobs,mandatory,starts[-1],a.window_master_clocks)
    identity=replay(fields,plan,maps,starts) if passed else False
    result=dict(schema='BYOR_COMPONENT_SOURCE_DEADLINES_V1',
                status='OFFLINE_DEADLINE_CANDIDATE' if passed and identity else 'GREEDY_DEADLINE_HEURISTIC_LIMIT',
                source_ticks_per_second=a.source_ticks_per_second,display_fields_per_second=a.fields_per_second,
                source_frame_start_fields=starts,window_master_clocks=a.window_master_clocks,
                cost_policy='8 master clocks per data byte + 336 per contiguous packet + 5000 per-field palette/setup allowance; not native admission',
                jobs=jobs,fields=fields,resident_identity_replay=identity,no_color_reduction=True,native_admitted=False,
                scope='Specified rational display-clock hypothesis, fixed pose context, fixed physical slot plan. No production cadence or optimality claim.')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('jobs','fields')}))


if __name__=='__main__':main()
