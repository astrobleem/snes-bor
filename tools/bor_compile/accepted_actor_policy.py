"""Read an explicit accepted-build binding; never infer compatibility by name.

The original project content hash and committed catalog scope the adapter.
Unshipped models and different PAKs cannot inherit the adapter.
"""
import json
import re
import struct
from functools import lru_cache

from compiler import baseline, digest, key
from actor_frame_abi import check_actor_media_extent


def bindings(report, ref, msu, rom):
    config,read=baseline(ref)
    read=lru_cache(None)(read)
    inventory=json.loads(read('docs/bor_environment_s4_bor.json'))
    if report['project_id']!=inventory['project_id']:
        raise ValueError('COMPAT_PROJECT_NOT_ACCEPTED')
    evidence=json.loads(read('docs/bor_environment_s4_runtime.json'))
    if digest(msu)!=evidence['msu_sha256'] or digest(rom)!=evidence['rom_sha256']:
        raise ValueError('COMPAT_ARTIFACT_NOT_ACCEPTED')
    main=read('src/main.pasm').decode()
    def constant(name):
        match=re.search(r'(?m)^'+re.escape(name)+r'\s*=\s*(\d+)',main)
        if not match: raise ValueError('UNBOUND_COMPAT_CONSTANT: '+name)
        return int(match[1])
    counts=[int(n) for row in re.findall(r'(?m)^\s*\.db\s+([^;\r\n]+)',
             read('src/generated/stage_environment_maps.pasm').decode()) for n in row.split(',')]
    if len(counts)!=256: raise ValueError('COMPAT_MAP_DIRECTORY_MISMATCH')
    # These are the committed ABI fields, not source role IDs.
    fields={'idle':(0,3),'walk':(1,4),'attack':(2,5),'fall':(6,7),
            'attack2':(12,13),'rise':(14,15),'jump':(17,18),
            'jumpattack':(19,20),'jumpattack2':(21,22),'special':(23,24)}
    for i,name in enumerate(('attack3','attack4','grab','slide','riseattack','grabattack','freespecial','get')):
        fields[name]=(25+2*i,26+2*i)
    fields['waiting']=(48,49)
    result={}
    for runtime_id,c in enumerate(config['ROSTER_CONFIGS']):
        if c['family']!='bor-original': continue
        identity=key(c['source_character'])
        candidates=[m for m in report['models'].values() if
                    key(m['ir']['source_path']).rsplit('/',1)[0]==identity or
                    key(m['ir']['source_path']).rsplit('.',1)[0]==identity]
        if len(candidates)!=1: raise ValueError('COMPAT_SOURCE_IDENTITY_AMBIGUOUS')
        model=candidates[0];source=model['actor_lowering']
        record=msu[16+runtime_id*50:16+(runtime_id+1)*50]
        if len(record)!=50: raise ValueError('COMPAT_ROSTER_RECORD_TRUNCATED')
        blob_start=struct.unpack_from('<I',record,8)[0]
        blob_end=struct.unpack_from('<I',msu,16+(runtime_id+1)*50+8)[0] if runtime_id+1<msu[9] else struct.unpack_from('<I',msu,12)[0]
        if not 16<=blob_start<blob_end<=len(msu): raise ValueError('COMPAT_ACTOR_BLOB_BOUNDS')
        check_actor_media_extent(blob_start,blob_end-blob_start,project=report['project_id'],model=source['source_path'])
        moveset=json.loads(read(c['converted_prefix']+'_moveset.json'))
        animations={}
        target_slots={role:dict(frame_count=record[count],delay=record[delay])
                      for role,(count,delay) in fields.items()}
        for role,(count,delay) in fields.items():
            ordinal=moveset['roles'].get(role)
            if ordinal is None or not record[count]: continue
            anim=moveset['animations'][ordinal]
            manifest=json.loads(read(anim['dir']+'/manifest.json'))
            if len(manifest['frames'])!=record[count]: raise ValueError('COMPAT_FRAME_COUNT_MISMATCH')
            slot_binding=dict(target_role=role,frame_count=record[count],
                delay=record[delay],clock='accepted available animation ticks; MSU busy gating retained',
                geometry={k:manifest.get(k) for k in ('scale','hotspot_canvas')})
            name=anim['name'].casefold()
            if name in animations:
                animations[name].setdefault('additional_runtime_bindings',[]).append(slot_binding)
            else:
                animations[name]=slot_binding
        result[tuple(source['source_identity'])]=dict(baseline=ref,
            source_identity=source['source_identity'],source_sha256=source['source_sha256'],
            runtime_id=runtime_id,animations=animations,
            contract=dict(kind='delegate_immutable_accepted_runtime',
                record_sha256=digest(record),blob_offset=blob_start,blob_size=blob_end-blob_start,
                runtime_slots=target_slots,
                rom_sha256=digest(rom),msu_sha256=digest(msu),
                damage=dict(hp_subtraction=constant('CHAR_HP_PER_HIT'),reaction='accepted knockdown/grab state logic'),
                collision=dict(abs_dx_less_than=constant('CHAR_HITBOX_W'),abs_dy_less_than=constant('CHAR_HITBOX_H')),
                behavior='unchanged accepted input/AI/prop/biker/emitter drivers; not source-exact AI',
                stats=dict(player_hp_max=constant('CHAR_HP_MAX'),player_speed=constant('PLAYER_SPEED'),
                           npc_health='packed stage spawn health; not the actor model health default',
                           source='src/main.pasm constants and existing Spawn_Play dispatch'),
                effects='unchanged accepted pickup/score/life/health paths; no new effect certified',
                palettes=dict(alternate_count=counts[runtime_id],format='16-color BGR555, 32 bytes each')))
    return result
