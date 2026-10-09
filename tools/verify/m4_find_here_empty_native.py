"""Actual canonical type/exists scan for the empty find_ent_here candidate set."""
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from actor_s5_entity_fixture import symbols
from source_find_here_empty_native import emit
from _source_leaf_fixture import run_fixture
from _harness import Reporter
W=0x7fa000


def authority(rows,folder):
    """Keep the complete pinned search function unchanged in a 32-bit C shim."""
    import os,subprocess
    from dialect_4086 import ENGINE_COMMIT
    from script_nested_authority import extract
    raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    function=extract(raw,'find_ent_here')
    cases=[c for c in rows if not c['bad']]
    source='''#include <stdio.h>
#include <string.h>
#include <math.h>
typedef struct entity {int exists,animpos;struct {int type;float grabdistance;}modeldata;
struct {float x,z;}position;struct {int vulnerable[1];}*animation;} entity;
entity storage[128],*ent_list[128],*self;int ent_max,geometry_calls,test_calls;
float difference(float a,float b){geometry_calls++;return (float)fabs(a-b);}
#define diff(a,b) difference(a,b)
int predicate(entity*a,entity*b){test_calls++;return 1;}
'''+function+'''
struct fixture{int count,exclude;unsigned mask;int candidate,alive,expected_empty;} fixtures[]={
'''
    source+=',\n'.join('{'+','.join(map(str,(c['count'],c['exclude'],str(c['mask'])+'u',c['candidate'],c['alive'],int(c['status']==2))))+'}' for c in cases)
    source+='''};
int main(void){int n,i;struct {int vulnerable[1];} anim={{1}};entity *result,*exclude;
if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
for(n=0;n<sizeof(fixtures)/sizeof(fixtures[0]);n++){
memset(storage,0,sizeof(storage));ent_max=fixtures[n].count;self=&storage[0];
for(i=0;i<128;i++){ent_list[i]=&storage[i];storage[i].exists=1;
storage[i].modeldata.type=i%3==0?1:i%3==1?2:0;storage[i].modeldata.grabdistance=60;
storage[i].position.x=10000;storage[i].animation=(void*)&anim;}
if(fixtures[n].candidate>=0){i=fixtures[n].candidate;storage[i].modeldata.type=fixtures[n].mask;storage[i].exists=fixtures[n].alive;}
exclude=fixtures[n].exclude==65535?NULL:&storage[fixtures[n].exclude];geometry_calls=test_calls=0;
result=find_ent_here(exclude,0,0,fixtures[n].mask,predicate);
if(result||test_calls||((geometry_calls==0)!=fixtures[n].expected_empty))return 3;
printf("EMPTYAUTH|%d|%d\\n",n,geometry_calls);
}return 0;}
'''
    (folder/'authority.c').write_text(source)
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','authority.c','-fe=authority.exe'],cwd=folder,
        env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True)
    (folder/'authority-build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('FIND_HERE_EMPTY_AUTHORITY_BUILD')
    result=subprocess.run([str(folder/'authority.exe')],cwd=folder,capture_output=True,text=True)
    observed=result.stdout.splitlines()
    report=dict(status='PASS'if result.returncode==0 and len(observed)==len(cases)else'FAIL',cases=len(cases),engine_commit=ENGINE_COMMIT,
        function_sha256=hashlib.sha256(function.encode('latin1')).hexdigest(),unchanged_pinned_find_ent_here=True,
        geometry_and_predicate_not_called_for_empty_type_candidate_set=True)
    (folder/'authority-report.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['status']!='PASS':raise ValueError('FIND_HERE_EMPTY_AUTHORITY_MISMATCH')
    return report
ASM='''
FindHereProbe:
.a16
.i16
 php
 sed
 jsl SourceFindHereEmpty_Execute
FindHereProbe_Return:
 nop
 bcs FindHereProbe_Bad
 plp
 clc
 rtl
FindHereProbe_Bad:
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local start=0;local fail=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];fail=0;before={}
 for j=0,23 do emu.write(W+j,0,mt)end
 put(W,0xb67d);put(W+4,c.exclude);put(W+6,c.mask,4);put(W+16,0xdeadbeef,4)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,c.count)
 put(sy.SourceModelEntityCopy4086_Ready,0xb4eb);put(sy.SourceModelEntityCopy4086_Entities,c.count)
 for i=0,127 do
  for j=0,79 do emu.write(0x414000+80*i+j,(j+i)&255,mt)end
  for j=0,95 do emu.write(0x40c000+96*i+j,(j+3*i)&255,mt)end
  put(0x414004+80*i,1,4);put(0x40c048+96*i,(i%3==0)and 1 or(i%3==1)and 2 or 0,4)
 end
 if c.candidate>=0 then put(0x40c048+96*c.candidate,c.mask,4);put(0x414004+80*c.candidate,c.alive,4)end
 if c.bad=='ready'then put(W,0)elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='pool'then put(sy.VmSourceWorld_PoolBase,0x4002)elseif c.bad=='count_zero'then put(sy.VmSourceWorld_Count,0)
 elseif c.bad=='count_large'then put(sy.VmSourceWorld_Count,129)elseif c.bad=='model_owner'then put(sy.SourceModelEntityCopy4086_Ready,0)
 elseif c.bad=='model_count'then put(sy.SourceModelEntityCopy4086_Entities,c.count-1)elseif c.bad=='exclude'then put(W+4,c.count)end
 for _,p in ipairs({{0x414000,10240},{0x40c000,12288}})do for i=0,p[2]-1 do before[p[1]+i]=emu.read(p[1]+i,mt)end end
 put(EXPECTFAULT,c.status~=2 and 1 or 0)
 local st=emu.getState();start=st.masterClock;cpu={};for _,k in ipairs({'a','x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if emu.getState()['cpu.ps']&8==0 then fail=fail+1 end end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();for _,k in ipairs({'a','x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then fail=fail+1 end end
 if(cpu.ps&254)~=(st['cpu.ps']&254)then fail=fail+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];for a,v in pairs(before)do if emu.read(a,mt)~=v then fail=fail+1 end end
 if word(W+2)~=c.status or word(W+16)~=0 or word(W+18)~=0 then fail=fail+1 end
 emu.log('FINDHEREEMPTY|'..word(INDEX)..'|'..fail..'|'..word(W+2)..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();rows=[]
    def row(**kw):
        return dict(dict(count=128,exclude=0,mask=4,candidate=-1,alive=1,bad='',status=2),**kw)
    for count in range(1,129):rows.append(row(count=count,exclude=count-1))
    for mask in (4,8,16,32,64,128,256,512,1024,0x80000000,0xffffffff):
        for candidate in (0,63,127):
            for alive in (0,1,65536):
                for excluded in (False,True):
                    exclude=candidate if excluded else 65535
                    other_matches=bool(mask&3)
                    requires=other_matches or bool(alive and not excluded)
                    rows.append(row(mask=mask,candidate=candidate,alive=alive,exclude=exclude,status=3 if requires else 2))
    guards=('ready','world','pool','count_zero','count_large','model_owner','model_count','exclude')
    rows.extend(row(bad=b,status=4)for b in guards)
    sy=symbols(Path('src/main.sym'));folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    reporter=Reporter('M4-FIND-HERE-EMPTY-NATIVE',kind='GATE');(folder/'report.json').write_text('{"status":"RUNNING"}\n')
    proof=authority(rows,folder);reporter.check('unchanged pinned find_ent_here short circuit authority',proof['status']=='PASS')
    raw,log=run_fixture(a.rom,folder,rows,'FindHereProbe','SourceAnimationInit4086_Ready',0xb4ec,[],re.sub(r'\bW\b',str(W),LUA),reporter,
        append=ASM+emit(W,sy),probes=dict(RETURN='FindHereProbe_Return'),batch_size=4,frame_limit=1000,link_pcm=False)
    observed=[list(map(int,line.split('FINDHEREEMPTY|',1)[1].strip().split('|')))for line in log.splitlines()if 'FINDHEREEMPTY|'in line]
    errors=[r for r in observed if r[1]]
    reporter.check('actual live/excluded/type filtering, explicit candidate-owner fault, exact actor and CPU retention',len(observed)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_FIND_HERE_EMPTY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),guards=len(guards),observed=len(observed),errors=errors[:8],
        rom_sha256=hashlib.sha256(raw).hexdigest(),authority=proof,peak_master_clocks=max((r[3]for r in observed),default=0),live_canonical_type_scan=True,full_find_ent_here_bound=False,
        geometry_vulnerability_predicate_not_needed_when_candidate_set_empty=True,matching_type_candidate_rejects=True,production_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
