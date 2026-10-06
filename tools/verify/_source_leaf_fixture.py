"""Bounded foreground leaf fixture using the existing native VM portal."""
import os, re, struct, subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_animation_init_native import luav
from _harness import McpSession, MESEN_EXE, _free_tcp_port, run_frames_exact, exact_input_edge
import game_bor_startup_select as startup

REQUEST, INDEX, ERROR = 0x7ffd80, 0x7ffd82, 0x7ffd84


def run_fixture(rom_path, folder, rows, apply, ready, magic, tables, lua, reporter, finish=None, post=None, append='', bindings=None, probes=None, batch_size=8):
    if batch_size not in (1,2,4,8,16,32,64):raise ValueError('LEAF_BATCH_SIZE')
    sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];first=39*32768;raw=bytearray(rom_path.read_bytes())
    if raw[first:first+32768]!=bytes(32768) or raw[59*32768:61*32768]!=bytes(65536) or raw[0x7fd8]!=8:raise ValueError('LEAF_PRIVATE_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
LeafFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #MAGIC
 bne LeafFixture_Return
LeafFixture_Init:
.a16
.i16
 nop
 jsl APPLY
LeafFixture_After:
.a16
.i16
 nop
 bcc LeafFixture_Success
 lda.l EXPECTFAULT
 beq LeafFixture_Bad
 bra LeafFixture_Result
LeafFixture_Success:
.a16
.i16
 lda.l EXPECTFAULT
 bne LeafFixture_Bad
LeafFixture_Result:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcs LeafFixture_Done
 and #7
 bne LeafFixture_Init
 bra LeafFixture_Return
LeafFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
LeafFixture_Done:
.a16
.i16
 lda #0
 sta.l REQUEST
 sta.l READY
 sta.l WORLDREADY
LeafFixture_Return:
.a16
.i16
 ply
 plx
 plp
 php
 rep #$31
 phx
 phy
 jml RESUME
'''
    asm=asm.replace(' and #7',' and #'+str(batch_size-1))
    if finish:
        asm=asm.replace(' jsl APPLY',' lda.l MODE\n beq LeafFixture_Begin\n jsl SECONDARY\n bra LeafFixture_After\nLeafFixture_Begin:\n.a16\n.i16\n jsl APPLY')
    if post:
        asm=asm.replace(' lda.l INDEX',' jsl POST\nLeafFixture_Post:\n.a16\n.i16\n nop\n lda.l INDEX')
    asm+=append
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,EXPECTFAULT=REQUEST+6,MODE=REQUEST+8,READY=sy[ready],WORLDREADY=sy['VmSourceWorld_Ready'],APPLY=sy.get(apply,apply),CASES=len(rows),RESUME=entry+5,MAGIC=magic)
    if bindings:values.update({k:sy[v] for k,v in bindings.items()})
    if finish:values['SECONDARY']=sy[finish]
    if post:values['POST']=sy[post]
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('LEAF_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:];raw[first:first+len(code)]=code
    if apply not in sy:values['APPLY']=fs[apply]
    if probes:values.update({k:fs[v] for k,v in probes.items()})
    for bank,at,data in tables:
        if bank not in (59,60) or not 0<=at<=32768-len(data):raise ValueError('LEAF_TABLE_RESERVATION')
        raw[bank*32768+at:bank*32768+at+len(data)]=data
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('LEAF_GATE')
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['LeafFixture_Gate'])[:3]+b'\xea'
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [rom_path.with_suffix('.msu'),*rom_path.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    if 'SourceRetirement4086_Ready' in sy:
        lua='emu.addMemoryCallback(function() emu.write('+str(sy['SourceRetirement4086_Ready'])+',0,emu.memType.snesMemory); emu.write('+str(sy['SourceRetirement4086_Ready']+1)+',0,emu.memType.snesMemory) end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,emu.memType.snesMemory)\n'+lua
    if 'SourceLifecycle4086_Ready' in sy:
        lua='emu.addMemoryCallback(function() emu.write('+str(sy['SourceLifecycle4086_Ready'])+',0,emu.memType.snesMemory); emu.write('+str(sy['SourceLifecycle4086_Ready']+1)+',0,emu.memType.snesMemory) end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,emu.memType.snesMemory)\n'+lua
    if 'SourceBirthCore4086_Ready' in sy:
        lua='emu.addMemoryCallback(function() emu.write('+str(sy['SourceBirthCore4086_Ready'])+',0,emu.memType.snesMemory); emu.write('+str(sy['SourceBirthCore4086_Ready']+1)+',0,emu.memType.snesMemory) end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,emu.memType.snesMemory)\n'+lua
    lua='local rows='+luav(rows)+'\nlocal sy='+luav({k:v for k,v in sy.items() if k in ('VmCode_Wram','VmSlots_Wram') or k.startswith(('SourceRandom4086_','SourcePlayerSpawnHeight4086_','SourceEmptyInitEnvironment4086_','SourceEnvironment4086_','SourceFactors4086_','SourceCtorModel4086_','SourceScriptClone4086_','SourceAnimationCallback4086_','SourceDefaultInit4086_','SourceDefaultPlayer4086_','SourceLifecycle4086_','SourceDefaultChoice4086_','SourceBirthCore4086_','VmCall_','VmNativeVariant_','SourceRetirement4086_','VmSourceVars_','SourceFrameEffect','SourceFrameMotion4086_','SourceUpdateFrame4086_','SourceIdle4086_','SourceModel','SourceWeapon4086_','SourceAnimationInit4086_','SourceSelf4086_','SourceClock4086_','SourceWorldTick4086_','SourceFrameStack4086_','VmSourceWorld_','VmState_'))})+'\n'+lua
    values.update(INIT=fs['LeafFixture_Init'],AFTER=fs['LeafFixture_After'],RESULT=fs['LeafFixture_Result'])
    if post:values['POSTRESULT']=fs['LeafFixture_Post']
    for k,v in values.items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('LEAF_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(INDEX,0);m.write_u16(ERROR,0);m.write_u16(REQUEST,magic)
        for _ in range(2000):
            run_frames_exact(m,1)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native leaf batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    return raw,(folder/'mesen.log').read_text()
