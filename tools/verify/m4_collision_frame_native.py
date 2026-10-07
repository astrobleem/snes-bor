"""Native B4FC reader over every source collision frame and corrupt guards."""
import argparse, hashlib, json, struct
from pathlib import Path
from m4_ai_owner_native import LUA as _IMPORT_PATH
from compiler import Source
from source_frame_state_4086 import derive, pack, unpack
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local cpu,ctx,before={},{},{}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v)put(sy[k],v)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('SourceCollisionFrame4086_Ready',c.bad=='ready'and 0 or 0xb5ee);set('SourceCollisionFrame4086_Status',c.bad=='busy'and 2 or 0)
 set('SourceCollisionFrame4086_Bank',c.bank);set('SourceCollisionFrame4086_Bytes',c.bytes);set('SourceCollisionFrame4086_Handle',c.handle);set('SourceCollisionFrame4086_Frame',c.frame)
 for _,k in ipairs({'Box','Attack','Vulnerable','Offset'})do set('SourceCollisionFrame4086_'..k,55)end
 for i,v in ipairs(tablebytes)do emu.write(59*32768+i-1,v,emu.memType.snesPrgRom)end
 if c.patch>=0 then for j=0,1 do emu.write(59*32768+c.patch+j,(c.value>>(8*j))&255,emu.memType.snesPrgRom)end end
 before={};for _,r in ipairs({{0x414000,18432},{0x41f500,2560},{0x42e000,8192},{0x439000,10240},{0x43eb00,4096},{0x43c000,8192}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('COLLISIONFRAME|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceCollisionFrame4086_Status)..'|'..word(sy.SourceCollisionFrame4086_Box)..'|'..word(sy.SourceCollisionFrame4086_Attack)..'|'..word(sy.SourceCollisionFrame4086_Vulnerable)..'|'..word(sy.SourceCollisionFrame4086_Offset))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--entity',action='store_true')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 ir=derive(Source(a.source));table=pack(ir);decoded=unpack(table);rows=[]
 for an,source in zip(decoded['animations'],ir['animations']):
  assert an['handle']==source['handle']
  start=struct.unpack_from('<H',table,16+(an['handle']-1)*8+4)[0]
  for i,(f,s)in enumerate(zip(an['frames'],source['frames'])):
   assert bool(f['bbox_index'])==s['vulnerable']
   rows.append(dict(handle=an['handle'],frame=i,bank=59,bytes=len(table),fault=0,bad='',patch=-1,value=0,expected=[f['bbox_index'],f['attack_index'],int(s['vulnerable']),start+12*i]))
 base=rows[0]
 for bad,change in [('ready',{}),('busy',{}),('bank',dict(bank=64)),('bytes_zero',dict(bytes=0)),('bytes_small',dict(bytes=23)),('bytes_large',dict(bytes=32769)),('handle_zero',dict(handle=0)),('handle_large',dict(handle=len(decoded['animations'])+1)),('frame_end',dict(frame=len(decoded['animations'][0]['frames']))),('frame_large',dict(frame=65535))]:rows.append(dict(base,**change,bad=bad,fault=1))
 start=base['expected'][3]
 for label,at,value in [('magic1',0,0),('magic2',2,0),('version',4,2),('reserved',14,1),('count_zero',6,0),('count_large',6,4095),('directory_handle',16,2),('directory_empty',18,0),('directory_offset_small',20,16),('directory_offset_overflow',20,65535),('directory_reserved',22,1),('frame_reserved',start+6,1),('bbox_range',start+8,65535),('attack_range',start+10,65535)]:rows.append(dict(base,bad=label,patch=at,value=value,fault=1))
 (a.output/'source.b4fc').write_bytes(table)
 lua=LUA;append='';bindings=None;probes=None;apply='SourceCollisionFrame4086_Query'
 if a.entity:
  for i,c in enumerate(rows):c.update(slot=(0,1,63,127)[i%4],exists=(1,65536,0xffffffff)[i%3])
  for bad in ('world','pool','side','count_zero','count_large','slot','token_low','token_high','retired'):rows.append(dict(rows[0],bad=bad,fault=1))
  setup=r'''
 local v=0x414000+c.slot*80;local side=0x416800+c.slot*64
 put(v,v,4);put(v+4,c.exists,4);put(side+4,c.handle);put(side+6,c.frame)
 -- Contradictory request controls prove that the live cursor is read.
 set('SourceCollisionFrame4086_Handle',65535);set('SourceCollisionFrame4086_Frame',65535)
 set('VmSourceWorld_Ready',c.bad=='world'and 0 or 0xb4a3);set('VmSourceWorld_PoolBase',c.bad=='pool'and 0x4002 or 0x4000);set('VmSourceWorld_SideBase',c.bad=='side'and 0x6802 or 0x6800);set('VmSourceWorld_Count',c.bad=='count_zero'and 0 or c.bad=='count_large'and 129 or 128)
 set('SourceCollisionFrame4086_EntitySlot',c.bad=='slot'and 128 or c.slot)
 if c.bad=='token_low'then put(v,v+1)elseif c.bad=='token_high'then put(v+2,0)elseif c.bad=='retired'then put(v+4,0,4)end
'''
  lua=lua.replace(' before={};',setup+' before={};')
  lua='local entitycpu,entityctx={},0\n'+lua.replace("..ctx..'|'","..(ctx+entityctx)..'|'")+r'''
emu.addMemoryCallback(function()local s=emu.getState();entitycpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do entitycpu[k]=s['cpu.'..k]end;entitycpu.sp=entitycpu.sp+3 end,emu.callbackType.exec,ENTITYQUERY,ENTITYQUERY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();entityctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if entitycpu[k]~=s['cpu.'..k]then entityctx=entityctx+1 end end;if(entitycpu.ps&254)~=(s['cpu.ps']&254)then entityctx=entityctx+1 end end,emu.callbackType.exec,ENTITYAFTER,ENTITYAFTER,emu.cpuType.snes,mt)
'''
  append='''
CollisionEntityProbe:
.a16
.i16
 php
 rep #$38
 lda.l ENTITYSLOT
 jsl ENTITYQUERY
CollisionEntityProbe_After:
.a16
.i16
 nop
 bcs CollisionEntityProbe_Bad
 plp
 clc
 rtl
CollisionEntityProbe_Bad:
.a16
.i16
 plp
 sec
 rtl
'''
  bindings=dict(ENTITYSLOT='SourceCollisionFrame4086_EntitySlot',ENTITYQUERY='SourceCollisionFrame4086_QueryEntity');probes=dict(ENTITYAFTER='CollisionEntityProbe_After');apply='CollisionEntityProbe'
 r=Reporter('M4-COLLISION-FRAME',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,apply,'SourceCollisionFrame4086_Ready',0xb5ee,[(59,0,table)],'local tablebytes='+luav(list(table))+'\n'+lua,r,batch_size=2,append=append,bindings=bindings,probes=probes)
 results=[list(map(int,l.split('COLLISIONFRAME|',1)[1].split('|')))for l in log.splitlines()if 'COLLISIONFRAME|'in l];wanted=[[i,0,0,3 if c['fault']else 2,*([55]*4 if c['fault']else c['expected'])]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('all source collision frames/bbox vulnerability and attack indexes; corrupt table/control guards; no partial outputs; CPU and physical world unchanged',len(results)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_COLLISION_FRAME_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),source_frames=sum(len(an['frames'])for an in ir['animations']),animations=len(ir['animations']),source_table_sha256=hashlib.sha256(table).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),inputs=rows,results=results,failures=failures[:20],actual_entity_cursor_read=a.entity,target_metadata_producer_bound=False,combat_collision_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
