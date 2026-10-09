"""Join unchanged check_move with unchanged movement callbacks in 32-bit C."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_check_move_4086 import check_move
from source_trymove_4086 import common_trymove
from source_trymove_authority import cases, FIELDS, FLOAT_FIELDS, bits, Services, EVENTS
from source_model_core_4086 import binary32

EVENTS.update(freeze=19,link=20)
EXTRA=('mark frozen time nextmove callback grabbing grabwalking pathblocked').split()


def evaluate(c):
    e=dict(update_mark=c['mark'],nextmove=c['nextmove'],landed_on_platform=None,
           position=dict(x=c['x'],z=c['z']),movex=c['xd'],movez=c['zd'],trymove=c['callback'] or None,
           grabbing=c['grabbing'],grabwalking=c['grabwalking'],pathblocked=c['pathblocked'],idling=c['idling'])
    inner=dict(x=c['x'],y=c['y'],z=c['z'],idling=c['idling'],frame_base=c['base'],anim_height=c['animheight'],jump_range=c['jump_range'])
    inner['modeldata']=dict(type=c['type'],hostile=c['hostile'],aimove=c['aimove'],height=c['height'],
        **{'subject_to_'+n:c[k] for n,k in (('minz','min'),('maxz','max'),('screen','screen'),('hole','hole'),('obstacle','obstacle'),('platform','platform'),('wall','wall'))})
    world=dict(minz=c['minz'],maxz=c['maxz'],advancex=c['advancex'],hres=320,wall_height=c['wallheight'],wall_z=c['wallz'],wall_depth=c['walldepth'])
    s=Services(c)
    def frozen(actor):s.record('freeze');return c['frozen']
    def callback(x,z):
        inner.update(e['position']);r=common_trymove(inner,x,z,world,s);e['position'].update(x=inner['x'],z=inner['z']);return r
    def linked(x,z):
        s.record('link',x,z);e['position']['x']=binary32(e['position']['x']+x);e['position']['z']=binary32(e['position']['z']+z)
    check_move(e,c['time'],frozen,callback,linked)
    return [bits(e['position']['x']),bits(e['position']['z']),bits(e['movex']),bits(e['movez']),e['nextmove'],e['update_mark'],e['pathblocked'],1,*s.events]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--movement-authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    parent=json.loads((a.movement_authority/'report.json').read_text())
    if parent['status']!='PASS' or parent['engine_commit']!=ENGINE_COMMIT:raise ValueError('CHECK_MOVE_CALLBACK_PARENT_AUTHORITY')
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
    header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd=a.engine).decode('latin1')
    if 'unsigned pathblocked;' not in header or 'int grabwalking;' not in header:raise ValueError('CHECK_MOVE_FIELD_TYPE_AUTHORITY')
    function=extract(raw,'check_move')
    code=(a.movement_authority/'trymove.c').read_text(encoding='latin1').split('int main(void)',1)[0]
    for name in ('testmove','common_trymove','player_trymove'):
        if extract(raw,name) not in code:raise ValueError('CHECK_MOVE_CALLBACK_UNCHANGED_'+name)
    code=code.replace('int animpos,idling;} entity;', 'int animpos,idling,grabbing,grabwalking;unsigned pathblocked,update_mark,nextmove;float movex,movez;struct entity *landed_on_platform,*link;int (*trymove)(float,float);} entity;')
    code=code.replace('entity actor,other,*self=&actor;', 'entity actor,other,previous,*self=&actor;')
    code+='''
unsigned time;int freeze_result;
int is_frozen(entity *e){event(19);return freeze_result;}
void check_link_move(float x,float z){coords(20,x,z);self->position.x+=x;self->position.z+=z;}
'''+function+'\n'
    main=(a.movement_authority/'trymove.c').read_text(encoding='latin1').split('int main(void)',1)[1]
    old='r=v[0]==0?common_trymove(xd,zd):v[0]==1?player_trymove(xd,zd):testmove(&actor,actor.position.x,actor.position.z,xd,zd);'
    if old not in main:raise ValueError('CHECK_MOVE_CALLBACK_SHIM_CONTRACT')
    fields=FIELDS+EXTRA;main=main.replace('unsigned v['+str(len(FIELDS))+']','unsigned v['+str(len(fields))+']').replace('i<'+str(len(FIELDS))+';','i<'+str(len(fields))+';')
    assignments=dict(mark='actor.update_mark',frozen='freeze_result',time='time',nextmove='actor.nextmove',grabbing='actor.grabbing',grabwalking='actor.grabwalking',pathblocked='actor.pathblocked')
    setup=''.join(lhs+'=v['+str(fields.index(k))+'];' for k,lhs in assignments.items())
    setup+='actor.movex=xd;actor.movez=zd;actor.trymove=v['+str(fields.index('callback'))+']==0?NULL:v['+str(fields.index('callback'))+']==1?player_trymove:common_trymove;self=&previous;check_move(&actor);'
    main=main.replace(old,setup)
    oldprint='printf("%d %u %u",r,bits(actor.position.x),bits(actor.position.z));'
    newprint='printf("%u %u %u %u %u %u %u %u",bits(actor.position.x),bits(actor.position.z),bits(actor.movex),bits(actor.movez),actor.nextmove,actor.update_mark,actor.pathblocked,self==&previous);'
    if oldprint not in main:raise ValueError('CHECK_MOVE_CALLBACK_SHIM_OUTPUT')
    code+='int main(void)'+main.replace(oldprint,newprint)
    (a.output/'check_move_callback.c').write_text(code,encoding='latin1')
    EVENTS.update(freeze=19,link=20)
    base=dict(cases()[0],throw=0,grab=0);rows=[]
    for mark,frozen,time,nextmove,motion,callback,idling,grabbing,grabwalking in itertools.product(
            (0,4,0x80000000),(0,1),(0,48,49,0xffffffff),(0,48,0xffffffff),
            ((0.,0.),(1.5,-.25),(-20.,-50.),(20.,50.)),(0,1,2),(0,1,-65536),(0,1),(0,1,-65536)):
        x,z=((80.,220.),(9.,189.),(311.,241.))[len(rows)%3]
        rows.append(dict(base,x=x,z=z,xd=motion[0],zd=motion[1],mark=mark,frozen=frozen,time=time,nextmove=nextmove,callback=callback,
            idling=idling,grabbing=grabbing,grabwalking=grabwalking,pathblocked=(0,1,0x7fffffff,0x80000000,0xffffffff)[len(rows)%5]))
    inputs=''.join(' '.join(str(bits(c[k]) if k in FLOAT_FIELDS else c[k]&0xffffffff) for k in fields)+'\n' for c in rows)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','check_move_callback.c','-fe=check_move_callback.exe'],cwd=a.output,env=env,capture_output=True,text=True)
    (a.output/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:raise ValueError('CHECK_MOVE_CALLBACK_C_BUILD:'+b.stdout+b.stderr)
    proc=subprocess.run([str(a.output/'check_move_callback.exe')],input=inputs,capture_output=True,text=True)
    actual=[list(map(int,l.split())) for l in proc.stdout.splitlines()];expected=[evaluate(c) for c in rows]
    mismatch=[dict(index=i,input=rows[i],actual=actual[i] if i<len(actual) else None,expected=e) for i,e in enumerate(expected) if i>=len(actual) or actual[i]!=e]
    report=dict(schema='BYOR_4086_CHECK_MOVE_CALLBACK_AUTHORITY_V1',status='PASS' if proc.returncode==0 and actual==expected else 'FAIL',cases=len(rows),
        engine_commit=ENGINE_COMMIT,source_functions_unmodified=True,check_move_sha256=hashlib.sha256(function.encode('latin1')).hexdigest(),parent_authority_sha256=hashlib.sha256((a.movement_authority/'report.json').read_bytes()).hexdigest(),
        inputs_sha256=hashlib.sha256(inputs.encode()).hexdigest(),outputs_sha256=hashlib.sha256(proc.stdout.encode()).hexdigest(),mismatches=mismatch,
        pathblocked_type='uint32',grabwalking_type='int32',unsigned_pathblocked_wrap_covered=True,actual_movement_callbacks_joined=True,
        frozen_and_linked_move_services_instrumented=True,platform_owner_proven=False,script_mutation_proven=False,
        original_engine_binary_float_equivalence=False,native_callback_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'joined source movement cases;',len(mismatch),'mismatches')
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
