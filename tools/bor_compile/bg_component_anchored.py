"""Compile a static background component prefix and a contiguous dynamic suffix."""
import argparse
import json
from pathlib import Path
import numpy as np
from bg_components import split_pixels,compile_frame
from contiguous_palette import attempt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--canvas',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();bits=(0,1,1)
    base=np.fromfile(a.baseline,dtype='<u2').reshape(224,256)
    pixels=np.fromfile(a.canvas,dtype='<u2').reshape(224,256)
    fixed=sorted(set(map(int,split_pixels(base,bits)[0].flat)));offset=len(fixed)
    high=split_pixels(pixels,bits)[0];lines=[set(map(int,row))-set(fixed) for row in high]
    solved=None
    for span in range(1,33):
        for layout in ('first','last','frequency','persistent'):
            trial=attempt(lines,236-offset,span,layout)
            if 'states' in trial:solved=trial;break
        if solved:break
    if solved is None:raise SystemExit('ANCHORED_CONTIGUOUS_HEURISTIC_LIMIT')
    states=[{0:fixed+s} for s in solved['states']];trace=[]
    for y,state in enumerate(states):
        updates=[dict(bank=0,slot=i+1,color=c) for i,c in enumerate(state[0])
                 if not y or states[y-1][0][i]!=c]
        trace.append(dict(scanline=y,updates=updates,colors_written=len(updates)))
    shared=dict(states=states,trace=trace,status='ANCHORED_CONTIGUOUS_COMPONENT_PROVEN')
    r,indices,low=compile_frame(pixels,bits,236,span,shared)
    r.update(static_component_colors=fixed,span=span,layout=layout,
             contiguous_bursts=[dict(scanline=row['scanline'],start_slot=row['start_slot']+offset,
                 values=row['values']) for row in solved['trace']])
    folder=a.output.with_suffix('');folder.mkdir(exist_ok=True)
    (folder/'indices.bin').write_bytes(indices.tobytes());(folder/'low_indices.bin').write_bytes(low.tobytes())
    (folder/'expected.rgb555').write_bytes(pixels.astype('<u2').tobytes())
    (folder/'initial.json').write_text(json.dumps(r.pop('initial'))+'\n')
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('trace','contiguous_bursts','static_component_colors')}))


if __name__=='__main__':main()
