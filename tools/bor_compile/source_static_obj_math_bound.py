"""Measure static ordinary OBJ coexistence with exact source effect math.

Ordinary visible source words are pinned in the four math-ineligible banks.
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
from raster_obj_math_cover import MODES,complete_math_cover
from raster_math_mode_liveness import lower_bound


def measure(source,stage,scene,time_limit=60,hardware_windows=True,scanline_interval=None,solver_method='highs-ipm',scanline_write_limits=None):
    if scanline_interval is not None and (len(scanline_interval)!=2 or not 0<=scanline_interval[0]<=scanline_interval[1]<224):raise ValueError('STATIC_OBJ_BOUND_SCANLINE_DOMAIN')
    actors,metadata,expected=prepare(source,stage,scene)
    background=rgb555(compose_rgb8(source,stage,dict(scene,actors=[]))[0])
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    models=discover(source,docs)['models'];reserve=set();records=[];pixels=[]
    for actor in actors:
        layer=actor['metadata']
        if not layer['alpha']:
            model=next(m for m in models if 'actor:'+m['name']==layer['kind'])
            pal,_=select_model_palette(model_palettes(source,model),layer['requested_map'])
            indices,rgb,_=decode(source,layer['path'],pal['rgb8']);raw=rgb555(rgb)
            all_words=set(map(int,raw[indices!=0]))
            if layer['source_flip']:raw=raw[:,::-1]
            words=set(map(int,raw[actor['pixels']>=0]));reserve|=words
            records.append(dict(source_model=model['name'],source_asset_path=layer['path'],whole_frame_raw_words=len(all_words),visible_raw_words=len(words)))
        else:
            for ly,lx in zip(*np.where(actor['pixels']>=0)):
                y,x=actor['top']+int(ly),actor['left']+int(lx)
                out=int(actor['pixels'][ly,lx]);bg=int(background[y,x])
                if out!=bg and (scanline_interval is None or scanline_interval[0]<=y<=scanline_interval[1]):pixels.append((y,x,out,bg))
    report=dict(schema='BYOR_STATIC_ORDINARY_OBJ_EFFECT_MATH_BOUND_V1',scene=scene,source_metadata=metadata,
        source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),ordinary_actors=records,
        reserved_visible_source_words=sorted(reserve),reserved_word_count=len(reserve),minimum_static_banks=(len(reserve)+14)//15,
        static_words_fixed_in_lower_class=True,source_context_reachability_certified=False,
        palette_bank_assignment_proven=False,physical_transfer_admitted=False,native_timing_admitted=False,
        zero_main_clipping_not_modeled=True,scanline_interval=scanline_interval,outside_interval_demand_relaxed=scanline_interval is not None,universal_raster_rejected=False,no_color_reduction=True)
    if not pixels:
        report.update(status='NO_NONBYPASSED_EFFECT_PIXELS');return report
    options,cover=complete_math_cover(((out,bg)for y,x,out,bg in pixels),modes=MODES,tag_modes=True)
    rows=[{mode:set()for mode in MODES}for _ in range(len(background))]
    window_pixels=[[]for _ in rows]if hardware_windows else None
    for y,x,out,bg in pixels:
        choices={mode:tuple(options[mode,out,bg])for mode in MODES}
        for mode in MODES:rows[y][mode].add((out,choices[mode]))
        if window_pixels is not None:window_pixels[y].append(dict(x=x,output=out,modes=choices))
    report['operand_cover']=cover
    report['cache_bound']=lower_bound(rows,time_limit=time_limit,window_pixels=window_pixels,reserved_normal_colors=reserve,solver_method=solver_method,scanline_write_limits=scanline_write_limits)
    report['status']=report['cache_bound']['status']
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
    args=parser.parse_args();limits={int(y):n for y,n in json.loads(args.scanline_write_limits.read_text()).items()}if args.scanline_write_limits else None
    result=measure(Source(args.source),args.stage,json.loads(args.scene.read_text()),args.time_limit,not args.no_windows,args.scanline_interval,args.lp_method,limits)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('status','reserved_word_count','cache_bound') if k in result}))


if __name__=='__main__':main()
