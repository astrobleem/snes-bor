"""Measure ordinary OBJ coexistence with exact source effect math.

Ordinary words may be pinned statically or only on their visible scanlines.
Effect banks, slot integrality and geometry are relaxed. Window controls are
a four-transition superset; these bounds cover this presentation policy only.
"""
import hashlib
import numpy as np
from source_profile import document,discover
from source_palette import model_palettes,select_model_palette
from source_scene_obj_raster import prepare
from source_scene_bg import compose_rgb8
from source_bg_feasibility import decode,rgb555
from raster_obj_math_cover import MODES,complete_math_cover,apply_math
from raster_math_mode_liveness import lower_bound


def measure(source,stage,scene,time_limit=60,hardware_windows=True,scanline_interval=None,solver_method='highs-ipm',scanline_write_limits=None,ordinary_residency='static',integer_pool_budget=None,initial_state=None,allowed_modes=MODES,all_visible_actor_pixels_reencodable=False,minimum_transfer_window=None,integer_cache_objective='peak',integer_pool_hint=None):
    if type(all_visible_actor_pixels_reencodable)is not bool:raise ValueError('STATIC_OBJ_BOUND_REENCODING_POLICY')
    if scanline_interval is not None and (len(scanline_interval)!=2 or not 0<=scanline_interval[0]<=scanline_interval[1]<224):raise ValueError('STATIC_OBJ_BOUND_SCANLINE_DOMAIN')
    if ordinary_residency not in ('static','scanline'):raise ValueError('STATIC_OBJ_BOUND_RESIDENCY_POLICY')
    if not allowed_modes or any(mode not in MODES for mode in allowed_modes):raise ValueError('STATIC_OBJ_BOUND_MATH_MODE_DOMAIN')
    actors,metadata,expected=prepare(source,stage,scene)
    background=rgb555(compose_rgb8(source,stage,dict(scene,actors=[]))[0])
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    models=discover(source,docs)['models'];reserve=set();records=[];pixels=[];ordinary_rows={}
    for actor in actors:
        layer=actor['metadata']
        if not layer['alpha'] and not all_visible_actor_pixels_reencodable:
            model=next(m for m in models if 'actor:'+m['name']==layer['kind'])
            pal,_=select_model_palette(model_palettes(source,model),layer['requested_map'])
            indices,rgb,_=decode(source,layer['path'],pal['rgb8']);raw=rgb555(rgb)
            all_words=set(map(int,raw[indices!=0]))
            if layer['source_flip']:raw=raw[:,::-1]
            words=set(map(int,raw[actor['pixels']>=0]));reserve|=words
            for ly,row in enumerate(raw):
                y=actor['top']+ly
                if not 0<=y<len(background)or(scanline_interval is not None and not scanline_interval[0]<=y<=scanline_interval[1]):continue
                cs=set(map(int,row[actor['pixels'][ly]>=0]))
                if cs:ordinary_rows.setdefault(y,set()).update(cs)
            records.append(dict(source_model=model['name'],source_asset_path=layer['path'],whole_frame_raw_words=len(all_words),visible_raw_words=len(words)))
        else:
            for ly,lx in zip(*np.where(actor['pixels']>=0)):
                y,x=actor['top']+int(ly),actor['left']+int(lx)
                out=int(actor['pixels'][ly,lx]);bg=int(background[y,x])
                if out!=bg and (scanline_interval is None or scanline_interval[0]<=y<=scanline_interval[1]):pixels.append((y,x,out,bg))
    report=dict(schema='BYOR_STATIC_ORDINARY_OBJ_EFFECT_MATH_BOUND_V1',scene=scene,source_metadata=metadata,
        source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),ordinary_actors=records,
        reserved_visible_source_words=sorted(reserve)if ordinary_residency=='static'else[],reserved_word_count=len(reserve)if ordinary_residency=='static'else 0,
        ordinary_union_word_count=len(reserve),ordinary_residency_policy=ordinary_residency,ordinary_peak_required_words=max(map(len,ordinary_rows.values()),default=0),minimum_static_banks=(len(reserve)+14)//15,
        static_words_fixed_in_lower_class=ordinary_residency=='static',source_context_reachability_certified=False,
        palette_bank_assignment_proven=False,physical_transfer_admitted=False,native_timing_admitted=False,
        zero_main_clipping_not_modeled=True,scanline_interval=scanline_interval,outside_interval_demand_relaxed=scanline_interval is not None,allowed_math_modes=list(allowed_modes),universal_raster_rejected=False,no_color_reduction=True)
    if not pixels:
        report.update(status='NO_NONBYPASSED_EFFECT_PIXELS');return report
    options,cover=complete_math_cover(((out,bg)for y,x,out,bg in pixels),modes=allowed_modes,tag_modes=True)
    rows=[{mode:set()for mode in allowed_modes}for _ in range(len(background))]
    window_pixels=[[]for _ in rows]if hardware_windows else None
    for y,x,out,bg in pixels:
        choices={mode:tuple(options[mode,out,bg])for mode in allowed_modes}
        for mode in allowed_modes:rows[y][mode].add((out,choices[mode]))
        if window_pixels is not None:window_pixels[y].append(dict(x=x,output=out,modes=choices))
    report['operand_cover']=cover
    report['all_visible_actor_pixels_reencodable']=all_visible_actor_pixels_reencodable
    report['cross_actor_compiled_mask_ownership_required']=all_visible_actor_pixels_reencodable
    report['source_alpha_policy']='BOR4086_SCREEN_RGB8_THEN_RGB555'
    report['alpha_compatibility_policy_selected']=False
    integer_options={}if integer_pool_budget is None else dict(integer_modes=True,integer_windows=hardware_windows,integer_palette=True,integer_backend='cp-sat',write_budget=integer_pool_budget)
    if integer_pool_hint is not None and(integer_pool_budget is None or integer_pool_hint.get('source_metadata')!=metadata or integer_pool_hint.get('source_rgb555_sha256')!=report['source_rgb555_sha256']or integer_pool_hint.get('scene')!=scene):raise ValueError('STATIC_OBJ_BOUND_POOL_HINT_SOURCE_IDENTITY')
    report['cache_bound']=lower_bound(rows,time_limit=time_limit,window_pixels=window_pixels,reserved_normal_colors=reserve if ordinary_residency=='static'else(),solver_method=solver_method,scanline_write_limits=scanline_write_limits,required_normal_rows=ordinary_rows if ordinary_residency=='scanline'else None,initial_state=initial_state,minimum_transfer_window=minimum_transfer_window,integer_cache_objective=integer_cache_objective,residency_hint=integer_pool_hint['cache_bound']if integer_pool_hint else None,**integer_options)
    report['status']=report['cache_bound']['status']
    bound=report['cache_bound']
    if integer_pool_budget is not None and bound.get('integer_pool_pixel_coverage_verified'):
        from raster_math_mode_liveness import verify_integer_pool
        replay_rows=[{mode:set(reqs)for mode,reqs in row.items()}for row in rows]
        if ordinary_residency=='scanline':
            for y,cs in ordinary_rows.items():
                for mode in replay_rows[y]or allowed_modes:replay_rows[y].setdefault(mode,set()).update((c,())for c in cs)
        verify_integer_pool(bound,replay_rows,window_pixels=window_pixels)
        from raster_math_windows import compile_sparse_mask,evaluate
        states={int(y):{int(k):set(v)for k,v in state.items()}for y,state in bound['selected_palette_residency'].items()}
        modes={int(y):mode for y,mode in bound['selected_modes'].items()}
        masks={int(y):{int(x):v for x,v in mask.items()}for y,mask in bound.get('selected_window_eligibility',{}).items()}
        windows={}
        for y in modes:
            eligibility=masks.get(y,{})
            # Ordinary-only rows have no effect pixels constraining a window.
            windows[y]=compile_sparse_mask({0:1})if window_pixels is None else compile_sparse_mask(eligibility)if eligibility else compile_sparse_mask({0:0})
        checked=0
        for actor in actors:
            for ly,lx in zip(*np.where(actor['pixels']>=0)):
                y,x=actor['top']+int(ly),actor['left']+int(lx)
                if y not in states:continue
                out=int(actor['pixels'][ly,lx]);bg=int(background[y,x])
                if out==bg:continue
                covered=out in states[y][0]or any((apply_math(c,bg,modes[y])if evaluate(windows[y],x)else c)==out for c in states[y][1])
                if not covered:raise AssertionError('ORDINARY_EFFECT_INTEGER_SOURCE_PIXEL_REPLAY')
                checked+=1
        report['source_control_candidate']=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata=metadata,
            source_rgb555_sha256=report['source_rgb555_sha256'],selected_modes=modes,
            selected_palette_residency=bound['selected_palette_residency'],compiled_color_window_descriptors=windows,
            full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
            checked_visible_source_pixels=checked,integer_pool_pixel_coverage_verified=True,
            geometry_and_bank_assignment_relaxed=True,physical_transfer_admitted=False,
            outside_control_rows_math_policy='FULL_ADD_NO_WINDOW_MINIMAL_OPERAND_OR_LITERAL',
            peak_replayed_pool_writes=bound['peak_replayed_pool_writes'],no_color_reduction=True)
    return report


def main():
    import argparse,json
    from pathlib import Path
    from compiler import Source
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True);parser.add_argument('--stage',required=True)
    parser.add_argument('--scene',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--time-limit',type=float,default=60);parser.add_argument('--no-windows',action='store_true')
    parser.add_argument('--scanline-interval',type=int,nargs=2);parser.add_argument('--lp-method',choices=('highs-ipm','highs-ds'),default='highs-ipm')
    parser.add_argument('--scanline-write-limits',type=Path)
    parser.add_argument('--ordinary-residency',choices=('static','scanline'),default='static')
    parser.add_argument('--integer-pool-budget',type=int,help='Search an independently replayed integer two-class cache; bank geometry and physical timing remain relaxed.')
    parser.add_argument('--reencode-all-visible-actors',action='store_true',help='Relax literal ordinary actor ownership and cover every final source actor pixel with exact shader operands. No live compositor admission.')
    parser.add_argument('--math-mode',action='append',choices=MODES,help='Restrict the globally selected scanline math modes; repeat to allow multiple modes.')
    parser.add_argument('--initial-palette-state',type=Path,help='Pin both class caches at the first controlled row, for continuation without a palette reset.')
    parser.add_argument('--minimum-transfer-window',type=int,help='Necessary two-class bank/write transfer bound only; fixed banks and physical slots remain unproved.')
    parser.add_argument('--integer-cache-objective',choices=('peak','loads'),default='peak',help='Select peak loads or total loads; total loads requires an integer pool budget.')
    parser.add_argument('--integer-pool-hint',type=Path,help='Source-bound prior integer pool; independently replayed before supplying soft cache and control hints.')
    args=parser.parse_args();limits={int(y):n for y,n in json.loads(args.scanline_write_limits.read_text()).items()}if args.scanline_write_limits else None
    initial=json.loads(args.initial_palette_state.read_text())if args.initial_palette_state else None
    result=measure(Source(args.source),args.stage,json.loads(args.scene.read_text()),args.time_limit,not args.no_windows,args.scanline_interval,args.lp_method,limits,args.ordinary_residency,args.integer_pool_budget,initial,args.math_mode or MODES,args.reencode_all_visible_actors,args.minimum_transfer_window,args.integer_cache_objective,json.loads(args.integer_pool_hint.read_text())if args.integer_pool_hint else None)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    bound=result.get('cache_bound',{})
    print(json.dumps(dict(status=result['status'],reserved_word_count=result['reserved_word_count'],cache_bound={k:bound[k]for k in ('status','message','validated_dual_lower_bound','peak_replayed_pool_writes','solver_seconds','variables','constraints')if k in bound})))


if __name__=='__main__':main()
