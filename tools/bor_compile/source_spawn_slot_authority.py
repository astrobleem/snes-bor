"""Pinned first-slot predicate under an explicit fixed heap lease."""
import argparse,hashlib,itertools,json,os,re,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT

def fixtures():
 rows=[]
 for priority,old,override,pattern in itertools.product((-2147483648,-65537,-65536,-2,-1,0,1,2147483647),(-2147483648,-65537,-65536,-2,-1,0,1,2147483647),(-2147483648,-1,0,1,2,4,65536,2147483647),range(5)):
  exists=([0,1,1,0],[1,0,1,0],[1,1,0,0],[1,1,1,0],[1,1,1,1])[pattern];rows.append(dict(priority=priority,old=old,override=override,exists=exists,count=sum(exists)))
 rows.extend(ordered_fixtures())
 return rows

def ordered_fixtures():
 rows=[]
 for order,priority,override,pattern in itertools.product(itertools.permutations(range(4)),(-2147483648,-65537,-65536,-2,-1,0,1,2147483647),(-1,2147483647),range(5)):
  exists=([0,1,1,0],[1,0,1,0],[1,1,0,0],[1,1,1,0],[1,1,1,1])[pattern]
  rows.append(dict(priority=priority,old=-1,override=override,exists=exists,count=sum(exists),order=list(order)))
 return rows

def choose(c):
 if c['count']>=len(c['exists']):return dict(slot=-1,needkill=0,limit=1)
 for i in c.get('order',range(len(c['exists']))):
  exists=c['exists'][i]
  if not exists or c['count']>=c['override']and c['old']<0 and c['old']<=c['priority']:return dict(slot=i,needkill=exists,limit=0)
 raise ValueError('SPAWN_SLOT_REFERENCE')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');predicate=re.search(r'if\(!ent_list\[i\]->exists \|\| \(ent_count[^\n]+',raw)[0].strip();rows=fixtures();data=',\n'.join('{'+','.join(str(c[k])for k in('priority','old','override'))+',{'+','.join(map(str,c['exists']))+'}}'for c in rows)
 code='#include <stdio.h>\n#include <string.h>\ntypedef struct {int priority;} Model;typedef struct {int exists;Model modeldata;} Entity;\nstruct {int priority,old,override,exists[4];} cases[]={'+data+'};\n'
 code+='int main(void){Entity pool[4],*ent_list[4];Model m,*model=&m;int i,j,ent_count,spawnoverride,slot,kill,limit;unsigned n;if(sizeof(int)!=4||sizeof(void*)!=4)return 2;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){ent_count=0;model->priority=cases[n].priority;spawnoverride=cases[n].override;for(i=0;i<4;i++){ent_list[i]=pool+i;pool[i].exists=cases[n].exists[i];pool[i].modeldata.priority=cases[n].old;ent_count+=pool[i].exists;}slot=-1;kill=0;limit=ent_count>=4;if(!limit)for(i=0;i<4;i++){'+predicate+'{slot=i;kill=ent_list[i]->exists;break;}}printf("SLOT|%u|%d|%d|%d\\n",n,slot,kill,limit);}return 0;}\n'
 # Keep the literal source predicate; expose physical pool identity separately
 # from the ent_list index after arbitrary valid pointer permutations.
 data=',\n'.join('{'+','.join(str(c[k])for k in('priority','old','override'))+',{'+','.join(map(str,c['exists']))+'},{'+','.join(map(str,c.get('order',range(4))))+'}}'for c in rows)
 code=code.replace('exists[4];} cases[]', 'exists[4],order[4];} cases[]')
 start=code.index('cases[]={')+len('cases[]={');end=code.index('};\n',start)
 code=code[:start]+data+code[end:]
 code=code.replace('ent_list[i]=pool+i;', 'ent_list[i]=pool+cases[n].order[i];')
 code=code.replace('{slot=i;kill=ent_list[i]->exists;', '{slot=(int)(ent_list[i]-pool);kill=ent_list[i]->exists;')
 (a.output/'slots.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','slots.c','-fe=slots.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
 if proc.returncode:raise ValueError('SPAWN_SLOT_AUTHORITY_C_BUILD')
 log=subprocess.check_output([str(a.output/'slots.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);results=[]
 for line in log.splitlines():
  if not line.startswith('SLOT|'):continue
  _,i,slot,kill,limit=line.split('|');i=int(i);actual=dict(slot=int(slot),needkill=int(kill),limit=int(limit));wanted=choose(rows[i]);results.append(dict(case=rows[i],actual=actual,expected=wanted,pass_case=actual==wanted))
 ok=len(results)==len(rows)and all(x['pass_case']for x in results);r=dict(schema='BYOR_4086_FIXED_SPAWN_SLOT_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,predicate=predicate,predicate_sha256=hashlib.sha256(predicate.encode()).hexdigest(),cases=len(results),results=results,heap_growth_policy='Explicit bounded lease; full capacity is a resource limit. Original alloc_ents and kill services are not implemented by this predicate proof.',native_allocation_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(results),'first-slot predicate cases')
 if not ok:raise SystemExit(1)
if __name__=='__main__':main()
