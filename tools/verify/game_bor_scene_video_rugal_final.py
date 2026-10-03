#!/usr/bin/env python3
"""Focused O2 Rugal natural/real-input regression."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import open_session, run_frames_exact, exact_input_edge, read_block, pasm_constant_in

def c(f, n): return pasm_constant_in(f, n)
STATE=c('src/core/game_state.pasm','Game_State'); SCENE=c('src/core/game_state.pasm','GAME_STATE_SCENE_FRAME'); TITLE=c('src/core/game_state.pasm','GAME_STATE_TITLE')
REQ=c('src/main.pasm','SceneVideo_TestRequest'); SID=c('src/main.pasm','SceneVideo_RequestedSceneId'); ACTIVE=c('src/main.pasm','SceneVideo_TestActive'); SEQ_ACTIVE=c('src/main.pasm','SceneVideo_SequenceActive'); PLAY_STATE=c('src/main.pasm','SceneVideo_PlayState'); PROBE=c('src/main.pasm','SceneVideo_MsuDmaProbe'); ERR=c('src/main.pasm','SceneVideo_TestError')
PRESENTED=c('src/main.pasm','SceneVideo_PlayPresented'); LATE=c('src/main.pasm','SceneVideo_PlayLateCount'); RETRIES=c('src/main.pasm','SceneVideo_PlayDmaRetries'); COMPLETE=c('src/main.pasm','SceneVideo_PlayCompletion'); AUDIO=c('src/main.pasm','SceneVideo_PlayAudioStartCount'); AUDIO_REPEAT=c('src/main.pasm','SceneVideo_PlayAudioRepeat'); SKIP=c('src/main.pasm','SceneVideo_PlaySkipCount'); SKIP_SWAPS=c('src/main.pasm','SceneVideo_PlaySkipSwaps'); SWAPS=c('src/main.pasm','SceneVideo_PlaySwaps'); RAW=c('src/main.pasm','SceneVideo_InputRawAtSkip'); TRIG=c('src/main.pasm','SceneVideo_InputTriggerAtSkip'); SEEN=c('src/main.pasm','SceneVideo_TestRequestSeen'); CONSUMED=c('src/main.pasm','SceneVideo_TestRequestConsumed'); TRANS=c('src/main.pasm','SceneVideo_SequenceTransitions'); SEQ_AUDIO=c('src/main.pasm','SceneVideo_SequenceAudioStarts'); SEQ_COMPLETE=c('src/main.pasm','SceneVideo_SequenceCompletion'); LOADS=c('src/main.pasm','SceneVideo_LoadCount'); PLAY_STATE=c('src/main.pasm','SceneVideo_PlayState'); NEXT=c('src/main.pasm','SceneVideo_PlayNext'); FCOUNT=c('src/main.pasm','SceneVideo_SequenceFrameCount'); FDUR=c('src/main.pasm','SceneVideo_PlayFrameDuration'); BUDGET=c('src/main.pasm','SceneVideo_PlayFrameBudget'); PHASE=c('src/main.pasm','SceneVideo_PlayTimingPhase')

def u8(m,a): return read_block(m,a,32)[0]
def u16(m,a): return int.from_bytes(read_block(m,a,32)[:2], 'little')

def reset(m):
    m.reset_emulator()
    for a in (REQ, ACTIVE, SEQ_ACTIVE, PLAY_STATE, PROBE, ERR, SKIP): m.write_u8(a, 0)
    for a in (SEEN, CONSUMED, PRESENTED, LATE, RETRIES, COMPLETE, AUDIO, SWAPS, TRANS, SEQ_AUDIO, SEQ_COMPLETE, LOADS, NEXT, FCOUNT, FDUR, FDUR+2, BUDGET, BUDGET+2, PHASE, PHASE+2): m.write_u16(a, 0)
    m.write_u8(SID, 1)
    m.write_u16(STATE, TITLE); m.write_u16(STATE+2, TITLE)
    run_frames_exact(m, 180)

def start(m):
    m.write_u8(PROBE, 0); m.write_u8(SID, 1); m.write_u16(REQ, 1); m.write_u16(STATE, SCENE)

def natural():
    with open_session(__file__, boot_wait=2.0) as m:
        reset(m); start(m)
        for _ in range(30):
            run_frames_exact(m, 240)
            if u16(m, STATE) == TITLE: break
        print('natural', {'state':u16(m,STATE), 'presented':u16(m,PRESENTED), 'late':u16(m,LATE), 'retries':u16(m,RETRIES), 'complete':u16(m,COMPLETE), 'audio':u16(m,AUDIO), 'repeat':u8(m,AUDIO_REPEAT), 'error':u8(m,ERR), 'loads':u16(m,LOADS), 'play_state':u8(m,PLAY_STATE), 'next':u16(m,NEXT), 'count':int.from_bytes(read_block(m,FCOUNT,32)[:4],'little'), 'duration':u16(m,FDUR), 'budget':int.from_bytes(read_block(m,BUDGET,32)[:4],'little'), 'phase':int.from_bytes(read_block(m,PHASE,32)[:4],'little')}, flush=True)
        assert u16(m,STATE)==TITLE and u16(m,PRESENTED)==126 and u16(m,LATE)==0 and u16(m,RETRIES)==0 and u16(m,COMPLETE)==1 and u16(m,AUDIO)==1 and u8(m,AUDIO_REPEAT)==0 and u8(m,ERR)==0

def skip():
    with open_session(__file__, boot_wait=2.0) as m:
        reset(m); start(m)
        for _ in range(20):
            run_frames_exact(m, 10)
            if u16(m,PRESENTED) >= 20: break
        before=u16(m,SWAPS)
        exact_input_edge(m, m.BTN_A, 1, port=0)
        run_frames_exact(m, 5)
        print('skip', {'presented':u16(m,PRESENTED), 'before_swaps':before, 'swaps':u16(m,SWAPS), 'skip_swaps':u16(m,SKIP_SWAPS), 'raw':u16(m,RAW), 'trigger':u16(m,TRIG), 'skip':u8(m,SKIP), 'state':u16(m,STATE)}, flush=True)
        assert u16(m,STATE)==TITLE and u8(m,SKIP)==1 and u16(m,RAW)!=0 and u16(m,TRIG)!=0 and u16(m,SKIP_SWAPS)==u16(m,SWAPS) and u16(m,COMPLETE)==0

if __name__ == '__main__':
    natural(); skip(); print('RUGAL FINAL: PASS')
