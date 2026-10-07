"""Native constructor body/reset/setup with actual model/script binding."""
import argparse,hashlib,itertools,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from script_callback_owner import derive,pack
from source_script_clone import derive as clone,pack as pack_clone
from source_lifecycle_inputs import derive as life,pack as pack_life
from source_model_core_4086 import derive as core,CACHED_FIELDS,FLOAT_FIELDS
from source_ctor_state import derive as state,pack as pack_state
from source_model_factors import derive as factors
from source_binary32_q16 import project
from source_model_attack_policy import derive as attack_policy,FIELDS as POLICY_FIELDS
from m4_ctor_model_native import LUA as MODEL_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols
LUA=MODEL_LUA.replace("local ranges={{0x40b000", "local ranges={{0x42e000,5120},{0x41f300,512},{0x42f400,3072},{0x40bc00,256},{0x437e00,2560},{0x432800,4096},{0x433800,8192},{0x43b900,512},{0x43eb00,4096},{0x41f500,2560},{0x43fd80,32},{0x40b000")
LUA=LUA.replace(" set('SourceCtorModel4086_Status',0)","""
 set('SourceCtorModel4086_Status',0)
 for i=0,127 do local r=0x414000+i*80;put(r,r,4);put(r+4,0,4)end;put(v+4,0,4)
 for i=0,c.live-1 do local slot=i>=c.slot and i+1 or i;put(0x414004+slot*80,1,4)end
 for i=0,31 do emu.write(0x43fd80+i,0,mt)end;put(0x43fd80,c.live,4);set('SourceWorldTick4086_Maximum',c.maximum)
 set('SourceFreeze4086_Ready',0xb5df);set('SourceToss4086_Ready',0xb4e2);set('SourceModelAttackPolicy4086_Ready',0xb5f0);set('SourceModelAttackPolicy4086_Models',16)
 for j,value in ipairs(c.policy)do emu.write(0x40bc00+c.model*16+j-1,value,mt)end
 set('SourceCtorState4086_Ready',0xb5c2);set('SourceCtorState4086_Status',0);set('SourceCtorState4086_Base',0x8000+CLONEBYTES+LIFEBYTES);set('SourceCtorState4086_Bank',59);set('SourceCtorState4086_Bytes',STATEBYTES);set('SourceCtorState4086_Models',16)
 put(sy.SourceCtorState4086_X,c.x,4);put(sy.SourceCtorState4086_Z,c.z,4);put(sy.SourceCtorState4086_A,c.a,4);put(sy.SourceCtorState4086_Direction,c.direction,4);put(sy.SourceCtorState4086_Time,c.time,4);put(sy.SourceCtorState4086_Player,c.player,4);set('SourceCtorState4086_NoHit',c.nohit);set('SourceCtorState4086_SavedMode',c.saved)
 set('SourceFactors4086_Ready',0xb5f1);set('SourceFactors4086_Status',2);put(0x43b900+c.slot*4,c.model);put(0x43b902+c.slot*4,0xb5f1);for j,value in ipairs(c.factor)do emu.write(0x432800+c.slot*32+j-1,value,mt)end
""")
LUA=LUA.replace(" if c.bad=='cleanup'then", """ if c.bad=='state_ready'then set('SourceCtorState4086_Ready',0)
 elseif c.bad=='state_sticky'then set('SourceCtorState4086_Status',3)
 elseif c.bad=='state_pending'then set('SourceCtorState4086_Status',1)
 elseif c.bad=='state_models'then set('SourceCtorState4086_Models',15)
 elseif c.bad=='state_base'then set('SourceCtorState4086_Base',0x8000)
 elseif c.bad=='state_bank'then set('SourceCtorState4086_Bank',0)
 elseif c.bad=='state_bytes'then set('SourceCtorState4086_Bytes',STATEBYTES-2)
 elseif c.bad=='player_high'then put(sy.SourceCtorState4086_Player+2,1)
 elseif c.bad=='player_range'then put(sy.SourceCtorState4086_Player,4,4)
 elseif c.bad=='nohit'then set('SourceCtorState4086_NoHit',2)
 elseif c.bad=='saved'then set('SourceCtorState4086_SavedMode',2)
 elseif c.bad=='level'then set('VmSourceWorld_Level',2)
 elseif c.bad=='alive'then put(v+4,1,4)
 elseif c.bad=='pool_alive'then put(0x414004+((c.slot+1)%128)*80,2,4)
 elseif c.bad=='role_count'then put(0x43fd80,c.live+1,4)
 elseif c.bad=='role_count_high'then put(0x43fd82,1)
 elseif c.bad=='maximum'then set('SourceWorldTick4086_Maximum',129)
 elseif c.bad=='factor_ready'then set('SourceFactors4086_Ready',0)
 elseif c.bad=='factor_status'then set('SourceFactors4086_Status',0)
 elseif c.bad=='factor_model'then put(0x43b900+c.slot*4,(c.model+1)%16)
 elseif c.bad=='factor_stamp'then put(0x43b902+c.slot*4,0)
 elseif c.bad=='callback_program'then set('SourceAnimationCallback4086_Base',0x8010)
 elseif c.bad=='cleanup'then""")
start=LUA.index(' if c.fault==0 then');end=LUA.index(' local s=emu.getState()',start)
LUA=LUA[:start]+""" if c.fault==0 then
 local function expect(base,bytes)for j,value in ipairs(bytes)do before[base+j-1]=value end end
 for j=0,39 do before[0x42e000+c.slot*40+j]=0 end;for j=0,3 do before[0x41f300+c.slot*4+j]=0 end
 for j=0,23 do before[0x42f400+c.slot*24+j]=0 end;expect(0x42f408+c.slot*24,c.policy)
 expect(0x40c000+c.slot*96,c.wantcore);expect(0x439000+c.slot*80,c.wantlife)
 expect(0x414000+c.slot*80,c.wantview);expect(0x416800+c.slot*64,c.wantside);expect(0x409000+c.slot*64,c.wantrelation);expect(0x433800+c.slot*64,c.wantname)
 for i=0,19 do before[0x437e00+c.slot*20+i]=0 end;before[0x437e10+c.slot*20]=0xfb;before[0x437e11+c.slot*20]=0xb5
 for i=0,31 do before[0x43eb00+c.slot*32+i]=0 end;for i=0,19 do before[0x41f500+c.slot*20+i]=0 end
 for _,r in ipairs(c.changes)do expect(r.address,r.bytes)end
 end
"""+LUA[end:]
LUA=LUA.replace("word(sy.SourceCtorModel4086_Status)","word(sy.SourceCtorState4086_Status)")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--attack-timing',action='store_true');p.add_argument('--movement-state',action='store_true');p.add_argument('--attack-cost',action='store_true');p.add_argument('--attack-body',action='store_true');a=p.parse_args();a.attack_cost=a.attack_cost or a.movement_state;a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);source=Source(a.source)
 cr=clone(source);ct=pack_clone(cr);cb,*_=derive(source);bt=pack(cb);lr=life(source);lt=pack_life(lr);mr=core(source);sr=state(source);st=pack_state(sr);fr=factors(source);policy=attack_policy(source);rows=[]
 def case(slot,m,level=1,live=0,maximum=0,time=48,player=3,nohit=0,saved=0,direction=1,mutate=False):
  f=dict(m['fields']);sm=sr['models'][m['id']]
  if mutate:f.update(speed=-1.25,health=-17,mp=23,multiple=-77,subject_to_wall=-2147483648,type=129)
  cache=bytearray()
  for field in CACHED_FIELDS:cache.extend(struct.pack('<f'if field in FLOAT_FIELDS else'<i',f[field]))
  cache.extend(struct.pack('<i',f['type']));bits=struct.unpack_from('<I',cache)[0];desired=bytearray(cache[80:152]+cache[156:160]+cache[144:148]+bytes(16))
  if f['type']&1 and(saved or level and nohit):
   for off in(40,44):struct.pack_into('<I',desired,off,struct.unpack_from('<I',desired,off)[0]&0xfffffffe)
  fl=lr['models'][m['id']]['fields'];wl=bytearray(80);struct.pack_into('<4if',wl,48,fl['subtype'],fl['nomove'],fl['makeinv'],fl['priority'],fl['knockdowncount']);struct.pack_into('<IHHH',wl,68,int(bits&0x7fffffff!=0),m['id'],0xb4fb,0xb508)
  x,z,alt=-120*65536,190*65536,13*65536+32768;view=bytearray(80);struct.pack_into('<II',view,0,0x414000+slot*80,1)
  for off,tag,val in((8,2,alt),(16,1,0),(24,1,direction),(32,1,f['health']),(40,1,player if f['type']&1 else 0),(48,2,x),(56,2,z),(64,1,f['health'])):struct.pack_into('<II',view,off,tag,val&0xffffffff)
  side=bytearray(64);struct.pack_into('<HH',side,0,m['id'],m['id']);struct.pack_into('<IiII',side,12,time,sm['lifespan'],(time+1)&0xffffffff,(time+1)&0xffffffff);struct.pack_into('<H',side,30,sm['alpha']);struct.pack_into('<I',side,32,65536);struct.pack_into('<i',side,60,project(bits))
  rel=bytearray(64);struct.pack_into('<i',rel,36,sm['summonkill']);struct.pack_into('<I',rel,44,cr['models'][m['id']]['initialized_mask']);name=bytearray(64);encoded=sm['display_name'].encode('ascii');name[:len(encoded)]=encoded;struct.pack_into('<H',name,50,m['id']);struct.pack_into('<H',name,62,0xb5c2)
  changes=[dict(address=0x43fd80,bytes=list(struct.pack('<I',live+1)))]
  if f['type']&128:changes.append(dict(address=0x43fd98,bytes=list(struct.pack('<I',0x414000+slot*80))))
  return dict(slot=slot,model=m['id'],mode=0,level=level,alive=0,multiple=0,platform=0,wall=0,bad='',fault=0,cache=list(cache),wantcore=list(desired),wantlife=list(wl),wantview=list(view),wantside=list(side),wantrelation=list(rel),wantname=list(name),changes=changes,factor=list(bytes.fromhex(fr['models'][m['id']]['vector_hex'])),policy=list(struct.pack('<4i',*(policy['models'][m['id']]['fields'][f]for f in POLICY_FIELDS))),live=live,maximum=maximum,time=time,player=player,nohit=nohit,saved=saved,direction=direction,x=x,z=z,a=alt,wantmaximum=max(maximum,live+1))
 for slot,m,mutate in itertools.product((0,1,95,96,127)if a.attack_body else(0,1,127),mr['models'],(False,True)):rows.append(case(slot,m,mutate=mutate))
 player_model=next(m for m in mr['models']if m['fields']['type']==1)
 for level,nohit,saved,time,direction in itertools.product((0,1),(0,1),(0,1),(0,0xffffffff),(0,2,-1)):rows.append(case(127,player_model,level=level,nohit=nohit,saved=saved,time=time,direction=direction,live=3,maximum=7))
 for slot,bad in itertools.product((0,127),('state_ready','state_sticky','state_pending','state_models','state_base','state_bank','state_bytes','player_high','player_range','nohit','saved','level','alive','pool_alive','role_count','role_count_high','maximum','factor_ready','factor_status','factor_model','factor_stamp','callback_program','ready','world','pool','side','count','clone_slot','token','token_high','models','model','table','bank','bytes','vars','callback','cleanup','core','entities','life_ready','life_sticky','life_models','life_table','initialized','clear_entry','onkill')):rows.append(dict(rows[0],slot=slot,bad=bad,fault=1))
 sy=symbols(Path('src/main.sym'));lua=LUA.replace('MODE',str(0x7ffd88)).replace('CLONEBYTES',str(len(ct))).replace('LIFEBYTES',str(len(lt))).replace('STATEBYTES',str(len(st))).replace('CALLBACKBYTES',str(len(bt))).replace('PROGRAMS',str(cb['program_count']))
 if a.attack_timing:
  from source_attack_timing_4086 import derive as timing,pack as pack_timing
  from m4_animation_init_native import luav
  timing_data=pack_timing(timing(source))
  for c in rows:c['wanttiming']=list(timing_data[28+c['model']*12:40+c['model']*12])+[3,0xb6]
  lua='local timingbytes='+luav(list(timing_data))+'\n'+lua
  lua=lua.replace('local ranges={{0x42e000','local ranges={{0x438800,1984},{0x40bd00,192},{0x42e000')
  lua=lua.replace(' before={};'," set('SourceAttackTiming4086_Ready',0xb603);set('SourceAttackTiming4086_Status',2);set('SourceAttackTiming4086_Models',16);for j=0,191 do emu.write(0x40bd00+j,timingbytes[29+j],mt)end\n before={};")
  lua=lua.replace('if c.fault==0 then\n local function expect','if c.fault==0 then\n for j,value in ipairs(c.wanttiming)do before[0x438800+c.slot*14+j-1]=value end\n local function expect')
 else:lua=lua.replace(' before={};'," set('SourceAttackTiming4086_Ready',0)\n before={};")
 tables=[(59,0,ct+lt+st),(60,0,bt)]
 if a.attack_body:
  from source_attack_body_profile import derive as body_profile,pack_runtime
  from m4_animation_init_native import luav
  data=pack_runtime(body_profile(source));assert len(ct+lt+st)<=32768-len(data);tables.append((59,32768-len(data),data))
  for c in rows:c['wantbody']=list(data[16+c['model']*9:25+c['model']*9])+[5,0xb6]
  for bad in ('body_ready','body_busy'):rows.append(dict(rows[0],bad=bad,fault=1))
  lua=lua.replace('local ranges={{','local ranges={{0x435800,1536},{0x40bdcc,352},{')
  lua=lua.replace(' before={};'," set('SourceAttackBody4086_Ready',c.bad=='body_ready'and 0xb606 or 0xb605);set('SourceAttackBody4086_Status',c.bad=='body_busy'and 1 or 0);set('SourceAttackBody4086_Bank',59);set('SourceAttackBody4086_Base',0xff60);set('SourceAttackBody4086_Bytes',160);set('SourceAttackBody4086_Models',c.bad=='body_count'and 15 or 16)\n before={};")
  lua=lua.replace('if c.fault==0 then\n', 'if c.fault==0 then\n local b=c.slot<96 and 0x435980+c.slot*11 or 0x40bdcc+(c.slot-96)*11;for j,value in ipairs(c.wantbody)do before[b+j-1]=value end\n',1)
 else:lua=lua.replace(' before={};'," set('SourceAttackBody4086_Ready',0)\n before={};")
 if a.attack_cost:
  for bad in ('cost_ready','cost_cache_ready','cost_cache_size'):
   rows.append(dict(rows[0],bad=bad,fault=1))
  lua=lua.replace('local ranges={{','local ranges={{0x43c000,8192},{')
  lua=lua.replace(' before={};'," set('SourceAttackCostState4086_Ready',c.bad=='cost_ready'and 0xb60a or 0xb609);set('SourceModelAnimationCopy4086_Ready',c.bad=='cost_cache_ready'and 0 or 0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',168);set('SourceModelAnimationCopy4086_Bytes',c.bad=='cost_cache_size'and 8192 or 5376)\n for j=0,8191 do emu.write(0x43c000+j,(j*17+91)&255,mt)end\n before={};")
  lua=lua.replace('if c.fault==0 then\n','if c.fault==0 then\n for j=0,3 do before[0x43de00+c.slot*4+j]=0 end\n',1)
  lua+="emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];emu.log('CTORCOSTPUBLISH|'..word(INDEX)..'|'..word(0x43de00+c.slot*4)..'|'..word(0x43de02+c.slot*4))end,emu.callbackType.exec,sy.SourceCtorState4086_AIStateBirthDone,sy.SourceCtorState4086_AIStateBirthDone,emu.cpuType.snes,mt)\n"
 else:lua=lua.replace(' before={};'," set('SourceAttackCostState4086_Ready',0)\n before={};")
 if a.movement_state:
     for bad in ('movement_ready','movement_cache_size'):rows.append(dict(rows[0],bad=bad,fault=1))
     lua=lua.replace(' before={};'," set('SourceMovementState4086_Ready',c.bad=='movement_ready'and 0xb60c or 0xb60b);if c.bad=='movement_cache_size'then set('SourceModelAnimationCopy4086_Bytes',6658)end\n before={};")
     lua=lua.replace('if c.fault==0 then\n','if c.fault==0 then\n for j=0,7 do before[0x43da00+c.slot*8+j]=0 end\n',1)
 else:lua=lua.replace(' before={};'," set('SourceMovementState4086_Ready',0)\n before={};")
 if a.movement_state:lua+="emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];local nonzero=0;for j=0,7 do nonzero=nonzero|emu.read(0x43da00+c.slot*8+j,mt)end;emu.log('CTORDESTPUBLISH|'..word(INDEX)..'|'..nonzero)end,emu.callbackType.exec,sy.SourceCtorState4086_AIStateBirthDone,sy.SourceCtorState4086_AIStateBirthDone,emu.cpuType.snes,mt)\n"

 lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
 entry=sy['SourceCtorState4086_Begin'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};ctx=0;for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 lua+="emu.addMemoryCallback(function()emu.log('CTORMAX|'..word(INDEX)..'|'..word(sy.SourceWorldTick4086_Maximum))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
 lua+=r'''
local ctortrace={}
for name,address in pairs(sy)do
 if address>=0x3e8000 and address<0x400000 and(name:match('^SourceCtorState4086_')or name:match('^SourceCtorModel4086_')or name:match('^SourceFreeze4086_'))then
  local label=name
  emu.addMemoryCallback(function()
   if word(INDEX)==0 then ctortrace[#ctortrace+1]=label;if #ctortrace>20 then table.remove(ctortrace,1)end end
   if label=='SourceCtorState4086_Bad'or label=='SourceCtorState4086_BeginBad'then emu.log('CTORFAILTRACE|'..table.concat(ctortrace,','))end
  end,emu.callbackType.exec,address,address,emu.cpuType.snes,mt)
 end
end
'''
 r=Reporter('M4-CTOR-STATE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceCtorState4086_Begin','SourceCtorState4086_Ready',0xb5c2,tables,lua,r,batch_size=2)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line];maxima=[list(map(int,line.split('CTORMAX|',1)[1].split('|')))for line in log.splitlines()if 'CTORMAX|'in line]
 r.check('all current models, independent fields, full reset/name/map/source roles, inherited mutations, signed coordinates and guards preserve physical/context boundaries',results==[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)])
 r.check('source count/maximum publication and unsigned nextthink/nextmove wrap',maxima==[[i,129 if c['bad']=='maximum'else c['maximum']if c['fault']else c['wantmaximum']]for i,c in enumerate(rows)])
 if a.attack_cost:
  publish=[list(map(int,l.split('CTORCOSTPUBLISH|',1)[1].split('|')))for l in log.splitlines()if 'CTORCOSTPUBLISH|'in l];r.check('actual cost field zeroed before actor exists publication',publish==[[i,0,0]for i,c in enumerate(rows)if not c['fault']])
 if a.movement_state:
  publish=[list(map(int,l.split('CTORDESTPUBLISH|',1)[1].split('|')))for l in log.splitlines()if 'CTORDESTPUBLISH|'in l];r.check('actual two destination DWORDs zero before exists publication',publish==[[i,0]for i,c in enumerate(rows)if not c['fault']])
 d=dict(schema='BYOR_4086_CTOR_STATE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,maxima=maxima,script_cleanup_and_factor_copy_instrumented=True,slot_allocation_bound=False,drawmethod_execution_bound=False,palette_upload_bound=False,full_constructor_bound=False,combat_birth_fields_zeroed=True,attack_timing_actual_model_copy_bound=a.attack_timing,attack_body_actual_model_copy_bound=a.attack_body,attack_cost_actual_birth_clear_bound=a.attack_cost,movement_dest_actual_birth_clear_bound=a.movement_state,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
