"""Compile a horizontal math eligibility mask into two SNES color windows.

Only the color-window bits are owned. OBJ/BG window fields must be merged by
their presentation owner. These descriptors do not admit register timing.
"""


def evaluate(descriptor,x):
    selected=[]
    for index,(left,right)in enumerate(descriptor['bounds']):
        enable=0x20 if index==0 else 0x80
        invert=0x10 if index==0 else 0x40
        if descriptor['wobjsel_color_bits']&enable:
            selected.append((left<=x<=right)^bool(descriptor['wobjsel_color_bits']&invert))
    if not selected:return False
    if len(selected)==1:return selected[0]
    return any(selected)if descriptor['wobjlog_color_bits']==0 else all(selected)


def compile_mask(mask,fixed_positive_union=False):
    mask=tuple(mask)
    if len(mask)!=256 or any(v not in (0,1,False,True)for v in mask):raise ValueError('COLOR_WINDOW_MASK_DOMAIN')
    def runs(value):
        result=[];start=None
        for x,v in enumerate((*mask,not value)):
            if v==value and start is None:start=x
            elif v!=value and start is not None:result.append((start,x-1));start=None
        return result
    positive=runs(True);negative=runs(False)
    inverted=False
    if len(positive)<=2:intervals=positive
    elif fixed_positive_union:raise ValueError('COLOR_WINDOW_POSITIVE_UNION_NOT_REPRESENTABLE')
    elif len(negative)<=2:intervals=negative;inverted=True
    else:raise ValueError('COLOR_WINDOW_MASK_NOT_REPRESENTABLE')
    bits=0
    for index in range(len(intervals)):
        bits|=0x20 if index==0 else 0x80
        if inverted:bits|=0x10 if index==0 else 0x40
    descriptor=dict(bounds=[list(pair)for pair in intervals]+[[0,0]]*(2-len(intervals)),wobjsel_color_bits=bits,
                    wobjlog_color_bits=4 if inverted and len(intervals)==2 else 0,
                    cgwsel_clip_and_prevent_bits=0x10,math_enabled_inside_window=True,
                    register_timing_admitted=False)
    if fixed_positive_union:
        descriptor.update(bounds=[list(pair)for pair in intervals]+[[255,0]]*(2-len(intervals)),wobjsel_color_bits=0xa0,wobjlog_color_bits=0,fixed_positive_union=True)
    if any(evaluate(descriptor,x)!=bool(v)for x,v in enumerate(mask)):raise AssertionError('COLOR_WINDOW_MASK_REPLAY')
    return descriptor


def compile_sparse_mask(eligibility,fixed_positive_union=False):
    """Fill unconstrained gaps while preserving every observed source pixel."""
    coordinates=sorted(eligibility)
    if not coordinates or any(not isinstance(x,int)or not 0<=x<256 for x in coordinates):raise ValueError('COLOR_WINDOW_COORDINATE_DOMAIN')
    mask=[];index=0
    for x in range(256):
        while index+1<len(coordinates)and coordinates[index+1]<=x:index+=1
        mask.append(eligibility[coordinates[index]])
    result=compile_mask(mask,fixed_positive_union)
    if any(evaluate(result,x)!=bool(v)for x,v in eligibility.items()):raise AssertionError('COLOR_WINDOW_SPARSE_REPLAY')
    return result
