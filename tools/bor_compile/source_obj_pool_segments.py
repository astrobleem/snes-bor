"""Merge overlapping exact source color-math cache witnesses without resets.

These are two hardware eligibility pools, not a fixed-bank or transfer proof.
The merged cache and rendered source outputs are independently replayed.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from compiler import Source
from source_scene_obj_raster import prepare
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from raster_math_windows import evaluate
from raster_obj_math_cover import MODES,apply_math


def merge(source,stage,scene,segments,write_budget=21):
    if type(write_budget)is not int or not 0<=write_budget<=120:raise ValueError('POOL_SEGMENT_WRITE_BUDGET_DOMAIN')
    actors,metadata,expected=prepare(source,stage,scene);expected=rgb555(expected)
    digest=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()
    background=rgb555(compose_rgb8(source,stage,dict(scene,actors=[]))[0])
    states={};modes={};windows={};boundaries=[]
    for segment in segments:
        if segment.get('status')!='INTEGER_POOL_SOURCE_REPLAY_PROVEN'or segment.get('metadata')!=metadata or segment.get('source_rgb555_sha256')!=digest or not segment.get('full_interval_source_pixels_verified')or segment.get('zero_main_clipping_palette_demand_relaxed'):raise ValueError('POOL_SEGMENT_SOURCE_IDENTITY')
        current={int(y):{int(k):set(cs)for k,cs in row.items()}for y,row in segment['selected_palette_residency'].items()}
        sm={int(y):m for y,m in segment['selected_modes'].items()};sw={int(y):w for y,w in segment['compiled_color_window_descriptors'].items()}
        if not current or set(current)!=set(range(min(current),max(current)+1))or set(sm)!=set(current)or set(sw)!=set(current):raise ValueError('POOL_SEGMENT_CONTIGUOUS_DOMAIN')
        first=min(current)
        if states:
            if first not in states or current[first]!=states[first]:raise ValueError('POOL_SEGMENT_BOUNDARY_PALETTE_RESET')
            boundaries.append(first)
        states.update(current);modes.update(sm);windows.update(sw)
    if not states:raise ValueError('POOL_SEGMENT_EMPTY')
    first,last=min(states),max(states);peak=0;writes={}
    if set(states)!=set(range(first,last+1)):raise ValueError('POOL_SEGMENT_MERGED_DOMAIN')
    for y,state in states.items():
        if not 0<=y<224 or set(state)!={0,1}or any(len(cs)>60 or any(type(c)is not int or not 0<=c<32768 for c in cs)for cs in state.values())or modes[y]not in MODES:raise ValueError('POOL_SEGMENT_CACHE_DOMAIN')
        w=windows[y]
        if len(w.get('bounds',[]))!=2 or any(len(pair)!=2 or any(type(v)is not int or not 0<=v<=255 for v in pair)for pair in w['bounds'])or w['wobjsel_color_bits']&~0xf0 or w['wobjlog_color_bits']not in(0,4)or w.get('cgwsel_clip_and_prevent_bits')!=0x10:raise ValueError('POOL_SEGMENT_WINDOW_DOMAIN')
        if y>first:
            count=sum(len(state[k]-states[y-1][k])for k in (0,1));writes[y]=count;peak=max(peak,count)
            if count>write_budget:raise ValueError('POOL_SEGMENT_PALETTE_WRITE_BUDGET')
    checked=0
    for actor in actors:
        for ly,lx in zip(*np.where(actor['pixels']>=0)):
            y,x=actor['top']+int(ly),actor['left']+int(lx)
            if y not in states:continue
            out=int(actor['pixels'][ly,lx]);bg=int(background[y,x])
            if out==bg:continue
            if actor['metadata']['alpha']==0 and out not in states[y][0]:raise ValueError('POOL_SEGMENT_ORDINARY_LITERAL_MISSING')
            if out not in states[y][0]and not any((apply_math(c,bg,modes[y])if evaluate(windows[y],x)else c)==out for c in states[y][1]):raise ValueError('POOL_SEGMENT_SOURCE_PIXEL_REPLAY')
            checked+=1
    return dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata=metadata,source_rgb555_sha256=digest,
        selected_modes=modes,compiled_color_window_descriptors=windows,
        selected_palette_residency={y:{k:sorted(cs)for k,cs in row.items()}for y,row in states.items()},
        full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
        checked_visible_source_pixels=checked,scanline_interval=[first,last],segment_boundaries=boundaries,
        boundary_palette_identity_verified=True,palette_writes_by_line=writes,peak_replayed_pool_writes=peak,
        initial_palette_free_only_once=True,integer_pool_pixel_coverage_verified=True,
        geometry_and_bank_assignment_relaxed=True,physical_transfer_admitted=False,native_timing_admitted=False,
        source_joint_ai_reachability_certified=False,universal_raster_rejected=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--stage',required=True)
    p.add_argument('--scene',type=Path,required=True);p.add_argument('--segments',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=merge(Source(a.source),a.stage,json.loads(a.scene.read_text()),json.loads(a.segments.read_text()))
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in ('status','scanline_interval','segment_boundaries','checked_visible_source_pixels','peak_replayed_pool_writes')}))


if __name__=='__main__':main()
