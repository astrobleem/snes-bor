"""Compile explicit source contexts with lossless hybrid palette admission.

Camera/poses and ordering are supplied inputs, not inferred gameplay states.
This inventory does not certify transition bandwidth or a live compositor.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import numpy as np
from compiler import Source
from source_hybrid_scene import derive


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--stage',required=True)
    p.add_argument('--contexts',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--obj-banks',type=int,required=True);p.add_argument('--time-limit',type=float,default=20)
    p.add_argument('--min-span',type=int,default=15);p.add_argument('--max-span',type=int,default=17)
    p.add_argument('--background-policy',choices=('auto','whole_frame','scanline_live'),default='auto')
    a=p.parse_args();items=json.loads(a.contexts.read_text())
    if not items or not isinstance(items,list):raise ValueError('HYBRID_CONTEXT_LIST_REQUIRED')
    labels=[c['label']for c in items]
    if len(set(labels))!=len(labels)or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',s)for s in labels):raise ValueError('HYBRID_CONTEXT_LABEL_DOMAIN')
    if not 1<=a.min_span<=a.max_span<=255:raise ValueError('HYBRID_CONTEXT_SPAN_DOMAIN')
    a.output.mkdir(parents=True,exist_ok=True);source=Source(a.source);cache={};rows=[]
    for item in items:
        assets=None
        attempts=[]
        for policy in (('whole_frame','scanline_live')if a.background_policy=='auto'else(a.background_policy,)):
            for span in range(a.min_span,a.max_span+1):
                r,assets=derive(source,a.stage,item['scene'],a.obj_banks,a.time_limit,span=span,assignment_cache=cache,fixed_background_policy=policy)
                attempts.append(dict(policy=policy,span=span,status=r.get('bg_schedule',{}).get('status')))
                if assets is not None:break
            if assets is not None:break
        r['context_palette_attempts']=attempts
        folder=a.output/item['label'];folder.mkdir(exist_ok=True)
        if assets is not None:
            for name,data in assets.items():
                if name in ('bg','expected'):data=data.astype('<u2')
                (folder/(name+'.bin')).write_bytes(data.tobytes())
        (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n')
        row=dict(label=item['label'],camera=r['camera'],compiled=assets is not None,
                 source_rgb555_sha256=r['source_rgb555_sha256'],obj_assignment=r['obj_assignment']['status'],
                 report_sha256=hashlib.sha256((folder/'report.json').read_bytes()).hexdigest())
        if assets is not None:
            counts={plane:len({assets[plane][y:y+8,x:x+8].tobytes()for y in range(0,224,8)for x in range(0,256,8)})for plane in ('high','low')}
            row.update(high_tiles=counts['high'],low_tiles=counts['low'],fixed_background_policy=r['fixed_background_policy'],peak_palette_words=r['bg_schedule']['span'],
                       peak_palette_bytes=r['bg_schedule']['peak_bytes'],native_obj_entries=r['native_obj_entries'])
        rows.append(row)
        report=dict(schema='BYOR_HYBRID_EXPLICIT_CONTEXT_INVENTORY_V1',rows=rows,complete=len(rows)==len(items),
                    all_offline_palette_schedules_proven=all(c['compiled']for c in rows),
                    static_obj_assignments=len(cache),input_contexts_sha256=hashlib.sha256(a.contexts.read_bytes()).hexdigest(),
                    native_contexts_proven=False,native_transitions_proven=False,authored_reachability_proven=False,
                    live_world_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(row),flush=True)
    if not all(c['compiled']for c in rows):raise ValueError('HYBRID_CONTEXT_PALETTE_ADMISSION_FAILED')


if __name__=='__main__':main()
