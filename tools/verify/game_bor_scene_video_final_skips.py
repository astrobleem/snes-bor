#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import open_session, run_frames_exact, exact_input_edge, read_block, pasm_constant_in

def c(f,n): return pasm_constant_in(f,n)
STATE=c('src/core/game_state.pasm','Game_State'); SCENE=c('src/core/game_state.pasm','GAME_STATE_SCENE_FRAME'); TITLE=c('src/core/game_state.pasm','GAME_STATE_TITLE')
REQ=c('src/main.pasm','SceneVideo_TestRequest'); SID=c('src/main.pasm','SceneVideo_RequestedSceneId'); CLIP=c('src/main.pasm','SceneVideo_SequenceClipId'); FRAME=c('src/main.pasm','SceneVideo_PlayVisible'); PRESENTED=c('src/main.pasm','SceneVideo_PlayPresented'); SKIP=c('src/main.pasm','SceneVideo_PlaySkipCount'); SKIP_SWAPS=c('src/main.pasm','SceneVideo_PlaySkipSwaps'); SWAP=c('src/main.pasm','SceneVideo_PlaySwaps'); RAW=c('src/main.pasm','SceneVideo_InputRawAtSkip'); TRIG=c('src/main.pasm','SceneVideo_InputTriggerAtSkip'); PROBE=c('src/main.pasm','SceneVideo_MsuDmaProbe'); ACTIVE=c('src/main.pasm','SceneVideo_TestActive'); SEQ_ACTIVE=c('src/main.pasm','SceneVideo_SequenceActive'); PLAY_STATE=c('src/main.pasm','SceneVideo_PlayState'); ERR=c('src/main.pasm','SceneVideo_TestError')
def r8(m,a): return read_block(m,a,32)[0]
def r16(m,a): return int.from_bytes(read_block(m,a,32)[:2],'little')
def run(target_clip,target_frame):
 with open_session(__file__,boot_wait=2.0) as m:
  m.reset_emulator(); m.write_u16(STATE,TITLE); m.write_u16(STATE+2,TITLE); run_frames_exact(m,180)
  m.write_u8(ACTIVE,0); m.write_u8(SEQ_ACTIVE,0); m.write_u8(PLAY_STATE,0); m.write_u8(PROBE,0)
  m.write_u8(SKIP,0); m.write_u8(ERR,0); m.write_u8(SID,2); m.write_u16(REQ,1); m.write_u16(STATE,SCENE)
  max_steps = 120 if target_clip == 2 else 500
  for _ in range(max_steps):
   if r8(m,CLIP)==target_clip and r16(m,FRAME)>=target_frame: break
   run_frames_exact(m,10)
  print('at',target_clip,r8(m,CLIP),r16(m,FRAME),r16(m,PRESENTED),r16(m,SWAP),r8(m,ACTIVE),r8(m,SEQ_ACTIVE),r16(m,STATE),flush=True)
  assert r8(m,CLIP)==target_clip and r16(m,FRAME)>=target_frame
  before=r16(m,SWAP); exact_input_edge(m,m.BTN_A,1,0); run_frames_exact(m,5)
  print('skip_telemetry', target_clip, r8(m,SKIP), r16(m,RAW), r16(m,TRIG), r16(m,SWAP), before, r16(m,SKIP_SWAPS), r16(m,STATE), flush=True)
  assert r8(m,SKIP)==1 and r16(m,RAW)!=0 and r16(m,TRIG)!=0 and r16(m,SKIP_SWAPS)==r16(m,SWAP) and r16(m,STATE)==TITLE
  print('PASS',target_clip,target_frame,flush=True)
if __name__=='__main__':
 run(2,20); run(5,256); run(6,0)
