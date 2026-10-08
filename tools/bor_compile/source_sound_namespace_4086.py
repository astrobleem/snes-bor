"""Generic frame/model/engine source sound identities, with stable frame prefix.

Paths for engine samples come from pinned load_special_sounds. This compiler
namespace is independent of BOR's process-wide sample cache numbering.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_profile import document,discover
from source_frame_effects_4086 import derive as frames,pack,unpack


def derive(source,engine=Path('E:/gh/openbor-bcec')):
 raw=subprocess.check_output(['git','-C',str(engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 body=extract(raw,'load_special_sounds')
 controller=subprocess.check_output(['git','-C',str(engine),'show',ENGINE_COMMIT+':engine/sdl/control.c']).decode('latin1')
 rumble=extract(controller,'control_rumble')
 rumble_body=re.sub(r'/\*.*?\*/|//[^\n]*','',rumble[rumble.index('{')+1:rumble.rindex('}')],flags=re.S)
 engine_paths=re.findall(r'(SAMPLE_\w+)\s*=\s*sound_load_sample\("([^"\n]+)"\s*,\s*packfile\s*,\s*0\s*\)',body)
 if len(engine_paths)!=14:raise ValueError('SOURCE_SPECIAL_SAMPLE_AUTHORITY_CHANGED')
 frame_bytes=pack(frames(source));namespace=list(unpack(frame_bytes)['media']);prefix=list(namespace)
 indices={key(n):i for i,n in enumerate(namespace)};identities=[]
 def add(name,required):
  canonical=key(name)
  if canonical not in source.index:
   if required:raise ValueError('SOURCE_REQUIRED_SPECIAL_SOUND_MISSING:'+name)
   return -1
  if canonical not in indices:indices[canonical]=len(namespace);namespace.append(name)
  return indices[canonical]
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs)
 for i,model in enumerate(structure['models']):
  bindings={}
  for row in docs[key(model['source_path'])]['directives']:
   if row['directive']=='anim':break
   if row['directive']in('diesound',):
    if len(row['values'])!=1:raise ValueError('SOURCE_MODEL_SOUND_ARITY')
    name=row['values'][0];bindings[row['directive']]=dict(source_path=name,sound_index=add(name,False),source_line=row['line'])
  identities.append(dict(id=i,identity=model['declaration'],source_path=model['source_path'],bindings=bindings))
 # load_special_sounds returns 0 on a missing sample, but startup continues.
 # Preserve each failed load as -1; guarded consumers skip that exact identity.
 specials={symbol:dict(source_path=name,sound_index=add(name,False))for symbol,name in engine_paths}
 assets=[dict(sound_index=i,source_path=name,source_sha256=hashlib.sha256(source.read(name)).hexdigest())for i,name in enumerate(namespace)]
 return dict(schema='BYOR_4086_SOURCE_SOUND_NAMESPACE_V1',engine_commit=ENGINE_COMMIT,engine_load_function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),
  source_frame_table_sha256=hashlib.sha256(frame_bytes).hexdigest(),frame_prefix_count=len(prefix),namespace=namespace,assets=assets,models=identities,specials=specials,
  frame_sound_indices_unchanged=namespace[:len(prefix)]==prefix,namespace_policy='frame prefix retained; model sound directives and pinned engine special samples appended by normalized source path',
  missing_model_sound_policy='explicit -1 binding, matching source load failure; no replacement asset',
  special_loader_success=all(r['sound_index']>=0 for r in specials.values()),missing_specials=[symbol for symbol,r in specials.items()if r['sound_index']<0],
  special_loader_failure_does_not_abort_startup=True,
  controller_rumble_source=dict(path='engine/sdl/control.c',function_sha256=hashlib.sha256(rumble.encode('latin1')).hexdigest(),body_empty=not rumble_body.strip(),native_no_op_is_source_equivalent=not rumble_body.strip()),
  runtime_binding_installed=False,audible_playback_proven=False,no_pcm_copies=True,no_color_reduction=True)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 report=derive(Source(a.source),a.engine);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
 print(len(report['namespace']),'source sounds;',report['frame_prefix_count'],'frame prefix;',len(report['specials']),'pinned special samples')


if __name__=='__main__':main()
