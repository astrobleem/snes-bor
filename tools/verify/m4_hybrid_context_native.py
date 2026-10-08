"""Prepare measured single-context VRAM residency and run independent PPU proof.

Each run starts an isolated ROM. No context transition, producer cadence,
production audio or gameplay reachability is inferred from these results.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--timer',type=int,default=160)
    a=p.parse_args();a.assets=a.assets.resolve();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    r=json.loads((a.assets/'report.json').read_text())
    if r.get('bg_schedule',{}).get('status')!='CONTIGUOUS_BURST_SCHEDULE_PROVEN' or not r['layer_pixel_identity_verified']:
        raise ValueError('HYBRID_CONTEXT_COMPILED_PALETTE_REQUIRED')
    expected=(a.assets/'expected.bin').read_bytes()
    if hashlib.sha256(expected).hexdigest()!=r['source_rgb555_sha256']:raise ValueError('HYBRID_CONTEXT_SOURCE_FRAME_HASH')
    counts={}
    for name in ('high','low'):
        frame=np.fromfile(a.assets/(name+'.bin'),dtype=np.uint8).reshape(224,256)
        counts[name]=len({frame[y:y+8,x:x+8].tobytes()for y in range(0,224,8)for x in range(0,256,8)})
    seq=a.output/'single-context';frame=seq/'frame-00';frame.mkdir(parents=True,exist_ok=True)
    for name in ('high.bin','low.bin','promoted.bin','oam.bin','obj_chr.bin'):
        target=frame/name
        if not target.exists():os.link(a.assets/name,target)
        elif target.read_bytes()!=(a.assets/name).read_bytes():raise ValueError('HYBRID_CONTEXT_STALE_SINGLE_FRAME_INPUT:'+name)
    (frame/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    (seq/'report.json').write_text(json.dumps(dict(complete=True,all_frames_compiled=True,rows=[dict(frame=0,start_source_tick=0)],
         scope='One source context; palette assets compiled, physical residency and native admission checked separately'))+'\n')
    # LOW is 2bpp at C000, with the BG1 map starting at F000: 768 legal tiles.
    # Exact tile demand determines its allocation. HIGH uses the aligned tail.
    low_slots=counts['low']
    if not 1<=low_slots<=768:raise ValueError('HYBRID_CONTEXT_LOW_CHR_CAPACITY:'+str(low_slots))
    tool=Path(__file__).resolve().parents[1]/'bor_compile'/'source_hybrid_residency.py';attempts=[];chosen=None
    for subdivide in (False,True):
        folder=a.output/('residency-subdivided'if subdivide else'residency-original')
        argv=[sys.executable,str(tool),'--sequence',str(seq),'--output',str(folder),'--share-low-offset-map','--tile-layout','frequency','--sparse-maps','--low-slots',str(low_slots)]
        if subdivide:argv.append('--subdivide-static-obj')
        run=subprocess.run(argv,capture_output=True,text=True)
        (a.output/('residency-subdivided.log'if subdivide else'residency-original.log')).write_text(run.stdout+run.stderr)
        attempts.append(dict(subdivision=subdivide,exit_code=run.returncode))
        if run.returncode==0:chosen=folder;break
    if chosen is None:
        (a.output/'admission-failed.json').write_text(json.dumps(dict(tile_demand=counts,low_slots=low_slots,residency_attempts=attempts,
            universal_lossless_infeasibility_proven=False,no_color_reduction=True),indent=2)+'\n')
        raise ValueError('HYBRID_CONTEXT_RESIDENCY_NOT_ADMITTED')
    native=a.output/'native'
    argv=[sys.executable,str(Path(__file__).with_name('m4_hybrid_scene_native.py')),'--assets',str(a.assets),'--output',str(native),
          '--timer',str(a.timer),'--static-residency',str(chosen),'--share-low-offset-map','--resident-bg-tiles']
    with (a.output/'native-runner.log').open('w')as log:run=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT)
    native_result=json.loads((native/'result.json').read_text())if(native/'result.json').exists()else{}
    passed=run.returncode==0 and native_result.get('pass',False)
    result=dict(schema='BYOR_HYBRID_SINGLE_CONTEXT_NATIVE_V1',status='PASS'if passed else'FAIL',source_scene=r['scene'],
                source_rgb555_sha256=r['source_rgb555_sha256'],source_report_sha256=hashlib.sha256((a.assets/'report.json').read_bytes()).hexdigest(),
                tile_demand=counts,low_slots=low_slots,residency_attempts=attempts,
                native_result_path=str(native/'result.json'),native_result_sha256=hashlib.sha256((native/'result.json').read_bytes()).hexdigest()if native_result else None,
                native_pixel_mismatches=native_result.get('pixel_mismatches'),native_obj_overflow_samples=native_result.get('obj_overflow_samples'),
                cgram_observer_verified=native_result.get('cgram_observer_verified'),oam_observer_verified=native_result.get('oam_observer_verified'),
                background_palette_capability=r.get('background_palette_capability',r.get('fixed_background_policy','whole_frame')),
                ordinary_actor_palette_capability='STATIC_OBJ_PALETTE',native_transition_proven=False,production_audio_proven=False,
                live_compositor_proven=False,authored_reachability_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ('status','tile_demand','low_slots','residency_attempts','native_pixel_mismatches','native_obj_overflow_samples')}))
    if not passed:raise ValueError('HYBRID_CONTEXT_NATIVE_PROOF_FAILED')


if __name__=='__main__':main()
