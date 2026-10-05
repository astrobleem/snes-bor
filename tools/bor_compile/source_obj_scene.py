"""Fixed-bank OBJ admission for explicit source actor poses, with no quantization.

Scene poses must be supplied, with provenance. This does not infer reachable
script combinations or certify alpha math. Alpha uses bank eligibility only.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image
from compiler import Source, key
from source_profile import document, discover
from source_palette import model_palettes
from dialect_4086 import animation_frames
from raster_palette import pieces_for_grid, split_scene_color_masks, schedule


def probe(source, scene, time_limit=60):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    models=discover(source,docs)['models']
    viewport=scene.get('viewport',[256,224]); w,h=viewport
    size=tuple(scene.get('piece_size',[16,32])); pieces=[]; actors=[]
    for actor in scene['actors']:
        model=next(m for m in models if m['name'].casefold()==actor['model'].casefold())
        anim=next(a for a in animation_frames(docs[key(model['source_path'])]['directives']) if a['role']==actor['animation'])
        frame=anim['frames'][actor['frame']]; path=source.image_path(frame['declaration']['values'][0]); raw=source.read(path)
        palette=model_palettes(source,model)['base']
        if palette is None: raise ValueError('MODEL_PALETTE_AUTHORITY_REQUIRED')
        with Image.open(io.BytesIO(raw)) as im:
            if im.mode!='P': raise ValueError('INDEXED_SOURCE_REQUIRED')
            indices=np.array(im); pixels=np.array(palette['rgb555'])[indices]
            pixels=np.where(indices!=0,pixels,-1)
        x,z,a=actor['position']; left=int(x-frame['offset'][0]); top=int(z-a-frame['offset'][1])
        if actor.get('direction',1)==0:
            # Source flip origin is explicit: mirrored offset transforms the
            # image about the entity origin; no sprite geometry is resized.
            pixels=pixels[:,::-1]; left=int(x-(pixels.shape[1]-frame['offset'][0]))
        yy,xx=np.indices(pixels.shape)
        pixels=np.where((xx+left>=0)&(xx+left<w)&(yy+top>=0)&(yy+top<h),pixels,-1)
        alpha_rows=model['properties'].get('alpha',[])
        alpha=int(alpha_rows[-1]['values'][0]) if alpha_rows else 0
        banks=list(range(4,8)) if alpha else list(range(8))
        own=pieces_for_grid(pixels,size)
        for p in own:
            p['x']+=left; p['y']+=top
            p['rows']={y+top:cs for y,cs in p['rows'].items() if 0<=y+top<h}
            p['actor']=len(actors); p['allowed_banks']=banks
        pieces.extend(own)
        actors.append(dict(**actor,source_path=model['source_path'],image_path=path,
            frame_sha256=hashlib.sha256(raw).hexdigest(),source_dimensions=list(indices.shape[::-1]),
            visible_pixels=int(np.count_nonzero(pixels>=0)),visible_colors=len(set(map(int,pixels[pixels>=0]))),
            allowed_banks=banks,source_alpha=alpha,alpha_semantics_admitted=(alpha==0),unmasked_pieces=len(own)))
    solved=split_scene_color_masks(pieces,time_limit=time_limit)
    result=dict(schema='BYOR_SOURCE_OBJ_SCENE_V1',scene=scene,actors=actors,
        assignment=solved,source_pixels_and_colors_unchanged=True,
        scope='Explicit pose/grid only; no depth occlusion credit, reachability or alpha-math admission.',
        source_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest(),native_admitted=False)
    if 'pieces' in solved:
        ps=solved['pieces']; assignments=solved['assignment']
        sprite=[sum(p['y']<=y<p['y']+p['height'] for p in ps) for y in range(h)]
        slivers=[sum((p['width']+7)//8 for p in ps if p['y']<=y<p['y']+p['height']) for y in range(h)]
        trace,_=schedule(ps,assignments,h,lookahead=8,prefetch_write_budget=16)
        result.update(geometry=dict(oam_entries=len(ps),peak_sprites=max(sprite),peak_8px_slivers=max(slivers)),
            schedule=trace,peak_scheduled_writes=max((t['colors_written'] for t in trace[1:]),default=0),
            piece_row_color_identity_verified=solved['piece_row_color_identity_verified'])
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--time-limit',type=float,default=60)
    a=p.parse_args();r=probe(Source(a.source),json.loads(a.scene.read_text()),a.time_limit)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(output=str(a.output),status=r['assignment']['status'],
        geometry=r.get('geometry'),peak_scheduled_writes=r.get('peak_scheduled_writes'),native_admitted=False)))


if __name__=='__main__': main()
