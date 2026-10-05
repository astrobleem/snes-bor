"""Compiler-owned NONE+WALK metadata for the existing horizontal drift adapter.

ACCEPTED_COMPAT: fixed-point motion and byte RNG, not BOR float/RNG identity.
Combat actors remain on persistent SA-1; typed scenery uses S-CPU services.
"""
from fractions import Fraction
from pathlib import Path
from compiler import Source, stage, model_catalog, key


def write_tables(configs, roster, output='src/generated/source_noncombat.pasm'):
    flags, speeds, health = [0]*256, [0]*256, [0]*256
    records = []
    sources = {}
    for physical, cfg in enumerate(configs):
        if cfg.get('queue_identity_policy') != 'source-identity':
            continue
        if cfg['pak'] not in sources:
            sources[cfg['pak']] = Source(cfg['pak'])
        source = sources[cfg['pak']]
        models = model_catalog(source)
        ir = stage(source, cfg['source_level'])
        for index, event in enumerate(ir.queue):
            if event.kind != 'spawn':
                continue
            model = models[event.character.casefold()]
            entity = model['entity']
            if entity.get('type') != 'none' or 'walk' not in entity['animations']:
                continue
            definition = key(model['source_path'])
            matches = [i for i,r in enumerate(roster) if r['family']==cfg['family']
                       and cfg['source_set_id'] in r.get('runtime_binding_sets',(0,1,2,3))
                       and key(r['source_character']) in (definition.rsplit('/',1)[0],definition.removesuffix('.txt'))]
            if len(matches)!=1:
                raise ValueError('NONCOMBAT_MODEL_BINDING: '+definition)
            slot=matches[0]
            flags[slot]=1
            authored_speed=entity.get('speed')
            speed=min(Fraction(30),max(Fraction(1,2),Fraction(10 if authored_speed is None else authored_speed,10)))*2560
            if speed.denominator != 1:
                raise ValueError('NONCOMBAT_SPEED_DOMAIN')
            speeds[slot]=int(speed)
            health[slot]=int(entity.get('health') or 0)
            records.append((physical,index+len(ir.environment.get('hole',[])),event.coords[0]))
    if len(records)>64:
        raise ValueError('NONCOMBAT_PROVENANCE_CAPACITY: '+str(len(records)))
    lines=['; Generated source NONE+WALK adapter tables; ACCEPTED_COMPAT.']
    def table(label,values):
        lines.append('ActorBehavior_'+label+':')
        for i in range(0,len(values),16):
            lines.append('    .db '+', '.join(map(str,values[i:i+16])))
    import struct
    table('ModelFlags',flags)
    table('ModelSpeed',list(struct.pack('<256I',*speeds)))
    table('ModelHealth',list(struct.pack('<256H',*health)))
    lines+=['ActorBehavior_SpawnCount:', '    .dw '+str(len(records))]
    data=b''.join(struct.pack('<BBh',*r) for r in records)
    table('SpawnRecords',list(data+bytes(256-len(data))))
    Path(output).write_text('\n'.join(lines)+'\n')
    return dict(records=records,adaptation='ACCEPTED_COMPAT_FIXED_POINT_BYTE_RNG_NONE_WALK')
