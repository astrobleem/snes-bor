"""Lossless direct-color BG1 plus raster 4bpp BG2 residual experiment.

With BG1 tile palette zero, direct RGB is RRR00/GGG00/BB000. BG2 adds
the remaining 2/2/3 bits. Its fixed tile bank is solved over all eight rows.
BG2 is also on main screen to represent direct-index-zero pixels opaquely.
This is an isolated offline alternative, not production/native admission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from raster_palette import assign_banks,pieces_for_grid,schedule


def split(pixels):
 p=np.asarray(pixels,dtype=np.uint16)
 high=((p&31)>>2)|((((p>>5)&31)>>2)<<3)|((((p>>10)&31)>>3)<<6)
 low=p&np.uint16(3|(3<<5)|(7<<10))
 restored=((high&7)<<2)|((high&0x38)<<4)|((high&0xc0)<<7)
 if not np.array_equal(restored+low,p):raise AssertionError('DIRECT_BG_RGB555_IDENTITY')
 return high.astype(np.uint8),low


def constructive_banks(pieces,attempts=256):
 """Bounded best-fit search; a returned assignment is checked row by row.

 Failure is only a heuristic search limit. The exact solver remains fallback.
 """
 rng=np.random.default_rng(4086)
 rows=[{y:set(cs)for y,cs in p['rows'].items()}for p in pieces]
 for attempt in range(attempts):
  unions=[{}for _ in range(8)];assignment=[None]*len(pieces)
  order=sorted(range(len(pieces)),key=lambda i:(-max(map(len,rows[i].values())), -sum(map(len,rows[i].values())),float(rng.random()) if attempt else i))
  if attempt%4==3:order=list(rng.permutation(len(pieces)))
  for i in order:
   options=[]
   for bank in range(8):
    sizes=[len(unions[bank].get(y,set())|cs)for y,cs in rows[i].items()]
    if max(sizes)>15:continue
    added=sum(len(cs-unions[bank].get(y,set()))for y,cs in rows[i].items())
    options.append((added,max(sizes),float(rng.random()) if attempt else bank,bank))
   if not options:break
   bank=min(options)[-1];assignment[i]=bank
   for y,cs in rows[i].items():unions[bank].setdefault(y,set()).update(cs)
  else:
   for bank in range(8):
    for y in {y for p in rows for y in p}:
     colors={c for p,b in zip(rows,assignment)if b==bank for c in p.get(y,set())}
     if len(colors)>15:raise AssertionError('CONSTRUCTIVE_FIXED_BANK_OVERFLOW')
   return dict(status='FIXED_BANK_ASSIGNMENT_PROVEN',assignment=assignment,method='bounded constructive best-fit',attempt=attempt)
 return None


def derive(pixels,*,time_limit=2,lookahead=16,obj_chr_bytes=0,promoted=None):
 high,low=split(pixels);height,width=pixels.shape
 if width%8 or height%8:raise ValueError('DIRECT_BG_WHOLE_8X8_TILES_REQUIRED')
 pieces=pieces_for_grid(low.astype(np.int32),(8,8));assignment=[];bands=[];previous={b:set()for b in range(8)}
 for y in range(0,height,8):
  slab=[p for p in pieces if p['y']==y];result=constructive_banks(slab)or assign_banks(slab,tuple(range(8)),time_limit)
  band=dict(scanline=y,status=result['status'],method=result.get('method','MILP'));bands.append(band);print(json.dumps(band),flush=True)
  if 'assignment'not in result:
   return dict(status='DIRECT_BG_BANK_ASSIGNMENT_UNPROVEN',bands=bands,no_color_reduction=True,native_admitted=False),None
  chosen=result['assignment'];incoming={b:{c for p,a in zip(slab,chosen)if a==b for c in p['rows'].get(y,[])}for b in range(8)}
  # Labels are symmetric within a slab. Retain as many boundary identities as
  # possible without altering the proven fixed bank selection of any tile.
  costs=np.array([[-len(incoming[a]&previous[b])for b in range(8)]for a in range(8)])
  rr,cc=linear_sum_assignment(costs);remap=dict(zip(map(int,rr),map(int,cc)));chosen=[remap[b]for b in chosen]
  assignment.extend(chosen);previous={b:{c for p,a in zip(slab,chosen)if a==b for c in p['rows'].get(y+7,[])}for b in range(8)}
 trace,states=schedule(pieces,assignment,height,lookahead=lookahead,prefetch_write_budget=8,capacity=15)
 indices=np.zeros(pixels.shape,dtype=np.uint8);tilebanks=np.zeros((height//8,width//8),dtype=np.uint8)
 for piece,bank in zip(pieces,assignment):
  x,y=piece['x'],piece['y'];tilebanks[y//8,x//8]=bank
  for row in range(y,y+8):
   slots=states[row][bank]
   for column in range(x,x+8):indices[row,column]=slots.index(int(low[row,column]))+1
 recovered=np.zeros(pixels.shape,dtype=np.uint16)
 for y in range(height):
  for x in range(width):recovered[y,x]=states[y][int(tilebanks[y//8,x//8])][int(indices[y,x])-1]
 if not np.array_equal(recovered,low):raise AssertionError('DIRECT_BG_LOW_PALETTE_IDENTITY')
 high_tiles=len({high[y:y+8,x:x+8].tobytes()for y in range(0,height,8)for x in range(0,width,8)})
 low_tiles=len({indices[y:y+8,x:x+8].tobytes()for y in range(0,height,8)for x in range(0,width,8)})
 maps=2*(width//8)*(32 if height<=256 else height//8)*2
 used=high_tiles*64+low_tiles*32+maps+obj_chr_bytes
 opaque_low_zero=int(np.sum((high==0)&(pixels!=0)));writes=[t['colors_written']for t in trace[1:]]
 report=dict(schema='BYOR_DIRECT_BG_FEASIBILITY_V1',status='OFFLINE_DIRECT_BG_COMPONENTS_PROVEN'if used<=65536 and high_tiles<=1024 and low_tiles<=1024 else'DIRECT_BG_VRAM_CAPACITY_LIMIT',
  source_rgb555_sha256=hashlib.sha256(pixels.astype('<u2').tobytes()).hexdigest(),bands=bands,tile_bank_assignment=assignment,
  required_hardware=dict(mode=3,CGWSEL=3,CGADSUB=1,main_layers=19,sub_layers=2,BG1_tile_palette=0,ordinary_OBJ_priority=1,promoted_BG1_and_BG2_priority=1),
  low_palette_banks=list(range(8)),low_opaque_slots_per_bank=15,low_frame_colors=len(set(map(int,low.flat))),low_peak_scanline_colors=max(len(set(map(int,row)))for row in low),
  source_direct_zero_nonzero_pixels=opaque_low_zero,low_zero_uses_opaque_slot=True,main_BG2_required_for_opacity=True,
  high_tiles=high_tiles,low_tiles=low_tiles,high_chr_bytes=high_tiles*64,low_chr_bytes=low_tiles*32,map_bytes=maps,obj_chr_bytes=obj_chr_bytes,VRAM_bytes=used,
  peak_changed_palette_words=max(writes,default=0),peak_changed_cgram_bytes=2*max(writes,default=0),average_changed_palette_words=sum(writes)/len(writes)if writes else 0,
  palette_trace=trace,slot_states=states,slot_schedule_policy='retention/farthest-future eviction with bounded empty-slot prefetch; not minimum bandwidth',
  transfer_descriptors_compiled=False,hardware_timing_proven=False,native_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 return report,dict(high=high,low=indices,tilebanks=tilebanks)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--canvas',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--time-limit',type=float,default=2);p.add_argument('--lookahead',type=int,default=16);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 data=a.canvas.read_bytes();authority=json.loads(a.authority.read_text());assert hashlib.sha256(data).hexdigest()==authority['bg_canvas_sha256']
 pixels=np.frombuffer(data,dtype='<u2').reshape(224,256);report,assets=derive(pixels,time_limit=a.time_limit,lookahead=a.lookahead,obj_chr_bytes=authority['obj_chr_bytes'])
 report['canvas_authority_sha256']=hashlib.sha256(a.authority.read_bytes()).hexdigest()
 if assets is not None:
  for name,array in assets.items():(a.output/(name+'.bin')).write_bytes(array.tobytes())
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])


if __name__=='__main__':main()
