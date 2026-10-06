"""Fold pre-first-use palette values into the existing VBlank restore.

Physical pixel indices and palette bank ownership stay fixed. Every pixel's
palette identity is independently replayed before the transformed schedule is
accepted. The initial restore size does not increase.
"""
from copy import deepcopy
import numpy as np


def fold(report,initial,indices):
    if indices.shape!=(224,256) or len(initial)!=236:raise ValueError('RASTER_FIRST_USE_DOMAIN')
    state=[v or 0 for v in initial];states=[]
    for row in report['trace']:
        if row['scanline']:
            for e in row['updates']:state[e['slot']-1]=e['color'] or 0
        states.append(list(state))
    if len(states)!=224:raise ValueError('RASTER_FIRST_USE_SCANLINES')
    first=[None]*236
    for y in range(224):
        for physical in np.unique(indices[y]):
            slot=int(physical)-4
            if 0<=slot<236 and first[slot] is None:first[slot]=y
    before=[v or 0 for v in initial]
    revised=[states[y][i] if y is not None else before[i] for i,y in enumerate(first)]
    resident=list(revised);output=deepcopy(report);removed=0
    for y,row in enumerate(output['trace']):
        values=[]
        if y:
            for e in row['updates']:
                slot=e['slot']-1
                color=revised[slot] if first[slot] is None or first[slot]>y else e['color'] or 0
                values.append(dict(slot=e['slot'],color=color))
        changed=any(resident[e['slot']-1]!=e['color'] for e in values)
        if not changed:
            if values:removed+=1
            row['updates']=[]
        else:
            row['updates']=values
            for e in values:resident[e['slot']-1]=e['color']
        for physical in np.unique(indices[y]):
            slot=int(physical)-4
            if 0<=slot<236 and resident[slot]!=states[y][slot]:
                raise ValueError('RASTER_FIRST_USE_PIXEL_IDENTITY:'+str(y)+':'+str(physical))
    return output,revised,dict(pixel_palette_identity_replayed=True,
        initial_words_changed=sum(a!=b for a,b in zip(before,revised)),raster_events_removed=removed,
        initial_restore_words_before=236,initial_restore_words_after=236)
