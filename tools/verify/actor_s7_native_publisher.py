"""Reproducible opt-in native publisher build; bounded entry-frame admission.

No OAM injection. Assets come from ModelIR, runtime identity from resident
contexts. Successful linking is not runtime/pixel or deadline certification.
"""
import argparse
import io
import json
import re
import struct
import tempfile
import shutil
import subprocess
from types import SimpleNamespace
from pathlib import Path

from actor_s5_isolated import ROOT, Source, parse_model, lower_model
from source_actor_raster import compile_animation, encode_tile
from frame_packing import pack_image
from frame_publication import pack_descriptor


from source_publication_native import db, emit_code

def prepare(folder,source,sym,*,stream=False):
    from PIL import Image
    from shipped_content import ROSTER_CONFIGS
    # Fixture choice only; native code matches linked roster/role/frame metadata.
    model=parse_model(source,'data/chars/kula/kula.txt','Kula','s7-publisher','historical-bor')
    actor=lower_model(model)
    role=sorted(a['role'] for a in actor['animations']).index('attack1')
    roster=next(i for i,c in enumerate(ROSTER_CONFIGS)
                if c['source_character'].replace('\\','/').split('/')[-1].casefold()=='kula')
    raster=compile_animation(source,model,'attack1',color_adapter='SNES_RGB555_TRUNCATE')
    frame=raster['manifest']['frames'][0]
    raw=source.read(frame['source_path'])
    packed=pack_image(raw,frame['offset'])
    image=Image.open(io.BytesIO(raw));image.load()
    mapping={v:i for i,v in enumerate(raster['manifest']['source_palette_indices'])}
    cells=[]
    for piece in packed['pieces']:
        px,py=piece['source_xy'];w,h=piece['size']
        cells.extend((px+x,py+y) for y in range(0,h,32) for x in range(0,w,16))
    assert len(cells)<=32,'ENTRY_VRAM_8K'
    tiles=bytearray(8192);chunks=[]
    for i,(x,y) in enumerate(cells):
        tile=(i//8)*64+(i%8)*2
        block=image.crop((x,y,x+16,y+32))
        for ty in range(4):
            for tx in range(2):
                pixels=bytes(mapping[block.getpixel((tx*8+dx,ty*8+dy))]
                             for dy in range(8) for dx in range(8))
                at=(tile+ty*16+tx)*32
                tiles[at:at+32]=encode_tile(pixels)
        ox,oy=frame['offset']
        chunks.append(dict(right_xy=[x-ox,y-oy],left_xy=[ox-x-15,y-oy],tile=tile))
    _,pieces=pack_descriptor(dict(chunks=chunks),role=role,index=0,map_selector=0,piece_address=0x20A100)
    # Immutable ROM source; transfer 1KiB at a time under existing queue cap.
    transfers=b''.join(struct.pack('<HHHBB',0x8000+i,0x8000+i,1024,32,0)
                       for i in range(0,8192,1024))
    transfers+=struct.pack('<HHHBB',0xA000,0x1C0,32,32,2) # OBJ palette6
    payload=tiles+raster['cgram']+bytes(224)+pieces
    (folder/'publisher-assets.bin').write_bytes(payload)
    (folder/'publisher-frame.json').write_text(json.dumps(dict(frame=frame,
        optimized_packing=packed,chunks=chunks,role_id=role,roster=roster,
        color=raster['manifest']['color_encoding'],vram_words=[0x4000,0x5000],
        cgram_bytes=[448,480],scope='ENTRY_FRAME_ONLY_NOT_TIMING_CERTIFIED'),indent=2))
    return emit_code(sym,roster,role,chunks,transfers,payload,stream=stream)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--second-actor',action='store_true',help='Second source player receives the same initial attack input')
    args=parser.parse_args()
    args.output=args.output.resolve()
    args.output.mkdir(parents=True,exist_ok=False)
    from actor_s6_production_world import build
    build(args.output,'kula',resident=True,layout_dispatch=True,publisher=True,second_action=args.second_actor)
    if args.live:run(args.output)
    print(args.output)


def run(folder):
    from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact
    from game_bor_startup_select import cold_to_title,select_case
    from unittest.mock import patch
    from frame_publication import oam_oracle
    from actor_s5_entity_fixture import symbols
    syms=symbols(folder/'world.sym')
    production=symbols(ROOT/'src/main.sym')
    lua=folder/'publisher-observer.lua'
    script='local mt=emu.memType.snesMemory\nlocal function w(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n'
    for name in ('S7Publisher_RenderOrCompat','S7Publisher_EmitPieces','S7Publisher_ResourcesReady'):
        addr=syms[name];off=(addr>>16)*32768+(addr&65535)-32768
        script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState()
 if w(0x7f8c06)==1 then emu.log("S7N|{name}|"..s["masterClock"].."|"..s["cpu.d"].."|"..s["cpu.x"].."|"..w(0x7f8c26)) end
end,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    addr=production['Core_Dma_ProcessQueue__next'];off=(addr>>16)*32768+(addr&65535)-32768
    script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();local q=0x7e0480+s["cpu.x"]
 if w(0x7e1760)>=3 or w(0x7f8c06)==1 then
  emu.log("S7DMA|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..w(q).."|"..w(q+2).."|"..emu.read(q+4,mt).."|"..w(0x7f8c16))
 end
end,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function(a,v)
 if v==1 and w(0x7f8c06)==1 then
  local s=emu.getState();emu.log("S7CAP|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..w(0x7f8c2c).."|"..w(0x7f8c28).."|"..w(0x7f8c2a))
 end
end,emu.callbackType.write,0x18c26,0x18c26,emu.cpuType.snes,emu.memType.snesWorkRam)
'''
    lua.write_text(script)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as session_module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            proxy=SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)
            with patch.object(session_module,'subprocess',proxy):return super().__enter__()
    report=Reporter('S7-NATIVE-ENTRY')
    manifest=json.loads((folder/'publisher-frame.json').read_text())
    pieces=(folder/'publisher-assets.bin').read_bytes()[0x2100:]
    rows=[];proof=None;captured=None
    with Observed(rom=folder/'bor.sfc',mesen=MESEN_EXE,cwd=folder,
                    port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',lambda:None):cold_to_title(m,report)
        m.write_memory('snesMemory',0x7E1700,bytes(256).hex())
        m.write_memory('snesMemory',0x7E1900,bytes(1536).hex())
        select_case(m,report,'KULA','KULA')
        m.write_u16(0x7E1770,1)
        for field in range(100):
            run_frames_exact(m,1)
            state=m.read_memory('snesMemory',0x7F8C00,256)
            world=m.read_memory('snesMemory',0x7E1700,256)
            u=lambda b,o:struct.unpack_from('<H',b,o)[0]
            row=dict(field=field,transfers=u(state,0),pending=u(state,2),ready=u(state,6),
                     valid=u(state,38),snapshot_tick=u(state,44),mode=u(world,96),
                     source_tick=u(world,60),error=u(world,100),x=u(state,32),y=u(state,34))
            rows.append(row)
            row['dma_budget']=m.read_u16(0x7E047A)
            if field==99:
                (folder/'failure-wram.bin').write_bytes(m.read_memory('snesMemory',0x7E0000,65536))
            if row['valid']==1 and row['ready']==1:
                captured=bytes(state)
            if captured is not None:
                oam=m.read_memory('snesSpriteRam',0,544)
                expected=oam_oracle(pieces,anchor_x=u(captured,32),anchor_y=u(captured,34),
                                    facing_left=not u(captured,36),palette_slot=6)
                admitted=[0]
                for slot in range(1,6):
                    at=32+slot*32
                    if u(captured,at+6):
                        admitted.append(slot)
                        expected+=oam_oracle(pieces,anchor_x=u(captured,at),anchor_y=u(captured,at+2),
                                            facing_left=not u(captured,at+4),palette_slot=6)
                wanted=b''.join(p['low'] for p in expected)
                row['oam']=oam[:max(len(wanted),64)].hex()
                row['expected_oam']=wanted.hex()
                (folder/'observed-oam.bin').write_bytes(oam)
                if not (folder/'observed.png').exists():
                    shot=m.take_screenshot()
                    shutil.copyfile(shot['path'],folder/'observed.png')
                if wanted and oam[:len(wanted)]==wanted:
                    vram=m.read_memory('snesVideoRam',0x8000,8192)
                    cgram=m.read_memory('snesCgRam',448,32)
                    assets=(folder/'publisher-assets.bin').read_bytes()
                    assert vram==assets[:8192],'VRAM_BYTES'
                    assert cgram==assets[8192:8224],'CGRAM_BYTES'
                    (folder/'hardware-oam.bin').write_bytes(oam)
                    (folder/'hardware-vram.bin').write_bytes(vram)
                    # Hardware OAM is consumed for the following raster; the
                    # current screenshot may still be the preceding framebuffer.
                    run_frames_exact(m,1)
                    shot=m.take_screenshot()
                    shutil.copyfile(shot['path'],folder/'source-frame0.png')
                    from PIL import Image
                    source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
                    src=Image.open(io.BytesIO(source.read(manifest['frame']['source_path'])))
                    screen=Image.open(folder/'source-frame0.png').convert('RGB')
                    palette=source.read('data/pal.act');ox,oy=manifest['frame']['offset'];matched=0
                    for yy in range(src.height):
                        for xx in range(src.width):
                            index=src.getpixel((xx,yy))
                            if not index:continue
                            x=u(captured,32)+xx-ox;y=u(captured,34)+yy-oy
                            assert 0<=x<256 and 0<=y<224,'PIXEL_SCOPE'
                            rgb=tuple(((v>>3)<<3)|((v>>3)>>2) for v in palette[index*3:index*3+3])
                            assert screen.getpixel((x,y))==rgb,f'PIXEL_MISMATCH: {x},{y}'
                            matched+=1
                    proof=dict(status='FRAME0_TILE_PALETTE_OAM_MATCH',observation=row,
                               pieces=len(expected),admitted_slots=admitted,target_pixels_matched=matched,timing_certified=False)
                    break
            if row['error']:break
    (folder/'publication.json').write_text(json.dumps(dict(proof=proof,observations=rows),indent=2))
    events=[line for line in (folder/'mesen.log').read_text().splitlines()
            if line.startswith(('S7N|','S7CAP|','S7DMA|'))]
    (folder/'publication-events.txt').write_text('\n'.join(events)+'\n')
    assert proof,'NATIVE_PUBLICATION_NOT_OBSERVED'


if __name__=='__main__':main()
