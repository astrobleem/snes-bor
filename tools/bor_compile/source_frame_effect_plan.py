"""Offline source-derived effect ordering, paired with immutable B4FE frames.

Dynamic predicates remain explicit operations: shared quake counter, summon
state, dust birth success, jumping and projectile success. No actor-name logic
or gameplay admission. Runtime services must complete before advancing an op.
"""
import argparse,hashlib,json,struct,zlib
from enum import IntEnum
from pathlib import Path
from compiler import Source
from source_frame_effects_4086 import derive as frame_effects,pack as pack_effects
from source_update_frame import Service


class Op(IntEnum):
    DROP_WEAPON=2
    SET_WEAPON=3
    SET_IDLE=4
    SPAWN=7
    SUMMON=8
    SOUND=9
    TOSS=10
    DUST_BIRTH=11
    SHOOT=15
    BOMB=16
    QUAKE=17
    UNSUMMON=18
    JUMP_VELOCITY=19
    DUST_RESULT=20
    THROW=21
    REACTIVE=22
    RESTORE_SELF=23


def frame_plan(animation,index):
    e=animation['events'];frame=animation['frames'][index];ops=[]
    if e['weapon_frame']==index:
        ops.extend((Op.DROP_WEAPON,Op.SET_WEAPON))
        if not e['weapon_keep']:ops.append(Op.SET_IDLE)
    ops.append(Op.QUAKE) # Predicate uses the current shared animation counter.
    if e['unsummonframe']==index:ops.append(Op.UNSUMMON)
    if e['spawn_frame']==index and e['subentity'] is not None:ops.append(Op.SPAWN)
    if e['summon_frame']==index and e['subentity'] is not None:ops.append(Op.SUMMON)
    # Symbolic SOURCE_ASSET_MISSING entries are bound to -1 by B4FE's packer.
    sound=frame['sound']
    if sound is not None and frame.get('sound_resolution')!='SOURCE_ASSET_MISSING' and (
        isinstance(sound,str) or isinstance(sound,int) and sound>=0 or isinstance(sound,dict) and sound.get('index',-1)>=0):ops.append(Op.SOUND)
    if e['jump_frame']==index:
        ops.extend((Op.TOSS,Op.JUMP_VELOCITY))
        if e['jump_entity'] is not None:ops.extend((Op.DUST_BIRTH,Op.DUST_RESULT))
    if e['throw_frame']==index:ops.extend((Op.THROW,Op.REACTIVE))
    if e['shoot_frame']==index:ops.extend((Op.SHOOT,Op.REACTIVE))
    if e['toss_frame']==index:ops.extend((Op.BOMB,Op.REACTIVE))
    ops.append(Op.RESTORE_SELF)
    return list(map(int,ops))


def execute_remaining(owner,ent,animation,index,ops):
    """Service reference for the compiler's plan; handlers return via owner."""
    e=animation.events
    for op in ops:
        op=Op(op)
        if op in (Op.DROP_WEAPON,Op.SET_WEAPON,Op.SET_IDLE,Op.SPAWN,Op.SOUND,Op.TOSS,Op.SHOOT,Op.BOMB):
            yield Service(int(op)),ent
        elif op==Op.QUAKE:
            if e['quake_start']+animation.quake_count==index:
                if owner.level:owner.quake=e['quake_value'] if animation.quake_count%2 or e['quake_value']>0 else -e['quake_value']
                animation.quake_count=animation.quake_count+1 if e['quake_repeat']-animation.quake_count>1 else 0
        elif op==Op.UNSUMMON:
            if ent.subentity is not None:
                owner.self_entity=ent.subentity
                yield Service.UNSUMMON_DAMAGE if ent.subentity.takedamage else Service.UNSUMMON_KILL,ent.subentity
                owner.self_entity=ent;ent.subentity=None
        elif op==Op.SUMMON:
            if ent.subentity is None or ent.subentity.dead:yield Service.SUMMON,ent
        elif op==Op.JUMP_VELOCITY:
            ent.vx=e['jump_x'] if ent.direction else -e['jump_x'];ent.vz=e['jump_z']
        elif op==Op.DUST_BIRTH:
            owner.dust=None;yield Service.DUST_BIRTH,ent
        elif op==Op.DUST_RESULT:
            if owner.dust is not None:
                owner.dust.base=ent.altitude;owner.dust.autokill=2
                yield Service.DUST_ONSPAWN,owner.dust
        elif op==Op.THROW:
            if e['knife'] is not None or e['flash'] is not None:yield Service.THROW_KNIFE,ent
            elif e['star'] is not None:yield Service.THROW_STAR,ent
            else:
                owner.projectile_succeeded=False
                first,second=(Service.THROW_STAR,Service.THROW_KNIFE) if ent.jumping else (Service.THROW_KNIFE,Service.THROW_STAR)
                yield first,ent
                if not owner.projectile_succeeded:yield second,ent
        elif op==Op.REACTIVE:ent.reactive=True
        elif op==Op.RESTORE_SELF:return


def update_frame_with_plan(owner,ent,index):
    """Pinned prefix/motion reference around the precomputed effect sequence."""
    animation=ent.animation
    if index<0:raise ValueError('SOURCE_UPDATE_FRAME_NEGATIVE_UNDEFINED')
    if index>=len(animation.frames):return
    oldself=owner.self_entity;owner.self_entity=ent;owner.completed=False
    try:
        ent.frame=index;frame=animation.frames[index]
        if ent.animating:
            ent.nextanim=(owner.time+frame.delay)&0xffffffff;ent.pausetime=0
            yield Service.ANIMATION_SCRIPT,ent
        if ent.animation is not animation or ent.frame!=index:return
        if owner.level and (frame.x or frame.z):
            ent.movex+=frame.x if ent.direction else -frame.x;ent.movez+=frame.z
        base=animation.frames[0].base
        if base and base>=0 and ent.base<=0:ent.base=float(base)
        elif not base or base<0:
            ent.base+=frame.y;ent.altbase=ent.altbase+frame.y if frame.y else 0
        if animation.events['flipframe']==index:ent.direction=int(not ent.direction)
        raw=dict(events=animation.events,frames=[dict(sound=f.sound) for f in animation.frames])
        yield from execute_remaining(owner,ent,animation,index,frame_plan(raw,index))
    finally:owner.self_entity=oldself;owner.completed=True


def derive(effects):
    fe=pack_effects(effects);animations=[]
    for index,a in enumerate(effects['animations'],1):
        if a['handle']!=index:raise ValueError('FRAME_EFFECT_PLAN_HANDLE_IDENTITY')
        animations.append(dict(handle=index,frames=[dict(index=f,ops=frame_plan(a,f)) for f in range(len(a['frames']))]))
    return dict(schema='BYOR_4086_FRAME_EFFECT_PLAN_V1',animations=animations,
        frame_effects_sha256=hashlib.sha256(fe).hexdigest(),frame_effects_crc32=zlib.crc32(fe)&0xffffffff,
        opcodes={op.name:int(op) for op in Op},native_effect_services_bound=False,motu_gameplay_proven=False)


def pack(report):
    animations=report['animations'];count=len(animations);frames=sum(len(a['frames']) for a in animations)
    if not 1<=count<=512 or frames>65535:raise ValueError('FRAME_EFFECT_PLAN_CAPACITY')
    dirs=bytearray();records=bytearray();pool=bytearray();frame_at=32+8*count;pool_at=frame_at+8*frames
    for handle,a in enumerate(animations,1):
        if a['handle']!=handle:raise ValueError('FRAME_EFFECT_PLAN_HANDLE_IDENTITY')
        if len(a['frames'])>65535:raise ValueError('FRAME_EFFECT_PLAN_FRAME_CAPACITY')
        dirs.extend(struct.pack('<4H',handle,len(a['frames']),frame_at+len(records),0))
        for f,r in enumerate(a['frames']):
            ops=r['ops']
            if r['index']!=f or not ops or len(ops)>32 or ops[-1]!=Op.RESTORE_SELF or any(n not in set(Op) for n in ops):raise ValueError('FRAME_EFFECT_PLAN_OPERATION')
            records.extend(struct.pack('<4H',pool_at+len(pool),len(ops),f,0));pool.extend(bytes(ops))
    body=dirs+records+pool
    if 32+len(body)>32768:raise ValueError('FRAME_EFFECT_PLAN_ROM_BANK_CAPACITY')
    return struct.pack('<4s6H4I',b'B4EP',1,count,8,8,1,0,frames,len(body),report['frame_effects_crc32'],zlib.crc32(body)&0xffffffff)+body


def unpack(table,effects_bytes):
    if len(table)<32:raise ValueError('FRAME_EFFECT_PLAN_HEADER')
    magic,version,count,ds,fs,os,flags,frames,size,paired,crc=struct.unpack_from('<4s6H4I',table)
    if magic!=b'B4EP' or version!=1 or ds!=8 or fs!=8 or os!=1 or flags or not 1<=count<=512 or size!=len(table)-32 or crc!=zlib.crc32(table[32:])&0xffffffff or paired!=zlib.crc32(effects_bytes)&0xffffffff:raise ValueError('FRAME_EFFECT_PLAN_ABI_OR_PAIRING')
    frame_at=32+8*count;pool_at=frame_at+8*frames;entries=[];expected_frame=frame_at;expected_pool=pool_at
    if pool_at>len(table):raise ValueError('FRAME_EFFECT_PLAN_DIRECTORY_BOUNDS')
    for i in range(count):
        handle,n,at,reserved=struct.unpack_from('<4H',table,32+8*i)
        if handle!=i+1 or reserved or at!=expected_frame or at+8*n>pool_at:raise ValueError('FRAME_EFFECT_PLAN_DIRECTORY')
        rows=[]
        for f in range(n):
            p,length,index,reserved=struct.unpack_from('<4H',table,at+8*f)
            if index!=f or reserved or p!=expected_pool or not 1<=length<=32 or p+length>len(table):raise ValueError('FRAME_EFFECT_PLAN_RECORD')
            ops=list(table[p:p+length])
            if ops[-1]!=Op.RESTORE_SELF or any(op not in set(Op) for op in ops):raise ValueError('FRAME_EFFECT_PLAN_OPCODE')
            rows.append(dict(index=f,ops=ops));expected_pool+=length
        entries.append(dict(handle=handle,frames=rows));expected_frame+=8*n
    if expected_frame!=pool_at or expected_pool!=len(table):raise ValueError('FRAME_EFFECT_PLAN_TRAILING_DATA')
    return entries


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();effects=frame_effects(Source(a.source));r=derive(effects);data=pack(r)
    assert unpack(data,pack_effects(effects))==r['animations']
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'frame-effects.b4ep').write_bytes(data);r.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(animations=len(r['animations']),frames=sum(len(a['frames']) for a in r['animations']),bytes=len(data))))


if __name__=='__main__':main()
