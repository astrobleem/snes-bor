"""Compare selected cached fields with verbatim pinned loader authority."""
import argparse,hashlib,json,os,re,struct,subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_model_core_4086 import CACHED_FIELDS,FLOAT_FIELDS,TYPE_NAMES,PHYSICS,load,number
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def fixtures(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    discovery=discover(source,docs);ids={m['declaration'].lower():i for i,m in enumerate(discovery['models'])}
    jump=4
    for r in docs[key(discovery['models_path'])]['directives']:
        if r['directive']=='jumpheight':jump=number(r['values'])
    rows=[dict(identity=m['declaration'],rows=docs[key(m['source_path'])]['directives'],jumpheight=jump,ids=ids) for m in discovery['models']]
    def row(n,*v):return dict(directive=n,values=list(map(str,v)))
    for t in TYPE_NAMES:
        for prefix in ([],[row('type','player')],[row('subject_to_gravity',0),row('aimove','chase')]):
            for rise in (False,True):
                rows.append(dict(identity='synthetic-type',rows=prefix+[row('type',t)]+([row('anim','riseattack')] if rise else []),jumpheight=4.5,ids={'flash':7}))
    for n in ('speed','speedf'):
        for v in ('-0','0','-100','4.99999','5','300','301','1.17549435e-38','10.1234567'):
            rows.append(dict(identity='synthetic-speed',rows=[row(n,v)],jumpheight=4,ids={}))
    for n in PHYSICS+['no_adjust_base','health','mp','shadow','weapnum']:
        for v in (-2147483648,-2,-1,0,1,2147483647):
            rows.append(dict(identity='synthetic-int',rows=[row(n,v)],jumpheight=4,ids={}))
    for n in ('hostile','candamage','projectilehit'):
        for values in (['enemy','obstacle'],['player','npc','shot'],['-1'],['0'],['3','8'],['ground']):
            rows.append(dict(identity='synthetic-mask',rows=[row(n,*values)],jumpheight=4,ids={}))
    for n,v in [('running',['20','4.5','2','-1','1']),('score',['70','-2']),('risetime',['-1','200']),('aimove',['arrow','notargetidle']),('aimove',['avoid','ignoreholes']),('aiattack',['noattack']),('aiattack',['always'])]:
        rows.append(dict(identity='synthetic-command',rows=[row(n,*v),row(n,*v)],jumpheight=4,ids={}))
    for seq in ([row('iconpain','pain'),row('icon','main')],[row('icon','main'),row('iconpain','pain')],[row('dust','flash','none','missing')],[row('playshotno','flash')],[row('flash','none')]):
        rows.append(dict(identity='synthetic-binding',rows=seq,jumpheight=4,ids={'flash':7}))
    return rows


def run(engine,source,folder):
    folder.mkdir(parents=True,exist_ok=True)
    def git(path):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+path],cwd=engine).decode('latin1')
    raw=git('engine/openbor.c');header=git('engine/openbor.h')
    enums='\n'.join(re.search(r'typedef enum\s*\{[^}]*\}\s*'+n+r'\s*;',header,re.S)[0] for n in ('e_entity_type','e_entity_type_sub','e_aimove_1','e_aimove_2','e_aiattack_1'))
    funcs='\n'.join(extract(raw,'lcmHandleCommand'+n) for n in ('Type','Hostile','Candamage','Projectilehit','Aimove','Aiattack'))
    mapping={n:n.upper() for n in ('health','mp','shadow','weapnum','score','risetime','speed','speedf','running','diesound','icon','iconpain','icondie','iconget','flash','bflash','knife','fireb','playshot','playshotw','playshotno','star','bomb','playbomb','dust')}
    mapping.update({n:n.upper() for n in PHYSICS+['no_adjust_base']})
    # Preserve shared case labels exactly as grouped in the pinned loader.
    groups=[]
    for block in re.findall(r'((?:            case CMD_MODEL_[^\n]*\n)+.*?                break;)',raw,re.S):
        tags=re.findall(r'case CMD_MODEL_(\w+):',block)
        if any(t in mapping.values() for t in tags):groups.append((tags,block))
    selected='\n'.join(b for _,b in groups)
    init=raw[raw.index('s_model *init_model('):raw.index('void update_model_loadflag(')]
    defaults=[]
    for line in init.splitlines():
        if re.match(r'\s*newchar->('+ '|'.join(re.escape(f) for f in CACHED_FIELDS)+r')\s*=',line):defaults.append(line)
    post=raw[raw.index('    if(newchar->risetime.rise == -1)',raw.index('s_model *load_cached_model(')):]
    post=post[:post.index('    if(newchar->jumpspeed < 0)')]
    fields=[f for f in CACHED_FIELDS if '.' not in f]
    declarations=';'.join(('float ' if f in FLOAT_FIELDS else 'int ')+f for f in fields)+';'
    c='''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GAME_SPEED 200
#define MAX_ATCHAIN 12
#define ANI_RISEATTACK 0
typedef struct {char *args[32];} ArgList;
#define GET_ARGP(i) (arglist->args[i])
#define GET_ARG(i) (arglist->args[i])
#define GET_INT_ARG(i) atoi(GET_ARG(i))
#define GET_FLOAT_ARG(i) ((float)atof(GET_ARG(i)))
'''+enums+'\ntypedef struct {'+declarations+'''int type,subtype,nopassiveblock,atchain[12],chainlength,bounce,offscreenkill,ground,score;
float antigravity;struct {int def,pain,get,die,usemap;} icon;struct {int fall_land,jump_land,jump_start;} dust;
struct {int rise,riseattack;} risetime;void *animation[1];} s_model;
float default_model_jumpheight;char *registry[16],*media[64];int registry_count,media_count,packfile,pixelformat;
void shutdown(int n,char *s,...){exit(3);}
int get_cached_model_index(char *s){int i;for(i=0;i<registry_count;i++)if(!stricmp(s,registry[i]))return i;return -1;}
int media_index(char *s){int i;for(i=0;i<media_count;i++)if(!strcmp(s,media[i]))return i;media[media_count]=s;return media_count++;}
int loadsprite(char *s,int a,int b,int f){return media_index(s);}
int sound_load_sample(char *s,int p,int n){return media_index(s);}
'''+funcs+'\nvoid initialize(s_model *newchar){\n'+ '\n'.join(defaults)+'\n}\nvoid finish(s_model *newchar){\n'+post+'}\n'
    tags=list(dict.fromkeys(t for ts,_ in groups for t in ts));c+='enum {'+','.join('CMD_MODEL_'+t+'='+str(i+1) for i,t in enumerate(tags))+'};\n'
    c+='void command(ArgList *arglist,s_model *newchar,int cmd){char *value,*shutdownmessage;switch(cmd){\n'+selected+'\n}lCleanup:;}\n'
    cases=fixtures(source);expected=[]
    c+='int main(void){s_model model,*newchar=&model;ArgList args,*arglist=&args;int aimoveset,aiattackset;unsigned bits;\nif(sizeof(int)!=4||sizeof(float)!=4||sizeof(void*)!=4)return 2;\n'
    for i,r in enumerate(cases):
        d,bindings=load(r['rows'],r['jumpheight'],r['ids']);media={}
        c+='memset(newchar,0,sizeof(model));registry_count=16;memset(registry,0,sizeof(registry));\n'
        # Empty names are valid strings for the registry stub, never NULL.
        for n in range(16):c+='registry['+str(n)+']='+json.dumps(next((k for k,v in r['ids'].items() if v==n),'__unused_'+str(n)))+';\n'
        c+='default_model_jumpheight='+str(r['jumpheight'])+';media_count=0;aimoveset=aiattackset=0;initialize(newchar);\n'
        for row in r['rows']:
            n,v=row['directive'],row['values'];active=n in mapping or n in ('type','hostile','candamage','projectilehit','aimove','aiattack')
            if n=='anim' and v and v[0].lower()=='riseattack':c+='newchar->animation[0]=newchar;\n'
            if not active:continue
            for j in range(32):c+='args.args['+str(j)+']='+json.dumps(v[j-1] if j and j<=len(v) else '')+';'
            c+='\n'
            if n in mapping:c+='command(arglist,newchar,CMD_MODEL_'+mapping[n]+');\n'
            else:
                tail=',"fixture"' if n=='type' else ',&aimoveset,"fixture"' if n=='aimove' else ',&aiattackset,"fixture"' if n=='aiattack' else ''
                c+='lcmHandleCommand'+dict(type='Type',hostile='Hostile',candamage='Candamage',projectilehit='Projectilehit',aimove='Aimove',aiattack='Aiattack')[n]+'(arglist,newchar'+tail+');\n'
            if n in ('icon','iconpain','icondie','iconget','diesound'):
                if v[0] not in media:media[v[0]]=len(media)
        c+='finish(newchar);printf("CORE|'+str(i)+'");\n'
        values=[]
        for f in CACHED_FIELDS+['type']:
            val=media[bindings[f]] if f in bindings else d[f]
            values.append(struct.unpack('<I',struct.pack('<f' if f in FLOAT_FIELDS else '<i',val))[0])
            c+='memcpy(&bits,&newchar->'+f+',4);printf("|%u",bits);\n'
        c+='printf("\\n");\n';expected.append(values)
    c+='return 0;}\n';(folder/'model_core.c').write_text(c)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    p=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','model_core.c','-fe=model_core_authority.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise ValueError('MODEL_CORE_AUTHORITY_BUILD')
    output=subprocess.check_output([str((folder/'model_core_authority.exe').resolve())],cwd=folder,text=True);results=[]
    for line in output.splitlines():
        if not line.startswith('CORE|'):continue
        parts=line.split('|');i=int(parts[1]);actual=list(map(int,parts[2:]));results.append(dict(case=i,identity=cases[i]['identity'],passed=actual==expected[i],mismatches=[dict(field=f,actual=a,expected=e) for f,a,e in zip(CACHED_FIELDS+['type'],actual,expected[i]) if a!=e]))
    authority=enums+funcs+selected+'\n'.join(defaults)+post
    report=dict(schema='BYOR_4086_MODEL_CORE_AUTHORITY_V1',status='PASS' if len(results)==len(cases) and all(r['passed'] for r in results) else 'FAIL',engine_commit=ENGINE_COMMIT,authority_sha256=hashlib.sha256(authority.encode('latin1')).hexdigest(),cases=len(cases),results=results,media_loader_instrumented=True,complete_model_constructor_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=run(a.engine,Source(a.source),a.output.resolve());print(json.dumps({k:r[k] for k in ('status','cases','authority_sha256')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
