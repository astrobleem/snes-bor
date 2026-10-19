"""Strict one-field host stepping with complete read-only native field records.

The Lua observer compares every RGB24 element. Unchanged images reference a
previous complete image only after exact equality; changed images are lossless
RLE. Calibration PNGs independently check the native buffer against the MCP
screenshot API. This is an opt-in diagnostic, never a relaxed frame step.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from m4_warm_world_capture import _observer, _parse_events, load_input_script, BUTTONS, analyze, digest
from warm_field_pixels import lua_observer, parse_log
from warm_field_state import observer as state_observer, decode as decode_state


def materialize(build,folder,host_rows):
    """Validate exact native/host joins and reconstruct retained image evidence."""
    import numpy as np
    from PIL import Image
    contract=json.loads((build/'contract.json').read_text())
    text=(folder/'mesen.log').read_text(errors='replace')
    events=_parse_events(folder/'mesen.log')
    host_frames=[r['frame']for r in host_rows]
    if not host_frames or any(b!=a+1 for a,b in zip(host_frames,host_frames[1:])):
        raise ValueError('FAST_HOST_FRAME_SEQUENCE')
    starts=[e['frame']for e in events['field_events']if host_frames[0]<=e['frame']+1<=host_frames[-1]]
    if not starts:raise ValueError('FAST_NO_OWNED_FIELD')
    expected=list(range(min(starts),host_frames[-1]))
    if starts!=expected:raise ValueError('FAST_OWNER_FIELD_COVERAGE')
    allowed=set(expected)
    field_lines=[];pixel_lines=[]
    for line in text.splitlines():
        if 'WARMFIELDDATA|'in line:
            frame=int(line.split('WARMFIELDDATA|',1)[1].split('|')[0])
            if frame in allowed:field_lines.append(line)
        elif 'WARMARMPACKET|'in line:
            frame=int(line.split('WARMARMPACKET|',1)[1].split('|')[1])
            if frame in allowed:field_lines.append(line)
        elif 'WARMFIELDAUDIOFAULT|'in line:field_lines.append(line)
        for tag in ('WARMPIXFULL|','WARMPIXREF|'):
            if tag in line:
                frame=int(line.split(tag,1)[1].split('|')[1],16)
                if frame in allowed:pixel_lines.append(line)
    cfg=contract['config']['audio'];raw=(build/'bor.sfc').read_bytes()
    payload=raw[cfg['payload_cpu']-0xc00000:cfg['payload_cpu']-0xc00000+cfg['payload_bytes']]
    data=decode_state('\n'.join(field_lines),expected,contract,payload)
    clocks=[r['master_clock']for r in data['progress']]
    if any(b<=a for a,b in zip(clocks,clocks[1:])):
        # Mesen's Lua GetState masterClock is uint32. A wrapped observation
        # cannot authorize a prior-publication or VBlank timing comparison.
        raise ValueError('FAST_NATIVE_FIELD_CLOCK_ORDER_OR_WRAP')
    if data['audio_faults']:raise ValueError('FAST_NATIVE_AUDIO_OBSERVER_FAULT:'+repr(data['audio_faults']))
    if data['audio_packet_mismatches']:
        raise ValueError('FAST_NATIVE_AUDIO_PACKET_MISMATCH:'+str(data['audio_packet_mismatches']))
    pixels=parse_log(pixel_lines,expected_ordinals=range(1,len(expected)+1))
    by_frame={p.ppu_frame:p for p in pixels.values()}
    if list(by_frame)!=expected:raise ValueError('FAST_PIXEL_FIELD_JOIN')
    native={r['frame']+1:r for r in data['progress']}
    pngs={};calibration=[];progress=[]
    for host in host_rows:
        if host['frame']not in native:
            if host['frame']>=expected[0]+1:raise ValueError('FAST_MISSING_NATIVE_FIELD')
            progress.append(dict(**host,constructor_ready=False,alias_fault=None,sticky_fault=None,
                                 capture_evidence='pre_owner_no_native_data'))
            continue
        row=native[host['frame']];native_frame=row['frame'];row['frame']=host['frame']
        p=by_frame[native_frame]
        if p.full_ordinal not in pngs:
            packed=np.asarray(p.pixels,dtype=np.uint32).reshape(p.height,p.width)
            rgb=np.stack(((packed>>16)&255,(packed>>8)&255,packed&255),axis=2).astype(np.uint8)
            path=folder/f'native-pixels-{p.full_ordinal:05d}.png'
            Image.fromarray(rgb).save(path)
            pngs[p.full_ordinal]=dict(path=path,rgb=rgb,sha256=digest(path))
        image=pngs[p.full_ordinal]
        if host.get('calibration_png'):
            actual=np.asarray(Image.open(folder/host['calibration_png']).convert('RGB'))
            exact=actual.shape==image['rgb'].shape and np.array_equal(actual,image['rgb'])
            calibration.append(dict(index=host['index'],frame=host['frame'],exact_rgb24=bool(exact),
                                    png=host['calibration_png'],native_full_ordinal=p.full_ordinal))
            if not exact:raise ValueError('FAST_PIXEL_MCP_CALIBRATION:'+str(host['index']))
        row.update(index=host['index'],frames_advanced=host['frames_advanced'],
                   scripted_input=host.get('scripted_input'),capture_evidence='native_complete_field',
                   mcp_constructor_ready=None,mcp_display_pin_hex=None,mcp_cold_pin_hex=None,
                   png=image['path'].name,png_sha256=image['sha256'],pixel_ordinal=p.ordinal,
                   pixel_full_ordinal=p.full_ordinal,pixel_exact_reference=p.referenced)
        progress.append(row)
    if not calibration or not any(r['index']==host_rows[-1]['index']for r in calibration):
        raise ValueError('FAST_FINAL_PIXEL_CALIBRATION_REQUIRED')
    for name,value in [('progress',progress),('audio-progress',data['audio_progress']),
                       ('audio-packets',data['packets']),('pixel-calibration',calibration)]:
        (folder/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    (folder/'native-field-schema.json').write_text(json.dumps(state_observer(contract)[1],indent=2)+'\n')
    return dict(fields=len(progress),owned_fields=len(expected),full_rgb24_images=len(pngs),
                exact_reference_fields=sum(p.referenced for p in pixels.values()),
                calibration=calibration,all_owned_fields_have_exact_pixels=True,
                runtime_field_batching_used=False)


def capture(build,folder,fields,input_script=None):
    if os.environ.get('BOR_PROBE_JOB_REQUIRED')!='1':raise ValueError('FAST_CONTAINED_JOB_REQUIRED')
    folder=folder.resolve();folder.mkdir(parents=True,exist_ok=False);build=build.resolve()
    contract=json.loads((build/'contract.json').read_text());sy=contract['symbols']
    if digest(build/'bor.sfc')!=contract['rom_sha256']:raise ValueError('FAST_ROM_SHA')
    source_exe=os.environ['MESEN_EXE'];python_path=Path(os.environ['MESEN_PYTHON_PATH'])
    sys.path.insert(0,str(python_path))
    from m4_eight_pair_native import prepare_capture_runtime
    exe=prepare_capture_runtime(folder/'capture-runtime',source_exe)
    from mesen_mcp.session import McpSession
    import mesen_mcp.session as actual
    from _harness import Reporter,exact_input_edge,run_frames_exact,_free_tcp_port
    import game_bor_startup_select as startup
    script,meta=_observer(folder,contract)
    s=script.read_text().replace('>=20000','>=200000')
    s+='\n'+state_observer(contract)[0]+'\n'+lua_observer()
    script.write_text(s)
    meta.update(final_observer_sha256=digest(script),cap=200000,complete_rgb24=True,
                source_writes_after_activation=False,strict_one_field_steps=True)
    (folder/'observer-report.json').write_text(json.dumps(meta,indent=2)+'\n')
    os.environ.update(MESEN_VOICE_CAPTURE_PATH=str(folder/'voice0.raw'),MESEN_VOICE_CAPTURE_VOICE='0',
                      MESEN_VOICE_CAPTURE_ARM_FILE=str(folder/'voice0.raw.arm'))
    launches=[]
    class Observed(McpSession):
        def __enter__(self):
            def launch(argv,**kw):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kw)
            with patch.object(actual,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                result=super().__enter__()
            kernel=ctypes.WinDLL('kernel32',use_last_error=True);query=kernel.QueryFullProcessImageNameW
            query.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint32)]
            query.restype=ctypes.c_int;buf=ctypes.create_unicode_buffer(32768);length=ctypes.c_uint32(len(buf))
            assert query(ctypes.c_void_p(int(self._proc._handle)),0,buf,ctypes.byref(length))
            assert Path(buf.value).resolve()==exe.resolve()
            launches.append(dict(pid=self._proc.pid,actual_executable=buf.value,argv=self._proc.args))
            (folder/'actual-launches.json').write_text(json.dumps(launches,indent=2)+'\n')
            return result
    actions=load_input_script(input_script,fields);host_rows=[]
    try:
        with Observed(rom=build/'bor.sfc',mesen=exe,port=_free_tcp_port(),stderr_log=folder/'mesen.log')as m:
            m.write_u16(0x7ffb96,0);m.write_u16(0x7ffb88,0)
            with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,Reporter('MOTU-WARM-FAST',kind='GATE'))
            startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
            if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('FAST_BOOTSTRAP')
            run_frames_exact(m,12)
            for n in ('StageWater_Enabled','StageWater_Pending','StageFp_BG2Loaded','StageFp_BG2Active',
                      'StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'):
                m.write_u8(sy[n],0)
            m.hold_input(0,port=0);run_frames_exact(m,2)
            (folder/'voice0.raw.arm').touch();m.record_audio(folder/'source-audio.wav')
            m.write_u16(0x7ffb80,0xb4e7)
            previous_mask=None
            for index in range(fields):
                action=actions.get(index);mask=0
                for b in action['buttons']if action else []:mask|=getattr(m,BUTTONS[b][0])
                if mask!=previous_mask:m.hold_input(mask,port=0);previous_mask=mask
                step=run_frames_exact(m,1);state=m.get_state()
                row=dict(index=index,frame=state['frameCount'],frames_advanced=step['framesAdvanced'],scripted_input=action)
                if index<4 or index==fields-1:
                    path=folder/f'calibration-{index:05d}.png';shutil.copyfile(m.take_screenshot()['path'],path)
                    row['calibration_png']=path.name
                host_rows.append(row)
                if index%64==0 or index==fields-1:
                    (folder/'host-steps.json').write_text(json.dumps(host_rows,indent=2)+'\n')
            m.release_input(port=0)
    except BaseException as error:
        (folder/'capture-error.json').write_text(json.dumps(dict(error=repr(error)),indent=2)+'\n');raise
    proof=materialize(build,folder,host_rows)
    (folder/'fast-field-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    return analyze(build,folder,fields,input_script)


if __name__=='__main__':
    if os.environ.get('BOR_PROBE_JOB_REQUIRED')=='1':
        print(json.dumps(dict(kind='BOR_PROBE_JOB_HELLO',pid=os.getpid(),parent_pid=os.getppid(),image=sys._base_executable)),flush=True)
        assert sys.stdin.buffer.read(1)==b'G'
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--fields',type=int,required=True)
    p.add_argument('--input-script',type=Path);a=p.parse_args()
    if a.fields<=0:p.error('positive fields required')
    capture(a.build,a.output,a.fields,a.input_script)
