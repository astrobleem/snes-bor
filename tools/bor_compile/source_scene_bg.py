"""Lossless BG context proof with source panels, actor poses and SCREEN alpha.

This offline probe supports horizontal cameras and one ordinary panel order. Explicit
pose/tie order is an input; no gameplay reachability or live compositor claim.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from compiler import Source,key
from source_profile import document,discover
from source_palette import model_palettes,select_model_palette
from dialect_4086 import animation_frames
from source_bg_feasibility import decode,rgb555,compile_canvas
from source_layer_position_4086 import legacy_layer,placements,f32


def overlay(canvas,indices,rgb,x,y,alpha=0,transparent=True):
    h,w=canvas.shape[:2];ih,iw=indices.shape
    x0=max(0,x);y0=max(0,y);x1=min(w,x+iw);y1=min(h,y+ih)
    if x1<=x0 or y1<=y0:return 0
    region=canvas[y0:y1,x0:x1];source=rgb[y0-y:y1-y,x0-x:x1-x]
    mask=indices[y0-y:y1-y,x0-x:x1-x]!=0 if transparent else np.ones(region.shape[:2],dtype=bool)
    if alpha==1:source=255-((255-source)*(255-region)//255)
    elif alpha!=0:raise ValueError('SOURCE_ALPHA_NOT_IMPLEMENTED_IN_CONTEXT_PROBE')
    region[mask]=source[mask]
    return int(mask.sum())


def compose_rgb8(source,stage,scene):
    camera=scene.get('camera',[0,0])
    if len(camera)!=2:raise ValueError('CONTEXT_CAMERA_ARITY')
    camera=tuple(map(f32,camera))
    if scene.get('quake',[0,0])!=[0,0]:raise ValueError('CONTEXT_QUAKE_NOT_IMPLEMENTED')
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    models=discover(source,docs)['models']; rows=docs[key(stage)]['directives']
    w,h=scene.get('viewport',[256,224]);canvas=np.zeros((h,w,3),dtype=np.int32);layers=[]
    def draw(path,x,y,kind,transparent=True,palette=None,alpha=0,flip=False):
        indices,rgb,digest=decode(source,path,palette)
        if flip:indices=indices[:,::-1];rgb=rgb[:,::-1]
        visible=overlay(canvas,indices,rgb,int(x),int(y),alpha,transparent)
        layers.append(dict(kind=kind,path=source.image_path(path),sha256=digest,
            source_dimensions=list(indices.shape[::-1]),position=[int(x),int(y)],alpha=alpha,
            visible_source_pixels=visible,source_flip=flip))
    backgrounds=[r for r in rows if r['directive']=='background']
    panels=[r for r in rows if r['directive']=='panel']
    orders=[r for r in rows if r['directive']=='order']
    if len(backgrounds)!=1 or len(panels)!=1 or len(orders)!=1 or orders[0]['values']!=['a']:
        raise ValueError('STAGE_LAYER_LAYOUT_NOT_IMPLEMENTED_IN_CONTEXT_PROBE')
    if any(v.lower()!='none' for v in panels[0]['values'][1:]):
        raise ValueError('PANEL_SECONDARY_LAYERS_NOT_IMPLEMENTED')
    if len(backgrounds[0]['values'])!=1:raise ValueError('BACKGROUND_LAYER_PARAMETERS_UNBOUND')
    if any(r['directive']in ('bglayer','fglayer','layer','water','rock','rocking','bgspeed')for r in rows):
        raise ValueError('STAGE_ADDITIONAL_LAYER_PARAMETERS_UNBOUND')
    direction=[r['values'] for r in rows if r['directive']=='direction']
    if direction and direction[-1]not in (['right'],['left'],['both'],['rightleft'],['leftright']):
        raise ValueError('CONTEXT_VERTICAL_SCROLL_NOT_IMPLEMENTED')
    def layer(path,kind,transparent=True,ordinal=0,front_count=0):
        indices,_,_=decode(source,path)
        spec=legacy_layer(kind,indices.shape[::-1],ordinal=ordinal,front_count=front_count)
        for x,y in placements(**spec,camera=camera,viewport=(w,h)):
            draw(path,x,y,kind,transparent)
    layer(backgrounds[0]['values'][0],'background',False)
    layer(panels[0]['values'][0],'panel')
    for actor in sorted(scene['actors'],key=lambda a:(a['position'][1],a['order'])):
        model=next(m for m in models if m['name'].casefold()==actor['model'].casefold())
        anim=next(a for a in animation_frames(docs[key(model['source_path'])]['directives']) if a['role']==actor['animation'])
        f=anim['frames'][actor['frame']];x,z,a=actor['position']
        direction=actor.get('direction',1)
        if direction not in (0,1):raise ValueError('CONTEXT_DIRECTION_REQUIRED')
        pal,selected_map=select_model_palette(model_palettes(source,model),actor.get('map',0))
        if pal is None:raise ValueError('MODEL_PALETTE_AUTHORITY_REQUIRED')
        alpha_rows=model['properties'].get('alpha',[])
        alpha=int(alpha_rows[-1]['values'][0]) if alpha_rows else 0
        path=f['declaration']['values'][0]
        anchor_x=int(f32(f32(x)-int(camera[0])))
        anchor_y=int(f32(f32(f32(z)-f32(a))-int(camera[1])))
        left=anchor_x-f['offset'][0]
        if direction==0:
            indices,_,_=decode(source,path,pal['rgb8'])
            left=anchor_x-(indices.shape[1]-f['offset'][0])
        draw(path,left,anchor_y-f['offset'][1],
             'actor:'+model['name'],palette=pal['rgb8'],alpha=alpha,flip=(direction==0))
        layers[-1].update(requested_map=actor.get('map',0),selected_map=selected_map,
            source_model_type=model['type'],
            palette_source_path=pal['source_path'],palette_asset_sha256=pal['asset_sha256'])
    front=[r for r in rows if r['directive']=='frontpanel']
    for ordinal,row in enumerate(front):
        if len(row['values'])!=1:raise ValueError('FRONTPANEL_SECONDARY_LAYERS_NOT_IMPLEMENTED')
        layer(row['values'][0],'frontpanel',ordinal=ordinal,front_count=len(front))
    metadata=dict(stage=stage,stage_sha256=docs[key(stage)]['sha256'],scene=scene,layers=layers,
        alpha='BOR4086_SCREEN_RGB8_THEN_RGB555_HIGH_BITS',
        alpha_source_dimensions=[layer['source_dimensions'] for layer in layers if layer['alpha']],
        camera=list(camera),layer_position_authority='Pinned load_layer/load_level/draw_scrolled_bg and screenx/screeny, horizontal stage',
        scope='Explicit source scene pose/tie order and horizontal camera, no HUD/shadows/quake. No runtime reachability claim.',
        all_actor_models_preserved=True)
    return canvas,metadata


def probe(source,stage,scene,capacity=175,write_budget=7,export=None):
    canvas,metadata=compose_rgb8(source,stage,scene)
    compiled=compile_canvas(rgb555(canvas),capacity,write_budget,True,export)
    return dict(compiled,**metadata)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--stage',required=True);p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--capacity',type=int,default=175)
    p.add_argument('--write-budget',type=int,default=7);a=p.parse_args()
    r=probe(Source(a.source),a.stage,json.loads(a.scene.read_text()),a.capacity,a.write_budget,a.output.with_suffix(''))
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('trace','layers','scene')}))


if __name__=='__main__':main()
