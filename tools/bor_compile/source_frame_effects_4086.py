"""Source-derived update_frame inputs, separate from collision and callbacks.

Movement persists between FRAME declarations. SOUND is consumed by one frame.
Animation events are final animation metadata, including directives after a
FRAME. Symbolic media/model identities must be bound by the world backend.
This table does not claim to execute update_frame or its service handlers.
"""
import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import struct
from compiler import Source, key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document, discover
from script_dispatch_4086 import compile_source

ANIMATION_FIELDS=('flipframe unsummonframe weapon_frame weapon_number weapon_keep '
 'quake_start quake_repeat quake_value jump_frame jump_y jump_x jump_z jump_entity '
 'spawn_frame spawn_x spawn_z spawn_y spawn_relative summon_frame summon_x summon_z '
 'summon_y summon_relative subentity throw_frame shoot_frame toss_frame projectile_y '
 'knife star bomb flash').split()
ANIMATION_STRIDE=128
FRAME_STRIDE=24
NUMERIC_FIELDS={'jump_y','jump_x','jump_z','spawn_x','spawn_z','spawn_y','spawn_relative',
 'summon_x','summon_z','summon_y','summon_relative'}
IDENTITY_FIELDS={'jump_entity','subentity','knife','star','bomb','flash'}


def integer(v,n=0):
    match=re.match(r'^[+-]?\d+',v[n]) if n<len(v) else None
    result=int(match[0]) if match else 0
    if not -0x80000000<=result<=0x7fffffff:raise ValueError('FRAME_EFFECT_INTEGER_DOMAIN')
    return result


def decimal(v,n):
    # GET_FLOAT_ARG lowers through the engine float before assignment.
    value=float(v[n]) if n<len(v) else 0.0
    value=struct.unpack('<f',struct.pack('<f',value))[0]
    if not -32768<=value<32768:raise ValueError('FRAME_EFFECT_Q16_DOMAIN')
    return value


def loader_frames(rows):
    animations=[];current=None;move=None;sound=None;delay=0
    for row in rows:
        name,v=row['directive'],row['values']
        if name=='anim':
            current=dict(role=' '.join(v),frames=[],events=dict.fromkeys(ANIMATION_FIELDS,0))
            e=current['events']
            for field in ('flipframe','unsummonframe','weapon_frame','jump_frame','spawn_frame',
                          'summon_frame','throw_frame','shoot_frame','toss_frame'):e[field]=-1
            for field in IDENTITY_FIELDS:e[field]=None
            # calloc leaves jumpframe.ent at cache index zero; a JUMPFRAME
            # declaration with no dust argument explicitly changes it to -1.
            e['jump_entity']=0
            animations.append(current);move=dict(base=-1,x=0,y=0,z=0);sound=None
        elif current is None:continue
        elif name=='delay':
            delay=integer(v)*2
            if not 0<=delay<=65535:raise ValueError('FRAME_EFFECT_DELAY_DOMAIN')
        elif name in ('move','movea','movez','seta'):
            move[dict(move='x',movea='y',movez='z',seta='base')[name]]=integer(v)
        elif name=='sound':
            if len(v)!=1:raise ValueError('FRAME_EFFECT_SOUND_ARITY')
            sound=v[0]
        elif name=='frame':
            current['frames'].append(dict(index=len(current['frames']),source_line=row['line'],
                image=v[0],move=deepcopy(move),sound=sound,delay_ticks=delay));sound=None
        elif name in ('flipframe','unsummonframe'):
            current['events'][name]=len(current['frames']) if v and v[0].lower()=='this' else integer(v)
        elif name in ('weaponframe','quakeframe','jumpframe','spawnframe','summonframe',
                       'throwframe','shootframe','tossframe','pshotframe','pshotframew','pshotframeno','pbombframe'):
            e=current['events'];f=len(current['frames']) if v and v[0].lower()=='this' else integer(v)
            if name=='weaponframe':e.update(weapon_frame=f,weapon_number=integer(v,1),weapon_keep=integer(v,2))
            elif name=='quakeframe':e.update(quake_start=f,quake_repeat=integer(v,1),quake_value=integer(v,2))
            elif name=='jumpframe':
                if len(v)<3:raise ValueError('FRAME_EFFECT_LEGACY_JUMP_FALLBACK_UNBOUND')
                e.update(jump_frame=f,jump_y=decimal(v,1),jump_x=decimal(v,2),jump_z=decimal(v,3),
                         jump_entity=v[4] if len(v)>4 else None)
            elif name in ('spawnframe','summonframe'):
                prefix=name[:-5]
                e.update({prefix+'_frame':f,**{prefix+'_'+field:decimal(v,n)
                    for n,field in enumerate(('x','z','y','relative'),1)}})
            else:
                field='throw_frame' if name in ('throwframe','pshotframe','pshotframew','pshotframeno') else 'shoot_frame' if name=='shootframe' else 'toss_frame'
                y=integer(v,1)
                if field=='throw_frame':y=70 if y==0 else 0 if y==-1 else y
                elif field=='shoot_frame':y=0 if y==-1 else y
                elif y<0:y=-1
                e.update({field:f,'projectile_y':y})
        elif name in ('subentity','custentity','custknife','custpshot','custpshotw','custpshotno','custstar','custbomb','custpbomb'):
            field={'subentity':'subentity','custentity':'subentity','custknife':'knife','custpshot':'knife',
                   'custpshotw':'knife','custpshotno':'flash','custstar':'star','custbomb':'bomb','custpbomb':'bomb'}[name]
            if not v:raise ValueError('FRAME_EFFECT_MODEL_IDENTITY_EMPTY')
            current['events'][field]=v[0]
        elif name in ('dive','dive1','dive2'):
            raise ValueError('FRAME_EFFECT_DIVE_INITIALIZATION_UNBOUND')
    return animations


def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs)
    handles={(h['model'],h['role']):h['handle'] for h in compile_source(source)['animation_handles']}
    models=[m['declaration'] for m in structure['models']];animations=[]
    for m in structure['models']:
        doc=docs[key(m['source_path'])]
        if any(d['directive']=='edelay' for d in doc['directives']):
            raise ValueError('FRAME_EFFECT_EDELAY_OWNER_UNBOUND')
        for a in loader_frames(doc['directives']):
            a.update(model=m['declaration'],handle=handles[m['declaration'],a['role']],
                     source_path=doc['source_path'],source_sha256=doc['sha256'])
            for field in IDENTITY_FIELDS:
                identity=a['events'][field]
                if isinstance(identity,int):
                    if not 0<=identity<len(models):raise ValueError('FRAME_EFFECT_MODEL_INDEX_DOMAIN')
                elif identity is not None and identity.lower() not in {n.lower() for n in models}:
                    raise ValueError('FRAME_EFFECT_MODEL_IDENTITY_UNBOUND:'+identity)
            for frame in a['frames']:
                frame['sound_resolution']='ABSENT' if frame['sound'] is None else (
                    'SOURCE_ASSET_PRESENT' if key(frame['sound']) in source.index else 'SOURCE_ASSET_MISSING')
            animations.append(a)
    return dict(schema='BYOR_4086_FRAME_EFFECT_INPUTS_V1',engine_authority=ENGINE_COMMIT,
        models=models,animations=animations,numeric_policy='ACCEPTED_COMPAT_Q16_16 for source binary32 event velocities',
        missing_sound_policy='Pinned sound_load_sample returns -1 on loadwave failure; update_frame skips negative indices. Retain authored missing identity in IR; isolated source namespace required.',
        update_frame_bound=False,callback_owner_bound=False,motu_gameplay_proven=False)


def pack(report):
    animations=sorted(report['animations'],key=lambda a:a['handle']);media=[]
    models={n.lower():i for i,n in enumerate(report['models'])}
    def sound_index(value):
        if value is None:return -1
        if value not in media:media.append(value)
        return media.index(value)
    header=16;cursor=header+len(animations)*8;directory=bytearray();body=bytearray()
    for number,a in enumerate(animations,1):
        if a['handle']!=number:raise ValueError('FRAME_EFFECT_HANDLE_ORDER')
        directory.extend(struct.pack('<4H',number,len(a['frames']),cursor,cursor+ANIMATION_STRIDE))
        values=[]
        for field in ANIMATION_FIELDS:
            value=a['events'][field]
            if field in NUMERIC_FIELDS:value=int(Fraction(value)*65536)
            if field in IDENTITY_FIELDS:value=-1 if value is None else value if isinstance(value,int) else models[value.lower()]
            values.append(value)
        body.extend(struct.pack('<32i',*values))
        for f in a['frames']:
            body.extend(struct.pack('<6i',*(f['move'][n] for n in ('base','x','y','z')),
                -1 if f.get('sound_resolution')=='SOURCE_ASSET_MISSING' else sound_index(f['sound']),f['delay_ticks']))
        cursor+=ANIMATION_STRIDE+len(a['frames'])*FRAME_STRIDE
    media_offset=cursor
    for name in media:
        raw=name.encode('utf-8');body.extend(struct.pack('<H',len(raw))+raw)
    result=struct.pack('<4s6H',b'B4FE',1,len(animations),sum(len(a['frames']) for a in animations),
                       media_offset,len(media),0)+directory+body
    if len(result)>32768:raise ValueError('FRAME_EFFECT_BANK_CAPACITY')
    return result


def unpack(data):
    if len(data)<16:raise ValueError('FRAME_EFFECT_HEADER')
    magic,version,count,frames,media_at,media_count,reserved=struct.unpack_from('<4s6H',data)
    if magic!=b'B4FE' or version!=1 or reserved or not count or media_at>len(data):
        raise ValueError('FRAME_EFFECT_HEADER')
    cursor=16+count*8;animations=[];total=0
    for n in range(count):
        if 16+(n+1)*8>len(data):raise ValueError('FRAME_EFFECT_DIRECTORY')
        handle,size,anim_at,frame_at=struct.unpack_from('<4H',data,16+n*8)
        end=frame_at+size*FRAME_STRIDE
        if handle!=n+1 or not size or anim_at!=cursor or frame_at!=cursor+ANIMATION_STRIDE or end>media_at:
            raise ValueError('FRAME_EFFECT_DIRECTORY')
        events=dict(zip(ANIMATION_FIELDS,struct.unpack_from('<32i',data,anim_at)))
        records=[]
        for i in range(size):
            row=struct.unpack_from('<6i',data,frame_at+i*FRAME_STRIDE)
            if row[4]<-1 or row[4]>=media_count:raise ValueError('FRAME_EFFECT_MEDIA_INDEX')
            if not 0<=row[5]<=65535:raise ValueError('FRAME_EFFECT_DELAY_DOMAIN')
            records.append(dict(move=dict(zip(('base','x','y','z'),row[:4])),sound_index=row[4],delay_ticks=row[5]))
        animations.append(dict(handle=handle,events=events,frames=records));cursor=end;total+=size
    if cursor!=media_at or total!=frames:raise ValueError('FRAME_EFFECT_FRAME_COUNT')
    media=[]
    for i in range(media_count):
        if cursor+2>len(data):raise ValueError('FRAME_EFFECT_MEDIA')
        size=struct.unpack_from('<H',data,cursor)[0];cursor+=2
        if not size or cursor+size>len(data):raise ValueError('FRAME_EFFECT_MEDIA')
        media.append(data[cursor:cursor+size].decode('utf-8'));cursor+=size
    if cursor!=len(data) or len(set(media))!=len(media):raise ValueError('FRAME_EFFECT_MEDIA')
    return dict(animations=animations,media=media)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=derive(Source(a.source));data=pack(report);unpack(data)
    report.update(table_bytes=len(data),table_sha256=hashlib.sha256(data).hexdigest())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n');a.output.with_suffix('.b4fe').write_bytes(data)
    print(json.dumps(dict(animations=len(report['animations']),frames=sum(len(x['frames']) for x in report['animations']),
                         bytes=len(data),sha256=report['table_sha256'])))


if __name__=='__main__':main()
