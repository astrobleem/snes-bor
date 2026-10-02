"""Private fixed-size transport experiment, same source/destination/ownership."""
import json
import os
import subprocess
from actor_s5_isolated import ROOT,sha
from actor_s5_entity_fixture import symbols


def install(folder,address=False):
    sym=symbols(ROOT/'src/main.sym');bank=28
    rom=bytearray((folder/'bor.sfc').read_bytes())
    assert rom[bank*32768:(bank+1)*32768]==bytes(32768)
    read=sym['Core_StreamScroll_FetchTileToBuffer__read']
    ret=sym['Core_StreamScroll_PickColumn']-1
    def off(a):return (a>>16)*32768+(a&65535)-32768
    assert rom[off(read):off(read)+5]==b'\xe2\x20\xad\x01\x20'
    assert rom[off(ret)]==0x60
    buf=sym['StreamScroll_TileBufN']
    asm=f'.snes\n.bank {bank}\n.org $8000\nS7Fetch_Copy:\n    sep #$20\n.a8\n.i16\n'
    for i in range(32):
        asm+=f'    lda $2001\n    sta.l ${buf+i:06X},x\n'
    # Preserve the original exit A/X/Y and comparison flags, not just bytes.
    asm+=f'''    rep #$31
.a16
.i16
    pha
    txa
    clc
    adc #32
    tax
    pla
    ldy #32
    cpy #32
    jml ${ret:06X}
'''
    if address:
        from actor_s7_fetch_address import emit
        start=sym['Core_StreamScroll_FetchTileToBuffer']
        program=rom.index(b'\x8d\x00\x20',off(start),off(sym['Core_StreamScroll_FetchTileToBuffer__seek_busy']))+0x8000
        assert rom[off(start):off(start)+6]==b'\xc2\x31\xaf'+sym['StreamStage_TileId'].to_bytes(3,'little')
        asm+='\n.org $8100\n'+emit(sym,f'jml ${program:06X}')
    path=folder/'fetch-unroll.pasm';path.write_text(asm)
    result=subprocess.run([os.environ.get('DOTNET_EXE',r'C:\Users\chad\.dotnet\dotnet.exe'),
        os.environ.get('POPPY_DLL',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll'),
        str(path),'-s',str(folder/'fetch-unroll.sym')],capture_output=True,text=True)
    (folder/'fetch-build.log').write_text(result.stdout+result.stderr)
    if result.returncode or 'warning' in (result.stdout+result.stderr).lower():raise RuntimeError(result.stdout+result.stderr)
    payload=path.with_suffix('.bin').read_bytes()[bank*32768:]
    assert len(payload)<512
    rom[bank*32768:bank*32768+len(payload)]=payload
    rom[off(read):off(read)+5]=b'\x5c\x00\x80'+bytes([bank])+b'\xea'
    if address:
        rom[off(start):off(start)+6]=b'\x5c\x00\x81'+bytes([bank])+b'\xea\xea'
    (folder/'bor.sfc').write_bytes(rom)
    (folder/'fetch-unroll.json').write_text(json.dumps(dict(private=True,bytes=32,address=address,
        code_bytes=len(payload),bank=bank,rom_sha256=sha(folder/'bor.sfc'),
        ownership='CPU copy only; no new DMA/PPU/WRAM-port ownership'),indent=2)+'\n')
