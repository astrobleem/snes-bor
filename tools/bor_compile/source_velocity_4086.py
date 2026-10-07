"""Pinned update_ents movement accumulation, plus explicit native Q16 policy.

No position integration, collision, AI or world traversal is implemented here.
The authority compiler keeps intermediate products in x87 excess precision.
Native arithmetic is an ACCEPTED_COMPAT policy, not a claim of binary32
identity. Overflow is rejected before either axis writes.
"""
import struct


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def source(movex, movez, vx, vz, speedmul, *, excess_precision=True):
    values = [f32(v) for v in (movex, movez, vx, vz, speedmul)]
    x, z, vx, vz, speed = values
    product = (lambda v: v) if excess_precision else f32
    return f32(x + product(vx * speed) * 0.5), f32(z + product(vz * speed) * 0.5)


def trunc_div(value, divisor):
    return (-1 if value < 0 else 1) * (abs(value) // divisor)


def native(movex, movez, vx, vz, speedmul):
    values = (movex, movez, vx, vz, speedmul)
    if any(type(v) is not int or not -0x80000000 <= v <= 0x7fffffff for v in values):
        raise ValueError('SOURCE_VELOCITY_Q16_DOMAIN')
    # One full 64-bit product per axis, then scale by 2^17. Do not truncate
    # the product to Q16 first: that creates a second rounding operation.
    result = (movex + trunc_div(vx * speedmul, 131072),
              movez + trunc_div(vz * speedmul, 131072))
    if any(not -0x80000000 <= v <= 0x7fffffff for v in result):
        raise ValueError('SOURCE_VELOCITY_ACCUMULATOR_OVERFLOW')
    return result
