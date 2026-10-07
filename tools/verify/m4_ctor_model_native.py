"""Fresh constructor copy of current cached fields, not model-switch fallback."""
import argparse,hashlib,itertools,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from script_callback_owner import derive,pack
from source_script_clone import derive as clone,pack as pack_clone
from source_lifecycle_inputs import derive as life,pack as pack_life
from source_model_core_4086 import derive as core,CACHED_FIELDS,FLOAT_FIELDS
from source_model_attack_policy import derive as attack_policy,FIELDS as POLICY_FIELDS
from source_binary32_q16 import project
from m4_script_clone_native import LUA as CLONE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols

LUA=CLONE_LUA.replace("put(rel+44,c.oldmask,4)","put(rel+44,0,4)")
LUA=LUA.replace("set('SourceScriptClone4086_Status',0)","set('SourceScriptClone4086_Status',2)")
LUA=LUA.replace(" set('SourceDefaultPlayer4086_Ready',0xb503)","""
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Status',0);set('SourceLifecycle4086_Base',0x8000+CLONEBYTES);set('SourceLifecycle4086_Bank',59);set('SourceLifecycle4086_Bytes',LIFEBYTES);set('SourceLifecycle4086_Models',16)
 set('SourceCtorModel4086_Status',0)
 for j,value in ipairs(c.cache)do emu.write(0x40b000+c.model*160+j-1,value,mt)end
 set('SourceDefaultPlayer4086_Ready',0xb503)""")
LUA=LUA.replace("local ranges={{0x40c000", "local ranges={{0x40b000,2560},{0x40c000")
LUA=LUA.replace(" if c.bad=='ready'then", """ if c.bad=='cleanup'then set('SourceScriptClone4086_Status',0)
 elseif c.bad=='life_ready'then set('SourceLifecycle4086_Ready',0)
 elseif c.bad=='life_sticky'then set('SourceLifecycle4086_Status',3)
 elseif c.bad=='life_models'then set('SourceLifecycle4086_Models',15)
 elseif c.bad=='life_table'then set('SourceLifecycle4086_Base',0x8000)
 elseif c.bad=='core'then set('SourceModelEntityCopy4086_Ready',0)
 elseif c.bad=='entities'then set('SourceModelEntityCopy4086_Entities',127)
 elseif c.bad=='initialized'then put(rel+44,1,4)
 elseif c.bad=='ready'then""")
start=LUA.index(' if c.fault==0 then');end=LUA.index(' local s=emu.getState()',start)
LUA=LUA[:start]+""" if c.fault==0 then
 local function expect(base,bytes)for j,value in ipairs(bytes)do before[base+j-1]=value end end
 expect(0x40c000+c.slot*96,c.wantcore);expect(0x439000+c.slot*80,c.wantlife)
 for _,r in ipairs(c.changes)do expect(r.address,r.bytes)end
 end
"""+LUA[end:]
LUA=LUA.replace("word(sy.SourceScriptClone4086_Status)","word(sy.SourceCtorModel4086_Status)")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--attack-policy',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);source=Source(a.source)
 cr=clone(source);ct=pack_clone(cr);cb,*_=derive(source);bt=pack(cb);lr=life(source);lt=pack_life(lr);mr=core(source);rows=[]
 for slot,m,mutate in itertools.product((0,1,127),mr['models'],(False,True)):
  f=dict(m['fields'])
  if mutate:f.update(speed=-1.25,health=-17,mp=23,multiple=-77,subject_to_wall=-2147483648)
  cache=bytearray()
  for field in CACHED_FIELDS:cache.extend(struct.pack('<f'if field in FLOAT_FIELDS else'<i',f[field]))
  cache.extend(struct.pack('<i',f['type']));bits=struct.unpack_from('<I',cache)[0]
  desired=cache[80:152]+cache[156:160]+cache[144:148]+bytes(16)
  fl=lr['models'][m['id']]['fields'];wl=bytearray(80);struct.pack_into('<4if',wl,48,fl['subtype'],fl['nomove'],fl['makeinv'],fl['priority'],fl['knockdowncount']);struct.pack_into('<IHHH',wl,68,int(bits&0x7fffffff!=0),m['id'],0xb4fb,0xb508)
  v=0x414000+slot*80;s=0x416800+slot*64
  def change(address,fmt,*values):return dict(address=address,bytes=list(struct.pack(fmt,*values)))
  changes=[change(v+32,'<Ii',1,f['health']),change(v+64,'<Ii',1,f['health']),change(s,'<HH',m['id'],m['id']),change(s+60,'<i',project(bits))]
  rows.append(dict(slot=slot,model=m['id'],mode=0,level=1,alive=1,multiple=0,platform=0,wall=0,bad='',fault=0,cache=list(cache),wantcore=list(desired),wantlife=list(wl),changes=changes))
 base=rows[0]
 for bits in(0,0x80000000,1,0x80000001,0x007fffff,0x80800000,0x37000000,0xb7000000,0x7f800000,0xff800000,0x7fc00000,0x47000000,0xc7000000):
  cache=bytearray(base['cache']);struct.pack_into('<I',cache,0,bits);fault=int(bits in(0x7f800000,0xff800000,0x7fc00000,0x47000000,0xc7000000));wl=bytearray(base['wantlife']);struct.pack_into('<I',wl,68,int(bits&0x7fffffff!=0));changes=list(base['changes'])
  if not fault:changes[-1]=change(0x41683c,'<i',project(bits))
  rows.append(dict(base,cache=list(cache),fault=fault,wantlife=list(wl),changes=changes))
 for slot,bad in itertools.product((0,127),('ready','world','pool','side','count','clone_slot','token','token_high','models','model','table','bank','bytes','vars','callback','cleanup','core','entities','life_ready','life_sticky','life_models','life_table','initialized','clear_entry','onkill')):rows.append(dict(base,slot=slot,bad=bad,fault=1))
 if a.attack_policy:
  policy=attack_policy(source)
  for bad in ('policy_ready','policy_models','policy_pair'):rows.append(dict(base,bad=bad,fault=1))
  for i,c in enumerate(rows):
   fields=policy['models'][c['model']]['fields'];values=[fields[k]for k in POLICY_FIELDS]if i%2==0 else[-1,65536,-2147483648,2147483647]
   c['policy']=list(struct.pack('<4i',*values))
 sy=symbols(Path('src/main.sym'));lua=LUA.replace('MODE',str(0x7ffd88)).replace('CLONEBYTES',str(len(ct))).replace('LIFEBYTES',str(len(lt))).replace('CALLBACKBYTES',str(len(bt))).replace('PROGRAMS',str(cb['program_count']))
 if a.attack_policy:
  setup="""
 set('SourceModelAttackPolicy4086_Ready',c.bad=='policy_ready'and 0xffff or 0xb5f0);set('SourceModelAttackPolicy4086_Models',c.bad=='policy_models'and 17 or c.bad=='policy_pair'and 15 or 16)
 for j=0,3071 do emu.write(0x42f400+j,0x5a,mt)end
 for j=0,255 do emu.write(0x40bc00+j,0xa5,mt)end
 for j,v in ipairs(c.policy)do emu.write(0x40bc00+c.model*16+j-1,v,mt)end
"""
  lua=lua.replace(" set('SourceCtorModel4086_Status',0)",setup+" set('SourceCtorModel4086_Status',0)")
  lua=lua.replace('local ranges={{0x40b000','local ranges={{0x40bc00,256},{0x42f400,3072},{0x40b000')
  lua=lua.replace(' expect(0x40c000+c.slot*96,c.wantcore);',' expect(0x42f408+c.slot*24,c.policy);expect(0x40c000+c.slot*96,c.wantcore);')
 lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
 entry=sy['SourceCtorModel4086_Apply'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};ctx=0;for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 r=Reporter('M4-CTOR-MODEL',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceCtorModel4086_Apply','SourceScriptClone4086_Ready',0xb5c1,[(59,0,ct+lt),(60,0,bt)],lua,r,batch_size=4)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('all sixteen current models, inherited mutations, signed/tiny speeds, fresh negative values, guards, full physical deltas and context',results==[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)])
 d=dict(schema='BYOR_4086_CTOR_MODEL_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,model_attack_policy_installed=a.attack_policy,media_bindings_bound=False,full_constructor_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
