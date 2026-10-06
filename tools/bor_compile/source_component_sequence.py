"""Measure every source animation pose against one explicit layered context.

Source SCREEN blending precedes lossless component decomposition. Independent
frame schedules are allowed; this is offline resource evidence, not live world
reachability, native bandwidth admission or source cadence certification.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from compiler import Source,key
from source_profile import document,discover
from dialect_4086 import animation_frames
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from bg_components import split_pixels,compile_frame
from contiguous_palette import attempt


def anchored_frame(base,pixels,bits=(0,1,1),spans=range(1,33)):
    fixed=sorted(set(map(int,split_pixels(base,bits)[0].flat)));offset=len(fixed)
    if offset>=236:return dict(status='STATIC_ANCHOR_CAPACITY_LIMIT',anchor_colors=offset),None,None
    high=split_pixels(pixels,bits)[0];lines=[set(map(int,row))-set(fixed) for row in high]
    attempts=[];solved=None
    for span in spans:
        if span>236-offset:continue
        for layout in ('first','last','frequency','persistent'):
            trial=attempt(lines,236-offset,span,layout)
            attempts.append({k:v for k,v in trial.items() if k not in ('states','trace')})
            if 'states' in trial:solved=trial;break
        if solved:break
    if solved is None:return dict(status='ANCHORED_CONTIGUOUS_HEURISTIC_LIMIT',attempts=attempts),None,None
    states=[{0:fixed+s} for s in solved['states']];trace=[]
    for y,state in enumerate(states):
        updates=[dict(bank=0,slot=i+1,color=c) for i,c in enumerate(state[0])
                 if not y or states[y-1][0][i]!=c]
        trace.append(dict(scanline=y,updates=updates,colors_written=len(updates)))
    shared=dict(states=states,trace=trace,status='ANCHORED_CONTIGUOUS_COMPONENT_PROVEN')
    report,indices,low=compile_frame(pixels,bits,236,span,shared)
    report.update(static_component_colors=fixed,span=span,layout=layout,attempts=attempts,
                  contiguous_bursts=[dict(scanline=row['scanline'],start_slot=row['start_slot']+offset,
                     values=row['values']) for row in solved['trace']])
    return report,indices,low


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--stage',required=True);p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--actor',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--preferred-span',type=int,default=13);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);scene=json.loads(a.scene.read_text());target=scene['actors'][a.actor]
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    model=next(m for m in discover(source,docs)['models'] if m['name'].casefold()==target['model'].casefold())
    animation=next(x for x in animation_frames(docs[key(model['source_path'])]['directives']) if x['role']==target['animation'])
    background_scene=copy.deepcopy(scene)
    background_scene['actors']=[actor for index,actor in enumerate(background_scene['actors']) if index!=a.actor]
    base=rgb555(compose_rgb8(source,a.stage,background_scene)[0]);frames=[]
    for index,frame in enumerate(animation['frames']):
        pose=copy.deepcopy(scene);pose['actors'][a.actor]['frame']=index
        canvas,metadata=compose_rgb8(source,a.stage,pose);pixels=rgb555(canvas)
        report,high,low=anchored_frame(base,pixels,spans=range(a.preferred_span,33))
        report.update(source_frame_index=index,source_delay_ticks=frame['delay_ticks'],
                      source_frame_path=frame['declaration']['values'][0],layers=metadata['layers'])
        folder=a.output/f'frame-{index:02d}';folder.mkdir(exist_ok=True)
        if high is not None:
            (folder/'indices.bin').write_bytes(high.tobytes());(folder/'low_indices.bin').write_bytes(low.tobytes())
            (folder/'expected.rgb555').write_bytes(pixels.astype('<u2').tobytes())
            (folder/'initial.json').write_text(json.dumps(report.pop('initial'))+'\n')
        path=folder/'frame.json';path.write_text(json.dumps(report,indent=2)+'\n')
        frames.append(dict(index=index,report=str(path),status=report['status'],
                           span=report.get('span'),high_chr_bytes=report.get('high_chr_bytes'),
                           low_chr_bytes=report.get('low_chr_bytes'),vram_admitted=report.get('vram_admitted'),
                           sha256=hashlib.sha256(pixels.astype('<u2').tobytes()).hexdigest()))
        print(json.dumps(frames[-1]),flush=True)
        (a.output/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
    result=dict(schema='BYOR_SOURCE_COMPONENT_SEQUENCE_V1',model=model['name'],animation=animation['role'],
                scene=scene,frames=frames,no_color_reduction=True,source_dimensions_preserved=True,
                all_offline_schedules_proven=all(f['status']=='LOSSLESS_BG_COMPONENT_SCHEDULE_PROVEN' for f in frames),
                all_individual_vram_admitted=all(f.get('vram_admitted') for f in frames),
                peak_contiguous_burst_colors=max((f.get('span') or 0) for f in frames),
                source_animation_native_admitted=False,production_compositor_bound=False,
                scope='Explicit stationary concurrent poses across every target animation frame; no camera or reachability admission.')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
