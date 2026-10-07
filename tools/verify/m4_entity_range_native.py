"""Actual AI-owned entity positions and mutable role-handle range lookup."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA as OWNER_LUA
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from compiler import Source
from source_animation_range_4086 import derive,pack
from source_check_range_4086 import check

ASM='''
EntityRangeProbe:
.a16
.i16
 php
 rep #$38
 lda.l ENTITYROLE
 tax
 lda.l ENTITYTARGET
 jsl ENTITYQUERY
EntityRangeProbe_After:
.a16
.i16
 nop
 bcs EntityRangeProbe_Bad
 plp
 clc
 rtl
EntityRangeProbe_Bad:
.a16
.i16
 plp
 sec
 rtl
'''
SETUP=r'''
 set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)
 set('SourceCommonThink4086_Ready',c.bad=='common_ready'and 0 or 0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',c.bad=='common_slot'and(s+1)%128 or s)
 set('VmSourceEntity_Ready',c.bad=='entity_ready'and 0 or 0xb5ef);set('VmSourceEntity_Base',c.bad=='entity_base'and 0x4002 or 0x4000);set('VmSourceEntity_Bank',c.bad=='entity_bank'and 0 or 0x41);set('VmSourceEntity_Count',c.bad=='entity_count'and 127 or 128)
 set('SourceEntityRange4086_Ready',c.bad=='range_ready'and 0 or 0xb5f9);set('SourceEntityRange4086_Status',c.bad=='range_busy'and 1 or 0);put(sy.SourceEntityRange4086_Result,55,4)
 set('SourceEntityRange4086_TargetSlot',c.bad=='target_slot'and 128 or c.null and 0xffff or c.targetslot);set('SourceEntityRange4086_Role',c.bad=='role'and 128 or c.role)
 set('SourceAnimationRange4086_Ready',c.bad=='table_ready'and 0 or 0xb5f8);set('SourceAnimationRange4086_Status',c.bad=='table_busy'and 1 or 0);set('SourceAnimationRange4086_Bank',59);set('SourceAnimationRange4086_Bytes',2576)
 set('SourceCheckRange4086_Ready',c.bad=='numeric_ready'and 0 or 0xb5f7);set('SourceCheckRange4086_Status',c.bad=='numeric_busy'and 1 or 0)
 local t=0x414000+c.targetslot*80;put(t,t,4);put(t+4,c.targetexists,4);put(v+4,c.exists,4)
 put(side,c.bad=='model'and 16 or c.model);put(0x43c000+256*c.model+2*c.role,c.bad=='handle'and 0 or c.handle)
 -- Contradict the birth/current animation cursor: selected role's mutable
 -- pointer, rather than that cursor, determines check_range animation.
 put(side+4,65535);put(side+6,65535)
 for which,view in ipairs({v,t})do local coords=which==1 and c.source or c.target
  for axis,off in ipairs({52,60,12})do put(view+off-4,2,4);put(view+off,coords[axis],4)end
 end
 put(side+48,c.source[4],4);put(0x416830+c.targetslot*64,c.target[4],4);put(v+24,1,4);put(v+28,c.direction,4)
 if c.bad=='target_token'then put(t,t+1)elseif c.bad=='target_bank'then put(t+2,0)
 elseif c.bad=='source_x'then put(v+48,1)elseif c.bad=='target_z'then put(t+56,1)
 elseif c.bad=='source_y_reserved'then put(v+10,1)elseif c.bad=='target_y_reserved'then put(t+10,1)
 elseif c.bad=='direction'then put(v+24,2)elseif c.bad=='direction_reserved'then put(v+26,1)end
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--action-owner',action='store_true')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 ir=derive(Source(a.source));table=pack(ir);rows=[]
 for i,an in enumerate(ir['animations']):
  for variant in range(3):
   ranges=an['ranges'];source=[0]*4;target=[(ranges[2*k]+ranges[2*k+1])//2*65536 for k in range(4)]
   direction=(0,1,65536)[variant]
   if variant==2:target[0]=(ranges[1]+1)*65536
   if direction!=1:target[0]=-target[0]
   s=(0,1,63,127)[i%4];t=(s+1)%128
   rows.append(dict(time=50,nextthink=50,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=1,animation=5,spawn=3,respawn=4,animating=1,exists=(0,1,65536)[variant],bad='',mutation=0,fault=0,slot=s,targetslot=t,targetexists=(0,65536,0xffffffff)[variant],source=source,target=target,direction=direction,ranges=ranges,handle=an['handle'],role=(0,12,15,38,49,104)[i%6],model=i*7%16,null=False,expected=int(check(ranges,source,target,direction))))
 for bad in ('range_ready','range_busy','common_ready','common_slot','entity_ready','entity_base','entity_bank','entity_count','target_slot','target_token','target_bank','role','handle','table_ready','table_busy','numeric_ready','numeric_busy','source_x','target_z','source_y_reserved','target_y_reserved','direction','direction_reserved','world','cache','model','token','phase'):
  rows.append(dict(rows[0],bad=bad,fault=1))
 for c in rows[:16]:rows.append(dict(c,null=True,handle=0,expected=0))
 lua=OWNER_LUA[:OWNER_LUA.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=')]
 lua=lua.replace(' before={};',SETUP+' before={};')
 if a.action_owner:
  rows=[c for c in rows if c['bad']not in ('common_ready','common_slot')]
  rows.append(dict(rows[0],bad='action_state',fault=1))
  lua=lua.replace("set('SourceAI4086_State',2)","set('SourceAI4086_State',c.bad=='action_state'and 2 or 1)")
  lua=lua.replace(' before={};',"set('SourceCommonThink4086_Ready',0);set('SourceCommonThink4086_State',0);set('SourceCommonThink4086_Slot',65535)\n before={};")

 lua+=r'''
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,ENTITYQUERY,ENTITYQUERY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('ENTITYRANGEPROOF|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceEntityRange4086_Status)..'|'..dw(sy.SourceEntityRange4086_Result))
end,emu.callbackType.exec,ENTITYAFTER,ENTITYAFTER,emu.cpuType.snes,mt)
'''
 reporter=Reporter('M4-ENTITY-RANGE',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'EntityRangeProbe','SourceEntityRange4086_Ready',0xb5f9,[(59,0,table)],lua,reporter,batch_size=2,append=ASM,bindings=dict(ENTITYROLE='SourceEntityRange4086_Role',ENTITYTARGET='SourceEntityRange4086_TargetSlot',ENTITYQUERY='SourceEntityRange4086_Execute'),probes=dict(ENTITYAFTER='EntityRangeProbe_After'))
 actual=[list(map(int,l.split('ENTITYRANGEPROOF|',1)[1].split('|')))for l in log.splitlines()if 'ENTITYRANGEPROOF|'in l]
 expected=[[i,0,0,3 if c['fault']else 2,55 if c['fault']else c['expected']]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('actual physical coordinates/current mutable cache; retired self/target accepted; null short circuit; CPU/entities retained and guards',len(actual)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_ENTITY_RANGE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),source_table_sha256=hashlib.sha256(table).hexdigest(),numeric_policy='ACCEPTED_COMPAT_Q16_16',actual_entity_binding=True,actual_action_owner=a.action_owner,current_mutable_cache_read=True,combat_attack_choice_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
