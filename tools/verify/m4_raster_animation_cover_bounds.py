"""Necessary exact-context palette liveness bounds for every source animation frame.

Explicit pose and immutable underlay only. No geometry, native admission or
authored gameplay reachability is inferred from the relaxed bounds.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from compiler import Source,key
from dialect_4086 import animation_frames
from source_profile import document,discover
from source_scene_obj_joint import probe


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--stage',required=True)
    parser.add_argument('--scene',type=Path,required=True)
    parser.add_argument('--actor',type=int,default=0)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--time-limit',type=int,default=45)
    parser.add_argument('--additive-only',action='store_true')
    parser.add_argument('--parent-actor',type=int)
    parser.add_argument('--birth-tick',type=int)
    parser.add_argument('--pool-math-mode',action='append',choices=('add','half-add','subtract','half-subtract'))
    args=parser.parse_args();source=Source(args.source)
    scene=json.loads(args.scene.read_text());actor=scene['actors'][args.actor]
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    model=next(m for m in discover(source,docs)['models']if m['name']==actor['model'])
    animation=next(a for a in animation_frames(docs[key(model['source_path'])]['directives'])if a['role']==actor['animation'])
    if (args.parent_actor is None)!=(args.birth_tick is None):raise ValueError('ANIMATION_BOUND_PARENT_CLOCK_PAIR_REQUIRED')
    parent_animation=None
    if args.parent_actor is not None:
        if args.parent_actor==args.actor or args.birth_tick<0:raise ValueError('ANIMATION_BOUND_PARENT_CLOCK_DOMAIN')
        parent=scene['actors'][args.parent_actor]
        parent_model=next(m for m in discover(source,docs)['models']if m['name']==parent['model'])
        parent_animation=next(a for a in animation_frames(docs[key(parent_model['source_path'])]['directives'])if a['role']==parent['animation'])
    report=dict(schema='BYOR_EXPLICIT_ANIMATION_COVER_BOUNDS_V1',
                source_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest(),
                scene=scene,scene_sha256=hashlib.sha256(args.scene.read_bytes()).hexdigest(),
                stage=args.stage,actor_index=args.actor,source_animation_frames=len(animation['frames']),
                additive_only=args.additive_only,parent_actor_index=args.parent_actor,parent_birth_tick=args.birth_tick,
                uninterrupted_parent_animation_assumed=parent_animation is not None,
                pool_math_modes=args.pool_math_mode,
                frames=[],geometry_and_bank_assignment_relaxed=True,
                authored_reachability_proven=False,native_presentation_proven=False,
                universal_raster_rejected=False,no_color_reduction=True)
    keys=('status','peak_write_lower_bound','validated_dual_lower_bound','maximum_primal_violation',
          'maximum_dual_residual','source_rgb555_sha256','source_actor_canvases','variables','constraints',
          'visible_final_obj_output_full_frame_colors','peak_visible_final_obj_output_colors_per_scanline')
    for index in range(len(animation['frames'])):
        pose=copy.deepcopy(scene);pose['actors'][args.actor]['frame']=index
        parent_frame=None
        if parent_animation is not None:
            tick=args.birth_tick+animation['frames'][index]['start_tick']
            matches=[f for f in parent_animation['frames']if f['start_tick']<=tick<f['start_tick']+f['delay_ticks']]
            if len(matches)!=1:raise ValueError('ANIMATION_BOUND_PARENT_FRAME_NOT_ACTIVE')
            parent_frame=matches[0]['index'];pose['actors'][args.parent_actor]['frame']=parent_frame
        result=probe(source,args.stage,pose,size='mixed',pool_only=True,align_visible_bounds=True,
                     clip_horizontal=True,underlay_bypass=True,complete_additive_cover=True,
                     additive_only=args.additive_only,time_limit=args.time_limit,pool_math_modes=args.pool_math_mode)
        row={k:result[k]for k in keys if k in result}
        layer=next(layer for layer in result['metadata']['layers']if layer['kind']=='actor:'+actor['model'])
        row.update(source_image_path=layer['path'],source_image_sha256=layer['sha256'],
                   source_dimensions=layer['source_dimensions'])
        row.update(frame=index,source_frame=animation['frames'][index],parent_frame=parent_frame)
        report['frames'].append(row)
        proven=[r for r in report['frames']if r['status']=='FRACTIONAL_COVER_LIVENESS_LOWER_BOUND']
        report['worst_validated_frame']=max(proven,key=lambda r:r['validated_dual_lower_bound'])['frame']if proven else None
        report['peak_validated_lower_bound']=max((r['validated_dual_lower_bound']for r in proven),default=None)
        args.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:row[k]for k in ('frame','status','validated_dual_lower_bound')if k in row}),flush=True)


if __name__=='__main__':main()
