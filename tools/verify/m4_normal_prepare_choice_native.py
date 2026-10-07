"""Actual normal_prepare weighted choices over source-derived range descriptors."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source
from source_frame_state_4086 import derive as frame_profile,pack as pack_frames
from source_frame_effects_4086 import derive as effect_profile,pack as pack_effects
from source_animation_init_4086 import derive as init_profile,pack as pack_init
from source_animation_range_4086 import derive as range_profile,pack as pack_ranges
from source_attack_choice_4086 import derive as choice_profile,pack as pack_choice
from source_attack_body_profile import derive as body_profile,pack_runtime
from m4_normal_prepare_native import ASM,SETUP
from m4_target_metadata_native import LUA as BASE_LUA
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--changed-animation',action='store_true')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);au=json.loads(a.authority.read_text());assert au['status']=='PASS';source=Source(a.source)
 fp=frame_profile(source);ft=pack_frames(fp);effects=pack_effects(effect_profile(source));init=pack_init(init_profile(source));rt=pack_ranges(range_profile(source));profile=choice_profile(source);pt=pack_choice(profile);body=pack_runtime(body_profile(source));assert profile['normal_roles']==[8,9,10,11]
 sample=next(an for an in fp['animations']if any(f['vulnerable']for f in an['frames']));frame=next(i for i,f in enumerate(sample['frames'])if f['vulnerable']);ids={m['identity']:m['index']for m in body_profile(source)['models']};rows=[]
 for c,e in zip(au['inputs'],au['actual']):
  if not(c['present']==c['ranges']or c['ranges']==0 and c['seed']==1):continue
  i=len(rows);slot=(0,1,95,96,127)[i%5];target=(slot+1)%128
  def entity(s,m,h,x,t):return dict(slot=s,model=m,handle=h,frame=frame if h==sample['handle']else 0,exists=1,type=t,hostile=int(t==2),dead=0,invincible=0,detect=-1,hide=-1,x=x,z=220*65536,direction=0 if t==2 else 1)
  options=[r for j,r in enumerate(profile['normal_roles'])if c['present']&c['ranges']&(1<<j)]
  rows.append(dict(c,expected=e,slot=slot,count=128,time=50,stalltime=0,noflip=0,found=1,entities=[entity(slot,14,1,0,2),entity(target,ids[sample['model']],sample['handle'],65536,1)],bad='',fault=0,options=options))
 if a.changed_animation:rows=[c for c in rows if c['total']]
 lua=BASE_LUA[:BASE_LUA.index('emu.addMemoryCallback(function()local s=emu.getState();cpu=')]
 lua=lua.replace('TABLESIZE',str(len(ft))).replace('put(v+28,1,4)','put(v+28,e.direction,4)').replace('put(v+52,65536*e.slot,4)','put(v+52,e.x,4)').replace('put(v+60,220*65536,4)','put(v+60,e.z,4)')
 setup=SETUP.replace('BODYBASE',str(0x8000+len(rt)+len(pt))).replace('BODYOFFSET',str(len(rt)+len(pt))).replace('CHOICEBYTES',str(len(pt))).replace("set('SourceAttackChoiceProfile4086_Base',0x8000)","set('SourceAttackChoiceProfile4086_Base',"+str(0x8000+len(rt))+")")
 setup+=r'''
 put(sy.SourceRandom4086_SeedLo,c.seed,4)
 for _,e in ipairs(c.entities)do put(0x414008+e.slot*80,2,4);put(0x41400c+e.slot*80,0,4);put(0x416830+e.slot*64,0,4)end
 set('SourceEntityRange4086_Ready',0xb5f9);set('SourceEntityRange4086_Status',0);set('SourceCheckRange4086_Ready',0xb5f7);set('SourceCheckRange4086_Status',0);set('SourceAnimationRange4086_Ready',0xb5f8);set('SourceAnimationRange4086_Status',0);set('SourceAnimationRange4086_Bank',60);set('SourceAnimationRange4086_Bytes',RANGEBYTES)
 for j=0,3 do if(c.present&(1<<j))~=0 then put(0x43c000+14*336+2*(8+j),(c.ranges&(1<<j))~=0 and NEARHANDLE or 18)end end
 for j=0,255 do emu.write(0x435800+j,0xa5,mt)end
 put(v+16,1,4);put(v+20,0,4)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',0);set('SourceAnimationInit4086_Number',55);set('SourceAnimationInit4086_Base',INITBASE);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',INITBYTES)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_Animations',80);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',58)
 '''
 for token,value in dict(NEARHANDLE=2 if a.changed_animation else 1,RANGEBYTES=len(rt),INITBASE=0x8000+len(ft),INITBYTES=len(init)).items():setup=setup.replace(token,str(value))
 lua='local choicebytes='+luav(list(pt))+'\nlocal bodybytes='+luav(list(body))+'\n'+lua.replace(' before={};',setup+' before={};')
 lua=lua.replace('{{0x414000,18432}', '{{0x43e000,512},{0x41f500,2560},{0x435800,1536},{0x40bdcc,352},{0x42e000,5120},{0x416800,8192},{0x43eb00,4096},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x414000,18432}')
 lua+=r'''
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,PREPARE,PREPARE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if word(sy.SourceNormalPrepare4086_Status)~=(CHANGED and 1 or 2) then emu.log('PREPFAULT|'..word(INDEX)..'|'..word(sy.SourceNormalPrepare4086_Status)..'|'..word(sy.SourceEntityRange4086_Status)..'|'..word(sy.SourceAnimationRange4086_Status)..'|'..word(sy.SourceCheckRange4086_Status)..'|'..word(sy.SourceAnimationInit4086_State))end;local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,PREPAREAFTER,PREPAREAFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local e=c.expected;local function expect(a,v,n)for j=0,n-1 do before[a+j]=(v>>(8*j))&255 end end
 expect(0x416824+c.slot*64,0,8);expect(0x43eb00+c.slot*32,e[3],4);expect(0x41401c+c.slot*80,e[6],4);expect(0x43900c+c.slot*80,e[5],4);expect(0x40c058+c.slot*96,e[4],4)
 if CHANGED then expect(0x416804+c.slot*64,2,2);expect(0x414014+c.slot*80,c.chosen,4);expect(0x41f508+c.slot*20,0,4);expect(0x41f510+c.slot*20,1,2);expect(0x43e004,0,4);expect(0x40c054+c.slot*96,0,4)end
 expect(sy.SourceRandom4086_SeedLo,c.seed_after,4);expect(sy.SourceRandom4086_CallsLo,(0xffffffff+c.calls)&0xffffffff,4)
 for j=17,#choicebytes do before[0x435900+j-17]=choicebytes[j]end
 for j,role in ipairs(c.options)do expect(0x435800+(j-1)*4,role,2);expect(0x435802+(j-1)*4,14-role,2)end
 local changed=0;local details='';for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1;if changed<=12 then details=details..string.format('%06x:%02x/%02x,',a,emu.read(a,mt),v)end end end
 if changed~=0 then emu.log('CHOICEDIAG|'..word(INDEX)..'|'..details)end
 emu.log('PREPCHOICE|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceNormalPrepare4086_Status)..'|'..word(sy.SourceAnimationInit4086_Number))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 lua=lua.replace('CHANGED','true'if a.changed_animation else'false')
 reporter=Reporter('M4-NORMAL-PREPARE-CHOICE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'PrepareProbe','SourceNormalPrepare4086_Ready',0xb606,[(58,0,effects),(59,0,ft+init),(60,0,rt+pt+body)],lua,reporter,append=ASM,bindings=dict(PROFILELOAD='SourceAttackChoiceProfile4086_Load',PREPARE='SourceNormalPrepare4086_Execute'),probes=dict(PREPAREAFTER='PrepareProbe_After'),batch_size=1,frame_limit=3000)
 actual=[list(map(int,l.split('PREPCHOICE|',1)[1].split('|')))for l in log.splitlines()if 'PREPCHOICE|'in l];expected=[[i,0,0,1 if a.changed_animation else 2,c['chosen']if c['chosen']>=0 else 55]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('literal C weighted role, one unconditional RNG plus selection RNG only with choices, actual source range masks, attack flags/action, CPU/VM/CRT/siblings',len(actual)==len(rows)and not failures)
 r=dict(schema='BYOR_4086_NORMAL_PREPARE_CHOICE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:10],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),domain='Mutable normal-role cache maps eligible roles to actual current handle 1 and ineligible present roles to source range handle 18; special roles absent, NULL weapon, chainlength 1',normal_weights=[6,5,4,3],changed_attack_animation_yield_bound=a.changed_animation,changed_attack_frame_zero_proven=False,common_attack_proc_executed=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
