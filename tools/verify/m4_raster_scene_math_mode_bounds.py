"""Relaxed slot liveness with one shared SNES math mode per scanline."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from compiler import Source
from source_scene_obj_raster import prepare
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from raster_obj_math_cover import MODES,complete_math_cover
from raster_math_mode_liveness import lower_bound


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--stage',required=True)
    parser.add_argument('--scene',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--integer-modes',action='store_true')
    parser.add_argument('--write-budget',type=int)
    parser.add_argument('--time-limit',type=int,default=180)
    args=parser.parse_args();source=Source(args.source);scene=json.loads(args.scene.read_text())
    actors,metadata,expected=prepare(source,args.stage,scene)
    background,_=compose_rgb8(source,args.stage,dict(scene,actors=[]));background=rgb555(background)
    pixels=[]
    for actor in actors:
        for ly,lx in zip(*np.where(actor['pixels']>=0)):
            y,x=int(ly+actor['top']),int(lx+actor['left'])
            out=int(actor['pixels'][ly,lx]);bg=int(background[y,x])
            if out!=bg:pixels.append((y,out,bg))
    options,cover=complete_math_cover(((out,bg)for y,out,bg in pixels),tag_modes=True)
    rows=[{mode:set()for mode in MODES}for y in range(len(background))]
    for y,out,bg in pixels:
        for mode in MODES:rows[y][mode].add((out,tuple(options[mode,out,bg])))
    report=lower_bound(rows,time_limit=args.time_limit,integer_modes=args.integer_modes,write_budget=args.write_budget)
    report.update(schema='BYOR_SHARED_SCANLINE_MATH_MODE_LIVENESS_V1',source_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest(),
                  source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
                  scene=scene,scene_sha256=hashlib.sha256(args.scene.read_bytes()).hexdigest(),metadata=metadata,
                  complete_mode_tagged_operand_cover=cover,exact_underlay_bypass=True,
                  native_timing_admitted=False,authored_pose_reachability_proven=False,universal_raster_rejected=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if not isinstance(v,(dict,list))}))


if __name__=='__main__':main()
