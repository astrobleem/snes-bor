"""Generic closed zero-depth collision capability from source metadata.

All source models must share immutable grabdistance. Dynamic property writers
remain outside this capability and must be rejected by profile admission.
"""
import hashlib,re,subprocess
from compiler import key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_frame_state_4086 import derive as frames,pack,unpack
from source_model_core_4086 import binary32
from source_checkhit_q16 import q16,checked
from source_checkhit_4086 import f32


def derive(source,engine='E:/gh/openbor-bcec'):
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine).decode('latin1')
    default=re.search(r'float\s+default_model_grabdistance\s*=\s*([0-9.]+)f',raw)
    if not default or not re.search(r'newchar->grabdistance\s*=\s*default_model_grabdistance',raw):raise ValueError('CHECKHIT_GRABDISTANCE_AUTHORITY')
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};found=discover(source,docs)
    if any(r['directive']=='grabdistance'for r in docs[key(found['models_path'])]['directives']):raise ValueError('CHECKHIT_GLOBAL_GRABDISTANCE_ORDER_UNBOUND')
    models=[]
    for m in found['models']:
        doc=docs[key(m['source_path'])];value=binary32(default[1])
        for r in doc['directives']:
            if r['directive']=='subclass':raise ValueError('CHECKHIT_GRABDISTANCE_SUBCLASS_UNBOUND')
            if r['directive']=='grabdistance':
                if len(r['values'])!=1:raise ValueError('CHECKHIT_GRABDISTANCE_ARITY')
                value=binary32(r['values'][0])
        models.append(dict(identity=m['declaration'],source_sha256=doc['sha256'],grabdistance=value))
    if not models or any(m['grabdistance']!=models[0]['grabdistance']for m in models):raise ValueError('CHECKHIT_UNIFORM_GRABDISTANCE_REQUIRED')
    ir=frames(source);table=pack(ir);data=unpack(table)
    for coords in data['boxes']+[r['attack_coords']for r in data['attacks']]:
        if any(coords[4:]):raise ValueError('CHECKHIT_ZERO_DEPTH_REQUIRED')
        if any(not -32768<=v<=32767 for v in coords):raise ValueError('CHECKHIT_BOUNDED_SOURCE_COORDINATES')
    if any(not -32768<=r['counterattack']<=32767 for r in data['attacks']):raise ValueError('CHECKHIT_COUNTER_BOUND_REQUIRED')
    distance=checked(q16(f32(f32(models[0]['grabdistance'])/3+1))+65536)
    if distance<0:raise ValueError('CHECKHIT_NONNEGATIVE_DEPTH_LIMIT_REQUIRED')
    return dict(schema='BYOR_CHECKHIT_ZERO_DEPTH_REQUIREMENTS_V1',capability='ZERO_DEPTH_IMMUTABLE_UNIFORM_GRABDISTANCE',engine_commit=ENGINE_COMMIT,models=models,collision_table_sha256=hashlib.sha256(table).hexdigest(),collision_table_bytes=len(table),box_count=len(data['boxes']),attack_count=len(data['attacks']),boxes=data['boxes'],attacks=data['attacks'],depth_limit_q16=distance,numeric_policy='EXISTING_Q16_COORDINATE_ADAPTATION_WITH_BOUNDED_SIGNED16_RECTANGLES',required_runtime_guards='live paired frame reader, full source coordinate tags, nonzero matching generation, source world phase and slot, signed arithmetic overflow, counter parameter 0/1',dynamic_grabdistance_writer_admitted=False,native_checkhit_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
