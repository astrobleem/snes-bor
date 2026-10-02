#!/usr/bin/env python3
"""Focused G15-R9 Normal 4A gate."""
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
PAK=os.path.join(ROOT,'Beats of Rage Original [v.3.0 Build 4086].pak');EASY=r'DATA\EASY\4AEASY.TXT';NORMAL=r'DATA\NORMAL\4A.TXT'
STATE=pasm_constant_in('src/core/game_state.pasm','Game_State');PLAYING=pasm_constant_in('src/core/game_state.pasm','GAME_STATE_PLAYING');STAGECLEAR=pasm_constant_in('src/core/game_state.pasm','GAME_STATE_STAGECLEAR');TITLE=pasm_constant_in('src/core/game_state.pasm','GAME_STATE_TITLE');CAMPAIGN=pasm_constant_in('src/core/game_state.pasm','Game_CampaignId');ORDINAL=pasm_constant_in('src/core/game_state.pasm','Game_CampaignOrdinal');STAGE=pasm_constant_in('src/core/game_state.pasm','Game_StageIndex');PENDING=pasm_constant_in('src/core/game_state.pasm','Stage_LoadPending');TIMES=pasm_constant_in('src/core/options.pasm','Bor_TimesCompleted');ACTIVE=pasm_constant_in('src/main.pasm','StageComplete_Active');ADVANCES=pasm_constant_in('src/main.pasm','StageComplete_AdvanceCount');MUSIC=pasm_constant_in('src/main.pasm','Music_LastTrack');SPAWN=pasm_constant_in('src/core/spawn.pasm','Spawn_Count')
def u8(m,a):return read_block(m,a,32)[0]
def u16(m,a):
 b=read_block(m,a,32);return b[0]|b[1]<<8
def source(r):
 t={p:extract(PAK,p).decode('latin1') for p in(EASY,NORMAL)};lv={p:parse_level(t[p],p) for p in t};ev={p:parse_spawns(t[p]) for p in t};n,e=lv[NORMAL],lv[EASY];ns=[x for x in ev[NORMAL] if isinstance(x,SpawnEvent)];es=[x for x in ev[EASY] if isinstance(x,SpawnEvent)];r.check('authoritative source exists',NORMAL in t);r.check('Pier presentation reused',(n.background,n.frontpanel,n.panels,n.order)==(e.background,e.frontpanel,e.panels,e.order));r.check('right scroll and scorcher supported','direction left' not in t[NORMAL].lower() and 'direction down' not in t[NORMAL].lower() and 'music\t\tdata/music/scorcher.bor' in t[NORMAL].lower());r.check('queue counts 63/51 and 4 waits/8 groups',len(ev[NORMAL])==63 and len(ns)==51 and len(ev[EASY])==55 and len(es)==43 and sum(isinstance(x,WaitEvent) for x in ev[NORMAL])==4 and sum(isinstance(x,GroupEvent) for x in ev[NORMAL])==8);r.check('Normal tuning and encounters differ faithfully',any(x.character.lower()=="biker-k'" and x.coords==(-130,165) for x in ns) and any(x.character.lower()=='jhun' and x.health==150 for x in ns) and any(x.character.lower()=='yashiro' and x.health==75 for x in ns));r.check('items and identities resolve',any(x.item and x.item.lower()=='meat' for x in ns) and any(x.item and x.item.lower()=='money' for x in ns) and {x.character.lower() for x in ns}<={'angel',"biker-k'",'box','crate','jhun',"k'",'ralf','shermie','yashiro'});q=next(s for s in parse_levels_from_pak(PAK) if s.name=='Normal').entries;r.check('no next after 4A',q[10][0]=='file' and q[11][0]=='file')
def catalog(r):
 f=[(i,s) for i,s in enumerate(build_rom.STAGE_CONFIGS) if s['source_level'].upper()==NORMAL];r.check('4A appended at physical 29',len(f)==1 and f[0][0]==len(build_rom.STAGE_CONFIGS)-1==29);r.check('packed queue count is 63',len(open(os.path.join(ROOT,f[0][1]['spawn']),'rb').read())//10==63);r.check('Normal map is 22..29',build_rom.CAMPAIGN_STAGE_MAPS['BOR_NORMAL_1A_INTERNAL']==list(range(22,30)));g=open(os.path.join(ROOT,'tools/audio/campaign_config.pasm'),encoding='ascii').read();r.check('flags 0,0,1,1,0,0,1,0','Campaign_BorNormalDev_NextFlags:\n    .db 0, 0, 1, 1, 0, 0, 1, 0' in g);r.check('Normal unavailable','BorSet_ContentAvailable:\n    .db 1, 0, 0, 0' in g);r.check('music count 30','Music_StageTrackCount = 30' in open(os.path.join(ROOT,'tools/audio/audio_music_ids.pasm'),encoding='ascii').read());return f[0][0]
def start(m,o):
 startup.cold_to_title(m,Reporter('startup',kind='SUB'));startup.select_case(m,Reporter('select',kind='SUB'),'KULA');m.run_frames(60);m.write_u8(CAMPAIGN,3);m.write_u8(ORDINAL,o);m.write_u8(PENDING,1);m.write_u16(STATE,STAGECLEAR);return poll_until(m,lambda s:u16(s,STATE)==PLAYING,max_frames=900)
def runtime(r,stage):
 with open_session(__file__) as m:
  ok=start(m,6);r.check('Normal 4A Stage_Load',ok and u16(m,STAGE)==stage);r.check('queue/music correct',ok and u8(m,SPAWN)==63 and u8(m,MUSIC)==12);before=(u8(m,TIMES),u16(m,ADVANCES));m.write_u8(PENDING,1);m.write_u16(STATE,STAGECLEAR);r.check('4A no-next bypasses showcomplete',poll_until(m,lambda s:u16(s,STATE)==TITLE,max_frames=60) and u8(m,ACTIVE)==0);r.check('DEV boundary no set credit', (u8(m,TIMES),u16(m,ADVANCES))==before)
 with open_session(__file__) as m:
  ok=start(m,5);m.write_u8(PENDING,1);m.write_u16(STATE,STAGECLEAR);entered=poll_until(m,lambda s:u8(s,ACTIVE)==1,max_frames=30);r.check('3C next enters showcomplete before 4A',entered and u8(m,MUSIC)==3 and u8(m,ORDINAL)==6);exact_input_edge(m,m.BTN_A,1);r.check('showcomplete then dispatches 4A without TITLE',poll_until(m,lambda s:u16(s,STATE)==PLAYING and u16(s,STAGE)==stage,max_frames=180) and u8(m,ORDINAL)==7);r.check('partial Normal remains uncredited',u8(m,TIMES)==0)
def main():
 r=Reporter('G15-BATCH-R9-NORMAL-4A',kind='GATE');source(r);runtime(r,catalog(r));r.finish()
if __name__=='__main__':main()
