"""Serial diagnostic capture of the private source-clock world owner.

Run only inside the shared emulator lease and a contained Windows Job Object.
The retained fixture installs immutable source inputs once before constructor
entry. All later instrumentation is read-only; physical input is the only
driver after that entry. A pending provider is reported, never acknowledged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observer(folder, contract):
    old = Path('out/byor-motu-online-v3/native/callback_owner.lua').read_text()
    from actor_s5_entity_fixture import symbols
    init = symbols(Path('out/byor-motu-online-v3/native/callback_fixture.sym'))['CallbackFixture_Init']
    end = re.search(r'end,emu.callbackType.exec,' + str(init) + ',' + str(init) +
                    r',emu.cpuType.snes,mt\)', old)
    if not end:
        raise ValueError('LIVE_WORLD_BOOTSTRAP_BOUNDARY')
    bootstrap = old[:end.end()] + '\n'
    # Exactly one preconstructor callback; no old movement/scripted test hooks.
    if bootstrap.count('emu.addMemoryCallback') != 1:
        raise ValueError('LIVE_WORLD_BOOTSTRAP_CALLBACK_COUNT')
    sy = contract['symbols']
    fields = ('SourceClock4086_TimeLo', 'SourceClock4086_Due',
              'VmSourceWorld_Time', 'SourceWorldTick4086_State',
              'SourceWorldTick4086_Phase', 'SourceWorldTick4086_Pending',
              'SourceWorldTick4086_Fault', 'SourceWorldTick4086_Slot')
    source = bootstrap + '''
local liveEvents=0
local liveTruncated=false
local function liveLog(name)
 if liveEvents>=20000 then
  if not liveTruncated then emu.log('LIVETRUNCATED|20000');liveTruncated=true end
  return
 end
 liveEvents=liveEvents+1
 local s=emu.getState()
 local v={name,s['masterClock'],s['ppu.frameCount']}
'''
    source += '\n'.join(f' v[#v+1]=word({sy[n]})' for n in fields)
    source += "\n v[#v+1]=dw(0x414034);v[#v+1]=word(0x416814);v[#v+1]=word(0x416818)\n"
    source += " v[#v+1]=word(0x7e7702);v[#v+1]=word(0x7e770c)\n v[#v+1]=s['cpu.a'];v[#v+1]=s['cpu.ps']\n emu.log('LIVE|'..table.concat(v,'|'))\nend\n"
    names = ['LiveWorld_WaitLegacy','LiveWorld_LegacyDrained',
             'LiveWorld_PreConstructor', 'LiveWorld_AcquireRejected',
             'LiveWorld_ConstructorAudio','LiveWorld_ConstructorAudioPending',
             'LiveWorld_Boot', 'LiveWorld_ColdPublished', 'LiveWorld_ColdFailed',
             'LiveWorld_Start', 'LiveWorld_BeginTick', 'LiveWorld_TickStarted', 'LiveWorld_TickCommitted',
             'LiveWorld_SnapshotSealed', 'LiveWorld_Pending', 'LiveWorld_Fault',
             'LiveWorld_ProviderFault', 'LiveHealth_Pending', 'LiveHealth_Fault',
             'LiveGroundPost_Pending', 'LiveGroundPost_Bad', 'CallbackFixture_Bad',
             'LiveWork_Bad','LiveWork_OwnerBad']
    names += [n for n in sy if n.startswith('LiveWorldDispatch_Ack_')]
    names += [n for n in sy if n in ('SourceCtorOwner4086_Continue',
              'SourceCtorOwner4086_Done','SourceCtorOwner4086_Result','SourceClock4086_Commit')]
    names += [n for n in sy if n in ('LiveFrameAudio_Admit','LiveFrameAudio_Complete',
              'LiveFrameAudio_Fault','LiveAudio_HdmaMaskFault','LiveAudio_PumpRetire',
              'SourceFrameEffectPlan4086_Ack','LiveWorld_ColdFailed')]
    names += [n for n in sy if n.startswith('LiveGroundPost_') and
              (n.endswith('_Bad') or n.endswith('_RestoreBad'))]
    # A real rejected guard identifies its exact provider. These observers do
    # not execute, bypass, repair or acknowledge any source operation.
    names += [n for n in sy if n.endswith('_Bad') and n.startswith(('Source', 'Foreign', 'Player', 'Ground', 'Flat', 'TimedWorldGeometry_'))]
    for name in dict.fromkeys(names):
        if name not in sy:
            continue
        at = sy[name]
        source += f"emu.addMemoryCallback(function()liveLog('{name}')end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,mt)\n"
        if name.startswith('TimedWorldGeometry_') and name.endswith('_Bad'):
            source += f'''emu.addMemoryCallback(function()
 local trace=emu.getTraceLog(16,emu.cpuType.snes)
 for _,row in ipairs(trace) do
  emu.log('LIVEBADTRACE|{name}|'..row.pc..'|'..row.text)
 end
end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,mt)
'''
    if contract['config'].get('audio'):
        source+='local liveColdFinished=false\nlocal audioEvents=0\n'
        for name in ('LiveFrameAudio_Admit','LiveFrameAudio_Complete','LiveFrameAudio_Fault',
                     'SourceFrameEffectPlan4086_Ack','LiveWorld_Boot',
                     'LiveWorld_ColdPublished','LiveWorld_Start','LiveAudio_PumpChannelActive'):
            if name not in sy:continue
            at=sy[name]
            source+='emu.addMemoryCallback(function()\n'
            if name=='LiveWorld_ColdPublished':source+='liveColdFinished=true\n'
            source+=f'''if audioEvents<200 then
 audioEvents=audioEvents+1
 local s=emu.getState()
 emu.log('LIVEAUDIO|{name}|'..s['masterClock']..'|'..s['ppu.frameCount']..'|'..s['cpu.a']..'|'..word({sy['SourceFrameEffectPlan4086_Service']})..'|'..word({sy['SourceFrameEffectPlan4086_Acknowledged']})..'|'..word({sy['SourceAudio_Status']})..'|'..word(0x7e8102)..'|'..word(0x7e82f8))
end
end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,mt)
'''
        source+='''emu.addMemoryCallback(function(a,v)
 if word(0x7ffb88)==0xb6d0 and not liveColdFinished then
  local s=emu.getState()
  emu.log('LIVEAUDIOEARLYFAULT|'..a..'|'..v..'|'..s['masterClock'])
 end
end,emu.callbackType.write,0x2140,0x2143,emu.cpuType.snes,mt)
'''
    original=symbols(Path('out/byor-motu-online-v3/native/callback_fixture.sym'))
    publisher=symbols(Path('out/byor-motu-abort-copy-v1/success/native/publisher.sym'))
    for name in ('OnlineReject','OnlinePublish','OnlinePublished'):
        if name in publisher:
            at=publisher[name]
            source+=f"emu.addMemoryCallback(function()liveLog('Publisher_{name}')end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,mt)\n"
    for name,at in original.items():
        if name.startswith('CallbackFixture_') and ('Branch' not in name):
            source+=f"emu.addMemoryCallback(function()liveLog('Original_{name}')end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,mt)\n"
    at=sy['LiveWorld_SnapshotSealed']
    source+=f'''emu.addMemoryCallback(function()
 local sealed={{}};local current={{}}
 for i=0,143 do
  sealed[#sealed+1]=string.format('%02x',emu.read(0x7e7800+i,mt))
  current[#current+1]=string.format('%02x',emu.read(i<80 and 0x414000+i or 0x416800+i-80,mt))
 end
 emu.log('LIVESC|'..word(0x7e7890)..'|'..table.concat(sealed)..'|'..table.concat(current))
end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,mt)
'''
    flags=('SceneVideo_TestActive','SceneVideo_TestRequest','SceneVideo_PlayState',
           'SceneVideo_SequenceActive','SceneVideo_SkipPending','StageFp_BG2Loaded',
           'StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting',
           'StreamScrollFp_ColPending','StreamScrollFp_Enabled','StageWater_Enabled',
           'StageWater_Pending','StageWater_Held','Msu1_StreamBusy')
    at=sy['LiveWorld_PreConstructor']
    source+='emu.addMemoryCallback(function()local v={}\n'
    for name in flags:
        source+=f"v[#v+1]='{name}='..emu.read({sy[name]},mt)\n"
    source+="for i=0,7 do v[#v+1]='dma'..i..'='..emu.read(0x7e0484+8*i,mt)end\n"
    source+=f"emu.log('LIVEACQ|'..table.concat(v,'|'))end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,mt)\n"
    # Observe physical BW-RAM, including alternate CPU aliases. Only the
    # unchanged accepted publisher may write its protected maps/ref/queue.
    # A full emu.getState serializes the whole console. Doing that per copied
    # byte exceeded the unchanged exact-frame wall cap. The instruction trace
    # supplies the executing PC; independently cross-check its bank on the
    # first 64 and every 1024th write, and for every unexpected/absent PC.
    source+='local liveWriteCount=0;local liveWriteChecks=0;local liveTraceEmpty=0\n'
    source+='emu.getTraceLog(1,emu.cpuType.snes)\n'
    for cpu in ('snes','sa1'):
        source+=f'''emu.addMemoryCallback(function(a,v)
 if word(0x7ffb88)~=0xb6d0 then return end
 liveWriteCount=liveWriteCount+1
 local trace=emu.getTraceLog(1,emu.cpuType.{cpu})
 local pc=trace[1] and trace[1].pc or nil
 if not pc then liveTraceEmpty=liveTraceEmpty+1 end
 if not pc or liveWriteCount<=64 or liveWriteCount%1024==0 or (pc>>16)~=0x39 or '{cpu}'~='snes' then
  local s=emu.getState();local actual=s['cpu.pc']+65536*s['cpu.k']
  liveWriteChecks=liveWriteChecks+1
  if pc and '{cpu}'=='snes' and (pc>>16)~=(actual>>16) then
   emu.log('LIVEOWNTRACEFAULT|'..pc..'|'..actual)
  end
  pc=actual
 end
 if '{cpu}'~='snes' or (pc>>16)~=0x39 then
  emu.log('LIVEOWNFAULT|renderer|{cpu}|'..a..'|'..pc)
 end
end,emu.callbackType.write,0x2c000,0x2d7ff,emu.cpuType.{cpu},emu.memType.snesSaveRam)
'''
    source+='''emu.addEventCallback(function()
 if word(0x7ffb88)==0xb6d0 then
  emu.log('LIVEOWNCOUNTS|'..liveWriteCount..'|'..liveWriteChecks..'|'..liveTraceEmpty)
 end
'''
    if contract['config'].get('audio'):
        # Pause on the emulation thread after each completed live field. The
        # host's 2-ms poll cannot advance a second field before Pause arrives.
        # This changes no emulated memory, input, source time or instructions.
        # Restrict it to the physical owner, whose WAI has real NMI/IRQ wakes.
        source+=''' if word(0x7ffb88)==0xb6d0 and word(0x7e8100)==0xb6d8 and emu.read(0x7e8102,mt)==1 then
  emu.breakExecution()
 end
'''
    source+='''
end,emu.eventType.endFrame)
'''
    target = folder / 'live-world-observer.lua'
    target.write_text(source)
    return target, dict(preconstructor_callback_count=1,
                        retained_bootstrap_sha256=hashlib.sha256(bootstrap.encode()).hexdigest(),
                        observer_sha256=digest(target), later_debugger_writes=False,
                        physical_end_frame_pause=bool(contract['config'].get('audio')),
                        writer_pc='opcode trace; full-state bank cross-check first64/every1024/absent-or-unexpected')


def capture(build, folder, fields):
    if os.environ.get('BOR_PROBE_JOB_REQUIRED') != '1':
        raise ValueError('LIVE_WORLD_CONTAINED_WORKER_REQUIRED')
    folder = folder.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    contract = json.loads((build / 'contract.json').read_text())
    assert digest(build / 'bor.sfc') == contract['rom_sha256']
    mesen_source = os.environ.get('MESEN_EXE')
    mesen_python = os.environ.get('MESEN_PYTHON_PATH')
    if not mesen_source or not Path(mesen_source).is_file():
        raise ValueError('LIVE_WORLD_CONFIGURE_MESEN_EXE')
    if not mesen_python or not (Path(mesen_python)/'mesen_mcp/session.py').is_file():
        raise ValueError('LIVE_WORLD_CONFIGURE_MESEN_PYTHON_PATH')
    sys.path.insert(0, str(Path(mesen_python).resolve()))
    import m4_eight_pair_native as runtime
    exe = runtime.prepare_capture_runtime(folder / 'capture-runtime',mesen_source)
    os.environ['MESEN_EXE'] = str(exe)
    import _harness
    from mesen_mcp.session import McpSession
    import mesen_mcp.session as actual
    assert Path(actual.__file__).resolve() == (Path(mesen_python)/'mesen_mcp/session.py').resolve()
    assert hasattr(McpSession, 'hold_input')
    from _harness import Reporter, exact_input_edge, run_frames_exact, _free_tcp_port
    import game_bor_startup_select as startup
    script, observer_report = observer(folder, contract)
    launches = []

    class Observed(McpSession):
        def __enter__(self):
            import ctypes
            def launch(argv, **kwargs):
                return subprocess.Popen([*argv, '--donotsavesettings', str(script)], **kwargs)
            with patch.object(actual, 'subprocess', SimpleNamespace(Popen=launch,
                    DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE)):
                result = super().__enter__()
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            query = kernel.QueryFullProcessImageNameW
            query.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_wchar_p,
                              ctypes.POINTER(ctypes.c_uint32)]
            query.restype = ctypes.c_int
            buffer = ctypes.create_unicode_buffer(32768)
            length = ctypes.c_uint32(len(buffer))
            assert query(ctypes.c_void_p(int(self._proc._handle)), 0, buffer, ctypes.byref(length))
            assert Path(buffer.value).resolve() == exe.resolve()
            launches.append(dict(pid=self._proc.pid, actual_executable=buffer.value,
                                 argv=self._proc.args))
            (folder / 'actual-launches.json').write_text(json.dumps(launches, indent=2)+'\n')
            return result

    progress = []; visible=[]; expected=None; pinned_initial=None
    audio_config=contract['config'].get('audio')
    audio_progress=[];packets=[];previous_chunks=0
    if audio_config:
        raw=(build/'bor.sfc').read_bytes()
        audio_payload=raw[audio_config['payload_cpu']-0xc00000:
                          audio_config['payload_cpu']-0xc00000+audio_config['payload_bytes']]
        os.environ.update(MESEN_VOICE_CAPTURE_PATH=str(folder/'voice0.raw'),
                          MESEN_VOICE_CAPTURE_VOICE='0',
                          MESEN_VOICE_CAPTURE_ARM_FILE=str(folder/'voice0.raw.arm'))
    sy = contract['symbols']
    with Observed(rom=build/'bor.sfc', mesen=exe, port=_free_tcp_port(),
                  stderr_log=folder/'mesen.log') as m:
        m.write_u16(0x7ffb96, 0)
        m.write_u16(0x7ffb88, 0)
        reporter = Reporter('MOTU-LIVE-WORLD-BOOT', kind='GATE')
        with patch.object(m, 'reset_emulator', return_value=None):
            startup.cold_to_title(m, reporter)
        startup.title_to_charselect(m)
        exact_input_edge(m, m.BTN_START, 1, port=0)
        if not startup.wait_state(m, startup.PLAYING, 300):
            raise ValueError('LIVE_WORLD_ORIGINAL_BOOTSTRAP')
        run_frames_exact(m, 12)
        # Existing foreign owner activation; retire original layer producers
        # before the constructor/lease. No actor/time/phase writes thereafter.
        for name in ('StageWater_Enabled','StageWater_Pending','StageFp_BG2Loaded',
                     'StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting',
                     'StreamScrollFp_ColPending','StreamScrollFp_Enabled'):
            m.write_u8(sy[name], 0)
        m.hold_input(0, port=0)
        run_frames_exact(m, 2)
        if audio_config:
            (folder/'voice0.raw.arm').touch()
            m.record_audio(folder/'source-audio.wav')
        m.write_u16(0x7ffb80, 0xb4e7)
        for index in range(fields):
            try:
                run_frames_exact(m, 1)
            except BaseException as error:
                cpu=m.get_cpu_state()
                pc=cpu.get('pc',0)+65536*cpu.get('k',0)
                diagnostic=dict(error=str(error),cpu=cpu,state=m.get_state(),
                    code=m.read_memory('SnesMemory',pc,32).hex(),
                    runtime=m.read_memory('SnesMemory',0x7e7700,128).hex(),
                    pinned=m.read_memory('SnesMemory',0x7fba00,146).hex())
                (folder/'stalled-field.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
                raise
            work = m.read_memory('SnesMemory', 0x7e7680, 0x140)
            state = m.get_state()
            progress.append(dict(index=index, state=state, health_work=work[:128].hex(),
                                 runtime_work=work[128:256].hex(),
                                 clock_control=m.read_memory('SnesMemory',sy['SourceClock4086_Ready'],64).hex(),
                                 world_control=m.read_memory('SnesMemory',sy['SourceWorldTick4086_Ready'],64).hex(),
                                 frame_owner=m.read_memory('SnesMemory',
                                     sy['SourceUpdateFrame4086_Ready'],64).hex(),
                                 effect_plan=m.read_memory('SnesMemory',
                                     sy['SourceFrameEffectPlan4086_Ready'],32).hex()))
            if audio_config:
                transport=m.read_memory('SnesMemory',sy['TadPrivate_stream_frame'],64)
                accepted=int.from_bytes(m.read_memory('SnesMemory',sy['TadPrivate_stream_chunks_accepted'],2),'little')
                for chunk in range(previous_chunks,accepted):
                    aram=sy['TAD_STREAM_RING_ADDR']+(chunk%8)*144
                    actual_packet=m.read_memory('SpcRam',aram,144)
                    expected_packet=bytearray(audio_payload[chunk*144:chunk*144+144])
                    if chunk%8==7 and chunk+1<audio_config['payload_bytes']//144:
                        expected_packet[135]|=3
                    packets.append(dict(chunk=chunk,index=index,aram=aram,
                        observer_gap=accepted-previous_chunks,
                        mismatched_bytes=sum(a!=b for a,b in zip(actual_packet,expected_packet)),
                        actual_sha256=hashlib.sha256(actual_packet).hexdigest(),
                        expected_sha256=hashlib.sha256(expected_packet).hexdigest()))
                previous_chunks=accepted
                audio_progress.append(dict(index=index,frame=state['frameCount'],
                    transport=transport.hex(),chunks_accepted=accepted,
                    control=m.read_memory('SnesMemory',0x7e8100,64).hex(),
                    channel11=m.read_memory('SnesMemory',0x7e8140+440,40).hex(),
                    compact11=m.read_memory('SnesMemory',0x7eff88+88,8).hex(),
                    source_status=int.from_bytes(m.read_memory('SnesMemory',sy['SourceAudio_Status'],2),'little'),
                    channel0_registers=m.read_memory('SnesMemory',0x4300,16).hex(),
                    dma=m.read_dma_state(),
                    voice0=next(v for v in m.get_audio_state()['voices'] if v['voice']==0)))
                (folder/'audio-progress.json').write_text(json.dumps(audio_progress,indent=2)+'\n')
                (folder/'audio-packets.json').write_text(json.dumps(packets,indent=2)+'\n')
            ready=int.from_bytes(m.read_memory('SnesMemory',0x7ffb96,32)[:2],'little')
            if ready==0xb4b8:
                import numpy as np
                from PIL import Image
                from compiler import Source
                from m4_live_ground_component_native import scene_from_snapshot
                from source_scene_bg import compose_rgb8
                from source_bg_feasibility import rgb555
                pinned=m.read_memory('SnesMemory',0x7fba00,146)
                if expected is None:
                    pinned_initial=pinned
                    source=Source('Masters of the Universe [v.3.0 Build 4086].pak')
                    scene=scene_from_snapshot(pinned,source)
                    pixels,_=compose_rgb8(source,'DATA/LEVELS/GUILE2.TXT',scene)
                    expected=rgb555(pixels).astype('<u2')
                    (folder/'pinned-expected.rgb555').write_bytes(expected.tobytes())
                shot=m.take_screenshot();image_path=folder/f'field-{index:04d}.png'
                shutil.copyfile(shot['path'],image_path)
                actual_pixels=rgb555(np.asarray(Image.open(image_path).convert('RGB')))
                exact=actual_pixels.shape==expected.shape and np.array_equal(actual_pixels,expected)
                visible.append(dict(index=index,frame=state['frameCount'],exact=bool(exact),
                     pixels=int(expected.size),pinned_unchanged=pinned==pinned_initial,
                     png_sha256=digest(image_path)))
                (folder/'visible-fields.json').write_text(json.dumps(visible,indent=2)+'\n')
            (folder/'progress.json').write_text(json.dumps(progress, indent=2)+'\n')
            if work[130:132] == b'\x03\x00' and (not audio_config or
                    m.read_memory('SnesMemory',0x7e8102,1)==b'\0'):
                break
        for name, at, size in [('latest',0x7e7800,146),('pinned',0x7fba00,146),
                              ('clock',sy['SourceClock4086_Ready'],64),
                              ('world',sy['SourceWorldTick4086_Ready'],64),
                              ('post-control',0x40bfe0,32),('physics-query',0x41ff00,104),
                              ('frame-owner',sy['SourceUpdateFrame4086_Ready'],64),
                              ('effect-plan',sy['SourceFrameEffectPlan4086_Ready'],32),
                              ('actor',0x414000,80),('side',0x416800,64)]:
            (folder/(name+'.bin')).write_bytes(m.read_memory('SnesMemory',at,size))
        shot=m.take_screenshot()
        if 'path' in shot:
            shutil.copyfile(shot['path'],folder/'last.png')
        (folder/'screenshot-result.json').write_text(json.dumps(shot,indent=2)+'\n')
        m.release_input(port=0)
    events=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        if 'LIVE|' not in line:
            continue
        name,*numbers=line.split('LIVE|',1)[1].split('|')
        events.append(dict(name=name, values=[int(v) for v in numbers]))
    commits=[e for e in events if e['name']=='LiveWorld_TickCommitted']
    ticks=[];begin=None
    for e in events:
        if e['name']=='LiveWorld_BeginTick':begin=e
        elif e['name']=='LiveWorld_TickCommitted' and begin:
            ticks.append(dict(source_time=begin['values'][2],
                master_clocks=e['values'][0]-begin['values'][0],
                fields=e['values'][1]-begin['values'][1],
                time_after=e['values'][2],world_after=e['values'][4]))
            begin=None
    sealed=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        if 'LIVESC|' in line:
            epoch,snapshot,current=line.split('LIVESC|',1)[1].split('|')
            sealed.append(dict(epoch=int(epoch),coherent=snapshot==current,
                               sha256=hashlib.sha256(bytes.fromhex(snapshot)).hexdigest()))
    ownership_faults=[line.split('LIVEOWNFAULT|',1)[1] for line in
                     (folder/'mesen.log').read_text().splitlines() if 'LIVEOWNFAULT|' in line]
    trace_faults=[line.split('LIVEOWNTRACEFAULT|',1)[1] for line in
                  (folder/'mesen.log').read_text().splitlines() if 'LIVEOWNTRACEFAULT|' in line]
    report=dict(schema='BYOR_LIVE_WORLD_NATIVE_DIAGNOSTIC_V1',
        status='COMPLETE_TICK_OBSERVED' if commits else 'NO_COMPLETE_TICK',
        rom_sha256=contract['rom_sha256'], accepted_renderer_bank_unchanged=contract['renderer_bank_unchanged'],
        observer=observer_report, launches=launches, events=events,
        event_log_truncated='LIVETRUNCATED|' in (folder/'mesen.log').read_text(),
        ticks=ticks,sealed_snapshots=sealed,visible_fields=visible,
        protected_renderer_write_faults=ownership_faults,
        protected_renderer_trace_faults=trace_faults,
        complete_ticks_observed=len(commits),fields_requested=fields,fields_captured=len(progress),
        unsupported_providers_remain_pending=True, presentation_joined=False,
        game_or_200hz_cadence_or_30fps_not_claimed=True)
    (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','complete_ticks_observed','fields_captured')}),flush=True)


if __name__ == '__main__':
    if os.environ.get('BOR_PROBE_JOB_REQUIRED') == '1':
        print(json.dumps(dict(kind='BOR_PROBE_JOB_HELLO',pid=os.getpid(),
              parent_pid=os.getppid(),image=sys._base_executable)),flush=True)
        assert sys.stdin.buffer.read(1)==b'G'
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--fields',type=int,default=100)
    args=p.parse_args()
    capture(args.build.resolve(),args.output,args.fields)
