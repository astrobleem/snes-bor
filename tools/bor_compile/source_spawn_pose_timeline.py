"""Conditional source-authored parent/child pose intersections; no native reachability."""
import argparse,json
from pathlib import Path
from compiler import Source
from source_profile import document
from dialect_4086 import animation_frames
from source_spawn_timeline import derive


def intersect(parent_frames,child_frame,birth_tick,expiry_tick):
    first=birth_tick+child_frame['start_tick'];last=min(expiry_tick,first+child_frame['delay_ticks'])
    return [dict(parent_frame=p['index'],child_frame=child_frame['index'],interval_ticks=[max(first,p['start_tick']),min(last,p['start_tick']+p['delay_ticks'])],parent_frame_source=p['declaration'],child_frame_source=child_frame['declaration'])
            for p in parent_frames if max(first,p['start_tick'])<min(last,p['start_tick']+p['delay_ticks'])]


def query(source,parent_model,parent_animation,child_model,child_frame,parent_position=(0,0,0),direction=1):
    if type(child_frame)is not int or child_frame<0:raise ValueError('SPAWN_POSE_CHILD_FRAME_DOMAIN')
    timeline=derive(source,parent_position,direction)
    parents=[a for a in timeline['animations']if a['parent_model'].casefold()==parent_model.casefold()and a['animation'].casefold()==parent_animation.casefold()]
    if len(parents)!=1:raise ValueError('SPAWN_POSE_PARENT_ANIMATION_REQUIRED')
    parent=parents[0];parent_doc=document(source,parent['parent_source_path']);frames=next(a['frames']for a in animation_frames(parent_doc['directives'])if a['role']==parent['animation'])
    events=[e for e in parent['births']if e['model'].casefold()==child_model.casefold()]
    if not events:raise ValueError('SPAWN_POSE_AUTHORED_CHILD_REQUIRED')
    results=[]
    for event in events:
        child_doc=document(source,event['model_source_path']);idle=[a for a in animation_frames(child_doc['directives'])if a['role']=='idle']
        if len(idle)!=1 or child_frame>=len(idle[0]['frames']):raise ValueError('SPAWN_POSE_CHILD_IDLE_FRAME_REQUIRED')
        selected=idle[0]['frames'][child_frame]
        results.append(dict(birth=event,child_nominal_frame_interval=[event['birth_tick']+selected['start_tick'],event['birth_tick']+selected['start_tick']+selected['delay_ticks']],parent_child_intersections=intersect(frames,selected,event['birth_tick'],event['expiry_tick'])))
    return dict(schema='BYOR_CONDITIONAL_SOURCE_SPAWN_POSE_V1',source_sha256=timeline['source_sha256'],engine_authority=timeline['engine_authority'],parent_model=parent['parent_model'],parent_animation=parent['animation'],parent_position=list(parent_position),direction=direction,parent_source_sha256=parent['parent_source_sha256'],script_sha256=parent['script_sha256'],parent_nominal_duration_ticks=parent['nominal_duration_ticks'],child_model=events[0]['model'],child_frame=child_frame,events=results,scope='Source script bytecode and nominal uninterrupted loader frame intervals. Successful allocation, child idle startup at birth and fixed parent position assumed.',source_reachability_proven=False,child_constructor_dispatch_phase_bound=False,loop_and_interrupt_behavior_bound=False,world_motion_and_collision_bound=False,universal_concurrency_bound=False,native_presentation_proven=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('source','parent-model','parent-animation','child-model'):p.add_argument('--'+n,required=True)
    p.add_argument('--parent-position',type=float,nargs=3,default=(0,0,0));p.add_argument('--direction',type=int,choices=(0,1),default=1)
    p.add_argument('--child-frame',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=query(Source(a.source),a.parent_model,a.parent_animation,a.child_model,a.child_frame,a.parent_position,a.direction);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(parent=r['parent_model'],child=r['child_model'],frame=r['child_frame'],intervals=[x['interval_ticks']for e in r['events']for x in e['parent_child_intersections']],source_reachability_proven=False)))


if __name__=='__main__':main()
