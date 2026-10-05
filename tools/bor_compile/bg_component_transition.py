"""Try retaining source-stable high-component slots across a frame transition."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from bg_components import split_pixels,compile_frame
from bg_component_group import changed_tiles
from raster_palette import bounded_schedule


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--previous',type=Path,required=True);p.add_argument('--next',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    canvases=[np.fromfile(f/'expected.rgb555',dtype='<u2').reshape(224,256) for f in (a.previous,a.next)]
    indices=[np.fromfile(f/'indices.bin',dtype=np.uint8).reshape(224,256) for f in (a.previous,a.next)]
    bits=(0,1,1);highs=[split_pixels(c,bits)[0] for c in canvases]
    stable=set(map(int,highs[0][canvases[0]==canvases[1]]))
    report=json.loads(a.previous.with_suffix('.json').read_text())
    state=json.loads((a.previous/'initial.json').read_text());states=[]
    for row in report['trace']:
        if row['scanline']:
            for e in row['updates']:state[e['slot']-1]=e['color']
        states.append(list(state))
    common_rows=[set(map(int,highs[0][y][canvases[0][y]==canvases[1][y]])) for y in range(224)]
    pins={(0,c,y):True for y,colors in enumerate(common_rows) for c in colors}
    locks={(0,i,y):c for y,s in enumerate(states) for i,c in enumerate(s) if c in common_rows[y]}
    rows={y:sorted(set(map(int,row))) for y,row in enumerate(highs[1])}
    solved=bounded_schedule([dict(rows=rows)],[0],224,236,7,lookahead=224,
                            fixed_residency=pins,slot_locks=locks)
    weights=np.bincount(indices[0].astype(np.int32).ravel()*237+indices[1].ravel(),minlength=237*237).reshape(237,237)
    i,j=linear_sum_assignment(weights[1:,1:],maximize=True);perm=np.arange(237,dtype=np.uint8);perm[j+1]=i+1
    result=dict(stable_high_colors=len(stable),source_changed_tiles=changed_tiles(*canvases),
        independent_high_changed_tiles=changed_tiles(*indices),
        constant_permutation_high_changed_tiles=changed_tiles(indices[0],perm[indices[1]]),
        pinned_solver={k:v for k,v in solved.items() if k not in ('states','trace')},
        scope='Pinned previous-frame residency is an optional optimization restriction, not general hardware feasibility.')
    if 'states' in solved:
        r,high,low=compile_frame(canvases[1],bits,236,7,solved)
        result.update(pinned_high_changed_tiles=changed_tiles(indices[0],high),compiled_frame=r)
        folder=a.output.with_suffix('');folder.mkdir(parents=True,exist_ok=True)
        (folder/'indices.bin').write_bytes(high.tobytes());(folder/'low_indices.bin').write_bytes(low.tobytes())
        (folder/'expected.rgb555').write_bytes(canvases[1].astype('<u2').tobytes())
        (folder/'initial.json').write_text(json.dumps(r.pop('initial'))+'\n')
        a.output.with_name(a.output.stem+'-frame.json').write_text(json.dumps(r,indent=2)+'\n')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='compiled_frame'}))


if __name__=='__main__':main()
