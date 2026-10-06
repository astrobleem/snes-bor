"""Closed single-walk-series capability; no target-search aliasing."""
from source_animation_ids import AUTHORITY
import json

def default_walk_capability(identities):
 if identities['limits']['max_walks']!=1:raise ValueError('SOURCE_WALK_RANGE_SERVICE_REQUIRED')
 default=json.loads(AUTHORITY.read_text())['default_arrays']['walks'][0]
 for model in identities['models']:
  if any(a['role']=='walk'and a['engine_animation_id']!=default for a in model['animations']):raise ValueError('SOURCE_DEFAULT_WALK_IDENTITY')
 return dict(schema='BYOR_4086_DEFAULT_WALK_CAPABILITY_V1',capability='DEFAULT_WALK_ONLY',default_animation_id=default,models=[m['identity']for m in identities['models']],walkmode_domain=[0,1],walkmode_physical_offset=44,native_animation_initializer_required=True,target_search_required=False,native_world_installer_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False)
