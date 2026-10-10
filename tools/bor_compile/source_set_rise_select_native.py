"""set_rise typed fallback shares the actual checked set_fall cache selector."""
from compiler import key
from source_profile import document,discover
from source_animation_ids import configure
from dialect_4086 import ENGINE_COMMIT

def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};st=discover(source,docs);ids=configure(docs[key(st['models_path'])]['directives'])
 return dict(schema='BYOR_SET_RISE_SELECTION_REQUIREMENTS_V1',engine_commit=ENGINE_COMMIT,rises=ids['arrays']['rises'],maximum=ids['max_animations'],full_set_rise_bound=False)

def emit(work,requirements,sy,code_bank=39):
 from source_set_fall_select_native import emit as select
 text=select(work,dict(falls=requirements['rises']),sy,code_bank)
 marker=' cmp #'+str(0xb6b6)
 if text.count(marker)!=1:raise ValueError('RISE_SELECTOR_SHARED_TAG_SHAPE')
 return text.replace(marker,' cmp #'+str(0xb6c3)).replace('SetFallSelect_','SetRiseSelect_')

def emit_begin(work,sy):
 from source_set_pain_select_native import emit_begin as begin
 # Velocity is cleared by set_rise after ent_set_anim, through target/self
 # pointers separately. The animation initializer cannot clear target XYZ.
 return begin(work,sy,prefix='SetRise',select='SetRiseSelect_Run',magic=0xb6c3,clear_velocity=False)

def emit_frame_prefix(work,sy):
 from source_set_pain_select_native import emit_frame_prefix as frame
 return frame(work,sy,prefix='SetRise')

def emit_frame_owner(sy):
 from source_set_pain_select_native import emit_frame_owner as owner
 return owner(sy,prefix='SetRise')
