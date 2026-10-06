"""Bounded native decision proof; does not execute update_frame or gameplay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bor_compile'))
from compiler import Source
from source_animation_step import Animation, decide, derive, ADDRESS
from actor_s5_entity_fixture import symbols
from _harness import McpSession, MESEN_EXE, _free_tcp_port, Reporter, exact_input_edge, run_frames_exact
from m4_input_controller_native import offset
import game_bor_startup_select as startup

REQUEST = 0x7ffa7c
INDEX = 0x7ffa7e


def cases(source):
    rows = []
    for a in derive(source)['animations']:
        rule = Animation(a['count'], a['loop_mode'], a['loop_min'], a['loop_max'])
        frames = sorted({0, a['count'] - 1, a['loop_min'], max(0, a['loop_max'] - 1)})
        for frame in frames:
            for direction in (-1, 0, 1):
                for autokill in (0, 1):
                    action, result = decide(rule, frame, direction, 0xffffffff, 0xffffffff, autokill)
                    inputs = [a['count'], frame, direction, a['loop_mode'], a['loop_min'], a['loop_max'], autokill,
                              65535, 65535, 65535, 65535]
                    rows.append(dict(handle=a['handle'], inputs=inputs, expected=[action, result, 0]))
        # Equal low words with unequal high words must not advance.
        rows.append(dict(handle=a['handle'], inputs=[a['count'], 0, 1, a['loop_mode'], a['loop_min'], a['loop_max'], 0,
                        6, 1, 6, 0], expected=[0, 0, 0]))
    for count, frame, direction, lo, hi in ((0, 0, 1, 0, 0), (3, 3, 1, 0, 0), (3, 0, 2, 0, 0),
                                           (3, 0, 1, 3, 0), (3, 0, 1, 0, 4)):
        rows.append(dict(handle=0, inputs=[count, frame, direction, 1, lo, hi, 0, 0, 0, 0, 0], expected=[0, frame, 1]))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('rom', 'output', 'source'): p.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args(); root = Path(__file__).resolve().parents[2]; folder = a.output.resolve(); folder.mkdir(parents=True, exist_ok=True)
    rows = cases(Source(a.source)); table = b''.join(struct.pack('<11H', *(n & 65535 for n in r['inputs'])) for r in rows)
    if len(table) > 0x7c00: raise ValueError('ANIMATION_FIXTURE_TABLE_CAPACITY')
    sy = symbols(root / 'src/main.sym'); rom = bytearray(a.rom.read_bytes()); entry = sy['Vm_SourceFrameGate']; start = 39 * 32768
    if rom[offset(entry):offset(entry)+5] != bytes.fromhex('08 c2 31 da 5a') or rom[start:start+32768] != bytes(32768):
        raise ValueError('ANIMATION_FIXTURE_HOOK_RESERVATION')
    loads = '\n'.join('    lda.l $%06X,x\n    sta.l $%06X' % (0x278400 + n, ADDRESS + n) for n in range(0, 22, 2))
    asm = '''.snes
.bank 39
.org $8000
AnimationFixture_Gate:
.a16
.i16
    php
    rep #$31
    pha
    phx
    phy
    lda.l $%(request)06X
    cmp #$B4C8
    bne AnimationFixture_Return
    ldx #0
AnimationFixture_Loop:
.a16
.i16
    txa
    sta.l $%(index)06X
%(loads)s
    jsl $%(decide)06X
AnimationFixture_Observe:
.a16
.i16
    nop
    txa
    clc
    adc #22
    tax
    cpx #%(size)d
    bcc AnimationFixture_Loop
    lda #0
    sta.l $%(request)06X
AnimationFixture_Return:
.a16
.i16
    ply
    plx
    pla
    plp
    php
    rep #$31
    phx
    phy
    jml $%(resume)06X
AnimationFixture_End:
.a16
.i16
''' % dict(request=REQUEST, index=INDEX, loads=loads, decide=sy['SourceAnimation4086_Decide'], size=len(table), resume=entry+5)
    pasm = folder / 'animation.pasm'; pasm.write_text(asm)
    proc = subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe', 'E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',
        str(pasm), '--output', str(folder / 'animation.bin'), '--symbols', str(folder / 'animation.sym'), '--no-pansy'], capture_output=True, text=True)
    (folder / 'poppy.log').write_text(proc.stdout + proc.stderr)
    if proc.returncode: raise ValueError('ANIMATION_FIXTURE_ASSEMBLY')
    gates = symbols(folder / 'animation.sym'); end = offset(gates['AnimationFixture_End'])
    if end > start + 1024: raise ValueError('ANIMATION_FIXTURE_CODE_CAPACITY')
    rom[start:end] = (folder / 'animation.bin').read_bytes()[start:end]
    rom[start+1024:start+1024+len(table)] = table
    rom[offset(entry):offset(entry)+5] = bytes.fromhex('5c 00 80 27 ea')
    path = folder / 'bor.sfc'; path.write_bytes(rom)
    for src in [a.rom.with_suffix('.msu'), *a.rom.parent.glob('bor*.pcm')]:
        dest = folder / src.name
        if not dest.exists(): os.link(src, dest)
    lua = folder / 'animation.lua'
    lua.write_text('''local mt=emu.memType.snesMemory; local begin=0
local function word(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
emu.addMemoryCallback(function() begin=emu.getState().masterClock end,emu.callbackType.exec,DECIDE,DECIDE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('ANIMATIONSTEP|'..word(INDEX)..'|'..word(ACTION)..'|'..word(RESULT)..'|'..word(FAULT)..'|'..(emu.getState().masterClock-begin))
end,emu.callbackType.exec,OBSERVE,OBSERVE,emu.cpuType.snes,mt)
'''.replace('DECIDE', str(sy['SourceAnimation4086_Decide'])).replace('INDEX', str(INDEX))
       .replace('ACTION', str(ADDRESS+22)).replace('RESULT', str(ADDRESS+24)).replace('FAULT', str(ADDRESS+26))
       .replace('OBSERVE', str(gates['AnimationFixture_Observe'])))
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv, **kwargs): return subprocess.Popen([*argv, '--donotsavesettings', str(lua)], **kwargs)
            with patch.object(module, 'subprocess', SimpleNamespace(Popen=launch, DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter = Reporter('M4-ANIMATION-STEP', kind='GATE')
    with Observed(rom=path, mesen=MESEN_EXE, port=_free_tcp_port(), stderr_log=folder/'mesen.log') as m:
        m.write_u16(REQUEST, 0)
        with patch.object(m, 'reset_emulator', return_value=None): startup.cold_to_title(m, reporter)
        startup.title_to_charselect(m); exact_input_edge(m, m.BTN_START, 1, port=0)
        if not startup.wait_state(m, startup.PLAYING, 300): raise ValueError('ANIMATION_FIXTURE_BOOTSTRAP')
        m.write_u16(REQUEST, 0xb4c8); run_frames_exact(m, 24)
        reporter.check('native batch completed', m.read_memory('snesMemory', REQUEST, 2) == bytes(2))
    events = []
    for line in (folder / 'mesen.log').read_text().splitlines():
        if 'ANIMATIONSTEP|' not in line: continue
        index, action, result, fault, cost = map(int, line.split('ANIMATIONSTEP|', 1)[1].split('|'))
        n = index // 22
        events.append(dict(case=n, actual=[action, result, fault], master_clocks=cost,
                           exact=index%22 == 0 and n < len(rows) and [action, result, fault] == rows[n]['expected']))
    reporter.check('all source handles and boundary decisions match', len(events) == len(rows) and all(e['exact'] for e in events))
    r = dict(schema='BYOR_SOURCE_ANIMATION_STEP_NATIVE_V1', status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(rom).hexdigest(), cases=rows, events=events,
        peak_master_clocks=max((e['master_clocks'] for e in events), default=0), bank0_growth=0,
        scope='Native timed advance decisions for source animations. No update_frame side effects, live world, rendering or MOTU gameplay.')
    (folder/'report.json').write_text(json.dumps(r, indent=2)+'\n'); reporter.finish()


if __name__ == '__main__': main()
