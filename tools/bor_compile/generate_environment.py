"""Generate source fixed-base altitude bindings for already selected build data.

No stage/model names are recognized here. Nonzero altitude on an unimplemented
source driver fails closed. The production catalog is selection, not semantics.
"""
import json
from pathlib import Path

from compiler import Source, stage, key
from entity_parse import parse_entity
from queue_abi import RECORD_SIZE
from environment_semantics import display_name


def generate(configs, output):
    sources = {}
    rows = []
    aliases = []
    for physical, cfg in enumerate(configs):
        if cfg['pak'] not in sources:
            sources[cfg['pak']] = Source(cfg['pak'])
        source = sources[cfg['pak']]
        ir = stage(source, cfg['source_level'])
        # Existing foreign-dialect production adapters do not establish this
        # parser's full queue alignment. Keep their alias presentation blocked.
        if not ir.diagnostics:
            prefix = len(ir.environment.get('hole', []))
            if len(Path(cfg['spawn']).read_bytes()) != (len(ir.queue) + prefix) * RECORD_SIZE:
                raise ValueError(f'ALIAS_QUEUE_ALIGNMENT: {ir.source_path}')
            for i, q in enumerate(ir.queue):
                if q.alias:
                    aliases.append(dict(physical=physical, queue=i + prefix, source_model=q.character,
                        source_path=ir.source_path, display_name=display_name(q.character, q.alias)))
        nonzero = [(i, q) for i, q in enumerate(ir.queue) if q.altitude not in (None, 0)]
        if not nonzero:
            continue
        if ir.diagnostics:
            raise ValueError(f'ALTITUDE_SOURCE_UNCERTAIN: {ir.source_path}: {ir.diagnostics}')
        models = {}
        for d in source.lines('DATA/MODELS.TXT'):
            if d.name in ('load', 'know') and len(d.values) == 2:
                models[d.values[0].casefold()] = parse_entity(source.read(d.values[1]).decode('latin1'))
        prefix = len(ir.environment.get('hole', []))
        packed = Path(cfg['spawn']).read_bytes()
        if len(packed) != (len(ir.queue) + prefix) * RECORD_SIZE:
            raise ValueError(f'ALTITUDE_QUEUE_ALIGNMENT: {ir.source_path}')
        for i, q in nonzero:
            model = models[q.character.casefold()]
            if model.get('type') != 'steamer':
                raise ValueError(f'ALTITUDE_DRIVER_UNBOUND: {ir.source_path}: {q.character}: {model.get("type")}')
            # Source 320 -> target 256 scale. Signed Q16.16 base is separate
            # from the unsigned Q8.8 jump/throw displacement; no state inference.
            value = round(q.altitude * 4 * 65536 / 5)
            if not -(1 << 31) <= value < 1 << 31:
                raise ValueError(f'ALTITUDE_TARGET_RANGE: {ir.source_path}: {q.altitude}')
            rows.append(dict(physical=physical, queue=i + prefix, source_path=ir.source_path,
                             source_model=q.character, source_altitude=q.altitude, base_q16_16=value))
    text = '; Generated fixed-base altitude records; source/type-driven, not stage exceptions.\n'
    text += f'StageEnv_BaseRecordCount = {len(rows)}\nStageEnv_BaseRecords:\n'
    for r in rows:
        data = bytes([r['physical'], r['queue']]) + r['base_q16_16'].to_bytes(4, 'little', signed=True)
        text += '    .db ' + ','.join(str(b) for b in data) + '\n'
    if not rows:
        text += '    .db 0\n'
    names = sorted({r['display_name'] for r in aliases})
    # Dedicated half-bank budget leaves the existing scene runtime and these
    # helpers in bank 13 intact. Indexed scans are 16-bit; never wrap a table.
    table_bytes=max(1,len(rows)*6)+max(1,len(aliases)*4)+2*(len(names)+1)+sum(len(n.encode('latin1'))+1 for n in names)
    if table_bytes>0x4000:
        raise ValueError(f'ENVIRONMENT_TABLE_CAPACITY_EXCEEDED: {table_bytes} required bytes, 16384 available')
    text += f'StageEnv_AliasRecordCount = {len(aliases)}\nStageEnv_AliasRecords:\n'
    for r in aliases:
        r['alias_id'] = names.index(r['display_name']) + 1
        text += f"    .db {r['physical']},{r['queue']}\n    .dw {r['alias_id']}\n"
    if not aliases:
        text += '    .db 0\n'
    text += 'StageEnv_AliasNamePtrs:\n    .dw 0\n'
    for i in range(len(names)):
        text += f'    .dw StageEnv_AliasName{i+1}\n'
    for i, name in enumerate(names):
        text += f'StageEnv_AliasName{i+1}:\n    .db ' + ','.join(map(str, name.encode('latin1') + b'\0')) + '\n'
    Path(output).write_text(text, encoding='ascii')
    return dict(bases=rows, aliases=aliases, names=names, table_bytes=table_bytes,
                alias_presentation='BLOCKED: runtime has no general opponent-name HUD')
