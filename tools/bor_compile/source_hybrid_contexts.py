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
    p.add_argument('--obj-banks',required=True,help='1..7 or auto for source-derived static palette admission');p.add_argument('--time-limit',type=float,default=20)
    p.add_argument('--min-span',type=int,default=15);p.add_argument('--max-span',type=int,default=17)
    p.add_argument('--background-policy',choices=('auto','whole_frame','scanline_live'),default='auto')
    p.add_argument('--opaque-effects',choices=('obj','bg'),default='obj',help='Generic type-none opaque effects in OBJ or exact promoted BG tiles')
    p.add_argument('--cull-covered-obj',action='store_true',help='Omit source pieces fully hidden by exact promoted BG tiles before bank solving')
    a=p.parse_args();items=json.loads(a.contexts.read_text())
    bank_counts=range(1,8)if a.obj_banks=='auto'else[int(a.obj_banks)]
    if any(not 1<=b<=7 for b in bank_counts):raise ValueError('HYBRID_CONTEXT_OBJ_BANK_DOMAIN')
    if not items or not isinstance(items,list):raise ValueError('HYBRID_CONTEXT_LIST_REQUIRED')
    labels=[c['label']for c in items]
    if len(set(labels))!=len(labels)or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',s)for s in labels):raise ValueError('HYBRID_CONTEXT_LABEL_DOMAIN')
    if not 1<=a.min_span<=a.max_span<=255:raise ValueError('HYBRID_CONTEXT_SPAN_DOMAIN')
    a.output.mkdir(parents=True,exist_ok=True);source=Source(a.source);cache={};rows=[]
    for item in items:
        assets=None
        attempts=[]
        for banks in bank_counts:
            # Bank selection is part of the assignment identity. An identical
            # piece geometry tried against another bank domain cannot reuse it.
            bank_cache=cache.setdefault(banks,{})
            for policy in (('whole_frame','scanline_live')if a.background_policy=='auto'else(a.background_policy,)):
                for span in range(a.min_span,a.max_span+1):
                    r,assets=derive(source,a.stage,item['scene'],banks,a.time_limit,span=span,assignment_cache=bank_cache,fixed_background_policy=policy,opaque_effect_policy=a.opaque_effects,cull_covered_obj=a.cull_covered_obj)
                    attempts.append(dict(obj_banks=banks,policy=policy,span=span,obj_assignment=r['obj_assignment']['status'],status=r.get('bg_schedule',{}).get('status')))
                    print(json.dumps(dict(context=item['label'],attempt=attempts[-1])),flush=True)
                    if assets is not None or 'obj_pieces'not in r:break
                if assets is not None or 'obj_pieces'not in r:break
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
                    static_obj_assignments=sum(map(len,cache.values())),input_contexts_sha256=hashlib.sha256(a.contexts.read_bytes()).hexdigest(),
                    native_contexts_proven=False,native_transitions_proven=False,authored_reachability_proven=False,
                    live_world_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(row),flush=True)
    if not all(c['compiled']for c in rows):raise ValueError('HYBRID_CONTEXT_PALETTE_ADMISSION_FAILED')


if __name__=='__main__':main()
