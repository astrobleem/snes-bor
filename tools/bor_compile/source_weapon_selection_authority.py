"""Pinned set_weapon selection and player bookkeeping; transition instrumented."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def fixtures():
    return [dict(type=t,loss=loss,player=p,number=n,anim_flag=a,weapon=w)
        for t in (0,1,3,512) for loss in (-1,0,3) for p in (0,3)
        for n in (-2147483648,-1,0,1,2,3,2147483647) for a in (0,1,-1)
        for w in (None,[],[2,0],[0,1],[-1,2])]


def expected(c):
    number=c['number'];weapons=c['weapon'];unsafe=bool(weapons and 0<number<=len(weapons) and weapons[number-1]<0)
    values=[77]*4
    if c['type']&1:values[c['player']]=number if c['loss']==3 else 5
    active=bool(weapons and 0<number<=len(weapons) and weapons[number-1])
    return dict(unsafe=unsafe,model=weapons[number-1] if active else 3,sync=int(not c['anim_flag']) if active else 1,players=values)


def run(engine,folder):
    folder.mkdir(parents=True,exist_ok=True);raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine).decode('latin1');function=extract(raw,'set_weapon');rows=fixtures()
    c='''#include <stdio.h>
#include <stdlib.h>
#define TYPE_PLAYER 1
#define WEAPLOSS_TYPE_CHANGE 3
typedef struct s_model {int id;} s_model;
typedef struct {int type,weaploss[2],*weapon,numweapons;} s_data;
typedef struct {s_data modeldata;float playerindex;s_model *defaultmodel;} entity;
struct {int weapnum;} player[4];struct {int setweap;} lv,*level=&lv;
int selected,sync_value,unsafe;
void set_model_ex(entity *e,char *name,int index,s_model *model,int sync){selected=model?model->id:index;sync_value=sync;if(selected<0)unsafe=1;}
'''+function+'\nint main(void){entity e;s_model def;int weapon[2],i;\nif(sizeof(int)!=4||sizeof(void*)!=4)return 2;def.id=3;lv.setweap=5;\n'
    for i,r in enumerate(rows):
        w=r['weapon'];c+='for(i=0;i<4;i++)player[i].weapnum=77;selected=sync_value=unsafe=0;\n'
        c+='e.modeldata.type='+str(r['type'])+';e.modeldata.weaploss[0]='+str(r['loss'])+';e.playerindex='+str(r['player'])+';e.defaultmodel=&def;\n'
        c+='e.modeldata.weapon='+('NULL' if w is None else 'weapon')+';e.modeldata.numweapons='+str(len(w or []))+';\n'
        for j,v in enumerate(w or []):c+='weapon['+str(j)+']='+str(v)+';'
        c+='set_weapon(&e,'+('-2147483647-1' if r['number']==-2147483648 else str(r['number']))+','+str(r['anim_flag'])+');printf("WEAPON|'+str(i)+'|%d|%d|%d|%d|%d|%d|%d\\n",selected,sync_value,unsafe,player[0].weapnum,player[1].weapnum,player[2].weapnum,player[3].weapnum);\n'
    c+='return 0;}\n';(folder/'weapon_selection.c').write_text(c)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    p=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','weapon_selection.c','-fe=weapon_selection_authority.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise ValueError('WEAPON_SELECTION_AUTHORITY_BUILD')
    out=subprocess.check_output([str((folder/'weapon_selection_authority.exe').resolve())],cwd=folder,text=True);results=[]
    for line in out.splitlines():
        if not line.startswith('WEAPON|'):continue
        parts=line.split('|');i=int(parts[1]);actual=list(map(int,parts[2:]));e=expected(rows[i]);wanted=[e['model'],e['sync'],int(e['unsafe']),*e['players']]
        results.append(dict(case=rows[i],actual=actual,expected=e,passed=actual==wanted))
    report=dict(schema='BYOR_4086_WEAPON_SELECTION_AUTHORITY_V1',status='PASS' if len(results)==len(rows) and all(r['passed'] for r in results) else 'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode('latin1')).hexdigest(),cases=len(rows),source_undefined_rejections=sum(r['expected']['unsafe'] for r in results),results=results,model_transition_instrumented=True,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=run(a.engine,a.output.resolve());print(json.dumps({k:r[k] for k in ('status','cases','source_undefined_rejections','function_sha256')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
