"""Bounded original-BOR selector/first-stage smoke and production bus census.

This measures the existing static runtime, not admission of new raster traffic.
No ROM/RAM mutation, PCM copy, or complete campaign is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
from _harness import McpSession, MESEN_EXE, _free_tcp_port, Reporter, run_frames_exact, read_block
from _harness import exact_input_edge
import game_bor_startup_select as startup


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.rom = a.rom.resolve(); a.output = a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=True)
    lua = a.output / 'observer.lua'
    lua.write_text('''local active=false;local selected=false;local fields=0
local counts={};local events={}
emu.addMemoryCallback(function(addr,value)
 if not active or fields>=4 then return end
 counts[addr]=(counts[addr] or 0)+1
 if addr==0x2100 or addr==0x420b or addr==0x420c then
  local s=emu.getState()
  events[#events+1]={address=addr,value=value,scanline=s['ppu.scanline'],masterClock=s['masterClock']}
 end
end,emu.callbackType.write,0x2100,0x437f,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 local state=emu.read(STATE,emu.memType.snesMemory)+256*emu.read(STATE+1,emu.memType.snesMemory)
 if state==CHARSELECT then selected=true end
 if active and fields<4 then
  fields=fields+1
  local cs={};local es={}
  for addr,n in pairs(counts) do cs[#cs+1]=string.format('"%d":%d',addr,n) end
  for _,e in ipairs(events) do es[#es+1]=string.format('{"address":%d,"value":%d,"scanline":%d,"masterClock":%d}',e.address,e.value,e.scanline,e.masterClock) end
  emu.log('M4BUS|{"field":'..fields..',"counts":{'..table.concat(cs,',')..'},"events":['..table.concat(es,',')..']}')
  counts={};events={}
 end
 if selected and state==PLAYING then active=true end
end,emu.eventType.endFrame)
'''.replace('STATE',str(startup.STATE)).replace('CHARSELECT',str(startup.CHARSELECT))
        .replace('PLAYING',str(startup.PLAYING)), encoding='utf-8')
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv, **kwargs): return subprocess.Popen([*argv, str(lua)], **kwargs)
            with patch.object(module, 'subprocess', SimpleNamespace(Popen=launch,
                    DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter = Reporter('M4-STATIC-SMOKE', kind='GATE')
    with Observed(rom=a.rom, mesen=MESEN_EXE, port=_free_tcp_port(), stderr_log=a.output/'mesen.log') as m:
        # This is already a fresh emulator process. Reset removes the attached
        # observer on this Mesen build; retain cold boot while skipping reset.
        with patch.object(m, 'reset_emulator', return_value=None):
            startup.cold_to_title(m, reporter)
        startup.title_to_charselect(m)
        exact_input_edge(m, m.BTN_START, 1, port=0)
        reporter.check('Kula selection reaches PLAYING', startup.wait_state(m, startup.PLAYING, 300))
        kula_index = next(index for index, entry in startup.normal_player_entries('bor-original')
                          if startup.entry_name(entry).upper() == 'KULA')
        reporter.check('Kula source roster identity', startup.u8(m, startup.P1+startup.CHAR_ROSTER_INDEX)==kula_index)
        campaign = [startup.u8(m, addr) for addr in (startup.CAMPAIGN_ID, startup.CAMPAIGN_ORDINAL, startup.STAGE_INDEX)]
        # Persistent-SA1 candidates bind selected source sets to campaign 3.
        reporter.check('persistent source campaign first stage', campaign == [3, 0, 0])
        run_frames_exact(m, 12)
        error = read_block(m, 0x7E4A58, 32)[0]
        reporter.check('static source presentation has no admission fault', error == 0)
        reporter.check('first stage remains PLAYING', startup.u16(m, startup.STATE) == startup.PLAYING)
        shot = m.tool('take_screenshot', {'format':'path'})
    shutil.copyfile(shot['path'], a.output/'screenshot.png')
    log = (a.output/'mesen.log').read_text(encoding='utf-8', errors='replace')
    samples = [json.loads(line.split('M4BUS|',1)[1]) for line in log.splitlines() if 'M4BUS|' in line]
    reporter.check('four bounded production fields observed', len(samples) == 4)
    result = dict(rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),
        checks=reporter.results, campaign_state=campaign, source_visual_error=error, bus_samples=samples,
        scope='Original BOR Easy Kula selector/first-stage only; no campaign traversal or new raster admission.',
        no_pcm_copies=True)
    (a.output/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    reporter.finish()


if __name__ == '__main__': main()
