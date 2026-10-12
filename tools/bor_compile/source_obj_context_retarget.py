"""Reuse exact OBJ masks in a source-composed context and repair bank capacity.

Explicit actor mappings and domains are inputs. This offline pose operation
does not admit a live compositor, physical transfer schedule or gameplay.
"""
import copy,hashlib,json
import numpy as np
from raster_obj_compact import unpack
from raster_slot_greedy import demand
from raster_palette import pieces_for_grid,schedule as logical_schedule
from raster_bank_search import assign
from source_scene_obj_raster import prepare
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555


def retarget(source,stage,scene,seed,actor_map,actor_domains,time_limit=30,lookahead=55,interval_budget=21):
    demand(seed)
    actors,metadata,expected=prepare(source,stage,scene)
    old_layers=[l for l in seed['metadata']['layers']if l['kind'].startswith('actor:')]
    if (not isinstance(actor_map,dict)or not actor_map or
        any(type(i)is not int or type(j)is not int or not 0<=i<len(old_layers)or not 0<=j<len(actors)for i,j in actor_map.items())or
        len(set(actor_map.values()))!=len(actor_map)):raise ValueError('OBJ_RETARGET_ACTOR_MAP')
    if not isinstance(actor_domains,(list,tuple))or len(actor_domains)!=len(actors)or any(not isinstance(d,(list,tuple))or not d or len(set(d))!=len(d)or any(type(b)is not int or not 0<=b<8 for b in d)for d in actor_domains):raise ValueError('OBJ_RETARGET_ACTOR_DOMAINS')
    if time_limit<=0 or type(lookahead)is not int or lookahead<0:raise ValueError('OBJ_RETARGET_SEARCH_DOMAIN')
    for i,j in actor_map.items():
        old,new=old_layers[i],actors[j]['metadata']
        if any(old[k]!=new[k]for k in('kind','sha256','source_dimensions','source_flip','requested_map','selected_map','palette_asset_sha256','alpha')):raise ValueError('OBJ_RETARGET_SOURCE_ACTOR_IDENTITY')
    pieces=[];images=[];banks=[];seed_indices=[]
    for j,actor in enumerate(actors):
        if j in actor_map.values():continue
        for q in pieces_for_grid(actor['pixels'],(16,16)):
            p=copy.deepcopy(q);p.update(actor=j,local_x=q['x'],local_y=q['y'],allowed_banks=sorted(actor_domains[j]))
            p['x']+=actor['left'];p['y']+=actor['top']
            p['rows']={y+actor['top']:cs for y,cs in q['rows'].items()if 0<=y+actor['top']<224}
            image=np.full((16,16),-1,dtype=np.int32)
            region=actor['pixels'][q['y']:q['y']+16,q['x']:q['x']+16]
            image[:region.shape[0],:region.shape[1]]=region
            pieces.append(p);images.append(image);banks.append(None);seed_indices.append(None)
    for i,(q,m)in enumerate(zip(seed['pieces'],seed['piece_pixel_masks'])):
        if q['actor']not in actor_map:raise ValueError('OBJ_RETARGET_UNMAPPED_SEED_ACTOR')
        j=actor_map[q['actor']];actor=actors[j]
        if q['width']not in(8,16)or q['height']!=q['width']:raise ValueError('OBJ_RETARGET_LEGAL_SIZE_PAIR')
        if (q['x']-q['local_x'],q['y']-q['local_y'])!=(actor['left'],actor['top']):raise ValueError('OBJ_RETARGET_SOURCE_ORIGIN')
        p=copy.deepcopy(q);p.update(actor=j,allowed_banks=sorted(actor_domains[j]));p.pop('bank',None)
        mask=unpack(m);image=np.full(mask.shape,-1,dtype=np.int32)
        for ly,lx in zip(*np.where(mask)):
            ay,ax=q['local_y']+int(ly),q['local_x']+int(lx)
            if not 0<=ay<actor['pixels'].shape[0]or not 0<=ax<actor['pixels'].shape[1]:raise ValueError('OBJ_RETARGET_SOURCE_EXTENT')
            image[ly,lx]=actor['pixels'][ay,ax]
        p['rows']={q['y']+y:sorted(set(map(int,row[row>=0])))for y,row in enumerate(image)if np.any(row>=0)}
        pieces.append(p);images.append(image);banks.append(q['bank']);seed_indices.append(i)
    geometry=dict(oam_entries=len(pieces),peak_sprites=max(sum(p['y']<=y<p['y']+p['height']for p in pieces)for y in range(224)),
                  peak_tile_slivers=max(sum(p['width']//8 for p in pieces if p['y']<=y<p['y']+p['height'])for y in range(224)))
    result=dict(schema='BYOR_SOURCE_OBJ_CONTEXT_RETARGET_V1',status='BOUNDED_SOURCE_CONTEXT_RETARGET_NO_CANDIDATE',metadata=metadata,geometry=geometry,
                source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),actor_map=actor_map,actor_bank_domains=actor_domains,
                color_math='precomposited',no_color_reduction=True,compiled_pixel_identity_verified=False,hardware_geometry_admitted=False,
                native_presentation_proven=False,live_compositor_admitted=False,motu_gameplay_proven=False,universal_raster_rejected=False)
    result['input_compiled_schedule_sha256']=seed.get('compiled_schedule_sha256')
    if geometry['oam_entries']>128 or geometry['peak_sprites']>32 or geometry['peak_tile_slivers']>34:
        result['status']='SUPPLIED_RETARGET_GEOMETRY_LIMIT';return result
    rows={}
    for p,b in zip(pieces,banks):
        if b is not None:
            for y,cs in p['rows'].items():rows.setdefault((y,b),set()).update(cs)
    bad={(y,b)for (y,b),cs in rows.items()if len(cs)>15};domains=[];mutable=[]
    for p,b,i in zip(pieces,banks,seed_indices):
        repair=b is None or b not in p['allowed_banks']or any((y,b)in bad for y in p['rows'])
        domains.append(p['allowed_banks']if repair else[b])
        if repair and i is not None:mutable.append(i)
    result['over_capacity_rows']=[dict(scanline=y,bank=b,colors=len(rows[y,b]))for y,b in sorted(bad)]
    result['mutable_seed_piece_indices']=mutable
    search=assign([dict(p,allowed_banks=d)for p,d in zip(pieces,domains)],tuple(range(8)),time_limit=time_limit,
                  interval_write_budget=interval_budget,interval_lines=8)
    result['bank_search']=search
    if 'assignment'not in search:return result
    trace,states=logical_schedule(pieces,search['assignment'],224,lookahead)
    for row in trace:row['resident_before']={b:row['resident_before'].get(b,[None]*15)for b in range(8)}
    masks=[];indices=np.zeros((224,256),dtype=np.uint8)
    background=rgb555(compose_rgb8(source,stage,dict(scene,actors=[]))[0]);replay=background.copy();owned=np.zeros((224,256),dtype=bool)
    for p,image,bank in zip(pieces,images,search['assignment']):
        p['bank']=bank;mask=np.zeros(image.shape,dtype=np.uint8)
        for ly,lx in zip(*np.where(image>=0)):
            y,x=p['y']+int(ly),p['x']+int(lx)
            if not 0<=y<224 or not 0<=x<256 or owned[y,x]:raise ValueError('OBJ_RETARGET_VISIBLE_PIXEL_OVERLAP_OR_EXTENT')
            slot=states[y][bank].index(int(image[ly,lx]))+1
            mask[ly,lx]=slot;indices[y,x]=128+16*bank+slot;owned[y,x]=True;replay[y,x]=states[y][bank][slot-1]
        flat=mask.flatten();masks.append(dict(width=p['width'],height=p['height'],pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    required=np.zeros_like(owned)
    for actor in actors:
        for ly,lx in zip(*np.where(actor['pixels']>=0)):required[actor['top']+ly,actor['left']+lx]=True
    if not np.array_equal(owned,required)or not np.array_equal(replay,rgb555(expected)):raise ValueError('OBJ_RETARGET_SOURCE_PIXEL_AND_TRANSPARENCY_IDENTITY')
    result.update(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',pieces=pieces,piece_pixel_masks=masks,trace=trace,
                  compiled_pixel_identity_verified=True,hardware_geometry_admitted=True,obsel_mode=0,mixed_small_size=8,mixed_large_size=16,
                  source_visible_opaque_pixels=int(owned.sum()),lookahead_lines=lookahead,
                  compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest())
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=pieces,pixel_masks=masks,trace=trace),sort_keys=True).encode()).hexdigest()
    _,_,verified=demand(result)
    if any(not np.array_equal(a,b)for a,b in zip(images,verified)):raise AssertionError('OBJ_RETARGET_INDEPENDENT_SOURCE_WORD_REPLAY')
    return result
