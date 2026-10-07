"""Explicit Q16.16 adaptation of the pinned check_range macro.

X truncates the target first. Z, altitude and base truncate the difference.
Integer arithmetic is extended here; native lowering must not wrap endpoints.
"""
def trunc_q16(value):
    return value // 65536 if value >= 0 else -((-value) // 65536)


def check(ranges, source, target, direction=1):
    if target is None: return False
    x = trunc_q16(target[0])*65536
    if direction == 1:
        if not source[0]+ranges[0]*65536 <= x <= source[0]+ranges[1]*65536: return False
    elif not source[0]-ranges[1]*65536 <= x <= source[0]-ranges[0]*65536: return False
    return all(ranges[2*i] <= trunc_q16(target[i]-source[i]) <= ranges[2*i+1] for i in range(1,4))
