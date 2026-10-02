#!/usr/bin/env python3
"""Focused G15-R10 Normal 4B gate."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter,open_session,pasm_constant_in,read_block,poll_until,exact_input_edge
import game_bor_startup_select as startup
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'));sys.path.insert(0,ROOT);sys.path[:0]=[os.path.join(ROOT,'tools','bor_converter'),os.path.join(ROOT,'tools','bg_converter')]
import build_rom
from pak_extract import extract
from level_parse import parse_level
from spawn_parse import parse_spawns,SpawnEvent,WaitEvent,GroupEvent
from bor_levels import parse_levels_from_pak
PAK=os.path.join(ROOT,'Beats of Rage Original [v.3.0 Build 4086].pak');EASY=r'DATA\EASY\4BEASY.TXT';NORMAL=r'DATA\NORMAL\4B.TXT'
STATE=pasm_constant_in('src/core/game_state.pasm','Game_State');PLAYING=pasm_constant_in('src/core/game_state.pasm','GAME_STATE_PLAYING');STAGECLEAR=pasm_constant_in('src/core/game_state.pasm','GAME_STATE_STAGECLEAR');TITLE=pasm_constant_in('src/core/game_state.pasm','GAME_STATE_TITLE');CAMPAIGN=pasm_constant_in('src/core/game_state.pasm','Game_CampaignId');ORDINAL=pasm_constant_in('src/core/game_state.pasm','Game_CampaignOrdinal');STAGE=pasm_constant_in('src/core/game_state.pasm','Game_StageIndex');PENDING=pasm_constant_in('src/core/game_state.pasm','Stage_LoadPending');TIMES=pasm_constant_in('src/core/options.pasm','Bor_TimesCompleted');ACTIVE=pasm_constant_in('src/main.pasm','StageComplete_Active');ADVANCES=pasm_constant_in('src/main.pasm','StageComplete_AdvanceCount');MUSIC=pasm_constant_in('src/main.pasm','Music_LastTrack');SPAWN=pasm_constant_in('src/core/spawn.pasm','Spawn_Count')
def u8(m,a):return read_block(m,a,32)[0]
def u16(m,a):
 b=read_block(m,a,32);return b[0]|b[1]<<8
def source(r):
 t={p:extract(PAK,p).decode('latin1') for p in(EASY,NORMAL)};lv={p:parse_level(t[p],p) for p in t};ev={p:parse_spawns(t[p]) for p in t};n,e=lv[NORMAL],lv[EASY];ns=[x for x in ev[NORMAL] if isinstance(x,SpawnEvent)];es=[x for x in ev[EASY] if isinstance(x,SpawnEvent)];r.check('authoritative source exists',NORMAL in t);r.check('Warehouse presentation reused',(n.background,n.frontpanel,n.panels,n.order)==(e.background,e.frontpanel,e.panels,e.order));r.check('necktie/bossmusic supported','music\t\tdata/music/necktie.bor' in t[NORMAL].lower() and 'bossmusic\tdata/music/1boss.bor' in t[NORMAL].lower());r.check('queue counts Normal 52/44 and Easy 50/42',len(ev[NORMAL])==52 and len(ns)==44 and len(ev[EASY])==50 and len(es)==42 and sum(isinstance(x,WaitEvent) for x in ev[NORMAL])==4 and sum(isinstance(x,GroupEvent) for x in ev[NORMAL])==4);r.check('Normal deltas preserve extra Jhun and health/placement',any(x.character.lower()=='jhun' and x.health is None for x in ns) and any(x.character.lower()=='angel' and x.health==120 for x in ns) and any(x.character.lower()=="k'" and x.at==985 and x.coords==(-30,180) for x in ns));r.check('items and identities resolve',any(x.item and x.item.lower()=='gold' for x in ns) and any(x.item and x.item.lower()=='meat' for x in ns));q=next(s for s in parse_levels_from_pak(PAK) if s.name=='Normal').entries;r.check('4A/4B no-next then next boundary',q[10][0]=='file' and q[11][0]=='file' and q[12][0]=='next')
def catalog(r):
 f=[(i,s) for i,s in enumerate(build_rom.STAGE_CONFIGS) if s['source_level'].upper()==NORMAL];r.check('4B physical tail index 30',len(f)==1 and f[0][0]==len(build_rom.STAGE_CONFIGS)-1==30);r.check('packed queue count 52',len(open(os.path.join(ROOT,f[0][1]['spawn']),'rb').read())//10==52);r.check('Normal map 22..30',build_rom.CAMPAIGN_STAGE_MAPS['BOR_NORMAL_1A_INTERNAL']==list(range(22,31)));g=open(os.path.join(ROOT,'tools/audio/campaign_config.pasm'),encoding='ascii').read();r.check('flags 0,0,1,1,0,0,1,0,1','Campaign_BorNormalDev_NextFlags:\n    .db 0, 0, 1, 1, 0, 0, 1, 0, 1' in g);r.check('Normal unavailable','BorSet_ContentAvailable:\n    .db 1, 0, 0, 0' in g);r.check('music count 31','Music_StageTrackCount = 31' in open(os.path.join(ROOT,'tools/audio/audio_music_ids.pasm'),encoding='ascii').read());return 30
def start(m,o):
 startup.cold_to_title(m,Reporter('startup',kind='SUB'));startup.select_case(m,Reporter('select',kind='SUB'),'KULA');m.run_frames(60);m.write_u8(CAMPAIGN,3);m.write_u8(ORDINAL,o);m.write_u8(PENDING,1);m.write_u16(STATE,STAGECLEAR);return poll_until(m,lambda s:u16(s,STATE)==PLAYING,max_frames=900)
def runtime(r,stage):
 with open_session(__file__) as m:
  ok=start(m,7);r.check('4A -> 4B direct typed dispatch',ok and u16(m,STAGE)==stage);r.check('4B queue/music correct',ok and u8(m,SPAWN)==52 and u8(m,MUSIC)==10);before=u8(m,TIMES);m.write_u8(PENDING,1);m.write_u16(STATE,STAGECLEAR);r.check('4B authored next enters showcomplete',poll_until(m,lambda s:u8(s,ACTIVE)==1,max_frames=30) and u8(m,MUSIC)==3);exact_input_edge(m,m.BTN_A,1);r.check('showcomplete reaches DEV TITLE',poll_until(m,lambda s:u16(s,STATE)==TITLE,max_frames=180) and u8(m,ACTIVE)==0);r.check('partial Normal remains uncredited',u8(m,TIMES)==before)
def main():
 r=Reporter('G15-BATCH-R10-NORMAL-4B',kind='GATE');source(r);runtime(r,catalog(r));r.finish()
if __name__=='__main__':main()
