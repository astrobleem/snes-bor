"""Pinned spawn allocation/construction policy; yielded services are unbound.

Model copies remain shallow. A constructor must finish all services in order
before exposing its result; this reference does not admit a foreign profile.
"""
from enum import IntEnum

class Service(IntEnum):
    ALLOCATE=1
    KILL=2
    VARLIST_CLEANUP=3
    COPY_FACTORS=4
    CLEAR_SCRIPTS=5
    FREE_WAYPOINTS=6
    COPY_SCRIPTS=7
    COLOURMAP=8
    DEFAULT_INIT=9

def spawn(owner,x,z,a,direction,name,index,model=None):
    if model is None:
        if index>=0:model=owner['models'][index]
        elif name is not None:model=owner['find_model'](name)
    if model is None:return None
    if owner['count']>=len(owner['entities']):
        allocated=yield Service.ALLOCATE,None,None
        if not allocated:return None
    for e in owner['entities']:
        if e['exists'] and not (owner['count']>=owner['override'] and e['modeldata']['priority']<0 and e['modeldata']['priority']<=model['priority']):continue
        if e['exists']:yield Service.KILL,e,None
        saved={k:e[k] for k in ('sortid','defense','offense_factors','varlist','scripts')}
        yield Service.VARLIST_CLEANUP,e,saved['varlist']
        yield Service.COPY_FACTORS,e,model
        yield Service.CLEAR_SCRIPTS,e,1
        if e.get('waypoints') is not None:yield Service.FREE_WAYPOINTS,e,e['waypoints']
        e.clear() # C memset: persistent resource identities restored separately.
        e.update(exists=1,drawmethod=dict(owner['plainmethod']),modeldata=dict(model),model=model,defaultmodel=model,scripts=saved['scripts'])
        e['drawmethod']['flag']=0
        owner['count']+=1
        yield Service.COPY_SCRIPTS,e,(model,1)
        owner['maximum']=max(owner['maximum'],owner['count'])
        data=e['modeldata']
        e.update(timestamp=owner['time'],health=data['health'],mp=data['mp'],knockdowncount=data['knockdowncount'],x=x,z=z,a=a,direction=direction,nextthink=(owner['time']+1)&0xffffffff,nextmove=(owner['time']+1)&0xffffffff,speedmul=1)
        yield Service.COLOURMAP,e,0
        e['lifespan']=model['lifespan']
        data=e['modeldata']
        if data['type']&1 and ((owner['level'] is not None and owner['level']['nohit']) or owner['saved_mode']):
            e['modeldata']['hostile']&=~1;e['modeldata']['candamage']&=~1
        e['playerindex']=owner['spawnplayer'] if data['type']&1 else 0
        if data['type']&128:owner['textbox']=e
        e['name']=data['name'][:owner['name_limit']]
        e.update({k:saved[k] for k in ('sortid','defense','offense_factors','varlist')})
        yield Service.DEFAULT_INIT,e,None
        return e
    return None
