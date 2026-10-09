"""Existing Q16 coordinate adaptation for source collision geometry.

Source rectangles and identities remain unchanged. Numeric projection is an
explicit ACCEPTED_COMPAT boundary, not a claim of arbitrary binary32 equality.
"""
from source_checkhit_4086 import f32


def q16(v):
    v=f32(v)
    if not -32768<v<32768:raise ValueError('CHECKHIT_Q16_POSITION_RANGE')
    return int(v*65536)


def checked(v):
    if not -0x80000000<=v<=0x7fffffff:raise ValueError('CHECKHIT_Q16_ARITHMETIC_RANGE')
    return v


def trunc(v):return v//65536 if v>=0 else-((-v)//65536)


def checkhit(attacker,target,counter=False):
    if attacker['token']==target['token']or not target['bbox_table']or not attacker['attack_table']or not target['vulnerable']:return None
    a=attacker['attack']
    if a is None:raise ValueError('CHECKHIT_CURRENT_ATTACK_REQUIRED')
    c1=a['attack_coords']
    if not counter:c2=target['bbox']
    elif target['attack_table']and target['attack']is not None and target['attack']['counterattack']<=a['counterattack']:c2=target['attack']['attack_coords']
    else:return None
    if c2 is None:raise ValueError('CHECKHIT_CURRENT_BOX_REQUIRED')
    for c in(c1,c2):
        if len(c)!=6 or any(type(v)is not int or not -32768<=v<=32767 for v in c):raise ValueError('CHECKHIT_BOUNDED_COORDINATES')
    ap=[q16(v)for v in attacker['position']];tp=[q16(v)for v in target['position']]
    z1,z2=ap[2],tp[2];width=0
    if c1[5]>c1[4]:
        half=(c1[5]-c1[4])//2;z1=checked(z1+(c1[4]+half)*65536);width=checked(width+half*65536)
    elif c1[4]:width=checked(width+c1[4]*65536)
    else:width=checked(width+q16(f32(f32(attacker['grabdistance'])/3+1)))
    if c2[5]>c2[4]:
        half=(c2[5]-c2[4])//2;z2=checked(z2+(c2[4]+half)*65536);width=checked(width+half*65536)
    elif c2[4]:width=checked(width+c2[4]*65536)
    width=checked(width+65536)
    if abs(checked(z1-z2))>width:return None
    x1,y1,x2,y2=trunc(ap[0]),trunc(checked(z1-ap[1])),trunc(tp[0]),trunc(checked(z2-tp[1]))
    def rect(x,y,c,d):return [x-c[2],y+c[1],x-c[0],y+c[3]]if d==0 else[x+c[0],y+c[1],x+c[2],y+c[3]]
    r1,r2=rect(x1,y1,c1,attacker['direction']),rect(x2,y2,c2,target['direction'])
    if r1[0]>r2[2]or r2[0]>r1[2]or r1[1]>r2[3]or r2[1]>r1[3]:return None
    midx=(max(r1[0],r2[0])+min(r1[2],r2[2]))*32768
    midy=(max(r1[1],r2[1])+min(r1[3],r2[3]))*32768
    z=checked((z1 if ap[2]>tp[2]else z2)+65536)
    return dict(x=checked(midx),y=checked(z-midy),z=z,type=a['attack_type'],confirm=1)
