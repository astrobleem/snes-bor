"""Pinned unbounded-animation target selection over authoritative world state.

The one-argument script API uses anim=-1 and detect adjustment zero. It selects
in pool order with facing and vulnerable/invincible preference, not simply the
nearest player. Positions remain the explicit Q16.16 target adaptation. This
reference and metadata ABI do not grant a world lease or implement AI.
"""
from dataclasses import dataclass
import struct

BASE = 0x41e800
STRIDE = 20
CAPACITY = 128
FIRST_UNUSED = BASE + STRIDE * CAPACITY
ORDER_BASE = FIRST_UNUSED
FIRST_UNUSED = ORDER_BASE + 2 * CAPACITY
ORDER_READY = 0xb4d3
READY = 0xb4d2
ADDRESS = 0x7ffa88
SCRATCH_END = 0x7ffae0


@dataclass(frozen=True)
class Target:
    token: int
    x: int = 0
    z: int = 0
    direction: int = 1
    alive: bool = True
    type: int = 0
    hostile: int = 65535
    dead: bool = False
    invincible: int = 0
    vulnerable: bool = True
    detect: int = 0
    hide: int = 0


def metadata(row):
    if not 0 <= row.type <= 65535 or not 0 <= row.hostile <= 65535:
        raise ValueError('SOURCE_TARGET_TYPE_MASK_DOMAIN')
    if not 0 <= row.invincible <= 65535:
        raise ValueError('SOURCE_TARGET_INVINCIBLE_DOMAIN')
    if any(not -2147483648 <= n <= 2147483647 for n in (row.detect, row.hide, row.x, row.z)):
        raise ValueError('SOURCE_TARGET_SIGNED32_DOMAIN')
    return struct.pack('<6Hii', row.type, row.hostile, int(row.dead), row.invincible,
                       int(row.vulnerable), 0, row.detect, row.hide)


def descriptor(count, time):
    if not 1 <= count <= CAPACITY or not 0 <= time <= 0xffffffff:
        raise ValueError('SOURCE_TARGET_DESCRIPTOR_DOMAIN')
    return struct.pack('<HHI', READY, count, time)


def order_table(indices):
    if not 1 <= len(indices) <= CAPACITY or sorted(indices) != list(range(len(indices))):
        raise ValueError('SOURCE_TARGET_ORDER_PERMUTATION')
    return struct.pack('<' + 'H' * len(indices), *indices)


def find(rows, token, order=None, scan_count=None):
    if not token: return None
    if (not 1 <= len(rows) <= CAPACITY or len({r.token for r in rows}) != len(rows)
            or any(not 0 < r.token <= 0xffffffff for r in rows)):
        raise ValueError('SOURCE_TARGET_POOL_DOMAIN')
    for row in rows: metadata(row)
    order = list(range(len(rows))) if order is None else order
    if len(order) != len(rows): raise ValueError('SOURCE_TARGET_ORDER_COUNT')
    order_table(order)
    scan_count = len(rows) if scan_count is None else scan_count
    if not 0 <= scan_count <= len(rows): raise ValueError('SOURCE_TARGET_SCAN_COUNT')
    self = next((r for r in rows if r.token == token and r.alive), None)
    if self is None: raise ValueError('SOURCE_TARGET_STALE_SELF')
    selected = None; distance = 0
    for index in order[:scan_count]:
        row = rows[index]
        diff = abs(row.x - self.x) + abs(row.z - self.z)
        if not (row.alive and row.token != token and row.type & self.hostile and not row.dead
                and diff <= 9999 * 65536 and row.hide <= self.detect):
            continue
        if (selected is None or not selected.vulnerable or selected.invincible == 1
                or ((self.x < row.x) == (self.direction == 1) and diff < distance)):
            selected = row; distance = diff
    return selected.token if selected else None
