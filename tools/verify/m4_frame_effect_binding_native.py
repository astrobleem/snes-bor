"""Weapon/idle cursor binding; external transition completion tickets instrumented."""
import argparse, hashlib, json, struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_frame_effects_4086 import ANIMATION_FIELDS, pack
from source_animation_init_4086 import pack as pack_init
from _harness import Reporter
from _source_leaf_fixture import run_fixture


def cases(weapon,drop):
    rows=[];numbers=sorted({r['case']['number'] for r in weapon['results']})
    for ar in weapon['results']:
        c=ar['case']
        if c['anim_flag']!=0:continue
        owner=65535 if c['weapon'] is None else [[],[2,0],[0,1],[-1,2]].index(c['weapon'])
        selected=ar['actual'][0];unsafe=ar['expected']['unsafe']
        rows.append(dict(c,op=3,mode=0,owner=owner,selected=selected,current=max(0,selected),players=ar['expected']['players'],fault=int(unsafe),pending=0,bad='',handle=numbers.index(c['number'])+1))
    for ar in drop['results']:
        c=ar['case'];n=c['loss'];wc=next(r for r in weapon['results'] if r['case']==dict(type=c['type'],loss=3,player=c['player'],number=n,anim_flag=0,weapon=[2,0]))
        rows.append(dict(type=c['type'],loss=3,player=c['player'],number=n,weapon=[2,0],op=2,mode=0,owner=1,selected=wc['actual'][0],current=wc['actual'][0],players=wc['expected']['players'] if n>0 else [77]*4,fault=0,pending=0,bad='',handle=1))
    for type_ in (0,1):
        for old in (1,2):
            for slot in (0,1,127):
                rows.append(dict(type=type_,loss=3,player=0,number=0,weapon=None,op=4,mode=0,owner=65535,selected=0,current=0,players=[77]*4,fault=0,pending=2 if old==2 else 0,bad='',handle=1,old=old,slot=slot))
    base=next(r for r in rows if r['op']==3 and r['selected']==2 and r['type']==1 and r['loss']==3 and r['player']==0 and not r['fault'])
    for op in (2,3):
        for slot in (0,1,127):rows.append(dict(base,op=op,current=0,pending=1,slot=slot,number=1,handle=numbers.index(1)+1))
    # Finish observes matching completion; it must never reselect a changed model.
    for op in (2,3,4):
        for slot in (0,1,127):rows.append(dict(base,op=op,mode=1,slot=slot,pending=0,current=2,players=[77]*4))
    for bad in ('ready','prefix','prefix_state','prefix_pending','cursor','cursor_state','slot','stale_handle','stale_frame','state','world','pool','side','count','bank','base','bounds','cursor_count','cursor_index','cursor_bank','cursor_base','cursor_bytes','weapon'):
        rows.append(dict(base,fault=1,bad=bad,players=[77]*4))
    dropbase=next(r for r in rows if r['op']==2 and r['number']==0)
    for bad in ('attached','flags','drop_entities','drop_bank','drop_bytes'):rows.append(dict(dropbase,fault=1,bad=bad))
    finishbase=next(r for r in rows if r['op']==3 and r['mode']==1)
    for bad in ('issued','unfinished','transition_slot','transition_target','transition_service','unissued'):
        rows.append(dict(finishbase,fault=1,bad=bad))
    idlebase=next(r for r in rows if r['op']==4 and r['mode']==1)
    for bad in ('idle_pending','idle_slot','idle_number','idle_reset'):
        rows.append(dict(idlebase,fault=1,bad=bad))
    for i,r in enumerate(rows):r.setdefault('slot',(0,1,127)[i%3]);r.setdefault('old',1)
    return rows,numbers


LUA=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local ctx=0;local start=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function long(a,v)put(a,v&65535);put(a+2,(v>>16)&65535)end
local function set(p,k,v)put(sy[p..'4086_'..k],v)end
local ranges={{0x414000,10240},{0x416800,8192},{0x40b000,3072},{0x40c000,12288},{0x41f500,2560},{0x43c000,8192},{0x43e000,512},{0x43e200,6416}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local core=0x40c000+96*c.slot;local f=0x43eb00+32*c.slot;local aux=0x41f500+20*c.slot;local meta=0x43e200+16*c.slot
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 for model=0,3 do long(0x40b000+160*model+156,c.type);put(0x40ba00+32*model+4,0);put(0x43c000+8*model,1);for j=1,3 do put(0x43c000+8*model+2*j,0)end end
 put(s,c.current);put(s+2,3);put(s+4,c.old);put(s+6,3);long(s+36,81920);long(s+40,-163840)
 put(v+16,1);put(v+18,0);long(v+20,99);put(v+40,1);put(v+42,0);long(v+44,c.player);long(core+72,c.type);long(core+80,123);long(core+84,77);long(core+88,7)
 long(f,-2);long(f+4,-1);long(f+8,3);long(f+12,2);long(f+16,17);long(f+20,0);long(f+24,48);long(f+28,0);long(aux+8,851968);put(aux+16,65535);long(0x43e000,17)
 put(meta,c.owner);put(meta+2,c.weapon and #c.weapon or 0);long(meta+4,c.loss);long(meta+8,c.op==2 and c.number or 0);long(meta+12,0)
 for i=0,3 do long(0x43ea00+4*i,77)end
 set('SourceIdle','Ready',0xb4f3)
 set('SourceFrameEffectBinding','Ready',0xb4f5);set('SourceFrameEffectBinding','State',c.mode==1 and (c.op==4 and 2 or 1) or 0);set('SourceFrameEffectBinding','Issued',c.mode==1 and c.op or 0);set('SourceFrameEffectBinding','Target',c.mode==1 and c.selected or 0)
 set('SourceUpdateFrame','Ready',0xb4e3);set('SourceUpdateFrame','State',1);set('SourceUpdateFrame','Pending',2);set('SourceUpdateFrame','Slot',c.slot);set('SourceUpdateFrame','Handle',c.handle);set('SourceUpdateFrame','Request',0);set('SourceUpdateFrame','Base',0x8000);set('SourceUpdateFrame','Bank',60);set('SourceUpdateFrame','Bytes',FEBYTES);set('SourceUpdateFrame','AnimationData',0x8000+16+8*HANDLES+152*(c.handle-1));set('SourceUpdateFrame','Animations',HANDLES)
 set('SourceFrameEffectPlan','Ready',0xb4f2);set('SourceFrameEffectPlan','State',1);set('SourceFrameEffectPlan','Service',c.op);set('SourceFrameEffectPlan','Acknowledged',0);set('SourceFrameEffectPlan','Slot',c.slot);set('SourceFrameEffectPlan','Handle',c.handle);set('SourceFrameEffectPlan','Frame',0);set('SourceFrameEffectPlan','Index',0);set('SourceFrameEffectPlan','Count',2);set('SourceFrameEffectPlan','Bank',59);set('SourceFrameEffectPlan','Base',0x8800);set('SourceFrameEffectPlan','Bytes',6);set('SourceFrameEffectPlan','Pool',2*(c.op-2))
 set('SourceWeapon','Ready',0xb4f1);set('SourceWeapon','Base',0x8400);set('SourceWeapon','Bank',59);set('SourceWeapon','Bytes',60);set('SourceWeapon','Models',4);set('SourceWeapon','Entities',128);set('SourceWeapon','Players',4);set('SourceWeapon','LevelWeaponLo',5);set('SourceWeapon','LevelWeaponHi',0)
 set('SourceModelEntityCopy','Ready',0xb4eb);set('SourceModelEntityCopy','Entities',128);set('SourceModelEntityCopy','Models',4)
 set('SourceModelCachedCopy','Ready',0xb4ee);set('SourceModelCachedCopy','Models',4)
 set('SourceModelAnimationCopy','Ready',0xb4e9);set('SourceModelAnimationCopy','Models',4);set('SourceModelAnimationCopy','Maximum',4);set('SourceModelAnimationCopy','Bytes',32)
 set('SourceModelAnimation','Ready',0xb4ef)
 set('SourceModelTransition','Ready',0xb4f0);set('SourceModelTransition','State',c.mode==1 and 2 or 0);set('SourceModelTransition','Service',0);set('SourceModelTransition','Slot',c.slot);set('SourceModelTransition','New',c.selected)
 set('SourceAnimationInit','Ready',0xb4ec);set('SourceAnimationInit','State',c.mode==1 and 2 or 0);set('SourceAnimationInit','Base',0x8000);set('SourceAnimationInit','Bank',59);set('SourceAnimationInit','Bytes',AIBYTES);set('SourceAnimationInit','Slot',c.slot);set('SourceAnimationInit','Number',0);set('SourceAnimationInit','Reset',0)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_SideBase,0x6800);put(sy.VmSourceWorld_Count,128)
 put(EXPECTFAULT,c.fault);put(MODE,c.mode)
 if c.bad=='ready'then set('SourceFrameEffectBinding','Ready',0)
 elseif c.bad=='prefix'then set('SourceUpdateFrame','Ready',0)
 elseif c.bad=='prefix_state'then set('SourceUpdateFrame','State',2)
 elseif c.bad=='prefix_pending'then set('SourceUpdateFrame','Pending',1)
 elseif c.bad=='cursor'then set('SourceFrameEffectPlan','Ready',0)
 elseif c.bad=='cursor_state'then set('SourceFrameEffectPlan','State',2)
 elseif c.bad=='slot'then set('SourceFrameEffectPlan','Slot',c.slot+1)
 elseif c.bad=='stale_handle'then set('SourceFrameEffectPlan','Handle',c.handle+1)
 elseif c.bad=='stale_frame'then set('SourceFrameEffectPlan','Frame',1)
 elseif c.bad=='state'then set('SourceFrameEffectBinding','State',1)
 elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='pool'then put(sy.VmSourceWorld_PoolBase,0x4002)
 elseif c.bad=='side'then put(sy.VmSourceWorld_SideBase,0x6802)
 elseif c.bad=='count'then put(sy.VmSourceWorld_Count,129)
 elseif c.bad=='bank'then set('SourceUpdateFrame','Bank',64)
 elseif c.bad=='base'then set('SourceUpdateFrame','Base',0x7ffe)
 elseif c.bad=='bounds'then set('SourceUpdateFrame','Bytes',100)
 elseif c.bad=='cursor_count'then set('SourceFrameEffectPlan','Count',1)
 elseif c.bad=='cursor_index'then set('SourceFrameEffectPlan','Index',1)
 elseif c.bad=='cursor_bank'then set('SourceFrameEffectPlan','Bank',64)
 elseif c.bad=='cursor_base'then set('SourceFrameEffectPlan','Base',0x7ffe)
 elseif c.bad=='cursor_bytes'then set('SourceFrameEffectPlan','Bytes',0)
 elseif c.bad=='weapon'then set('SourceWeapon','Ready',0)
 elseif c.bad=='attached'then long(f+28,0x414000)
 elseif c.bad=='flags'then set('SourceIdle','Ready',0)
 elseif c.bad=='drop_entities'then set('SourceWeapon','Entities',127)
 elseif c.bad=='drop_bank'then set('SourceWeapon','Bank',64)
 elseif c.bad=='drop_bytes'then set('SourceWeapon','Bytes',14)
 elseif c.bad=='issued'then set('SourceFrameEffectBinding','Issued',0)
 elseif c.bad=='unfinished'then set('SourceModelTransition','State',1)
 elseif c.bad=='transition_slot'then set('SourceModelTransition','Slot',c.slot+1)
 elseif c.bad=='transition_target'then set('SourceModelTransition','New',c.selected+1)
 elseif c.bad=='transition_service'then set('SourceModelTransition','Service',1)
 elseif c.bad=='unissued'then set('SourceFrameEffectBinding','State',0)
 elseif c.bad=='idle_pending'then set('SourceAnimationInit','State',1)
 elseif c.bad=='idle_slot'then set('SourceAnimationInit','Slot',c.slot+1)
 elseif c.bad=='idle_number'then set('SourceAnimationInit','Number',1)
 elseif c.bad=='idle_reset'then set('SourceAnimationInit','Reset',1)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
local function capture()local s=emu.getState();start=s.masterClock;ctx=0;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end end
emu.addMemoryCallback(capture,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(capture,emu.callbackType.exec,SECONDARY,SECONDARY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('EFFECTBINDCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local s=0x416800+64*c.slot;local v=0x414000+80*c.slot;local core=0x40c000+96*c.slot;local f=0x43eb00+32*c.slot;local aux=0x41f500+20*c.slot
 local function expect(a,n)for i=0,3 do before[a+i]=(n>>(8*i))&255 end end
 if c.mode==0 then
  for i=0,3 do expect(0x43ea00+4*i,c.players[i+1])end
  if c.op==4 and c.fault==0 then
   expect(f,3);expect(f+4,0);expect(f+8,0);expect(f+12,0);expect(core+88,0)
   if c.type~=0 then expect(s+36,0);expect(s+40,0)end
   if c.old~=1 then expect(v+20,0);before[s+4]=1;before[s+5]=0;expect(core+84,123);expect(aux+8,0);before[aux+16]=1;before[aux+17]=0;expect(0x43e000,0)end
  end
 end
 local mismatch=0;for addr,value in pairs(before)do if emu.read(addr,mt)~=value then mismatch=mismatch+1;if mismatch<3 then emu.log('BINDDIFF|'..word(INDEX)..'|'..addr..'|'..emu.read(addr,mt)..'|'..value)end end end
 local ticket=0;local ps=word(sy.SourceFrameEffectPlan4086_State);local hs=word(sy.SourceFrameEffectBinding4086_State)
 if c.fault==1 then if ps~=3 or hs~=3 then ticket=1 end
 elseif c.pending~=0 then
  if ps~=1 or hs~=c.pending or word(sy.SourceFrameEffectPlan4086_Index)~=0 or word(sy.SourceFrameEffectPlan4086_Service)~=c.op or word(sy.SourceFrameEffectBinding4086_Issued)~=c.op then ticket=1 end
  if c.pending==1 and (word(sy.SourceModelTransition4086_State)~=1 or word(sy.SourceModelTransition4086_Service)~=1 or word(sy.SourceFrameEffectBinding4086_Target)~=c.selected)then ticket=1 end
  if c.pending==2 and word(sy.SourceAnimationInit4086_State)~=1 then ticket=1 end
 else
  if ps~=1 or hs~=0 or word(sy.SourceFrameEffectPlan4086_Index)~=1 or word(sy.SourceFrameEffectPlan4086_Service)~=23 or word(sy.SourceFrameEffectBinding4086_Issued)~=0 then ticket=1 end
 end
 emu.log('EFFECTBINDRESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..ticket)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--weapon-authority',type=Path,required=True);p.add_argument('--drop-authority',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);weapon=json.loads(a.weapon_authority.read_text());drop=json.loads(a.drop_authority.read_text())
    if weapon['status']!='PASS' or weapon['function_sha256']!='f3aa6e1c2fb5b0ec566b70df86ed487502be6905af07cfff3e4656803052d295' or drop['status']!='PASS' or drop['function_sha256']!='0413ce75b29f0db14a4862c0690f7f1dc61855c121c67c7dcc794e677d75b0f1':raise ValueError('EFFECT_BINDING_C_AUTHORITY')
    rows,numbers=cases(weapon,drop);anims=[]
    for i,number in enumerate(numbers,1):
        e=dict.fromkeys(ANIMATION_FIELDS,0);e['weapon_number']=number;anims.append(dict(handle=i,events=e,frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6)]))
    fe=pack(dict(models=[],animations=anims));ai=pack_init(dict(maximum_animations=4,animations=[dict(handle=i,numframes=1,sync=-1,engine_animation_id=0) for i in range(1,len(numbers)+1)]))
    mw=struct.pack('<4s6H',b'B4MW',1,4,8,16,32,0)+b''.join(struct.pack('<4H',i,0 if i==0 else 2,48 if i<2 else 52 if i==2 else 56,0) for i in range(4))+struct.pack('<6h',2,0,0,1,-1,2)
    lua=LUA.replace('AIBYTES',str(len(ai))).replace('FEBYTES',str(len(fe))).replace('HANDLES',str(len(numbers)))
    reporter=Reporter('M4-FRAME-EFFECT-BINDING',kind='GATE');raw,log=run_fixture(a.rom,folder,rows,'SourceFrameEffectBinding4086_Begin','SourceFrameEffectBinding4086_Ready',0xb4f5,[(59,0,ai),(59,1024,mw),(59,2048,bytes((2,23,3,23,4,23))),(60,0,fe)],lua,reporter,finish='SourceFrameEffectBinding4086_Finish')
    results=[];costs=[]
    for line in log.splitlines():
        for marker,target in [('EFFECTBINDRESULT|',results),('EFFECTBINDCOST|',costs)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('policy mutations, pending tickets and guarded cursor advancement preserve bytes/context',len(results)==len(rows) and all(r==[i,0,0,0] for i,r in enumerate(results)))
    report=dict(schema='BYOR_4086_FRAME_EFFECT_BINDING_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),results=results,cpu_costs=costs,completion_tickets_instrumented=True,full_transition_services_bound=False,attached_weapon_release_bound=False,nested_idle_frame_execution_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
