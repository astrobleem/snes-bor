"""Pinned common_attack and literal common_move prefix; Q16 air differences."""
import argparse,hashlib,itertools,json,os,re,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_common_drop_authority import f32,q16

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 def source(path):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+path],cwd='E:/gh/openbor-bcec').decode('latin1')
 text=source('engine/openbor.c');header=source('engine/openbor.h')
 enums='\n'.join(re.search(r'typedef enum\s*\{[^}]*'+name+r'[^}]*\}\s*'+typ+r';',header).group()for name,typ in (('AIATTACK1_NORMAL','e_aiattack_1'),('AIMOVE1_CHASE','e_aimove_1')))
 common_move=extract(text,'common_move');prefix=common_move[:common_move.index('        // store this for turning checking')]
 functions='\n\n'.join(extract(text,n)for n in ('diff','inair','common_attack'))
 rows=[]
 for phase,styles,times in ((7,(-1,0,1,2,3,4,7,8,65537,65538,65540,2147483647),(0,1,2,6,7,8,49,50,65536,0xffffffff)),(8,(-1,0,1,64,128,256,512,1024,2048,2176,2304,2560,3072,65536,67584,2147483647),(48,))):
  for style,time,base,delta in itertools.product(styles,times,(-1,0,100),(0,.099999994,.10000000149,1)):
   y=f32(base+delta);b=f32(base);air=int(abs(q16(y)-q16(b))>=6554)
   gated=(time//2%4==0 or style==-1 or style&65535 in (1,2,4))if phase==7 else (style==-1 or (not(style&0x780)and bool(style&0x800)))
   unbound=not gated and ((phase==8 and bool(style&0x780))or not air)
   rows.append(dict(phase=phase,style=style,time=time,y=y,base=b,y_q16=q16(y),base_q16=q16(b),compat_air=air,fault=int(unbound),result=0))
 code='''#include <stdio.h>
#define THINK_SPEED 2
'''+enums+'''
typedef struct entity {struct {float y;} position;float base;struct {int aiattack,aimove;} modeldata;} entity;
entity ent,*self=&ent;unsigned time;int effects;
int normal_attack(void){effects++;return 1;}
int biker_move(void){effects++;return 11;}int arrow_move(void){effects++;return 12;}int star_move(void){effects++;return 13;}int bomb_move(void){effects++;return 14;}
'''+functions+'\n'+prefix+'''        effects++;return 77;
    }
}
'''+ '\nstruct {int phase,style;unsigned time;float y,base;} cases[]={'+','.join('{'+str(c['phase'])+','+str(c['style'])+','+str(c['time'])+'u,'+format(c['y'],'.17g')+','+format(c['base'],'.17g')+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int r;ent.modeldata.aiattack=ent.modeldata.aimove=cases[i].style;time=cases[i].time;ent.position.y=cases[i].y;ent.base=cases[i].base;effects=0;r=cases[i].phase==7?common_attack():common_move();printf("%d,%d,%d\\n",r,effects,inair(self));}return 0;}
'''
 (a.output/'ai_gates.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','ai_gates.c','-fe=ai_gates.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'ai_gates.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()]
 differences=[];expected=[]
 for i,c in enumerate(rows):
  style=c['style'];air=int(f32(abs(f32(c['y'])-f32(c['base'])))>=.1)
  if c['phase']==7:
   result=int(not(c['time']//2%4==0 or style==-1 or style&65535 in (1,2,4))and not air);effect=result
  else:
   result=0 if style==-1 else next((n for bit,n in ((128,11),(256,12),(512,13),(1024,14))if style&bit),0 if style&2048 or air else 77);effect=int(result!=0)
  expected.append([result,effect,air]);c['source_result']=result;c['source_effects']=effect
  if bool(effect)!=bool(c['fault']):differences.append(i)
 ok=actual==expected
 report=dict(schema='BYOR_4086_AI_ACTION_GATE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),common_move_sha256=hashlib.sha256(common_move.encode()).hexdigest(),common_move_prefix_sha256=hashlib.sha256(prefix.encode()).hexdigest(),enums_sha256=hashlib.sha256(enums.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,expected=expected,q16_compat_differences=differences,policy='ACCEPTED_COMPAT Q16 inair >=6554; actual source threshold differences retained',normal_attack_body_instrumented=True,grounded_common_move_tail_instrumented=True,special_move_bodies_instrumented=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'action gate cases;',len(differences),'source/Q16 differences');assert ok
if __name__=='__main__':main()
