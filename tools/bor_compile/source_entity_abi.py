"""Generic source-world read view for the typed native script boundary.

Positions use the existing explicit ACCEPTED_COMPAT_Q16_16 policy. This view
does not allocate entities or alias original-BOR character indices. The world
owner publishes one-bank WRAM records while a script holds its context lease.
"""
import struct

MAGIC = 0xB48B  # V2: distinct from the former seven-property B48D view
STRIDE = 80
MAX_RECORDS = 512
# Build 4086 openborscript.c, af23dc9: property return types and entity fields.
PROPERTIES = [('a', 2), ('animationid', 1), ('direction', 1), ('health', 1),
              ('playerindex', 1), ('x', 2), ('z', 2), ('maxhealth', 1)]
ALIASES = {'y': 'a', 'animnum': 'animationid'}


def record(token, values, *, alive=True):
    if not 0 < token <= 0xffffffff:
        raise ValueError('ENTITY_TOKEN_INVALID')
    if set(values) != {name for name, _ in PROPERTIES}:
        raise ValueError('ENTITY_VIEW_PROPERTIES_INCOMPLETE')
    payload = bytearray(struct.pack('<IHH', token, int(alive), 0))
    for name, kind in PROPERTIES:
        value = values[name]
        if not isinstance(value, int) or not -0x80000000 <= value <= 0x7fffffff:
            raise ValueError('ENTITY_VIEW_SIGNED32_REQUIRED:' + name)
        payload.extend(struct.pack('<BBHI', kind, 0, 0, value & 0xffffffff))
    payload.extend(bytes(STRIDE-len(payload)))
    return bytes(payload)


def view(address, records):
    if address >> 16 not in (0x7e, 0x7f):
        raise ValueError('ENTITY_VIEW_WRAM_REQUIRED')
    if not 0 < len(records) <= MAX_RECORDS:
        raise ValueError('ENTITY_VIEW_COUNT_INVALID')
    if (address & 0xffff) + len(records) * STRIDE > 0xffff:
        raise ValueError('ENTITY_VIEW_BANK_SPILL')
    tokens = []
    for item in records:
        if len(item) != STRIDE:
            raise ValueError('ENTITY_VIEW_RECORD_SIZE')
        token, alive, reserved = struct.unpack_from('<IHH', item)
        if not token or alive not in (0, 1) or reserved:
            raise ValueError('ENTITY_VIEW_HEADER_INVALID')
        if item[72:] != bytes(8):
            raise ValueError('ENTITY_VIEW_RESERVED_TAIL_INVALID')
        for i, (_, kind) in enumerate(PROPERTIES):
            if item[8 + i*8:12 + i*8] != bytes((kind, 0, 0, 0)):
                raise ValueError('ENTITY_VIEW_VARIANT_INVALID')
        tokens.append(token)
    if len(tokens) != len(set(tokens)):
        raise ValueError('ENTITY_VIEW_DUPLICATE_TOKEN')
    descriptor = struct.pack('<HBxHH', address & 0xffff, address >> 16,
                             len(records), MAGIC)
    return descriptor, b''.join(records)


def get_property(records, token, name):
    """Host oracle for the exact eight-byte read-view result."""
    if token is None or token == 0:
        return bytes(8)
    name = ALIASES.get(name.lower(), name.lower())
    index = next((i for i, (key, _) in enumerate(PROPERTIES) if key == name), None)
    if index is None:
        raise ValueError('ENTITY_PROPERTY_UNBOUND:' + name)
    for item in records:
        if struct.unpack_from('<I', item)[0] == token and struct.unpack_from('<H', item, 4)[0] == 1:
            return item[8 + index*8:16 + index*8]
    raise ValueError('ENTITY_HANDLE_STALE_OR_UNKNOWN')
