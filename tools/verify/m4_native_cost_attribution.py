"""Read-only native callback profiling of the certified fused MOTU ROM."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from compiler import Source
from m4_input_controller_native import offset
import m4_online_component_native as native_driver

BASE=Path('out/byor-motu-tile-fusion-v2')
ROM_SHA='01b757d34ec1ad568758d325678b63bb96ad2f5b87badedae4ee65e1ac711977'
ROUTINES=('WarmCopyBackdrop','WarmStage','WarmFlush','WarmCompare','WarmSparseMaps','WarmAdvance','WarmSourcePresence','OnlineRowPointers','AstraOpaqueTile','WarmMapDmaHigh')
PHASES=('OnlinePublish','OnlinePreflight','OnlineWorklist','OnlineAllocationStart','OnlineAllocate','OnlineBlank','WarmColdBootstrap','WarmBootstrapDone','WarmRestore','OnlineTile','OnlineEncode','OnlineTransfer','OnlineMapsTransfer','OnlineComplete','OnlineVblank','OnlineNoopComplete','OnlineReject')


def plan(folder,contract):
    sy=contract['native_symbols'];rom=(folder/'native/bor.sfc').read_bytes()
    if hashlib.sha256(rom).hexdigest()!=ROM_SHA:raise ValueError('PROFILE_ROM_IDENTITY')
    asm=(folder/'native/publisher.pasm').read_text();bank=rom[57*32768:58*32768]
    points=defaultdict(list);calls=[];mvns=[]
    def add(at,kind,name,ret=0):points[at].append((kind,name,ret))
    for name in ROUTINES:
        address=sy[name];wide=name=='AstraOpaqueTile';opcode=bytes([0x22 if wide else 0x20])+address.to_bytes(3,'little')[:3 if wide else 2]
        aliases=[n for n,v in sy.items() if v==address]
        expected=sum(len(re.findall(r'^\s*(?:jsr|jsl) '+re.escape(n)+r'\s*$',asm,re.M)) for n in aliases)
        found=[m.start() for m in re.finditer(re.escape(opcode),bank)]
        if len(found)!=expected:raise ValueError('PROFILE_CALLSITE_AMBIGUITY:'+name)
        for at in found:
            pc=0x398000+at;ret=pc+len(opcode);add(ret,'P',str(ret));calls.append(dict(name=name,call=pc,return_address=ret,opcode=opcode.hex()))
        add(address,'E',name,3 if wide else 2)
    for dest,source in ((0x42,0xe1),(0x42,0xf4),(0x42,0x42),(0x42,0xe0)):
        opcode=bytes([0x54,dest,source]);found=[m.start() for m in re.finditer(re.escape(opcode),bank)]
        expected=len(re.findall(r'^\s*mvn \$%02X,\$%02X\s*$'%(dest,source),asm,re.M))
        if len(found)!=expected:raise ValueError('PROFILE_MVN_AMBIGUITY')
        for at in found:
            pc=0x398000+at
            if sy['WarmStage']<=pc<sy['WarmFlush']:name='StageMVN'
            elif sy['WarmCopyBackdrop']<=pc<sy['WarmStage']:name='BackdropMVN'
            else:name='MapInitMVN' if pc<sy['OnlineAllocationStart'] else 'MapCommitMVN'
            name+='_%06X'%pc;add(pc,'B',name,pc+3);add(pc+3,'P',str(pc+3));mvns.append(dict(name=name,address=pc,end=pc+3,destination_bank=dest,source_bank=source))
    add(sy['WarmColdBootstrap'],'B','ColdBootstrap',sy['WarmBootstrapDone']);add(sy['WarmBootstrapDone'],'P',str(sy['WarmBootstrapDone']))
    for name in PHASES:add(sy[name],'S',name)
    micro=(('AstraTileNextRow','foreground_mask'),('AstraTileNoSource','source_row_pointer'),('AstraTileRow','blend_body'),('AstraTilePixelDone','row_pointer_progression'),('AstraTileDone','tile_register_restore'))
    for label,name in micro:add(sy[label],'M',name)
    start=offset(sy['AstraTilePixelDone']);section=rom[start:offset(sy['AstraTileDone'])]
    marker=bytes.fromhex('e61ea51ec90800')
    if section.count(marker)!=1:raise ValueError('PROFILE_TILE_LOOP_BOUNDARY')
    add(sy['AstraTilePixelDone']+section.index(marker),'M','row_loop_control')
    return dict(points={str(k):v for k,v in sorted(points.items())},calls=calls,mvns=mvns,nmi=sy['OnlineNmi'])


def append_observer(script,contract,p):
    sy=contract['native_symbols'];actions=json.dumps(p['points'])
    # JSON is used only to generate literal numeric/string Lua statements below.
    code=["local profActive=false;local profOwnedBlank=false;local profDma=false;local profBlocks={};local profPoints={};local profVblank=false;local profPolls=0",
          "local profNmiPending={};local profState=nil;local function profLog(k,n,r,x)local s=profState or emu.getState();emu.log('PROF|'..k..'|'..n..'|'..s['masterClock']..'|'..(r or 0)..'|'..(x or 0))end",
          "local function profReturn(at)if profActive then profLog('P',tostring(at))end end",
          "local function profCheckNmi(at)local pending=profNmiPending[at];if profActive and pending and pending==emu.getState()['cpu.sp'] then profReturn(at);profNmiPending[at]=nil end end"]
    for key,entries in p['points'].items():
        at=int(key);body=[f'profPoints[{at}]=true']
        callback=[]
        for kind,name,ret in entries:
            if kind=='P':callback.append(f'profReturn({at});profBlocks[{at}]=nil')
        for kind,name,ret in entries:
            if kind=='S':
                if name=='OnlinePublish':callback.append('profActive=true;profOwnedBlank=false;profVblank=false;profPolls=0;profBlocks={}')
                if name=='OnlineBlank':callback.append('profOwnedBlank=true')
                if name=='OnlineVblank':callback.append("if profActive then profPolls=profPolls+1;if not profVblank then profLog('S','OnlineVblank');profVblank=true end end")
                else:callback.append(f"if profActive then profLog('S','{name}')end")
                if name in ('OnlineNoopComplete','OnlineReject'):callback.append('profActive=false')
            elif kind=='E':
                callback.append(f"if profActive then local s=profState or emu.getState();local sp=s['cpu.sp'];local mt=emu.memType.snesMemory;local r=emu.read((sp+1)&65535,mt)+256*emu.read((sp+2)&65535,mt);r=((r+1)&65535)+65536*({'emu.read((sp+3)&65535,mt)' if ret==3 else '0x39'});profLog('E','{name}',r)end")
            elif kind=='B':callback.append(f"if profActive and not profBlocks[{ret}] then profBlocks[{ret}]=true;local s=emu.getState();profLog('B','{name}',{ret},s['cpu.a']+1)end")
            elif kind=='M':callback.append(f"if profActive then profLog('M','{name}')end")
        body.append(f"emu.addMemoryCallback(function()profState=nil;profCheckNmi({at});{';'.join(callback)};profState=nil end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)")
        code+=body
    code+=[f"emu.addMemoryCallback(function()if profActive then local s=emu.getState();local sp=s['cpu.sp'];local mt=emu.memType.snesMemory;local r=emu.read((sp+2)&65535,mt)+256*emu.read((sp+3)&65535,mt)+65536*emu.read((sp+4)&65535,mt);profLog('E','NMI',r);profNmiPending[r]=(sp+4)&65535;if not profPoints[r] then profPoints[r]=true;emu.addMemoryCallback(function()profCheckNmi(r)end,emu.callbackType.exec,r,r,emu.cpuType.snes,emu.memType.snesMemory)end end end,emu.callbackType.exec,{p['nmi']},{p['nmi']},emu.cpuType.snes,emu.memType.snesMemory)",
      "emu.addMemoryCallback(function(a,v)if profActive then profDma=true;local mt=emu.memType.snesMemory;local n=emu.read(0x4375,mt)+256*emu.read(0x4376,mt);profLog('D','DMA',n,emu.read(0x4371,mt))end end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)"]
    ends=[at+2 for name,at in sy.items() if name.startswith('OnlineDmaDone')]
    rom=(script.parent/'bor.sfc').read_bytes();first=sy['OnlineBlank'];section=rom[offset(first):offset(sy['OnlineTile'])]
    ends +=[first+m.start()+7 for m in re.finditer(re.escape(bytes.fromhex('a9808d0b42')),section)]
    for at in sorted(set(ends)):
        code.append(f"emu.addMemoryCallback(function()if profActive and profDma then profLog('d','DMA');profDma=false end end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)")
    code.append("emu.addMemoryCallback(function(a,v)if profActive and profOwnedBlank and v==128 then profLog('S','ForcedBlank')elseif profActive and profOwnedBlank and v==15 then profLog('S','Release',profPolls);profActive=false end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)")
    with script.open('a') as f:f.write('\n-- NATIVE_COST_OBSERVER_BEGIN\n'+'\n'.join(code)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source',type=Path,default=Path('Masters of the Universe [v.3.0 Build 4086].pak'))
    p.add_argument('--warm',action='store_true');p.add_argument('--occupancy',type=Path,required=True);p.add_argument('--tile-fusion',action='store_true');a=p.parse_args()
    if not a.warm or not a.tile_fusion:raise ValueError('PROFILE_REQUIRES_CERTIFIED_FUSED_FLAGS')
    if a.output.exists():raise ValueError('PROFILE_OUTPUT_MUST_BE_NEW')
    folder=a.output.resolve();native=folder/'native';native.mkdir(parents=True)
    contract=json.loads((BASE/'contract.json').read_text())
    if json.loads((a.occupancy/'occupancy-manifest.json').read_text())!=contract['occupancy_manifest']:raise ValueError('PROFILE_OCCUPANCY_IDENTITY')
    for name in ('bor.sfc','publisher.pasm','publisher.sym','callback_owner.lua'):shutil.copyfile(BASE/'native'/name,native/name)
    os.link(BASE/'native/bor.msu',native/'bor.msu')
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    instrumentation=plan(folder,contract);(folder/'profile-plan.json').write_text(json.dumps(instrumentation,indent=2)+'\n')
    original=native_driver.observer
    def observed(script,c):original(script,c);append_observer(script,c,instrumentation)
    step_retries=[]
    def exact_profile_frames(m,count):
        remaining=count;last_end=None;attempts=0
        while remaining:
            r=m.run_frames(remaining);advanced=r.get('framesAdvanced',-1)
            if not 0<=advanced<=remaining or (last_end is not None and r['startFrame']!=last_end):raise ValueError('PROFILE_FRAME_STEP_DRIFT')
            remaining-=advanced;last_end=r['endFrame']
            if remaining:
                attempts+=1;step_retries.append(r)
                if not r.get('timedOut') or attempts>8:raise ValueError('PROFILE_FRAME_STEP_LIMIT')
    with patch.object(native_driver,'observer',observed),patch.object(native_driver,'run_frames_exact',exact_profile_frames):
        result=native_driver.run(folder,Source(a.source),symbols(Path('src/main.sym')),contract)
    (folder/'profile-step-retries.json').write_text(json.dumps(step_retries,indent=2)+'\n')
    from m4_opaque_dma_replay import verify
    result['actual_dma_replay']=verify(folder)
    from m4_tile_fusion_evidence import certify
    result['tile_fusion']=certify(folder,result)
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    from m4_native_cost_accounting import analyze
    profile=analyze(folder,result)
    (folder/'cost-attribution.json').write_text(json.dumps(profile,indent=2)+'\n')
    print(json.dumps(profile['summary'],indent=2))


if __name__=='__main__':main()
