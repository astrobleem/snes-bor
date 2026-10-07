"""Native common_try_grab(NULL) early gates; target/grab bodies unbound."""
import argparse, hashlib, json
from pathlib import Path
from m4_ai_owner_native import LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','authority','random-authority','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 au=json.loads(a.authority.read_text());ra=json.loads(a.random_authority.read_text());assert au['status']==ra['status']=='PASS'
 seeds={}
 for c in ra['inputs']:seeds.setdefault(c['expected']&7,c)
 base=dict(time=48,nextthink=48,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=0x12340001,animation=5,spawn=3,respawn=4,animating=1,exists=1,bad='',mutation=0)
 rows=[];seen=set()
 for c in au['inputs']:
  key=tuple(c[k]for k in ('chance','throw','grab','idling'))
  if key in seen:continue
  seen.add(key);seed=seeds[c['chance']]
  rows.append(dict(base,**c,slot=(0,1,63,127)[len(rows)%4],calls=(0,65535,0xffffffff)[len(rows)%3],seed_before=seed['seed_before'],seed_after=seed['seed_after'],random_result=seed['expected'],fault=c['requires_find_service'],advance=1))
 for bad in ('ready','busy','commonready','commonphase','commonslot','normalready','normalphase','normalslot','world','pool','side','count','slot','tick','phase','state','pending','time','self_lease','self_active','self_fault','self_pointer','life','freeze','cache','cache_models','cache_max','cache_bytes','spawn_id','respawn_id','token','model','randready','randprofile','randbusy'):
  rows.append(dict(rows[0],bad=bad,fault=1,advance=0))
 lua=LUA.replace("set('SourceAI4086_State',0)","set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)")
 setup="""
 set('SourceTryGrab4086_Ready',0xb5ec);set('SourceTryGrab4086_Status',0)
 set('SourceNormalAttack4086_Ready',0xb5eb);set('SourceNormalAttack4086_State',1);set('SourceNormalAttack4086_Slot',s);set('SourceNormalAttack4086_Response',55,4)
 set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',s)
 set('SourceCRandom4086_Ready',0xb5ea);set('SourceCRandom4086_Profile',1);set('SourceCRandom4086_Busy',0);set('SourceCRandom4086_Result',55,4);set('SourceCRandom4086_SeedLo',c.seed_before,4);set('SourceCRandom4086_CallsLo',c.calls,4)
 put(flags,c.idling,4);put(cache+40,c.throw);put(cache+34,c.grab)
 local extra={ready={'SourceTryGrab4086_Ready',0},busy={'SourceTryGrab4086_Status',2},commonready={'SourceCommonThink4086_Ready',0},commonphase={'SourceCommonThink4086_State',6},commonslot={'SourceCommonThink4086_Slot',(s+1)%128},normalready={'SourceNormalAttack4086_Ready',0},normalphase={'SourceNormalAttack4086_State',2},normalslot={'SourceNormalAttack4086_Slot',(s+1)%128},randready={'SourceCRandom4086_Ready',0},randprofile={'SourceCRandom4086_Profile',2},randbusy={'SourceCRandom4086_Busy',1}}
 if extra[c.bad]then local f=extra[c.bad];set(f[1],f[2])end
 for j=0,11 do put(sy.SourceRandom4086_Ready+j,0xa5,1)end
"""
 lua=lua.replace(' local faults=',setup+' local faults=')
 # Dedicated lease overrides the inherited AI-ready fault entry.
 lua=lua.replace("ready={'SourceAI4086_Ready',0},busy={'SourceAI4086_State',1},",'')
 lua=lua.replace("end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)"," for j=0,11 do before[sy.SourceRandom4086_Ready+j]=0xa5 end\nend,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)",1)
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=')
 end=lua.index('emu.addMemoryCallback(function()',start+30)
 lua=lua[:start]+lua[end:]
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local s=c.slot;local e=c.expected')
 lua=lua[:start]+r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('TRYGRAB|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceTryGrab4086_Status)..'|'..dw(sy.SourceNormalAttack4086_Response)..'|'..dw(sy.SourceCRandom4086_SeedLo)..'|'..dw(sy.SourceCRandom4086_CallsLo)..'|'..dw(sy.SourceCRandom4086_Result))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
'''
 r=Reporter('M4-TRY-GRAB',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceTryGrab4086_Execute','SourceTryGrab4086_Ready',0xb5ec,[],lua,r,batch_size=2)
 results=[list(map(int,l.split('TRYGRAB|',1)[1].split('|')))for l in log.splitlines()if 'TRYGRAB|'in l]
 wanted=[[i,0,0,3 if c['fault']else 2,55 if c['fault']else 0,c['seed_after']if c['advance']else c['seed_before'],(c['calls']+c['advance'])&0xffffffff,c['random_result']if c['advance']else 55]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('mandatory single CRT call including absent animations/idling false; mutable cache/full32 flags; unbound find faults; owner/CPU/siblings/engine RNG',len(results)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_TRY_GRAB_NULL_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),random_profile=ra['profile'],target_and_grab_services_bound=False,grounded_attack_integrated=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
