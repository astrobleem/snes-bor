"""Immutable source assets for a fixed-camera online component producer.

Contains no actor-position canvases. The backdrop has no actor; foreground
coverage stays separate so native actor composition preserves source ordering.
Actor rows retain source indices, palette identity, dimensions and offsets.
"""
import hashlib
import json
from unittest.mock import patch
import numpy as np
from compiler import key
from source_profile import document,discover
from source_palette import model_palettes,select_model_palette
from dialect_4086 import animation_frames
from source_bg_feasibility import decode,rgb555
import source_scene_bg as scene_bg
from source_animation_init_4086 import derive as animations
from source_model_registry import derive as registry
from bg_components import compile_frame
from bg_component_residency import encode


def derive(source,stage,folder):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    model=next(m for m in discover(source,docs)['models'] if m['name']=='He_Man')
    palette,selected=select_model_palette(model_palettes(source,model),0)
    alpha=model['properties'].get('alpha',[])
    if alpha and int(alpha[-1]['values'][0])!=0:raise ValueError('ONLINE_OPAQUE_SOURCE_CAPABILITY_ONLY')
    frames=[]
    identities=animations(source)['animations']
    for role in ('select','idle','walk'):
        a=next(a for a in animation_frames(docs[key(model['source_path'])]['directives']) if a['role']==role)
        f=a['frames'][0];indices,rgb,digest=decode(source,f['declaration']['values'][0],palette['rgb8'])
        yy,xx=np.nonzero(indices);bounds=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
        if indices.shape[0]>255 or indices.shape[1]>511:raise ValueError('ONLINE_SOURCE_ROW_GEOMETRY')
        identity=next(a for a in identities if a['model']=='He_Man' and a['role']==role)
        frames.append(dict(role=role,handle=identity['handle'],frame=0,indices=indices,offset=f['offset'],bounds=bounds,
                           source_sha256=digest,path=source.image_path(f['declaration']['values'][0]),rgb=rgb))
    foreground=np.zeros((224,256),dtype=np.uint8);original=scene_bg.overlay
    frontpaths={source.image_path(r['values'][0]) for r in docs[key(stage)]['directives'] if r['directive']=='frontpanel'}
    # Trace source compositor draws to capture foreground coverage, rather
    # than infer it from equality with the backdrop's final colors.
    original_decode=scene_bg.decode;current=[None]
    def tracked_decode(src,path,pal=None):
        current[0]=src.image_path(path)
        return original_decode(src,path,pal)
    def overlay(canvas,indices,rgb,x,y,alpha=0,transparent=True):
        if current[0] in frontpaths:
            if alpha:raise ValueError('ONLINE_FOREGROUND_ALPHA_CAPABILITY')
            h,w=indices.shape;x0=max(0,x);y0=max(0,y);x1=min(256,x+w);y1=min(224,y+h)
            if x1>x0 and y1>y0:foreground[y0:y1,x0:x1]|=(indices[y0-y:y1-y,x0-x:x1-x]!=0).astype(np.uint8)
        return original(canvas,indices,rgb,x,y,alpha,transparent)
    with patch.object(scene_bg,'decode',tracked_decode),patch.object(scene_bg,'overlay',overlay):
        backdrop,metadata=scene_bg.compose_rgb8(source,stage,dict(viewport=[256,224],camera=[0,0],actors=[]))
    pixels=rgb555(backdrop).astype('<u2')
    allcolors=set(map(int,pixels.flat))
    for f in frames:allcolors.update(map(int,rgb555(f['rgb'])[f['indices']!=0]))
    colors=sorted({c&~0x420 for c in allcolors})
    if len(colors)>236:raise ValueError('ONLINE_STATIC_SOURCE_PALETTE_CAPACITY')
    initial=colors+[None]*(236-len(colors))
    shared=dict(states=[{0:initial} for _ in range(224)],trace=[dict(scanline=y,updates=[],colors_written=0,cgram_data_bytes=0) for y in range(224)],status='STATIC_SOURCE_ASSET_PALETTE')
    report,high,low=compile_frame(pixels,(0,1,1),236,7,shared)
    report['low_chr_vram_base']=49152
    packed=high.astype(np.uint16)+3+(low.astype(np.uint16)<<8)
    known={};tiles=[];tilemap=np.zeros((32,32),dtype='<u2')
    for y in range(28):
        for x in range(32):
            tile=packed[y*8:y*8+8,x*8:x*8+8];raw=tile.astype('<u2').tobytes()
            if raw not in known:known[raw]=len(tiles);tiles.append(tile.copy())
            tilemap[y,x]=known[raw]
    if len(tiles)>768:raise ValueError('ONLINE_BACKDROP_TILE_CAPACITY')
    hi=b''.join(encode((t&255).astype(np.uint8),8) for t in tiles)
    lo=b''.join(encode((t>>8).astype(np.uint8),2) for t in tiles)
    lookup=np.zeros(256,dtype='<u2')
    used={int(i) for f in frames for i in f['indices'].flat if i}
    for i in used:
        c=palette['rgb555'][i];lookup[i]=colors.index(c&~0x420)+4+((((c>>5)&1)|(((c>>10)&1)<<1))<<8)
    folder.mkdir(parents=True,exist_ok=True)
    for name,data in [('indices.bin',high.tobytes()),('low_indices.bin',low.tobytes()),('expected.rgb555',pixels.tobytes()),
                      ('high.chr',hi),('low.chr',lo),('0-high.map',tilemap.tobytes()),('0-low.map',tilemap.tobytes()),
                      ('backdrop-pixels.bin',b''.join(t.astype('<u2').tobytes() for t in tiles)),
                      ('foreground.bin',foreground.tobytes()),('actor-palette.bin',lookup.tobytes())]:
        (folder/name).write_bytes(data)
    (folder/'initial.json').write_text(json.dumps(report.pop('initial'))+'\n')
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (folder/'layout.json').write_text(json.dumps(dict(low_chr_vram_base=49152)))
    modelid=next(m['id'] for m in registry(source)['models'] if m['identity']=='He_Man')
    for f in frames:
        (folder/(f['role']+'.indices')).write_bytes(f['indices'].tobytes())
        f['dimensions']=list(f['indices'].shape[::-1]);del f['rgb'];del f['indices']
    result=dict(schema='BYOR_COMPONENT_SOURCE_ASSETS_V1',source_pak_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest(),
                stage=metadata,model_id=modelid,model_source_sha256=model['source_sha256'] if 'source_sha256'in model else docs[key(model['source_path'])]['sha256'],
                palette_identity=palette,selected_map=selected,frames=frames,backdrop_tiles=len(tiles),
                high_palette_colors=len(colors),complete_actor_contexts=0,alpha_scope='Source actor and foreground are opaque; any alpha request rejects before rendering.')
    (folder/'source-assets.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
