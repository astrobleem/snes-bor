"""Literal pinned set_pain selection, frame-call ordering and painflags.

Animation/frame, unfreeze and onpain callbacks are instrumented here. They
are explicit children, not acknowledgements of a native full callback.
"""
import argparse, hashlib, itertools, json, os, struct, subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_animation_ids import configure

FIELDS = ('idling','falling','projectile','drop','attacking','getting',
          'charging','jumping','blocking','inpain','frozen')


def reference(row, pains, enum):
    kind, valid_mask, maximum, current, frozen, frame_mutation, script_mutation, reset = row
    velocity = [37.,38.,39.]; flags = dict.fromkeys(FIELDS,-7); flags['frozen']=frozen
    velocity = [0.,0.,0.]
    if maximum>0 and current<=0:
        requested=enum['ANI_GUARDBREAK']; current=maximum
    elif kind==-1 or kind>=len(pains):requested=enum['ANI_GRABBED']
    else:requested=pains[kind]
    valid={requested:bool(valid_mask&1),pains[0]:bool(valid_mask&2),enum['ANI_IDLE']:bool(valid_mask&4)}
    events=[]; chosen=-1
    for number in (requested,pains[0],enum['ANI_IDLE']):
        events.append(1000+number)
        if valid[number]:chosen=number; break
    result=0
    if chosen!=-1:
        events.append(2000+chosen)
        if frame_mutation:
            velocity=[73.,74.,75.]; flags=dict.fromkeys(FIELDS,17)
        for field in FIELDS[:-2]:flags[field]=0
        flags['inpain']=1
        if flags['frozen']:
            events.append(3000);flags['frozen']=0
        if requested==enum['ANI_GRABBED']:flags['inpain']=0
        events.append(4000)
        if script_mutation:flags['inpain']=-9;flags['drop']=23
        result=1
    bits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
    values=[result,requested,chosen,current,*map(bits,velocity),*[flags[f]for f in FIELDS],len(events),*events]
    return struct.pack('<'+'I'*27,*[v&0xffffffff for v in values+[0]*(27-len(values))])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    function=extract(raw,'set_pain');at=raw.index('#define painflags(');macro=raw[at:raw.index('\n\n',at)]
    ids=configure([]);pains=ids['arrays']['pains'];enum=ids['authority']['enum']
    rows=list(itertools.product((-1,0,1,3,19,20),range(8),((0,0),(5,-1),(5,3),(-1,-1)),(-3,0,1),(0,1),(0,1),(0,1)))
    rows=[(kind,mask,*guard,frozen,frame,script,reset)for kind,mask,guard,frozen,frame,script,reset in rows]
    payload=b''.join(struct.pack('<8i',*row)for row in rows)
    code='''#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef struct entity {struct{float x,y,z;}velocity;struct{struct{int max,current;}guardpoints;}modeldata;
'''+','.join(['int '+FIELDS[0],*FIELDS[1:]])+''';}entity;
int max_attack_types=20,animpains[20]={'''+','.join(map(str,pains))+'''};
enum {ANI_IDLE='''+str(enum['ANI_IDLE'])+',ANI_GRABBED='+str(enum['ANI_GRABBED'])+',ANI_GUARDBREAK='+str(enum['ANI_GUARDBREAK'])+'''};
int candidate,validmask,frame_mutation,script_mutation,selected,event_count,events[8];
void event(int v){events[event_count++]=v;}
int validanim(entity*e,int n){event(1000+n);if(n==ANI_IDLE)return !!(validmask&4);if(n==animpains[0])return !!(validmask&2);return n==candidate&&!!(validmask&1);}
void ent_set_anim(entity*e,int n,int reset){selected=n;event(2000+n);
if(frame_mutation){e->velocity.x=73;e->velocity.y=74;e->velocity.z=75;
'''+''.join('e->'+f+'=17;'for f in FIELDS)+'''}}
void unfrozen(entity*e){event(3000);e->frozen=0;}
void execute_onpain_script(entity*e,int t,int r){event(4000);if(script_mutation){e->inpain=-9;e->drop=23;}}
'''+macro+'\n'+function+'''
int main(void){int row[8],i,returned;unsigned output[27];entity e;
setmode(fileno(stdin),O_BINARY);setmode(fileno(stdout),O_BINARY);
if(sizeof(int)!=4||sizeof(float)!=4)return 1;
while(fread(row,sizeof(row),1,stdin)==1){memset(&e,0,sizeof(e));memset(output,0,sizeof(output));
'''+''.join('e.'+f+'=-7;'for f in FIELDS)+'''
e.velocity.x=37;e.velocity.y=38;e.velocity.z=39;e.modeldata.guardpoints.max=row[2];e.modeldata.guardpoints.current=row[3];e.frozen=row[4];
validmask=row[1];frame_mutation=row[5];script_mutation=row[6];selected=-1;event_count=0;
candidate=row[2]>0&&row[3]<=0?ANI_GUARDBREAK:row[0]==-1||row[0]>=max_attack_types?ANI_GRABBED:animpains[row[0]];
returned=set_pain(&e,row[0],row[7]);output[0]=returned;output[1]=candidate;output[2]=selected;output[3]=e.modeldata.guardpoints.current;
memcpy(output+4,&e.velocity.x,4);memcpy(output+5,&e.velocity.y,4);memcpy(output+6,&e.velocity.z,4);
'''+''.join('output['+str(7+i)+']=e.'+f+';'for i,f in enumerate(FIELDS))+'''
output[18]=event_count;for(i=0;i<event_count;i++)output[19+i]=events[i];if(fwrite(output,sizeof(output),1,stdout)!=1)return 2;
}return 0;}
'''
    (out/'set-pain.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    run=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','set-pain.c','-fe=set-pain.exe'],cwd=out,env=env,capture_output=True,text=True)
    (out/'build.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise ValueError('SET_PAIN_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'set-pain.exe')],input=payload,cwd=out)
    expected=b''.join(reference(row,pains,enum)for row in rows)
    mismatches=[i for i in range(len(rows))if actual[i*108:(i+1)*108]!=expected[i*108:(i+1)*108]]
    (out/'inputs.bin').write_bytes(payload);(out/'actual.bin').write_bytes(actual);(out/'expected.bin').write_bytes(expected)
    report=dict(schema='BYOR_SET_PAIN_4086_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,source_function_unmodified=True,source_function_sha256=hashlib.sha256(function.encode('latin1')).hexdigest(),source_macro_unmodified=True,source_macro_sha256=hashlib.sha256(macro.encode('latin1')).hexdigest(),cases=len(rows),mismatched_cases=mismatches[:20],actual_bytes=len(actual),expected_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),input_sha256=hashlib.sha256(payload).hexdigest(),source_pain_ids=pains,source_role_ids={k:enum[k]for k in('ANI_IDLE','ANI_GRABBED','ANI_GUARDBREAK')},negative_type_below_minus_one_admitted=False,instrumented_children=['validanim','ent_set_anim/frame callback','unfrozen','execute_onpain_script'],native_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(rows),'literal set_pain cases','mismatches',len(mismatches))
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
