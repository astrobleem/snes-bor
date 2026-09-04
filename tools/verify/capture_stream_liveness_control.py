#!/usr/bin/env python3
"""Harness-only physical voice-0 control for a real diesound stream."""
from __future__ import annotations
import argparse, hashlib, json, os, struct, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'/'verify'))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block
import audio_semantic_diesound as semantic
ACTIVE=pasm_constant('AudioSemantic_FootDieStreamActive')
PENDING=pasm_constant('TadPrivate_stream_pending')
OFFSET=pasm_constant('TadPrivate_stream_source_offset')
LENGTH=pasm_constant('AudioStream_SourceLength')
SOURCE=pasm_constant('AudioStream_SourceId')
COMMAND=pasm_constant('TadPrivate_previousCommand')
CHAR_SELECT=pasm_constant('CharSelect_Index')
CHAR_ZP_LEN=pasm_constant('CHAR_ZP_LEN')
CHAR_HP=pasm_constant('CHAR_HP')
CHAR_ROSTER_INDEX=pasm_constant('CHAR_ROSTER_INDEX')
CHAR_INPUT_DRIVEN=pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_AI=pasm_constant('CHAR_INPUT_DRIVEN_AI')
SPAWN_INDEX=pasm_constant_in('src/core/spawn.pasm','Spawn_Index')
SPAWN_COUNT=pasm_constant_in('src/core/spawn.pasm','Spawn_Count')
SPAWN_TABLE=pasm_constant_in('src/core/spawn.pasm','SpawnTable_Wram')
SPAWN_KIND_PROP=pasm_constant_in('src/core/spawn.pasm','SPAWN_KIND_PROP')
MSU_STREAM_BUSY=pasm_constant('Msu1_StreamBusy')
SPAWN_GROUP_MIN=pasm_constant_in('src/core/spawn.pasm','Spawn_GroupMin')
SPAWN_GROUP_MAX=pasm_constant_in('src/core/spawn.pasm','Spawn_GroupMax')
SPAWN_WAITING=pasm_constant_in('src/core/spawn.pasm','Spawn_Waiting')
SPAWN_SCRATCH_ROSTER=pasm_constant_in('src/core/spawn.pasm','Spawn_ScratchRosterIdx')
ENTITY1_IS_BOSS=pasm_constant_in('src/core/spawn.pasm','Entity1_IsBoss')
SCREEN_POS_X=0x7E1601
ENTITY1=0x7E0A00+CHAR_ZP_LEN
ENTITY_BASES=[0x7E0A00+i*CHAR_ZP_LEN for i in range(4)]
def u16(m,addr):
 b=read_block(m,addr,32); return b[0]|(b[1]<<8)
def spawn_target(m,roster):
 """Use the real Spawn_Play reassignment path for the dying target."""
 record=struct.pack('<HHBBBBBB',0,100,100,0,SPAWN_KIND_PROP,64,0,roster)
 m.write_memory('snesMemory',SPAWN_TABLE,record.hex())
 m.write_u8(SPAWN_COUNT,1); m.write_u8(SPAWN_INDEX,0)
 m.write_u16(SCREEN_POS_X,0); m.write_u8(SPAWN_GROUP_MIN,100); m.write_u8(SPAWN_GROUP_MAX,100); m.write_u8(SPAWN_WAITING,0)
 m.write_u8(ENTITY1+CHAR_HP,0)
 m.write_u8(ENTITY1+CHAR_INPUT_DRIVEN,CHAR_INPUT_DRIVEN_AI)
 for _ in range(120):
  m.run_frames(1); m.pause()
  if read_block(m,SPAWN_INDEX,32)[0] == 1:
   break
 if read_block(m,SPAWN_INDEX,32)[0] != 1:
  raise RuntimeError(f'Spawn_Play did not consume fixture record; msu_busy={read_block(m,MSU_STREAM_BUSY,32)[0]}')
 live={slot:read_block(m,base+CHAR_ROSTER_INDEX,32)[0] for slot,base in enumerate(ENTITY_BASES[1:],1)}
 if live[1] != roster:
  raise RuntimeError(f'Spawn_Play did not assign roster {roster}: live={live}, scratch_roster={read_block(m,SPAWN_SCRATCH_ROSTER,32)[0]}, is_boss={read_block(m,ENTITY1_IS_BOSS,32)[0]}')
 return 1
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--roster',type=int,required=True,help='Runtime roster index for the real lethal target')
 parser.add_argument('--output',type=Path,required=True,help='Raw selected-voice capture path')
 args=parser.parse_args()
 out=args.output.resolve(); arm=Path(str(out)+'.arm')
 env={'MESEN_VOICE_CAPTURE_PATH':str(out),'MESEN_VOICE_CAPTURE_VOICE':'0','MESEN_VOICE_CAPTURE_ARM_FILE':str(arm)}
 for p in (out,Path(str(out)+'.json'),Path(str(out)+'.trace'),arm): p.unlink(missing_ok=True)
 with open_session(__file__,env=env) as m:
  semantic.boot(m)
  for _ in range(300):
   if read_block(m,ACTIVE,32)[0] == 0 and read_block(m,PENDING,32)[0] == 0:
    break
   m.run_frames(1); m.pause()
  if read_block(m,ACTIVE,32)[0] != 0 or read_block(m,PENDING,32)[0] != 0:
   raise RuntimeError('pre-fixture stream did not become idle')
  target_slot=spawn_target(m,args.roster); semantic.clear_observation(m); arm.touch(); roster_before_hit=read_block(m,ENTITY_BASES[target_slot]+CHAR_ROSTER_INDEX,32)[0]; before=semantic.u16(m,semantic.REQ_COUNT)
  _, _, _, rows, roster_samples=semantic.kill_spawned_target(m,target_slot)
  roster_after_hit=read_block(m,ENTITY_BASES[target_slot]+CHAR_ROSTER_INDEX,32)[0]
  snapshots=[]
  for frame in range(30):
   snapshots.append({'frame':frame,'active':read_block(m,ACTIVE,32)[0],
                     'pending':read_block(m,PENDING,32)[0],
                     'offset':u16(m,OFFSET),'length':u16(m,LENGTH),
                     'source':read_block(m,SOURCE,32)[0],
                     'command':read_block(m,COMMAND,32)[0]})
   m.run_frames(1); m.pause()
  # Stream source transfer is paced by the consumer.  A fixed tail can end
  # while a valid long source is still in flight, so wait for the producer's
  # own completion state instead.
  for _ in range(900):
   if u16(m,OFFSET) >= u16(m,LENGTH) and read_block(m,PENDING,32)[0] == 0:
    break
   m.run_frames(1); m.pause()
  if u16(m,OFFSET) < u16(m,LENGTH) or read_block(m,PENDING,32)[0] != 0:
   raise RuntimeError('stream source did not finish within bounded tail')
  after=semantic.u16(m,semantic.REQ_COUNT)
  final_stream_state={'active':read_block(m,ACTIVE,32)[0],
                      'pending':read_block(m,PENDING,32)[0],
                      'offset':u16(m,OFFSET),'length':u16(m,LENGTH),
                      'source':read_block(m,SOURCE,32)[0],
                      'command':read_block(m,COMMAND,32)[0]}
 raw=out.read_bytes() if out.exists() else b''; side={}
 sp=Path(str(out)+'.json')
 if sp.exists(): side=json.loads(sp.read_text(encoding='utf-8').splitlines()[0])
 print(json.dumps({**side,'roster':args.roster,'spawned_slot':target_slot,'roster_before_hit':roster_before_hit,'roster_samples':roster_samples,'roster_after_hit':roster_after_hit,'semantic_delta':(after-before)&0xffff,'semantic_rows':rows,'capture_bytes':len(raw),'capture_sha256':hashlib.sha256(raw).hexdigest(),'snapshots':snapshots,'final_stream_state':final_stream_state},sort_keys=True))
if __name__=='__main__': main()
