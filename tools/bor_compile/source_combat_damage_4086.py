"""Combat callback scalar reference, with explicit instrumented action services.

No grab, item, boss or initialized damage scripts in this proof domain.
Animation, colourmap, unlink, weapon, score and rumble services are traced.
All factors are one and all defense pain is zero.
"""
import struct


def bits(v):
    return struct.unpack('<I',struct.pack('<f',v))[0]


def run(c):
    hp=c['health'];dead=c['dead'];drop=c['drop'];direction=c['direction']
    count=c['count'];ktime=c['ktime'];landing=c['landing'];escape=3
    idling=1;nograb=0;action=0;vx=vy=vz=0;events=[];score=0
    frozen=c['frozen'];freezetime=c['previous_freezetime'];colourmap=9
    projectile=3;rise=11;riseattack=12;maptime=0
    force=0 if c['callback'] and (c['cheat'] or (c['nohurt'] and c['other_type']&2)) else c['force']
    dtype=0;opponent=-1;otheropp=-1
    def result(ret):
        return [ret,hp,dead,nograb,idling,drop,count,ktime,dtype,direction,landing,escape,action,bits(vx),bits(vy),bits(vz),opponent,otheropp,score,frozen,freezetime,colourmap,projectile,rise,riseattack,maptime],events
    if dead or c['bomb']==2:return result(0)
    opponent=1;otheropp=0
    dtype=c['attack_type'] if 0<=c['attack_type']<20 else 0
    if c['animal']:drop=1
    attackdrop=0 if c['guard'] else c['attack_drop']
    if not drop and not c['no_pain']:
        if ktime and ktime<48:count=c['model_count']
        count-=attackdrop;ktime=248;drop=int(count<0)
    if c['weaploss']==0:events.append(2)
    if not c['guard']:
        if c['freeze'] and not frozen:
            frozen=1
            if not freezetime:freezetime=48+c['freezetime']
            if c['forcemap']==-1 and c['frozen_map']!=-1:
                colourmap=c['frozen_map'];events.append(18)
            drop=0
        elif frozen:
            colourmap=7;events.append(17);frozen=0;freezetime=0;drop=1
        if c['forcemap']>0 and not c['freeze']:
            maptime=48+c['maptime'];colourmap=c['forcemap'];events.append(18)
        if c['nodrop']:drop=0
        if abs(c['y']-c['base'])>=.1 and not frozen and c['nodrop']<2:drop=1
        if c['no_pain']:drop=0
        projectile=c['blast']
        if drop:rise=c['rise'];riseattack=c['riseattack']
    if (drop or not(c['no_pain'] or c['nopain'])) and not frozen and not c['noflip']:
        fd=c['force_direction']
        if fd==0:
            if c['x']<c['other_x']:direction=1
            elif c['x']>c['other_x']:direction=0
        elif fd==1:direction=c['other_direction']
        elif fd==-1:direction=int(not c['other_direction'])
        elif fd==2:direction=1
        elif fd==-2:direction=0
    if c['other_type']&1:events.extend((7,8));score+=force*2
    damage=0 if c['guard'] else force
    hp=min(hp-damage,300)
    if c['no_kill'] and hp<=0:hp=1
    if hp<=0:
        if c['y']>=-250 and c['lifespan']>=0:
            if c['invincible']==2:hp=1
            elif c['invincible']==3:hp=300
    if hp<=0:
        dead=1;nograb=1;idling=0
        if c['other_type']&1:events.append(7);score+=100
        if c['diesound']>=0:events.append(9)
    if c['callback']:events.append(8)
    if c['y']<=-250 and dead:events.append(16 if c['callback'] else 15);return result(1)
    if landing:landing=0;return result(1)
    if not c['other_grabbing'] or dead or frozen or drop:events.append(10)
    if c['escapehits']:escape=0 if drop else escape+1
    if drop or hp<=0:
        action=1
        if (c['weaploss']==2 and hp<=0) or c['weaploss']==1:events.append(2)
        if hp<=0 and c['falldie']==1:events.append(14)
        else:
            vx=-c['dropx'] if direction==1 else c['dropx'];vy=c['dropy'];vz=c['dropz'];events.append(12)
            landing=c['attack_landing'];count=c['model_count'];ktime=0;events.append(13)
            if not c['valid_fall']:events.append(16 if c['callback'] else 15);return result(1)
        if c['callback']:events.append(8)
    elif not frozen and not c['nopain'] and not c['no_pain']:
        action=2;events.append(11)
    return result(1)
