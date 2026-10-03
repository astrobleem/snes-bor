"""Project-scoped, deterministic descriptor catalog; not a publication certificate.

16-byte header: magic/version u16, project token u32, count/stride/size/reserved
u16. 16-byte entries: actor/role/profile/flags/count u16, table u24 + pad,
reserved u16. All bytes occupy one bank; frame encoding belongs to actor_frame_abi.
Profile 1 is SOURCE_EXACT; profile 2 is explicitly labeled fixture compatibility
control data, never an inferred accepted-runtime equivalence certificate.
"""
import hashlib
import struct

from actor_frame_abi import pack_animation
from actor_lowering import allocate_ids
from lowering_policy import source_fingerprint

MAGIC=0x3543
VERSION=1
HEADER_BYTES=ENTRY_BYTES=16


def generate_catalog(models, *, base_address, pinned=None, compatibility_controls=()):
    models=list(models)
    if not models: raise ValueError('CATALOG_EMPTY')
    identities=[tuple(m['source_identity']) for m in models]
    if len(set(identities))!=len(identities): raise ValueError('CATALOG_DUPLICATE_MODEL')
    projects={identity[0] for identity in identities}
    if len(projects)!=1: raise ValueError('CATALOG_PROJECT_SCOPE')
    if not 0<=base_address<=0xFFFFFF or base_address&65535<0x8000:
        raise ValueError('CATALOG_LOROM_ADDRESS')
    project=next(iter(projects))
    project_token=int.from_bytes(hashlib.sha256(project.encode()).digest()[:4],'little')
    ids=allocate_ids(identities,pinned=pinned)
    roles=sorted({a['role'] for m in models for a in m['animations']})
    role_ids={role:i+1 for i,role in enumerate(roles)}
    rows=[];by_identity=dict(zip(identities,models))
    for identity,model in sorted(by_identity.items()):
        seen=set()
        for animation in model['animations']:
            role=animation['role']
            if role in seen: raise ValueError('CATALOG_DUPLICATE_ROLE')
            seen.add(role)
            frames=pack_animation(model,role)
            rows.append(dict(identity=identity,actor_id=ids[identity],role=role,
                role_id=role_ids[role],profile=1,profile_name='SOURCE_EXACT',
                scope='SOURCE_DESCRIPTOR_ONLY',frames=frames,
                source_fingerprint=source_fingerprint(model)))
    for control in compatibility_controls:
        identity=tuple(control['source_identity']);role=control['role']
        if identity not in by_identity or not any(a['role']==role for a in by_identity[identity]['animations']):
            raise ValueError('CATALOG_CONTROL_IDENTITY')
        if control.get('scope')!='ISOLATED_GOLDEN_CONTROL' or not control.get('policy'):
            raise ValueError('CATALOG_EXPLICIT_COMPAT_POLICY_REQUIRED')
        frames=control['frame_bytes']
        source_row=next(r for r in rows if r['identity']==identity and r['role']==role and r['profile']==1)
        if len(frames)!=len(source_row['frames']): raise ValueError('CATALOG_CONTROL_FRAME_COUNT')
        rows.append(dict(identity=identity,actor_id=ids[identity],role=role,
            role_id=role_ids[role],profile=2,profile_name='ACCEPTED_COMPAT',
            scope=control['scope'],policy=control['policy'],frames=frames,
            source_fingerprint=source_fingerprint(by_identity[identity])))
    rows.sort(key=lambda r:(r['actor_id'],r['role_id'],r['profile']))
    keys=[(r['actor_id'],r['role_id'],r['profile']) for r in rows]
    if len(keys)!=len(set(keys)): raise ValueError('CATALOG_DUPLICATE_KEY')
    offset=HEADER_BYTES+ENTRY_BYTES*len(rows)
    total=offset+sum(len(r['frames']) for r in rows)
    if not rows or total>65535 or (base_address&65535)+total>65536:
        raise ValueError(f'CATALOG_BANK_EXTENT: project={project}, required_bytes={total}, '
                         f'bank_available_bytes={65536-(base_address&65535)}, base_address={base_address:#08x}')
    entries=bytearray();payload=bytearray();manifest_rows=[]
    for row in rows:
        pointer=base_address+offset
        entries.extend(struct.pack('<5H',row['actor_id'],row['role_id'],row['profile'],0,len(row['frames'])//32))
        entries.extend(pointer.to_bytes(3,'little')+b'\0\0\0')
        manifest_rows.append({**{k:v for k,v in row.items() if k!='frames'},
                              'address':pointer,'frame_count':len(row['frames'])//32})
        payload.extend(row['frames']);offset+=len(row['frames'])
    header=struct.pack('<HHI4H',MAGIC,VERSION,project_token,len(rows),ENTRY_BYTES,total,0)
    blob=header+entries+payload
    assert len(blob)==total
    manifest=dict(version=VERSION,project=project,project_token=project_token,
        base_address=base_address,bytes=total,role_ids=role_ids,entries=manifest_rows,
        sha256=hashlib.sha256(blob).hexdigest(),runtime_certified=False,
        id_contract='project-scoped sorted identities with explicit pins; sorted source role names')
    return blob,manifest
