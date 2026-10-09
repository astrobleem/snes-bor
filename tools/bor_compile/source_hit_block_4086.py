"""Ordered passive, active and counter branch choice from do_attack.

Returns a branch requirement, not completed blocking or damage. Services must
use actual actor state, immutable source metadata and the source random stream.
"""
import struct


def f32(v):
    return struct.unpack('<f',struct.pack('<f',v))[0]


def choose(defender, attacker, attack, force, initial_blockthreshold, valid_block, inair, rand32):
    d=defender;guard=d['guardmax']==0 or d['guardmax']>0 and d['guardcurrent']>0
    behind=d['direction']==attacker['direction'] and d['blockback']<1
    if (not d['nopassiveblock'] and valid_block() and guard and
        not (d['link'] or inair() or d['frozen'] or behind or not d['idling'] and d['attacking']>=0) and
        f32(attack['no_block'])<=d['blockpower'] and
        (rand32() & (d['blockodds'] & 0xffffffff))==1 and
        (not d['thold'] or d['thold']>0 and d['thold']>force) and
        (not initial_blockthreshold or initial_blockthreshold>force)):
        return 'PASSIVE_BLOCK'
    if ((d['nopassiveblock'] or d['type']==1) and d['blocking'] and guard and
        not (behind or d['frozen']) and f32(attack['no_block'])<=d['blockpower'] and
        (not d['thold'] or d['thold']>0 and d['thold']>force) and
        (not d['blockthreshold'] or d['blockthreshold']>f32(force))):
        return 'ACTIVE_BLOCK'
    if d['counter_min']<=d['animpos']<=d['counter_max'] and not d['frozen']:
        return 'COUNTER'
    return 'DAMAGE'
