"""Bounded read-only trace of the inherited source block admission stall."""
import argparse,json,subprocess,hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,read_block,exact_input_edge
from actor_s5_entity_fixture import symbols
import game_bor_startup_select as startup

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 syms=symbols(Path(__file__).resolve().parents[2]/'src/main.sym');lua=a.output/'trace.lua'
 text="""local mt=emu.memType.snesMemory;local count=0;local stopped=false
local function word(a)return emu.read(a,mt)+256*emu.read(a+1,mt)end
local function probe(kind)
 if stopped or word(STATE)~=PLAYING or word(0x7e4b6a)~=1 then return end
 if count<96 then
  count=count+1;local s=emu.getState()
  emu.log('M4RES|{\"event\":\"'..kind..'\",\"scan\":'..word(0x7e4b92)..',\"piece\":'..word(0x7e4b5e)..',\"block\":'..word(0x7e4b80)..',\"slot18state\":'..word(0x7e4c92)..',\"clock\":'..s.masterClock..'}')
 end
 if kind=='claim' and word(0x7e4b5e)==8 then stopped=true;emu.breakExecution()end
end
emu.addMemoryCallback(function()probe('find_miss')end,emu.callbackType.exec,MISS,MISS,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()probe('claim')end,emu.callbackType.exec,CLAIM,CLAIM,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()probe('piece')end,emu.callbackType.exec,PIECE,PIECE,emu.cpuType.snes,mt)
""".replace('STATE',str(startup.STATE)).replace('PLAYING',str(startup.PLAYING)).replace('MISS',str(syms['SourceVisual_FindBlock__miss'])).replace('CLAIM',str(syms['SourceVisual_AllocateBlock__claim'])).replace('PIECE',str(syms['SourceVisual_PrepareBlocks__piece']))
 lua.write_text(text)
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 reporter=Reporter('M4-STATIC-RESIDENCY-TRACE',kind='GATE')
 with Observed(rom=a.rom.resolve(),mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
  with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
  startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
  if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('TRACE_PLAYING_REQUIRED')
  m.run_until(max_frames=180)
  r=dict(cpu=m.get_cpu_state(),state_hex=read_block(m,0x7e4b50,128).hex(),cache_hex=read_block(m,0x7e4c00,512).hex(),rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest())
 log=(a.output/'mesen.log').read_text(errors='replace');r['events']=[json.loads(line.split('M4RES|')[1]) for line in log.splitlines() if 'M4RES|'in line]
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['cpu']));print(json.dumps(r['events']))
if __name__=='__main__':main()
