"""Source model juggle metric, including shallow-copy current-value reset."""
import hashlib,re,subprocess
from compiler import key
from dialect_4086 import ENGINE_COMMIT
from source_profile import discover,document
from source_model_core_4086 import integer


def derive(source,engine='E:/gh/openbor-bcec'):
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine).decode('latin1')
    default=re.search(r'newchar->jugglepoints.current = newchar->jugglepoints.max = 0;',raw)
    command=re.search(r'case CMD_MODEL_JUGGLEPOINTS:([\s\S]*?)break;',raw)
    if not default or not command or 'newchar->jugglepoints.current = atoi(value);'not in command[1]or 'newchar->jugglepoints.max = atoi(value);'not in command[1]:raise ValueError('JUGGLE_METRIC_SOURCE_AUTHORITY')
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};found=discover(source,docs);models=[]
    for m in found['models']:
        d=docs[key(m['source_path'])];value=0
        for r in d['directives']:
            if r['directive']=='subclass':raise ValueError('JUGGLE_METRIC_SUBCLASS_UNBOUND')
            if r['directive']=='jugglepoints':value=integer(r['values'])
        models.append(dict(identity=m['declaration'],source_sha256=d['sha256'],current=value,maximum=value))
    return dict(schema='BYOR_JUGGLE_METRIC_V1',engine_commit=ENGINE_COMMIT,authority_sha256=hashlib.sha256((default[0]+command[0]).encode('latin1')).hexdigest(),models=models,birth_policy='modeldata shallow copy installs current and maximum',model_switch_policy='replace current and maximum with selected cached model metric; retain entity pain_time',native_model_metric_provider_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
