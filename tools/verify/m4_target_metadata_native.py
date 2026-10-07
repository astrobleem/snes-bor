"""Observe real target metadata production, never inject its expected output."""
import argparse, hashlib, json, struct
from pathlib import Path
from m4_ai_owner_native import LUA as _IMPORT_PATH
from compiler import Source
from source_frame_state_4086 import derive, pack
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu,ctx={}, {},0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v)put(sy[k],v)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs({{0x414000,18432},{0x40c000,12288},{0x42f400,3072},{0x439000,10240}})do for j=0,r[2]-1 do emu.write(r[1]+j,0,mt)end end
 set('SourceTargetMeta4086_Ready',c.bad=='ready'and 0 or 0xb5f2);set('SourceTargetMeta4086_Status',c.bad=='busy'and 1 or 0)
 set('VmSourceWorld_Ready',c.bad=='world'and 0 or 0xb4a3);set('VmSourceWorld_PoolBase',c.bad=='pool'and 0x4002 or 0x4000);set('VmSourceWorld_SideBase',c.bad=='side'and 0x6802 or 0x6800);set('VmSourceWorld_Count',c.bad=='count_zero'and 0 or c.bad=='count_large'and 129 or c.count)
 put(sy.VmSourceWorld_Time,c.time,4)
 set('SourceModelEntityCopy4086_Ready',c.bad=='core_ready'and 0 or 0xb4eb);set('SourceModelEntityCopy4086_Entities',c.bad=='entities'and c.count+1 or c.count);set('SourceModelEntityCopy4086_Models',c.bad=='core_models'and 15 or 16)
 set('SourceModelAttackPolicy4086_Ready',c.bad=='policy'and 0 or 0xb5f0);set('SourceModelAttackPolicy4086_Models',c.bad=='models_zero'and 0 or c.bad=='models_large'and 17 or 16)
 set('SourceLifecycle4086_Ready',c.bad=='life_ready'and 0 or 0xb4fb);set('SourceLifecycle4086_Models',c.bad=='life_models'and 15 or 16)
 set('SourceCollisionFrame4086_Ready',c.bad=='collision'and 0 or 0xb5ee);set('SourceCollisionFrame4086_Bank',59);set('SourceCollisionFrame4086_Bytes',TABLESIZE)
 set('SourceTarget4086_Ready',0x5555);set('SourceTarget4086_Count',55);set('SourceTarget4086_ScanCount',1);set('SourceTarget4086_OrderReady',c.bad=='order_ready'and 0 or 0xb4d3)
 for j=0,c.count-1 do put(0x41f200+2*j,c.count-1-j);for k=0,19 do emu.write(0x41e800+20*j+k,0xa5,mt)end end
 if c.bad=='order_duplicate'then put(0x41f202,c.count-1)elseif c.bad=='order_range'then put(0x41f202,c.count)end
 for _,e in ipairs(c.entities)do
  local v=0x414000+80*e.slot;local core=0x40c000+96*e.slot;local life=0x439000+80*e.slot;local ai=0x42f400+24*e.slot;local side=0x416800+64*e.slot
  put(v,v,4);put(v+4,e.exists,4);put(v+24,1,4);put(v+28,1,4);put(v+48,2,4);put(v+52,65536*e.slot,4);put(v+56,2,4);put(v+60,220*65536,4)
  put(core+72,e.type,4);put(core+40,e.hostile,4);put(life+20,e.dead,4);put(life+24,e.invincible,4);put(life+72,e.model);put(life+74,0xb4fb);put(ai+16,e.detect,4);put(ai+20,e.hide,4);put(side,e.model);put(side+4,e.handle);put(side+6,e.frame)
 end
 local e=c.entities[#c.entities];local v=0x414000+80*e.slot;local life=0x439000+80*e.slot;local side=0x416800+64*e.slot
 if c.bad=='token_low'then put(v,v+1)elseif c.bad=='token_high'then put(v+2,0)elseif c.bad=='coordinate'then put(v+48,1)elseif c.bad=='coordinate_reserved'then put(v+50,1)elseif c.bad=='direction'then put(v+24,2)elseif c.bad=='wide_type'then put(0x40c000+96*e.slot+74,1)elseif c.bad=='life_marker'then put(life+74,0)elseif c.bad=='model_range'then put(life+72,16)elseif c.bad=='model_mismatch'then put(side,(e.model+1)%16)elseif c.bad=='handle'then put(side+4,0)elseif c.bad=='frame'then put(side+6,65535)end
 before={};for _,r in ipairs({{0x414000,18432},{0x40c000,12288},{0x42f400,3072},{0x439000,10240},{0x41f200,256}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 local hex='';for j=0,c.count*20-1 do hex=hex..string.format('%02x',emu.read(0x41e800+j,mt))end
 emu.log('TARGETMETA|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceTargetMeta4086_Status)..'|'..word(sy.SourceTarget4086_Ready)..'|'..word(sy.SourceTarget4086_Count)..'|'..word(sy.SourceTarget4086_ScanCount)..'|'..hex)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 ir=derive(Source(a.source));table=pack(ir);(a.output/'source.b4fc').write_bytes(table)
 models=json.loads(Path('out/byor-motu-model-attack-policy/report.json').read_text())['models'];ids={m['identity']:m['index']for m in models}
 frames=[dict(model=ids[an['model']],handle=an['handle'],frame=i,vulnerable=int(f['vulnerable']))for an in ir['animations']for i,f in enumerate(an['frames'])]
 rows=[]
 def ent(f,slot=1,i=0):return dict(f,slot=slot,exists=[1,65536,0xffffffff,0x80000000][i%4],type=[1,2,0x8000,0xffff][i%4],hostile=[0xffffffff,0x10000,0x80000000,1][i%4],dead=[0,65536,0xffffffff][i%3],invincible=[0,1,2,65537,0xffffffff][i%5],detect=[0,-1,-2147483648,2147483647][i%4],hide=[-1,0,2147483647,-2147483648][i%4])
 for i,f in enumerate(frames):rows.append(dict(count=3,time=(0xffffffff-i),entities=[ent(f,i%3,i)],bad='',fault=0))
 for model in range(16):
  f=next(f for f in frames if f['model']==model)
  rows.append(dict(count=128,time=0x80010000+model,entities=[ent(f,s,model+j)for j,s in enumerate((0,63,127))],bad='',fault=0))
 rows.append(dict(count=128,time=48,entities=[dict(ent(frames[0],127),exists=0,handle=65535,frame=65535)],bad='',fault=0))
 base=dict(count=3,time=48,entities=[ent(frames[0],0),ent(frames[-1],2)],bad='',fault=0)
 for bad in ('ready','busy','world','pool','side','count_zero','count_large','core_ready','entities','core_models','policy','models_zero','models_large','life_ready','life_models','collision','order_ready','order_duplicate','order_range','token_low','token_high','coordinate','coordinate_reserved','direction','wide_type','life_marker','model_range','model_mismatch','handle','frame'):rows.append(dict(base,bad=bad,fault=1))
 r=Reporter('M4-TARGET-METADATA',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'SourceTargetMeta4086_Build','SourceTargetMeta4086_Ready',0xb5f2,[(59,0,table)],LUA.replace('TABLESIZE',str(len(table))),r,batch_size=1,frame_limit=6000)
 results=[];failures=[]
 for line in log.splitlines():
  if 'TARGETMETA|'not in line:continue
  fields=line.split('TARGETMETA|',1)[1].split('|');i,ctx,changed,status,ready,count,scan=map(int,fields[:7]);c=rows[i]
  expected=bytearray(c['count']*20)
  for e in c['entities']:
   if e['exists']:struct.pack_into('<6Hii',expected,e['slot']*20,e['type'],e['hostile']&65535,int(bool(e['dead'])),int(e['invincible']==1),e['vulnerable'],0,e['detect'],e['hide'])
  ok=ctx==0 and changed==0 and status==(3 if c['fault']else 2)and ready==((0x5555 if c['bad']=='ready'else 0)if c['fault']else 0xb4d2)
  if not c['fault']:ok=ok and count==c['count']and scan==count and fields[7]==expected.hex()
  results.append(dict(index=i,status=status,ready=ready,context_faults=ctx,entity_changed=changed,metadata_sha256=hashlib.sha256(bytes.fromhex(fields[7])).hexdigest(),ok=ok))
  if not ok:failures.append(dict(input=c,actual=fields,expected=expected.hex()))
 r.check('all current source frame metadata, full32 flags and stealth, 128-slot scan, inactive invalid cursors, guarded publication, immutable entities and CPU',len(results)==len(rows)and not failures)
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_TARGET_METADATA_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),source_frames=len(frames),results=results,failures=failures[:10],table_sha256=hashlib.sha256(table).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),live_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()
if __name__=='__main__':main()
