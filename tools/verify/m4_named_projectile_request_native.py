"""Exercise typed named projectile request parsing through the real native dispatcher."""
import argparse,hashlib,json
from pathlib import Path
from compiler import Source
from source_model_registry import derive,pack
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu={},{}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(j*8))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for j=0,r[2]-1 do emu.write(r[1]+j,0xa5,mt)end end
 for _,p in ipairs({{'SourceNativeRequest4086_Ready',0xb615},{'SourceNativeContinuation4086_Ready',0xb612},{'SourceNativeSnapshot4086_Ready',0xb614},{'SourceNamedKnife4086_Ready',0xb611},{'VmNativeVariant_ContextValid',0xb48f},{'SourceVMRun4086_Busy',0xb4d8},{'SourceCtorState4086_Ready',0xb5c2},{'SourceSpawnSlot4086_Ready',0xb5a1},{'SourceUpdateFrame4086_Ready',0xb4e3},{'SourceUpdateFrame4086_State',1},{'SourceUpdateFrame4086_Pending',1}})do set(p[1],p[2])end
 set('SourceNativeContinuation4086_Request',0);set('VmState_Status',2,1);set('VmState_Budget',99);set('VmCall_TargetId',0x20e);set('VmCall_Argc',8,1);set('VmCall_ArgListIndex',0);set('VmCall_ArgSlotsOff',64)
 set('VmSourceModels_Ready',0xb4a1);set('VmSourceModels_Base',0x8000);set('VmSourceModels_Bank',58,1);set('VmSourceModels_Count',MODELCOUNT);set('VmSourceModels_Bytes',TABLEBYTES)
 for j=0,63 do put(sy.VmSourceModels_Loaded+j,255,1)end
 if c.unloaded then put(sy.VmSourceModels_Loaded+(c.model>>3),255~(1<<(c.model&7)),1)end
 for j=0,7 do put(sy.VmCode_Wram+64+j*2,j);put(sy.VmSlots_Wram+j*8,c.cells[j+1][1],4);put(sy.VmSlots_Wram+j*8+4,c.cells[j+1][2],4)end
 set('VmStr_StringsOff',80);put(sy.VmCode_Wram+80,1);put(sy.VmCode_Wram+82,0);put(sy.VmCode_Wram+84,#c.name+1)
 for j=1,#c.name do put(sy.VmCode_Wram+85+j,string.byte(c.name,j),1)end;put(sy.VmCode_Wram+86+#c.name,0,1)
 put(sy.VmSlots_Wram+2,#c.name)
 if c.dynamic then put(sy.VmSlots_Wram+4,3);put(sy.VmSlots_Wram+6,0x8000);put(0x7fe400+3*64,1,1);put(0x7fe400+3*64+1,#c.name,1);for j=1,#c.name do put(0x7fe400+3*64+1+j,string.byte(c.name,j),1)end end
 for _,g in ipairs(c.guards)do set(g[1],g[2],g[3])end
 before={};for _,r in ipairs(ranges)do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
 local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local st=emu.getState();local ctx=0
 for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&124)~=(st['cpu.ps']&124)then ctx=ctx+1 end
 local want={};for a,v in pairs(before)do want[a]=v end
 local function expect(a,v,n)for j=0,(n or 2)-1 do want[a+j]=(v>>(j*8))&255 end end
 if c.fault==0 then
  expect(sy.SourceSpawnSlot4086_Model,c.unloaded and 65535 or c.model)
  for i,k in ipairs({'X','Z','A','Direction'})do expect(sy['SourceCtorState4086_'..k],c.expected[i],4)end
  for j=0,7 do want[sy.VmNativeVariant_Result+j]=0 end
  expect(sy.VmState_Budget,0);expect(sy.SourceNativeContinuation4086_Request,0xb613)
 end
 local mismatch=0;for a,v in pairs(want)do if emu.read(a,mt)~=v then mismatch=mismatch+1;if mismatch<=2 then emu.log('REQUESTDIFF|'..word(INDEX)..'|'..a..'|'..v..'|'..emu.read(a,mt))end end end
 emu.log('PROJECTILEREQUEST|'..word(INDEX)..'|'..ctx..'|'..mismatch..'|'..(st['cpu.ps']&1))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()set('VmState_Status',4,1);set('SourceVMRun4086_Busy',0);set('VmSourceCallback_Active',0);set('SourceUpdateFrame4086_Ready',0)end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();emu.log('REQUESTENTRY|'..word(sy.VmCall_TargetId)..'|'..word(sy.SourceNativeRequest4086_Ready)..'|'..st['cpu.a']..'|'..st['cpu.ps'])end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
for k,v in pairs(sy)do if k:match('^SourceNativeRequest4086_Check')or k=='SourceNativeRequest4086_Bad'then emu.addMemoryCallback(function()if word(INDEX)==0 then local st=emu.getState();emu.log('REQUESTGUARD|'..k..'|'..st['cpu.a']..'|'..st['cpu.ps'])end end,emu.callbackType.exec,v,v,emu.cpuType.snes,mt)end end

'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 registry=derive(Source(a.source));table=pack(registry);rows=[]
 for m in registry['models']:
  for dynamic in (False,True):
   for decimal in (False,True):
    values=[12.25,220.5,34.75]if decimal else [12,220,34]
    cells=[[6,0]]+[[2 if decimal else 1,int(v*65536)if decimal else v]for v in values]+[[1,1],[1,65536],[1,0],[1,0]]
    rows.append(dict(name=m['identity'].upper(),model=m['id'],dynamic=dynamic,cells=cells,expected=[int(v*65536)for v in values]+[1],fault=0,guards=[]))
 base=rows[0]
 rows.append(dict(base,unloaded=True))
 for arg,value in [(1,[1,32768]),(2,[1,-32769]),(1,[0,0]),(6,[1,1]),(7,[1,1]),(0,[1,1])]:
  cells=[c.copy()for c in base['cells']];cells[arg]=value;rows.append(dict(base,cells=cells,fault=1))
 for name,value in [('SourceNativeRequest4086_Ready',0),('SourceNativeContinuation4086_Request',0xb613),('SourceVMRun4086_Busy',0),('SourceCtorState4086_Ready',0),('SourceSpawnSlot4086_Ready',0),('VmCall_Argc',7),('SourceUpdateFrame4086_Pending',2)]:rows.append(dict(base,guards=[[name,value,1 if name=='VmCall_Argc'else 2]],fault=1))
 ranges=[(0x414000,18432),(0x40c000,12288),(0x439000,10240),(0x7fc000,8192),(0x7fe400,4096),(0x40f000,4096),(0x43fd00,128),(0x43b854,16),(0x43b882,2),(0x7ff600,8),(0x7fe098,2),(0x40bfae,2),(0x7ff67e,66)]
 lua='local ranges='+luav([list(x)for x in ranges])+'\n'+LUA.replace('MODELCOUNT',str(len(registry['models']))).replace('TABLEBYTES',str(len(table)))
 r=Reporter('M4-NAMED-PROJECTILE-REQUEST',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'Vm_NativeVariantDispatch','SourceNativeRequest4086_Ready',0xb615,[(58,0,table)],lua,r,batch_size=4)
 actual=[list(map(int,line.split('PROJECTILEREQUEST|',1)[1].split('|')))for line in log.splitlines()if'PROJECTILEREQUEST|'in line]
 expected=[[i,0,0,c['fault']]for i,c in enumerate(rows)]
 r.check('actual native dispatch; loaded source model names/literal and dynamic strings; typed coordinate conversion; queued descriptor only; rejected inputs atomic; no actor/VM slot/spawnentry mutation',actual==expected)
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_NAMED_PROJECTILE_REQUEST_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,rom_sha256=hashlib.sha256(raw).hexdigest(),registry_sha256=hashlib.sha256(table).hexdigest(),vm_call_boundary_instrumented=True,constructor_executed=False,actual_scripted_projectile_proven=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
