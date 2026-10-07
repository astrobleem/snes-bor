"""Pinned model/weapon switching policy, separate from live engine services.

Cached model inheritance is mutable and shared across entities. Entity modeldata
is a shallow value copy with a separate uninitialized-property fallback from
the previous entity copy. Do not flatten these two authorities into one table.
Animation initialization and script copying are services, not bound here.
"""
GLOBAL_NEGATIVE=('icon.def icon.pain icon.get icon.die shadow knife pshotno bomb star '
 'flash bflash dust.fall_land dust.jump_land diesound').split()
ENTITY_NEGATIVE=('multiple subject_to_wall subject_to_platform subject_to_obstacle '
 'subject_to_hole subject_to_gravity subject_to_screen subject_to_minz subject_to_maxz '
 'no_adjust_base hostile candamage projectilehit').split()
RUN_FIELDS='runspeed runjumpheight runjumpdist runupdown runhold'.split()
ENTITY_CORE_FIELDS=ENTITY_NEGATIVE+['aimove','aiattack','health','mp','risetime.rise']
CACHED_FIELDS=['speed',*RUN_FIELDS,*GLOBAL_NEGATIVE,*ENTITY_NEGATIVE,'aimove','aiattack','health','mp','risetime.rise','weapnum']


def copy_cached_defaults(old,new):
    if new['model_flag']&1:return
    if not new['speed']:new['speed']=old['speed']
    if not new['runspeed']:
        for field in RUN_FIELDS:new[field]=old[field]
    for field in GLOBAL_NEGATIVE:
        if new[field]<0:new[field]=old[field]
    for number,animation in old['animation'].items():
        if new['animation'].get(number) is None and animation is not None and animation['numframes']>0:
            new['animation'][number]=animation
    if not new['model_flag']&2:
        new['weapnum']=old['weapnum']
        if new['weapon'] is None:
            new['weapon']=old['weapon'];new['numweapons']=old['numweapons']


def copy_entity_uninitialized(entity,old):
    data=entity['modeldata']
    for field in ENTITY_NEGATIVE:
        if data[field]<0:data[field]=old[field]
    for field in ('aimove','aiattack','risetime.rise'):
        if data[field]==-1:data[field]=old[field]
    for field in ('health','mp'):
        if not data[field]:data[field]=old[field]
        entity[field]=min(entity[field],data[field])


def set_colourmap(entity,which):
    # Pinned ent_set_colourmap takes unsigned int, including when a signed
    # source property is passed through C's parameter conversion.
    which&=0xffffffff
    data=entity['modeldata']
    if which>data['maps_loaded']:which=0
    entity['colourmap']=data['palette'] if which<=0 else data['colourmap'][which-1]
    entity['map']=which


def set_model(entity,new,sync,owner):
    old=entity['modeldata'];entity['model']=new;entity['modeldata']=dict(new)
    copy_entity_uninitialized(entity,old);set_colourmap(entity,entity['map'])
    set_model_animation(entity,sync,owner)


def set_model_animation(entity,sync,owner):
    new=entity['modeldata'];animation=new['animation'].get(entity['animnum'])
    if sync and animation is not None:
        entity['animation']=animation
        if entity['animpos']>=animation['numframes']:entity['animpos']=animation['numframes']-1
        entity['nextanim']=(owner['time']+animation['delay'][entity['animpos']])&0xffffffff
    else:
        entity['attacking']=0
        valid=lambda n:new['animation'].get(n) is not None and new['animation'][n]['numframes']>0
        if (not owner['select'] and not owner['time']) or not new['type']&1:
            selected=owner['spawn'] if valid(owner['spawn']) else owner['idle']
        elif not owner['select'] and owner['time'] and new['type']&1:
            selected=next((n for n in (owner['respawn'],owner['spawn']) if valid(n)),owner['idle'])
        elif owner['select'] and valid(owner['select_animation']):selected=owner['select_animation']
        else:selected=owner['idle']
        owner['set_animation'](entity,selected,0)


def set_model_ex(entity,new,anim_flag,owner):
    if new is entity['model']:return
    oldtype=entity['modeldata']['type'];old=entity['model']
    copy_cached_defaults(old,new)
    snapshot=owner['snapshot_entity'](entity) if new['onmodelcopy'] else dict(exists=0)
    set_model(entity,new,anim_flag,owner)
    entity['modeldata']['type']=oldtype
    if new['model_flag']&4:owner['clear_scripts'](entity,0)
    owner['copy_scripts'](new,entity,0)
    owner['copy_combat_factors'](entity)
    set_colourmap(entity,entity['map'])
    if entity['onmodelcopy']:owner['onmodelcopy'](entity,snapshot)


def set_weapon(entity,number,anim_flag,owner):
    if entity is None:return
    data=entity['modeldata']
    if data['type']&1:
        owner['player_weapons'][entity['playerindex']]=number if data['weaploss'][0]==3 else owner['level_weapon']
    weapons=data['weapon']
    if weapons is not None and 0<number<=data['numweapons'] and weapons[number-1]:
        selected=weapons[number-1]
        if not 0<=selected<len(owner['models']):
            # The pinned function indexes model_cache with this nonzero value;
            # a declared NONE slot (-1) reaches undefined C memory, not Python
            # negative indexing or an implicit default-model alias.
            raise ValueError('SOURCE_WEAPON_CACHED_INDEX_UNDEFINED')
        set_model_ex(entity,owner['models'][selected],int(not anim_flag),owner)
    else:set_model_ex(entity,entity['defaultmodel'],1,owner)
