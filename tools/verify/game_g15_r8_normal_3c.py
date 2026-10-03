#!/usr/bin/env python3
"""Focused G15-R8 Normal 3C import and authored-next gate."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant_in, read_block, poll_until, exact_input_edge
import game_bor_startup_select as startup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT); sys.path[:0] = [os.path.join(ROOT,'tools','bor_converter'), os.path.join(ROOT,'tools','bg_converter')]
import build_rom
from pak_extract import extract
from level_parse import parse_level
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent
from bor_levels import parse_levels_from_pak
PAK=os.path.join(ROOT,'Beats of Rage Original [v.3.0 Build 4086].pak'); EASY=r'DATA\EASY\3CEASY.TXT'; NORMAL=r'DATA\NORMAL\3C.TXT'
STATE=pasm_constant_in('src/core/game_state.pasm','Game_State'); PLAYING=pasm_constant_in('src/core/game_state.pasm','GAME_STATE_PLAYING'); STAGECLEAR=pasm_constant_in('src/core/game_state.pasm','GAME_STATE_STAGECLEAR'); TITLE=pasm_constant_in('src/core/game_state.pasm','GAME_STATE_TITLE'); CAMPAIGN=pasm_constant_in('src/core/game_state.pasm','Game_CampaignId'); ORDINAL=pasm_constant_in('src/core/game_state.pasm','Game_CampaignOrdinal'); STAGE=pasm_constant_in('src/core/game_state.pasm','Game_StageIndex'); PENDING=pasm_constant_in('src/core/game_state.pasm','Stage_LoadPending'); TIMES=pasm_constant_in('src/core/options.pasm','Bor_TimesCompleted'); ACTIVE=pasm_constant_in('src/main.pasm','StageComplete_Active'); ADVANCES=pasm_constant_in('src/main.pasm','StageComplete_AdvanceCount'); MUSIC=pasm_constant_in('src/main.pasm','Music_LastTrack'); SPAWN=pasm_constant_in('src/core/spawn.pasm','Spawn_Count')
def u8(m,a): return read_block(m,a,32)[0]
def u16(m,a):
 b=read_block(m,a,32); return b[0]|b[1]<<8
def source_gate(r):
 t={p:extract(PAK,p).decode('latin1') for p in (EASY,NORMAL)}; lv={p:parse_level(t[p],p) for p in t}; ev={p:parse_spawns(t[p]) for p in t}; e,n=lv[EASY],lv[NORMAL]; ns=[x for x in ev[NORMAL] if isinstance(x,SpawnEvent)]; es=[x for x in ev[EASY] if isinstance(x,SpawnEvent)]
 r.check('authoritative Normal 3C source exists',NORMAL in t)
 r.check('Boat3 presentation is source-identical',(n.background,n.frontpanel,n.panels,n.order)==(e.background,e.frontpanel,e.panels,e.order))
 r.check('Normal 3C uses supported right scroll and authored 1boss music','direction left' not in t[NORMAL].lower() and 'direction down' not in t[NORMAL].lower() and 'music\t\tdata/music/1boss.bor' in t[NORMAL].lower())
 r.check('Normal and Easy 3C each have 31 records / 30 spawns / 1 group / 0 waits',len(ev[NORMAL])==31 and len(ev[EASY])==31 and len(ns)==30 and len(es)==30 and sum(isinstance(x,GroupEvent) for x in ev[NORMAL])==1 and sum(isinstance(x,WaitEvent) for x in ev[NORMAL])==0)
 r.check('Normal-vs-Easy delta is Robert health 400 vs 300',any(x.character.lower()=='robert' and x.health==400 and x.boss for x in ns) and any(x.character.lower()=='robert' and x.health==300 and x.boss for x in es))
 r.check('3C items and identities resolve',any(x.item=='meat' for x in ns) and {x.character.lower() for x in ns} <= {'furnace','steamer','1up','crate','robert','yashiro','ralf','shermie',"k'",'angel','joe'})
 normal=next(s for s in parse_levels_from_pak(PAK) if s.name=='Normal').entries; r.check('authored next is after 3C',normal[8][0]=='file' and normal[9][0]=='next')
def catalog_gate(r):
 found=[(i,s) for i,s in enumerate(build_rom.STAGE_CONFIGS) if s['source_level'].upper()==NORMAL]; r.check('Normal 3C is appended physical index 28',len(found)==1 and found[0][0]==len(build_rom.STAGE_CONFIGS)-1==28); idx,st=found[0]; r.check('authored and packed queues are independently 31',len(open(os.path.join(ROOT,st['spawn']),'rb').read())//10==31); r.check('Normal map is 22..28',build_rom.CAMPAIGN_STAGE_MAPS['BOR_NORMAL_1A_INTERNAL']==[22,23,24,25,26,27,28]); g=open(os.path.join(ROOT,'tools/audio/campaign_config.pasm',),encoding='ascii').read(); r.check('flags are 0,0,1,1,0,0,1','Campaign_BorNormalDev_NextFlags:\n    .db 0, 0, 1, 1, 0, 0, 1' in g); r.check('Normal unavailable','BorSet_ContentAvailable:\n    .db 1, 0, 0, 0' in g); a=open(os.path.join(ROOT,'tools/audio/audio_music_ids.pasm'),encoding='ascii').read(); r.check('music table has 29 stages','Music_StageTrackCount = 29' in a); return idx
def setup(m,ordinal):
 startup.cold_to_title(m,Reporter('startup',kind='SUB')); startup.select_case(m,Reporter('select',kind='SUB'),'KULA'); m.run_frames(60); m.write_u8(CAMPAIGN,3); m.write_u8(ORDINAL,ordinal); m.write_u8(PENDING,1); m.write_u16(STATE,STAGECLEAR); return poll_until(m,lambda s:u16(s,STATE)==PLAYING,max_frames=900)
def runtime_gate(r,stage):
 with open_session(__file__) as m:
  loaded=setup(m,5); r.check('3B -> 3C direct typed dispatch',loaded and u16(m,STAGE)==stage); r.check('3C queue is 31',loaded and u8(m,SPAWN)==31); r.check('3C authored music is selected normally',loaded and u8(m,MUSIC)==1); before=(u8(m,TIMES),u16(m,ADVANCES)); m.write_u8(PENDING,1); m.write_u16(STATE,STAGECLEAR); entered=poll_until(m,lambda s:u8(s,ACTIVE)==1,max_frames=30); r.check('3C authored next enters showcomplete',entered and u8(m,MUSIC)==3); r.check('3C completion precedes progression and no set credit',entered and u8(m,ORDINAL)==6 and u8(m,TIMES)==before[0]); exact_input_edge(m,m.BTN_A,1); finished=poll_until(m,lambda s:u16(s,STATE)==TITLE,max_frames=120); r.check('action-button skip resolves showcomplete to DEV TITLE',finished and u8(m,ACTIVE)==0); r.check('partial Normal does not credit set completion',u8(m,TIMES)==before[0])
def main():
 r=Reporter('G15-BATCH-R8-NORMAL-3C',kind='GATE'); source_gate(r); runtime_gate(r,catalog_gate(r)); r.finish()
if __name__=='__main__': main()
