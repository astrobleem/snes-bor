"""Pinned source collision geometry with bounded binary32 positions.

This is an offline semantic reference. It grants no native hit/damage service.
"""
import math,struct


def f32(value):
    result=struct.unpack('<f',struct.pack('<f',value))[0]
    if not math.isfinite(result):raise ValueError('CHECKHIT_FINITE_BINARY32')
    return result


def checkhit(attacker,target,counter=False):
    if attacker['token']==target['token'] or not target['bbox_table'] or not attacker['attack_table'] or not target['vulnerable']:
        return None
    a=attacker['attack']
    if a is None:raise ValueError('CHECKHIT_CURRENT_ATTACK_REQUIRED')
    c1=a['attack_coords']
    if not counter:c2=target['bbox']
    elif target['attack_table']and target['attack']is not None and target['attack']['counterattack']<=a['counterattack']:c2=target['attack']['attack_coords']
    else:return None
    if c2 is None:raise ValueError('CHECKHIT_CURRENT_BOX_REQUIRED')
    for coords in (c1,c2):
        if len(coords)!=6 or any(type(v)is not int or not -32768<=v<=32767 for v in coords):raise ValueError('CHECKHIT_BOUNDED_COORDINATES')
    ap=[f32(v)for v in attacker['position']];tp=[f32(v)for v in target['position']]
    if any(not -32768<v<32768 for v in ap+tp):raise ValueError('CHECKHIT_POSITION_DOMAIN')
    z1=ap[2];z2=tp[2];zdist=f32(0)
    if c1[5]>c1[4]:
        half=(c1[5]-c1[4])//2;z1=f32(z1+c1[4]+half);zdist=f32(zdist+half)
    elif c1[4]:zdist=f32(zdist+c1[4])
    else:zdist=f32(zdist+f32(attacker['grabdistance'])/3+1)
    if c2[5]>c2[4]:
        half=(c2[5]-c2[4])//2;z2=f32(z2+c2[4]+half);zdist=f32(zdist+half)
    elif c2[4]:zdist=f32(zdist+c2[4])
    zdist=f32(zdist+1)
    if f32(abs(z1-z2))>zdist:return None
    x1,y1,x2,y2=int(ap[0]),int(f32(z1-ap[1])),int(tp[0]),int(f32(z2-tp[1]))
    def rectangle(x,y,c,d):
        return [x-c[2],y+c[1],x-c[0],y+c[3]]if d==0 else[x+c[0],y+c[1],x+c[2],y+c[3]]
    r1=rectangle(x1,y1,c1,attacker['direction']);r2=rectangle(x2,y2,c2,target['direction'])
    if r1[0]>r2[2]or r2[0]>r1[2]or r1[1]>r2[3]or r2[1]>r1[3]:return None
    medx=f32(max(r1[0],r2[0])+min(r1[2],r2[2]))/2
    medy=f32(max(r1[1],r2[1])+min(r1[3],r2[3]))/2
    z=f32((z1 if ap[2]>tp[2]else z2)+1)
    return dict(x=f32(medx),y=f32(z-medy),z=z,type=a['attack_type'],confirm=1)
