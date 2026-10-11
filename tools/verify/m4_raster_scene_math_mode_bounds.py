"""Relaxed slot liveness with one shared SNES math mode per scanline."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import time
from compiler import Source
from source_scene_obj_raster import prepare
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from raster_obj_math_cover import MODES,complete_math_cover,apply_math
from raster_math_mode_liveness import lower_bound,verify_integer_pool
from raster_math_windows import compile_sparse_mask,evaluate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--stage',required=True)
    parser.add_argument('--scene',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--integer-modes',action='store_true')
    parser.add_argument('--write-budget',type=int)
    parser.add_argument('--time-limit',type=int,default=180)
    parser.add_argument('--lp-method',choices=('highs-ipm','highs-ds'),default='highs-ipm')
    parser.add_argument('--first-line',type=int)
    parser.add_argument('--last-line',type=int)
    parser.add_argument('--relaxed-window-bypass',action='store_true')
    parser.add_argument('--math-window',type=int,nargs=2,metavar=('LEFT','RIGHT'))
    parser.add_argument('--hardware-windows',action='store_true')
    parser.add_argument('--integer-windows',action='store_true')
    parser.add_argument('--pin-lp-controls',action='store_true')
    parser.add_argument('--math-mode',action='append',choices=MODES)
    parser.add_argument('--positive-windows-only',action='store_true')
    parser.add_argument('--subset-mode-cuts',action='store_true')
    parser.add_argument('--relax-clipped-pixels',action='store_true',help='Necessary relaxation: remove black and half-subscreen outputs that zero-main clipping may produce.')
    parser.add_argument('--integer-palette',action='store_true')
    parser.add_argument('--integer-backend',choices=('highs','cp-sat'),default='highs')
    parser.add_argument('--lp-hint',action='store_true')
    parser.add_argument('--candidate',type=Path,help='Replay a saved integer pool against the same source and scope, without another solve.')
    parser.add_argument('--residency-hint',type=Path,help='Source-replay a saved integer pool and supply its residency and controls as soft CP-SAT hints.')
    args=parser.parse_args();source=Source(args.source);scene=json.loads(args.scene.read_text());modes=tuple(dict.fromkeys(args.math_mode or MODES))
    actors,metadata,expected=prepare(source,args.stage,scene)
    background,_=compose_rgb8(source,args.stage,dict(scene,actors=[]));background=rgb555(background)
    if (args.first_line is None)!=(args.last_line is None):raise ValueError('MATH_MODE_SCANLINE_WINDOW_PAIR_REQUIRED')
    if args.first_line is not None and not 0<=args.first_line<=args.last_line<len(background):raise ValueError('MATH_MODE_SCANLINE_WINDOW_DOMAIN')
    if args.math_window and not 0<=args.math_window[0]<=args.math_window[1]<background.shape[1]:raise ValueError('MATH_MODE_HORIZONTAL_WINDOW_DOMAIN')
    if args.math_window and args.relaxed_window_bypass:raise ValueError('MATH_MODE_WINDOW_POLICIES_CONFLICT')
    if args.hardware_windows and(args.math_window or args.relaxed_window_bypass):raise ValueError('MATH_MODE_WINDOW_POLICIES_CONFLICT')
    if args.integer_windows and not args.hardware_windows:raise ValueError('MATH_MODE_HARDWARE_WINDOWS_REQUIRED')
    pixels=[];clipped_relaxed=0
    for actor in actors:
        for ly,lx in zip(*np.where(actor['pixels']>=0)):
            y,x=int(ly+actor['top']),int(lx+actor['left'])
            out=int(actor['pixels'][ly,lx]);bg=int(background[y,x])
            if out!=bg and(args.first_line is None or args.first_line<=y<=args.last_line):
                half_bg=((bg&31)//2)|((((bg>>5)&31)//2)<<5)|((((bg>>10)&31)//2)<<10)
                if args.relax_clipped_pixels and out in (0,half_bg):clipped_relaxed+=1;continue
                pixels.append((y,x,out,bg,args.math_window is None or args.math_window[0]<=x<=args.math_window[1]))
    fixed_context=bool(args.math_window or args.hardware_windows)
    if args.hardware_windows:requirements=((out,bg,enabled)for y,x,out,bg,_ in pixels for enabled in (False,True))
    elif args.math_window:requirements=((out,bg,enabled)for y,x,out,bg,enabled in pixels)
    else:requirements=((out,bg)for y,x,out,bg,enabled in pixels)
    if args.candidate and args.residency_hint:raise ValueError('MATH_MODE_CANDIDATE_AND_HINT_CONFLICT')
    saved_candidate=json.loads((args.candidate or args.residency_hint).read_text())if args.candidate or args.residency_hint else None
    retained={c for state in saved_candidate['selected_palette_residency'].values()for c in state['1']}if args.residency_hint else ()
    started=time.perf_counter();options,cover=complete_math_cover(requirements,modes=modes,tag_modes=True,allow_window_bypass=args.relaxed_window_bypass,fixed_window_context=fixed_context,retained_operands=retained)
    cover_seconds=time.perf_counter()-started
    rows=[{mode:set()for mode in modes}for y in range(len(background))]
    union_rows=[set()for y in range(len(background))]
    window_pixels=[[]for y in range(len(background))]if args.hardware_windows else None
    for y,x,out,bg,enabled in pixels:
        def values(mode):
            if args.candidate:
                words=saved_candidate['selected_palette_residency'][str(y)]['1']
                return tuple(c for c in words if(apply_math(c,bg,mode)==out if args.hardware_windows or enabled else c==out))
            return options[mode,out,bg,True if args.hardware_windows else enabled]if fixed_context else options[mode,out,bg]
        for mode in modes:rows[y][mode].add((out,tuple(values(mode))))
        union={c for mode in modes for c in values(mode)}
        if args.hardware_windows:
            union.add(out)
            window_pixels[y].append(dict(x=x,output=out,modes={mode:tuple(values(mode))for mode in modes}))
        union_rows[y].add((out,tuple(sorted(union))))
    source_digest=hashlib.sha256(source.path.read_bytes()).hexdigest();pixel_digest=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest()
    if args.candidate or args.residency_hint:
        report=saved_candidate
        scope={'source_sha256':source_digest,'source_rgb555_sha256':pixel_digest,'scene_sha256':hashlib.sha256(args.scene.read_bytes()).hexdigest(),
               'scanline_window':[args.first_line,args.last_line],'math_modes_allowed':list(modes),'hardware_window_masks_modeled':args.hardware_windows,
               'horizontal_math_window':args.math_window,'zero_main_clipping_palette_demand_relaxed':args.relax_clipped_pixels,
               'positive_union_with_disabled_edges_only':args.positive_windows_only}
        if not report.get('integer_palette')or any(report.get(k)!=v for k,v in scope.items()):raise ValueError('MATH_MODE_INTEGER_CANDIDATE_SCOPE')
        if window_pixels is not None:
            for y,line in enumerate(window_pixels):
                for pixel in line:
                    mask=report['selected_window_eligibility'][str(y)]
                    if str(pixel['x'])not in mask:mask[str(pixel['x'])]=int(evaluate(report['compiled_color_window_descriptors'][str(y)],pixel['x']))
        verify_integer_pool(report,rows,window_pixels=window_pixels)
        report['saved_candidate_coverage_method']='DIRECT_RGB555_MATH_OF_RESIDENT_WORDS'if args.candidate else'EXACT_SOURCE_COVER_WITH_RETAINED_HINT_OPERANDS'
        report['saved_candidate_source_replay_verified']=True
        report['saved_candidate_sha256']=hashlib.sha256((args.candidate or args.residency_hint).read_bytes()).hexdigest()
        if 'candidate_generation'not in report:
            provenance=('status','solver_status','message','variables','constraints','mode_variables','solver_seconds','solver_method','boolean_stats','lp_residency_hint','maximum_primal_violation','maximum_integer_control_residual')
            report['candidate_generation']={k:report.pop(k)for k in provenance if k in report}
        report['status']='INTEGER_POOL_SOURCE_REPLAY_PROVEN'
    if not args.candidate:
        report=lower_bound(rows,time_limit=args.time_limit,integer_modes=args.integer_modes or args.integer_palette,write_budget=args.write_budget,solver_method=args.lp_method,union_rows=union_rows,window_pixels=window_pixels,integer_windows=args.integer_windows or args.integer_palette and args.hardware_windows,pin_lp_controls=args.pin_lp_controls,positive_windows_only=args.positive_windows_only,subset_mode_cuts=args.subset_mode_cuts,integer_palette=args.integer_palette,integer_backend=args.integer_backend,lp_hint=args.lp_hint,residency_hint=saved_candidate if args.residency_hint else None)
        if args.residency_hint:report['source_residency_hint']['source_replay_sha256']=hashlib.sha256(args.residency_hint.read_bytes()).hexdigest()
    if 'selected_window_eligibility'in report:
        report['compiled_color_window_descriptors']={y:compile_sparse_mask({int(x):v for x,v in mask.items()},args.positive_windows_only)for y,mask in report['selected_window_eligibility'].items()}
    if report.get('integer_pool_pixel_coverage_verified')and not(args.relax_clipped_pixels or args.relaxed_window_bypass):
        states={int(y):{int(k):set(v)for k,v in state.items()}for y,state in report['selected_palette_residency'].items()}
        selected_modes={int(y):m for y,m in report['selected_modes'].items()}
        descriptors={int(y):d for y,d in report.get('compiled_color_window_descriptors',{}).items()}
        for y,x,out,bg,enabled in pixels:
            if args.hardware_windows:enabled=evaluate(descriptors[y],x)
            if out not in states[y][0]and not any((apply_math(c,bg,selected_modes[y])if enabled else c)==out for c in states[y][1]):
                raise AssertionError('MATH_MODE_COMPILED_CONTROL_SOURCE_PIXEL_REPLAY')
        report.update(full_interval_source_pixels_verified=True,source_interval_pixels_verified=len(pixels),
            complete_source_frame_pixel_identity_proven=args.first_line is None,
            source_pixel_replay_scope='CLASS_POOL_ONLY_NO_FIXED_BANK_OR_OBJ_GEOMETRY',
            compiled_mode_window_pixel_coverage_replayed=True)
    report.update(schema='BYOR_SHARED_SCANLINE_MATH_MODE_LIVENESS_V1',source_sha256=source_digest,
                  source_rgb555_sha256=pixel_digest,
                  scene=scene,scene_sha256=hashlib.sha256(args.scene.read_bytes()).hexdigest(),metadata=metadata,
                  complete_mode_tagged_operand_cover=cover,cover_enumeration_seconds=cover_seconds,exact_underlay_bypass=True,
                  scanline_window=[args.first_line,args.last_line],outside_window_demand_relaxed=args.first_line is not None,
                  horizontal_math_window=args.math_window,math_enabled_inside_horizontal_window=True if args.math_window else None,
                  window_mask_transition_superset_only=args.hardware_windows,window_register_schedule_proven=False,
                  math_modes_allowed=list(modes),restricted_math_mode_family=len(modes)!=len(MODES),
                  zero_main_clipping_palette_demand_relaxed=args.relax_clipped_pixels,clipping_relaxed_pixels=clipped_relaxed,
                  clipping_mode_and_window_constraints_proven=False,
                  native_timing_admitted=False,authored_pose_reachability_proven=False,universal_raster_rejected=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if not isinstance(v,(dict,list))}))


if __name__=='__main__':main()
