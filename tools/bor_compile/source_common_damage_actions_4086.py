"""Pinned common pain/fall/grabbed actions with explicit child service trace."""
def run(c):
 e=dict(c);events=[]
 def air():events.append(10);return e['air']
 if e['callback']==0:
  if e['animating']or air():return e,events
  e['inpain']=0
  if e['link']:e['action']=3
  elif e['blocking']:e['action']=4;events.extend([1,1])
  else:e['action']=0;events.append(2)
 elif e['callback']==1:
  if e['falling']or air()or e['vy']:return e,events
  if e['projectile']>0:
   if e['projectile']==2 and((e['autoland']==1 and e['landing']==-1)or e['landing']==-2):events.append(3);return e,events
   e['falling']=0
  if e['boss']and e['completed']:e['speedup']=1
  e['action']=5;e['stall']=(e['time']+max(0,int(e['rise']+200-e['model_rise'])))&0xffffffff;e['rise_stall']=(e['time']+max(0,int(e['riseattack']-e['model_riseattack'])))&0xffffffff;e['rise']=e['riseattack']=0.
 else:
  if e['link']:return e,events
  e['stall']=0;e['action']=0;events.append(2)
 return e,events
