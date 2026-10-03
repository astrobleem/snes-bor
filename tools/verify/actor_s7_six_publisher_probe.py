"""Small read-only probe for the six-request publisher fixture."""
import argparse
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from _harness import McpSession, MESEN_EXE, _free_tcp_port, run_frames_exact, Reporter
from actor_s5_entity_fixture import symbols
from actor_s5_isolated import ROOT
from game_bor_startup_select import cold_to_title, select_case


def off(a):
    return (a >> 16) * 32768 + (a & 65535) - 32768


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--fields', type=int, default=80)
    a = p.parse_args(); folder = a.fixture.resolve()
    s = symbols(folder / 'world.sym'); prod = symbols(ROOT / 'src/main.sym')
    names = ('S7Publisher_Reset', 'S7Publisher_Capture',
             'S7Publisher_ResourcesReady', 'S7Publisher_RenderOrCompat',
             'S7Publisher_RenderOrCompat__source', 'S7Publisher_RenderOrCompat__done',
             'S7Publisher_EmitPieces', 'S7Multi_EmitActive', 'S7Multi_CaptureComplete',
             'S7Admission_Upper', 'S7Admission_Upper__pass', 'S7Admission_Upper__owned',
             'S7Admission_Scanlines', 'S7Admission_Scanlines__result',
             'S7Multi_OamTail', 'S7Multi_OamTail__legacy', 'S7Multi_OamTail__missing',
             'S7Multi_Missing', 'S7Multi_Lookup',
             'S7Multi_CaptureComplete', 'S7Multi_PublishSnapshot',
             'S7Multi_PublishSnapshot__completed', 'S7Packet_Submit__source',
             'S7Packet2_Submit__source', 'S7Packet_Submit__fault',
             'S7Packet2_Submit__fault', 'Character_RenderPass',
             'Core_Nmi_Play', 'Core_Nmi_Play__do_commit',
             'Core_Dma_ProcessQueue', 'Core_Dma_ProcessQueue__done',
             'Core_Nmi_Play__done',
             'Character_RenderPass__render_live', 'Character_RenderPass__dispatch',
             'Character_RenderPass__render_done',
             'S6Host_Tick', 'S6Host_Tick__return')
    names = [n for n in names if n in s or n in prod]
    lua = folder / 'six-probe.lua'
    code = '''local mt=emu.memType.snesMemory
local function w(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
local function row(tag)
 local q=emu.getState(); local x={tag,q["masterClock"],q["ppu.frameCount"],q["cpu.d"],
  w(0x7f8c00),w(0x7f8c02),w(0x7f8c06),w(0x7f8c1c),w(0x7f8c1e),w(0x7f8c20),
  w(0x7f8c26),w(0x7f8c28),w(0x7f8c2a),w(0x7f8c2c),w(0x7f8ce0),w(0x7f8cf2),w(0x7f8cf4),
  w(0x7e173c),w(0x7e1760),w(0x7e1764),w(0x7f8ce2),w(0x7f8ce4),w(0x7fa8da),w(0x7fa8dc),w(0x7fa8de),w(0x7fad28),w(0x7fad22),w(q["cpu.d"]+0x06),w(q["cpu.d"]+0xe4),w(0x20c000),w(0x20c002),w(0x20c004),w(0x20c006),emu.read(0x7e554f,mt),emu.read(0x7e5550,mt),emu.read(0x7e5551,mt),emu.read(0x7e5552,mt),emu.read(0x7e5553,mt),emu.read(0x7e5554,mt)}
 for i=0,5 do
  local b=0x7e1900+i*256; local p=0x7e0a00+i*133
  table.insert(x,w(b+0x06));table.insert(x,w(b+0x34));table.insert(x,w(b+0x40))
  table.insert(x,emu.read(p+0x23,mt));table.insert(x,emu.read(p+0x0c,mt));table.insert(x,emu.read(p+0x34,mt));table.insert(x,emu.read(p+0x0b,mt))
 end
emu.log("S7SIX|"..table.concat(x,"|"))
end
emu.addMemoryCallback(function()
 local s=emu.getState()
 emu.log("S7SIX|S6TICK|"..tostring(s["masterClock"]).."|"..tostring(s["ppu.frameCount"]).."|"..tostring(w(0x7e173c)))
end,emu.callbackType.write,0x1774,0x1774,emu.cpuType.snes,emu.memType.snesWorkRam)
'''
    for n in names:
        addr = s.get(n, prod.get(n)); code += f'emu.addMemoryCallback(function() row("{n}") end,emu.callbackType.exec,{off(addr)},{off(addr)},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
    lua.write_text(code)
    class Obs(McpSession):
        def __enter__(self):
            import mesen_mcp.session as m
            def launch(argv, **kw): return subprocess.Popen([*argv, str(lua)], **kw)
            with patch.object(m, 'subprocess', SimpleNamespace(Popen=launch, DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE)):
                return super().__enter__()
    r = Reporter('S7-SIX-PROBE')
    with Obs(rom=folder/'bor.sfc', mesen=MESEN_EXE, cwd=folder,
             port=_free_tcp_port(), stderr_log=folder/'six-probe-mesen.log') as m:
        with patch.object(m, 'reset_emulator', lambda: None): cold_to_title(m, r)
        select_case(m, r, 'KULA', 'KULA'); m.write_u16(0x7e1770, 1)
        for _ in range(a.fields): run_frames_exact(m, 1)
        lines=[x.decode(errors='replace') if isinstance(x,bytes) else x for x in m._stderr_lines]
    rows=[x[x.index('S7SIX|'):].strip().split('|') for x in lines if 'S7SIX|' in x]
    (folder/'six-probe.json').write_text(json.dumps(rows, indent=2)+'\n')
    print(json.dumps({'rows':len(rows),'tags':sorted(set(x[1] for x in rows)),'last':rows[-10:]},indent=2))


if __name__ == '__main__': main()
