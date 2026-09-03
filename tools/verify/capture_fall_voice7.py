#!/usr/bin/env python3
"""Capture one real FALL resident-SFX event on physical DSP voice 7."""
import hashlib
import json
import os
import subprocess
import sys
import threading
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MESEN_ROOT = r'E:\\gh\\Mesen2-mcp-voice7'
ROM = os.path.join(ROOT, 'distribution', 'bor.sfc')
CAPTURE = os.environ.get('MESEN_VOICE_CAPTURE_PATH',
                         os.path.join(MESEN_ROOT, 'capture-fall-current.raw'))
ARM = os.environ.get('MESEN_VOICE_CAPTURE_ARM_FILE', CAPTURE + '.arm')
os.environ['MESEN_VOICE_CAPTURE_PATH'] = CAPTURE
os.environ['MESEN_VOICE_CAPTURE_VOICE'] = '7'
os.environ['MESEN_VOICE_CAPTURE_ARM_FILE'] = ARM
try:
    os.unlink(ARM)
except FileNotFoundError:
    pass

sys.path.insert(0, r'E:\\gh\\Mesen2\\python')
from mesen_mcp.session import McpSession
sys.path.insert(0, os.path.dirname(__file__))
import audio_semantic_diesound as semantic


class DotnetSession(McpSession):
    def __enter__(self):
        self._proc = subprocess.Popen([
            r'C:\\Users\\chad\\.dotnet\\dotnet.exe',
            os.path.join(MESEN_ROOT, r'bin\\win-x64\\Release\\Nexen.dll'),
            '--mcp', f'--mcp-port={self._port}', ROM,
        ], cwd=os.path.join(MESEN_ROOT, r'bin\\win-x64\\Release'),
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        threading.Thread(target=lambda: self._proc.stderr.read(), daemon=True).start()
        time.sleep(self._boot_wait)
        self._sock = self._connect()
        self.call('initialize', {})
        return self


def fall_capture_target(m):
    """Same deterministic fixture as the semantic gate, using the capture
    launcher protocol's established one-frame input call."""
    for i, base in enumerate(semantic.ENTITY_BASES[1:], 1):
        semantic.w8(m, base + semantic.CHAR_HP,
                    0 if i != 1 else semantic.CHAR_HP_MAX)
        semantic.w8(m, semantic.ENTITY_INVULN[i], 0)
        semantic.w8(m, base + semantic.CHAR_INPUT_DRIVEN, 0)
    semantic.prepare_target(m, semantic.SLOT1, 5, semantic.CHAR_HP_MAX)
    for off, value in ((semantic.CHAR_KNOCKDOWN_COUNT, 0xFF),
                       (semantic.CHAR_KNOCKDOWN_TIMER, 60),
                       (semantic.CHAR_SELECTED, 0),
                       (semantic.CHAR_FALL_STATE_TIMER, 0),
                       (semantic.CHAR_FRAME_INDEX, 0xFF),
                       (semantic.CHAR_TICK_COUNTER, 1)):
        semantic.w8(m, semantic.SLOT1 + off, value)
    semantic.w8(m, semantic.PLAYER + semantic.CHAR_HIT_STUN, 0)
    semantic.w8(m, semantic.PLAYER + semantic.CHAR_HIT_APPLIED, 0)
    before = semantic.u16(m, semantic.FALL_COUNT)
    for _ in range(3):
        m.set_input(m.BTN_Y, 1)
    for _ in range(60):
        m.run_frames(1)
        m.pause()
    return before, semantic.u16(m, semantic.FALL_COUNT), semantic.trace(m)


with DotnetSession(rom=ROM, mesen='unused', cwd=ROOT, port=7446,
                   boot_wait=2.0) as m:
    semantic.boot(m)
    semantic.clear_observation(m)
    open(ARM, 'wb').close()
    before, after, rows = fall_capture_target(m)
    print(json.dumps({
        'fall_request_delta': after - before,
        'trace': rows,
        'rom_sha256': hashlib.sha256(open(ROM, 'rb').read()).hexdigest(),
    }, sort_keys=True))
    for _ in range(120):
        semantic.run_frames_exact(m, 1)
        m.pause()

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
    'voice': 7,
    'event': 'FALL',
})
with open(CAPTURE + '.report.json', 'w', encoding='ascii') as f:
    json.dump(metadata, f, sort_keys=True, indent=2)
print(json.dumps(metadata, sort_keys=True))
