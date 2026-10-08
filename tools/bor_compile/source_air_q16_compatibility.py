"""Measure Q16 air integration against retained pinned C and source trajectories."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from source_check_gravity_air_4086 import check_gravity_air
from source_check_gravity_air_q16 import check_gravity_air_q16
from source_level_physics_4086 import derive as level_physics
from source_frame_effects_4086 import derive as frame_effects
from source_model_core_4086 import binary32


def q(value):return round(binary32(value)*65536)
def floating(bits):return struct.unpack('<f',struct.pack('<I',bits))[0]


def run(source,authority,output):
    pinned=json.loads(authority.read_text());assert pinned['status']=='PASS'
    one_step=[];discrete_failures=[]
    for index,(c,actual)in enumerate(zip(pinned['inputs'],pinned['actual'])):
        physics=dict(gravity=q(c['gravity']),maxfallspeed=q(-6),maxtossspeed=q(100))
        e=dict(update_mark=c['mark'],toss_time=c['toss'],falling=0,velocity_y=q(c['velocity']),a=q(100),base=q(34),
            height=0,subject_to_platform=1,animation_antigrav=c['animation_antigrav'],antigravity=q(c['antigravity']),
            subject_to_gravity=c['subject'],dropframe=-1,animpos=0,idling=0,walkoff_valid=False,hithead=1)
        calls=[]
        check_gravity_air_q16(e,c['time'],physics,lambda e:calls.append('adjust'),lambda e:(calls.append('freeze')or bool(c['freeze'])),lambda e:calls.append('movea'))
        discrete=[e['update_mark'],e['toss_time'],int(e['hithead']is not None),calls.count('adjust'),calls.count('freeze'),calls.count('movea'),1]
        if discrete!=actual[2:]:discrete_failures.append(index)
        one_step.append(dict(index=index,altitude_error_q16_units=e['a']-q(floating(actual[0])),
            velocity_error_q16_units=e['velocity_y']-q(floating(actual[1]))))
    velocities=sorted({float(a['events']['jump_y'])for a in frame_effects(source)['animations']if float(a['events']['jump_y'])>0})
    trajectories=[]
    for stage in level_physics(source)['stages']:
        physics=stage['physics'];fixed={k:q(v)for k,v in physics.items()}
        for velocity in velocities:
            common=dict(update_mark=0,toss_time=0,falling=1,base=0, height=0,subject_to_platform=1,
                animation_antigrav=0,antigravity=0,subject_to_gravity=1,dropframe=-1,animpos=0,idling=0,
                walkoff_valid=False,hithead=None)
            f=dict(common,a=0.0,velocity_y=binary32(velocity));n=dict(common,a=0,velocity_y=q(velocity))
            land_f=land_n=None;peak_a=peak_v=0.0;trace=[]
            for time in range(2000):
                def landing_f(e):
                    nonlocal land_f
                    land_f=time;e['a']=e['base'];e['falling']=0;e['velocity_y']=0
                def landing_n(e):
                    nonlocal land_n
                    land_n=time;e['a']=e['base'];e['falling']=0;e['velocity_y']=0
                if land_f is None:
                    f['update_mark']=0;check_gravity_air(f,time,physics,lambda e:None,lambda e:False,lambda e:None,landing_f)
                if land_n is None:
                    n['update_mark']=0;check_gravity_air_q16(n,time,fixed,lambda e:None,lambda e:False,lambda e:None,landing_n)
                error_a=n['a']/65536-f['a'];error_v=n['velocity_y']/65536-f['velocity_y']
                peak_a=max(peak_a,abs(error_a));peak_v=max(peak_v,abs(error_v))
                trace.append([time,f['a'],n['a'],f['velocity_y'],n['velocity_y']])
                if land_f is not None and land_n is not None:break
            trajectories.append(dict(stage=stage['source_path'],initial_source_frame_jump_velocity=velocity,
                source_landing_tick=land_f,q16_landing_tick=land_n,landing_tick_difference=None if land_f is None or land_n is None else land_n-land_f,
                peak_altitude_error_pixels=peak_a,peak_velocity_error=peak_v,trace=trace))
    report=dict(schema='BYOR_4086_AIR_Q16_COMPATIBILITY_V1',status='PASS'if not discrete_failures and all(t['source_landing_tick']is not None and t['q16_landing_tick']is not None for t in trajectories)else'FAIL',
        engine_commit=ENGINE_COMMIT,authority_path=str(authority).replace('\\','/'),authority_sha256=hashlib.sha256(authority.read_bytes()).hexdigest(),
        source_c_one_step_cases=len(one_step),discrete_failures=discrete_failures,
        peak_one_step_altitude_error_q16_units=max(abs(c['altitude_error_q16_units'])for c in one_step),
        peak_one_step_velocity_error_q16_units=max(abs(c['velocity_error_q16_units'])for c in one_step),
        one_step_results=one_step,source_frame_jump_velocities=velocities,trajectories=trajectories,
        numeric_policy='ACCEPTED_COMPAT_Q16_16; nearest input conversion, arithmetic-shift halves, fixed multiplication floor; source inair threshold approximated by6554units',
        numeric_binary32_exact=False,trajectory_scope='Derived stage constants and authored jump velocities, controlled sticky base/no animation changes/no callbacks/no bounce; stops at first landing; not authored gameplay',
        native_airborne_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(one_step),'C cases',len(trajectories),'trajectories',
        'peak velocity LSB',report['peak_one_step_velocity_error_q16_units'],
        'peak altitude pixels',max((t['peak_altitude_error_pixels']for t in trajectories),default=0))
    assert report['status']=='PASS'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(Source(a.source),a.authority,a.output)


if __name__=='__main__':main()
