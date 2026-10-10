"""Doland fixed source caches: present LAND and absent LAND across all models."""
import argparse,hashlib,itertools,json,struct
from pathlib import Path
from compiler import Source
from source_model_transition_bundle import compile as bundle
from source_foreign_state_layout import layout
from source_doland_native import emit
from source_foreign_water_retirement import emit as water,transform as retire_water
from source_engine_function_ids import function_id
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--authority',type=Path,required=True)
 for n in ('rom','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';reports,data,manifest=bundle(Source(a.source));sy=symbols(Path('src/main.sym'));work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls');maximum=reports['animations']['maximum_animations'];rows=[]
 for slot,model,direction in itertools.product((0,63,127),range(16),(-1,0,1,2,65536)):
  h=struct.unpack_from('<H',data['animation_cache'],(model*maximum+3)*2)[0];valid=int(bool(h and reports['animations']['animations'][h-1]['numframes']));k=authority['inputs'].index(dict(callback=0,direction=direction,valid=valid,animating=0));state,events=authority['actual'][k];rows.append(dict(slot=slot,model=model,direction=direction,land_handle=h,valid=valid,expected_direction=state[6],action=function_id('common_land')if state[7]==2 else 0,service=2 if valid else 1,role=3 if valid else 0,fault=0,bad=''))
 for bad in ('tag','generation','time','slot','world','life','pointer','physics','effects','effect_model','effect_marker','combat_marker','combat_reserved','animation_busy','frame_busy','direction_tag','state','cache_ready','cache_models','cache_bytes','cache_handle'):
  rows.append(dict(next(c for c in rows if c['valid']),fault=1,bad=bad))
 lua='local extras='+luav({k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\nfor k,v in pairs(extras)do sy[k]=v end\nlocal cache='+luav(list(data['animation_cache']))+'\n'
 lua+=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={},{},0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(assert(sy[k],k),v,n)end
local ranges={{0x414000,18432},{0x439000,10240},{0x437e00,2560},{0x7ef100,3072},{0x42d800,2048},{0x43c000,CACHEBYTES}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Time',48,4);set('SourceLifecycle4086_Ready',0xb4fb)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4);put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end;for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 set('SourcePhysicsState4086_Ready',0xb61c);set('SourceDamageEffectsState4086_Ready',0xb62f)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',0);set('SourceAnimationInit4086_Base',0x8000);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',AIBYTES)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Maximum',MAXIMUM);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Bytes',CACHEBYTES)
 set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',FEBYTES);set('SourceUpdateFrame4086_Animations',HANDLES);set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 for i,v in ipairs(cache)do put(0x43c000+i-1,v,1)end
 for i=0,127 do
  local v=0x414000+i*80;put(v,v,4);put(v+16,1,4);put(v+20,0,4);put(v+24,1,4);put(v+28,c.direction,4)
  local s=0x416800+i*64;put(s,c.model);put(s+4,0);put(s+36,65536,4);put(s+40,2*65536,4);put(s+44,3*65536,4)
  local l=0x439000+i*80;put(l+12,22,4);put(l+72,c.model);put(l+74,0xb4fb)
  put(0x7ef100+i*24,2,4);put(0x7ef114+i*24,0xb62f);put(0x7ef116+i*24,c.model)
  put(0x437e00+i*20,7,4);put(0x437e10+i*20,0xb5fb);put(0x437e12+i*20,0)
  put(0x42d80c+i*16,-2,4)
 end
 for i=0,23 do put(CTRL+i,0,1)end;put(CTRL,0xb6bc);put(CTRL+4,c.slot);put(CTRL+8,1,4);put(CTRL+16,48,4)
 local v=0x414000+c.slot*80
 if c.bad=='tag'then put(CTRL,0)elseif c.bad=='generation'then put(CTRL+8,2,4)elseif c.bad=='time'then put(CTRL+16,49,4)elseif c.bad=='slot'then put(CTRL+4,128)elseif c.bad=='world'then set('VmSourceWorld_Ready',0)elseif c.bad=='life'then put(0x43904a+c.slot*80,0)elseif c.bad=='pointer'then put(v,v+1,4)elseif c.bad=='physics'then set('SourcePhysicsState4086_Ready',0)elseif c.bad=='effects'then set('SourceDamageEffectsState4086_Ready',0)elseif c.bad=='effect_model'then put(0x7ef116+c.slot*24,65535)elseif c.bad=='effect_marker'then put(0x7ef114+c.slot*24,0)elseif c.bad=='combat_marker'then put(0x437e10+c.slot*20,0)elseif c.bad=='combat_reserved'then put(0x437e12+c.slot*20,1)elseif c.bad=='animation_busy'then set('SourceAnimationInit4086_State',1)elseif c.bad=='frame_busy'then set('SourceUpdateFrame4086_State',1)elseif c.bad=='direction_tag'then put(v+24,2)elseif c.bad=='state'then put(CTRL+2,4)elseif c.bad=='cache_ready'then set('SourceModelAnimationCopy4086_Ready',0)elseif c.bad=='cache_models'then set('SourceModelAnimationCopy4086_Models',0)elseif c.bad=='cache_bytes'then set('SourceModelAnimationCopy4086_Bytes',0)elseif c.bad=='cache_handle'then put(0x43c000+(c.model*MAXIMUM+3)*2,65535)end
 before={};for _,r in ipairs(ranges)do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local function value(a,v,n)for j=0,(n or 4)-1 do before[a+j]=(v>>(8*j))&255 end end
 if c.fault==0 then value(0x416824+c.slot*64,0);value(0x416828+c.slot*64,0);value(0x437e00+c.slot*20,0);value(0x7ef100+c.slot*24,0);value(0x42d80c+c.slot*16,0);value(0x43900c+c.slot*80,c.action);value(0x41401c+c.slot*80,c.expected_direction)end
 local n=0;for at,v in pairs(before)do if emu.read(at,mt)~=v then n=n+1 end end;emu.log('DOLANDCACHERESULT|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(CTRL+2)..'|'..word(CTRL+6)..'|'..word(CTRL+14))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 for k,v in dict(CTRL=work,MAXIMUM=maximum,CACHEBYTES=len(data['animation_cache']),AIBYTES=len(data['animations']),HANDLES=len(reports['animations']['animations']),FEBYTES=len(data['effects'])).items():lua=lua.replace(k,str(v))
 wrapper='''DolandCacheProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 ldx #1
 ldy #0
 jsl CommonDoland_Run
 bcs DolandCacheBad
 jsl CommonDoland_Run
 bcs DolandCacheBad
 ply
 plx
 plp
 clc
 rtl
DolandCacheBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
 wrapper+=f'''DolandCacheIsolatedReturn:
.a16
.i16
 php
 rep #$20
 pha
 lda #0
 sta.l {sy['VmSourceWorld_Ready']}
 pla
 plp
 ply
 plx
 plp
 php
 rep #$31
 phx
 phy
 jml {sy['Vm_SourceFrameGate']+5}
'''
 def isolate(raw,linked):
  retire_water(raw,linked);at=offset(linked['LeafFixture_Return']);assert raw[at:at+4]==bytes.fromhex('7a fa 28 08');raw[at:at+4]=b'\x5c'+linked['DolandCacheIsolatedReturn'].to_bytes(3,'little')
 lua+='''
emu.addMemoryCallback(function()local s=emu.getState();emu.log('DOLANDCACHEFAULT|'..word(INDEX)..'|a='..s['cpu.a']..'|d='..s['cpu.d']..'|x='..s['cpu.x']..'|ai='..word(sy.SourceAnimationInit4086_State)..'|model='..word(sy.SourceAnimationInit4086_Model)..'|handle='..word(sy.SourceAnimationInit4086_Handle))end,emu.callbackType.exec,DOLANDFAULT,DOLANDFAULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();emu.log('DOLANDCACHERESOLVEFAULT|'..word(INDEX)..'|a='..s['cpu.a']..'|x='..s['cpu.x'])end,emu.callbackType.exec,RESOLVEFAULT,RESOLVEFAULT,emu.cpuType.snes,mt)
'''
 r=Reporter('M4-DOLAND-SOURCE-CACHE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'DolandCacheProbe','SourceLifecycle4086_Ready',0xb4fb,[(59,0,data['animations']),(60,0,data['effects'])],lua,r,append=wrapper+emit(work,sy)+water(sy),rom_transform=isolate,probes={'DOLANDFAULT':'CommonDoland_Bad'},bindings={'RESOLVEFAULT':'SourceAnimationInit4086_ResolveBad'},batch_size=8,link_pcm=False)
 actual=[list(map(int,l.split('DOLANDCACHERESULT|')[1].split('|')))for l in log.splitlines()if'DOLANDCACHERESULT|'in l];expected=[[i,0,0,4 if c['fault']else 3,0 if c['fault']else c['service'],0 if c['fault']else c['role']]for i,c in enumerate(rows)];r.check('pinned C mutations with actual authored LAND presence/absence and unchanged siblings/CPU under retry',actual==expected);r.check('bank0 remains byte-identical',raw[:32768]==a.rom.read_bytes()[:32768]);result=dict(schema='BYOR_DOLAND_SOURCE_CACHE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,model_identities=manifest['models'],animation_cache_sha256=manifest['tables']['animation_cache']['sha256'],rom_sha256=hashlib.sha256(raw).hexdigest(),land_present_models=sorted({c['model']for c in rows if not c['fault']and c['valid']}),land_absent_models=sorted({c['model']for c in rows if not c['fault']and not c['valid']}),source_cache_and_provider_leases_installed_by_fixture=True,actual_animation_resolve_bound=True,frame_child_bound=False,full_doland_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True);(a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
