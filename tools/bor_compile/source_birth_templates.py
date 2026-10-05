"""Source-derived initialization data for generic TYPE_NONE idle births.

Admission covers birth initialization only. Physics, collisions, rendering,
audio and level ownership still need a world backend. Other initialization
policies and initial callbacks are explicitly rejected rather than aliased.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import zlib
from compiler import Source,key
from source_profile import document,discover
from source_model_registry import derive as model_registry
from source_animation_ids import configure,role_id
from script_dispatch_4086 import compile_source
from dialect_4086 import animation_frames,ENGINE_COMMIT

HEADER=24
STRIDE=160
CAP_NONE_IDLE=1
SIDE_BYTES=64


def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);registry=model_registry(source);scripts=compile_source(source)
    configuration=configure(docs[key(structure['models_path'])]['directives'])
    handles={(h['model'],h['role']):h['handle'] for h in scripts['animation_handles']}
    models=[]
    for model,row in zip(structure['models'],registry['models']):
        directives=docs[key(model['source_path'])]['directives'];rejections=[]
        def scalar(name,default):
            values=[d['values'] for d in directives if d['directive']==name]
            if not values:return default
            if len(values[-1])!=1:raise ValueError('BIRTH_TEMPLATE_SCALAR_ARITY:'+name)
            return values[-1][0]
        roles={a['role'] for a in model['animations']}
        if scalar('type','').lower()!='none':rejections.append('TYPE_SPECIFIC_INITIALIZATION_UNBOUND')
        if 'idle' not in roles:rejections.append('IDLE_REQUIRED')
        if roles&{'walk','spawn','respawn'}:rejections.append('INITIAL_ACTION_POLICY_UNBOUND')
        if model['scripts'] or model['inline_scripts']:rejections.append('INITIAL_CALLBACK_OWNER_UNBOUND')
        if any(d['directive'] in ('onspawnscript','spawnscript','subclass','edelay') for d in directives):
            rejections.append('EXTENDED_INITIALIZATION_UNBOUND')
        animations=animation_frames(directives);idle=next((a for a in animations if a['role']=='idle'),None)
        delay=idle['frames'][0]['delay_ticks'] if idle and idle['frames'] else 0
        if not delay:rejections.append('POSITIVE_INITIAL_DELAY_REQUIRED')
        # Initial update_frame effects must not be skipped during spawn().
        if idle and idle['frames']:
            first_line=idle['frames'][0]['declaration']['line']
            effect_names={'move','movez','movea','move_y','move_x','move_z','sound','@cmd','@script',
                          'weaponframe','flipframe','jumpframe','spawnframe','summonframe','unsummonframe','quakeframe'}
            if any(d['directive'] in effect_names and d['line']<=first_line for d in idle['directives']):
                rejections.append('INITIAL_FRAME_SIDE_EFFECT_UNBOUND')
        for name in ('subject_to_wall','subject_to_platform'):
            if int(scalar(name,'0'))>0:rejections.append('INITIAL_ENVIRONMENT_QUERY_UNBOUND:'+name)
        if int(scalar('mp','0'))!=0:rejections.append('MP_MODEL_STATE_UNBOUND')
        declared_lifespan=scalar('lifespan',None)
        lifespan=Fraction(declared_lifespan)*200 if declared_lifespan is not None else Fraction(0x7fffffff)
        if lifespan.denominator!=1 or not 0<=lifespan<=0x7fffffff:
            rejections.append('LIFESPAN_INTEGER_TICK_POLICY_REQUIRED')
        gravity=int(scalar('subject_to_gravity','1'));no_adjust=int(scalar('no_adjust_base','1'))
        if gravity<0:gravity=1
        if no_adjust<0:no_adjust=1
        if gravity not in (0,1) or no_adjust not in (0,1):rejections.append('INITIAL_PHYSICS_FLAG_POLICY_UNBOUND')
        models.append(dict(id=row['id'],identity=row['identity'],source_path=row['source_path'],
                           source_sha256=row['source_sha256'],capability='SOURCE_NONE_IDLE_BIRTH',
                           admitted=not rejections,rejections=rejections,maxhealth=row['maxhealth'],alpha=row['alpha'],
                           initial_animation_id=role_id(configuration,'idle'),initial_frame_handle=handles.get((model['declaration'],'idle'),0),
                           initial_delay_ticks=delay,lifespan_ticks=int(lifespan),gravity=gravity,no_adjust_base=no_adjust))
    return dict(schema='BYOR_SOURCE_BIRTH_TEMPLATES_V1',engine_authority=ENGINE_COMMIT,models=models,
                admission_scope='TYPE_NONE idle birth without initial script/frame/environment side effects',
                model_template_complete_engine_behavior=False,live_world_owner_bound=False,motu_gameplay_proven=False)


def pack(report):
    body=bytearray()
    for index,row in enumerate(report['models']):
        if row['id']!=index:raise ValueError('BIRTH_TEMPLATE_MODEL_ID')
        data=bytearray(STRIDE)
        struct.pack_into('<HH',data,0,index,CAP_NONE_IDLE if row['admitted'] else 0)
        # View payload excludes the pool-owned token/alive header. Eight variants.
        values=[(2,0),(1,row['initial_animation_id']),(1,0),(1,row['maxhealth']),
                (1,0),(2,0),(2,0),(1,row['maxhealth'])]
        for n,(kind,value) in enumerate(values):struct.pack_into('<BBHI',data,16+n*8,kind,0,0,value&0xffffffff)
        side=88
        struct.pack_into('<HHHH',data,side,index,index,row['initial_frame_handle'],0)
        struct.pack_into('<I',data,side+16,row['lifespan_ticks'])
        struct.pack_into('<HHI',data,side+28,7,row['alpha'],2*65536) # nograb,idling,animating; speedmul
        struct.pack_into('<HHI',data,side+52,row['gravity'],row['no_adjust_base'],row['initial_delay_ticks'])
        body.extend(data)
    return struct.pack('<4sHHHHIII',b'B4BT',1,STRIDE,len(report['models']),0,len(body),zlib.crc32(body)&0xffffffff,0)+body


def unpack(table):
    if len(table)<HEADER:raise ValueError('BIRTH_TEMPLATE_HEADER')
    magic,version,stride,count,reserved,size,crc,flags=struct.unpack_from('<4sHHHHIII',table)
    if (magic!=b'B4BT' or version!=1 or stride!=STRIDE or not 1<=count<=128 or reserved or flags
        or size!=count*STRIDE or len(table)!=HEADER+size or crc!=zlib.crc32(table[HEADER:])&0xffffffff):
        raise ValueError('BIRTH_TEMPLATE_ABI')
    for n in range(count):
        row=table[HEADER+n*STRIDE:HEADER+(n+1)*STRIDE]
        model,cap=struct.unpack_from('<HH',row)
        if model!=n or cap not in (0,CAP_NONE_IDLE) or row[4:16]!=bytes(12) or row[152:]!=bytes(8):
            raise ValueError('BIRTH_TEMPLATE_RECORD')
        for index,tag in enumerate((2,1,1,1,1,2,2,1)):
            if row[16+index*8:20+index*8]!=bytes((tag,0,0,0)):
                raise ValueError('BIRTH_TEMPLATE_PROPERTY_TYPE')
        if row[80:88]!=bytes(8):raise ValueError('BIRTH_TEMPLATE_VIEW_RESERVED')
        model_id,default_id,handle,frame=struct.unpack_from('<4H',row,88)
        state_flags,alpha,speedmul=struct.unpack_from('<HHI',row,116)
        if model_id!=n or default_id!=n or frame or state_flags!=7 or alpha>6 or speedmul!=2*65536:
            raise ValueError('BIRTH_TEMPLATE_INITIAL_STATE')
        if cap and not handle:raise ValueError('BIRTH_TEMPLATE_FRAME_HANDLE_REQUIRED')
    return count


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    r=derive(Source(a.source));table=pack(r);unpack(table);r['table_bytes']=len(table);r['table_sha256']=hashlib.sha256(table).hexdigest()
    (a.output/'birth.b4bt').write_bytes(table);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(models=len(r['models']),admitted=sum(m['admitted'] for m in r['models']),bytes=len(table),world_owner_bound=False)))


if __name__=='__main__':main()
