"""Reproduce actual epoch-17 actor and backdrop admission counts."""
import argparse,json
from pathlib import Path
import numpy as np
from m4_nonblank_component_native import sha

def verify(output):
    assets=Path('out/byor-motu-online-v3/assets');native=Path('out/byor-motu-rect-map-v1/native')
    frames={f['role']:f for f in json.loads((assets/'source-assets.json').read_text())['frames']}
    ob=json.loads((native/'observations.json').read_text())[17];frame=frames['idle'];w,h=frame['dimensions']
    src=np.frombuffer((assets/'idle.indices').read_bytes(),dtype='u1').reshape(h,w)!=0
    ox=ob['x_q16']//65536-frame['offset'][0];oy=ob['z_q16']//65536-frame['offset'][1]
    mask=np.zeros((224,256),dtype=bool);x0,x1=max(0,ox),min(256,ox+w);y0,y1=max(0,oy),min(224,oy+h)
    mask[y0:y1,x0:x1]=src[y0-oy:y1-oy,x0-ox:x1-ox]
    front=np.frombuffer((assets/'foreground.bin').read_bytes(),dtype='u1').reshape(224,256)!=0
    tile=lambda x:x.reshape(28,8,32,8).any(axis=(1,3)).reshape(-1)
    conservative=tile(mask);exact=tile(mask&~front)
    base=np.frombuffer((assets/'0-high.map').read_bytes(),dtype='<u2')[:896];directory=np.frombuffer((native/'directory-16.bin').read_bytes(),dtype='<u2')
    restoration=lambda actor:sorted(set(map(int,base[(~actor)&((directory[base]&0x8000)!=0)])))
    old=(native/'vram-16.bin').read_bytes();hi=(assets/'high.chr').read_bytes();lo=(assets/'low.chr').read_bytes()
    homes=restoration(exact)
    if any(old[s*64:s*64+64]==hi[s*64:s*64+64] and old[49152+s*16:49152+s*16+16]==lo[s*16:s*16+16] for s in homes):raise ValueError('CAPACITY_HOME_FLAG_NOT_PHYSICALLY_OVERWRITTEN')
    result=dict(conservative_actor=int(conservative.sum()),exact_actor=int(exact.sum()),occluded=int((conservative&~exact).sum()),conservative_restoration_homes=restoration(conservative),exact_restoration_homes=homes,free_tail=int(np.count_nonzero((directory[596:]&0x3fff)==0)),occluded_cells=list(map(int,np.flatnonzero(conservative&~exact))),physical_home_contents_verified=True,input_sha256={str(p):sha(p.read_bytes()) for p in (assets/'idle.indices',assets/'foreground.bin',assets/'0-high.map',assets/'high.chr',assets/'low.chr',native/'directory-16.bin',native/'vram-16.bin',native/'world-17.bin')})
    result['conservative_slots']=result['conservative_actor']+len(result['conservative_restoration_homes']);result['exact_slots']=result['exact_actor']+len(homes)
    output.write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.output),indent=2))
