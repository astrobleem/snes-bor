"""Real weighted picker: loaded profile, mutable cache, physical helpers/RNG."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA as OWNER_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from compiler import Source
from source_animation_range_4086 import derive as ranges,pack as pack_ranges
from source_animation_energy_4086 import derive as energy,pack as pack_energy
from source_attack_choice_4086 import derive,pack

ASM='''
AttackPickerProbe:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl PROFILELOAD
AttackPickerProbe_ProfileAfter:
.a16
.i16
 nop
 jsl PICKEXECUTE
AttackPickerProbe_PickAfter:
.a16
.i16
 nop
 bcs AttackPickerProbe_Bad
 ply
 plx
 plp
 clc
 rtl
AttackPickerProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
SETUP=r'''
 set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)
 set('SourceCommonThink4086_Ready',c.bad=='common_ready'and 0 or 0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',s)
 set('SourceModelAnimationCopy4086_Maximum',MAXIMUM);set('SourceModelAnimationCopy4086_Bytes',MAXIMUM*32);set('SourceModelAnimationCopy4086_Frames',80)
 put(side,c.model);put(side+4,65535);put(side+6,65535)
 for role=0,MAXIMUM-1 do put(0x43c000+MAXIMUM*2*c.model+role*2,0)end
 for role,handle in pairs(c.cache)do put(0x43c000+MAXIMUM*2*c.model+tonumber(role)*2,handle)end
 set('VmSourceEntity_Ready',0xb5ef);set('VmSourceEntity_Base',0x4000);set('VmSourceEntity_Bank',0x41);set('VmSourceEntity_Count',128)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128)
 set('SourceAttackChoiceProfile4086_Ready',c.bad=='profile_ready'and 0 or 0xb5fe);set('SourceAttackChoiceProfile4086_Status',c.bad=='profile_busy'and 1 or 0);set('SourceAttackChoiceProfile4086_Bank',59);set('SourceAttackChoiceProfile4086_Base',PROFILEBASE);set('SourceAttackChoiceProfile4086_Bytes',PROFILEBYTES)
 for i,v in ipairs(profilebytes)do emu.write(59*32768+PROFILEOFFSET+i-1,v,emu.memType.snesPrgRom)end
 if c.patch>=0 then for j=0,1 do emu.write(59*32768+PROFILEOFFSET+c.patch+j,(c.value>>(8*j))&255,emu.memType.snesPrgRom)end end
 set('SourceAttackPicker4086_Ready',c.bad=='picker_ready'and 0 or 0xb5ff);set('SourceAttackPicker4086_Status',c.bad=='picker_busy'and 1 or 0);set('SourceAttackPicker4086_Target',c.target_present and c.targetslot or 0xffff);put(sy.SourceAttackPicker4086_TestOnly,c.testonly,4);put(sy.SourceAttackPicker4086_Result,55,4)
 set('SourceEntityRange4086_Ready',0xb5f9);set('SourceEntityRange4086_Status',0);set('SourceCheckRange4086_Ready',0xb5f7);set('SourceCheckRange4086_Status',0);set('SourceAnimationRange4086_Ready',0xb5f8);set('SourceAnimationRange4086_Status',0);set('SourceAnimationRange4086_Bank',59);set('SourceAnimationRange4086_Bytes',RANGEBYTES)
 set('SourceEntityEnergy4086_Ready',0xb5fd);set('SourceEntityEnergy4086_Status',0);set('SourceCheckEnergy4086_Ready',0xb5fa);set('SourceCheckEnergy4086_Status',0);set('SourceAnimationEnergy4086_Ready',0xb5fc);set('SourceAnimationEnergy4086_Status',0);set('SourceAnimationEnergy4086_Bank',60);set('SourceAnimationEnergy4086_Bytes',ENERGYBYTES)
 local t=0x414000+c.targetslot*80;put(t,t,4);put(t+4,0x10000,4)
 for which,view in ipairs({v,t})do local coords=which==1 and c.source or c.target
  for axis,off in ipairs({52,60,12})do put(view+off-4,2,4);put(view+off,coords[axis],4)end
 end
 put(side+48,c.source[4],4);put(0x416830+c.targetslot*64,c.target[4],4);put(v+24,1,4);put(v+28,c.direction,4);put(v+32,1,4);put(v+36,c.health,4)
 put(0x40c048+s*96,c.type,4);put(0x40c04c+s*96,c.mp,4);put(0x437e04+s*20,c.seal,4);put(0x437e10+s*20,0xb5fb);put(0x437e12+s*20,0)
 local w=(s+2)%128;local wp=0x414000+80*w;put(wp,wp,4);put(wp+4,0,4);put(0x439030+w*80,9,4);put(0x43904a+w*80,0xb4fb);put(life+76,0xb508);put(flags+28,c.projectile and wp or 0,4)
 set('SourceRandom4086_Ready',c.bad=='rng_ready'and 0 or 0xb4d4);put(sy.SourceRandom4086_SeedLo,c.seed,4);put(sy.SourceRandom4086_CallsLo,0xffffffff,4);set('SourceRandom4086_Busy',c.bad=='rng_busy'and 1 or 0)
 if c.bad=='target_token'then put(t,t+1)elseif c.bad=='health_tag'then put(v+32,2)
 elseif c.bad=='handle'then put(0x43c000+MAXIMUM*2*c.model+16,81)elseif c.bad=='profile_base'then set('SourceAttackChoiceProfile4086_Base',0x7fff)
 elseif c.bad=='profile_extent'then set('SourceAttackChoiceProfile4086_Base',0xfff0)
 elseif c.bad=='weapon_token'then put(wp,wp+1)elseif c.bad=='weapon_bank'then put(flags+30,0)
 elseif c.bad=='combat_marker'then put(0x437e10+s*20,0)end
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--limit',type=int)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 au=json.loads(a.authority.read_text());assert au['status']=='PASS';source=Source(a.source);profile=derive(source);pt=pack(profile);rt=pack_ranges(ranges(source));et=pack_energy(energy(source));rows=[]
 for i,(c,e)in enumerate(zip(au['inputs'],au['actual'])):
  s=(0,1,63,127)[i%4];rows.append(dict(c,slot=s,targetslot=(s+1)%128,time=50,nextthink=50,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=1,animation=5,spawn=3,respawn=4,animating=1,exists=(0,1,65536,0xffffffff)[i%4],bad='',mutation=0,fault=0,patch=-1,value=0,expected=e[0]&0xffffffff,seed_after=e[1],calls=e[2]))
 base=next(c for c in reversed(rows)if c['total']>0 and c['projectile']and c['target_present'])
 for bad in ('picker_ready','picker_busy','profile_ready','profile_busy','profile_base','profile_extent','common_ready','phase','target_token','health_tag','handle','weapon_token','weapon_bank','combat_marker','rng_ready','rng_busy'):
  rows.append(dict(base,bad=bad,fault=1,expected=55,seed_after=base['seed'],calls=0))
 for label,at,value in [('magic',0,0),('version',4,2),('normal_min',6,3),('special_min',8,7),('capacity',12,63),('frames_zero',14,0),('frames_large',14,2048),('role',16,65535)]:rows.append(dict(base,bad=label,patch=at,value=value,fault=1,expected=55,seed_after=base['seed'],calls=0))
 if a.limit:rows=rows[:a.limit]
 lua=OWNER_LUA[:OWNER_LUA.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=')]
 lua=lua.replace(' before={};',SETUP+" if word(INDEX)==0 then emu.log('PICKREG|'..tostring(picker_registration_error or 'OK'))end\n before={};").replace('{{0x414000,18432}', '{{0x437e00,2560},{0x40c000,12288},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x414000,18432}')
 lua='local picker_registration_error=nil\nlocal profilebytes='+__import__('m4_animation_init_native').luav(list(pt))+'\n'+lua
 lua+=r'''
local profilecpu,pickcpu,profilectx={}, {},0
local profileclock,pickclock,profilecost=0,0,0
local function capture()local st=emu.getState();local cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3;return cpu,st.masterClock end
local function context(cpu)local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end;return ctx end
local regok,regerr=pcall(function()
emu.addMemoryCallback(function()profilecpu,profileclock=capture()end,emu.callbackType.exec,PROFILELOAD,PROFILELOAD,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()profilectx=context(profilecpu);profilecost=emu.getState().masterClock-profileclock end,emu.callbackType.exec,PROFILEAFTER,PROFILEAFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()pickcpu,pickclock=capture()end,emu.callbackType.exec,PICKEXECUTE,PICKEXECUTE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local ok,err=pcall(function()
 local c=rows[word(INDEX)+1];for j=0,3 do before[sy.SourceRandom4086_SeedLo+j]=(c.seed_after>>(8*j))&255;before[sy.SourceRandom4086_CallsLo+j]=(((0xffffffff+c.calls)&0xffffffff)>>(8*j))&255 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('WEIGHTEDPICKER|'..word(INDEX)..'|'..profilectx..'|'..context(pickcpu)..'|'..changed..'|'..word(sy.SourceAttackPicker4086_Status)..'|'..dw(sy.SourceAttackPicker4086_Result)..'|'..dw(sy.SourceRandom4086_SeedLo)..'|'..dw(sy.SourceRandom4086_CallsLo)..'|'..profilecost..'|'..(emu.getState().masterClock-pickclock))
 end);if not ok then emu.log('PICKEROBSERVERERROR|'..tostring(err))end
end,emu.callbackType.exec,PICKAFTER,PICKAFTER,emu.cpuType.snes,mt)
end);if not regok then picker_registration_error=regerr end
'''
 for token,value in dict(MAXIMUM=profile['maximum_animations'],PROFILEBASE=0x8000+len(rt),PROFILEOFFSET=len(rt),PROFILEBYTES=len(pt),RANGEBYTES=len(rt),ENERGYBYTES=len(et)).items():lua=lua.replace(token,str(value))
 reporter=Reporter('M4-ATTACK-PICKER',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'AttackPickerProbe','SourceAttackPicker4086_Ready',0xb5ff,[(59,0,rt+pt),(60,0,et)],lua,reporter,batch_size=1,frame_limit=6000,append=ASM,bindings=dict(PROFILELOAD='SourceAttackChoiceProfile4086_Load',PICKEXECUTE='SourceAttackPicker4086_Execute'),probes=dict(PROFILEAFTER='AttackPickerProbe_ProfileAfter',PICKAFTER='AttackPickerProbe_PickAfter'))
 actual=[list(map(int,l.split('WEIGHTEDPICKER|',1)[1].split('|')))for l in log.splitlines()if 'WEIGHTEDPICKER|'in l]
 expected=[[i,0,0,0,3 if c['fault']else 2,c['expected'],c['seed_after'],(0xffffffff+c['calls'])&0xffffffff]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v[:8],expected=e)for c,v,e in zip(rows,actual,expected)if v[:8]!=e]
 reporter.check('literal weighted selection through real current cache/physical range/energy/weapon and engine RNG; exact consumption; CPU/entities/VM/CRT retention and guards',len(actual)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_ATTACK_PICKER_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),profile_sha256=hashlib.sha256(pt).hexdigest(),profile_loader_peak_master_cycles=max((v[8]for v in actual),default=None),picker_peak_master_cycles=max((v[9]for v in actual),default=None),timing_includes_runtime_interrupts=True,choice_capacity=64,choice_storage_bytes=256,role_storage_bytes=128,normal_tryattack_caller_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
