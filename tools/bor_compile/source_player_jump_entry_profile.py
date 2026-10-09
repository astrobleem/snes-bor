"""Readonly source jump-entry requirements, without actor-name dispatch."""
from compiler import key
from source_profile import document,discover
from source_model_core_4086 import derive as model_core,binary32,number,integer
from script_dispatch_4086 import compile_source

ABSENT_ROLES=('slide','runslide','runjump','forwardjump')


def load(rows,height,speed,core):
    fields=dict(jumpheight=height,jumpspeed=speed,jumpmovez=0)
    for row in rows:
        name=row['directive'];v=row['values']
        if name=='jumpheight':fields[name]=number(v)
        elif name=='jumpspeed':fields[name]=binary32(number(v)/10)
        elif name=='jumpspeedf':fields['jumpspeed']=number(v)
        elif name=='jumpmove':fields['jumpmovez']=integer(v,1)
    if fields['jumpspeed']<0:fields['jumpspeed']=max(core['speed'],1.0)
    fields.update(runjumpheight=core['runjumpheight'],runjumpdist=core['runjumpdist'])
    return fields


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    structure=discover(source,docs);height=4.0;speed=-1.0
    for row in docs[key(structure['models_path'])]['directives']:
        if row['directive']=='jumpheight':height=number(row['values'])
        elif row['directive']=='jumpspeed':speed=number(row['values'])
    animations=compile_source(source)['animation_handles'];result=[]
    for m in model_core(source)['models']:
        declared=[a['role']for a in animations if a['model']==m['identity']]
        if any(r in declared for r in ABSENT_ROLES):raise ValueError('PLAYER_JUMP_ENTRY_ALTERNATE_OWNER_REQUIRED:'+m['identity'])
        fields=load(docs[key(m['source_path'])]['directives'],height,speed,m['fields'])
        result.append(dict(id=m['id'],source_sha256=m['source_sha256'],fields=fields,jump_present='jump'in declared,jumpdelay_present='jumpdelay'in declared))
    return dict(capability='READONLY_ABSENT_SLIDE_AND_ALTERNATE_JUMP',models=result,absent_roles=list(ABSENT_ROLES),
        direct_animation_table_mutation_admitted=False,pending_jump_descriptor_owner_required=True,tryjump_and_dojump_services_required=True,native_bound=False,motu_gameplay_proven=False)
