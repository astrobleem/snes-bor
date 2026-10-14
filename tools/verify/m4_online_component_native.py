"""Real JOY1/source world -> online native lossless component display proof.

Host builds immutable source assets once before boot. After boot it supplies
controller inputs and request words, reads evidence and independently composes
golden images only after native DMA/publication. It never injects graphics.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
from actor_s5_entity_fixture import symbols
import game_bor_startup_select as startup
from m4_live_ground_owner import REQUEST,SNAPSHOT
from m4_live_ground_component_native import sha,scene_from_snapshot,check_motion
from m4_bounded_component_publisher import READY,DISPLAY_EPOCH
from m4_online_component_publisher import build
from compiler import Source
from component_source_assets import derive
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555


def observer(script,contract):
    fs=contract['native_symbols']
    original=script.read_text().split('-- ONLINE_OBSERVER_BEGIN',1)[0]
    # Drop observers appended by earlier exploratory executions of this private
    # candidate. The constructor bootstrap itself remains byte-for-byte intact.
    original=original.split('\nlocal online=false;',1)[0]
    script.write_text(original+'\n-- ONLINE_OBSERVER_BEGIN\n')
    with script.open('a') as f:
        f.write('''
local online=false;local blank=false;local unsafe=0;local dmas=0;local vramword=0;local dmaActive=false
local function stamp(name)
 local s=emu.getState();emu.log('ONLINE|'..name..'|'..s['masterClock']..'|'..s['ppu.frameCount']..'|'..s['ppu.scanline'])
end
''')
        for name in ('OnlinePublish','OnlinePreflight','OnlineAllocationStart','WarmAllocationDone','OnlineBlank','OnlineTile','OnlineEncode','OnlineTransfer','OnlineMapsTransfer','OnlineComplete','OnlineReject',*[n for n in fs if n.startswith(('OnlineDmaDone','OnlineNoopComplete'))]):
            if name not in fs:continue
            address=fs[name]+(2 if name.startswith('OnlineDmaDone') else 0)
            body=f"stamp('{name}')"
            if name.startswith('OnlineDmaDone'):body=f"if dmaActive then {body};dmaActive=false end"
            f.write(f"emu.addMemoryCallback(function(){'online=true;' if name=='OnlineBlank' else ''}{body} end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,emu.memType.snesMemory)\n")
        from m4_input_controller_native import offset
        rom=(script.parent/'bor.sfc').read_bytes();first=fs['OnlineBlank'];section=rom[offset(first):offset(fs['OnlineTile'])]
        cursor=0;index=0
        while True:
            at=section.find(bytes.fromhex('a9808d0b42'),cursor)
            if at<0:break
            index+=1;address=first+at+7;cursor=at+5
            f.write(f"emu.addMemoryCallback(function()if dmaActive then stamp('OnlineBootDmaDone{index}');dmaActive=false end end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,emu.memType.snesMemory)\n")
        if 'OnlineCoverage' in fs:
            start=fs['OnlineCoverage'];body=rom[offset(start):offset(start)+256]
            end=start+body.index(bytes.fromhex('a55a60'))+2
            if 'WarmSourcePresence' in fs:start,end=fs['WarmSourcePresence'],fs['WarmPresenceDone']
            f.write('''
local coverageStart=0;local coverageClocks=0;local coverageCalls=0
local kernelStart=0;local kernelClocks=0;local kernelCalls=0
local function clock()return emu.getState()['masterClock']end
''')
            for label,at in (('coverage_entry',start),('coverage_exit',end),('kernel_entry',fs['AstraOpaqueRow']),('kernel_exit',fs['AstraDone'])):
                prefix='coverage' if label.startswith('coverage') else 'kernel'
                body=f'{prefix}Start=clock()' if label.endswith('entry') else f'{prefix}Clocks={prefix}Clocks+clock()-{prefix}Start;{prefix}Calls={prefix}Calls+1'
                f.write(f'emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n')
            for label in ('OnlineComplete','OnlineNoopComplete'):
                if label not in fs:continue
                at=fs[label]
                f.write(f"emu.addMemoryCallback(function()emu.log('ONLINE_HELPERS|'..coverageCalls..'|'..coverageClocks..'|'..kernelCalls..'|'..kernelClocks);coverageCalls=0;coverageClocks=0;kernelCalls=0;kernelClocks=0 end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n")
        f.write('''
emu.addMemoryCallback(function(a,v)
 if not online then return end
 if a==0x2116 then vramword=(vramword&0xff00)|v end
 if a==0x2117 then vramword=(vramword&0x00ff)|(v<<8) end
 if a==0x2100 then
  blank=(v&0x80)~=0;stamp('INIDISP:'..v)
 elseif not blank then unsafe=unsafe+1;emu.log('ONLINE_UNSAFE|'..a..'|'..v) end
end,emu.callbackType.write,0x2100,0x2133,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if online then
  dmas=dmas+1;local mt=emu.memType.snesMemory
  dmaActive=true
  local n=emu.read(0x4375,mt)+256*emu.read(0x4376,mt)
  local target=emu.read(0x4371,mt)
  stamp('DMA:'..n..':'..target..':'..vramword)
  local source=emu.read(0x4372,mt)+256*emu.read(0x4373,mt)+65536*emu.read(0x4374,mt)
  local bytes={}
  if source<0xc00000 then
   for j=0,n-1 do bytes[#bytes+1]=string.format('%02x',emu.read(source+j,mt)) end
  end
  emu.log('ONLINE_PACKET|'..target..'|'..vramword..'|'..source..'|'..n..'|'..table.concat(bytes))
  if target==0x18 then
   if 2*vramword+n>65536 then emu.log('ONLINE_RESOURCE_FAULT|VRAM_RANGE') end
   vramword=(vramword+n//2)&0xffff
  elseif target~=0x22 or n~=512 then emu.log('ONLINE_RESOURCE_FAULT|DMA_TARGET') end
  if not blank then emu.log('ONLINE_UNSAFE|DMA') end
 end
end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
''')


def run(folder,source,sy,contract):
    native=folder/'native';script=native/'callback_owner.lua';observer(script,contract)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kw):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kw)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter=Reporter('MOTU-ONLINE-COMPONENT',kind='GATE');observations=[];samples=[];last=None
    with Observed(rom=native/'bor.sfc',mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=native/'mesen.log') as m:
        m.write_u16(READY,0)
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('ONLINE_BOOTSTRAP')
        run_frames_exact(m,12)
        for n in ('StageWater_Enabled','StageWater_Pending','StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'):m.write_u8(sy[n],0)
        m.write_u16(0x7ffb84,0);m.write_u16(0x7ffb82,0)
        sequence=['birth']+['right']*8+['released']+['up']*4+['released']+['right']*2+['released']
        for i,label in enumerate(sequence):
            m.hold_input(dict(birth=0,right=m.BTN_RIGHT,up=m.BTN_UP,released=0)[label],port=0)
            run_frames_exact(m,2)
            # Borrowed graphics storage ends before immutable source physics.
            # Returning worker code and adjacent bytes must
            # survive every composition, including large IDLE bounding boxes.
            fence_regions=(('physics','SnesSaveRam',0x2d800,2048),('worker_code','Sa1InternalRam',0x200,512),('graphics_end','SnesSaveRam',0x2d700,256))
            fences={name:m.read_memory(kind,at,n) for name,kind,at,n in fence_regions}
            if i==0:(native/'initial-vram.bin').write_bytes(m.read_memory('SnesVideoRam',0,65536))
            m.write_u16(REQUEST,0xb4e7 if i==0 else 0xb4e8)
            for fields in range(1,501):
                run_frames_exact(m,1)
                if startup.u16(m,0x7ffb84):
                    (native/'fault-state.json').write_text(json.dumps(m.get_cpu_state(),indent=2))
                    (native/'fault-snapshot.bin').write_bytes(m.read_memory('SnesMemory',SNAPSHOT,146))
                    raise ValueError('ONLINE_NATIVE_REJECTION:'+str(i))
                if startup.u16(m,READY)==0xb4b8 and startup.u16(m,DISPLAY_EPOCH)==i:break
            else:
                (native/'fault-state.json').write_text(json.dumps(m.get_cpu_state(),indent=2))
                raise ValueError('ONLINE_PUBLICATION_TIMEOUT:'+str(i))
            run_frames_exact(m,2)
            snapshot=m.read_memory('SnesMemory',SNAPSHOT,146)
            path=native/f'world-{i:02d}.bin';path.write_bytes(snapshot)
            scene=scene_from_snapshot(snapshot,source)
            # Golden composition occurs AFTER native generation and publication.
            expected,metadata=compose_rgb8(source,'DATA/LEVELS/GUILE2.TXT',scene)
            expected=rgb555(expected).astype('<u2');(native/f'expected-{i:02d}.rgb555').write_bytes(expected.tobytes())
            shot=m.tool('take_screenshot',{'format':'path'});dest=native/f'display-{i:02d}.png';shutil.copyfile(shot['path'],dest)
            actual=rgb555(np.asarray(Image.open(dest).convert('RGB')))
            mismatches=int(np.count_nonzero(actual!=expected)) if actual.shape==expected.shape else None
            vram=m.read_memory('SnesVideoRam',0,65536);cgram=m.read_memory('SnesCgRam',0,512)
            fence_checks={name:fences[name]==m.read_memory(kind,at,n) for name,kind,at,n in fence_regions}
            if not all(fence_checks.values()):raise ValueError('ONLINE_RESOURCE_FENCE:'+str(fence_checks))
            (native/f'vram-{i:02d}.bin').write_bytes(vram)
            (native/f'cgram-{i:02d}.bin').write_bytes(cgram)
            if contract.get('warm_residency'):
                directory=m.read_memory('SnesSaveRam',0x2d000,1536);(native/f'directory-{i:02d}.bin').write_bytes(directory)
                words=np.frombuffer(directory,dtype='<u2');maps=np.frombuffer(vram[0xf000:0xf800],dtype='<u2')
                if not np.array_equal(words&0x3fff,np.bincount(maps,minlength=768)):raise ValueError('WARM_DIRECTORY_REFERENCE_FAULT')
                authority=Path('out/byor-motu-online-v3/assets');high=(authority/'high.chr').read_bytes();low=(authority/'low.chr').read_bytes()
                for slot in range(len(high)//64):
                    if not words[slot]&0x8000 and (vram[slot*64:slot*64+64]!=high[slot*64:slot*64+64] or vram[0xc000+slot*16:0xc000+slot*16+16]!=low[slot*16:slot*16+16]):raise ValueError('WARM_HOME_IDENTITY_FAULT')
            sample=dict(label=label,epoch=i,snapshot=str(path),sha256=sha(snapshot),raw_controller=startup.u16(m,sy['SourceInputController_Raw1']),
                x_q16=struct.unpack_from('<i',snapshot,52)[0],z_q16=struct.unpack_from('<i',snapshot,60)[0])
            samples.append(sample)
            observations.append(dict(**sample,actor_pointer=struct.unpack_from('<I',snapshot)[0],scene=scene,
                pixel_mismatches=mismatches,pixels=int(expected.size),changed_pixels=int(np.count_nonzero(expected!=last)) if last is not None else 0,
                expected_sha256=sha(expected.tobytes()),vram_sha256=sha(vram),palette_sha256=sha(cgram),
                resource_fences=fence_checks,
                descriptor_sha256=sha(m.read_memory('SnesMemory',0x42c000,2048)),dirty_tiles=struct.unpack('<H',m.read_memory('SnesMemory',0x343a,2))[0],
                displayed_epoch=startup.u16(m,DISPLAY_EPOCH),publication_wait_fields=fields))
            (native/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
            if mismatches!=0:
                (native/'ppu-state.json').write_text(json.dumps(m.get_ppu_state(),indent=2))
                raise ValueError('ONLINE_PIXEL_MISMATCH:'+str(i)+':'+str(mismatches))
            last=expected
            print(f'ONLINE epoch={i} {label} x={sample["x_q16"]/65536} z={sample["z_q16"]/65536} dirty={observations[-1]["dirty_tiles"]} fields={fields} pixels={expected.size} mismatch={mismatches}',flush=True)
        # Actual source left input changes direction to unsupported flipped art.
        # Preflight rejects it before any PPU/CHR mutation; foreground owner stays.
        before=m.read_memory('SnesVideoRam',0,65536);old=startup.u16(m,DISPLAY_EPOCH)
        m.hold_input(m.BTN_LEFT,port=0);run_frames_exact(m,2);m.write_u16(REQUEST,0xb4e8);run_frames_exact(m,4)
        rejected=startup.u16(m,0x7ffb84)==1 and startup.u16(m,DISPLAY_EPOCH)==old
        rejected_world=m.read_memory('SnesMemory',SNAPSHOT,146);(native/'rejected-world.bin').write_bytes(rejected_world)
        unchanged=before==m.read_memory('SnesVideoRam',0,65536)
        (native/'rejected-vram.bin').write_bytes(m.read_memory('SnesVideoRam',0,65536))
        rejected_controller=startup.u16(m,sy['SourceInputController_Raw1'])
        shot=m.tool('take_screenshot',{'format':'path'});shutil.copyfile(shot['path'],native/'rejected.png')
        retained=np.array_equal(rgb555(np.asarray(Image.open(native/'rejected.png').convert('RGB'))),last)
        m.release_input(port=0)
    motion=check_motion(samples)
    log=(native/'mesen.log').read_text(errors='replace')
    events=[]
    for line in log.splitlines():
        if 'ONLINE|' in line:
            pieces=line.split('ONLINE|',1)[1].split('|')
            if len(pieces)>=4:events.append(dict(phase=pieces[0],clock=int(pieces[1]),field=int(pieces[2]),line=int(pieces[3])))
    (native/'timing-events.json').write_text(json.dumps(events,indent=2)+'\n')
    helpers=[];packets=[];epoch=-1
    for line in log.splitlines():
        if 'ONLINE|OnlinePublish|' in line:epoch+=1
        if 'ONLINE_HELPERS|' in line:
            values=list(map(int,line.split('ONLINE_HELPERS|',1)[1].split('|')))
            helpers.append(dict(epoch=epoch,coverage_kind='source_occupancy' if contract.get('occupancy_preflight') else 'foreground_row_scan',coverage_calls=values[0],coverage_clocks=values[1],kernel_calls=values[2],kernel_clocks=values[3]))
        if 'ONLINE_PACKET|' in line:
            values=line.split('ONLINE_PACKET|',1)[1].split('|')
            packets.append(dict(epoch=epoch,target=int(values[0]),vram_word=int(values[1]),source=int(values[2]),bytes=int(values[3]),payload=values[4] if len(values)>4 else ''))
    (native/'dma-packets.json').write_text(json.dumps(packets,indent=2)+'\n')
    from m4_online_component_evidence import costs,verify
    result=dict(schema='BYOR_MOTU_ONLINE_COMPONENT_NATIVE_V1',status='PASS',classification='BYOR_MOTU_ONLINE_COMPONENT_PASS',
        source_pak_sha256=sha(source.path.read_bytes()),candidate=str(native/'bor.sfc'),rom_sha256=sha((native/'bor.sfc').read_bytes()),
        observations=observations,verified_epochs=len(observations),verified_pixels=sum(r['pixels'] for r in observations),pixel_mismatches=0,
        negative=dict(rejected=rejected,vram_unchanged=unchanged,previous_display_retained=retained,world_snapshot_sha256=sha(rejected_world),raw_controller=rejected_controller),
        independent_movement_checks=motion,unsafe_register_writes=log.count('ONLINE_UNSAFE|'),contract=contract,
        measured_costs=costs(events),helper_measurements=helpers,resource_faults=log.count('ONLINE_RESOURCE_FAULT|'))
    if not rejected or not unchanged or not retained or result['unsafe_register_writes'] or result['resource_faults']:raise ValueError('ONLINE_RETENTION_OR_UNSAFE_PPU_WRITE')
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    result['independent_evidence']=verify(folder,source)
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--build-only',action='store_true');p.add_argument('--run-existing',action='store_true');a=p.parse_args()
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);source=Source(a.source);sy=symbols(Path('src/main.sym'))
    if not a.run_existing:
        assets=folder/'assets';derive(source,'DATA/LEVELS/GUILE2.TXT',assets)
        base=folder/'base';base.mkdir(exist_ok=True)
        import build_rom
        with patch.object(build_rom,'assemble',return_value=None):baseline=build_rom.link_rom()
        (base/'bor.sfc').write_bytes(baseline)
        if not(base/'bor.msu').exists():
            media=Path('out/byor-motu-player-controller-native/bor.msu').resolve()
            try:os.link(media,base/'bor.msu')
            except OSError as exc:
                if getattr(exc,'winerror',None)!=1142:raise
                shutil.copyfile(media,base/'bor.msu')
        native=folder/'native';native.mkdir(exist_ok=True)
        args=[sys.executable,'tools/verify/m4_animation_callback_owner_native.py','--source',str(a.source.resolve()),'--rom',str(base/'bor.sfc'),'--output',str(native)]
        args+=['--'+n for n in ('effects-runner','frame-owner','initial-select','default-owner','ctor-owner','ctor-state','ctor-factors','ctor-model','script-clone','player-state-birth','run-tuple-birth','ground-walk','live-ground','live-ground-display','live-ground-online','emit-only')]
        subprocess.run(args,check=True)
        rom,contract=build((native/'bor.sfc').read_bytes(),sy,native,assets);(native/'bor.sfc').write_bytes(rom)
        (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    else:contract=json.loads((folder/'contract.json').read_text())
    if not a.build_only:run(folder,source,sy,contract)


if __name__=='__main__':main()
