"""Source-derived readonly absence admission for the jump dust service."""
import hashlib
import subprocess
from compiler import key
from source_profile import document, discover
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def derive(source):
    authority = subprocess.check_output(['git', '-C', 'E:/gh/openbor-bcec', 'show',
                                         ENGINE_COMMIT + ':engine/openbor.c']).decode('latin1')
    init = authority[authority.index('s_model *init_model('):authority.index('void update_model_loadflag(')]
    default = next(line for line in init.splitlines() if 'newchar->dust.jump_start' in line)
    if default.split('=')[1].strip() != '-1;':
        raise ValueError('DOJUMP_DUST_DEFAULT_AUTHORITY_CHANGED')
    docs = {k: document(source, n) for k, (n, _) in source.index.items() if k.endswith('.txt')}
    structure = discover(source, docs)
    models = []
    for i, model in enumerate(structure['models']):
        doc = docs[key(model['source_path'])]
        if any(r['directive'] == 'dust' for r in doc['directives']):
            raise ValueError('DOJUMP_DUST_SPAWN_OWNER_REQUIRED:' + model['declaration'])
        models.append(dict(id=i, identity=model['declaration'],
                           source_sha256=hashlib.sha256(source.read(model['source_path'])).hexdigest(),
                           dust_jump_start=-1))
    return dict(capability='READONLY_JUMP_DUST_ABSENCE', models=models,
                engine_commit=ENGINE_COMMIT, literal_default_sha256=hashlib.sha256(default.encode()).hexdigest(),
                literal_dojump_sha256=hashlib.sha256(extract(authority, 'dojump').encode()).hexdigest(),
                mutable_dust_fields_admitted=False, native_bound=False, motu_gameplay_proven=False)
