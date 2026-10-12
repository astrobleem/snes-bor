"""Repack exact fixed-bank pixels with sampled, non-grid legal OBJ rectangles.

This bounded candidate family is not a universal geometry feasibility test.
Palette slots, source ownership, words, controls and write times stay fixed.
Every selected hardware rectangle counts, including transparent padding.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack
from raster_slot_greedy import demand


def cover(schedule,time_limit=30,large_size=16,geometry_reservation=None,repair_hint=False,solver_backend='cp-sat'):
    from ortools.sat.python import cp_model
    demand(schedule)
    if large_size not in(16,32)or time_limit<=0:raise ValueError('MASK_COVER_DOMAIN')
    if type(repair_hint)is not bool:raise ValueError('MASK_COVER_REPAIR_HINT_DOMAIN')
    if solver_backend not in('cp-sat','highspy'):raise ValueError('MASK_COVER_SOLVER_BACKEND')
    height=len(schedule['trace'])
    reserve=dict(oam_entries=0,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height)
    if geometry_reservation is not None:
        if not isinstance(geometry_reservation,dict)or set(geometry_reservation)!=set(reserve):raise ValueError('MASK_COVER_RESERVATION')
        reserve=copy.deepcopy(geometry_reservation)
        if(type(reserve['oam_entries'])is not int or not 0<=reserve['oam_entries']<=128 or
           any(not isinstance(reserve[k],list)or len(reserve[k])!=height or any(type(v)is not int or not 0<=v<=limit for v in reserve[k])
               for k,limit in [('sprites_per_line',32),('tile_slivers_per_line',34)])):
            raise ValueError('MASK_COVER_RESERVATION')
    planes={};original={};origins={};eligibility={};input_rectangles={};visible=set()
    for p,mask in zip(schedule['pieces'],schedule['piece_pixel_masks']):
        actor=p.get('actor',0);key=actor,p['bank'];image=unpack(mask)
        origin=p['x']-p.get('local_x',p['x']),p['y']-p.get('local_y',p['y'])
        if actor in origins and origins[actor]!=origin:raise ValueError('MASK_COVER_ACTOR_ORIGIN')
        origins[actor]=origin
        if p['width']==p['height']and p['width']in(8,large_size):
            input_rectangles.setdefault(key,set()).add((p['width'],p['x'],p['y']))
        for ly,lx in zip(*np.where(image)):
            y,x=int(p['y']+ly),int(p['x']+lx);slot=int(image[ly,lx]);identity=actor,y,x
            if identity in original:raise ValueError('MASK_COVER_SOURCE_OVERLAP')
            if (y,x)in visible:raise ValueError('MASK_COVER_GLOBAL_VISIBLE_OVERLAP')
            visible.add((y,x))
            original[identity]=(p['bank'],slot)
            planes.setdefault(key,{})[y,x]=slot
            eligibility[identity]=set(p.get('allowed_banks',range(8)))
    model=cp_model.CpModel();variables=[];candidates=[];owners={};by_line={};plane_rows={};tile_lower=[0]*height;raw_candidates=0
    for (actor,bank),points in sorted(planes.items()):
        horizontal={}
        for y,x in points:horizontal.setdefault(y,[]).append(x)
        lower={}
        for y,xs in horizontal.items():
            end=-1000;count=0
            for x in sorted(xs):
                if x>end:count+=1;end=x+7
            lower[y]=count;tile_lower[y]+=count
        candidates_xy=set(input_rectangles.get((actor,bank),()))
        for y,x in points:
            for size in(8,large_size):
                for dx in(0,size//2,size-1):
                    for dy in(0,size//2,size-1):
                        xx,yy=x-dx,y-dy
                        if -256<=xx<256 and -256<=yy<256:candidates_xy.add((size,xx,yy))
        # Equivalent opaque masks with identical full hardware row costs need
        # only one x-position. Prefer an input rectangle so its soft hint survives.
        # Different vertical padding or tile widths remain separate candidates.
        equivalent={}
        for size,x,y in sorted(candidates_xy):
            covered=[(yy,xx)for yy in range(max(0,y),min(height,y+size))for xx in range(max(0,x),min(256,x+size))if(yy,xx)in points]
            if not covered:continue
            raw_candidates+=1
            identity=(size,max(0,y),min(height,y+size),tuple(covered))
            if identity not in equivalent or (size,x,y)in input_rectangles.get((actor,bank),()):
                equivalent[identity]=(size,x,y,covered)
        for size,x,y,covered in equivalent.values():
            index=len(variables);v=model.new_bool_var('mask'+str(index));variables.append(v)
            model.add_hint(v,int((size,x,y)in input_rectangles.get((actor,bank),())))
            candidates.append((actor,bank,size,x,y,covered))
            for point in covered:owners.setdefault((actor,bank,*point),[]).append(v)
            for yy in range(max(0,y),min(height,y+size)):
                by_line.setdefault(yy,[]).append((v,size//8))
                plane_rows.setdefault((actor,bank,yy),[]).append((v,size//8))
        # Exact minimum horizontal coverage by eight-pixel intervals. These
        # cuts also hold for unaligned rectangles and strengthen the LP without
        # requiring the solver to derive interval coverage from individual pixels.
        for y,count in lower.items():
            entries=plane_rows[actor,bank,y]
            model.add(sum(v*w for v,w in entries)>=count)
            model.add(sum(v for v,w in entries)>=(count+large_size//8-1)//(large_size//8))
    for options in owners.values():model.add(sum(options)==1)
    model.add(sum(variables)<=128-reserve['oam_entries'])
    peak=model.new_int_var(0,34,'combinedPeakTiles')
    combined_lower=max(a+b for a,b in zip(tile_lower,reserve['tile_slivers_per_line']))
    model.add(peak>=combined_lower)
    for y,entries in by_line.items():
        model.add(sum(v for v,w in entries)<=32-reserve['sprites_per_line'][y])
        tiles=sum(v*w for v,w in entries)+reserve['tile_slivers_per_line'][y]
        model.add(tiles<=34);model.add(peak>=tiles)
    model.minimize(129*peak+sum(variables))
    if solver_backend=='highspy':
        from raster_bank_residency import solve_linear
        value,statistics=solve_linear(model,time_limit,native_highs=True)
    else:
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
        if repair_hint:solver.parameters.repair_hint=True;solver.parameters.hint_conflict_limit=50000
        status=solver.solve(model)
        value=solver.value if status in(cp_model.FEASIBLE,cp_model.OPTIMAL)else None
        statistics=dict(solver_backend=solver_backend,solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
            solver_objective_lower_bound=solver.best_objective_bound)
    report=dict(schema='BYOR_FIXED_BANK_PIXEL_RECTANGLE_COVER_V1',status='BOUNDED_FIXED_BANK_PIXEL_RECTANGLE_COVER_NO_CANDIDATE',
        **statistics,candidate_rectangles=len(candidates),raw_candidate_rectangles=raw_candidates,
        equivalent_candidate_rectangles_removed=raw_candidates-len(candidates),
        soft_input_rectangle_hint=True,repair_hint=repair_hint,repair_hint_consumed=repair_hint and solver_backend=='cp-sat',
        source_bank_mask_horizontal_tile_lower_bound=tile_lower,combined_horizontal_tile_lower_bound=combined_lower,
        candidate_family='OPAQUE_PIXEL_CORNER_OR_MIDPOINT_PLUS_INPUT_RECTANGLES',obj_size_pair=[8,large_size],geometry_reservation=reserve,
        fixed_bank_and_slot_per_source_pixel=True,palette_writes_unchanged=True,universal_raster_rejected=False,
        concurrent_palette_or_layer_admitted=False,native_timing_admitted=False,no_color_reduction=True)
    if value is None:return report
    pieces=[];masks=[];replayed={};indices=np.zeros((height,256),dtype=np.uint8)
    for candidate,v in zip(candidates,variables):
        if not value(v):continue
        actor,bank,size,x,y,points=candidate;image=np.zeros((size,size),dtype=np.uint8);allowed=set(range(8))
        for yy,xx in points:
            identity=actor,yy,xx;slot=planes[actor,bank][yy,xx]
            if identity in replayed:raise AssertionError('MASK_COVER_OUTPUT_OVERLAP')
            replayed[identity]=bank,slot;allowed&=eligibility[identity]
            image[yy-y,xx-x]=slot;indices[yy,xx]=128+16*bank+slot
        if bank not in allowed:raise AssertionError('MASK_COVER_BANK_ELIGIBILITY')
        ox,oy=origins[actor]
        pieces.append(dict(actor=actor,bank=bank,x=x,y=y,local_x=x-ox,local_y=y-oy,width=size,height=size,allowed_banks=sorted(allowed)))
        flat=image.flatten();masks.append(dict(width=size,height=size,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    if replayed!=original:raise AssertionError('MASK_COVER_PIXEL_BANK_SLOT_IDENTITY')
    sprites=[sum(p['y']<=y<p['y']+p['height']for p in pieces)for y in range(height)]
    tiles=[sum(p['width']//8 for p in pieces if p['y']<=y<p['y']+p['height'])for y in range(height)]
    combined=dict(oam_entries=len(pieces)+reserve['oam_entries'],peak_sprites=max(a+b for a,b in zip(sprites,reserve['sprites_per_line'])),peak_tile_slivers=max(a+b for a,b in zip(tiles,reserve['tile_slivers_per_line'])))
    if combined['oam_entries']>128 or combined['peak_sprites']>32 or combined['peak_tile_slivers']>34:raise AssertionError('MASK_COVER_HARDWARE_GEOMETRY')
    report.update(status='FIXED_BANK_PIXEL_RECTANGLE_COVER_PROVEN',source_pixel_bank_slot_identity_verified=True,combined_geometry=combined)
    index_hash=hashlib.sha256(indices.tobytes()).hexdigest()
    if schedule.get('compiled_indices_sha256')not in(None,index_hash):raise AssertionError('MASK_COVER_INPUT_INDEX_IDENTITY')
    result=copy.deepcopy(schedule)
    result.update(pieces=pieces,piece_pixel_masks=masks,geometry=dict(oam_entries=len(pieces),peak_sprites=max(sprites),peak_tile_slivers=max(tiles)),
        geometry_pixel_rectangle_cover=report,mixed_small_size=8,mixed_large_size=large_size,obsel_mode=0 if large_size==16 else 1,
        compiled_indices_sha256=index_hash,native_presentation_proven=False)
    payload=dict(pieces=pieces,pixel_masks=masks,trace=result['trace'])
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    demand(result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--time-limit',type=float,default=30);p.add_argument('--large-size',type=int,choices=(16,32),default=16)
    p.add_argument('--geometry-reservation',type=Path)
    p.add_argument('--repair-hint',action='store_true')
    p.add_argument('--solver-backend',choices=('cp-sat','highspy'),default='cp-sat')
    a=p.parse_args();r=cover(json.loads(a.schedule.read_text(encoding='utf-8')),a.time_limit,a.large_size,json.loads(a.geometry_reservation.read_text(encoding='utf-8'))if a.geometry_reservation else None,a.repair_hint,a.solver_backend)
    a.output.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in r.get('geometry_pixel_rectangle_cover',r).items()
        if k not in('geometry_reservation','source_bank_mask_horizontal_tile_lower_bound')}))


if __name__=='__main__':main()
