"""Literal full check_costmove/check_energy/unlink, animation service observed."""
import argparse,hashlib,json,os,re,struct,subprocess
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_animation_energy_4086 import derive
from source_costmove_4086 import execute


def cases(report):
    authored=[a for a in report['animations']if a['role'].lower().startswith(('freespecial','special'))]
    for n in range(2304):
        a=authored[n%len(authored)];fields=dict(a['fields'])
        if n%5==0:fields=dict(cost=(-3,0,6,100)[(n//5)%4],mponly=(n//20)%4,disable=(0,-1,-2,-3,-4)[(n//80)%5])
        t=(1,2,512,513)[n%4];cost=fields['cost']
        entity=dict(modeldata=dict(type=t,animation={5:dict(energycost=fields,numframes=0 if n%17==0 else 2)}),
                    seal=(0,cost-1,cost,cost+1)[(n//4)%4],mp=(cost-1,cost,cost+10)[(n//16)%3],
                    health=(cost,cost+1,cost+30)[(n//48)%3],takeaction=99,velocity=dict(x=3.5,z=-2.5),
                    attacking=0,idling=3,inpain=9,combostep=[1,2,3,4,5],grabbing=object(),link=None)
        peer=dict(link=entity,grabbing=entity)
        linked=n%3!=0
        if linked:entity['link']=peer
        context=dict(nospecial=(-1,0,1,2,3,4)[(n//144)%6],nocost=(n//864)%2,healthcheat=(n//432)%2)
        fs=(0,1,2)[(n//12)%3];jump=n%2
        original=dict(type=t,fields=fields,frames=entity['modeldata']['animation'][5]['numframes'],seal=entity['seal'],mp=entity['mp'],health=entity['health'])
        gen=execute(entity,context,5,fs,jump);events=[]
        while True:
            try:events.append(next(gen))
            except StopIteration as stop:result=stop.value;break
        bits=lambda f:struct.unpack('<I',struct.pack('<f',f))[0]
        values=[result,entity['mp'],entity['health'],entity['takeaction'],entity['attacking'],entity['idling'],entity['inpain'],*entity['combostep'],
                int(peer['link']is not None),int(peer['grabbing']is not None),int(entity['link']is not None),int(entity['grabbing']is not None),
                bits(entity['velocity']['x']),bits(entity['velocity']['z']),len(events),events[0][2]if events else 0]
        yield dict(original=original,context=context,fs=fs,jump=jump,linked=linked,expected=struct.pack('<20I',*[v&0xffffffff for v in values]),origin=a['model']+'/'+a['role'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    def pinned(path):return subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':'+path]).decode('latin1')
    source=pinned('engine/openbor.c');header=pinned('engine/openbor.h')
    functions={n:extract(source,n)for n in ('check_costmove','check_energy','ent_unlink')}
    enums='\n'.join(re.search(r'typedef enum\s*\{[^}]*\}\s*'+n+r'\s*;',header,re.S)[0]for n in ('e_cost_check','e_cost_type','e_entity_type'))
    macro=re.search(r'#define set_attacking\(e\)[^\n]*\\\s*\n[^\n]*',header)[0]
    rows=list(cases(derive(Source(a.source))))
    code='''#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#define TRUE 1
#define FALSE 0
typedef unsigned long u32;
'''+enums+'\n'+macro+'''
typedef struct {struct {int cost,mponly,disable;}energycost;int numframes;}animation;
typedef struct entity {struct {int type;animation*animation[168];}modeldata;int seal,mp,health,attacking,idling,inpain,combostep[5];void(*takeaction)(void);struct {float x,z;}velocity;struct entity*link,*grabbing;}entity;
entity e,peer,*self=&e;animation an;struct {int nospecial;}lev,*level=&lev;
int nocost,healthcheat,calls,lastanim;
#define validanim(e,a) ((e)->modeldata.animation[a]&&(e)->modeldata.animation[a]->numframes)
void common_attack_proc(void){}void old_action(void){}
void ent_set_anim(entity*e,int s,int reset){if(reset!=0)calls=999;calls++;lastanim=s;}
'''+ '\n'.join(functions.values())+'\n'
    data=[]
    for c in rows:
        v=c['original'];f=v['fields'];o=c['context']
        values=[v['type'],f['cost'],f['mponly'],f['disable'],v['frames'],v['seal'],v['mp'],v['health'],o['nospecial'],o['nocost'],o['healthcheat'],c['fs'],c['jump'],int(c['linked'])]
        data.append('{'+','.join(str(v)for v in values)+'}')
    code+='int cases[][14]={'+',\n'.join(data)+'''};
int main(void){u32 words[20];int ret,i,n;int *v;setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4||sizeof(float)!=4)return 3;
for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
v=cases[n];memset(&e,0,sizeof(e));memset(&peer,0,sizeof(peer));
e.modeldata.animation[5]=&an;e.modeldata.type=v[0];an.energycost.cost=v[1];an.energycost.mponly=v[2];an.energycost.disable=v[3];an.numframes=v[4];e.seal=v[5];e.mp=v[6];e.health=v[7];
e.takeaction=old_action;e.velocity.x=3.5f;e.velocity.z=-2.5f;e.idling=3;e.inpain=9;for(i=0;i<5;i++)e.combostep[i]=i+1;e.grabbing=&peer;peer.link=&e;peer.grabbing=&e;
e.link=v[13]?&peer:NULL;level->nospecial=v[8];nocost=v[9];healthcheat=v[10];calls=lastanim=0;ret=check_costmove(5,v[11],v[12]);
words[0]=ret;words[1]=e.mp;words[2]=e.health;words[3]=e.takeaction==common_attack_proc?17:99;words[4]=e.attacking;words[5]=e.idling;words[6]=e.inpain;for(i=0;i<5;i++)words[7+i]=e.combostep[i];words[12]=peer.link!=NULL;words[13]=peer.grabbing!=NULL;words[14]=e.link!=NULL;words[15]=e.grabbing!=NULL;memcpy(words+16,&e.velocity.x,4);memcpy(words+17,&e.velocity.z,4);words[18]=calls;words[19]=lastanim;fwrite(words,4,20,stdout);
}
'''
    code+='return 0;}\n';(out/'costmove.c').write_text(code,encoding='utf-8')
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','costmove.c','-fe=costmove.exe'],cwd=out,env=env,capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr,encoding='utf-8')
    if build.returncode:raise ValueError('COSTMOVE_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'costmove.exe')],cwd=out);expected=b''.join(c['expected']for c in rows);ok=actual==expected
    errors=[dict(case=i,origin=c['origin'],actual=list(struct.unpack('<20I',actual[80*i:80*i+80])),expected=list(struct.unpack('<20I',c['expected'])))for i,c in enumerate(rows)if actual[80*i:80*i+80]!=c['expected']]
    r=dict(schema='BYOR_4086_COSTMOVE_AUTHORITY_V1',status='PASS'if ok else'FAIL',cases=len(rows),engine_commit=ENGINE_COMMIT,
           literal_source_functions_unmodified=True,function_sha256={n:hashlib.sha256(s.encode()).hexdigest()for n,s in functions.items()},
           macro_sha256=hashlib.sha256(macro.encode()).hexdigest(),compared_state_bytes=len(expected),errors=errors[:10],
           actual_sha256=hashlib.sha256(actual).hexdigest(),animation_service_instrumented=True,native_costmove_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(r['status'],len(rows),'literal costmove cases');assert ok

if __name__=='__main__':main()
