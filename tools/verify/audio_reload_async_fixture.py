import json
import os
import socket
import sys

sys.path.insert(0, r'E:\gh\Mesen2\python')
from mesen_mcp.session import McpSession

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ROM = os.path.join(ROOT, 'build', 'audio_reload_async_fixture.sfc')
EXE = r'E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe'
OUT = os.path.join(ROOT, 'build', 'audio_reload_async_fixture_evidence.json')
WAV = os.path.join(ROOT, 'build', 'audio_reload_async_fixture.wav')


def port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    value = s.getsockname()[1]
    s.close()
    return value


def u8(m, addr):
    return m.read_memory('snesMemory', addr, 32)[0]


def u16(m, addr):
    data = m.read_memory('snesMemory', addr, 32)
    return data[0] | (data[1] << 8)


def snapshot(m, frame):
    return {
        'observation_frame': frame,
        'enabled': u8(m, 0x7E2A00),
        'ready': u8(m, 0x7E2A01),
        'request_count': u8(m, 0x7E2A03),
        'final_state': u8(m, 0x7E2A07),
        'main_counter': u8(m, 0x7E2A13),
        'callback_count': u8(m, 0x7E2A15),
        'callback_bank': u8(m, 0x7E2A16),
        'callback_addr': u16(m, 0x7E2A17),
        'callback_size': u16(m, 0x7E2A19),
        'queued_bank': u8(m, 0x7E2A1B),
        'queued_addr': u16(m, 0x7E2A1C),
        'queued_size': u16(m, 0x7E2A1E),
        'transfer_chunks': u16(m, 0x7E2A11),
        'raw_nmi': u8(m, 0x7E2A20),
        'async_request_raw': u8(m, 0x7E2A28),
        'async_request_nmi': u8(m, 0x7E2A29),
        'async_request_main': u8(m, 0x7E2A2A),
        'async_common_raw': u8(m, 0x7E2A2B),
        'async_common_nmi': u8(m, 0x7E2A2C),
        'async_common_main': u8(m, 0x7E2A2D),
        'async_ready_raw': u8(m, 0x7E2A2E),
        'async_ready_nmi': u8(m, 0x7E2A2F),
        'async_ready_main': u8(m, 0x7E2A30),
        'async_common_seen': u8(m, 0x7E2A31),
        'nmi_frame_counter': u16(m, 0x7E5023),
    }


def main():
    evidence = {'rom': ROM, 'transfer_size': 800, 'snapshots': []}
    with McpSession(rom=ROM, mesen=EXE, port=port(), boot_wait=2.0) as m:
        m.reset_emulator()
        m.record_audio(WAV)
        ready_frame = None
        for frame in range(1, 500):
            m.run_frames(1)
            if frame in (1, 20, 40, 60, 100, 150, 200, 250, 300, 400):
                evidence['snapshots'].append(snapshot(m, frame))
            if ready_frame is None and u8(m, 0x7E2A01):
                ready_frame = frame
                break
        m.pause()
        evidence['ready_observation_frame'] = ready_frame
        evidence['ready_snapshot'] = snapshot(m, ready_frame or frame)
        post_ready_frames = 80
        for _ in range(post_ready_frames):
            m.run_frames(1)
        evidence['post_ready_frames'] = post_ready_frames
        evidence['final'] = snapshot(m, (ready_frame or frame) + post_ready_frames)
        evidence['audio_state'] = m.get_audio_state()
        m.stop_audio()
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(evidence, f, indent=2, sort_keys=True)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    print('audio_capture=' + WAV)


if __name__ == '__main__':
    main()
