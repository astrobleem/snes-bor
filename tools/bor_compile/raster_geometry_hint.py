"""Source-exact small masks for offline geometry search, never native admission."""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand


def construct(source,origin=(0,0)):
    if len(origin)!=2 or any(type(v)is not int or not 0<=v<8 for v in origin):raise ValueError('GEOMETRY_HINT_ORIGIN')
    _,_,images=demand(source);height=len(source['trace']);ox,oy=origin
    state={b:[None]*15 for b in range(8)};states=[]
    for row in source['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        states.append(copy.deepcopy(state))
    groups={};expected={};screen=set()
    for p,image in zip(source['pieces'],images):
        for ly,lx in zip(*np.where(image>=0)):
            x,y=int(p['local_x']+lx),int(p['local_y']+ly);sx,sy=int(p['x']+lx),int(p['y']+ly)
            point=p['actor'],x,y
            if point in expected or(sy,sx)in screen:raise ValueError('GEOMETRY_HINT_SOURCE_OVERLAP')
            word=int(image[ly,lx]);expected[point]=p['bank'],word;screen.add((sy,sx))
            gx,gy=(x-ox)//8*8+ox,(y-oy)//8*8+oy
            key=p['actor'],p['bank'],gx,gy,sx-x,sy-y
            if key not in groups:groups[key]=(np.zeros((8,8),dtype=np.uint8),set(p.get('allowed_banks',range(8))))
            encoded,allowed=groups[key];allowed.intersection_update(p.get('allowed_banks',range(8)))
            if p['bank']not in allowed:raise ValueError('GEOMETRY_HINT_BANK_ELIGIBILITY')
            encoded[y-gy,x-gx]=states[sy][p['bank']].index(word)+1
    pieces=[];masks=[]
    for(actor,bank,gx,gy,left,top),(encoded,allowed)in sorted(groups.items()):
        pieces.append(dict(actor=actor,bank=bank,local_x=gx,local_y=gy,x=gx+left,y=gy+top,width=8,height=8,allowed_banks=sorted(allowed)))
        flat=encoded.flatten();masks.append(dict(width=8,height=8,packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    clip=source.get('horizontal_clip_limit_counted',False)
    def slivers(p):return int(not clip or p['x']==-256 or p['x']+8>0 and p['x']<256)
    geometry=dict(oam_entries=len(pieces),peak_sprites=max((sum(p['y']<=y<p['y']+8 for p in pieces)for y in range(height)),default=0),
        peak_tile_slivers=max((sum(slivers(p)for p in pieces if p['y']<=y<p['y']+8)for y in range(height)),default=0))
    result=copy.deepcopy(source)
    for key in('physical_slot_layout','prepared_dma_packets','geometry_compaction','bank_subdivision','bounded_subdivision_search','physical_slot_refinement'):result.pop(key,None)
    result.update(status='SOURCE_EXACT_GEOMETRY_SEARCH_HINT',pieces=pieces,piece_pixel_masks=masks,geometry=geometry,
        hardware_geometry_admitted=False,native_presentation_proven=False,source_operand_identity_verified=True,
        mixed_small_size=8,mixed_large_size=16,obsel_mode=0,piece_bank_assignment=[p['bank']for p in pieces])
    replay={};indices=np.zeros((height,256),dtype=np.uint8)
    for p,image in zip(pieces,demand(result,allow_geometry_hint=True)[2]):
        for ly,lx in zip(*np.where(image>=0)):
            replay[p['actor'],p['local_x']+int(lx),p['local_y']+int(ly)]=p['bank'],int(image[ly,lx])
            y,x=p['y']+int(ly),p['x']+int(lx);indices[y,x]=128+16*p['bank']+states[y][p['bank']].index(int(image[ly,lx]))+1
    if expected!=replay:raise AssertionError('GEOMETRY_HINT_INDEPENDENT_SOURCE_REPLAY')
    payload=dict(pieces=pieces,pixel_masks=masks,trace=result['trace'])
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result.update(compiled_schedule_sha256=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),
        compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),geometry_search_hint=dict(origin=list(origin),
        input_geometry=source.get('geometry'),geometry=geometry,source_pixels=len(expected),source_operands_and_banks_exact=True,
        input_palette_schedule_unchanged=True,hardware_candidate=False,native_timing_admitted=False,no_color_reduction=True))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--origin',type=int,nargs=2,default=(0,0));a=p.parse_args();r=construct(json.loads(a.schedule.read_text()),a.origin)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['geometry_search_hint']))


if __name__=='__main__':main()
