"""Derive the closed synchronized player drop-weapon model domain."""
from source_model_transition_bundle import compile
import struct


def derive(source):
    reports,data,manifest=compile(source);models=reports['requirements']['models'];rows=[]
    roles={m['id']:{a['engine_animation_id']:dict(handle=a['handle'],numframes=a['numframes'])for a in reports['animations']['animations']if a['model']==m['identity']and a['numframes']}for m in models}
    for base in models:
        if not struct.unpack_from('<i',data['core'],160*base['id']+156)[0]&1 or not base['weapon_ids']:continue
        for old_id in sorted({base['id'],*(i for i in base['weapon_ids']if i is not None and i>=0)}):
            old=models[old_id];target=base
            if old_id==target['id']:continue
            current=set(roles[old_id])
            inherited_into_weapon=sorted(set(roles[base['id']])-current)if not old['model_flag']&1 else []
            current.update(inherited_into_weapon)
            missing=sorted(current-set(roles[target['id']]))
            # All positive old roles are inherited unless the new cache refuses
            # inheritance. The pinned source does this before choosing animation.
            remaining=missing if target['model_flag']&1 else []
            rows.append(dict(default_model=base['id'],old_model=old_id,new_model=target['id'],old_identity=old['identity'],new_identity=target['identity'],target_model_flag=target['model_flag'],current_roles=sorted(current),roles_inherited_into_weapon_before_drop=inherited_into_weapon,roles_inherited_before_animation_selection=missing if not target['model_flag']&1 else [],unresolved_roles=remaining,synchronized=not remaining))
    return dict(schema='BYOR_PLAYER_DROP_MODEL_SYNC_CAPABILITY_V1',engine_commit=reports['requirements']['engine_commit'],transitions=rows,all_declared_current_roles_synchronize=bool(rows)and all(r['synchronized']for r in rows),direct_model_animation_mutators_admitted=False,source_cache_inheritance_required=True,production_binding=False,motu_gameplay_proven=False,no_color_reduction=True)
