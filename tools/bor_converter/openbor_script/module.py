"""Pack a Compiler Module (compiler.py) into the FORMAT.md revision-1 binary.

All multibyte fields little-endian, no host pointers, no struct dumps --
FORMAT.md's own normalization rules. CRC32 is the zlib/ISO-HDLC variant
(poly $EDB88320 reflected, init/final $FFFFFFFF), matching
vm_load.pasm's table-driven Vm_ValidateHeader exactly (same table,
tools/verify/vm_fixtures's committed Vm_Crc32Table source).
"""
import struct
import zlib

from .natives import NATIVES, BY_NAME as NATIVE_BY_NAME
from .compiler import VT_EMPTY

MAGIC = b'B48S'
FORMAT_VERSION = 1
OPCODE_ABI = 0x30           # 48 -- OPCODE_END sentinel
NUMERIC_PROFILE_Q16 = 0
HEADER_SIZE = 0x40


class ModuleLimitError(Exception):
    pass


def pack_module(m, vm_instr_max=4096, vm_slot_max=1024, native_arities=None, vm_code_max=17760):
    """m: compiler.Module. Enforces the engine's real bounds (vm_consts.pasm's
    VM_INSTR_MAX/VM_SLOT_MAX), not FORMAT.md's more permissive 0..8192/range --
    advisor note: "enforce the engine's numbers in the exporter so an
    over-large script fails host-side with a useful message instead of as
    VMERR_BAD_MODULE."
    """
    if len(m.instructions) > vm_instr_max:
        raise ModuleLimitError(f'{len(m.instructions)} instructions exceeds VM_INSTR_MAX={vm_instr_max}')
    if len(m.slots) > vm_slot_max:
        raise ModuleLimitError(f'{len(m.slots)} slots exceeds VM_SLOT_MAX={vm_slot_max}')
    for ins in m.instructions:
        if ins.op >= OPCODE_ABI:
            raise ModuleLimitError(f'instruction opcode {ins.op} >= {OPCODE_ABI} (OPCODE_END)')
        if ins.op == 7:  # FIELD -- reserved/fault, reject per FORMAT.md rule 7
            raise ModuleLimitError('FIELD (opcode 7) is not a valid compiler output -- reject')

    instr_bytes = b''.join(
        struct.pack('<BBHHH', ins.op & 0xFF, ins.flags & 0xFF, ins.a, ins.b, ins.c)
        for ins in m.instructions
    )

    slot_bytes = b''.join(
        struct.pack('<BBHI', vtype & 0xFF, flags & 0xFF, aux & 0xFFFF, value & 0xFFFFFFFF)
        for vtype, flags, aux, value in m.slots
    )

    arg_slot_flat = []
    callsite_bytes_parts = []
    for cs in m.callsites:
        callsite_bytes_parts.append(struct.pack(
            '<BBHHHHH', cs.target_kind & 0xFF, cs.argc & 0xFF, cs.target_id & 0xFFFF,
            cs.result_slot & 0xFFFF, cs.arg_list_index & 0xFFFF, cs.flags & 0xFFFF,
            cs.debug_name_id & 0xFFFF))
        arg_slot_flat.extend(cs.arg_slot_ids)
    callsite_bytes = b''.join(callsite_bytes_parts)
    arg_slot_bytes = b''.join(struct.pack('<H', s & 0xFFFF) for s in arg_slot_flat)

    string_count = len(m.strings)
    offsets = [0]
    for s in m.strings:
        offsets.append(offsets[-1] + len(s))
    strings_bytes = struct.pack('<H', string_count) + b''.join(
        struct.pack('<H', o) for o in offsets) + b''.join(m.strings)

    natives_sorted = sorted(m.natives_used)
    arities = NATIVES_ARGC if native_arities is None else native_arities
    missing = set(natives_sorted) - set(arities)
    if missing:
        raise ModuleLimitError(f'undeclared native IDs: {sorted(missing)}')
    native_id_by_stable = {sid: sid for sid in natives_sorted}
    native_bytes = b''.join(
        struct.pack('<HHH', sid & 0xFFFF, argc & 0xFFFF, argc & 0xFFFF)
        for sid, argc in ((sid, arities[sid]) for sid in natives_sorted)
    )

    sections = [
        ('instructions', instr_bytes),
        ('initial_slots', slot_bytes),
        ('callsites', callsite_bytes),
        ('arg_slot_ids', arg_slot_bytes),
        ('strings', strings_bytes),
        ('natives', native_bytes),
    ]
    offset = HEADER_SIZE
    section_offsets = {}
    body = b''
    for name, data in sections:
        section_offsets[name] = offset
        body += data
        offset += len(data)

    module_size = HEADER_SIZE + len(body)
    if module_size > vm_code_max:
        raise ModuleLimitError(f'{module_size} bytes exceeds VM_CODE_MAX={vm_code_max}')

    header_no_crc = struct.pack(
        '<4sBBBBHHHHHHHH',
        MAGIC, FORMAT_VERSION, OPCODE_ABI, NUMERIC_PROFILE_Q16, 0,
        len(m.instructions), len(m.slots), len(m.callsites), len(natives_sorted),
        m.entry_main, 0xFFFF, 0xFFFF, 0,
    ) + struct.pack(
        '<IIIIIIII',
        section_offsets['instructions'], section_offsets['initial_slots'],
        section_offsets['callsites'], section_offsets['arg_slot_ids'],
        section_offsets['strings'], section_offsets['natives'],
        0, module_size,
    )
    assert len(header_no_crc) == HEADER_SIZE - 8, len(header_no_crc)  # crc32 + reserved not yet appended

    crc = zlib.crc32(body) & 0xFFFFFFFF
    header = header_no_crc + struct.pack('<II', crc, 0)
    assert len(header) == HEADER_SIZE, len(header)

    return header + body


NATIVES_ARGC = {sid: argc for sid, _name, argc in NATIVES}
