"""Pinned non-self common/player callbacks and scalar services, traced effects."""
import argparse
import hashlib
import itertools
import json
import os
import re
import struct
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_landing_callback_authority import PREAMBLE
from source_combat_damage_4086 import run
from compiler import Source
from source_hit_block_requirements import derive

FLOAT_FIELDS=('dropx','dropy','dropz')


def encoded(row,name):
    return struct.unpack('<i',struct.pack('<f',row[name]))[0] if name in FLOAT_FIELDS else row[name]


def cases():
    base=dict(callback=0,health=100,force=7,dead=0,bomb=0,drop=0,count=0,ktime=0,model_count=0,
              landing=0,direction=0,other_direction=1,x=0,other_x=1,y=0,lifespan=0,attack_type=0,
              attack_drop=0,no_pain=0,no_kill=0,guard=0,animal=0,frozen=0,noflip=0,nopain=0,
              force_direction=0,weaploss=0,other_type=1,other_grabbing=0,escapehits=1,falldie=0,
              valid_fall=1,attack_landing=0,invincible=0,cheat=0,nohurt=0,diesound=-1,
              freeze=0,freezetime=600,forcemap=0,frozen_map=0,previous_freezetime=0,maptime=0,
              nodrop=0,base=0,blast=0,rise=0,riseattack=0,dropx=3.,dropy=2.,dropz=0.)
    rows=[]
    for vals in itertools.product(range(2),(1,100),(7,150),range(2),range(2),range(4),(-2,-1,0,1,2),range(2)):
        rows.append(dict(base,**dict(zip(('callback','health','force','attack_drop','frozen','weaploss','force_direction','guard'),vals))))
    for name,values in dict(dead=(1,-1),bomb=(1,2,3),drop=(-1,1),count=(-3,1,3),ktime=(47,48,49),model_count=(-1,3),
                            landing=(-1,7),direction=(-3,1,2),other_direction=(-3,0,2),x=(-1,1,2),y=(-251,-250,-249),
                            lifespan=(-1,),attack_type=(1,5,6,7,16,19),no_pain=(-1,1),no_kill=(1,),animal=(1,),noflip=(1,),nopain=(1,),
                            force_direction=(3,4,-3),other_type=(0,2,3),other_grabbing=(1,),escapehits=(0,),falldie=(1,),
                            valid_fall=(0,),attack_landing=(7,),invincible=(1,2,3),cheat=(1,),nohurt=(1,),diesound=(0,7),force=(-10,0,25,30),
                            freeze=(1,),forcemap=(-1,1,3),frozen_map=(-1,3),previous_freezetime=(123,),nodrop=(-1,1,2),blast=(1,),rise=(7,),riseattack=(8,)).items():
        for value,callback,drop,health in itertools.product(values,range(2),range(2),(1,100)):
            row=dict(base,callback=callback,attack_drop=drop,health=health);row[name]=value;rows.append(row)
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);p.add_argument('--source',required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    header=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
    for fragment in ('DIRECTION_ADJUST_OPPOSITE  = -1','DIRECTION_ADJUST_RIGHT     = 2','DIRECTION_ADJUST_LEFT      = -2'):
        if fragment not in header:raise ValueError('COMBAT_DIRECTION_ENUM_AUTHORITY')
    names=('diff','inair','set_opponent','checkgrab','checkdamageflip','checkdamagedrop','checkdamageeffects','checkmpadd','checkhitscore','checkdamage','checkdeath','common_takedamage','player_takedamage','execute_takedamage_script','execute_ondeath_script')
    bodies={n:extract(raw,n)for n in names};pre=PREAMBLE
    script_raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openborscript.c']).decode('latin1')
    bodies={'Script_IsInitialized':extract(script_raw,'Script_IsInitialized'),**bodies}
    macro=re.search(r'^#define unfrozen\(e\).*?(?=\n\s*\n)',header,re.M|re.S).group(0)
    pre='\n'.join(l for l in pre.splitlines()if not l.startswith(('void checkdamageeffects(','void execute_takedamage_script(','void execute_ondeath_script(')))+'\n'
    pre=pre.replace('typedef struct entity entity;',r'''
#define VOID void
#define LONG long
#define VT_PTR 2
#define VT_INTEGER 1
typedef struct {int initialized;} Script;
typedef struct {void *ptrVal;long lVal;} ScriptVariant;
typedef struct {Script *takedamage_script,*ondeath_script;} ScriptSet;
Script damage_script,death_script;ScriptSet script_set={&damage_script,&death_script};
typedef struct {int rise,riseattack;} Stay;
typedef struct entity entity;
''')
    pre=pre.replace('typedef struct {int attack_force,','typedef struct {int freeze,maptime,freezetime,forcemap,blast,steal,seal,sealtime,dot,dot_index,dot_time,dot_force,dot_rate;Stay staydown;int attack_force,')
    pre=pre.replace('typedef struct {int type,health,','typedef struct {int nodrop;struct{int frozen;}maps;int type,health,')
    pre=pre.replace('struct entity {Model modeldata;','struct entity {ScriptSet *scripts;float base;int projectile,map,colourmap,seal;unsigned freezetime,maptime,sealtime;Stay staydown;entity *dot_owner[4];int dot[4],dot_force[4],dot_rate[4],dot_atk[4];unsigned dot_time[4];Model modeldata;')
    pre=pre.replace('#define DIRECTION_ADJUST_OPPOSITE 2','#define DIRECTION_ADJUST_OPPOSITE -1').replace('#define DIRECTION_ADJUST_RIGHT 3','#define DIRECTION_ADJUST_RIGHT 2').replace('#define DIRECTION_ADJUST_LEFT 4','#define DIRECTION_ADJUST_LEFT -2')
    pre=pre.replace('entity *opponent,*grabbing,*item;','entity *opponent,*grabbing,*item,*owner;')
    replace=dict(
        set_opponent='void set_opponent(entity*,entity*);',
        ent_unlink='void ent_unlink(entity *e){event(10);}',
        set_pain='void set_pain(entity *e,int t,int r){event(11);}',
        toss='void toss(entity *e,float f){e->velocity.y=f;event(12);}',
        set_fall='int valid_fall;int set_fall(entity *e,int t,int r,entity *o,int f,int d,int b,int g,int j,int p){event(13);return valid_fall;}',
        set_death='void set_death(entity *e,int t,int r){event(14);}',
        kill='void kill(entity *e){event(15);}',
        player_die='void player_die(void){event(16);}')
    for n,line in replace.items():
        old=next(l for l in pre.splitlines()if l.startswith(('void '+n+'(','int '+n+'(')))
        pre=pre.replace(old,line)
    pre+=r'''
void checkdamageeffects(s_attack*);
void execute_takedamage_script(entity*,entity*,int,int,int,int,int,int,int);
void execute_ondeath_script(entity*,entity*,int,int,int,int,int,int,int);
void ScriptVariant_Init(ScriptVariant *v){unexpected();}
void ScriptVariant_ChangeType(ScriptVariant *v,int t){unexpected();}
void Script_Set_Local_Variant(Script *s,char *n,ScriptVariant *v){unexpected();}
void Script_Execute(Script *s){unexpected();}
void ScriptVariant_Clear(ScriptVariant *v){unexpected();}
void ent_set_colourmap(entity *e,int n){event(17);e->colourmap=n;}
int model_get_colourmap(Model *m,int n){event(18);return n;}
float fvalue(int n){float f;memcpy(&f,&n,4);return f;}
unsigned fbits(float f){unsigned n;memcpy(&n,&f,4);return n;}
'''
    rows=cases();requirements=derive(Source(a.source))
    for attack in requirements['attacks']:
        if any(attack[n] for n in ('grab','steal','seal','dot')):raise ValueError('COMBAT_AUTHORED_ATTACK_OUTSIDE_PROOF_DOMAIN')
        for callback,frozen,health,guard in itertools.product(range(2),range(2),(1,100),range(2)):
            row=dict(rows[0],callback=callback,frozen=frozen,health=health,guard=guard)
            for n in ('force_direction','no_pain','no_kill','attack_type','attack_drop','freeze','freezetime','forcemap','maptime','blast'):row[n]=attack[n]
            row.update(force=attack['attack_force'],attack_landing=attack['damage_on_landing'],dropx=attack['dropv'][0],dropy=attack['dropv'][1],dropz=attack['dropv'][2],rise=attack['staydown'][0],riseattack=attack['staydown'][1]);rows.append(row)
    fields=list(rows[0]);code=pre+macro+'\n'+'\n'.join(bodies.values())
    code+='\nint main(void){int v['+str(len(fields))+'],ret,j;while(scanf("'+' '.join('%d'for _ in fields)+'",'+','.join('&v['+str(i)+']'for i in range(len(fields)))+')=='+str(len(fields))+'){\n'
    code+='memset(&victim,0,sizeof(victim));memset(&opponent,0,sizeof(opponent));memset(&lev,0,sizeof(lev));self=&victim;ne=score_total=0;victim.exists=opponent.exists=1;victim.idling=1;victim.escapecount=3;victim.modeldata.health=300;victim.modeldata.multiple=2;victim.modeldata.score=100;\n'
    mappings=dict(callback='victim.modeldata.type',health='victim.health',force='attack.attack_force',dead='victim.dead',bomb='victim.toexplode',drop='victim.drop',count='victim.knockdowncount',ktime='victim.knockdowntime',model_count='victim.modeldata.knockdowncount',landing='victim.damage_on_landing',direction='victim.direction',other_direction='opponent.direction',x='victim.position.x',other_x='opponent.position.x',y='victim.position.y',lifespan='victim.lifespancountdown',attack_type='attack.attack_type',attack_drop='attack.attack_drop',no_pain='attack.no_pain',no_kill='attack.no_kill',guard='victim.modeldata.guardpoints.max',animal='victim.modeldata.animal',frozen='victim.frozen',noflip='victim.modeldata.noflip',nopain='victim.modeldata.nopain',force_direction='attack.force_direction',weaploss='victim.modeldata.weaploss[0]',other_type='opponent.modeldata.type',other_grabbing='opponent.grabbing',escapehits='victim.modeldata.escapehits',falldie='victim.modeldata.falldie',valid_fall='valid_fall',attack_landing='attack.damage_on_landing',invincible='victim.invincible',cheat='healthcheat',nohurt='lev.nohurt',diesound='victim.modeldata.diesound')
    code=code.replace('int v['+str(len(fields))+'],ret,j;', 'int v['+str(len(fields))+'],ret,j;s_attack attack;')
    mappings.update(freeze='attack.freeze',freezetime='attack.freezetime',forcemap='attack.forcemap',frozen_map='victim.modeldata.maps.frozen',previous_freezetime='victim.freezetime',maptime='attack.maptime',nodrop='victim.modeldata.nodrop',base='victim.base',blast='attack.blast',rise='attack.staydown.rise',riseattack='attack.staydown.riseattack',dropx='attack.dropv.x',dropy='attack.dropv.y',dropz='attack.dropv.z')
    code+='memset(&attack,0,sizeof(attack));victim.scripts=&script_set;victim.map=7;victim.colourmap=9;victim.projectile=3;victim.staydown.rise=11;victim.staydown.riseattack=12;\n'
    for i,n in enumerate(fields):
        val=f'v[{i}]'
        if n=='callback':val=f'(v[{i}]?TYPE_PLAYER:TYPE_ENEMY)'
        if n=='other_grabbing':val=f'(v[{i}]?self:NULL)'
        if n in FLOAT_FIELDS:val=f'fvalue(v[{i}])'
        code+=mappings[n]+'='+val+';\n'
    code+='for(j=0;j<20;j++){victim.defense[j].factor=victim.defense[j].knockdown=opponent.offense_factors[j]=1;}\n'
    code+=f'ret=v[{fields.index("callback")}]?player_takedamage(&opponent,&attack):common_takedamage(&opponent,&attack);\n'
    expr=['ret','victim.health','victim.dead','victim.nograb','victim.idling','victim.drop','(int)victim.knockdowncount','victim.knockdowntime','victim.damagetype','victim.direction','victim.damage_on_landing','victim.escapecount','victim.takeaction==common_fall?1:victim.takeaction==common_pain?2:0','(int)victim.velocity.x','(int)victim.velocity.y','(int)victim.velocity.z','victim.opponent==&opponent?1:-1','opponent.opponent==&victim?0:-1','score_total']
    expr[13:16]=['fbits(victim.velocity.x)','fbits(victim.velocity.y)','fbits(victim.velocity.z)']
    expr+=['victim.frozen','victim.freezetime','victim.colourmap','victim.projectile','victim.staydown.rise','victim.staydown.riseattack','victim.maptime']
    code+='printf("'+' '.join('%u'if i in (13,14,15)else'%d'for i in range(len(expr)))+'|",'+','.join(expr)+');for(j=0;j<ne;j++)printf("%s%d",j?" ":"",events[j]);puts("");}return 0;}\n'
    (a.output/'combat.c').write_text(code,encoding='latin1');env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    q=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','combat.c','-fe=combat.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(q.stdout+q.stderr)
    if q.returncode:raise ValueError('COMBAT_C_BUILD:'+q.stdout+q.stderr)
    q=subprocess.run([str(a.output/'combat.exe')],input=''.join(' '.join(str(encoded(r,n))for n in fields)+'\n'for r in rows),capture_output=True,text=True)
    actual=[tuple(list(map(int,v.split()))for v in line.split('|'))for line in q.stdout.splitlines()];expected=[run(r)for r in rows]
    failures=[dict(index=i,input=rows[i],actual=x,expected=y)for i,(x,y)in enumerate(zip(actual,expected))if x!=y]
    report=dict(schema='BYOR_COMBAT_DAMAGE_AUTHORITY_V2',status='PASS'if q.returncode==0 and actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),observed_cases=len(actual),source_functions_unmodified=True,source_function_hashes={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},direction_enum_authority='pinned openbor.h: 0,1,-1,2,-2',actual_effects_body_and_empty_damage_scripts=True,authored_attacks=len(requirements['attacks']),instrumented_services=['colourmap','weapon','score','rumble','unlink','toss','fall/pain/death animation','kill/player_die'],proof_domain='non-self, no grab/steal/seal/dot, no boss/items, uniform unit factors, zero defense pain; colourmap service returns requested map identity',failures=failures,output_sha256=hashlib.sha256(q.stdout.encode()).hexdigest(),native_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'non-self combat callbacks;',len(failures),'mismatches');print(json.dumps(failures[:2],indent=2))
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
