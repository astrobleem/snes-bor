"""Literal pinned set_fall, including braced unfreeze and fallback attack type."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_animation_ids import configure
FIELDS=('drop','inpain','idling','falling','jumping','getting','charging','attacking','blocking','nograb','frozen')

def reference(row,falls):
 kind,mask,frozen,frame,script,reset=row;flags=dict.fromkeys(FIELDS,-7);flags['frozen']=frozen;deadline=0x12345678;visible=99;events=[];selected=-1;t=kind
 def valid(n):
  events.append(1000+n)
  return bool(mask&(2 if n==falls[0]else 1))
 if t<0 or t>=len(falls)or not valid(falls[t]):t=0
 if not valid(falls[t]):result=0
 else:
  selected=falls[t];events.append(2000+selected)
  if frame:flags=dict.fromkeys(FIELDS,17)
  flags.update(drop=1,inpain=0,idling=0,falling=1,jumping=0,getting=0,charging=0,attacking=0,blocking=0,nograb=1)
  if flags['frozen']:events.append(3000);flags['frozen']=0;deadline=0;visible=7
  events.extend([4000,t,reset]);result=1
  if script:flags['drop']=23;flags['inpain']=-9
 values=[result,selected,*[flags[f]for f in FIELDS],deadline,visible,len(events),*events]
 return struct.pack('<32I',*[v&0xffffffff for v in values+[0]*(32-len(values))])

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');header=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1');function=extract(raw,'set_fall');at=header.index('#define unfrozen(');macro=header[at:header.index('\n\n',at)];falls=configure([])['arrays']['falls']
 rows=list(itertools.product((-3,-1,0,1,3,19,20,65536),range(4),(-3,0,1),range(2),range(2),range(2)));payload=b''.join(struct.pack('<6i',*r)for r in rows)
 code='''#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef struct entity{'''+','.join(['int '+FIELDS[0],*FIELDS[1:]])+''';unsigned freezetime;int map,visiblemap;}entity;
int max_attack_types=20,animfalls[20]={'''+','.join(map(str,falls))+'''};
int selected,validmask,frame_mutation,script_mutation,ne,events[16],requested;
void event(int n){events[ne++]=n;}
int validanim(entity*e,int n){event(1000+n);return !!(validmask&(n==animfalls[0]?2:1));}
void ent_set_anim(entity*e,int n,int r){selected=n;event(2000+n);if(frame_mutation){'''+''.join('e->'+f+'=17;'for f in FIELDS)+'''}}
void ent_set_colourmap(entity*e,int n){event(3000);e->visiblemap=n;}
void execute_onfall_script(entity*e,entity*o,int f,int d,int t,int b,int g,int j,int p){if(o==e||f!=7||d!=1||b!=2||g!=3||j!=4||p!=5){fprintf(stderr,"BAD_CHILD_PARAMETERS");_exit(9);}event(4000);event(t);event(requested);if(script_mutation){e->drop=23;e->inpain=-9;}}
'''+macro+'\n'+function+'''
int main(void){int row[6],i;entity e,other;unsigned output[32];setmode(fileno(stdin),O_BINARY);setmode(fileno(stdout),O_BINARY);
while(fread(row,sizeof(row),1,stdin)==1){memset(&e,0,sizeof(e));memset(output,0,sizeof(output));'''+''.join('e.'+f+'=-7;'for f in FIELDS)+'''
e.frozen=row[2];e.freezetime=0x12345678;e.map=7;e.visiblemap=99;validmask=row[1];frame_mutation=row[3];script_mutation=row[4];requested=row[5];selected=-1;ne=0;
output[0]=set_fall(&e,row[0],row[5],&other,7,1,2,3,4,5);output[1]=selected;
'''+''.join('output['+str(2+i)+']=e.'+f+';'for i,f in enumerate(FIELDS))+'''
output[13]=e.freezetime;output[14]=e.visiblemap;output[15]=ne;for(i=0;i<ne;i++)output[16+i]=events[i];if(fwrite(output,sizeof(output),1,stdout)!=1)return 2;}return 0;}
'''
 (out/'authority.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');q=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','authority.c','-fe=authority.exe'],cwd=out,env=env,capture_output=True,text=True);(out/'build.log').write_text(q.stdout+q.stderr)
 if q.returncode:raise ValueError('SET_FALL_C_BUILD:'+q.stdout+q.stderr)
 actual=subprocess.check_output([str(out/'authority.exe')],input=payload);expected=b''.join(reference(r,falls)for r in rows);mismatches=[i for i in range(len(rows))if actual[i*128:(i+1)*128]!=expected[i*128:(i+1)*128]]
 for name,data in [('inputs',payload),('actual',actual),('expected',expected)]:(out/(name+'.bin')).write_bytes(data)
 report=dict(schema='BYOR_SET_FALL_4086_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),mismatches=mismatches[:20],literal_function_unmodified=True,function_sha256=hashlib.sha256(function.encode('latin1')).hexdigest(),unfreeze_macro_unmodified=True,unfreeze_macro_sha256=hashlib.sha256(macro.encode('latin1')).hexdigest(),falls=falls,actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),unfreeze_only_when_frozen=True,instrumented_children=['validanim','ent_set_anim/frame','colourmap','onfall'],full_callback_native_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'set_fall cases',len(mismatches),'mismatches')
 if actual!=expected:raise SystemExit(1)
if __name__=='__main__':main()
