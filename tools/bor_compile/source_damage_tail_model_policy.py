"""Pinned loader authority for common_takedamage's remaining model policy."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_model_core_4086 import integer
FIELDS=('falldie','escapehits','nopain','weaploss')


def load(rows):
    d=dict(falldie=0,escapehits=0,nopain=0,weaploss_type=0,weaploss_model=-1)
    for row in rows:
        n,v=row['directive'],row['values']
        if n=='subclass':raise ValueError('DAMAGE_TAIL_SUBCLASS_REQUIRED')
        if n in ('falldie','death'):d['falldie']=integer(v)
        elif n in ('escapehits','nopain'):d[n]=integer(v)
        elif n=='weaploss':d.update(weaploss_type=integer(v),weaploss_model=integer(v,1))
    return d


def authority():
    raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');header=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
    calloc='s_model *newchar = calloc(1, sizeof(*newchar));'
    if calloc not in raw:raise ValueError('DAMAGE_TAIL_MODEL_CALLOC_AUTHORITY')
    defaults='\n'.join(re.search(r'^    newchar->weaploss\['+str(i)+r'\].*?;',raw,re.M)[0]for i in (0,1))
    blocks=[]
    for n in FIELDS:
        a=re.search('case CMD_MODEL_'+n.upper()+r'\s*:',raw).start();b=raw.index('break;',a)+6;blocks.append(raw[a:b])
    i=header.index('WEAPLOSS_TYPE_ANY');a=header.rfind('typedef enum',0,i);enum=header[a:header.index(';',i)+1]
    helpers='\n'.join(extract(raw,n)for n in ('isNumeric','getValidInt'))
    return dict(calloc=calloc,defaults=defaults,loader_blocks=blocks,enum=enum,helpers=helpers)


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};st=discover(source,docs);a=authority();models=[]
    for i,m in enumerate(st['models']):
        d=docs[key(m['source_path'])];models.append(dict(id=i,identity=m['declaration'],source_sha256=d['sha256'],fields=load(d['directives']),declarations=[r for r in d['directives']if r['directive']in (*FIELDS,'death')]))
    return dict(schema='BYOR_COMMON_DAMAGE_TAIL_MODEL_POLICY_V1',engine_commit=ENGINE_COMMIT,models=models,source_authority_sha256={k:hashlib.sha256(('\n'.join(v)if isinstance(v,list)else v).encode('latin1')).hexdigest()for k,v in a.items()},model_policy_mutators_admitted=False,native_tail_bound=False,full_common_takedamage_bound=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);req=derive(Source(a.source));auth=authority();cases=[[]]
    names=['falldie','death','escapehits','nopain','weaploss']
    for n in names:
        for v in ('','-3','-1','0','1','2','3','65536','1.5','bad'):
            for w in (None,'','-1','7'):cases.append([dict(directive=n,values=[v]+([]if w is None else[w]))])
    cases.extend(m['declarations']for m in req['models'])
    snippets=[]
    for i,rows in enumerate(cases):
        c='memset(newchar,0,sizeof(*newchar));'+auth['defaults']+'\n'
        for row in rows:
            v=row['values'];c+='arglist.count='+str(len(v)+1)+';arglist.args[1]='+json.dumps(v[0]if v else'')+';arglist.args[2]='+json.dumps(v[1]if len(v)>1 else'')+';switch('+str(names.index(row['directive']))+'){'+ '\n'.join(auth['loader_blocks'])+'}\n'
        c+='printf("TAIL|'+str(i)+'|%d,%d,%d,%d,%d\\n",newchar->falldie,newchar->escapehits,newchar->nopain,newchar->weaploss[0],newchar->weaploss[1]);\n';snippets.append(c)
    defines='\n'.join('#define CMD_MODEL_'+n.upper()+' '+str(i)for i,n in enumerate(names))
    c='''#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
'''+auth['enum']+'\n'+defines+'''
#define GET_ARG(z) (arglist.count > z ? arglist.args[z] : "")
#define GET_INT_ARG(z) getValidInt(GET_ARG(z), filename, command)
typedef struct {int falldie,escapehits,nopain,weaploss[2];}Model;
struct{int count;char*args[3];}arglist;char*filename="private",*command="tail";
'''+auth['helpers']+'\nint main(void){Model model,*newchar=&model;\n'+'\n'.join(snippets)+'return 0;}\n'
    (a.output/'authority.c').write_text(c);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');r=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','authority.c','-fe=authority.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(r.stdout+r.stderr)
    if r.returncode:raise ValueError('DAMAGE_TAIL_LOADER_C_BUILD')
    log=subprocess.check_output([str(a.output/'authority.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split('|')[2].split(',')))for l in log.splitlines()if l.startswith('TAIL|')];expected=[list(load(rows).values())for rows in cases]
    report=dict(schema='BYOR_COMMON_DAMAGE_TAIL_LOADER_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',cases=len(cases),inputs=cases,actual=actual,expected=expected,requirements=req,loader_blocks_unmodified=True,integer_helpers_unmodified=True,zero_initialization_matches_pinned_calloc=True,native_tail_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(cases),'loader/default cases',len(req['models']),'source models')
    if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
