"""Joint fixed-bank OBJ probe with exact source SCREEN precompositing.

This is an explicit-pose offline candidate. It does not admit a live compositor,
background/foreground architecture, native timing or source reachability.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from compiler import Source,key
from source_profile import document,discover
from source_palette import model_palettes,select_model_palette
from source_scene_bg import compose_rgb8,overlay
from source_bg_feasibility import decode,rgb555
from raster_palette import pieces_for_grid,assign_banks,schedule
from raster_bank_search import assign as search_banks
from raster_palette_interval import interval_bound

def prepare(source,stage,scene):
 expected,metadata=compose_rgb8(source,stage,scene);h,w=expected.shape[:2];canvas=np.zeros_like(expected);actors=[];owner=np.full((h,w),-1,dtype=np.int16)
 if (w,h)!=(256,224):raise ValueError('JOINT_CONTEXT_NATIVE_VIEWPORT_REQUIRED')
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};models=discover(source,docs)['models']
 for layer in metadata['layers']:
  palette=None
  if layer['kind'].startswith('actor:'):
   model=next(m for m in models if layer['kind']=='actor:'+m['name']);pal,_=select_model_palette(model_palettes(source,model),layer['requested_map']);palette=pal['rgb8']
  indices,rgb,_=decode(source,layer['path'],palette)
  if layer['source_flip']:indices=indices[:,::-1];rgb=rgb[:,::-1]
  x,y=layer['position'];overlay(canvas,indices,rgb,x,y,layer['alpha'],layer['kind']!='background')
  ih,iw=indices.shape;x0=max(0,x);y0=max(0,y);x1=min(w,x+iw);y1=min(h,y+ih)
  if x1>x0 and y1>y0:
   mask=indices[y0-y:y1-y,x0-x:x1-x]!=0 if layer['kind']!='background'else np.ones((y1-y0,x1-x0),dtype=bool)
   view=owner[y0:y1,x0:x1];view[mask]=len(actors)if layer['kind'].startswith('actor:')else-1
  if not layer['kind'].startswith('actor:'):continue
  ih,iw=indices.shape;pixels=np.full((ih,iw),-1,dtype=np.int32);x0=max(0,x);y0=max(0,y);x1=min(w,x+iw);y1=min(h,y+ih)
  if x1>x0 and y1>y0:
   mask=indices[y0-y:y1-y,x0-x:x1-x]!=0;view=pixels[y0-y:y1-y,x0-x:x1-x];colors=rgb555(canvas[y0:y1,x0:x1]);view[mask]=colors[mask]
  actors.append(dict(metadata=layer,pixels=pixels,left=x,top=y))
 if not np.array_equal(expected,canvas):raise AssertionError('SOURCE_LAYER_REPLAY_MISMATCH')
 for i,a in enumerate(actors):
  x,y=a['left'],a['top'];ih,iw=a['pixels'].shape;x0=max(0,x);y0=max(0,y);x1=min(w,x+iw);y1=min(h,y+ih)
  a['metadata']['pre_occlusion_pixels']=int(np.sum(a['pixels']>=0))
  if x1>x0 and y1>y0:a['pixels'][y0-y:y1-y,x0-x:x1-x][owner[y0:y1,x0:x1]!=i]=-1
  a['metadata']['final_visible_pixels']=int(np.sum(a['pixels']>=0))
 background,_=compose_rgb8(source,stage,dict(scene,actors=[]));replay=rgb555(background)
 for a in actors:
  for ly,lx in zip(*np.where(a['pixels']>=0)):replay[ly+a['top'],lx+a['left']]=a['pixels'][ly,lx]
 if not np.array_equal(replay,rgb555(expected)):raise AssertionError('SOURCE_VISIBLE_OBJ_COMPOSITE_MISMATCH')
 return actors,metadata,expected

def geometry(actors,mode):
 pieces=[]
 for i,actor in enumerate(actors):
  pixels=actor['pixels'];cells=pieces_for_grid(pixels,(32,32))if mode=='mixed'else pieces_for_grid(pixels,(8,8))
  local=[]
  for cell in cells:
   if mode=='mixed'and any(len(cs)>15 for cs in cell['rows'].values()):
    x,y=cell['x'],cell['y'];children=pieces_for_grid(pixels[y:y+32,x:x+32],(8,8))
    for p in children:p['x']+=x;p['y']+=y;p['rows']={yy+y:cs for yy,cs in p['rows'].items()};local.append(p)
   else:local.append(cell)
  for p in local:
   p.update(actor=i,local_x=p['x'],local_y=p['y']);p['x']+=actor['left'];p['y']+=actor['top'];p['rows']={yy+actor['top']:cs for yy,cs in p['rows'].items()if 0<=yy+actor['top']<224};pieces.append(p)
 return pieces

def probe(source,stage,scene,mode,time_limit,lookahead):
 actors,metadata,expected=prepare(source,stage,scene);pieces=geometry(actors,mode);height=expected.shape[0]
 geom=dict(oam_entries=len(pieces),peak_sprites_per_line=max((sum(p['y']<=y<p['y']+p['height']for p in pieces)for y in range(height)),default=0),peak_tile_slivers_per_line=max((sum(p['width']//8 for p in pieces if p['y']<=y<p['y']+p['height'])for y in range(height)),default=0),tile_sliver_count_policy='conservative complete width of every visible object rectangle')
 line_sets=[{c for p in pieces for c in p['rows'].get(y,[])}for y in range(height)]
 r=dict(schema='BYOR_JOINT_SCREEN_OBJ_RASTER_V1',source_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest(),source_context_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),metadata=metadata,geometry=geom,geometry_mode=mode,obsel_mode=1 if mode=='mixed'else 0,all_actor_banks_scheduled_together=True,static_actor_palettes_reserved=False,final_occlusion_applied=True,source_visible_composite_verified=True,alpha_policy='BOR4086_SCREEN_RGB8_PRECOMPOSITED_FOR_EXPLICIT_SOURCE_CONTEXT',direct_obj_color_math_used=False,maximum_scanline_colors=max(map(len,line_sets),default=0),maximum_adjacent_union=max((len(line_sets[y-1]|line_sets[y])for y in range(1,height)),default=0),source_pixels_colors_reduced=False,no_color_reduction=True,native_timing_admitted=False,live_compositor_admitted=False,production_static_path_changed=False,motu_gameplay_proven=False,scope='Explicit pose and horizontal camera; no HUD/shadows/quake or reachability. Native presentation and live source pixel-index remapping unproven.')
 r['no_math_palette_interval_bound']=interval_bound(line_sets)
 r['no_math_palette_interval_bound']['scope']='Exact precomposited RGB555 OBJ outputs in the explicit pose. Excludes alternative BG/OBJ math decompositions; not a universal raster rejection.'
 if geom['oam_entries']>128 or geom['peak_sprites_per_line']>32 or geom['peak_tile_slivers_per_line']>34:
  r.update(status='CANDIDATE_GEOMETRY_OVERFLOW',universal_raster_rejection=False);return r
 assignment=search_banks(pieces,tuple(range(8)),min(20,time_limit));r['bounded_bank_search']=dict(assignment)
 if 'assignment'not in assignment:assignment=assign_banks(pieces,tuple(range(8)),time_limit)
 r.update(assignment)
 if 'assignment'not in assignment:return r
 trace,states=schedule(pieces,assignment['assignment'],height,lookahead);recovered=[np.full_like(a['pixels'],-1)for a in actors];indices=[np.zeros_like(a['pixels'],dtype=np.uint8)for a in actors]
 for p,bank in zip(pieces,assignment['assignment']):
  a=actors[p['actor']]
  for y,colors in p['rows'].items():
   ly=y-a['top']
   for lx in range(p['local_x'],min(p['local_x']+p['width'],a['pixels'].shape[1])):
    color=int(a['pixels'][ly,lx])
    if color>=0:
     slot=states[y][bank].index(color);indices[p['actor']][ly,lx]=slot+1;recovered[p['actor']][ly,lx]=states[y][bank][slot]
 if any(not np.array_equal(a['pixels'],b)for a,b in zip(actors,recovered)):raise AssertionError('SOURCE_ACTOR_PIXEL_IDENTITY_FAULT')
 counts=[v['colors_written']for v in trace[1:]]
 r.update(status='JOINT_CONTEXT_SLOT_SCHEDULE_PROVEN',piece_bank_assignment=assignment['assignment'],pieces=pieces,trace=trace,lookahead_lines=lookahead,peak_scheduled_writes=max(counts,default=0),peak_cgram_data_bytes=2*max(counts,default=0),average_writes=float(np.mean(counts)),worst_scanline=1+int(np.argmax(counts)),actor_pixel_identity_verified=True,compiled_indices_sha256=[hashlib.sha256(v.tobytes()).hexdigest()for v in indices])
 return r

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--stage',required=True);p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--geometry',choices=('mixed','small'),default='mixed');p.add_argument('--time-limit',type=int,default=60);p.add_argument('--lookahead',type=int,default=16);a=p.parse_args();r=probe(Source(a.source),a.stage,json.loads(a.scene.read_text()),a.geometry,a.time_limit,a.lookahead);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k in('status','geometry','maximum_scanline_colors','maximum_adjacent_union','peak_scheduled_writes','peak_cgram_data_bytes','worst_scanline','message')}))
if __name__=='__main__':main()
