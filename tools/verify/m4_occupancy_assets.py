"""Independent source-index coverage checks, including signed/clipped origins."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from phase_occupancy import tile_maybe_covered


def verify(phases,occupancy,assets,observations):
    m=json.loads((phases/'manifest.json').read_text())
    om=json.loads((occupancy/'occupancy-manifest.json').read_text())
    authority=json.loads((assets/'source-assets.json').read_text())
    frames={f['role']:f for f in authority['frames']}
    front=np.frombuffer((assets/'foreground.bin').read_bytes(),dtype='u1').reshape(224,256)!=0
    inputs=[*phases.iterdir(),*occupancy.iterdir(),*(assets/f'{r}.indices' for r in frames)]
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs if p.is_file()}
    comparisons=0;bounds={};epochs=[]
    def projected(src,ox,oy):
        mask=np.zeros((224,256),dtype=bool)
        x0,x1=max(0,ox),min(256,ox+src.shape[1]);y0,y1=max(0,oy),min(224,oy+src.shape[0])
        if x1>x0 and y1>y0:mask[y0:y1,x0:x1]=src[y0-oy:y1-oy,x0-ox:x1-ox]
        return mask
    def tiles(mask):return mask.reshape(28,8,32,8).any(axis=(1,3))
    def lookup(role,ox,oy):
        e=om['frames'][role]['x_phases'][ox&7];data=(occupancy/e['filename']).read_bytes()
        return np.array([[tile_maybe_covered(data,e,origin_x=ox,origin_y=oy,screen_tx=tx,screen_ty=ty) for tx in range(32)] for ty in range(28)])
    for role,f in frames.items():
        w,h=f['dimensions'];src=np.frombuffer((assets/f'{role}.indices').read_bytes(),dtype='u1').reshape(h,w)!=0
        crop=m['frames'][role];cx,cy=crop['crop_x'],crop['crop_y'];src=src[cy:cy+crop['height'],cx:cx+crop['width']]
        bound=0
        for px in range(8):
            e=om['frames'][role]['x_phases'][px];data=(occupancy/e['filename']).read_bytes()
            for q in range(8):
                # Whole source in a padded local canvas: independent of phase records.
                local=np.zeros((e['tile_rows']*8,e['cols']*8),dtype=bool)
                local[q:q+src.shape[0],px:px+src.shape[1]]=src
                expected=local.reshape(e['tile_rows'],8,e['cols'],8).any(axis=(1,3))
                actual=np.frombuffer(data,dtype='u1').reshape(8,e['tile_rows'],e['cols'])[q]!=0
                if not np.array_equal(actual,expected):raise ValueError('SOURCE_LOCAL_OCCUPANCY_MISMATCH')
                bound=max(bound,int(expected.sum()))
                for bx,by in ((-16,-24),(-1,-1),(0,0),(12,20),(31,27)):
                    ox,oy=bx*8+px,by*8+q
                    if not np.array_equal(lookup(role,ox,oy),tiles(projected(src,ox,oy))):raise ValueError('SIGNED_CLIPPED_OCCUPANCY_MISMATCH')
                    comparisons+=896
        bounds[role]=bound
    for ob in json.loads(observations.read_text()):
        a=ob['scene']['actors'][0];role=a['animation'];f=frames[role];crop=m['frames'][role]
        ox=ob['x_q16']//65536-f['offset'][0];oy=ob['z_q16']//65536-f['offset'][1]
        w,h=f['dimensions'];src=np.frombuffer((assets/f'{role}.indices').read_bytes(),dtype='u1').reshape(h,w)!=0
        visible=tiles(projected(src,ox,oy)&~front)
        conservative=lookup(role,ox+crop['crop_x'],oy+crop['crop_y'])
        if np.any(visible&~conservative):raise ValueError('LEGACY_COVERAGE_FALSE_NEGATIVE')
        epochs.append(dict(epoch=ob['epoch'],legacy_visible_tiles=int(visible.sum()),source_occupied_tiles=int(conservative.sum()),extra_admissions=int((conservative&~visible).sum())))
    after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs if p.is_file()}
    if before!=after:raise ValueError('OCCUPANCY_INPUT_MUTATION')
    if bounds!={r:e['maximum_source_occupied_tiles'] for r,e in om['frames'].items()}:raise ValueError('OCCUPANCY_BOUND_MISMATCH')
    return dict(status='PASS',all_phase_screen_tile_comparisons=comparisons,source_coverage_bounds=bounds,maximum_required_pairs=596+max(bounds.values()),capacity=768,legacy_false_negatives=0,epochs=epochs,inputs_unchanged=True,input_sha256=before)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phases',type=Path,required=True);p.add_argument('--occupancy',type=Path,required=True)
    p.add_argument('--assets',type=Path,default=Path('out/byor-motu-online-v3/assets'))
    p.add_argument('--observations',type=Path,default=Path('out/byor-motu-opaque-warm-v4/native/observations.json'))
    p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    result=verify(a.phases,a.occupancy,a.assets,a.observations)
    a.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_sha256','epochs')},indent=2))
