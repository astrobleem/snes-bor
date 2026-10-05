"""Measure shared lossless component schedules and exact tile upload deltas."""
import argparse
import json
from pathlib import Path
import numpy as np
from bg_components import compile_frame,schedule_group


def changed_tiles(a,b):
    return sum(not np.array_equal(a[y:y+8,x:x+8],b[y:y+8,x:x+8])
               for y in range(0,224,8) for x in range(0,256,8))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--canvas',type=Path,action='append',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--time-limit',type=float,default=60)
    a=p.parse_args();canvases=[np.frombuffer(f.read_bytes(),dtype='<u2').reshape(224,256) for f in a.canvas]
    results=[]
    for bits in ((0,1,1),(1,0,1),(1,1,0)):
        solved=schedule_group(canvases,bits,time_limit=a.time_limit)
        result=dict(low_bits=list(bits),solver={k:v for k,v in solved.items() if k not in ('states','trace')},
                    scope='Shared union schedule only. Failure does not reject frame-specific scheduling.')
        if 'states' in solved:
            frames=[compile_frame(c,bits,236,7,solved) for c in canvases]
            result['vram_admitted']=all(f[0]['vram_admitted'] for f in frames)
            result['transitions']=[dict(source_tiles=changed_tiles(canvases[i-1],canvases[i]),
                high_tiles=changed_tiles(frames[i-1][1],frames[i][1]),
                low_tiles=changed_tiles(frames[i-1][2],frames[i][2])) for i in range(1,len(frames))]
            result['schedule']=solved
        results.append(result)
        a.output.write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='schedule'}),flush=True)


if __name__=='__main__':main()
