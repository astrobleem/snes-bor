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
from raster_obj_math_cover import MODES,complete_math_cover
from raster_math_mode_liveness import lower_bound
from raster_math_windows import compile_sparse_mask


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
    args=parser.parse_args();source=Source(args.source);scene=json.loads(args.scene.read_text());modes=tuple(dict.fromkeys(args.math_mode or MODES))
    actors,metadata,expected=prepare(source,args.stage,scene)
    background,_=compose_rgb8(source,args.stage,dict(scene,actors=[]));background=rgb555(background)
    if (args.first_line is None)!=(args.last_line is None):raise ValueError('MATH_MODE_SCANLINE_WINDOW_PAIR_REQUIRED')
    if args.first_line is not None and not 0<=args.first_line<=args.last_line<len(background):raise ValueError('MATH_MODE_SCANLINE_WINDOW_DOMAIN')
    if args.math_window and not 0<=args.math_window[0]<=args.math_window[1]<background.shape[1]:raise ValueError('MATH_MODE_HORIZONTAL_WINDOW_DOMAIN')
    if args.math_window and args.relaxed_window_bypass:raise ValueError('MATH_MODE_WINDOW_POLICIES_CONFLICT')
    if args.hardware_windows and(args.math_window or args.relaxed_window_bypass):raise ValueError('MATH_MODE_WINDOW_POLICIES_CONFLICT')
    if args.integer_windows and not args.hardware_windows:raise ValueError('MATH_MODE_HARDWARE_WINDOWS_REQUIRED')
    pixels=[]
    for actor in actors:
        for ly,lx in zip(*np.where(actor['pixels']>=0)):
            y,x=int(ly+actor['top']),int(lx+actor['left'])
            out=int(actor['pixels'][ly,lx]);bg=int(background[y,x])
            if out!=bg and(args.first_line is None or args.first_line<=y<=args.last_line):pixels.append((y,x,out,bg,args.math_window is None or args.math_window[0]<=x<=args.math_window[1]))
    fixed_context=bool(args.math_window or args.hardware_windows)
    if args.hardware_windows:requirements=((out,bg,enabled)for y,x,out,bg,_ in pixels for enabled in (False,True))
    elif args.math_window:requirements=((out,bg,enabled)for y,x,out,bg,enabled in pixels)
    else:requirements=((out,bg)for y,x,out,bg,enabled in pixels)
    started=time.perf_counter();options,cover=complete_math_cover(requirements,modes=modes,tag_modes=True,allow_window_bypass=args.relaxed_window_bypass,fixed_window_context=fixed_context)
    cover_seconds=time.perf_counter()-started
    rows=[{mode:set()for mode in modes}for y in range(len(background))]
    union_rows=[set()for y in range(len(background))]
    window_pixels=[[]for y in range(len(background))]if args.hardware_windows else None
    for y,x,out,bg,enabled in pixels:
        def values(mode):return options[mode,out,bg,True if args.hardware_windows else enabled]if fixed_context else options[mode,out,bg]
        for mode in modes:rows[y][mode].add((out,tuple(values(mode))))
        union={c for mode in modes for c in values(mode)}
        if args.hardware_windows:
            union.add(out)
            window_pixels[y].append(dict(x=x,output=out,modes={mode:tuple(values(mode))for mode in modes}))
        union_rows[y].add((out,tuple(sorted(union))))
    report=lower_bound(rows,time_limit=args.time_limit,integer_modes=args.integer_modes,write_budget=args.write_budget,solver_method=args.lp_method,union_rows=union_rows,window_pixels=window_pixels,integer_windows=args.integer_windows,pin_lp_controls=args.pin_lp_controls)
    if 'selected_window_eligibility'in report:
        report['compiled_color_window_descriptors']={y:compile_sparse_mask(mask)for y,mask in report['selected_window_eligibility'].items()}
    report.update(schema='BYOR_SHARED_SCANLINE_MATH_MODE_LIVENESS_V1',source_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest(),
                  source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
                  scene=scene,scene_sha256=hashlib.sha256(args.scene.read_bytes()).hexdigest(),metadata=metadata,
                  complete_mode_tagged_operand_cover=cover,cover_enumeration_seconds=cover_seconds,exact_underlay_bypass=True,
                  scanline_window=[args.first_line,args.last_line],outside_window_demand_relaxed=args.first_line is not None,
                  horizontal_math_window=args.math_window,math_enabled_inside_horizontal_window=True if args.math_window else None,
                  window_mask_transition_superset_only=args.hardware_windows,window_register_schedule_proven=False,
                  math_modes_allowed=list(modes),restricted_math_mode_family=len(modes)!=len(MODES),
                  native_timing_admitted=False,authored_pose_reachability_proven=False,universal_raster_rejected=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if not isinstance(v,(dict,list))}))


if __name__=='__main__':main()
