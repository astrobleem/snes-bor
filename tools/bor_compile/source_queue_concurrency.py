"""Explore queue-admitted enemy identities without inventing combat timing.

Uses the pinned source dispatch reference. Enemy retirement and camera arrival
are nondeterministic inputs, so this is an admission overapproximation, not a
claim that a pose, animation, projectile or rendered overlap is reachable.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from source_model_registry import derive as registry
from source_stage_queue_4086 import derive as queues
from source_stage_dispatch_4086 import dispatch


def zero_constructor_requests(records, models):
    result=[]
    for i,row in enumerate(records):
        if row['kind']!='empty':continue
        # A zero loader entry resolves cache index zero; it is not a noop.
        # This explorer counts enemies only, so other cache-zero types require
        # a separate admission model instead of silently ignoring an enemy.
        if not models or models[0]['declared_type']!='none':
            raise ValueError('QUEUE_CONCURRENCY_ZERO_ENTRY_TYPE_SERVICE_REQUIRED')
        result.append(dict(queue_index=i,cache_index=0,model=models[0]['identity'],
                           declared_type=models[0]['declared_type'],
                           constructor_if_cache_resident=True,actual_residency_proven=False,
                           included_in_enemy_count=False))
    return result


def explore(records, *, state_limit=100000):
    # index, groupmin, groupmax, waiting, source scroll position, live queue IDs
    initial=(0,100,100,0,0,())
    pending=deque([initial]);seen={initial};parent={initial:None};actions={}
    combinations={};terminal=False
    def add(old,new,action):
        if new in seen:return
        if len(seen)>=state_limit:raise ValueError('QUEUE_CONCURRENCY_STATE_LIMIT')
        seen.add(new);parent[new]=old;actions[new]=action;pending.append(new)
    while pending:
        old=pending.popleft();index,minimum,maximum,waiting,pos,live=old
        combinations.setdefault(live,(old,[]))
        if index==len(records) and not live:terminal=True
        for identity in live:
            remaining=tuple(i for i in live if i!=identity)
            add(old,(index,minimum,maximum,waiting if remaining else 0,pos,remaining),
                dict(kind='enemy_retirement_input',queue_index=identity))
        state=dict(index=index,groupmin=minimum,groupmax=maximum,waiting=waiting,
                   pos=pos,go_time=0,completed=0,time=1,advancetime=0,freezeall=0,
                   players=[dict(dead=0)],leveltype=0)
        entities=[dict(exists=1,type=2,queue_index=i)for i in live]
        def spawn(row,pool):
            if row['kind']=='spawn':
                identity=state['index']
                pool.append(dict(exists=1,type=2,queue_index=identity))
                # Include transient combinations inside one dispatch call.
                transient=tuple(sorted(e['queue_index']for e in pool))
                combinations.setdefault(transient,(old,[dict(kind='source_dispatch_prefix',
                    consumed_queue_indices=list(range(index,state['index']+1)))]))
        trace=dispatch(state,records,entities,spawn)
        newlive=tuple(sorted(e['queue_index']for e in entities))
        new=(state['index'],state['groupmin'],state['groupmax'],
             state['waiting'] if newlive else 0,pos,newlive)
        add(old,new,dict(kind='source_dispatch',consumed_queue_indices=trace))
        # Camera cannot pass a wait with an enemy still present. Arrival at
        # the next authored threshold is an input, not a camera simulation.
        if not waiting and index<len(records) and records[index]['at']>pos:
            add(old,(index,minimum,maximum,waiting,records[index]['at'],live),
                dict(kind='camera_arrival_input',pos=records[index]['at']))
    def witness(state):
        steps=[]
        while parent[state] is not None:
            steps.append(actions[state]);state=parent[state]
        return list(reversed(steps))
    peak=max(map(len,combinations),default=0)
    return dict(states=len(seen),queue_completion_admitted=terminal,peak_enemy_count=peak,
                combinations=[dict(queue_indices=list(live),count=len(live))for live in sorted(combinations)],
                peak_witnesses=[dict(queue_indices=list(live),steps=witness(state)+suffix,
                                     transient_dispatch_possible=True)
                                for live,(state,suffix) in combinations.items()if len(live)==peak])


def derive(source, state_limit=100000):
    models=registry(source)['models'];stages=queues(source)['stages'];result=[]
    for stage in stages:
        records=stage['records']
        zero_requests=zero_constructor_requests(records,models)
        for row in records:
            if row['kind']=='spawn' and models[row['model']]['declared_type']!='enemy':
                raise ValueError('QUEUE_CONCURRENCY_NON_ENEMY_SPAWN_SERVICE_REQUIRED')
        report=explore(records,state_limit=state_limit)
        for combination in report['combinations']:
            combination['enemies']=[dict(queue_index=i,model=models[records[i]['model']]['identity'],
                                         map=records[i]['map'],boss=records[i]['boss'])
                                    for i in combination['queue_indices']]
        result.append(dict(source_path=stage['source_path'],source_sha256=stage['source_sha256'],
                           queue_records=len(records),spawn_records=sum(r['kind']=='spawn'for r in records),
                           zero_initialized_constructor_requests=zero_requests,**report))
    return dict(schema='BYOR_SOURCE_QUEUE_CONCURRENCY_V1',engine_commit=ENGINE_COMMIT,stages=result,
                dispatch_reference_sha256=hashlib.sha256(Path(__file__).with_name('source_stage_dispatch_4086.py').read_bytes()).hexdigest(),
                retirement_and_camera_inputs_nondeterministic=True,
                scope='Queue-admitted enemy combinations; zero-entry non-enemy constructor requests are retained separately. Excludes other-effect lifetimes, scripts/minions/projectile births, animation timing, collision, visibility and player multiplicity.',
                authored_pose_reachability_proven=False,live_world_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--state-limit',type=int,default=100000)
    a=p.parse_args();report=derive(Source(a.source),a.state_limit)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([dict(stage=s['source_path'],states=s['states'],peak_enemies=s['peak_enemy_count'],
                           combinations=len(s['combinations']),queue_completion_admitted=s['queue_completion_admitted'])for s in report['stages']]))


if __name__=='__main__':main()
