"""Source horizontal scroller branch. Unsupported directions fail explicitly.

Coordinates are original binary32 values. This is an offline oracle, not a
claim that a native fixed-point camera or moving renderer has been bound.
"""
import struct
from source_wait_4086 import release

def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]

def move(s):
    direction=s['direction']
    if direction not in (2,3,8,9):raise ValueError('SOURCE_CAMERA_DIRECTION_SERVICE_REQUIRED')
    players=[p for p in s['players'][:s['maxplayers']] if p is not None]
    if not 1<=s['maxplayers']<=4:raise ValueError('SOURCE_CAMERA_PLAYER_COUNT_DOMAIN')
    tx,ty=s['x'],s['y'];release(s,s['enemies'])
    # WAIT release precedes this return in source. Dead/exists/type do not
    # participate in player-role camera eligibility: a role pointer suffices.
    if not players:return False
    rm=max([-9999.0]+[p['x'] for p in players]);lm=min([999999.0]+[p['x'] for p in players])
    bm=max([-9999.0]+[p['z'] for p in players]);tm=min([999999.0]+[p['z'] for p in players])
    if not s['waiting']:
        end=s['width']<=s['hres']
        to=s['x'] if rm-lm>s['hres'] else f32((lm+rm)/2-s['hres']//2+s['offsetx'])
        if to<s['minx']:to=s['minx']
        elif to>s['maxx']:to=s['maxx']
        right=bool(direction&2);back=bool(direction&1)
        if back:
            if right and to<s['blockade']:to=s['blockade']
            elif not right and s['width']-s['hres']-to<s['blockade']:to=f32(s['width']-s['hres']-s['blockade'])
        if to>s['x'] and(right or back):s['x']=min(to,f32(s['x']+s['speed']))
        elif to<s['x'] and(not right or back):s['x']=max(to,f32(s['x']-s['speed']))
        if right:
            if s['x']<0:s['x']=0.0
            if s['x']>=s['width']-s['hres']:s['x']=f32(s['width']-s['hres']);end=True
        else:
            if s['x']>s['width']-s['hres']:s['x']=f32(s['width']-s['hres'])
            if s['x']<=0:s['x']=0.0;end=True
        s['pos']=s['pos']+1 if end else int(s['x'] if right else(s['width']-s['hres'])-s['x'])
    # Depth camera continues during WAIT, independently of horizontal hold.
    if s['cameratype']==1:
        bm=max([-9999.0]+[f32(p['z']-p['a']) for p in players]);tm=min([999999.0]+[f32(p['z']-p['a']) for p in players])
    to=s['y'] if bm-tm>s['vres'] else f32((bm+tm)/2-s['vres']//2+s['offsetz'])
    if to>s['maxz']:to=s['maxz']
    elif to<s['minz']:to=s['minz']
    if to!=s['y']:s['y']=min(max(to,f32(s['y']-s['speed'])),f32(s['y']+s['speed']))
    limit=s['height']-(16 if s['rocking'] else 12)-s['vres']
    if s['y']>limit:s['y']=f32(limit)
    if s['y']<0:s['y']=0.0
    s['dx']=f32(s['x']-tx);s['dy']=f32(s['y']-ty)
    return True
