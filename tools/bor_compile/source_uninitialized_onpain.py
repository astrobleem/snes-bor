"""Derive a closed uninitialized onpain capability from source declarations."""
import argparse,ast,hashlib,json,os,re,subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from script_ir_4086 import inspect
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs);models=[]
    for i,m in enumerate(structure['models']):
        d=docs[key(m['source_path'])];kinds=[]
        for row in d['directives']:
            kind=row['directive']
            if kind=='subclass':raise ValueError('ONPAIN_ABSENCE_SUBCLASS_REQUIRED')
            if kind.endswith('script')and kind not in ('animationscript','@script'):
                raise ValueError('ONPAIN_ABSENCE_SCRIPT_KIND_REQUIRED:'+kind)
            if kind in ('animationscript','@script'):kinds.append(kind)
        models.append(dict(id=i,identity=m['declaration'],source_sha256=d['sha256'],onpain_initialized=False,script_kinds=sorted(set(kinds))))
    ir=inspect(source);mutations=[]
    if ir['diagnostics']:raise ValueError('ONPAIN_ABSENCE_SCRIPT_FRONTEND')
    allowed={'NULL','changeentityproperty','checkwall','clearlocalvar','clearspawnentry','findtarget','getentityproperty','getlocalvar','killentity','openborconstant','performattack','playerkeys','projectile','rand','setlocalvar','setspawnentry','spawn','tossentity','updateframe'}
    if set(ir['engine_api_requirements'])-allowed:raise ValueError('ONPAIN_ABSENCE_API_CLOSURE_REQUIRED')
    property_capabilities={'velocity','animation','animpos','direction','aiflag','position','speed'}
    def walk(n):
        children={c['edge']:c['node']for c in n.get('children',[])}
        if n.get('kind')=='FuncCall'and children.get('name',{}).get('name')=='changeentityproperty':
            args=children.get('args',{}).get('children',[])
            if len(args)<2:raise ValueError('ONPAIN_ABSENCE_PROPERTY_ARITY')
            prop=args[1]['node']
            if prop.get('kind')!='Constant'or prop.get('type')!='string':raise ValueError('ONPAIN_ABSENCE_DYNAMIC_PROPERTY_REQUIRED')
            name=ast.literal_eval(prop['value'])
            if name not in property_capabilities:raise ValueError('ONPAIN_ABSENCE_PROPERTY_CLOSURE_REQUIRED:'+name)
            mutations.append(dict(property=name,line=n.get('source_line')))
        for c in n.get('children',[]):walk(c['node'])
    for lib in ir['libraries'].values():
        for f in lib['functions'].values():walk(f['ast'])
    for block in ir['inline_blocks']:walk(block['ast'])
    return dict(schema='BYOR_UNINITIALIZED_ONPAIN_REQUIREMENTS_V1',engine_commit=ENGINE_COMMIT,models=models,engine_API_requirements=ir['engine_api_requirements'],literal_property_mutations=mutations,source_script_sha256={l['source_path']:l['asset_sha256']for l in ir['libraries'].values()},capability='UNINITIALIZED_ONPAIN',initialized_onpain_admitted=False,production_binding=False)


def emit(work,requirements,sy):
    if requirements['schema']!='BYOR_UNINITIALIZED_ONPAIN_REQUIREMENTS_V1'or any(m['onpain_initialized']for m in requirements['models']):raise ValueError('UNINITIALIZED_ONPAIN_NATIVE_REQUIREMENTS')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SetPainFinish_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='SetPainFinish_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp SetPainFinish_'+n+'\n'+l+':\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    label('Run');put(' php\n rep #$39\n phx\n phy')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6b5)
    put(f' lda.l {work}+2\n cmp #6');branch('beq','Validate');put(' cmp #7');branch('bne')
    label('Validate')
    for at,v in ((sy['SourceScriptClone4086_Ready'],0xb5c1),(sy['SourceAnimationInit4086_State'],2),(sy['SourceUpdateFrame4086_State'],2),(sy['SourceUpdateFrame4086_Pending'],0),(sy['SourceSelf4086_Active'],0)):
        require(at,v)
    for src,dst in ((sy['SourceAnimationInit4086_Slot'],work+4),(sy['SourceAnimationInit4086_Number'],work+14),(sy['SourceAnimationInit4086_Handle'],work+16)):
        put(f' lda.l {src}\n cmp.l {dst}');branch('bne')
    put(f' lda.l {work}+4\n cmp #128');branch('bcs');put(' asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n tax')
    put(' lda.l $40902E,x');branch('bne');put(' lda.l $40902C,x\n cmp #2');branch('bcs')
    # The admitted script-clone mask represents only animation script state.
    # All other kinds, including onpain, were proven uninitialized offline.
    put(f' lda #7\n sta.l {work}+2\n lda #1\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    req=derive(Source(a.source));engine=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');scripts=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openborscript.c']).decode('latin1');initialized=extract(scripts,'Script_IsInitialized');onpain=extract(engine,'execute_onpain_script')
    alloc=re.search(r'Script \*alloc_script\(\)\s*\{.*?\n\}',scripts,re.S)[0];assert 'calloc(1, sizeof(*pscript))'in alloc
    code='''#include <stdio.h>
#include <string.h>
#define LONG int
#define VOID void
#define VT_PTR 3
typedef struct {int initialized;}Script;
typedef struct {Script *onpain_script;}Scripts;
typedef struct {Scripts *scripts;}entity;
typedef struct {void *ptrVal;int lVal;}ScriptVariant;
int actions;
void ScriptVariant_Init(ScriptVariant*v){actions++;memset(v,0,sizeof(*v));}
void ScriptVariant_ChangeType(ScriptVariant*v,int t){actions++;}
void Script_Set_Local_Variant(Script*s,char*n,ScriptVariant*v){actions++;}
void Script_Execute(Script*s){actions++;}
void ScriptVariant_Clear(ScriptVariant*v){actions++;}
'''+initialized+'\n'+onpain+'''
int main(void){Script s;Scripts scripts;entity e;int init,type,reset;scripts.onpain_script=&s;e.scripts=&scripts;
for(init=0;init<2;init++)for(type=-1;type<=20;type++)for(reset=0;reset<2;reset++){
s.initialized=init;actions=0;execute_onpain_script(&e,type,reset);printf("ONPAIN|%d|%d|%d|%d\\n",init,type,reset,actions);}return 0;}
'''
    (a.output/'authority.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');p=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','authority.c','-fe=authority.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise ValueError('ONPAIN_AUTHORITY_BUILD')
    log=subprocess.check_output([str(a.output/'authority.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);rows=[list(map(int,l.split('|')[1:]))for l in log.splitlines()if l.startswith('ONPAIN|')];expected=[[i,t,r,10 if i else 0]for i in range(2)for t in range(-1,21)for r in range(2)]
    report=dict(schema='BYOR_UNINITIALIZED_ONPAIN_AUTHORITY_V1',status='PASS'if rows==expected else'FAIL',cases=len(rows),actual=rows,expected=expected,source_functions_unmodified=True,source_functions_sha256={n:hashlib.sha256(v.encode('latin1')).hexdigest()for n,v in [('Script_IsInitialized',initialized),('execute_onpain_script',onpain)]},source_zero_allocator_sha256=hashlib.sha256(alloc.encode('latin1')).hexdigest(),requirements=req,initialized_branch_instrumented=True,initialized_branch_native_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(req['models']),'uninitialized source models',len(rows),'literal authority cases')
    if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
