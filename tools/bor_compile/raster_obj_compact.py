"""Merge exact fixed-bank 8x8 masks into legal 32x32 OBJ pieces offline.

No bank, pixel index or palette schedule changes. Transparent padding is allowed;
OAM, sprite and tile-sliver limits are checked over full hardware rectangles.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint


def unpack(mask):
    data=np.frombuffer(bytes.fromhex(mask['pixels_hex']),dtype=np.uint8)
    result=np.empty(len(data)*2,dtype=np.uint8);result[::2]=data&15;result[1::2]=data>>4
    return result.reshape(mask['height'],mask['width'])


def compact(schedule,time_limit=30,large_size=32,retain_small_geometry=False):
    if large_size not in (16,32):raise ValueError('OBJ_COMPACT_SIZE_PAIR')
    if schedule.get('status')not in('JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN','BOUNDED_FIXED_BANK_COMPACTION_NO_LEGAL_GEOMETRY','POOL_CONSTRUCTION_FIXED_SMALL_GEOMETRY_OVERFLOW') or not schedule.get('compiled_pixel_identity_verified'):
        raise ValueError('OBJ_COMPACT_VALIDATED_SCHEDULE_REQUIRED')
    original=schedule['pieces'];masks=[unpack(m)for m in schedule['piece_pixel_masks']]
    if len(original)!=len(masks) or any(p['width']!=8 or p['height']!=8 for p in original):
        raise ValueError('OBJ_COMPACT_SMALL_GRID_REQUIRED')
    if any(p['bank']not in p.get('allowed_banks',range(8))for p in original):
        raise ValueError('OBJ_COMPACT_PIECE_BANK_ELIGIBILITY')
    height=len(schedule['trace']);clip=schedule.get('horizontal_clip_limit_counted',False)
    def slivers(p):
        if not clip or p['x']==-256:return p['width']//8
        return sum(p['x']+8*c+8>0 and p['x']+8*c<256 for c in range(p['width']//8))
    def costs(pieces):
        return np.array([len(pieces)]+[sum(p['y']<=y<p['y']+p['height']for p in pieces)for y in range(height)]+[sum(slivers(p)for p in pieces if p['y']<=y<p['y']+p['height'])for y in range(height)])
    origins={}
    for p in original:
        old=origins.get(p['actor'],(p['local_x'],p['local_y']))
        origins[p['actor']]=min(old[0],p['local_x']),min(old[1],p['local_y'])
    groups={}
    for i,p in enumerate(original):
        ox,oy=origins[p['actor']]
        groups.setdefault((p['actor'],p['bank'],ox+(p['local_x']-ox)//large_size*large_size,oy+(p['local_y']-oy)//large_size*large_size),[]).append(i)
    options=[]
    for (actor,bank,lx,ly),indices in sorted(groups.items()):
        if len(indices)<2:continue
        parent=original[indices[0]];p=dict(actor=actor,bank=bank,local_x=lx,local_y=ly,
            x=parent['x']-parent['local_x']+lx,y=parent['y']-parent['local_y']+ly,width=large_size,height=large_size,rows={})
        if any('allowed_banks'in original[i]for i in indices):
            p['allowed_banks']=sorted(set.intersection(*(set(original[i].get('allowed_banks',range(8)))for i in indices)))
        pixels=np.zeros((large_size,large_size),dtype=np.uint8)
        for i in indices:
            child=original[i];x=child['local_x']-lx;y=child['local_y']-ly
            view=pixels[y:y+8,x:x+8]
            if np.any((view!=0)&(masks[i]!=0)):raise AssertionError('OBJ_COMPACT_CHILD_OVERLAP')
            view|=masks[i]
            for row,colors in child['rows'].items():p['rows'].setdefault(int(row),set()).update(colors)
        p['rows']={y:sorted(c)for y,c in p['rows'].items()}
        options.append((indices,p,pixels))
    initial=costs(original);limits=np.array([128]+[32]*height+[34]*height)
    solver=None;selected=set()
    if options:
        matrix=np.column_stack([costs([p])-costs([original[i]for i in indices])for indices,p,pixels in options])
        objective=np.ones(len(options))if retain_small_geometry else matrix[0].astype(float)
        solver=milp(objective,integrality=np.ones(len(options)),bounds=Bounds(0,1),
            constraints=LinearConstraint(matrix,-np.inf,limits-initial),options={'time_limit':time_limit})
        if solver.x is not None:selected={i for i,v in enumerate(solver.x)if v>.5}
    replaced={child for i in selected for child in options[i][0]}
    pieces=[copy.deepcopy(p)for i,p in enumerate(original)if i not in replaced]
    pixels=[m for i,m in enumerate(masks)if i not in replaced]
    for i in sorted(selected):pieces.append(options[i][1]);pixels.append(options[i][2])
    final=costs(pieces)
    if np.any(final>limits):
        if selected:raise AssertionError('OBJ_COMPACT_HARDWARE_OVERFLOW')
        result=copy.deepcopy(schedule)
        result.update(status='BOUNDED_FIXED_BANK_COMPACTION_NO_LEGAL_GEOMETRY',hardware_geometry_admitted=False,native_presentation_proven=False,
            geometry=dict(oam_entries=len(pieces),peak_sprites=int(max(final[1:height+1],default=0)),peak_tile_slivers=int(max(final[height+1:],default=0))),
            geometry_compaction=dict(candidate_merges=len(options),selected_merges=0,original_geometry=schedule['geometry'],
                objective='FEWEST_MERGES_WITHIN_HARDWARE_LIMITS'if retain_small_geometry else'MINIMUM_OAM_ENTRIES',
                solver_status=int(solver.status)if solver is not None else None,solver_message=solver.message if solver is not None else'NO_MERGE_CHOICES',
                pixel_bank_slot_identity_verified=True,native_geometry_admitted=False,universal_raster_rejected=False))
        for field in ('prepared_dma_packets','physical_slot_layout'):result.pop(field,None)
        return result
    def encoded(objects,images):
        result={}
        for p,image in zip(objects,images):
            for y,x in zip(*np.where(image!=0)):
                point=p['actor'],int(y+p['local_y']),int(x+p['local_x'])
                if point in result:raise AssertionError('OBJ_COMPACT_MASK_OVERLAP')
                result[point]=p['bank'],int(image[y,x])
        return result
    if encoded(original,masks)!=encoded(pieces,pixels):raise AssertionError('OBJ_COMPACT_INDEX_IDENTITY_FAULT')
    result=copy.deepcopy(schedule)
    result.update(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',hardware_geometry_admitted=True,
        pieces=pieces,geometry=dict(oam_entries=len(pieces),peak_sprites=int(max(final[1:height+1],default=0)),peak_tile_slivers=int(max(final[height+1:],default=0))),
        geometry_mode=f'EXACT_FIXED_BANK_{large_size}_8_COMPACTION',obsel_mode=1 if large_size==32 else 0,
        mixed_small_size=8,mixed_large_size=large_size,
        geometry_compaction=dict(candidate_merges=len(options),selected_merges=len(selected),original_geometry=schedule['geometry'],
            objective='FEWEST_MERGES_WITHIN_HARDWARE_LIMITS'if retain_small_geometry else'MINIMUM_OAM_ENTRIES',
            solver_status=int(solver.status)if solver is not None else None,solver_message=solver.message if solver is not None else 'NO_MERGE_CHOICES',
            pixel_bank_slot_identity_verified=True,native_geometry_admitted=False),
        piece_pixel_masks=[dict(width=p['width'],height=p['height'],packed_nibble_order='low then high',pixels_hex=(image.flatten()[::2]|(image.flatten()[1::2]<<4)).tobytes().hex())for p,image in zip(pieces,pixels)])
    payload=dict(pieces=pieces,pixel_masks=result['piece_pixel_masks'],trace=result['trace'])
    if result.get('scanline_math_controls_source_bound'):
        payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--time-limit',type=int,default=30)
    p.add_argument('--large-size',type=int,choices=(16,32),default=32)
    p.add_argument('--retain-small-geometry',action='store_true')
    a=p.parse_args();r=compact(json.loads(a.schedule.read_text()),a.time_limit,a.large_size,a.retain_small_geometry)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(geometry=r['geometry'],compaction=r['geometry_compaction'])))


if __name__=='__main__':main()
