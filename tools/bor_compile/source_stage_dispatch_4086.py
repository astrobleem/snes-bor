"""Closed source queue branch of update_scroller, before camera movement.

The spawn callback must execute the real constructor/properties and may change
the entity pool. Waiting holds camera advance; it does not break this loop.
"""


def count(entities, mask):
    return sum(bool(e['exists'] and e['type'] & mask) for e in entities)


def dispatch(state, records, entities, spawn):
    trace=[]
    if state['time'] < state['advancetime'] or state['freezeall']:
        return trace
    state['advancetime']=state['time']
    if state['completed']:
        return trace
    live_player=any(e is not None and not e['dead'] for e in state['players'])
    if state['index']>=len(records) and not count(entities,2) and live_player:
        if not count(entities,256) and (state['leveltype']==0 or state['leveltype']==1 and not count(entities,4|8)):
            state['completed']=1
    elif count(entities,2)<state['groupmin']:
        while count(entities,2)<state['groupmax'] and state['index']<len(records) and state['pos']>=records[state['index']]['at']:
            row=records[state['index']]
            if row['kind']=='wait':
                state['waiting']=1;state['go_time']=0
            elif row['kind']=='group':
                state['groupmin'],state['groupmax']=row['group']
            elif row['kind'] in ('spawn','empty'):
                spawn(row,entities)
            else:
                raise ValueError('STAGE_DISPATCH_RECORD_SERVICE_REQUIRED')
            trace.append(state['index']);state['index']+=1
    return trace
