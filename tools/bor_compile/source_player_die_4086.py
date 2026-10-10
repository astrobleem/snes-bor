"""Pinned player_die continuation plan; scripts, kill and respawn are services."""
from enum import IntEnum
class Service(IntEnum):
 PDIE=1
 KILL=2
 SPAWN=3
 RESPAWN=4
 RUMBLE=5
 DROP_ENEMIES=6

def player_die(s):
 index=s['self']['playerindex'];p=s['players'][index]
 if not s['livescheat']:p['lives']-=1
 if s['firstplayer']is s['self']:s['firstplayer']=None
 yield Service.PDIE,index,0
 # The original engine reads global self again after the pdie script.
 if s['rush_policy']>=1:p['rush_saved']=p['ent']['rush_max']
 p['ent']=None;p['spawnhealth']=s['self']['health'];p['spawnmp']=s['self']['mp']
 if s['self']['nodieblink']!=3:yield Service.KILL,s['self']['token'],0
 else:s['self'].update(think=0,action=0,type=0)
 if p['lives']<=0:
  if not any(q['ent']is not None for q in s['players']):
   s['timeleft']=4000
   # Preserve the source's duplicated joining[0] tests exactly.
   if not s['players'][0]['joining']and not s['players'][1]['joining']and ((not s['noshare']and s['credits']<1)or(s['noshare']and all(q['credits']<1 for q in s['players']))):s['timeleft']=200
  if s['self']['weaploss']==3:p['weapnum']=s['setweap']
  if s['rush_policy']!=2:p['rush_saved']=0
  return
 yield Service.SPAWN,index,0
 yield Service.RESPAWN,index,0
 if not s['nodropen']:
  yield Service.RUMBLE,index,125
  yield Service.DROP_ENEMIES,0,0
 if not s['noreset']:s['timeleft']=s['settime']*400
