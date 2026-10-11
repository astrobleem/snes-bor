"""Measure the exact constant-addition subscreen route's source constraints.

This route presents actor-free BG1 on the main screen and every visible OBJ
on the subscreen. A darker output channel cannot be produced by addition.
Rejection covers this routing policy, not other raster or BG architectures.
"""
import hashlib
import numpy as np
from source_scene_obj_raster import prepare
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555


def measure(source,stage,scene):
    actors,metadata,expected=prepare(source,stage,scene)
    background=rgb555(compose_rgb8(source,stage,dict(scene,actors=[]))[0]);complete=rgb555(expected)
    rows=[set()for _ in range(len(complete))];records=[];total_bad=0
    for i,actor in enumerate(actors):
        words=set();bad=0;visible=0;first=None;raw=actor['pixels']
        for ly,lx in zip(*np.where(raw>=0)):
            y,x=actor['top']+int(ly),actor['left']+int(lx)
            if not 0<=y<len(complete)or not 0<=x<complete.shape[1]:continue
            output=int(raw[ly,lx]);underlay=int(background[y,x]);visible+=1;words.add(output);rows[y].add(output)
            darker=[channel for channel,shift in enumerate((0,5,10))if((output>>shift)&31)<((underlay>>shift)&31)]
            if darker:
                bad+=1
                if first is None:first=dict(x=x,y=y,source_local_x=int(lx),source_local_y=int(ly),expected_rgb555=output,background_rgb555=underlay,darker_channels=darker)
        records.append(dict(actor=i,source_model=actor['metadata']['kind'].removeprefix('actor:'),source_asset_path=actor['metadata'].get('path'),visible_source_pixels=visible,distinct_final_rgb555_words=len(words),unrepresentable_additive_pixels=bad,first_unrepresentable_pixel=first));total_bad+=bad
    return dict(schema='BYOR_CONSTANT_SUBSCREEN_ADDITION_SOURCE_DEMAND_V1',status='CONSTANT_SUBSCREEN_ADDITION_ROUTE_REJECTED_FOR_CONTEXT'if total_bad else'CONSTANT_SUBSCREEN_ADDITION_OPERANDS_EXIST_FOR_CONTEXT',
        source_metadata=metadata,scene_provenance=scene.get('provenance'),actors=records,total_visible_source_pixels=sum(a['visible_source_pixels']for a in records),unrepresentable_additive_pixels=total_bad,
        simultaneous_final_rgb555_words=len(set.union(*rows)),peak_scanline_final_rgb555_words=max(map(len,rows)),source_rgb555_sha256=hashlib.sha256(complete.astype('<u2').tobytes()).hexdigest(),
        main_screen='ACTOR_FREE_BG1',subscreen='ALL_VISIBLE_OBJ',main_obj_disabled=True,subscreen_bg_disabled=True,math_mode='ADD',eligible_subscreen_obj_banks=list(range(8)),
        fixed_color_zero=True,source_output_rgb555_measured=True,source_context_reachability_certified=False,palette_bank_assignment_proven=False,palette_transfer_proven=False,native_routing_proven=False,
        universal_raster_rejected=False,no_color_reduction=True)


def main():
    import argparse,json
    from pathlib import Path
    from compiler import Source
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True);parser.add_argument('--stage',required=True)
    parser.add_argument('--scene',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=measure(Source(args.source),args.stage,json.loads(args.scene.read_text()))
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
