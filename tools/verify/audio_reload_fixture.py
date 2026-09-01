import os, socket, sys, time, wave
sys.path.insert(0, r'E:\gh\Mesen2\python')
from mesen_mcp.session import McpSession
ROOT=r'E:\gh\snes-bor'
ROM=os.path.join(ROOT,'build','audio_reload_fixture.sfc')
EXE=r'E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe'
def port():
    s=socket.socket(); s.bind(('127.0.0.1',0)); p=s.getsockname()[1]; s.close(); return p
def u8(m,a): return m.read_memory('snesMemory',a,32)[0]
def u16(m,a):
    b=m.read_memory('snesMemory',a,32); return b[0]|b[1]<<8
def main():
    with McpSession(rom=ROM,mesen=EXE,port=port(),boot_wait=2.0) as m:
        m.reset_emulator()
        m.record_audio(os.path.join(ROOT,'build','audio_reload_fixture.wav'))
        for i in range(900):
            r=m.run_frames(1)
            if u8(m,0x7E2A01):
                print('ready_frame',i+1)
                break
        else: print('ready_frame NONE')
        m.pause()
        vals={
          'request':u8(m,0x7E2A03),'ready':u8(m,0x7E2A01),
          'state_before':u8(m,0x7E2A04),'after_process':u8(m,0x7E2A05),
          'after_finish':u8(m,0x7E2A06),'final':u8(m,0x7E2A07),
          'main_counter':u16(m,0x7E2A13),'raw_nmi':u8(m,0x7E2A0C),
          'commit_start':u16(m,0x7E2A0D),'commit_end':u16(m,0x7E2A0F),
          'chunks':u16(m,0x7E2A11),'beat_queued':u8(m,0x7E2A02)}
        print(vals)
        print('audio_state',m.get_audio_state())
        m.stop_audio()
if __name__=='__main__': main()
