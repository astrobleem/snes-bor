"""Independently observe each admitted hybrid frame; no sequence/cadence claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sequence',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timer',type=int,default=158)
    a=p.parse_args();inventory=json.loads((a.sequence/'report.json').read_text())
    if not inventory['complete'] or not inventory['all_frames_compiled']:
        raise ValueError('HYBRID_INCOMPLETE_FRAME_INVENTORY')
    a.output.mkdir(parents=True,exist_ok=True);rows=[]
    for frame in inventory['rows']:
        i=frame['frame'];folder=a.output/('frame-%02d'%i);folder.mkdir(exist_ok=True)
        with (folder/'runner.log').open('w') as log:
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('m4_hybrid_scene_native.py')),
                '--assets',str(a.sequence/('frame-%02d'%i)), '--output',str(folder),
                '--timer',str(a.timer)],stdout=log,stderr=subprocess.STDOUT)
        path=folder/'result.json'
        observed=json.loads(path.read_text()) if path.exists() else {}
        row=dict(frame=i,passed=result.returncode==0 and observed.get('pass',False),
            result_sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
            rom_sha256=observed.get('rom_sha256'),pixel_mismatches=observed.get('pixel_mismatches'),
            active_window_samples=observed.get('active_window_samples'),
            obj_overflow_samples=observed.get('obj_overflow_samples'),
            oam_observer_verified=observed.get('oam_observer_verified'))
        rows.append(row)
        report=dict(schema='BYOR_HYBRID_FRAME_INVENTORY_NATIVE_V1',rows=rows,
            complete=len(rows)==len(inventory['rows']),pass_all_frames=all(r['passed'] for r in rows),
            sequence_inventory_sha256=hashlib.sha256((a.sequence/'report.json').read_bytes()).hexdigest(),
            timer_dots=a.timer,no_color_reduction=True,native_sequence_proven=False,
            scope='Independent static hybrid frames, fresh boot for each; no transfer cadence, moving actors, production audio or MOTU gameplay proof')
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(row),flush=True)
        if not row['passed']:raise SystemExit(1)


if __name__=='__main__':main()
