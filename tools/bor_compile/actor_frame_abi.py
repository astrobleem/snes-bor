"""Compiler-owned exact frame ABI consumed by the isolated 65816 core.

This frame format is independent of the legacy 50-byte actor directory.
It does not install a role, infer attack eligibility, or implement damage/AI.
"""
import struct

from lowering_policy import Profile
from actor_media_abi import ACTOR_MEDIA_ADDRESS_BITS, check_actor_media_extent

FRAME_BYTES=32
MAX_BANK_BYTES=65536
MAX_FRAMES=MAX_BANK_BYTES//FRAME_BYTES
ATTACK_TYPES={'attack':0,'blast':1,'burn':2,'freeze':3,'shock':4}


def _signed(value, field):
    if not isinstance(value,int) or not -32768<=value<=32767:
        raise ValueError(f'ACTOR_FRAME_ABI_RANGE: {field}={value}, signed16 required')
    return value & 65535


def pack_source_frame(frame):
    binding=frame.get('source_binding')
    if binding is None: raise ValueError('ACTOR_FRAME_DIALECT_UNBOUND')
    delay=binding['delay_ticks']
    if not isinstance(delay,int) or not 0<=delay<=65535:
        raise ValueError(f'ACTOR_FRAME_DELAY_RANGE: {delay}, unsigned16 source ticks required')
    attack=frame.get('attack')
    force,drop,kind,box=0,0,0,[0]*4
    if attack is not None:
        if attack['kind'] not in ATTACK_TYPES:
            raise ValueError('ACTOR_ATTACK_TYPE_UNBOUND: '+attack['kind'])
        force,drop,kind=attack['force'],attack['drop'],ATTACK_TYPES[attack['kind']]
        box=binding['attack_corners']
    values=[delay,int(binding['vulnerable']),
            *[_signed(v,'body') for v in binding['body_corners']],
            _signed(force,'force'),_signed(drop,'drop'),kind,
            *[_signed(v,'attack') for v in box],0,0,0]
    if len(values)!=16: raise ValueError('ACTOR_FRAME_GEOMETRY_ARITY')
    return struct.pack('<16H',*values)


def pack_animation(actor, role, *, bank_offset=0, profile=Profile.SOURCE_EXACT):
    if Profile(profile)!=Profile.SOURCE_EXACT:
        raise ValueError('EXACT_FRAME_ABI_REQUIRES_EXPLICIT_SOURCE_EXACT_POLICY')
    if 'policy_contract' in actor or any('runtime_binding' in a for a in actor['animations']):
        raise ValueError('EXACT_FRAME_ABI_REJECTS_COMPAT_TARGET')
    if actor['dialect']!='historical-bor': raise ValueError('ACTOR_FRAME_DIALECT_UNBOUND')
    animation=next(a for a in actor['animations'] if a['role']==role)
    count=len(animation['frames'])
    if not 0<count<=MAX_FRAMES or not 0<=bank_offset<MAX_BANK_BYTES or bank_offset+count*FRAME_BYTES>MAX_BANK_BYTES:
        raise ValueError(f'ACTOR_FRAME_TABLE_BANK_CAPACITY: frames={count}, bytes={count*FRAME_BYTES}, offset={bank_offset}')
    return b''.join(pack_source_frame(frame) for frame in animation['frames'])
