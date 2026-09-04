#!/usr/bin/env python3
"""Harness-only table-read provenance for authored frame backend selection."""
from __future__ import annotations
import os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'/'verify'))
from _harness import open_session
import audio_semantic_diesound as semantic
from game_g7_jump import (CHAR_SELECTED, CHAR_THROW_ZPOS, CHAR_THROW_ZVEL, ENTITY_BASES,
                          load_leo_onto_player, neutralize_ai)

STREAM_BRANCH=0x0C908A
TABLE=0x0C916D
TABLE_END=TABLE+78*8-1

def main():
 os.environ['MESEN_EXE']=r'E:\\gh\\Mesen2-runtime\\voice-capture-5fb1f1b\\Mesen.exe'
 os.environ['USE_STANDARD_MESEN']='1'
 with open_session(__file__) as m:
  semantic.boot(m); neutralize_ai(m); load_leo_onto_player(m,12); neutralize_ai(m)
  for _ in range(30): m.run_frames(1); m.pause()
  m.write_u8(ENTITY_BASES[0]+CHAR_SELECTED,0)
  m.write_u16(ENTITY_BASES[0]+CHAR_THROW_ZPOS,0); m.write_u16(ENTITY_BASES[0]+CHAR_THROW_ZVEL,0)
  stream=m.add_exec_hook(STREAM_BRANCH, STREAM_BRANCH)
  reads=m.add_read_hook(TABLE, TABLE_END)
  m.set_input(m.BTN_A,1); m.run_frames(1); m.pause(); m.set_input(0,1)
  result=m.run_until(60,stream)
  base_bytes=m.read_memory('snesMemory',0x7e28de,32)
  base=base_bytes[0] | (base_bytes[1]<<8)
  hp=m.read_memory('snesMemory',base+semantic.CHAR_HP,32)[0]
  events=m.drain_notifications()
  rows=[e.get('params',{}) for e in events if e.get('params',{}).get('handle')==reads]
  spin_backend=TABLE+48*8+5
  print({'result':result,'entity_base':hex(base),'entity_hp':hp,'spin_backend_address':spin_backend,
         'spin_backend_reads':[r for r in rows if r.get('address')==spin_backend],
         'table_reads_tail':rows[-12:]})
  m.remove_hook(stream); m.remove_hook(reads)
if __name__=='__main__': main()
