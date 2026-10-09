"""Live target predicate followed by actual native source collision calls."""
import argparse,hashlib,json,re
from pathlib import Path
from m4_check_attack_native import ASM as BASE_ASM,LUA as BASE_LUA
from compiler import Source
from source_hit_state_layout import layout as hits
from source_hit_contact_layout import layout
from source_hit_state_native import emit as storage
from source_hit_contact_native import emit as contacts
from source_attack_target_native import emit
from source_attack_target_requirements import derive_requirements
from source_checkhit_zero_depth import derive as geometry
from source_checkhit_zero_depth_native import emit as collision
from source_frame_state_4086 import derive as frames,pack,unpack
from source_checkhit_q16 import checkhit
from source_attack_target_filter_4086 import decide,FIELDS
from source_engine_function_ids import function_id
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 src=Source(a.source);req=derive_requirements(src);gr=geometry(src);table=pack(frames(src));data=unpack(table);plan=layout();hp=hits();sy=symbols(Path('src/main.sym'))
 previous=json.loads(Path('out/byor-motu-checkhit-zero-depth-native/report.json').read_text())
 if previous['status']!='PASS'or previous['requirements']['collision_table_sha256']!=req['collision_table_sha256']:raise ValueError('TARGET_NATIVE_PAIRED_GEOMETRY_REQUIRED')
 seed=dict(next(r for r in previous['inputs']if r['hit']and not r.get('bad')))
 defaults=dict(exists=1,dead=0,invincible=0,type=1,them=1,pain_time=47,takedamage=1,hit_by=1,attack_id=2,lie=0,falling=0,jugglepoints=0,projectile=0,candamage=1,projectilehit=1)
 rows=[];seen=set()
 for row in previous['inputs']:
  if row.get('bad')or row['fault']:continue
  identity=(row['handle'],row['frame'],row['target_handle'],row['target_frame'])
  if identity not in seen:seen.add(identity);rows.append(dict(row,**defaults))
 axes=dict(exists=(0,-65536),dead=(1,-65536),invincible=(1,-65536,65536),type=(0,2,65536,-2147483648),pain_time=(0,48,49,0xffffffff),takedamage=(0,10),hit_by=(2,0xffffffff),falling=(1,-65536,65536),jugglepoints=(-2147483648,-1,1,65536,2147483647),lie=(1,),projectile=(-65536,1,65536),candamage=(0,2,65536,-2147483648),projectilehit=(0,2,65536,-2147483648))
 for field,values in axes.items():
  for value in values:rows.append(dict(seed,**(defaults|{field:value})))
 for falling in (0,1,-65536,65536):
  for juggle in (-2147483648,-1,0,1,65536):rows.append(dict(seed,**(defaults|dict(falling=falling,jugglepoints=juggle))))
 for val in (65536,-2147483648):
  rows.append(dict(seed,**(defaults|dict(type=val,candamage=val))))
  rows.append(dict(seed,**(defaults|dict(type=val,projectilehit=val,projectile=65536,candamage=0))))
 for c in rows:
  aa=data['animations'][c['handle']-1]['frames'][c['frame']];bb=data['animations'][c['target_handle']-1]['frames'][c['target_frame']];attack=data['attacks'][aa['attack_index']-1]
  def pos(values):return[(v if v<0x80000000 else v-0x100000000)/65536 for v in values]
  att=dict(token=c['slot'],position=pos(c['ap']),direction=c['ad'],grabdistance=36,attack_table=True,attack=attack)
  target=dict(token=c['target_slot'],position=pos(c['tp']),direction=c['td'],bbox_table=bool(bb['bbox_index']),bbox=data['boxes'][bb['bbox_index']-1]if bb['bbox_index']else None,vulnerable=bool(bb['bbox_index']),attack_table=bool(bb['attack_index']),attack=data['attacks'][bb['attack_index']-1]if bb['attack_index']else None)
  normal=checkhit(att,target,False);counter=checkhit(att,target,True)
  fields={k:c[k]for k in defaults if k in FIELDS};fields.update(time=48,attack_type=attack['attack_type'],attackone=-1,lasthit_present=1,is_last=0,otg=attack['otg'],jugglecost=attack['jugglecost'],counterattack=attack['counterattack'],normal_hit=int(normal is not None),counter_hit=int(counter is not None),them=c['projectilehit']if c['projectile']>0 else c['candamage'])
  q=decide(fields);c['hit']=int(q['admitted']);c['modes']=q['collision_modes'];hit=normal if normal else counter;c['contact']=[hit[k]&0xffffffff for k in ('x','y','z','type','confirm')]if q['admitted']else None
 for bad in ('phase','pending','time','world_view','world_side','canvas_generation','contact_ready','contact_generation','target_generation','life_ready','life_marker','core_ready','physics_ready','damage_ready','table_bank','table_bytes','life_model','life_side_model','model_count','life_model_count','entity_capacity'):
  rows.append(rows[0]|seed|defaults|dict(bad=bad,fault=1,hit=0,contact=None,modes=[]))
 setup=r"""
 local tv=0x414000+80*c.target_slot;local ts=0x416800+64*c.target_slot;local tl=0x439000+80*c.target_slot;local tc=0x40c000+96*c.target_slot
 put(tv,tv,4);put(tv+4,c.exists,4);put(ts,0);put(ts+4,c.target_handle);put(ts+6,c.target_frame)
 for _,pair in ipairs({{v,c.ap,c.ad},{tv,c.tp,c.td}})do local at=pair[1];local pose=pair[2]
  put(at+8,2,4);put(at+12,pose[2],4);put(at+48,2,4);put(at+52,pose[1],4);put(at+56,2,4);put(at+60,pose[3],4);put(at+24,1,4);put(at+28,pair[3],4)
 end
 put(tc+72,c.type,4);put(0x40c030+96*c.slot,c.candamage,4);put(0x40c034+96*c.slot,c.projectilehit,4)
 put(tl+72,0);put(tl+74,0xb4fb);put(tl+20,c.dead,4);put(tl+24,c.invincible,4);put(tl+4,c.takedamage,4);put(tl+12,c.lie==1 and LIE or 0,4)
 put(0x42d800+16*c.target_slot,c.falling,4)
 for i=0,1023 do put(CONTACT+i,165,1)end
 for i=0,63 do put(CW+i,0,1)end;put(CW,0xb6a3);put(CW+8,1,4);put(CW+16,CONTACT%65536);put(CW+18,0x42);put(CW+20,HC);put(CW+22,128)
 put(CONTACT+8*c.target_slot,c.pain_time,4);put(CONTACT+8*c.target_slot+4,c.jugglepoints,4)
 local targethit=HB+16*c.target_slot;put(targethit+8,1,4);put(targethit+12,0xb6a1);put(targethit+14,c.target_slot);put(targethit+4,c.hit_by,4)
 put(HW+4,c.slot);put(HW+26,c.target_slot);put(HB+16*c.slot,c.attack_id,4);for i=0,19 do put(HW+44+i,165,1)end
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Models',MODELCOUNT);set('SourceLifecycle4086_Models',MODELCOUNT);set('SourceModelEntityCopy4086_Entities',128)
 if c.bad=='contact_ready'then put(CW,0)elseif c.bad=='contact_generation'then put(CW+8,2,4)
 elseif c.bad=='target_generation'then put(targethit+8,2,4)elseif c.bad=='life_ready'then set('SourceLifecycle4086_Ready',0)
 elseif c.bad=='life_marker'then put(tl+74,0)elseif c.bad=='core_ready'then set('SourceModelEntityCopy4086_Ready',0)
 elseif c.bad=='physics_ready'then set('SourcePhysicsState4086_Ready',0)elseif c.bad=='damage_ready'then set('SourceDamageEffectsState4086_Ready',0)
 elseif c.bad=='life_model'then put(tl+72,MODELCOUNT)elseif c.bad=='life_side_model'then put(ts,1)
 elseif c.bad=='model_count'then set('SourceModelEntityCopy4086_Models',MODELCOUNT-1)elseif c.bad=='life_model_count'then set('SourceLifecycle4086_Models',MODELCOUNT-1)
 elseif c.bad=='entity_capacity'then set('SourceModelEntityCopy4086_Entities',127)
 elseif c.bad=='table_bank'then set('SourceCollisionFrame4086_Bank',59)elseif c.bad=='table_bytes'then set('SourceCollisionFrame4086_Bytes',CB-2)end
 before={};for _,r in ipairs(ranges)
"""
 lua=BASE_LUA.replace('local ranges={','local ranges={{CONTACT,1024},{0x439000,10240},{HW+44,20},{HW+4,2},')
 lua=lua.replace(' before={};for _,r in ipairs(ranges)',setup)
 lua=lua.replace(' if c.fault==0 and c.ticket==0 then for i=0,3 do before[HB+16*c.slot+i]=0 end end'," if c.fault==0 and c.hit==1 then for n,value in ipairs(c.contact)do for i=0,3 do before[HW+44+(n-1)*4+i]=(value>>(8*i))&255 end end end")
 lua='local normal_calls,counter_calls=0,0\n'+lua
 lua=lua.replace('ctx=0;ticket=0;decimal=0','ctx=0;ticket=0;decimal=0;normal_calls=0;counter_calls=0').replace('..word(sy.SourceWorldTick4086_Pending))',"..word(sy.SourceWorldTick4086_Pending)..'|'..normal_calls..'|'..counter_calls)")
 lua+='\nemu.addMemoryCallback(function()if word(HW+24)==0 then normal_calls=normal_calls+1 else counter_calls=counter_calls+1 end end,emu.callbackType.exec,COLLISION,COLLISION,emu.cpuType.snes,mt)\n'
 lua=lua.replace("'ATTACKGATE|'","'ATTACKTARGET|'").replace("..(c.fault==0 and ticket or -1)..","..(c.fault==0 and ticket or -1)..")
 for k,v in dict(HW=hp['controls'],HB=hp['base'],HC=plan['chr_capacity'],CB=len(table),CW=plan['controls'],CONTACT=plan['base'],LIE=function_id('common_lie'),MODELCOUNT=req['model_count']).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
 extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'};lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
 asm=BASE_ASM.replace('CheckAttack_Run','AttackTarget_Run')+storage(hp,sy)+contacts(plan,sy)+collision(gr,hp,sy,58)+emit(req,plan,sy)
 reporter=Reporter('M4-SOURCE-ATTACK-TARGET',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'AttackGateProbe','VmState_Error',0xb6a0,[(58,0,table)],lua,reporter,append=asm,probes={'RETURN':'AttackGateProbe_Return','COLLISION':'CheckHit_Run'},batch_size=4,link_pcm=False)
 actual=[list(map(int,l.split('ATTACKTARGET|',1)[1].split('|')))for l in log.splitlines()if 'ATTACKTARGET|'in l];wanted=[[i,0,0,8,-1 if c['fault']else c['hit'],7 if c.get('bad')=='phase'else 8,0 if c.get('bad')=='pending'else 1,int(0 in c['modes']),int(1 in c['modes'])]for i,c in enumerate(rows)]
 reporter.check('live target filtering, real source collision/contact, no actor or hit-state mutation, stale guards and CPU',actual==wanted);reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
 report=dict(schema='BYOR_SOURCE_ATTACK_TARGET_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,results=actual,expected=wanted,requirements=req,rom_sha256=hashlib.sha256(raw).hexdigest(),memory_lease_installed_by_fixture=True,ordered_target_loop_bound=False,damage_callbacks_bound=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
