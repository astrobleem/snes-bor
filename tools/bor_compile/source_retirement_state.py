"""Physical relation/lifecycle ABI and source-derived retirement requirements.

This proposed exclusive lease is not published by an installer yet. Existing
core grabbing/lasthit and flags weapent remain their authoritative locations.
Declaring this ABI does not make the native kill API available.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from script_ir_4086 import parse_script

BASE=0x409000
STRIDE=64
CAPACITY=128
RELATIONS=('parent','subentity','owner','opponent','binding','landed','hithead','link')
SCALARS=('cantfire','summonkill','takedamage','script_initialized','script_clear_entries','onkill_initialized')
ROLE_BASE=0x43fd80
ROLE_BYTES=32

def slot(token,count):
    if not 1<=count<=CAPACITY:raise ValueError('RETIREMENT_POOL_COUNT')
    if token==0:return None
    n=token-0x414000
    if n<0 or n%80 or n//80>=count:raise ValueError('RETIREMENT_PHYSICAL_POINTER')
    return n//80

def pack_row(row,count):
    if set(row)!=set(RELATIONS+SCALARS):raise ValueError('RETIREMENT_RELATION_ROW_SCHEMA')
    for f in RELATIONS:slot(row[f],count)
    for f in ('takedamage','onkill_initialized'):
        if row[f] not in (0,1):raise ValueError('RETIREMENT_BOOLEAN_DOMAIN')
    values=[row[f] for f in RELATIONS+SCALARS]
    for f in ('cantfire','summonkill'):
        if not -0x80000000<=row[f]<=0x7fffffff:raise ValueError('RETIREMENT_INT32_DOMAIN')
    for f in ('script_initialized','script_clear_entries'):
        if not 0<=row[f]<=0xffffffff:raise ValueError('RETIREMENT_SCRIPT_MASK_DOMAIN')
    return struct.pack('<14I',*[v&0xffffffff for v in values])+bytes(8)

def unpack_row(data,count):
    if len(data)!=STRIDE or data[56:]!=bytes(8):raise ValueError('RETIREMENT_RESERVED_BYTES')
    row=dict(zip(RELATIONS+SCALARS,struct.unpack_from('<14I',data)))
    for f in ('cantfire','summonkill'):
        if row[f]&0x80000000:row[f]-=0x100000000
    if pack_row(row,count)!=data:raise ValueError('RETIREMENT_CANONICAL_ROW')
    return row

def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')};structure=discover(source,docs);models=[]
    for index,m in enumerate(structure['models']):
        doc=docs[key(m['source_path'])];rows=doc['directives'];top=[]
        for r in rows:
            if r['directive']=='anim':break
            top.append(r)
        summon=1 # pinned calloc setup explicitly overwrites zero with 1
        scripts=[];onkill=False;clear=[]
        for r in top:
            n=r['directive'];v=r['values']
            if n=='summonkill':
                if len(v)!=1:raise ValueError('RETIREMENT_SUMMONKILL_ARITY')
                summon=int(v[0]);
                if not -0x80000000<=summon<=0x7fffffff:raise ValueError('RETIREMENT_SUMMONKILL_DOMAIN')
            if n.endswith('script'):
                if len(v)!=1:raise ValueError('RETIREMENT_SCRIPT_ARITY')
                raw=source.read(v[0]);library=parse_script(raw.decode('latin1'),v[0]);scripts.append(dict(kind=n,path=v[0],sha256=hashlib.sha256(raw).hexdigest()))
                if n=='onkillscript':onkill=True
                if 'clear' in library['functions']:clear.append(v[0])
        models.append(dict(id=index,identity=m['declaration'],source_path=m['source_path'],source_sha256=doc['sha256'],summonkill=summon,onkill_required=onkill,clear_entry_scripts=clear,scripts=scripts,retirement_requirements=['RELATION_UNLINK','SCRIPT_INSTANCE_CLEAR_METHOD_1','ROLE_AND_RELATION_REPAIR','ENGINE_GLOBAL_SELF_RESTORE']+(['ONKILL_CALLBACK'] if onkill else [])+(['SCRIPT_CLEAR_ENTRY_CALLBACK'] if clear else [])+(['ONE_MINION_DAMAGE_OR_RECURSIVE_KILL'] if summon==1 else ['ALL_MINION_DAMAGE_OR_RECURSIVE_KILL'] if summon==2 else [])))
    return dict(schema='BYOR_4086_RETIREMENT_REQUIREMENTS_V1',engine_commit=ENGINE_COMMIT,models=models,relation_lease=dict(base=BASE,stride=STRIDE,count=CAPACITY,bytes=STRIDE*CAPACITY,fields={f:4*i for i,f in enumerate(RELATIONS+SCALARS)},reserved=[56,64]),role_lease=dict(base=ROLE_BASE,bytes=ROLE_BYTES,fields=dict(ent_count=0,players=[4,8,12,16],smartbomber=20,textbox=24,level_completed=28)),other_authorities=dict(grabbing='entity core +80',lasthit='entity core +84',weapent='entity flags +28',type='entity core +72',health='entity view +36',exists='entity view +4'),summonkill_default=1,native_retirement_bound=False,physical_lease_published=False,motu_gameplay_proven=False,no_color_reduction=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print('Retirement requirements:',len(r['models']),'models; onkill',sum(m['onkill_required'] for m in r['models']),'clear entries',sum(bool(m['clear_entry_scripts']) for m in r['models']))

if __name__=='__main__':main()
