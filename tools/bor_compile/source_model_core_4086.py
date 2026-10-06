"""Source-derived cached model core. Media bindings remain explicit identities."""
import argparse,hashlib,json,re,struct
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_model_switch_4086 import CACHED_FIELDS,ENTITY_CORE_FIELDS,GLOBAL_NEGATIVE

TYPE_NAMES=dict(none=0,player=1,enemy=2,item=4,obstacle=8,steamer=16,pshot=32,trap=64,text=128,endlevel=256,npc=512,panel=1024)
MASK_NAMES={k:v for k,v in TYPE_NAMES.items() if k in ('enemy','player','obstacle','npc')};MASK_NAMES['shot']=32
MOVE_NAMES=dict(normal=0,chase=1,chasez=2,chasex=4,avoid=8,avoidz=16,avoidx=32,wander=64,biker=128,arrow=256,star=512,bomb=1024,nomove=2048)
MOVE2_NAMES=dict(normal=0,ignoreholes=0x10000,notargetidle=0x20000)
ATTACK_NAMES=dict(normal=0,noattack=4,always=8)
FLOAT_FIELDS={'speed','runspeed','runjumpheight','runjumpdist'}
PHYSICS=[f for f in ENTITY_CORE_FIELDS if f.startswith('subject_to_')]


def integer(values,index=0):
    match=re.match(r'^[+-]?\d+',values[index]) if index<len(values) else None
    n=int(match[0]) if match else 0
    if not -0x80000000<=n<=0x7fffffff:raise ValueError('MODEL_CORE_INTEGER_DOMAIN')
    return n


def binary32(value):
    return struct.unpack('<f',struct.pack('<f',float(value)))[0]


def number(values,index=0):
    n=binary32(values[index] if index<len(values) else 0)
    if not -32768<=n<32768:raise ValueError('MODEL_CORE_FLOAT_DOMAIN')
    return n


def defaults(jumpheight=4,model_ids=None):
    d=dict.fromkeys(CACHED_FIELDS,0);d.update(type=0,subtype=0)
    for f in GLOBAL_NEGATIVE:
        if f!='shadow':d[f]=-1
    for f in PHYSICS+['no_adjust_base','hostile','candamage','projectilehit','aimove','aiattack','risetime.rise']:d[f]=-1
    d.update(runjumpheight=binary32(jumpheight),runjumpdist=1.0)
    if model_ids is not None:d['flash']=d['bflash']=model_ids.get('flash',-1)
    return d


def apply_type(d,name):
    if name not in TYPE_NAMES:raise ValueError('MODEL_CORE_TYPE_UNSUPPORTED:'+name)
    t=TYPE_NAMES[name];d['type']=t
    if t in (1,2,4,8,64,256,512):
        for f in ('subject_to_wall','subject_to_platform','subject_to_hole','subject_to_gravity'):d[f]=1
        if t in (1,2,4,8,64,512):
            d['subject_to_minz']=d['subject_to_maxz']=1;d['no_adjust_base']=0
        if t in (1,2,4,256,512):d['subject_to_obstacle']=1
        if t==1:d['subject_to_screen']=1
    if t==8:
        if d['aimove']==-1:d['aimove']=0
        d['aimove']|=2048
        # Preserve the pinned loader's second aimove check and OR, including
        # its apparent aiattack typo. Do not silently repair source behavior.
        if d['aimove']==-1:d['aiattack']=0
        d['aimove']|=4
    if t==32:
        if d['aimove']==-1:d['aimove']=0
        d['aimove']|=256
        for f in ('subject_to_hole','subject_to_wall','subject_to_platform','subject_to_screen'):d[f]=0
        for f in ('subject_to_gravity','subject_to_minz','subject_to_maxz','no_adjust_base'):d[f]=1
    if t==128:d.update(subject_to_gravity=0,subject_to_minz=1,subject_to_maxz=1)
    if t==1024:d.update(subject_to_gravity=1,no_adjust_base=1)


def finish(d,riseattack=False):
    t=d['type']
    if d['risetime.rise']==-1:
        if t==1:d['risetime.rise']=100 if riseattack else 200
        elif t in (2,512):d['risetime.rise']=0
    tables={'hostile':{1:11,2:1,8:0,64:0,32:2,512:2},
            'candamage':{1:11,2:33,8:11,64:11,32:11,512:10,4:1},
            'projectilehit':{1:11,2:11,8:11,64:11,32:11,512:11}}
    for field,table in tables.items():
        if d[field]<0 and t in table:d[field]=table[t]


def load(rows,jumpheight=4,model_ids=None):
    d=defaults(jumpheight,model_ids);bindings={};aimove=False;aiattack=False
    for row in rows:
        name,v=row['directive'],row['values']
        if name=='type':
            if len(v)!=1:raise ValueError('MODEL_CORE_TYPE_ARITY')
            apply_type(d,v[0].lower())
        elif name=='subtype':raise ValueError('MODEL_CORE_SUBTYPE_BACKEND_REQUIRED')
        elif name in ('health','mp','shadow','weapnum'):d[name]=integer(v)
        elif name=='score':d['multiple']=integer(v,1)
        elif name=='risetime':d['risetime.rise']=integer(v)
        elif name in PHYSICS or name=='no_adjust_base':d[name]=int(integer(v)!=0)
        elif name in ('speed','speedf'):
            value=number(v)
            if name=='speed':value=max(.5,min(30,binary32(value/10)))
            d['speed']=value
        elif name=='running':
            d.update(runspeed=binary32(number(v)/10),runjumpheight=number(v,1),runjumpdist=number(v,2),runupdown=integer(v,3),runhold=integer(v,4))
        elif name in ('hostile','candamage','projectilehit'):
            d[name]=0
            for value in v:
                if name=='candamage' and value.lower()=='ground':continue
                d[name]|=MASK_NAMES.get(value.lower(),integer([value]))
        elif name=='aimove':
            if not aimove:d['aimove']=0;aimove=True
            if v:
                if v[0].lower() not in MOVE_NAMES:raise ValueError('MODEL_CORE_AIMOVE_UNSUPPORTED')
                d['aimove']|=MOVE_NAMES[v[0].lower()]
            if len(v)>1:
                if v[1].lower() not in MOVE2_NAMES:raise ValueError('MODEL_CORE_AIMOVE2_UNSUPPORTED')
                d['aimove']|=MOVE2_NAMES[v[1].lower()]
        elif name=='aiattack':
            if not aiattack:d['aiattack']=0;aiattack=True
            if v:
                if v[0].lower() not in ATTACK_NAMES:raise ValueError('MODEL_CORE_AIATTACK_UNSUPPORTED')
                d['aiattack']|=ATTACK_NAMES[v[0].lower()]
        elif name in ('flash','bflash','knife','fireb','playshot','playshotw','bomb','playbomb','star','playshotno'):
            if len(v)!=1:raise ValueError('MODEL_CORE_DEPENDENCY_ARITY')
            field={'fireb':'knife','playshot':'knife','playshotw':'knife','playbomb':'bomb','playshotno':'pshotno'}.get(name,name)
            if model_ids is None:bindings[field]=v[0]
            else:d[field]=-1 if v[0].lower()=='none' else model_ids.get(v[0].lower(),-1)
        elif name=='dust':
            for i,field in enumerate(('dust.fall_land','dust.jump_land')):
                value=v[i] if i<len(v) else ''
                if model_ids is None:bindings[field]=value
                else:d[field]=-1 if value.lower()=='none' else model_ids.get(value.lower(),-1)
        elif name in ('icon','iconpain','icondie','iconget','diesound'):
            if not v:raise ValueError('MODEL_CORE_MEDIA_ARITY')
            fields=['icon.'+x for x in ('def','pain','die','get')] if name=='icon' else ['diesound'] if name=='diesound' else ['icon.'+name[4:]]
            if name=='icon' and 'icon.def' in bindings:raise ValueError('MODEL_CORE_DUPLICATE_ICON')
            for f in fields:bindings[f]=v[0]
    finish(d,any(r['directive']=='anim' and r['values'] and r['values'][0].lower()=='riseattack' for r in rows))
    return d,bindings


def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')};structure=discover(source,docs)
    globals=docs[key(structure['models_path'])]['directives'];jumpheight=4
    for row in globals:
        if row['directive']=='jumpheight':jumpheight=number(row['values'])
    ids={m['declaration'].lower():i for i,m in enumerate(structure['models'])};models=[]
    for i,m in enumerate(structure['models']):
        doc=docs[key(m['source_path'])];d,bindings=load(doc['directives'],jumpheight,ids)
        models.append(dict(id=i,identity=m['declaration'],source_path=m['source_path'],source_sha256=doc['sha256'],fields=d,media_bindings=bindings))
    return dict(schema='BYOR_4086_CACHED_MODEL_CORE_INPUTS_V1',models=models,cache_fields=CACHED_FIELDS,
        core_fields=ENTITY_CORE_FIELDS,media_indices_bound=False,complete_model_constructor_bound=False,motu_gameplay_proven=False)


def pack(report,media_indices):
    if not 1<=len(report['models'])<=16:raise ValueError('MODEL_CORE_NATIVE_CAPACITY')
    data=bytearray()
    for number,m in enumerate(report['models']):
        if m['id']!=number:raise ValueError('MODEL_CORE_IDENTITY')
        d=dict(m['fields'])
        for field,name in m['media_bindings'].items():
            if field not in CACHED_FIELDS or key(name) not in media_indices:raise ValueError('MODEL_CORE_MEDIA_INDEX_UNBOUND:'+name)
            d[field]=media_indices[key(name)]
        for field in CACHED_FIELDS:data.extend(struct.pack('<f' if field in FLOAT_FIELDS else '<i',d[field]))
        data.extend(struct.pack('<i',d['type']))
    return bytes(data)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(models=len(r['models']),media_indices_bound=False)))


if __name__=='__main__':main()
