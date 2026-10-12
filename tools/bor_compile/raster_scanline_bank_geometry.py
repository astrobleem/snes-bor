"""Necessary per-row geometry test with separate fifteen-slot OBJ banks.

Each arbitrary-position eight-pixel sliver selects one bank. Pixels may choose
any bank explicitly allowed by their exact input encoding. Vertical geometry,
OAM count, fixed bank lifetimes and all transfer costs are relaxed, so a row
witness cannot admit a complete raster frame. Infeasibility rejects only the
input words and eligibility domains, not alternate exact alpha encodings.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand


def exact_row_word_options(schedule,scanline,background_row,expected_row):
    """Reopen every exact operand for the bound's original shared row controls."""
    from raster_obj_math_cover import complete_math_cover,apply_math
    from raster_math_windows import evaluate
    if schedule.get('color_math','additive')!='additive' or not schedule.get('scanline_math_controls_source_bound'):
        raise ValueError('ROW_BANK_GEOMETRY_SOURCE_CONTROLS')
    bg=np.asarray(background_row);expected=np.asarray(expected_row)
    if any(a.shape!=(256,)or a.dtype.kind not in'ui' or np.any(a<0)or np.any(a>32767)for a in(bg,expected)):
        raise ValueError('ROW_BANK_GEOMETRY_RGB555_CONTEXT')
    replay=schedule
    if schedule.get('status')=='POOL_CONSTRUCTION_FIXED_SMALL_GEOMETRY_OVERFLOW':
        if not schedule.get('compiled_pixel_identity_verified')or schedule.get('hardware_geometry_admitted'):raise ValueError('ROW_BANK_GEOMETRY_OVERFLOW_IDENTITY')
        replay=dict(schedule,status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
    _,_,images=demand(replay);mode=schedule['selected_modes'][str(scanline)];descriptor=schedule['compiled_color_window_descriptors'][str(scanline)]
    actual=bg.copy();points={}
    for p,image in zip(schedule['pieces'],images):
        ly=scanline-p['y']
        if not 0<=ly<p['height']:continue
        for lx in np.where(image[ly]>=0)[0]:
            x=int(p['x']+lx)
            if x in points:raise ValueError('ROW_BANK_GEOMETRY_VISIBLE_OVERLAP')
            gate=evaluate(descriptor,x);word=int(image[ly,lx]);out=int(expected[x]);under=int(bg[x])
            actual[x]=apply_math(word,under,mode)if p['bank']>=4 and gate else word
            points[x]=(out,under,gate)
    if not np.array_equal(actual,expected):raise ValueError('ROW_BANK_GEOMETRY_SOURCE_OUTPUT_REPLAY')
    operands,cover=complete_math_cover(points.values(),modes=(mode,),fixed_window_context=True)
    options={}
    for x,key in points.items():
        options[x]={b:[key[0]]for b in range(4)}
        for b in range(4,8):
            if operands[key]:options[x][b]=operands[key]
    proof=dict(complete_row_source_pixels_replayed=256,source_output_row_sha256=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest(),
        background_row_sha256=hashlib.sha256(bg.astype('<u2').tobytes()).hexdigest(),shared_math_mode=mode,
        compiled_window_descriptor=descriptor,all_exact_source_output_operands_included=True,operand_cover=cover,
        source_alpha_adaptation_selected=False,no_color_reduction=True)
    return options,proof


def bound(schedule,scanline,time_limit=30,tile_limit=34,pixel_word_options=None):
    from ortools.sat.python import cp_model
    if type(scanline)is not int or not 0<=scanline<len(schedule['trace']) or time_limit<=0 or type(tile_limit)is not int or not 0<=tile_limit<=128:
        raise ValueError('ROW_BANK_GEOMETRY_DOMAIN')
    replay=schedule
    if schedule.get('status')=='POOL_CONSTRUCTION_FIXED_SMALL_GEOMETRY_OVERFLOW':
        if not schedule.get('compiled_pixel_identity_verified') or schedule.get('hardware_geometry_admitted'):
            raise ValueError('ROW_BANK_GEOMETRY_OVERFLOW_IDENTITY')
        replay=dict(schedule,status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
    _,_,images=demand(replay);points={}
    for p,image in zip(schedule['pieces'],images):
        ly=scanline-p['y']
        if not 0<=ly<p['height']:continue
        allowed=p.get('allowed_banks',[p['bank']])
        if not allowed or any(type(b)is not int or not 0<=b<8 for b in allowed)or p['bank']not in allowed:
            raise ValueError('ROW_BANK_GEOMETRY_ELIGIBILITY')
        for lx in np.where(image[ly]>=0)[0]:
            x=int(p['x']+lx)
            if x in points:raise ValueError('ROW_BANK_GEOMETRY_VISIBLE_OVERLAP')
            points[x]=(int(image[ly,lx]),set(allowed))
    if not points:raise ValueError('ROW_BANK_GEOMETRY_EMPTY')
    options={x:{b:{c}for b in banks}for x,(c,banks)in points.items()}
    if pixel_word_options is not None:
        if not isinstance(pixel_word_options,dict)or set(pixel_word_options)!=set(points):raise ValueError('ROW_BANK_GEOMETRY_OPTION_PIXELS')
        options={}
        for x,banks in pixel_word_options.items():
            if not isinstance(banks,dict)or not banks:raise ValueError('ROW_BANK_GEOMETRY_OPTION_BANKS')
            options[x]={}
            for b,colors in banks.items():
                if type(b)is not int or not 0<=b<8 or not isinstance(colors,(list,set,tuple))or not colors or any(type(c)is not int or not 0<=c<32768 for c in colors):
                    raise ValueError('ROW_BANK_GEOMETRY_OPTION_DOMAIN')
                options[x][b]=set(colors)
    model=cp_model.CpModel();palette={};tiles=[];owners={x:[]for x in points};assignments=[]
    for x,banks in options.items():
        for b,colors in banks.items():
            for c in colors:
                if (b,c)not in palette:palette[b,c]=model.new_bool_var(f'color{b}_{c}')
    for b in range(8):model.add(sum(v for (bb,c),v in palette.items()if bb==b)<=15)
    for start in range(-7,256):
        for bank in range(8):
            covered=[x for x,banks in options.items()if start<=x<start+8 and bank in banks]
            if not covered:continue
            tile=model.new_bool_var(f'tile{start}_{bank}');tiles.append((start,bank,tile))
            for x in covered:
                v=model.new_bool_var(f'pixel{start}_{bank}_{x}');model.add(v<=tile)
                model.add(v<=sum(palette[bank,c]for c in options[x][bank]))
                owners[x].append(v);assignments.append((x,bank,v))
    for owner_options in owners.values():model.add_exactly_one(owner_options)
    model.add(sum(v for start,b,v in tiles)<=tile_limit);model.minimize(sum(v for start,b,v in tiles))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    status=solver.solve(model)
    report=dict(schema='BYOR_ROW_BANK_GEOMETRY_NECESSARY_RELAXATION_V1',
        status='ROW_BANK_GEOMETRY_NO_WITNESS',solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
        solver_objective_lower_bound=solver.best_objective_bound,scanline=scanline,opaque_pixels=len(points),tile_limit=tile_limit,
        hardware_tile_sliver_limit=34,diagnostic_limit_exceeds_hardware=tile_limit>34,
        source_rgb555_sha256=schedule.get('source_rgb555_sha256'),input_compiled_schedule_sha256=schedule.get('compiled_schedule_sha256'),
        palette_banks=8,opaque_slots_per_bank=15,transparent_slot=0,arbitrary_sliver_positions_included=True,
        fixed_exact_pixel_words=pixel_word_options is None,explicit_pixel_word_option_domain=pixel_word_options is not None,
        bank_eligibility_preserved=pixel_word_options is None,vertical_geometry_and_oam_lifetimes_relaxed=True,
        palette_liveness_and_transfers_relaxed=True,complete_frame_admitted=False,native_timing_admitted=False,
        universal_raster_rejected=False,no_color_reduction=True)
    if status==cp_model.INFEASIBLE:
        report['status']='ROW_OBJ_SLIVER_LIMIT_INFEASIBLE_FOR_FIXED_WORD_ENCODING'if pixel_word_options is None else'ROW_OBJ_SLIVER_LIMIT_INFEASIBLE_FOR_DECLARED_WORD_OPTIONS'
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    chosen={};colors={b:set()for b in range(8)}
    for x,b,v in assignments:
        if not solver.value(v):continue
        if x in chosen or b not in options[x]:raise AssertionError('ROW_BANK_GEOMETRY_PIXEL_OWNER')
        available=[c for c in options[x][b]if solver.value(palette[b,c])]
        if not available:raise AssertionError('ROW_BANK_GEOMETRY_WORD_OPTION')
        chosen[x]=(b,min(available));colors[b].add(min(available))
    if set(chosen)!=set(points)or any(len(cs)>15 for cs in colors.values()):raise AssertionError('ROW_BANK_GEOMETRY_REPLAY')
    palettes={b:sorted(cs)for b,cs in colors.items()}
    pixels=[dict(x=x,bank=b,slot=palettes[b].index(c)+1,color=c)for x,(b,c)in sorted(chosen.items())]
    selected=[dict(x=x,bank=b,width=8)for x,b,v in tiles if solver.value(v)]
    if len(selected)>tile_limit or any(not any(p['bank']==b and p['x']<=x<p['x']+8 for p in selected)for x,(b,c)in chosen.items()):
        raise AssertionError('ROW_BANK_GEOMETRY_SLIVER_REPLAY')
    report.update(status='ROW_BANK_GEOMETRY_RELAXED_WITNESS',tile_slivers=len(selected),slivers=selected,
        palette_words=palettes,pixels=pixels,declared_word_options_and_bank_capacity_replayed=True,
        source_word_and_bank_capacity_replayed=pixel_word_options is None)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--scanline',type=int,required=True);p.add_argument('--time-limit',type=float,default=30);p.add_argument('--tile-limit',type=int,default=34)
    p.add_argument('--exact-source',type=Path,help='Reopen complete exact operands after replaying the declared scene from this source archive.')
    p.add_argument('--stage',help='Required with exact-source; must match the source-bound schedule metadata.')
    a=p.parse_args();schedule=json.loads(a.schedule.read_text(encoding='utf-8'));options=None;proof=None
    if a.exact_source:
        if not a.stage:p.error('--exact-source requires --stage')
        from compiler import Source
        from source_scene_obj_raster import prepare
        from source_scene_bg import compose_rgb8
        from source_bg_feasibility import rgb555
        source=Source(a.exact_source);scene=schedule['metadata']['scene'];_,metadata,expected=prepare(source,a.stage,scene);expected=rgb555(expected)
        if metadata!=schedule['metadata']or hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()!=schedule['source_rgb555_sha256']:
            raise ValueError('ROW_BANK_GEOMETRY_SOURCE_ARCHIVE_IDENTITY')
        background=rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0])
        options,proof=exact_row_word_options(schedule,a.scanline,background[a.scanline],expected[a.scanline])
        proof['source_pak_sha256']=hashlib.sha256(a.exact_source.read_bytes()).hexdigest()
    r=bound(schedule,a.scanline,a.time_limit,a.tile_limit,options)
    if proof is not None:r['source_context_proof']=proof
    r['input_sha256']=hashlib.sha256(a.schedule.read_bytes()).hexdigest();a.output.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in r.items()if k not in('slivers','palette_words','pixels','source_context_proof')}))


if __name__=='__main__':main()
