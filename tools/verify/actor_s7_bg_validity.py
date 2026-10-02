"""Private immutable-BG validity experiment; does not modify distribution."""
import json
import os
import subprocess
from actor_s5_entity_fixture import symbols
from actor_s5_isolated import ROOT,sha


def install(folder,enabled=True):
    sym=symbols(ROOT/'src/main.sym')
    link=json.loads((folder/'link.json').read_text())
    assert link['scenario']=='kula' and link['resident'], 'BOUNDED_SOURCE_WORLD_ADMISSION'
    # Its source-stage parser already requires no environment directives and
    # ordinary scroll. No animated/dynamic BG writer is admitted by this host.
    rom=bytearray((folder/'bor.sfc').read_bytes())
    bank=27
    assert rom[bank*32768:(bank+1)*32768]==bytes(32768)
    def off(pc):return (pc>>16)*32768+(pc&65535)-32768
    def raw(pc,n):return bytes(rom[off(pc):off(pc)+n])
    init=sym['Core_StreamCache_Init']
    allocate=sym['Core_StreamCache_AllocateSlot__allocate']
    evict_at=rom.index(b'\x8f'+sym['StreamCache_OldTile'].to_bytes(3,'little'),
                      off(allocate),off(sym['Core_StreamCache_AllocateSlot__no_evict']))
    evict=evict_at+0x8000
    ready=sym['Bg_LoadScene_Streaming__hud_done']
    pick_call=b'\x20'+(sym['Core_StreamScroll_PickColumn']&65535).to_bytes(2,'little')
    start=off(sym['Core_StreamScroll_Play']);end=off(sym['Core_StreamScroll_Play__resume'])
    at=rom.index(pick_call,start,end)+3
    pick=0x8000+at
    finish=sym['Core_StreamScroll_Play__resume']+3
    rts=sym['Core_StreamScroll_ClampCamera__left_ok']
    assert raw(init,4)==b'\x08\x78\xc2\x31'
    assert raw(ready,4)==b'\x28\xc2\x31\x60'
    assert raw(pick,4)==b'\x8f'+sym['StreamScroll_PendCol'].to_bytes(3,'little')
    assert raw(finish,1)==b'\x28' and raw(rts,1)==b'\x60'
    aliases=dict(S7BG_InitResume=init+4,S7BG_EvictionResume=evict+4,S7BG_Enable=int(enabled),
                 S7BG_Bank0Rts=rts,S7BG_PickResume=pick+4,S7BG_PlayFinish=finish)
    asm='.snes\n'+'\n'.join(f'{k} = ${v:X}' for k,v in {**sym,**aliases}.items()
                  if k in aliases or k.startswith(('Stream','Game_StageIndex','DmaQueue')))
    asm+=f'\n.bank {bank}\n.org $8000\n.include "{(ROOT/"src/core/actor_source_bg_validity.pasm").as_posix()}"\n'
    pasm=folder/'bg-validity.pasm';pasm.write_text(asm)
    result=subprocess.run([os.environ.get('DOTNET_EXE',r'C:\Users\chad\.dotnet\dotnet.exe'),
        os.environ.get('POPPY_DLL',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll'),
        str(pasm),'-s',str(folder/'bg-validity.sym')],capture_output=True,text=True)
    (folder/'bg-build.log').write_text(result.stdout+result.stderr)
    if result.returncode or 'warning' in (result.stdout+result.stderr).lower():raise RuntimeError(result.stdout+result.stderr)
    sy=symbols(folder/'bg-validity.sym');binary=pasm.with_suffix('.bin').read_bytes()
    payload=binary[bank*32768:(bank+1)*32768]
    rom[bank*32768:bank*32768+len(payload)]=payload
    patches=[]
    for pc,n,name in ((init,4,'S7BG_Init'),(evict,4,'S7BG_Eviction'),
                      (ready,4,'S7BG_BootReady'),(pick,4,'S7BG_AfterPick')):
        before=raw(pc,n)
        rom[off(pc):off(pc)+n]=b'\x5c'+sy[name].to_bytes(3,'little')+b'\xea'*(n-4)
        patches.append(dict(pc=pc,before=before.hex(),target=name))
    (folder/'bor.sfc').write_bytes(rom)
    (folder/'bg-validity.json').write_text(json.dumps(dict(private=True,production_changed=False,
        enabled=enabled,state_region=[0x7e1640,0x7e1660],patches=patches,rom_sha256=sha(folder/'bor.sfc'),
        contract='no evictions since cache init; immutable asset identity; empty DMA and column ownership',
        fallback='any eviction or identity change: existing repair until stage reload'),indent=2))
    return sy
