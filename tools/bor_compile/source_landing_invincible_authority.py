"""Pinned checkdamage with real empty script dispatchers at pit/lifespan limits."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--coupled-authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 report=json.loads((a.coupled_authority/'report.json').read_text());assert report['status']=='PASS'and report['actual_empty_damage_script_dispatchers_proven']
 code=(a.coupled_authority/'callback.c').read_text().split('\nstruct Case{',1)[0]
 raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 bodies={n:extract(raw,n)for n in('checkdamage','execute_takedamage_script','execute_ondeath_script')}
 for name,body in bodies.items():assert extract(code,name)==body
 assert 'escapecount,lifespancountdown;'in code
 header=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
 import re
 pit=int(re.search(r'^#define\s+PIT_DEPTH\s+(-?\d+)',header,re.M)[1]);assert pit==-250
 rows=[dict(y=y,life=life,invincible=inv,maximum=maximum)for y,life,inv,maximum in itertools.product((pit-1.,pit-1/65536,pit,pit+1/65536,pit+1.,0.),(-2147483648,-1,0,1,2147483647),(-1,0,1,2,3,2147483647),(0,300))]
 code+='\nstruct Case{float y;int life,invincible,maximum;}cases[]={\n'+',\n'.join('{%sf,%s,%s,%s}'%(str(float(r['y'])),'(-2147483647-1)'if r['life']==-2147483648 else r['life'],r['invincible'],r['maximum'])for r in rows)+'\n};\n'
 code+=r'''
int main(void){unsigned i;s_attack attack;struct Case *c;
if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
c=cases+i;memset(&victim,0,sizeof(victim));memset(&attack,0,sizeof(attack));self=&victim;victim.scripts=&script_set;
victim.health=1;victim.modeldata.health=c->maximum;victim.position.y=c->y;victim.lifespancountdown=c->life;victim.invincible=c->invincible;
victim.offense_factors[ATK_LAND]=victim.defense[ATK_LAND].factor=1;attack.attack_force=7;attack.attack_type=ATK_LAND;
ne=0;checkdamage(self,&attack);printf("INV|%u|%d,%d\n",i,victim.health,ne);
}return 0;}
'''
 (a.output/'invincible.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','invincible.c','-fe=invincible.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise ValueError('INVINCIBLE_SOURCE_C_BUILD:'+build.stdout+build.stderr)
 log=subprocess.check_output([str(a.output/'invincible.exe')],cwd=a.output,text=True);actual=[];expected=[]
 for line,r in zip(log.splitlines(),rows):
  _,index,values=line.split('|');assert int(index)==len(actual);actual.append(list(map(int,values.split(','))))
  value=-6
  if r['y']>=pit and r['life']>=0:
   if r['invincible']==2:value=1
   elif r['invincible']==3:value=r['maximum']
  expected.append([value,0])
 ok=actual==expected and len(actual)==len(rows)
 out=dict(schema='BYOR_4086_LANDING_INVINCIBLE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),inputs=rows,actual=actual,expected=expected,
  functions={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},lifespan_type='signed int32, pinned engine/openbor.h',pit_depth=pit,pit_authority='pinned engine/openbor.h',source_pit_comparison='strict y<PIT_DEPTH',source_scripts_uninitialized=True,native_death_service_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],len(rows),'source invincibility boundary cases')
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
