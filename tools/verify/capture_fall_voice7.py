#!/usr/bin/env python3
"""Capture the generated sfx_fall resident effect directly on voice 7.

This is a backend/content golden, not a gameplay-semantic test. The gameplay
fixture is intentionally separate so a lower-ID hit cannot replace FALL in
the one-entry TAD queue and yield a false positive.
"""
import hashlib
import json
import os
import sys
import subprocess
import sys
import threading
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MESEN_ROOT = os.environ.get('MESEN_ROOT', r'E:\\gh\\Mesen2-mcp-voice7')
CAPTURE_VOICE = int(os.environ.get('MESEN_VOICE_CAPTURE_VOICE', '7'))
ROM = os.path.join(ROOT, 'distribution', 'bor.sfc')
CAPTURE = os.environ.get('MESEN_VOICE_CAPTURE_PATH',
                         os.path.join(MESEN_ROOT, 'capture-fall-current.raw'))
ARM = os.environ.get('MESEN_VOICE_CAPTURE_ARM_FILE', CAPTURE + '.arm')
CAPTURE_ENV = {
    'MESEN_VOICE_CAPTURE_PATH': os.path.abspath(CAPTURE),
    'MESEN_VOICE_CAPTURE_VOICE': str(CAPTURE_VOICE),
    'MESEN_VOICE_CAPTURE_ARM_FILE': os.path.abspath(ARM),
}
CAPTURE = CAPTURE_ENV['MESEN_VOICE_CAPTURE_PATH']
ARM = CAPTURE_ENV['MESEN_VOICE_CAPTURE_ARM_FILE']
os.makedirs(os.path.dirname(CAPTURE), exist_ok=True)
STDERR_LOG = CAPTURE + '.stderr.log'
for stale in (CAPTURE, CAPTURE + '.json', CAPTURE + '.report.json', ARM):
    try:
        os.unlink(stale)
    except FileNotFoundError:
        pass

sys.path.insert(0, r'E:\\gh\\Mesen2\\python')
from mesen_mcp.session import McpSession
sys.path.insert(0, os.path.dirname(__file__))
import audio_semantic_diesound as semantic
from _harness import open_session

TAD_SFX_QUEUE_SFX = 0x7E0020
TAD_SFX_QUEUE_PAN = 0x7E0021
FALL_LOCAL_ID = 1
GAMEPLAY_MODE = '--gameplay' in sys.argv
NO_REQUEST = os.environ.get('NO_REQUEST') == '1'


def advance_probe_frame(m):
    m.run_frames(1)
    if os.environ.get('CONTINUOUS_FRAMES') != '1':
        m.pause()


class DotnetSession(McpSession):
    def __enter__(self):
        self._proc = subprocess.Popen([
            r'C:\\Users\\chad\\.dotnet\\dotnet.exe',
            os.path.join(MESEN_ROOT, r'bin\\win-x64\\Release\\Nexen.dll'),
            '--mcp', f'--mcp-port={self._port}', ROM,
        ], cwd=os.path.join(MESEN_ROOT, r'bin\\win-x64\\Release'),
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=self._env)
        threading.Thread(target=lambda: self._proc.stderr.read(), daemon=True).start()
        time.sleep(self._boot_wait)
        self._sock = self._connect()
        self.call('initialize', {})
        return self


session = (open_session(__file__, env=CAPTURE_ENV, stderr_log=STDERR_LOG) if os.environ.get('USE_STANDARD_MESEN') == '1'
           else DotnetSession(rom=ROM, mesen='unused', cwd=ROOT, port=7446,
                              boot_wait=2.0))
with session as m:
    semantic.boot(m)
    # Enable the SPC trace before the controlled request.  trace_log is lazy;
    # requesting it only after the event leaves the command path unrecorded.
    m.trace_log(1, 'Spc')
    spc_apu_read_hook = m.add_read_hook(0xF4, 0xF4, cpu_type='Spc')
    spc_apu_write_hook = m.add_write_hook(0xF4, 0xF7, cpu_type='Spc')
    spc_dispatch_hook = m.add_exec_hook(0x08C1, 0x08C1, cpu_type='Spc')
    semantic.clear_observation(m)
    open(ARM, 'wb').close()
    apu_hook = m.add_write_hook(0x002140, 0x002143)
    queue_hook = m.add_write_hook(0x000020, 0x000021)
    spc_port_hook = m.add_write_hook(0x0000F4, 0x0000F7, cpu_type='Spc')
    spc_dsp_hook = m.add_write_hook(0x0000F2, 0x0000F3, cpu_type='Spc')
    spc_unpause_exec = []
    if os.environ.get('FORCE_TAD_UNPAUSE') == '1':
        # The semantic boot fixture can leave the SPC in its reset/paused
        # timer state while the host mirror still says PLAYING.  Use TAD's
        # normal queued UNPAUSE command, never a direct APUIO write.
        unpause_hook = m.add_exec_hook(0x087D, 0x087D, cpu_type='Spc')
        semantic.w8(m, 0x7E003D,
                   int(os.environ.get('FORCE_TAD_COMMAND', '4'), 0))
        semantic.w8(m, 0x7E003E, 0)
        semantic.w8(m, 0x7E003F, 0)
        for _ in range(2):
            advance_probe_frame(m)
        spc_unpause_exec = [n.get('params', {}) for n in m.drain_notifications()]
        m.remove_hook(unpause_hook)
        m.pause()
    if GAMEPLAY_MODE:
        before, after, rows = semantic.fall_target(m)
        print(json.dumps({
            'fixture': 'ordinary-thrown-landing',
            'fall_request_delta': after - before,
            'semantic_trace': rows,
        }, sort_keys=True))
    elif not NO_REQUEST:
        # Normal TAD resident queue path: Tad_Process consumes this queue
        # entry and submits generated local sfx_fall ID. No APUIO bypass.
        semantic.w8(m, TAD_SFX_QUEUE_PAN, 0x40)
        semantic.w8(m, TAD_SFX_QUEUE_SFX, FALL_LOCAL_ID)
    event_audio_state = []
    command_state_timeline = []
    pre_service_host = {
        'host_state': m.read_memory('snesMemory', 0x7E0032, 1)[0],
        'host_previous_command': m.read_memory('snesMemory', 0x7E0035, 1)[0],
        'host_queue': m.read_memory('snesMemory', 0x7E0020, 2).hex(),
        'stream_pending': m.read_memory('snesMemory', 0x7E28B0, 1)[0],
        'spc_ports': m.read_memory('spcMemory', 0x00F4, 4).hex(),
        'spc_previous_command': m.read_memory('spcMemory', 0x01DF, 1).hex(),
    }
    command_trace_snapshot = None
    command_state_snapshot = None
    spc_run_until = None
    spc_handler_state = None
    spc_handler_ram = None
    spc_handler_trace = None
    spc_disassembly = None
    spc_handler_cpu_state = None
    spc_allocator_snapshot = None
    spc_run_until_notifications = []
    all_notifications = []
    spc_hook_diag = None
    for handle in (spc_apu_read_hook, spc_apu_write_hook, apu_hook,
                   queue_hook, spc_port_hook, spc_dsp_hook):
        m.remove_hook(handle)
    spc_run_until = m.run_until(60, spc_dispatch_hook)
    spc_run_until_notifications = m.drain_notifications()
    spc_hook_diag = m.hook_diag()
    if spc_run_until.get('reason') == 'hookFired':
        spc_handler_state = m.get_audio_state()['spc']
        spc_handler_cpu_state = None
        spc_handler_ram = m.read_memory('spcMemory', 0, 512).hex()
        spc_allocator_snapshot = {
            'zp_0c_14': m.read_memory('spcMemory', 0x000C, 9).hex(),
            'zp_18_1f': m.read_memory('spcMemory', 0x0018, 8).hex(),
            'zp_24_27': m.read_memory('spcMemory', 0x0024, 4).hex(),
            'n_sound_effects': m.read_memory('spcMemory', 0x17FD, 1).hex(),
            'command_jump_table_07b5': m.read_memory('spcMemory', 0x07B5, 16).hex(),
        }
        disasm_starts = [int(value, 0) for value in
                         os.environ.get('SPC_DISASM_STARTS',
                                        os.environ.get('SPC_DISASM_START', '0x0500')).split(',')]
        spc_disassembly = []
        for disasm_start in disasm_starts:
            spc_disassembly.extend(m.disassemble(disasm_start, 256, 'Spc'))
        spc_handler_trace = m.trace_log(1000, 'Spc')
    m.remove_hook(spc_dispatch_hook)
    sfx_bytecode_hook = None
    spc_stage_until = None
    spc_stage_notifications = []
    spc_stage_state = None
    spc_stage_audio = None
    spc_tick_snapshots = []
    spc_bounded_exec = []
    if os.environ.get('SPC_BOUNDED_EXEC') == '1':
        bounded_exec_hook = m.add_exec_hook(0x0000, 0xFFFF, cpu_type='Spc')
        for _ in range(int(os.environ.get('SPC_BOUNDED_FRAMES', '2'))):
            advance_probe_frame(m)
            spc_bounded_exec.extend(m.drain_notifications())
        m.remove_hook(bounded_exec_hook)
    if os.environ.get('SPC_CONTINUE_AFTER_HANDLER') != '1':
        sfx_bytecode_hook = m.add_exec_hook(0x098F, 0x098F, cpu_type='Spc')
        spc_stage_until = m.run_until(60, sfx_bytecode_hook)
        spc_stage_notifications = m.drain_notifications()
        if spc_stage_until.get('reason') == 'hookFired':
            spc_stage_state = m.get_audio_state()['spc']
            spc_stage_audio = m.get_audio_state()
        m.remove_hook(sfx_bytecode_hook)
    m.resume()
    for _ in range(50 if GAMEPLAY_MODE else 4):
        advance_probe_frame(m)
        frame_notifications = m.drain_notifications()
        spc_run_until_notifications.extend(frame_notifications)
        all_notifications.extend(frame_notifications)
        if _ < 3:
            tick_state = m.get_audio_state()
            spc_tick_snapshots.append({
                'frame_offset': _,
                'spc': tick_state['spc'],
                'dsp_key_on': tick_state['dsp']['keyOn'],
                'dsp_key_off': tick_state['dsp']['keyOff'],
                'spc_control_timers': m.read_memory('spcMemory', 0x00F1, 12).hex(),
                'voice6': tick_state['voices'][6],
                'voice7': tick_state['voices'][7],
                'zp_0c_27': m.read_memory('spcMemory', 0x000C, 28).hex(),
                'lastvar_169a_1708': m.read_memory('spcMemory', 0x169A, 0x6F).hex(),
            })
        if _ == 0:
            spc_hook_diag = m.hook_diag()
            spc_handler_state = m.get_audio_state()['spc']
            spc_handler_ram = m.read_memory('spcMemory', 0, 512).hex()
            spc_handler_trace = m.trace_log(1000, 'Spc')
            state = m.get_audio_state()
            host_bytes = m.read_memory('snesMemory', 0x7E0030, 0x12)
            queue_bytes = m.read_memory('snesMemory', 0x7E0020, 2)
        command_state_timeline.append({
            'frame_offset': _,
            'spc_cycle': state['spc']['cycle'],
            'host_previous_command': host_bytes[5],
            'host_state': host_bytes[2],
            'host_queue_sfx': queue_bytes[0],
            'host_queue_pan': queue_bytes[1],
            'stream_pending': m.read_memory('snesMemory', 0x7E28B0, 1)[0],
            'snes_apu': m.read_memory('snesMemory', 0x2140, 4).hex(),
            'spc_ports': m.read_memory('spcMemory', 0x00F4, 4).hex(),
            'spc_previous_command': m.read_memory('spcMemory', 0x01DF, 1).hex(),
        })
        if _ == 0:
            command_trace_snapshot = m.trace_log(1000, 'Spc')
            command_state_snapshot = {
                'spc_ram_01c0': m.read_memory('spcMemory', 0x01C0, 64).hex(),
                'spc_ports_f4_f7': m.read_memory('spcMemory', 0x00F4, 32).hex(),
                'spc_state': state['spc'],
            }
        if not GAMEPLAY_MODE or _ in (0, 37, 38, 39, 40, 49):
            voice = state['voices'][CAPTURE_VOICE]
            event_audio_state.append({
                    'frame_offset': _,
                    'spc_cycle': state['spc']['cycle'],
                    'key_on': state['dsp']['keyOn'],
                    'key_off': state['dsp']['keyOff'],
                    'voices_ended': state['dsp']['voicesEnded'],
                    'voice': voice,
                })
    notifications = all_notifications + m.drain_notifications()
    spc_apu_reads = [n.get('params', {}) for n in notifications
                     if n.get('method', '').endswith('hookFired')
                     and n.get('params', {}).get('handle') == spc_apu_read_hook]
    spc_apu_writes = [n.get('params', {}) for n in notifications
                      if n.get('method', '').endswith('hookFired')
                      and n.get('params', {}).get('handle') == spc_apu_write_hook]
    print(json.dumps({
        'fixture': 'ordinary-thrown-landing' if GAMEPLAY_MODE else ('no-request' if NO_REQUEST else 'direct-resident-sfx-fall'),
        'queued_local_sfx_id': FALL_LOCAL_ID,
        'rom_sha256': hashlib.sha256(open(ROM, 'rb').read()).hexdigest(),
    }, sort_keys=True))
    for _ in range(120):
        advance_probe_frame(m)
        m.pause()
    notes = m.drain_notifications()
    def hook_writes(handle):
        return [n['params'] for n in notes
                if n.get('method', '').endswith('hookFired')
                and n.get('params', {}).get('handle') == handle]
    print(json.dumps({
        'queue_writes': [(x.get('frame'), x.get('address'), x.get('value'))
                         for x in hook_writes(queue_hook)],
        'apu_writes': [(x.get('frame'), x.get('address'), x.get('value'))
                       for x in hook_writes(apu_hook)],
        'spc_port_writes': [(x.get('frame'), x.get('address'), x.get('value'))
                            for x in hook_writes(spc_port_hook)],
        'spc_dsp_writes': [(x.get('frame'), x.get('address'), x.get('value'))
                          for x in hook_writes(spc_dsp_hook)],
        'audio_state': m.get_audio_state(),
        'event_audio_state': event_audio_state,
        'command_state_timeline': command_state_timeline,
        'pre_service_host': pre_service_host,
    'spc_trace': m.trace_log(int(os.environ.get('SPC_TRACE_SIZE', '1000')), 'Spc'),
        'spc_trace_snapshot': {
            'bufferSize': command_trace_snapshot['bufferSize'],
            'returned': command_trace_snapshot['returned'],
            'rows': command_trace_snapshot['rows'],
        } if command_trace_snapshot else None,
        'command_state_snapshot': command_state_snapshot,
        'spc_apu_reads': spc_apu_reads,
        'spc_apu_writes': spc_apu_writes,
        'spc_dispatch_exec': hook_writes(spc_dispatch_hook),
        'spc_run_until': spc_run_until,
        'spc_handler_state': spc_handler_state,
        'spc_handler_cpu_state': spc_handler_cpu_state,
        'spc_allocator_snapshot': spc_allocator_snapshot,
        'spc_handler_ram': spc_handler_ram,
        'spc_handler_trace': spc_handler_trace,
        'spc_disassembly': spc_disassembly,
        'spc_run_until_notifications': spc_run_until_notifications,
        'spc_hook_diag': spc_hook_diag,
        'spc_stage_exec': [n.get('params', {}) for n in
                           spc_stage_notifications],
        'spc_stage_until': spc_stage_until,
        'spc_stage_state': spc_stage_state,
        'spc_stage_audio': spc_stage_audio,
        'spc_unpause_exec': spc_unpause_exec,
        'spc_bounded_exec': [n.get('params', {}) for n in spc_bounded_exec],
        'spc_tick_snapshots': spc_tick_snapshots,
    }, sort_keys=True))

raw = open(CAPTURE, 'rb').read() if os.path.exists(CAPTURE) else b''
sidecar = CAPTURE + '.json'
metadata = {}
if os.path.exists(sidecar):
    with open(sidecar, encoding='utf-8') as f:
        metadata = json.loads(f.readline())
metadata.update({
    'rom_sha256': hashlib.sha256(open(ROM, 'rb').read()).hexdigest(),
    'capture_sha256': hashlib.sha256(raw).hexdigest(),
    'capture_bytes': len(raw),
    'voice': CAPTURE_VOICE,
    'event': 'FALL_GAMEPLAY' if GAMEPLAY_MODE else 'FALL_GOLDEN',
    'local_sfx_id': FALL_LOCAL_ID,
    'fixture': 'ordinary-thrown-landing' if GAMEPLAY_MODE else 'direct-resident-sfx-fall',
})
with open(CAPTURE + '.report.json', 'w', encoding='ascii') as f:
    json.dump(metadata, f, sort_keys=True, indent=2)
print(json.dumps(metadata, sort_keys=True))
