"""Pinned unchanged checkdamagedrop with exact binary32 counter observation."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT,GAME_SPEED
from script_nested_authority import extract
from compiler import Source
from source_combat_drop_requirements import derive


def fb(v):return struct.unpack('<I',struct.pack('<f',v))[0]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);req=derive(Source(a.source))
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');body=extract(raw,'checkdamagedrop')
    counts=sorted({0,-1,-2**24}|{-2**e+d for e in range(1,24)for d in (-1,0,1)})
    rows=[dict(count=c,attack_drop=ad,ktime=kt,drop=drop,now=now)for c,ad,kt,drop,now in itertools.product(counts,(0,1),(0,47,48,49),(-1,0,1),(48,0xffffff80,0xffffffff))]
    pre='''#include <stdio.h>
#include <string.h>
#define GAME_SPEED 200
struct {struct {int animal;float knockdowncount;struct{int max,current;}guardpoints;}modeldata;int drop;float knockdowncount;unsigned knockdowntime;struct{float knockdown;}defense[20];}victim,*self=&victim;
typedef struct {int attack_drop,attack_type,no_pain;}s_attack;
unsigned time;
'''
    main='''
int main(void){int count,ad,drop;unsigned kt,now,bits;s_attack attack;while(scanf("%d %d %u %d %u",&count,&ad,&kt,&drop,&now)==5){memset(&victim,0,sizeof(victim));memset(&attack,0,sizeof(attack));victim.knockdowncount=count;victim.knockdowntime=kt;victim.drop=drop;victim.defense[0].knockdown=1;attack.attack_drop=ad;time=now;checkdamagedrop(&attack);memcpy(&bits,&victim.knockdowncount,4);printf("%u %u %d\\n",bits,victim.knockdowntime,victim.drop);}return 0;}
'''
    (a.output/'drop.c').write_text(pre+body+main,encoding='latin1');env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');q=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','drop.c','-fe=drop.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(q.stdout+q.stderr)
    if q.returncode:raise ValueError('DAMAGE_DROP_AUTHORITY_BUILD:'+q.stdout+q.stderr)
    q=subprocess.run([str(a.output/'drop.exe')],input=''.join(' '.join(str(r[k])for k in ('count','attack_drop','ktime','drop','now'))+'\n'for r in rows),capture_output=True,text=True);actual=[list(map(int,l.split()))for l in q.stdout.splitlines()];expected=[]
    for r in rows:
        count=r['count'];ktime=r['ktime'];drop=r['drop']
        if not drop:
            if ktime and ktime<r['now']:count=0
            count=max(-2**24,count-r['attack_drop']);ktime=(r['now']+GAME_SPEED)&0xffffffff;drop=int(count<0)
        expected.append([fb(count),ktime,drop])
    failures=[dict(index=i,input=r,actual=actual[i]if i<len(actual)else None,expected=expected[i])for i,r in enumerate(rows)if i>=len(actual)or actual[i]!=expected[i]]
    report=dict(schema='BYOR_COMBAT_DROP_AUTHORITY_V1',status='PASS'if q.returncode==0 and actual==expected else'FAIL',cases=len(rows),observed_cases=len(actual),engine_commit=ENGINE_COMMIT,source_function_unmodified=True,source_function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),binary32_counter_observed=True,requirements=req,counter_values=counts,failures=failures,output_sha256=hashlib.sha256(q.stdout.encode()).hexdigest(),full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'exact counter/drop/deadline cases;',len(failures),'mismatches');print(json.dumps(failures[:2]))
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
