"""Source-derived closed post-constructor capabilities, never actor aliases.

The immutable model palette identity is separate from physical palette upload.
No-events admission requires absence of onspawn and stage spawn scripts.
"""
import argparse
import hashlib
import json
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from source_profile import document
from source_model_registry import derive as registry
from source_stage_queue_4086 import derive as queue


def derive(source):
    models=[]
    for model in registry(source)['models']:
        doc=document(source,model['source_path'])
        rows=doc['directives']
        for row in rows:
            if row['directive'] in ('remap','globalmap','subclass'):
                raise ValueError('SPAWN_PALETTE_LOADER_REQUIRED:'+row['directive'])
            if row['directive']=='onspawnscript':
                raise ValueError('SPAWN_EVENT_OWNER_REQUIRED')
        alternates=[r for r in rows if r['directive']=='alternatepal']
        if len(alternates)>65535:
            raise ValueError('SPAWN_MAP_IDENTITY_CAPACITY')
        assets=[]
        for row in alternates:
            if len(row['values'])!=1:
                raise ValueError('SPAWN_ALTERNATEPAL_ARITY')
            path=source.image_path(row['values'][0])
            assets.append(dict(map=len(assets)+1,source_path=path,
                               sha256=hashlib.sha256(source.read(path)).hexdigest()))
        models.append(dict(model=model['id'],source_path=model['source_path'],
                           source_sha256=doc['sha256'],maps_loaded=len(assets),
                           alternate_palettes=assets,spawn_event_policy='NO_MODEL_ONSPAWN'))
    stages=queue(source)['stages']
    return dict(schema='BYOR_4086_SPAWN_CAPABILITIES_V1',engine_commit=ENGINE_COMMIT,
                models=models,stages=[dict(stage_id=s['stage_id'],source_path=s['source_path'],
                source_sha256=s['source_sha256'],spawn_event_policy='NO_STAGE_SPAWN_SCRIPT') for s in stages],
                palette_upload_bound=False,boss_music_service_required=True,
                native_properties_bound=False,live_queue_dispatch_bound=False,
                foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    d=derive(Source(a.source))
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n')
    print('DERIVED',len(d['models']),'model capabilities;',sum(m['maps_loaded'] for m in d['models']),'alternate palettes')


if __name__=='__main__':main()
