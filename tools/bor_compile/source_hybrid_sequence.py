"""Bounded source animation hybrid resource inventory, with explicit failures.

The other actor poses and camera remain specified inputs. No gameplay timing
or reachability is inferred from this compiled display sequence.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import numpy as np
from compiler import Source
from source_animation_step import derive as timing
from source_hybrid_scene import derive


def count_tiles(indices):
    return len({indices[y:y+8,x:x+8].tobytes() for y in range(0,224,8) for x in range(0,256,8)})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--stage',required=True);p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--actor',type=int,required=True);p.add_argument('--obj-banks',type=int,required=True)
    p.add_argument('--min-span',type=int,default=15);p.add_argument('--max-span',type=int,default=17)
    p.add_argument('--retain-frame-palette',action='store_true')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    if not 1<=a.min_span<=a.max_span<=255:raise ValueError('HYBRID_SEQUENCE_SPAN_DOMAIN')
    source=Source(a.source);scene=json.loads(a.scene.read_text());actor=scene['actors'][a.actor]
    animation=next(v for v in timing(source)['animations'] if v['model'].casefold()==actor['model'].casefold() and v['role']==actor['animation'])
    rows=[];cache={};tick=0;palette_seed=None
    for frame in range(animation['count']):
        pose=deepcopy(scene);pose['actors'][a.actor]['frame']=frame
        span_attempts=[]
        for seed in ([palette_seed,None] if palette_seed is not None else [None]):
            for span in range(a.min_span,a.max_span+1):
                r,assets=derive(source,a.stage,pose,a.obj_banks,span=span,assignment_cache=cache,palette_seed=seed)
                span_attempts.append(dict(span=span,status=r.get('bg_schedule',{}).get('status'),retained_initial_palette=seed is not None))
                if assets is not None:break
            if assets is not None:break
        r['sequence_span_attempts']=span_attempts
        folder=a.output/('frame-%02d'%frame);folder.mkdir(exist_ok=True)
        if assets:
            for name,value in assets.items():
                if name in ('bg','expected'):value=value.astype('<u2')
                (folder/(name+'.bin')).write_bytes(value.tobytes())
        (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n')
        row=dict(frame=frame,start_source_tick=tick,delay_ticks=animation['delays'][frame],
            obj_assignment=r['obj_assignment']['status'],bg_schedule=r.get('bg_schedule',{}).get('status'),
            static_obj_assignment_sha256=r['static_obj_assignment_sha256'],compiled_report_sha256=hashlib.sha256((folder/'report.json').read_bytes()).hexdigest())
        if assets:
            row.update(high_tiles=count_tiles(assets['high']),low_tiles=count_tiles(assets['low']),
                native_obj_entries=r['native_obj_entries'],obj_chr_bytes=r['obj_chr_bytes'],
                promoted_tiles=r['promoted_tiles'],peak_cgram_bytes=r['bg_schedule']['peak_bytes'])
            row['span']=r['bg_schedule']['span']
            if a.retain_frame_palette:palette_seed=r['bg_schedule']['final_dynamic_residency']
            row['single_frame_hybrid_layout_admitted']=row['high_tiles']<=640 and row['low_tiles']<=640 and row['obj_chr_bytes']<=8192
        else:row['single_frame_hybrid_layout_admitted']=False
        rows.append(row);tick+=animation['delays'][frame]
        progress=dict(schema='BYOR_HYBRID_SEQUENCE_INVENTORY_V1',rows=rows,complete=len(rows)==animation['count'],
            static_obj_assignments=len(cache),all_frames_compiled=all(v['single_frame_hybrid_layout_admitted'] for v in rows),
            source_animation_handle=animation['handle'],source_duration_ticks=tick,
            requested_span_range=[a.min_span,a.max_span],
            retain_frame_palette=a.retain_frame_palette,
            no_color_reduction=True,native_sequence_proven=False,live_world_bound=False,motu_gameplay_proven=False,
            scope='Source animation with explicit fixed concurrent poses; individual palette and VRAM admission only, no transfer deadline or native sequence claim')
        (a.output/'report.json').write_text(json.dumps(progress,indent=2)+'\n')
        print(json.dumps(row),flush=True)


if __name__=='__main__':main()
