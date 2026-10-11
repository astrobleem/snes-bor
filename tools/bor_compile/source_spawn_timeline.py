"""Source-order spawn01 callbacks and nominal child lifetime overlap.

The real script body runs through variant bytecode with a valid parent and
successful allocation. This is a conditional uninterrupted-animation probe;
AI reachability, collisions, interruptions and dynamic loops are not admitted.
"""
import argparse,ast,hashlib,json
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from dialect_4086 import animation_frames,ENGINE_COMMIT
from source_integer_ticks_4086 import ticks
from source_model_core_4086 import binary32
from script_ir_4086 import parse_script,inspect
from script_bytecode import compile_library
from script_vm_reference import Machine,Value,integer


def overlap(events):
    boundaries=sorted({t for e in events for t in(e['birth_tick'],e['expiry_tick'])})
    snapshots=[]
    for t in boundaries:
        active=[i for i,e in enumerate(events)if e['birth_tick']<=t<e['expiry_tick']]
        snapshots.append(dict(tick=t,active_events=active,count=len(active)))
    return max((r['count']for r in snapshots),default=0),snapshots


def derive(source,parent_position=(0,220,0),direction=1):
    if direction not in(0,1)or len(parent_position)!=3:raise ValueError('SPAWN_TIMELINE_PARENT_DOMAIN')
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    models=discover(source,docs)['models'];lookup={m['name'].casefold():m for m in models};reports=[]
    builtins=inspect(source)['engine_api_requirements']
    for model in models:
        if not model['scripts']:continue
        path=model['scripts'][0]['values'][0];raw=source.read(path)
        library=compile_library(parse_script(raw.decode('latin1'),path),builtins)
        for animation in animation_frames(docs[key(model['source_path'])]['directives']):
            selected=[e for e in animation['events']if e['function']=='spawn01']
            if not selected:continue
            events=[]
            for event in selected:
                entries={};changes=[]
                properties=dict(zip(('x','z','a'),[Value('DECIMAL',binary32(v))for v in parent_position]));properties['direction']=integer(direction)
                def read_parent(pointer,name):
                    if pointer!=Value('POINTER',1):raise ValueError('SPAWN_TIMELINE_PARENT_PROPERTY_REQUIRED')
                    return properties[name.data]
                def change_child(*args):
                    values=[v.data for v in args]
                    if values[0]!=2 or values[1]not in('position','direction'):raise ValueError('SPAWN_TIMELINE_CHILD_PROPERTY_REQUIRED')
                    if values[1]=='position':values[2:]=[binary32(v)for v in values[2:]]
                    changes.append(values);return Value()
                hooks={'getlocalvar':lambda k:Value('POINTER',1),'getentityproperty':read_parent,
                       'clearspawnentry':lambda:entries.clear()or Value(),
                       'setspawnentry':lambda k,v:entries.update({k.data:v.data})or Value(),
                       'spawn':lambda:Value('POINTER',2),
                       'changeentityproperty':change_child}
                args=[]
                for token in event['arguments']:
                    kind='STRING'if token.startswith('"')else'DECIMAL'if any(c in token.lower()for c in('.','e'))else'INTEGER'
                    args.append(Value('STRING',ast.literal_eval(token))if kind=='STRING'else Value('DECIMAL',float(token))if kind=='DECIMAL'else integer(int(token,0)))
                returned=Machine(library,hooks).call(event['function'],args)
                if returned!=Value('POINTER',2)or 'name'not in entries:raise ValueError('SPAWN_TIMELINE_CALLBACK_BINDING')
                child=lookup[str(entries['name']).casefold()];life=child['properties'].get('lifespan',[])
                if not life:raise ValueError('SPAWN_TIMELINE_FINITE_CHILD_LIFESPAN_REQUIRED')
                duration=ticks(life[-1]['values'][0])
                if duration<=0 or event['start_tick']is None:raise ValueError('SPAWN_TIMELINE_LIFETIME_DOMAIN')
                events.append(dict(source_callback=event,model=child['name'],model_source_path=child['source_path'],model_source_sha256=docs[key(child['source_path'])]['sha256'],birth_tick=event['start_tick'],expiry_tick=event['start_tick']+duration,lifespan_ticks=duration,script_position_changes=changes,allocation_assumed_successful=True))
            peak,snapshots=overlap(events)
            reports.append(dict(parent_model=model['name'],parent_source_path=model['source_path'],parent_source_sha256=docs[key(model['source_path'])]['sha256'],animation=animation['role'],nominal_duration_ticks=animation['duration_ticks'],script_path=path,script_sha256=hashlib.sha256(raw).hexdigest(),births=events,peak_declared_lifetime_overlap_upper_bound=peak,overlap_snapshots=snapshots,loop_and_interrupt_behavior_bound=False,child_initialization_and_callbacks_bound=False))
    return dict(schema='BYOR_SOURCE_SPAWN_TIMELINE_V1',engine_authority=ENGINE_COMMIT,source_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest(),parent_position=list(parent_position),direction=direction,animations=reports,scope='Actual spawn01 script body; nominal uninterrupted single animation; successful allocation and valid parent. Declared child lifetime upper bound only: child initialization, spawn scripts, kills, motion and visible frames are unbound.',source_reachability_proven=False,world_motion_and_collision_bound=False,universal_actor_count_bound=False,native_presentation_proven=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=derive(Source(a.source));a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps([dict(parent=r['parent_model'],animation=r['animation'],births=len(r['births']),lifetime_overlap_upper_bound=r['peak_declared_lifetime_overlap_upper_bound'])for r in result['animations']]))


if __name__=='__main__':main()
