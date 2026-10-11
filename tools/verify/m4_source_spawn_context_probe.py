import hashlib,json
from pathlib import Path
import numpy as np
from compiler import Source,key
from source_profile import document,discover
from dialect_4086 import animation_frames
from source_spawn_timeline import derive
from script_dispatch_4086 import compile_source
from script_vm_reference import Machine,Value,integer
from source_scene_obj_raster import prepare
from source_scene_obj_lower_bound import bound
from source_bg_feasibility import rgb555

source=Source('Masters of the Universe [v.3.0 Build 4086].pak')
timeline=derive(source,parent_position=(1970,220,0));rise=next(a for a in timeline['animations']if a['parent_model']=='Skeletor'and a['animation']=='rise')
docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};models=discover(source,docs)['models'];lookup={m['name']:m for m in models}
compiled=compile_source(source);programs={p['model']:p['program']for p in compiled['programs']};handles={(h['model'],h['role']):h['handle']for h in compiled['animation_handles']}
child=lookup[rise['births'][0]['model']];animations={a['role']:a for a in animation_frames(docs[key(child['source_path'])]['directives'])}
assert child['type']=='none'and not animations['idle']['events']and not child['properties'].get('speed')
spawn=animations['spawn'];idle=animations['idle'];assert len(spawn['frames'])==2 and not any(r['directive']=='loop'for r in spawn['directives'])
assert spawn['duration_ticks']==8
survivors=[];killed=[]
for event in rise['births']:
    position=event['script_position_changes'][0][2:];dead=[]
    hooks={'getlocalvar':lambda k:integer(1)if k.data=='frame'else integer(handles[child['declaration'],'spawn'])if k.data=='animhandle'else Value('POINTER',2),
           'getentityproperty':lambda p,k:Value('DECIMAL',position[1])if k.data=='z'else (_ for _ in()).throw(ValueError('UNBOUND_CHILD_PROPERTY')),
           'openborconstant':lambda k:integer({'PLAYER_MIN_Z':160,'PLAYER_MAX_Z':232}[k.data]),
           'killentity':lambda p:dead.append(p.data)or Value()}
    Machine(programs[child['declaration']],hooks).call('main')
    (killed if dead else survivors).append(event)
root=next(a for a in animation_frames(docs[key(lookup['Skeletor']['source_path'])]['directives'])if a['role']=='rise')
reports=[];best=None;tile_best=None
times={r['start_tick']for r in root['frames']}
for e in survivors:
    times.update(e['birth_tick']+offset for offset in [0,4,8,9,e['lifespan_ticks']]+[9+r['start_tick']for r in idle['frames']])
for t in sorted(t for t in times if 208<=t<root['duration_ticks']):
    children=[]
    for i,event in enumerate(survivors):
        age=t-event['birth_tick']
        if not 0<=age<event['lifespan_ticks']:continue
        # check_ai precedes update_animation; stopped spawn returns to idle
        # on the following tick, with no action/think delaying nextthink.
        if age<9:role='spawn';f=min(age//4,1)
        else:
            role='idle';f=max(j for j,row in enumerate(idle['frames'])if row['start_tick']<=age-9)
        children.append(dict(model=child['name'],animation=role,frame=f,position=event['script_position_changes'][0][2:],order=10+i))
    frame=max(j for j,row in enumerate(root['frames'])if row['start_tick']<=t)
    # Independently timed breathing begins 66 ticks before this sample. This
    # is a conditional source pose; combat interruption/reachability is open.
    scene=dict(camera=[1800,0],viewport=[256,224],actors=[dict(model='He_ManB',animation='freespecial4',frame=6,position=[1880,220,0],order=0),dict(model='HBreath',animation='idle',frame=11,position=[1898,220,93],order=1),dict(model='Skeletor',animation='rise',frame=frame,position=[1970,220,0],order=2)]+children)
    actors,metadata,expected=prepare(source,'data/levels/Guile2.txt',scene)
    height,width=expected.shape[:2];lower=bound(actors,height,width);colors=rgb555(expected)
    visible_children=sum(a['metadata']['final_visible_pixels']>0 for a in actors if a['metadata']['kind']=='actor:'+child['name'])
    row_colors=[]
    for y in range(height):
        words=set()
        for a in actors:
            ly=y-a['top']
            if 0<=ly<len(a['pixels']):words.update(int(c)for c in a['pixels'][ly]if c>=0)
        row_colors.append(len(words))
    report=dict(tick=t,surviving_declared_lifetimes_active=len(children),visible_children=visible_children,peak_final_obj_scanline_colors=max(row_colors),peak_actor_owned_tile_lower_bound=lower['peak_actor_owned_tile_lower_bound'],source_rgb555_sha256=hashlib.sha256(colors.astype('<u2').tobytes()).hexdigest())
    reports.append(report)
    score=(report['peak_final_obj_scanline_colors'],report['peak_actor_owned_tile_lower_bound'],visible_children)
    if best is None or score>best[0]:best=(score,scene,report,metadata,lower)
    if tile_best is None or lower['peak_actor_owned_tile_lower_bound']>tile_best[0]:tile_best=(lower['peak_actor_owned_tile_lower_bound'],scene,report,metadata,lower)
    if t%40==0:print(json.dumps(report),flush=True)
receipt=dict(schema='BYOR_SKELETOR_RISE_CONDITIONAL_VISUAL_PROBE_V1',timeline=rise,initial_spawn_killed_children=len(killed),surviving_lifetime_children=len(survivors),player_z_bounds=[160,232],spawn_to_idle_delay_ticks=9,peak_declared_lifetime_overlap_upper_bound=rise['peak_declared_lifetime_overlap_upper_bound'],worst_measured_frame=best[2],scene=best[1],metadata=best[3],sliver_bound=best[4],worst_tile_frame=tile_best[2],worst_tile_scene=tile_best[1],worst_tile_metadata=tile_best[3],worst_tile_bound=tile_best[4],rows=reports,all_nominal_visual_transition_ticks_sampled=True,scope='Fixed-position conditional nominal rise and source spawn script Z guard; child default-init and check_ai ordering applied; no physics/collisions/AI reachability admission.',source_pose_reachability_proven=False,universal_raster_rejected=False,native_presentation_proven=False,no_color_reduction=True)
Path('out/byor-motu-skeletor-rise-conditional-visual.json').write_text(json.dumps(receipt,indent=2)+'\n')
Path('out/byor-motu-skeletor-rise-conditional-scene.json').write_text(json.dumps(best[1],indent=2)+'\n')
Path('out/byor-motu-skeletor-rise-tile-peak-scene.json').write_text(json.dumps(tile_best[1],indent=2)+'\n')
print(json.dumps(dict(worst=best[2],tile_peak=tile_best[2],killed=len(killed),source_reachability_proven=False)),flush=True)
