"""Extra physical state for compiler-admitted NONE/idle births.

No new birth admission: B4BI pairs exactly with B4BT. Frame, script and
environment initializers still reject their unsupported policies.
"""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
from compiler import Source
from source_birth_templates import derive as birth
from source_model_core_4086 import derive as core
from source_model_switch_4086 import ENTITY_CORE_FIELDS
from source_retirement_state import derive as retirement,pack_row,RELATIONS,SCALARS

HEADER=24
STRIDE=208

def derive(source):
    b=birth(source);c=core(source);r=retirement(source);models=[]
    for x,y,z in zip(b['models'],c['models'],r['models']):
        assert x['id']==y['id']==z['id'] and x['source_sha256']==y['source_sha256']==z['source_sha256']
        d=dict(y['fields'])
        if x['admitted']:
            if d['type']!=0 or z['onkill_required'] or z['clear_entry_scripts']:raise ValueError('BIRTH_CORE_POLICY')
            for f in ('multiple','subject_to_gravity','no_adjust_base'):
                if d[f]<0:d[f]=0 if f=='multiple' else 1
        models.append(dict(id=x['id'],identity=x['identity'],source_sha256=x['source_sha256'],admitted=x['admitted'],rejections=x['rejections'],core={f:d[f] for f in ENTITY_CORE_FIELDS},type=d['type'],mp=d['mp'],idling=3 if x['admitted'] else 0,summonkill=z['summonkill']))
    return dict(schema='BYOR_4086_NONE_IDLE_BIRTH_CORE_V1',models=models,admission_scope=b['admission_scope'],world_installer_bound=False,native_birth_core_bound=False,motu_gameplay_proven=False,no_color_reduction=True)

def pack(report):
    if not 1<=len(report['models'])<=16:raise ValueError('BIRTH_CORE_CAPACITY')
    body=bytearray()
    for i,m in enumerate(report['models']):
        if m['id']!=i:raise ValueError('BIRTH_CORE_ID')
        body.extend(struct.pack('<HH12x',i,int(m['admitted'])))
        values=[m['core'][f] for f in ENTITY_CORE_FIELDS]+[m['type'],m['mp'],0,0,0,0]
        assert len(values)==24
        body.extend(struct.pack('<24I',*[n&0xffffffff for n in values]))
        body.extend(struct.pack('<8I',m['idling'],0,0,0,0,0,0,0))
        row=dict.fromkeys(RELATIONS+SCALARS,0);row['summonkill']=m['summonkill'];body.extend(pack_row(row,128))
    return struct.pack('<4sHHHHIII',b'B4BI',1,STRIDE,len(report['models']),0,len(body),zlib.crc32(body)&0xffffffff,0)+body

def unpack(raw):
    if len(raw)<HEADER:raise ValueError('BIRTH_CORE_HEADER')
    magic,version,stride,count,res,size,crc,flags=struct.unpack_from('<4sHHHHIII',raw)
    if (magic,version,stride,res,flags)!=(b'B4BI',1,STRIDE,0,0) or not 1<=count<=16 or size!=count*STRIDE or len(raw)!=HEADER+size or crc!=zlib.crc32(raw[HEADER:])&0xffffffff:raise ValueError('BIRTH_CORE_ABI')
    for i in range(count):
        row=raw[HEADER+i*STRIDE:HEADER+(i+1)*STRIDE];identity,cap=struct.unpack_from('<HH',row)
        if identity!=i or cap not in (0,1) or row[4:16]!=bytes(12):raise ValueError('BIRTH_CORE_ROW')
        if cap and (row[16+72:16+96]!=bytes(24) or row[112:144]!=struct.pack('<8I',3,0,0,0,0,0,0,0)):raise ValueError('BIRTH_CORE_ADMITTED_STATE')
        if row[144:180]!=bytes(36) or row[184:]!=bytes(24):raise ValueError('BIRTH_CORE_RELATIONS')
    return count

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));raw=pack(r);unpack(raw);r.update(table_bytes=len(raw),table_sha256=hashlib.sha256(raw).hexdigest());a.output.mkdir(parents=True,exist_ok=True);(a.output/'birthcore.b4bi').write_bytes(raw);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(len(r['models']),'models;',sum(m['admitted'] for m in r['models']),'admitted existing birth policies;',len(raw),'bytes')

if __name__=='__main__':main()
