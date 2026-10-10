"""Native common_pain prefix, actual inair predicate and retained child requests."""
import argparse,hashlib,itertools,json
from pathlib import Path
from actor_s5_entity_fixture import symbols
from source_foreign_state_layout import layout
from source_common_pain_native import emit
from source_engine_function_ids import function_id
from source_animation_ids import configure
from source_foreign_water_retirement import emit as water,transform as retire_water
from source_common_damage_actions_4086 import run as reference
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_input_controller_native import offset
from m4_animation_init_native import luav

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('rom','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);sy=symbols(Path('src/main.sym'));work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls');block=configure([])['authority']['enum']['ANI_BLOCK'];rows=[]
 mapping={0:0,1:function_id('common_pain'),3:function_id('common_grabbed'),4:function_id('common_block')}
 for s,anim,y,link,blocking in itertools.product((0,63,127),(0,1,2),(-6554,-6553,0,6553,6554),(0,1),(-1,0,1)):
  c=dict(slot=s,animating=anim,y=y,link=link,blocking=blocking,time=48,inpain=-7,fault=0,bad='');e,events=reference(dict(c,callback=0,air=int(abs(y)>=6554),action=1));c.update(expected_inpain=e['inpain'],expected_action=mapping[e['action']],service=1 if 2 in events else 2 if 1 in events else 0);rows.append(c)
 seed=next(c for c in rows if c['animating']==0 and c['y']==0 and c['link']==0 and c['blocking']==0)
 rows.extend(dict(seed,fault=1,bad=b)for b in ('tag','generation','time','slot','world','life_marker','action','pointer','alt_tag','status'))
 lua='local extra='+luav({k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\nfor k,v in pairs(extra)do sy[k]=v end\n'
 lua+=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={},{},0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(assert(sy[k],k),v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);local view=0x414000+c.slot*80
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Time',c.time,4);set('SourceLifecycle4086_Ready',0xb4fb)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4);put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end;for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 for i=0,127 do
  local v=0x414000+i*80;put(v,v,4);put(v+4,1,4);put(v+8,2,4);put(v+12,c.y,4)
  local s=0x416800+i*64;put(s+48,0,4)
  local l=0x439000+i*80;put(l+12,PAINACTION,4);put(l+72,3);put(l+74,0xb4fb)
  put(0x43eb04+i*32,c.inpain,4);put(0x43eb14+i*32,c.blocking,4);put(0x40901c+i*64,c.link==1 and 0x414000+80*((i+7)%128)or 0,4);put(0x41f510+i*20,c.animating)
 end
 for i=0,23 do put(CTRL+i,0,1)end;put(CTRL,0xb6b8);put(CTRL+4,c.slot);put(CTRL+8,1,4);put(CTRL+16,c.time,4)
 if c.bad=='tag'then put(CTRL,0)elseif c.bad=='generation'then put(CTRL+8,2,4)elseif c.bad=='time'then put(CTRL+16,c.time+1,4)elseif c.bad=='slot'then put(CTRL+4,128)elseif c.bad=='world'then set('VmSourceWorld_Ready',0)elseif c.bad=='life_marker'then put(0x43904a+c.slot*80,0)elseif c.bad=='action'then put(0x43900c+c.slot*80,0,4)elseif c.bad=='pointer'then put(view,view+1,4)elseif c.bad=='alt_tag'then put(view+8,1)elseif c.bad=='status'then put(CTRL+2,4)end
 before={};for _,r in ipairs({{0x414000,18432},{0x439000,10240},{0x43eb00,4096},{0x409000,8192},{0x41f500,2560}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then for _,f in ipairs({{0x43900c+c.slot*80,c.expected_action},{0x43eb04+c.slot*32,c.expected_inpain}})do for j=0,3 do before[f[1]+j]=(f[2]>>(8*j))&255 end end end
 local n=0;for at,v in pairs(before)do if emu.read(at,mt)~=v then n=n+1 end end;emu.log('COMMONPAINRESULT|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(CTRL+2)..'|'..word(CTRL+6)..'|'..word(CTRL+14))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
''';lua=lua.replace('CTRL',str(work)).replace('PAINACTION',str(function_id('common_pain')))
 wrapper='''CommonPainProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 ldx #1
 ldy #0
 jsl CommonPain_Run
 bcs CommonPainProbe_Bad
 jsl CommonPain_Run
 bcs CommonPainProbe_Bad
 ply
 plx
 plp
 clc
 rtl
CommonPainProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
 wrapper+=f"""CommonPainFixtureIsolatedReturn:
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
"""
 def isolate(raw,linked):
  retire_water(raw,linked);at=offset(linked['LeafFixture_Return']);assert raw[at:at+4]==bytes.fromhex('7a fa 28 08');raw[at:at+4]=b'\x5c'+linked['CommonPainFixtureIsolatedReturn'].to_bytes(3,'little')
 reporter=Reporter('M4-COMMON-PAIN-PREFIX',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'CommonPainProbe','SourceLifecycle4086_Ready',0xb4fb,[],lua,reporter,append=wrapper+emit(work,sy)+water(sy),rom_transform=isolate,batch_size=8,link_pcm=False)
 actual=[list(map(int,x.split('COMMONPAINRESULT|')[1].split('|')))for x in log.splitlines()if'COMMONPAINRESULT|'in x];expected=[[i,0,0,4 if c['fault']else 3 if c['service']else 2,0 if c['fault']else c['service'],block if not c['fault']and c['service']==2 else 0]for i,c in enumerate(rows)];reporter.check('actual common_pain short-circuit, Q16 inair, inpain/action writes and retained idle/block requests under retry preserve complete sibling/CPU state',actual==expected);reporter.check('bank0 remains byte-identical',raw[:32768]==a.rom.read_bytes()[:32768]);r=dict(schema='BYOR_COMMON_PAIN_PREFIX_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,rom_sha256=hashlib.sha256(raw).hexdigest(),numeric_policy='ACCEPTED_COMPAT_Q16_16 inair threshold6554; arbitrary binary32 boundary equivalence unclaimed',native_common_pain_prefix_bound=True,idle_or_block_frame_child_bound=False,full_common_pain_bound=False,new_foreign_arena_bytes=0,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()
if __name__=='__main__':main()
