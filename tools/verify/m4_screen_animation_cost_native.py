"""Measure full source animation shading; no renderer deadline admission."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from compiler import Source
from source_animation_step import derive
import m4_screen_sa1_native as screen


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source',required=True);p.add_argument('--stage',required=True)
 p.add_argument('--scene',type=Path,required=True);p.add_argument('--actor',type=int,required=True)
 p.add_argument('--output',type=Path,required=True);p.add_argument('--first-frame',type=int,default=0)
 p.add_argument('--frame-count',type=int);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 source=Source(a.source);scene=json.loads(a.scene.read_text());actor=scene['actors'][a.actor]
 animation=next(v for v in derive(source)['animations']if v['model'].casefold()==actor['model'].casefold()and v['role']==actor['animation'])
 stop=min(animation['count'],a.first_frame+a.frame_count)if a.frame_count is not None else animation['count']
 if not 0<=a.first_frame<stop<=animation['count']:raise ValueError('ANIMATION_FRAME_RANGE')
 rows=[];tick=sum(animation['delays'][:a.first_frame])
 for frame in range(a.first_frame,stop):
  pose=deepcopy(scene);pose['actors'][a.actor]['frame']=frame;folder=out/('frame-%02d'%frame);folder.mkdir(exist_ok=True)
  pose_path=folder/'scene.json';pose_path.write_text(json.dumps(pose)+'\n');pairs,metadata=screen.capture(source,a.stage,pose)
  pixels=len(pairs)//3
  if pixels:
   cmd=[sys.executable,str(Path(__file__).with_name('m4_screen_grouped_native.py')),'--source',a.source,'--stage',a.stage,'--scene',str(pose_path),'--output',str(folder),'--busy-host','--gather-underlay','--move-x','0']
   with (folder/'runner.log').open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,env=os.environ.copy())
   r=json.loads((folder/'report.json').read_text())
   if r['status']!='PASS' or any(r['RGB555_byte_mismatches']):raise ValueError('ANIMATION_NATIVE_PIXEL_MISMATCH')
   clocks=max(r['master_clocks']);digest=r['rom_sha256'];report_hash=hashlib.sha256((folder/'report.json').read_bytes()).hexdigest()
  else:clocks=0;digest=None;report_hash=None
  row=dict(frame=frame,start_source_tick=tick,delay_ticks=animation['delays'][frame],opaque_pixels=pixels,peak_shader_master_clocks=clocks,shader_ms=clocks/21477.27,native_job_proven=bool(pixels),transparent_no_shader_required=not bool(pixels),rom_sha256=digest,report_sha256=report_hash,source_effect_layers=[v for v in metadata['layers']if v['alpha']==1])
  rows.append(row);tick+=animation['delays'][frame]
  result=dict(schema='BYOR_SOURCE_SCREEN_ANIMATION_NATIVE_COST_V1',status='MEASURED_PARTIAL'if len(rows)<stop-a.first_frame else'MEASURED',source_animation_handle=animation['handle'],source_frame_count=animation['count'],rows=rows,measured_frames=[a.first_frame,frame],source_duration_ticks=sum(animation['delays']),peak_shader_master_clocks=max(v['peak_shader_master_clocks']for v in rows),sum_shader_master_clocks=sum(v['peak_shader_master_clocks']for v in rows),no_color_reduction=True,deadline_admitted=False,native_underlay_composition=False,joint_audio_proven=False,motu_gameplay_proven=False,scope='Native source-address SCREEN gather/shading for every measured source frame with explicit fixed opaque actors/camera. Underlay composition, palette planning, CHR transfer and joint audio costs are excluded. Transparent source frames need no SCREEN job.')
  (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(row),flush=True)


if __name__=='__main__':main()
