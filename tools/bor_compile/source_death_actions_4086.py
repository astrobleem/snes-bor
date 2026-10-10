"""Pinned player_blink/suicide deadlines; child operations remain explicit."""
def player_blink(e,time):
 e['blink']=1
 return ['PLAYER_DIE'] if time>=e['stall'] else []

def suicide(e,time,completed):
 if time<e['stall']:return completed,[]
 return (completed|e['boss'])&0xffffffff,['KILL']
