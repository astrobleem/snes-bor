"""Cover fixed-bank source pixels with legal, freely aligned OBJ masks.

Palette words, indices, write times and actor coordinates stay unchanged.
All hardware rectangles count even where their mask is transparent.
Bounded search failure never rejects general raster feasibility.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack
from raster_slot_greedy import demand


def retile(source,time_limit=30,oam_limit=128,sprite_limit=32,tile_limit=34,large_size=None,objective_kind='oam',geometry_reservation=None):
    from ortools.sat.python import cp_model
    if time_limit<=0 or any(type(v)is not int or not 0<=v<=m for v,m in
                           [(oam_limit,128),(sprite_limit,32),(tile_limit,34)]):
        raise ValueError('MASK_RETILE_RESOURCE_DOMAIN')
    if large_size not in(None,16):raise ValueError('MASK_RETILE_SIZE_PAIR_DOMAIN')
    if objective_kind not in('oam','tiles'):raise ValueError('MASK_RETILE_OBJECTIVE_DOMAIN')
    _,_,words=demand(source)
    height=len(source['trace']);points={};eligibility={};origins={};seed=set()
    reservation=dict(oam_entries=0,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height)
    if geometry_reservation is not None:
        if not isinstance(geometry_reservation,dict)or set(geometry_reservation)!=set(reservation):raise ValueError('MASK_RETILE_RESERVATION_DOMAIN')
        reservation=copy.deepcopy(geometry_reservation)
        if (type(reservation['oam_entries'])is not int or not 0<=reservation['oam_entries']<=128 or
            any(not isinstance(reservation[k],list)or len(reservation[k])!=height or
                any(type(v)is not int or not 0<=v<=limit for v in reservation[k])
                for k,limit in [('sprites_per_line',32),('tile_slivers_per_line',34)])):
            raise ValueError('MASK_RETILE_RESERVATION_DOMAIN')
    for p,mask,image in zip(source['pieces'],source['piece_pixel_masks'],words):
        allowed=p.get('allowed_banks',list(range(8)))
        if (not isinstance(allowed,(list,tuple))or not allowed or
            any(type(b)is not int or not 0<=b<8 for b in allowed)or p['bank']not in allowed):
            raise ValueError('MASK_RETILE_BANK_ELIGIBILITY')
        if p['width']not in(8,16)or p['height']!=p['width']:raise ValueError('MASK_RETILE_LEGAL_8_16_GEOMETRY_REQUIRED')
        origin=p['x']-p['local_x'],p['y']-p['local_y']
        if p['actor']in origins and origins[p['actor']]!=origin:raise ValueError('MASK_RETILE_ACTOR_ORIGIN')
        origins[p['actor']]=origin;seed.add((p['actor'],p['bank'],p['x'],p['y'],p['width']))
        indices=unpack(mask)
        for ly,lx in zip(*np.where(image>=0)):
            key=p['actor'],p['bank'],p['x']+int(lx),p['y']+int(ly)
            if key in points:raise ValueError('MASK_RETILE_INPUT_OVERLAP')
            points[key]=int(indices[ly,lx]),int(image[ly,lx])
            eligibility[key]=set(allowed)
    candidates={}
    for actor,bank,x,y in points:
        for size in ((8,16)if large_size else(8,)):
            for dx in range(size):
                for dy in range(size):
                    left,top=x-dx,y-dy
                    if 0<=left<=256-size and 0<=top<=height-size:
                        candidates.setdefault((actor,bank,left,top,size),[]).append((actor,bank,x,y))
    keys=sorted(candidates);model=cp_model.CpModel()
    row_points={};row_tile_bounds=[0]*height
    for actor,bank,x,y in points:row_points.setdefault((actor,bank,y),set()).add(x)
    for (actor,bank,y),xs in row_points.items():
        end=-1
        for x in sorted(xs):
            if x>end:row_tile_bounds[y]+=1;end=x+7
    selected=[model.new_bool_var('rectangle'+str(i))for i in range(len(keys))]
    owners={key:[]for key in points}
    for i,key in enumerate(keys):
        for pixel in candidates[key]:owners[pixel].append(i)
        model.add_hint(selected[i],int(key in seed))
    for choices in owners.values():model.add(sum(selected[i]for i in choices)>=1)
    model.add(sum(selected)+reservation['oam_entries']<=oam_limit)
    peak_tiles=model.new_int_var(0,tile_limit,'peakTiles')if objective_kind=='tiles'else None
    for y in range(height):
        live=[i for i,key in enumerate(keys)if key[3]<=y<key[3]+key[4]]
        model.add(sum(selected[i]for i in live)+reservation['sprites_per_line'][y]<=sprite_limit)
        line_tiles=sum(selected[i]*(keys[i][4]//8)for i in live)
        model.add(line_tiles+reservation['tile_slivers_per_line'][y]<=tile_limit)
        model.add(line_tiles>=row_tile_bounds[y])
        if peak_tiles is not None:model.add(line_tiles<=peak_tiles)
    model.minimize(sum(selected)if peak_tiles is None else peak_tiles*(oam_limit+1)+sum(selected))
    if peak_tiles is not None:model.add_hint(peak_tiles,source['geometry']['peak_tile_slivers'])
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit
    solver.parameters.num_search_workers=4
    status=solver.solve(model)
    report=dict(schema='BYOR_FIXED_BANK_MASK_RETILE_V1',solver_status=solver.status_name(status),
        seconds=solver.wall_time,candidate_rectangles=len(keys),source_pixels=len(points),legal_sizes=[8,16]if large_size else[8],
        objective_kind=objective_kind,objective_lower_bound=solver.best_objective_bound,
        independent_row_tile_lower_bound=max(row_tile_bounds),row_tile_lower_bounds=row_tile_bounds,
        resource_limits=dict(oam_entries=oam_limit,sprites_per_line=sprite_limit,tile_slivers_per_line=tile_limit),
        geometry_reservation=reservation,reservation_proves_concurrent_palette_or_layer_admission=False,
        status='BOUNDED_MASK_RETILE_NO_CANDIDATE',native_timing_admitted=False,
        concurrent_palette_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    chosen=[i for i in range(len(keys))if solver.value(selected[i])]
    ownership={pixel:next(i for i in owners[pixel]if i in chosen)for pixel in points}
    pieces=[];masks=[];replayed={}
    for i in chosen:
        actor,bank,x,y,size=keys[i];ox,oy=origins[actor];image=np.zeros((size,size),dtype=np.uint8);rows={};allowed=set(range(8))
        for pixel in candidates[keys[i]]:
            if ownership[pixel]!=i:continue
            _,_,px,py=pixel;index,word=points[pixel]
            image[py-y,px-x]=index;rows.setdefault(py,set()).add(word);replayed[pixel]=(index,word)
            allowed.intersection_update(eligibility[pixel])
        if not np.any(image):continue
        pieces.append(dict(actor=actor,bank=bank,x=x,y=y,local_x=x-ox,local_y=y-oy,width=size,height=size,
                           rows={line:sorted(colors)for line,colors in rows.items()},allowed_banks=sorted(allowed)))
        flat=image.flatten();masks.append(dict(width=size,height=size,packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    if replayed!=points:raise AssertionError('MASK_RETILE_PIXEL_INDEX_WORD_IDENTITY')
    peak=max(sum(p['y']<=y<p['y']+p['height']for p in pieces)for y in range(height))
    tiles=max(sum(p['width']//8 for p in pieces if p['y']<=y<p['y']+p['height'])for y in range(height))
    geometry=dict(oam_entries=len(pieces),peak_sprites=peak,peak_tile_slivers=tiles)
    combined=dict(oam_entries=len(pieces)+reservation['oam_entries'],
        peak_sprites=max(sum(p['y']<=y<p['y']+p['height']for p in pieces)+reservation['sprites_per_line'][y]for y in range(height)),
        peak_tile_slivers=max(sum(p['width']//8 for p in pieces if p['y']<=y<p['y']+p['height'])+reservation['tile_slivers_per_line'][y]for y in range(height)))
    if combined['oam_entries']>oam_limit or combined['peak_sprites']>sprite_limit or combined['peak_tile_slivers']>tile_limit:raise AssertionError('MASK_RETILE_HARDWARE_GEOMETRY')
    result=copy.deepcopy(source)
    for field in ('physical_slot_layout','prepared_dma_packets'):result.pop(field,None)
    report.update(status='FIXED_BANK_RETILED_PIXEL_IDENTITIES_PROVEN',pixel_bank_index_word_identity_replayed=True,
                  original_geometry=source['geometry'],geometry=geometry,combined_reserved_geometry=combined)
    result.update(pieces=pieces,piece_pixel_masks=masks,geometry=geometry,geometry_mode='SOURCE_EXACT_FREE_ALIGNMENT_MASKS',
        mixed_small_size=8,mixed_large_size=16,obsel_mode=0,mask_retile=report,
        piece_bank_assignment=[p['bank']for p in pieces],bank_assignment_authority='source_exact_fixed_bank_mask_retile',
        input_compiled_schedule_sha256=source.get('compiled_schedule_sha256'),
        hardware_geometry_admitted=True,native_presentation_proven=False)
    payload=dict(pieces=pieces,pixel_masks=masks,trace=result['trace'])
    if result.get('scanline_math_controls_source_bound'):
        payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    rebuilt={}
    for p,indices,words in zip(pieces,masks,demand(result)[2]):
        image=unpack(indices)
        for ly,lx in zip(*np.where(words>=0)):
            key=p['actor'],p['bank'],p['x']+int(lx),p['y']+int(ly)
            if key in rebuilt:raise AssertionError('MASK_RETILE_OUTPUT_OVERLAP')
            rebuilt[key]=int(image[ly,lx]),int(words[ly,lx])
    if rebuilt!=points:raise AssertionError('MASK_RETILE_INDEPENDENT_REPLAY')
    if source.get('physical_slot_layout',{}).get('status')=='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN':
        from raster_slot_refine import verify_packets
        verify_packets(source)
        result['prepared_dma_packets']=copy.deepcopy(source['prepared_dma_packets'])
        result['physical_slot_layout']=copy.deepcopy(source['physical_slot_layout'])
        result['physical_slot_layout'].update(native_timing_admitted=False,
            geometry_rebound_by_exact_pixel_bank_index_replay=True)
        verify_packets(result)
        report['physical_packets_retained_and_independently_replayed']=True
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--time-limit',type=float,default=30)
    p.add_argument('--oam-limit',type=int,default=128);p.add_argument('--sprite-limit',type=int,default=32);p.add_argument('--tile-limit',type=int,default=34)
    p.add_argument('--large-size',type=int,choices=(16,),help='Also permit legal 16x16 objects, charging two tile slivers on every rectangle row.')
    p.add_argument('--objective',choices=('oam','tiles'),default='oam',help='Tiles minimizes peak tile slivers first, then OAM count.')
    p.add_argument('--geometry-reservation',type=Path,help='Other actors OAM count and per-line sprite/tile counts; palette and layer admission remain separate.')
    a=p.parse_args();r=retile(json.loads(a.schedule.read_text()),a.time_limit,a.oam_limit,a.sprite_limit,a.tile_limit,a.large_size,a.objective,json.loads(a.geometry_reservation.read_text())if a.geometry_reservation else None)
    a.output.write_text(json.dumps(r,indent=2)+'\n');report=r.get('mask_retile',r)
    print(json.dumps({k:v for k,v in report.items()if k not in('geometry_reservation','row_tile_lower_bounds')}))


if __name__=='__main__':main()
