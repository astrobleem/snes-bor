"""Native uppercut/runattack entry gates, current cache and full32 running."""
import argparse, hashlib, json
from pathlib import Path
from m4_ai_owner_native import LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--jump-authority',type=Path)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 au=json.loads(a.authority.read_text());assert au['status']=='PASS'
 base=dict(time=48,nextthink=48,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=0x12340001,animation=5,spawn=3,respawn=4,animating=1,exists=1,bad='',mutation=0)
 rows=[];seen=set()
 for c in au['inputs']:
  key=tuple(c[k]for k in ('selector','animation','running'))
  if key in seen:continue
  seen.add(key)
  for model in range(16):rows.append(dict(base,**c,model=model,slot=(0,1,63,127)[len(rows)%4],fault=c['requires_target_service']))
 if a.jump_authority:
  jump=json.loads(a.jump_authority.read_text());assert jump['status']=='PASS';seen=set()
  for c in jump['inputs']:
   key=(c['first'],c['second'])
   if key in seen:continue
   seen.add(key)
   for model in range(16):rows.append(dict(base,selector=6,running=0,first=c['first'],second=c['second'],model=model,slot=(0,1,63,127)[len(rows)%4],fault=c['requires_target_service']))
 for bad in ('ready','busy','commonready','commonphase','commonslot','normalready','normalphase','normalslot','world','pool','side','count','slot','tick','phase','state','pending','time','self_lease','self_active','self_fault','self_pointer','life','freeze','cache','cache_models','cache_max','cache_bytes','spawn_id','respawn_id','token','model'):
  rows.append(dict(rows[0],bad=bad,fault=1))
 lua=LUA.replace("set('SourceAI4086_State',0)","set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)")
 setup="""
 put(side,c.model);cache=0x43c000+c.model*256;put(cache+24,c.animation);put(cache+76,c.animation);put(0x42f404+s*24,c.running,4)
 put(cache+28,c.first or 0);put(cache+30,c.second or 0)
 set('SourceAttackEntry4086_Ready',0xb5ed);set('SourceAttackEntry4086_Status',0)
 set('SourceNormalAttack4086_Ready',0xb5eb);set('SourceNormalAttack4086_State',c.selector);set('SourceNormalAttack4086_Slot',s);set('SourceNormalAttack4086_Response',55,4)
 set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',s)
 local extra={ready={'SourceAttackEntry4086_Ready',0},busy={'SourceAttackEntry4086_Status',2},commonready={'SourceCommonThink4086_Ready',0},commonphase={'SourceCommonThink4086_State',6},commonslot={'SourceCommonThink4086_Slot',(s+1)%128},normalready={'SourceNormalAttack4086_Ready',0},normalphase={'SourceNormalAttack4086_State',3},normalslot={'SourceNormalAttack4086_Slot',(s+1)%128}}
 if extra[c.bad]then local f=extra[c.bad];set(f[1],f[2])end
 for j=0,11 do put(sy.SourceRandom4086_Ready+j,0xa5,1)end
 for j=0,17 do put(sy.SourceCRandom4086_Ready+j,0x5a,1)end
"""
 lua=lua.replace(' local faults=',setup+' local faults=')
 lua=lua.replace("ready={'SourceAI4086_Ready',0},busy={'SourceAI4086_State',1},",'')
 lua=lua.replace("end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)"," for j=0,11 do before[sy.SourceRandom4086_Ready+j]=0xa5 end\n for j=0,17 do before[sy.SourceCRandom4086_Ready+j]=0x5a end\nend,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)",1)
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=');end=lua.index('emu.addMemoryCallback(function()',start+30);lua=lua[:start]+lua[end:]
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local s=c.slot;local e=c.expected')
 lua=lua[:start]+r'''
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('ATTACKENTRY|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceAttackEntry4086_Status)..'|'..dw(sy.SourceNormalAttack4086_Response))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
'''
 r=Reporter('M4-ATTACK-ENTRY',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceAttackEntry4086_Execute','SourceAttackEntry4086_Ready',0xb5ed,[],lua,r,batch_size=2)
 results=[list(map(int,l.split('ATTACKENTRY|',1)[1].split('|')))for l in log.splitlines()if 'ATTACKENTRY|'in l];wanted=[[i,0,0,3 if c['fault']else 2,55 if c['fault']else 0]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('source early false gates; full32 running and all16 mutable model caches; target paths explicit fault; owners/CPU/siblings/both RNG streams',len(results)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_ATTACK_ENTRY_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),target_services_bound=False,grounded_attack_integrated=False,motu_gameplay_proven=False,no_color_reduction=True)
 if a.jump_authority:report['jump_authority_sha256']=hashlib.sha256(a.jump_authority.read_bytes()).hexdigest()
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
