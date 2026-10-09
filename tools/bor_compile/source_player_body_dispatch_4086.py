"""Ordered post-pain controller dispatch from BOR 4086 player_think."""

def select(e):
    if e['projectile']==2:return 'FALL'
    if e['grabbing'] and not e['attacking'] and not e['throw_wait']:return 'GRAB'
    if e['jumping']:return 'JUMP'
    if e['drop'] and e['y']==e['base'] and not e['vy']:return 'LIE'
    return 'CONTINUE'
