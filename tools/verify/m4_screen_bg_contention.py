"""Co-observe native lossless BG palette IRQ and exact SA-1 SCREEN arithmetic."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch
import numpy as np
import m4_bg_components_native as bg
from m4_screen_sa1_native import capture, build
from compiler import Source
from _harness import McpSession


def combine(raw,pairs):
    helper,entry,done=build(pairs,False,'lut-linear',True)
    stop=helper[0x9000:0x9800].find(bytes([255])*32)
    if stop<0:raise ValueError('SCREEN_WORKER_END')
    worker=helper[0x9000:0x9000+stop].replace(bytes.fromhex('bf 00 00 c1'),bytes.fromhex('bf 00 00 c4')).replace(bytes.fromhex('a9 04 48 ab'),bytes.fromhex('a9 0a 48 ab'))
    if worker==helper[0x9000:0x9000+stop]:raise ValueError('SCREEN_WORKER_RELOCATION')
    rom=bytearray(raw)+bytearray([255])*262144
    rom[0x40000:0x50000]=helper[0x10000:0x20000]
    rom[0x50000:0x50000+len(pairs)*2]=helper[0x20000:0x20000+len(pairs)*2]
    rom[0x58000:0x58000+len(worker)]=worker
    code=rom[0x8000:0x8400];end=code.find(bytes([255])*32)
    if end<0:raise ValueError('BG_MAIN_END')
    code=bytearray(code[:end]);marker=code.find(bytes.fromhex('a9 0f 8d 00 21'))
    if marker<0 or code[-3]!=0x4c:raise ValueError('BG_MAIN_RELOCATION')
    init=bytearray()
    for address,value in [(0x2229,255),(0x2226,128),(0x2228,0),(0x2200,32),(0x2203,0),(0x2204,0x32)]:
        init.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    init.extend(bytes.fromhex('a2 00 00'));loop=len(init)
    init.extend(bytes.fromhex('bf 00 80 0b 9f 00 32 00 e8 e0'));init.extend(struct.pack('<H',len(worker)))
    init.extend(bytes([0xd0,(loop-len(init)-2)&255]))
    old_target=struct.unpack('<H',code[-2:])[0]
    code[-2:]=struct.pack('<H',old_target+len(init))
    code[marker:marker]=init
    start=code.find(bytes.fromhex('a9 10 8d 00 42 58'))
    if start<0:raise ValueError('BG_IRQ_PREPARATION')
    code[start+5:start+5]=bytes.fromhex('9c 00 22')  # release SA-1 after IRQ setup; subsequent zero writes have no reset edge
    if len(code)>1024:raise ValueError('BG_SCREEN_CODE_OVERLAP')
    rom[0x8000:0x8400]=bytes([255])*1024;rom[0x8000:0x8000+len(code)]=code
    rom[0x7fd5:0x7fdc]=bytes([0x23,0x35,9,8,1,0x33,0])
    return bytes(rom),entry,done


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--stage',required=True)
    p.add_argument('--scene',type=Path,required=True);p.add_argument('--components',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    pairs,metadata=capture(Source(a.source),a.stage,json.loads(a.scene.read_text()))
    compile_base=bg.compile_rom;details={}
    def compile_combo(*args,**kwargs):
        raw,trace,resources=compile_base(*args,**kwargs);raw,entry,done=combine(raw,pairs)
        details.update(entry=entry,done=done)
        resources.update(sa1_screen_channels=len(pairs),sa1_screen_irq_co_observer=True)
        return raw,trace,resources
    class Extra(McpSession):
        def __enter__(self):
            with (folder/'observer.lua').open('a') as f:
                f.write('''\nlocal function job(a,v) local s=emu.getState();emu.log('SCREENJOB|'..table.concat({a,s['masterClock'],s['ppu.frameCount'],s['ppu.scanline']},',')) end
emu.addMemoryCallback(job,emu.callbackType.exec,ENTRY,ENTRY,emu.cpuType.sa1,emu.memType.sa1Memory)
emu.addMemoryCallback(job,emu.callbackType.exec,DONE,DONE,emu.cpuType.sa1,emu.memType.sa1Memory)
'''.replace('ENTRY',str(details['entry'])).replace('DONE',str(details['done'])))
            return super().__enter__()
        def __exit__(self,*args):
            raw=self.read_memory('SnesMemory',0x420000,len(pairs)*2)
            raw=bytes.fromhex(raw['hex']) if isinstance(raw,dict) else bytes(raw)
            (folder/'screen.rgb8words').write_bytes(raw)
            return super().__exit__(*args)
    argv=['m4_bg_components_native','--report',str(a.components),'--assets',str(a.components.parent),'--output',str(folder),'--timer','160']
    with patch.object(bg,'compile_rom',compile_combo),patch.object(bg,'McpSession',Extra),patch.object(sys,'argv',argv):bg.main()
    r=json.loads((folder/'result.json').read_text());actual=np.fromfile(folder/'screen.rgb8words',dtype='<u2')&255
    expected=255-((255-pairs[:,0])*(255-pairs[:,1])//255)
    events=[[int(v) for v in line.split('SCREENJOB|',1)[1].split(',')] for line in (folder/'mesen.log').read_text().splitlines() if 'SCREENJOB|' in line]
    r.update(screen_rgb8_channels_exact=bool(np.array_equal(actual,expected)),screen_channel_mismatches=int(np.count_nonzero(actual!=expected)),
             screen_job_events=events,screen_job_master_clocks=events[1][1]-events[0][1] if len(events)==2 else None,
             screen_input_sha256=hashlib.sha256(pairs.astype('<u2').tobytes()).hexdigest(),
             scope='Fixed native lossless BG with palette IRQ and dummy channel-0 HDMA while SA-1 computes source RGB8 SCREEN. No geometry/palette allocation/live world/production TAD admission.')
    r['pass']=r['pass'] and r['screen_rgb8_channels_exact'] and len(events)==2
    (folder/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
    if not r['pass']:raise SystemExit(1)


if __name__=='__main__':main()
