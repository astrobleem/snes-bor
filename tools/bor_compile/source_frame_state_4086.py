"""Pinned loader collision state, kept separate from update_frame side effects.

Boxes use source origin-relative endpoints, not scaled sprite bounds. A zero
width/height suppresses the stored box/attack. Persistent depth adjustment is
intentional: it follows af23dc9c's FRAME loader, including its asymmetry.
"""
from copy import deepcopy
from fractions import Fraction
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from compiler import Source, key
from source_profile import document, discover
from script_dispatch_4086 import compile_source
from dialect_4086 import ENGINE_COMMIT

ATTACK_TYPES = {'attack': 0, 'attack1': 0, 'attack2': 1, 'attack3': 2,
    'attack4': 3, 'attack5': 9, 'attack6': 10, 'attack7': 11, 'attack8': 12,
    'attack9': 13, 'attack10': 14, 'burn': 5, 'freeze': 6, 'shock': 7,
    'steal': 8, 'itembox': 15}
SCALARS = {'counterattack': 'counterattack', 'forcedirection': 'force_direction',
    'otg': 'otg', 'jugglecost': 'jugglecost', 'guardcost': 'guardcost',
    'noreflect': 'no_pain', 'nokill': 'no_kill'}
MEDIA = {'hitfx': 'hitsound', 'hitflash': 'hitflash',
         'blockfx': 'blocksound', 'blockflash': 'blockflash'}
FIELDS = ('attack_force no_block counterattack no_pain no_kill no_flash grab '
    'freeze steal blast force_direction forcemap seal freezetime maptime '
    'sealtime dot dot_index dot_time dot_force dot_rate otg jugglecost '
    'guardcost attack_drop attack_type damage_on_landing pause_add pain_time').split()
MEDIA_FIELDS = ('hitsound','hitflash','blockflash','blocksound')
UNSIGNED_FIELDS = {'freezetime','maptime','sealtime','dot_time','pain_time'}
ATTACK_STRUCT = struct.Struct('<'+'i'*9+
    ''.join('I' if n in UNSIGNED_FIELDS else 'i' for n in FIELDS)+'ffffHHHH')


def empty_attack():
    names = ('attack_force no_block counterattack no_pain no_kill no_flash grab '
        'freeze steal blast force_direction forcemap seal freezetime maptime '
        'sealtime dot dot_index dot_time dot_force dot_rate otg jugglecost '
        'guardcost attack_drop attack_type damage_on_landing grab_distance '
        'pause_add pain_time').split()
    a = dict.fromkeys(names, 0)
    a.update(attack_coords=[0]*6, staydown=[0]*3, dropv=['0']*3,
             hitsound='ENGINE_SAMPLE_BEAT', hitflash=None,
             blockflash=None, blocksound=None)
    return a


def loader_frames(rows):
    """Numeric collision loader subset; preserve other operations verbatim."""
    result = []; current = None; delay = 0
    def integer(values, n):
        # GET_INT_ARG uses atoi, including the integer prefix of freeze time.
        m = re.match(r'^[+-]?\d+', values[n]) if n < len(values) else None
        value = int(m[0]) if m else 0
        if not -0x80000000 <= value <= 0x7fffffff:
            raise ValueError('FRAME_COLLISION_INTEGER_DOMAIN')
        return value
    def number(values, n):
        return Fraction(values[n]) if n < len(values) else Fraction(0)
    def ticks(values, n):
        value = number(values, n)*200
        if value.denominator != 1 or not 0 <= value <= 0xffffffff:
            raise ValueError('FRAME_COLLISION_TIME_DOMAIN')
        return int(value)
    for row in rows:
        name, v = row['directive'], row['values']
        if name == 'anim':
            current = dict(role=' '.join(v), frames=[], retained_directives=[])
            result.append(current)
            bbox = [0]*6; abox = [0]*4; offset = [0]*2; attack = empty_attack()
        elif current is None:
            continue
        elif name == 'delay': delay = integer(v, 0)
        elif name == 'offset': offset = [integer(v, n) for n in range(2)]
        elif name == 'bbox': bbox = [integer(v, n) for n in range(6)]
        elif name == 'bboxz': bbox[4:] = [integer(v, n) for n in range(2)]
        elif name in ATTACK_TYPES:
            abox = [integer(v, n) for n in range(4)]
            attack.update(attack_force=integer(v, 4), attack_drop=integer(v, 5),
                no_block=integer(v, 6), no_flash=integer(v, 7), pause_add=integer(v, 8),
                attack_type=ATTACK_TYPES[name], dropv=['3', '1.2', '0']) # y,x,z
            attack['attack_coords'][4] = integer(v, 9)
            if name == 'freeze':
                attack.update(freeze=1, freezetime=ticks(v, 5), forcemap=-1, attack_drop=0)
            if name == 'steal': attack['steal'] = 1
        elif name in ('attackz', 'hitz'):
            attack['attack_coords'][4:] = [integer(v, n) for n in range(2)]
        elif name == 'dropv': attack['dropv'] = [str(number(v, n)) for n in range(3)]
        elif name in SCALARS: attack[SCALARS[name]] = integer(v, 0)
        elif name in MEDIA: attack[MEDIA[name]] = None if not v or v[0].lower() == 'none' else v[0]
        elif name == 'stun': attack.update(freeze=1, freezetime=ticks(v, 0), attack_drop=0)
        elif name == 'fastattack':
            if integer(v, 0): attack['pain_time'] = 10
        elif name == 'forcemap': attack.update(forcemap=integer(v, 0), maptime=ticks(v, 1))
        elif name == 'seal': attack.update(sealtime=integer(v, 0)*200, seal=integer(v, 1))
        elif name == 'staydown': attack['staydown'][:2] = [integer(v, n) for n in range(2)]
        elif name == 'dot':
            for n, field in enumerate(('dot_index','dot_time','dot','dot_force','dot_rate')):
                attack[field] = integer(v, n)
        elif name == 'grabin': attack.update(grab=integer(v, 0), grab_distance=str(number(v, 1)))
        elif name == 'damageonlanding': attack.update(damage_on_landing=integer(v, 0), blast=integer(v, 1))
        elif name == 'blast' or (name.startswith('attack') and name[6:].isdigit()):
            raise ValueError('FRAME_COLLISION_ATTACK_VARIANT_UNBOUND:'+name)
        elif name == 'frame':
            b = [bbox[0]-offset[0], bbox[1]-offset[1], 0, 0, bbox[4], bbox[5]]
            b[2] = bbox[2]+b[0]; b[3] = bbox[3]+b[1]
            if bbox[5] > bbox[4]:
                bbox[4] -= offset[1]; bbox[5] -= offset[1]
            coords = attack['attack_coords']
            coords[:4] = [abox[0]-offset[0], abox[1]-offset[1],
                          abox[2]+abox[0]-offset[0], abox[3]+abox[1]-offset[1]]
            if coords[5] > coords[4]:
                coords[4] -= offset[1]; coords[5] -= offset[1]
            current['frames'].append(dict(index=len(current['frames']), source_line=row['line'],
                image=v[0], offset=list(offset), delay_ticks=delay*2,
                vulnerable=bool(b[2]-b[0] and b[3]-b[1]),
                bbox=b if b[2]-b[0] and b[3]-b[1] else None,
                attack=deepcopy(attack) if abox[2] and abox[3] else None))
        else: current['retained_directives'].append(row)
    return result


def derive(source):
    docs = {k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure = discover(source, docs)
    handles = {(h['model'],h['role']):h['handle'] for h in compile_source(source)['animation_handles']}
    animations = []
    # The global default drop velocity can be reconfigured by models.txt.
    # Until that is parameterized, reject it instead of assuming MOTU defaults.
    if any(d['directive']=='dropv' for d in docs[key(structure['models_path'])]['directives']):
        raise ValueError('FRAME_COLLISION_GLOBAL_DROPV_UNBOUND')
    for model in structure['models']:
        doc = docs[key(model['source_path'])]
        for a in loader_frames(doc['directives']):
            a.update(model=model['declaration'], handle=handles[model['declaration'],a['role']],
                     source_path=doc['source_path'], source_sha256=doc['sha256'])
            animations.append(a)
    return dict(schema='BYOR_4086_FRAME_COLLISION_IR_V1', engine_authority=ENGINE_COMMIT,
        animations=animations, media_binding='symbolic source identities; native binding required',
        numeric_policy='source decimal strings for drop velocity; runtime lowering not performed',
        collision_runtime_bound=False, update_frame_bound=False, live_world_bound=False,
        motu_gameplay_proven=False)


def pack(report):
    """One bank of deduplicated frame descriptors, boxes and attack records.

    Float fields retain the pinned loader's binary32 representation. These
    records do not imply that SNES numeric operations or media are bound.
    Index zero is absent; no absent collision record occupies storage.
    """
    animations=sorted(report['animations'],key=lambda a:a['handle'])
    boxes=[]; attacks=[]; media=[]; frames=[]
    def intern(items,value):
        if value is None: return 0
        if value not in items: items.append(value)
        return items.index(value)+1
    for number,a in enumerate(animations,1):
        if a['handle']!=number: raise ValueError('FRAME_COLLISION_HANDLE_ORDER')
        for f in a['frames']:
            frames.append((f['offset'][0],f['offset'][1],f['delay_ticks'],0,
                           intern(boxes,f['bbox']),intern(attacks,f['attack'])))
    directory_size=16+len(animations)*8
    b=bytearray(struct.pack('<4s6H',b'B4FC',1,len(animations),len(frames),len(boxes),len(attacks),0))
    cursor=directory_size
    for a in animations:
        b.extend(struct.pack('<4H',a['handle'],len(a['frames']),cursor,0))
        cursor+=12*len(a['frames'])
    for f in frames: b.extend(struct.pack('<hhHHHH',*f))
    for box in boxes: b.extend(struct.pack('<6i',*box))
    for attack in attacks:
        values=attack['attack_coords']+attack['staydown']+[attack[k] for k in FIELDS]
        floats=[float(Fraction(v)) for v in attack['dropv']]+[float(Fraction(attack['grab_distance']))]
        refs=[intern(media,attack[k]) for k in MEDIA_FIELDS]
        b.extend(ATTACK_STRUCT.pack(*values,*floats,*refs))
    b.extend(struct.pack('<H',len(media)))
    for name in media:
        value=name.encode('utf-8'); b.extend(struct.pack('<H',len(value))); b.extend(value)
    if len(b)>32768: raise ValueError('FRAME_COLLISION_TABLE_BANK_LIMIT')
    return bytes(b)


def unpack(data):
    if len(data)<16 or len(data)>32768: raise ValueError('FRAME_COLLISION_TABLE_HEADER')
    magic,version,count,total,box_count,attack_count,reserved=struct.unpack_from('<4s6H',data)
    if magic!=b'B4FC' or version!=1 or not count or reserved: raise ValueError('FRAME_COLLISION_TABLE_HEADER')
    cursor=16+count*8; animations=[]; frames=[]
    for i in range(count):
        if 16+(i+1)*8>len(data): raise ValueError('FRAME_COLLISION_TABLE_DIRECTORY')
        handle,n,offset,pad=struct.unpack_from('<4H',data,16+i*8)
        if handle!=i+1 or not n or offset!=cursor or pad or cursor+n*12>len(data):
            raise ValueError('FRAME_COLLISION_TABLE_DIRECTORY')
        row=[]
        for f in range(n):
            x,y,delay,pad,box,attack=struct.unpack_from('<hhHHHH',data,cursor+f*12)
            if pad or box>box_count or attack>attack_count: raise ValueError('FRAME_COLLISION_TABLE_FRAME')
            row.append(dict(offset=[x,y],delay_ticks=delay,bbox_index=box,attack_index=attack))
        frames.extend(row); animations.append(dict(handle=handle,frames=row)); cursor+=n*12
    if len(frames)!=total or cursor+24*box_count+ATTACK_STRUCT.size*attack_count+2>len(data):
        raise ValueError('FRAME_COLLISION_TABLE_EXTENT')
    boxes=[list(struct.unpack_from('<6i',data,cursor+n*24)) for n in range(box_count)]
    cursor+=24*box_count; attacks=[]
    for n in range(attack_count):
        v=ATTACK_STRUCT.unpack_from(data,cursor); cursor+=ATTACK_STRUCT.size
        attack=dict(zip(FIELDS,v[9:9+len(FIELDS)]))
        attack.update(attack_coords=list(v[:6]),staydown=list(v[6:9]),dropv=list(v[-8:-5]),
                      grab_distance=v[-5],media_indices=list(v[-4:]))
        attacks.append(attack)
    media_count=struct.unpack_from('<H',data,cursor)[0];cursor+=2;media=[]
    for n in range(media_count):
        if cursor+2>len(data): raise ValueError('FRAME_COLLISION_TABLE_MEDIA')
        size=struct.unpack_from('<H',data,cursor)[0];cursor+=2
        if not size or cursor+size>len(data): raise ValueError('FRAME_COLLISION_TABLE_MEDIA')
        media.append(data[cursor:cursor+size].decode('utf-8'));cursor+=size
    if cursor!=len(data) or len(set(media))!=len(media) or any(max(a['media_indices'])>media_count for a in attacks):
        raise ValueError('FRAME_COLLISION_TABLE_MEDIA')
    return dict(animations=animations,boxes=boxes,attacks=attacks,media=media)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); r=derive(Source(a.source))
    table=pack(r);unpack(table)
    r.update(table_bytes=len(table),table_sha256=hashlib.sha256(table).hexdigest())
    data=(json.dumps(r,indent=2)+'\n').encode()
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_bytes(data)
    a.output.with_suffix('.b4fc').write_bytes(table)
    frames=[f for an in r['animations'] for f in an['frames']]
    print(json.dumps(dict(animations=len(r['animations']),frames=len(frames),
        vulnerable_frames=sum(f['vulnerable'] for f in frames),
        attack_frames=sum(f['attack'] is not None for f in frames),
        sha256=hashlib.sha256(data).hexdigest())))


if __name__=='__main__': main()
