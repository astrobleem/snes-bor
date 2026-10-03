"""Isolated forced-blank raster geometry proof, not deadline certification.

--live explicitly launches Mesen. No production writes. Every attempt retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import struct
import subprocess
import shutil
import io

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/bor_compile'))
from analyze import scoped_id
from compiler import Source
from model_ir import parse_model
from source_actor_raster import compile_animation
from actor_lowering import lower_model
from actor_frame_abi import pack_source_frame


def emit(data):
    return '\n'.join('    .db '+','.join(f'${b:02X}' for b in data[i:i+16])
                     for i in range(0,len(data),16))+'\n'


def build_rom(folder, model, result, timed=False):
    frames = result['manifest']['frames']
    if not 0 < len(frames) <= 8:
        raise ValueError('FIXTURE_RASTER_COUNT: available=8')
    records = bytearray(); banks = []
    for i, frame in enumerate(frames):
        if not frame['chunks']:
            raise ValueError('FIXTURE_EMPTY_FRAME_UNBOUND')
        for chunk in frame['chunks']:
            for xy in ('left_xy','right_xy'):
                x,y = chunk[xy]
                if not (0 <= x+120 <= 240 and 0 <= y+160 <= 192):
                    raise ValueError('FIXTURE_ONSCREEN_ADMISSION')
        bank = i+2
        writes = frame['writes']
        geometry = b''.join(struct.pack('<hhhH', *c['right_xy'][:1], c['left_xy'][0],
                                         c['right_xy'][1], c['tile']) for c in frame['chunks'])
        gaddr = 0x8000+len(writes)*7
        payload = bytearray(); descriptors = bytearray()
        paddr = gaddr+len(geometry)
        for write in writes:
            descriptors.extend(struct.pack('<HHBH', 0x4000+write['vram_word_offset'],
                                            paddr+len(payload),bank,write['size']))
            o=write['packet_offset']; payload.extend(result['packets'][o:o+write['size']])
        data=descriptors+geometry+payload
        if len(data)>32768: raise ValueError('FIXTURE_BANK_EXTENT')
        banks.append(data)
        records.extend(struct.pack('<HBBHBB8x',0x8000,bank,len(writes),gaddr,bank,len(frame['chunks'])))
    lowered=lower_model(model)
    animation=next(a for a in lowered['animations'] if a['role']==result['manifest']['role'])
    descriptors=bytearray()
    for i,frame in enumerate(animation['frames']):
        packed=bytearray(pack_source_frame(frame));struct.pack_into('<HH',packed,28,frame.get('move',0)&65535,i)
        descriptors.extend(packed)
    table=bytearray(0x400)
    table[:len(records)]=records
    table[0x100:0x100+len(descriptors)]=descriptors
    table[0x200:0x210]=struct.pack('<HHHBB8x',1,len(frames),0x8100,1,0)
    table[0x300:0x320]=result['cgram']
    code='''.snes
.lorom
.bank 0
.org $8000
Reset:
    sei
    clc
    xce
    rep #$30
    .a16
    .i16
    ldx #$1FFF
    txs
    lda #0
    tcd
    sep #$20
    .a8
    pha
    plb
    lda #$80
    sta $2100
    stz $4200
    stz $2105
    stz $2133
    stz $212C
    stz $212D
    stz $2130
    stz $2131
    lda #$C2
    sta $2101
    lda #$10
    sta $212C
    stz $2121
    stz $2122
    stz $2122
    lda #$80
    sta $2121
    ldx #0
Palette:
    .a8
    .i16
    lda.l $018300,x
    sta $2122
    inx
    cpx #32
    bne Palette
    rep #$30
    .a16
    .i16
    lda #$1000
    tcd
    ldx #254
    lda #0
Clear:
    .a16
    .i16
    sta $00,x
    dex
    dex
    bpl Clear
    sta.l $7E2000
    sta.l $7E2002
    sta.l $7E2010
    sta.l $7E2012
    sta.l $7E2014
    sta.l $7E2018
    lda #$8200
    sta $C8
    lda #1
    sta $CA
    sta $CC
    sta $E0
    sta $F6
    sta $1A
    sta $FA
    lda #120
    sta $14
    lda #160
    sta $16
    lda #1
    jsl S6_SetRole
Advance:
    .a16
    .i16
    inc $D0
    jsl S6_AnimationPass
    lda $10
    bne Advance
    lda $1A
    beq Complete
    stz $1A
    stz $D0
    lda #1
    jsl S6_SetRole
    bra Advance
Complete:
    .a16
    .i16
    lda #$5636
    sta.l $7E200A
Done:
    .a16
    .i16
    bra Done
S6_Think:
    .a16
    .i16
    rtl
S5_HostRandom03:
    .a16
    .i16
    rtl
'''
    if timed:
        code=code.replace('    jsl S6_SetRole\nAdvance:', '    sta.l $7E2012\n    jsl S6_SetRole\nAdvance:',1)
        start=code.index('Advance:');end=code.index('S6_Think:')
        code=code[:start]+f'.include "{(ROOT/"src/core/actor_s6_raster_clock_fixture.pasm").as_posix()}"\n'+code[end:]
        code+=f'.include "{(ROOT/"src/core/actor_s5_clock_isolated.pasm").as_posix()}"\n'
    for filename in ('actor_s6_raster_fixture.pasm','actor_s5_isolated.pasm','actor_source_scheduler.pasm'):
        code+=f'.include "{(ROOT/"src/core"/filename).as_posix()}"\n'
    code+='''.org $FFC0
    .db "S6 RASTER FIXTURE    "
    .db $20,$00,$08,$00,$01,$00,$00
    .dw $FFFF,0
.org $FFE0
    .dw 0,0,Done,Done,0,Done,0,Done
    .dw 0,0,Done,0,0,Done,Reset,Done
.bank 1
.org $8000
'''+emit(table)
    for i,data in enumerate(banks): code+=f'.bank {i+2}\n.org $8000\n'+emit(data)
    pasm=folder/'fixture.pasm';pasm.write_text(code)
    command=[r'C:\Users\chad\.dotnet\dotnet.exe',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll',str(pasm),'-s',str(folder/'fixture.sym')]
    proc=subprocess.run(command,capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode or 'warning' in (proc.stdout+proc.stderr).lower():
        raise RuntimeError(proc.stdout+proc.stderr)
    rom=bytearray((folder/'fixture.bin').read_bytes())
    rom.extend(bytes(262144-len(rom)));rom[0x7fdc:0x7fe0]=b'\xff\xff\0\0'
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
    path=folder/'fixture.sfc';path.write_bytes(rom)
    return path


def live(folder, rom, result, source):
    from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact
    cases=[];world_x=120
    # Source frame-local movement occurs before raster emission, including entry.
    actor=lower_model(parse_model(source,result['manifest']['source_identity'][1],
        'fixture',scoped_id(source),'historical-bor'))
    source_frames=next(a['frames'] for a in actor['animations'] if a['role']==result['manifest']['role'])
    with McpSession(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),boot_wait=1,
                    stderr_log=folder/'mesen.log') as m:
        m.reset_emulator();m.pause()
        for direction in (1,0):
            for index,frame in enumerate(result['manifest']['frames']):
                world_x+=source_frames[index].get('move',0)*(1 if direction else -1)
                request=len(cases)+1
                run_frames_exact(m,4);m.pause()
                full=m.read_memory('snesMemory',0x7e0000,65536)
                ram=full[0x2000:0x2020]
                (folder/f'wram_{request}.bin').write_bytes(full)
                (folder/f'cpu_{request}.json').write_text(json.dumps(m.get_state(),indent=2))
                (folder/f'state_{request}.bin').write_bytes(ram)
                actual=struct.unpack_from('<5H',ram)
                assert actual[0]==request and actual[2:]==(index,direction,index),(request,actual)
                vram=m.read_memory('snesVideoRam',0,65536)
                oam=m.read_memory('snesSpriteRam',0,544)
                cgram=m.read_memory('snesCgRam',0,512)
                (folder/f'vram_{request}.bin').write_bytes(vram)
                (folder/f'oam_{request}.bin').write_bytes(oam)
                (folder/f'cgram_{request}.bin').write_bytes(cgram)
                assert cgram[256:288]==result['cgram'],'CGRAM mismatch'
                for write in frame['writes']:
                    start=0x8000+write['vram_word_offset']*2;o=write['packet_offset']
                    assert vram[start:start+write['size']]==result['packets'][o:o+write['size']],'VRAM mismatch'
                for slot,c in enumerate(frame['chunks']):
                    x,y=c['right_xy' if direction else 'left_xy']
                    expected=struct.pack('<BBH',world_x+x,160+y,c['tile']|0x3000|(0 if direction else 0x4000))
                    assert oam[slot*4:slot*4+4]==expected,('OAM mismatch',request,slot,oam[slot*4:slot*4+4].hex(),expected.hex())
                shot=m.take_screenshot()
                snapshot=folder/f'frame_{request}.png'
                shutil.copyfile(shot['path'],snapshot)
                shot['retained_path']=str(snapshot)
                # Independent source-pixel oracle. BOR.C loads the mirrored
                # sprite with center=(width+clipl)-ofsx-1, hence x+ofsx-sx.
                original=Image.open(io.BytesIO(source.read(frame['source_path'])))
                expected_image=Image.new('RGB',(256,224),(0,0,0))
                palette_words=struct.unpack('<16H',result['cgram'])
                colors={idx:tuple((((palette_words[i]>>s)&31)<<3)|(((palette_words[i]>>s)&31)>>2)
                                  for s in (0,5,10))
                        for i,idx in enumerate(result['manifest']['source_palette_indices'])}
                ox,oy=frame['offset']
                for sy in range(original.height):
                    for sx in range(original.width):
                        index_value=original.getpixel((sx,sy))
                        if not index_value:continue
                        px=world_x+sx-ox if direction else world_x+ox-sx
                        py=160+sy-oy
                        if 0<=px<256 and 0<=py<224:expected_image.putpixel((px,py),colors[index_value])
                expected_image.save(folder/f'expected_{request}.png')
                actual_image=Image.open(snapshot).convert('RGB')
                assert actual_image.tobytes()==expected_image.tobytes(),('VISIBLE_PIXEL_MISMATCH',request)
                (folder/f'screenshot_{request}.json').write_text(json.dumps(shot,indent=2))
                cases.append(dict(actor=result['manifest']['source_identity'][1],role=result['manifest']['role'],
                                  frame=index,direction=direction,cpu_ack=request,status='PASS_MEDIA',
                                  chunks=len(frame['chunks']),dma_bytes=frame['dma_bytes'],dma_transfers=len(frame['writes']),
                                  screenshot=shot,visible_pixels='PASS',source_x=world_x))
                (folder/'cases.json').write_text(json.dumps(cases,indent=2))
                m.write_u16(0x7e2002,request)
        run_frames_exact(m,3);m.pause()
        ram=m.read_memory('snesMemory',0x7e0000,65536)[0x2000:0x2020]
        assert struct.unpack_from('<H',ram,10)[0]==0x5636,'post-observation continuation'
    return cases


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def timed_live(folder,rom):
    from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact
    with McpSession(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),boot_wait=1,stderr_log=folder/'mesen.log') as m:
        m.reset_emulator();run_frames_exact(m,34);m.pause()
        ram=m.read_memory('snesMemory',0x7e0000,65536)
        (folder/'timed-wram.bin').write_bytes(ram)
        (folder/'ppu.json').write_text(json.dumps(m.get_ppu_state(),indent=2))
        shot=m.take_screenshot();shutil.copyfile(shot['path'],folder/'timed-final.png')
    assert struct.unpack_from('<H',ram,0x200a)[0]==0x5636,'timed fixture did not complete'
    elapsed=0;rows=[]
    for i in range(30):
        tick,frame,x,animating,uploads,vblank,parity,remainder=struct.unpack_from('<8H',ram,0x6000+i*16)
        end_parity=ram[0x7002+i*16]
        assert end_parity==(parity^128),('FIELD_SKIPPED_OR_PHASE_MISMATCH',i,parity,end_parity)
        if i:assert parity!=rows[-1]['parity'],('FIELD_CADENCE',i)
        elapsed+=(357368-(4 if parity else 0))*200
        expected_tick,expected_remainder=divmod(elapsed,21477270)
        expected_frame=min(sum(expected_tick>=d for d in (8,16,24,32,36,40)),5)
        assert tick==expected_tick and remainder==(expected_remainder&65535),(i,tick,expected_tick,remainder,expected_remainder)
        assert frame==expected_frame and animating==int(tick<40),(i,frame,animating)
        if uploads>1:assert vblank&128,('DMA_DEADLINE_MISSED',i,tick,frame,vblank)
        rows.append(dict(field=i+1,tick=tick,frame=frame,x=x,uploads=uploads,vblank=vblank&255,parity=parity))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
    parser.add_argument('--model', default='data/chars/kula/kula.txt')
    parser.add_argument('--declaration', default='Kula')
    parser.add_argument('--role', default='attack1')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--timed',action='store_true',help='one-actor unblanked DMA deadline probe')
    args = parser.parse_args()
    folder = Path(tempfile.mkdtemp(prefix='actor_s6_raster_', dir=ROOT/'out'))
    source = Source(args.source)
    model = parse_model(source, args.model, args.declaration, scoped_id(source), 'historical-bor')
    result = compile_animation(source, model, args.role, color_adapter='SNES_RGB555_TRUNCATE')
    (folder/'chunks.bin').write_bytes(result['chunk_pool'])
    (folder/'packets.bin').write_bytes(result['packets'])
    if result['cgram'] is not None:
        (folder/'palette.bin').write_bytes(result['cgram'])
    manifest = result['manifest']
    report = dict(status='PREPARED_NOT_RUN', project_id=model.project_id,
                  source_pak_sha256=file_sha(args.source) if args.source.is_file() else None,
                  source_hashes={str(p.relative_to(ROOT)):file_sha(p) for p in
                      [Path(__file__), ROOT/'tools/bor_compile/source_actor_raster.py',
                       ROOT/'tools/bor_compile/model_ir.py', ROOT/'out/bor_compile_s6/BOR.C',
                       ROOT/'out/bor_compile_s6/SPRITE.C',ROOT/'out/bor_compile_s6/SPRITEQ.C',
                       *[ROOT/'src/core'/n for n in ('actor_source_scheduler.pasm','actor_s5_isolated.pasm',
                          'actor_s5_clock_isolated.pasm','actor_s6_raster_fixture.pasm','actor_s6_raster_clock_fixture.pasm')]]},
                  manifest=manifest, cases=[],
                  evidence=dict(live_render=False,source_pixel_geometry=False,dma_deadline=False,clock_alignment=False),
                  nonclaims=dict(full_actor_certification=False,production_changes=False,
                                 real_hardware=False,source_rgb8_exact=False,multi_actor_admission=False),
                  pending=['Native scheduler callback binding', 'Serialized live visible-frame proof'])
    if manifest['color_encoding']['status'] == 'BLOCK':
        report['pending'].append(manifest['color_encoding']['reason'])
    print(folder,flush=True)
    try:
        rom=build_rom(folder,model,result,timed=args.timed)
        report.update(status='BUILD_ONLY',rom_sha256=file_sha(rom))
        if args.live:
            if args.timed:
                report['cases']=timed_live(folder,rom)
                report.update(status='PASS_BOUNDED_DEADLINE',pending=['Multi-actor admission','Actor/world lifecycle integration'])
                report['evidence'].update(live_render=True,dma_deadline=True,clock_alignment=True)
            else:
                report['cases']=live(folder,rom,result,source)
                report.update(status='PASS_BOUNDED_MEDIA',pending=['Unblanked DMA deadlines and 200Hz raster alignment'])
                report['evidence'].update(live_render=True,source_pixel_geometry=True)
    except Exception as error:
        report.update(status='FAIL',error=repr(error))
        raise
    finally:
        (folder/'proof.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(output=str(folder), status=report['status'], pending=report['pending']), indent=2))


if __name__ == '__main__':
    main()
