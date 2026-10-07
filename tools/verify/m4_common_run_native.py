"""Real ordered common enemy predicates; no Lua service acknowledgements."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--limit',type=int);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 base=dict(time=48,nextthink=48,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=0x12340001,animation=5,spawn=3,respawn=4,animating=1,exists=1,mutation=0,bad='',dead=0,subtype=0,parent=0,link=0,grabbing=0,attacking=0,idling=3,aiattack=0,aimove=0,y=65536,base_y=0,rise=0,special=0,escape=0,fault=0,trace=list(range(1,9)),common=9)
 variations=[dict(name='air'),dict(name='dead',dead=1,trace=[]),dict(name='dead_high',dead=65536,trace=[]),dict(name='busy_link',link=1,trace=list(range(1,7))),dict(name='busy_idle',idling=0,trace=list(range(1,7))),dict(name='grab_no_link',grabbing=1,trace=list(range(1,5))),dict(name='grab_high_no_link',grabbing=65536,trace=list(range(1,5))),dict(name='attacking_grab',grabbing=1,attacking=65536),dict(name='follow_parent',subtype=10,parent=1,fault=1,trace=[1],common=1),dict(name='rise_initialized',rise=1,fault=1,trace=[1,2],common=2),dict(name='special_initialized',special=1,fault=1,trace=[1,2,3],common=3),dict(name='escape_initialized',escape=1,fault=1,trace=list(range(1,6)),common=5),dict(name='ground_move',y=0,fault=1,common=8),dict(name='ground_attack',y=0,time=50,nextthink=50,fault=1,trace=list(range(1,8)),common=7),dict(name='nomove_attack_disabled',y=0,time=50,nextthink=50,aiattack=1,aimove=2048),dict(name='attack_mask_high',y=0,time=50,nextthink=50,aiattack=65537,aimove=2048),dict(name='attack_style_combined',y=0,time=50,nextthink=50,aiattack=3,aimove=2048,fault=1,trace=list(range(1,8)),common=7),dict(name='arrow_priority',aimove=2304,fault=1,common=8)]
 rows=[dict(base,**v,slot=slot,model=slot%16)for v in variations for slot in (0,1,63,127)]
 rows.extend(dict(base,name='current_model_'+str(model),slot=(0,1,63,127)[model%4],model=model)for model in range(16))
 for bad in ('ready','repeat','world','pool','side','count','slot','tick','state','pending','time','self_lease','self_active','self_fault','self_pointer','life','freeze','cache','cache_models','cache_max','cache_bytes','spawn_id','respawn_id','token','model','commonready','readonlyready','relations','core','ytag','ytaghigh'):
  phase=1 if bad in ('readonlyready','relations')else 4 if bad=='core'else 8 if bad in ('ytag','ytaghigh')else 0
  rows.append(dict(base,name='guard_'+bad,slot=0,model=0,bad=bad,fault=1,trace=list(range(1,phase+1)),common=phase if phase else 0 if bad in ('ready','repeat')else 10))
 if a.limit is not None:rows=rows[:a.limit]
 for c in rows:c['expected']=[0,0,0,0,0,c['update_mark'],c['nextthink'],6,0,1,5,1]
 lua=LUA.replace("set('SourceAI4086_State',0)","set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)")
 lua=lua.replace(' local faults=',""" set('SourceCommonRun4086_Ready',0xb5e9);set('SourceCommonRun4086_State',0);set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',0);set('SourceCommonThink4086_Response',0,4);set('SourceAIReadonly4086_Ready',0xb5e8);set('SourceAIReadonly4086_Status',0);set('SourceRetirement4086_Ready',0xb4f8);set('SourceModelEntityCopy4086_Ready',0xb4eb)
 put(side,c.model);put(life+20,c.dead,4);put(life+48,c.subtype,4);put(flags,c.idling,4);put(v+8,2,4);put(v+12,c.y,4);put(side+48,c.base_y,4);put(0x409000+s*64,c.parent==1 and 0x414000 or 0,4);put(0x40901c+s*64,c.link==1 and 0x414000 or 0,4)
 local core=0x40c000+s*96;put(core+80,c.grabbing,4);put(core+88,c.attacking,4);put(core+52,c.aimove,4);put(core+56,c.aiattack,4);cache=0x43c000+c.model*256;put(cache+98,c.rise);put(cache+42,c.special);put(cache+72,c.escape)
 local faults=""")
 lua=lua.replace(" if c.bad=='token'"," if c.bad=='ready'then set('SourceCommonRun4086_Ready',0)elseif c.bad=='repeat'then set('SourceCommonRun4086_State',3)elseif c.bad=='commonready'then set('SourceCommonThink4086_Ready',0)elseif c.bad=='readonlyready'then set('SourceAIReadonly4086_Ready',0)elseif c.bad=='relations'then set('SourceRetirement4086_Ready',0)elseif c.bad=='core'then set('SourceModelEntityCopy4086_Ready',0)elseif c.bad=='ytag'then put(v+8,1)elseif c.bad=='ytaghigh'then put(v+10,1)end\n if c.bad=='token'")
 lua=lua.replace('{{0x414000,18432}', '{{0x409000,8192},{0x40c000,12288},{0x414000,18432}')
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=');end=lua.index('emu.addMemoryCallback(function()',start+len('emu.addMemoryCallback(function()'));lua=lua[:start]+lua[end:]
 lua=lua.replace("word(sy.SourceAI4086_State)..'|'..table.concat(trace,',')","word(sy.SourceCommonRun4086_State)..'|'..word(sy.SourceCommonThink4086_State)..'|'..table.concat(trace,',')")
 entry=symbols(Path('src/main.sym'))['SourceAIReadonly4086_Execute'];lua+=f"emu.addMemoryCallback(function()trace[#trace+1]=word(sy.SourceCommonThink4086_State)end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 lua+="emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)\n"
 lua+="emu.addMemoryCallback(function()emu.log('COMMONRUNCHECK|'..word(INDEX)..'|'..word(sy.SourceCommonRun4086_State)..'|'..word(sy.SourceCommonThink4086_State)..'|'..word(sy.SourceAIReadonly4086_Status)..'|'..table.concat(trace,','))end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)\n"
 r=Reporter('M4-COMMON-RUN',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceCommonRun4086_Begin','SourceCommonRun4086_Ready',0xb5e9,[],lua,r,batch_size=2)
 results=[]
 for l in log.splitlines():
  if 'AISEQUENCE|'in l:
   v=l.split('AISEQUENCE|',1)[1].split('|');results.append([*map(int,v[:5]),list(map(int,v[5].split(',')))if v[5]else []])
 wanted=[[i,0,0,3 if c['fault']else 2,c['common'],c['trace']]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('actual ordered native predicates, source short circuits, unbound handler rejection, CPU and all physical siblings',len(results)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_COMMON_RUN_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),service_responses_instrumented=False,controlled_entity_states=True,ai_parent_callback_completion_proven=False,grounded_normal_attack_bound=False,grounded_common_move_bound=False,initialized_special_handlers_bound=False,numeric_policy='ACCEPTED_COMPAT Q16 inair >=6554',motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
