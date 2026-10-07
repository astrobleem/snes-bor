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
from m4_ctor_model_native import LUA as MODEL_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols
LUA=MODEL_LUA.replace("local ranges={{0x40b000", "local ranges={{0x432800,4096},{0x433800,8192},{0x43b900,512},{0x43eb00,4096},{0x41f500,2560},{0x43fd80,32},{0x40b000")
LUA=LUA.replace(" set('SourceCtorModel4086_Status',0)","""
 set('SourceCtorModel4086_Status',0)
 for i=0,127 do local r=0x414000+i*80;put(r,r,4);put(r+4,0,4)end;put(v+4,0,4)
 for i=0,c.live-1 do local slot=i>=c.slot and i+1 or i;put(0x414004+slot*80,1,4)end
 for i=0,31 do emu.write(0x43fd80+i,0,mt)end;put(0x43fd80,c.live,4);set('SourceWorldTick4086_Maximum',c.maximum)
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
 expect(0x40c000+c.slot*96,c.wantcore);expect(0x439000+c.slot*80,c.wantlife)
 expect(0x414000+c.slot*80,c.wantview);expect(0x416800+c.slot*64,c.wantside);expect(0x409000+c.slot*64,c.wantrelation);expect(0x433800+c.slot*64,c.wantname)
 for i=0,31 do before[0x43eb00+c.slot*32+i]=0 end;for i=0,19 do before[0x41f500+c.slot*20+i]=0 end
 for _,r in ipairs(c.changes)do expect(r.address,r.bytes)end
 end
"""+LUA[end:]
LUA=LUA.replace("word(sy.SourceCtorModel4086_Status)","word(sy.SourceCtorState4086_Status)")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);source=Source(a.source)
 cr=clone(source);ct=pack_clone(cr);cb,*_=derive(source);bt=pack(cb);lr=life(source);lt=pack_life(lr);mr=core(source);sr=state(source);st=pack_state(sr);fr=factors(source);rows=[]
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
  return dict(slot=slot,model=m['id'],mode=0,level=level,alive=0,multiple=0,platform=0,wall=0,bad='',fault=0,cache=list(cache),wantcore=list(desired),wantlife=list(wl),wantview=list(view),wantside=list(side),wantrelation=list(rel),wantname=list(name),changes=changes,factor=list(bytes.fromhex(fr['models'][m['id']]['vector_hex'])),live=live,maximum=maximum,time=time,player=player,nohit=nohit,saved=saved,direction=direction,x=x,z=z,a=alt,wantmaximum=max(maximum,live+1))
 for slot,m,mutate in itertools.product((0,1,127),mr['models'],(False,True)):rows.append(case(slot,m,mutate=mutate))
 player_model=next(m for m in mr['models']if m['fields']['type']==1)
 for level,nohit,saved,time,direction in itertools.product((0,1),(0,1),(0,1),(0,0xffffffff),(0,2,-1)):rows.append(case(127,player_model,level=level,nohit=nohit,saved=saved,time=time,direction=direction,live=3,maximum=7))
 for slot,bad in itertools.product((0,127),('state_ready','state_sticky','state_pending','state_models','state_base','state_bank','state_bytes','player_high','player_range','nohit','saved','level','alive','pool_alive','role_count','role_count_high','maximum','factor_ready','factor_status','factor_model','factor_stamp','callback_program','ready','world','pool','side','count','clone_slot','token','token_high','models','model','table','bank','bytes','vars','callback','cleanup','core','entities','life_ready','life_sticky','life_models','life_table','initialized','clear_entry','onkill')):rows.append(dict(rows[0],slot=slot,bad=bad,fault=1))
 sy=symbols(Path('src/main.sym'));lua=LUA.replace('MODE',str(0x7ffd88)).replace('CLONEBYTES',str(len(ct))).replace('LIFEBYTES',str(len(lt))).replace('STATEBYTES',str(len(st))).replace('CALLBACKBYTES',str(len(bt))).replace('PROGRAMS',str(cb['program_count']))
 lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
 entry=sy['SourceCtorState4086_Begin'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};ctx=0;for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 lua+="emu.addMemoryCallback(function()emu.log('CTORMAX|'..word(INDEX)..'|'..word(sy.SourceWorldTick4086_Maximum))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
 r=Reporter('M4-CTOR-STATE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceCtorState4086_Begin','SourceCtorState4086_Ready',0xb5c2,[(59,0,ct+lt+st),(60,0,bt)],lua,r,batch_size=2)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line];maxima=[list(map(int,line.split('CTORMAX|',1)[1].split('|')))for line in log.splitlines()if 'CTORMAX|'in line]
 r.check('all current models, independent fields, full reset/name/map/source roles, inherited mutations, signed coordinates and guards preserve physical/context boundaries',results==[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)])
 r.check('source count/maximum publication and unsigned nextthink/nextmove wrap',maxima==[[i,129 if c['bad']=='maximum'else c['maximum']if c['fault']else c['wantmaximum']]for i,c in enumerate(rows)])
 d=dict(schema='BYOR_4086_CTOR_STATE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,maxima=maxima,script_cleanup_and_factor_copy_instrumented=True,slot_allocation_bound=False,drawmethod_execution_bound=False,palette_upload_bound=False,full_constructor_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
