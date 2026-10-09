"""Readonly jump landing admission from source model/animation authority."""
import hashlib
import subprocess
from dialect_4086 import ENGINE_COMMIT
from source_dojump_profile import derive as dust_absence
from source_animation_physics_4086 import derive as physics
from source_run_tuple_profile import derive as run_tuples
from script_dispatch_4086 import compile_source


def derive(source):
    dust = dust_absence(source)
    raw = subprocess.check_output(['git', '-C', 'E:/gh/openbor-bcec', 'show',
                                   ENGINE_COMMIT + ':engine/openbor.c']).decode('latin1')
    init = raw[raw.index('s_model *init_model('):raw.index('void update_model_loadflag(')]
    default = next(line for line in init.splitlines() if 'newchar->dust.jump_land' in line)
    if default.split('=')[1].strip() != '-1;':
        raise ValueError('COMMON_JUMP_DUST_DEFAULT_CHANGED')
    animations = compile_source(source)['animation_handles']
    metadata = physics(source)['animations']
    by_model = {m['identity']: m['id'] for m in dust['models']}
    return dict(capability='READONLY_JUMP_LAND_DUST_ABSENCE', models=dust['models'],
                run_tuples=run_tuples(source), animations=[dict(handle=a['handle'], model=by_model[a['model']],
                    landframe=a['landframe'], role=a['role']) for a in metadata],
                jumpland_handles=[a['handle'] for a in animations if a['role']=='jumpland'],
                literal_dust_default_sha256=hashlib.sha256(default.encode()).hexdigest(),
                mutable_animation_or_dust_fields_admitted=False, native_bound=False,
                motu_gameplay_proven=False)
