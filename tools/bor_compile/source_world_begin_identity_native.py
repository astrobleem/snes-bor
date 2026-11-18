"""Opt-in identity-order validation for the owned live-world fixture.

The original Begin prologue and guards remain in place. Only the fully guarded
128-slot identity case uses the shortcut; other cases enter the original code.
This module changes no default builder or runtime behavior by itself.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping


PARENT_ROM_SHA256 = 'ed76234ddd506334638bb6d0de8a8443d9ffe97c293d7e6ae6f771f91481b920'
HOOK_PC = 0x2F8237
HOOK_BYTES = bytes.fromhex('A9 00 00 8F F4 FA 7F')
RESUME_INITIALIZATION = HOOK_PC + len(HOOK_BYTES)
HELPER_START = 0x2B9F55
HELPER_LIMIT = 0x2C0000

EXPECTED = {
    'SourceWorldTick4086_Begin': 0x2F81EA,
    'SourceWorldTick4086_Poll': 0x2F82F5,
    'SourceWorldTick4086_Pending': 0x7FFAF0,
    'SourceWorldTick4086_Phase': 0x7FFAF2,
    'SourceWorldTick4086_Index': 0x7FFAF4,
    'SourceWorldTick4086_Slot': 0x7FFAF6,
    'SourceWorldTick4086_View': 0x7FFAF8,
    'SourceWorldTick4086_Side': 0x7FFAFA,
    'SourceWorldTick4086_Maximum': 0x7FFAFC,
    'SourceWorldTick4086_Fault': 0x7FFB08,
    'SourceWorldTick4086_Temporary': 0x7FFB0C,
    'SourceWorldTick4086_Seen': 0x7FFB10,
    'VmSourceWorld_Count': 0x7FF748,
    'SOURCE_WORLD_POOL': 0x414000,
    'SOURCE_TARGET_ORDER': 0x41F200,
    'SourceClock4086_Ready': 0x7FFA00,
    'WarmNative_CodeEnd': HELPER_START,
    'SourceWorldTick4086_Begin__validate': 0x2F825B,
    'SourceWorldTick4086_Branch_15': 0x2F82D4,
    'SourceWorldTick4086_ReadSlot': 0x2F8878,
    'VmSourceWorld_Time': 0x7FF752,
    'Vm_SourceTargetBitMask': 0x1CF44F,
}


class WorldBeginIdentityError(ValueError):
    pass


def _address(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFF:
        raise WorldBeginIdentityError('WORLD_BEGIN_SYMBOL_ADDRESS:'+name)
    return value


def checked_symbols(symbols: Mapping) -> dict:
    if not isinstance(symbols, Mapping):
        raise WorldBeginIdentityError('WORLD_BEGIN_SYMBOL_MAPPING')
    for name, expected in EXPECTED.items():
        if name not in symbols or _address(symbols[name], name) != expected:
            raise WorldBeginIdentityError('WORLD_BEGIN_SYMBOL_MISMATCH:'+name)
    result = dict(symbols)
    validate = result['SourceWorldTick4086_Begin__validate']
    after = result['SourceWorldTick4086_Branch_15']
    if not RESUME_INITIALIZATION < validate < after < EXPECTED['SourceWorldTick4086_Poll']:
        raise WorldBeginIdentityError('WORLD_BEGIN_TARGET_ORDER')
    return result


def lorom_offset(pc):
    return (pc >> 16) * 0x8000 + (pc & 0x7FFF)


def validate_parent(rom: bytes, symbols: Mapping) -> dict:
    symbols = checked_symbols(symbols)
    if hashlib.sha256(rom).hexdigest() != PARENT_ROM_SHA256:
        raise WorldBeginIdentityError('WORLD_BEGIN_PARENT_ROM')
    if rom[lorom_offset(HOOK_PC):lorom_offset(HOOK_PC)+7] != HOOK_BYTES:
        raise WorldBeginIdentityError('WORLD_BEGIN_HOOK_BYTES')
    if rom[lorom_offset(RESUME_INITIALIZATION):lorom_offset(RESUME_INITIALIZATION)+4] != bytes.fromhex('8F F0 FA 7F'):
        raise WorldBeginIdentityError('WORLD_BEGIN_RESUME_BYTES')
    at = lorom_offset(symbols['SourceWorldTick4086_Begin'])
    if rom[at:at+5] != bytes.fromhex('08 C2 38 DA 5A'):
        raise WorldBeginIdentityError('WORLD_BEGIN_PROLOGUE_BYTES')
    at = lorom_offset(symbols['SourceWorldTick4086_Begin__validate'])
    if rom[at:at+3] != b'\x20'+(symbols['SourceWorldTick4086_ReadSlot'] & 65535).to_bytes(2,'little'):
        raise WorldBeginIdentityError('WORLD_BEGIN_GENERIC_VALIDATE_BYTES')
    at = lorom_offset(symbols['SourceWorldTick4086_Branch_15'])
    if rom[at:at+4] != b'\xAF'+symbols['VmSourceWorld_Time'].to_bytes(3,'little'):
        raise WorldBeginIdentityError('WORLD_BEGIN_AFTER_VALIDATE_BYTES')
    at = lorom_offset(symbols['Vm_SourceTargetBitMask'])
    masks = b''.join((1 << i).to_bytes(2,'little') for i in range(16))
    if rom[at:at+32] != masks:
        raise WorldBeginIdentityError('WORLD_BEGIN_MASK_TABLE')
    return symbols


def emit(symbols: Mapping) -> str:
    symbols = checked_symbols(symbols)
    lines = []

    def put(text):
        lines.extend(text.strip().splitlines())

    def label(name):
        put('WorldBeginIdentity_'+name+':\n.a16\n.i16')

    def accept(op, name, fallback):
        put(f' {op} WorldBeginIdentity_{name}\n jmp WorldBeginIdentity_{fallback}')
        label(name)

    label('Entry')
    # These predicates are the exact stable branch selectors in the pinned
    # owned NMI/IRQ closure. The whole-ROM parent check binds that proof.
    for address, mask, expected, name in (
        (0x7FFB88, None, 0xB6D0, 'LiveOwner'),
        (0x7E8100, None, 0xB6D8, 'AudioOwner'),
        (0x7E8102, 0x00FF, 1, 'AudioEnabled'),
        (0x7FFA00, None, 0xB4C5, 'ClockOwner'),
    ):
        put(f' lda.l ${address:06X}')
        if mask is not None:
            put(f' and #${mask:04X}')
        put(f' cmp #${expected:04X}')
        accept('beq', name, 'OriginalInit')
    put(' lda.l $7E5003\n and #$0020')
    accept('bne', 'OwnedIrq', 'OriginalInit')
    put(' lda.l $7FF748\n cmp #128')
    accept('beq', 'Count128', 'OriginalInit')

    label('Initialize')
    put(' lda #0')
    for name in ('Index','Pending','Phase','Fault'):
        put(f' sta.l ${symbols["SourceWorldTick4086_"+name]:06X}')
    put(' ldx #0')
    label('ClearSeen')
    put(' sta.l $7FFB10,x\n inx\n inx\n cpx #16\n bcc WorldBeginIdentity_ClearSeen')

    # No scratch writes occur inside this scan. Any failed predicate can
    # therefore replay the original validator with its exact entry invariant.
    for i in range(128):
        put(f' lda.l ${0x41F200+2*i:06X}\n cmp #{i}')
        accept('beq', f'Order_{i}', 'OriginalValidate')
        put(f' lda.l ${0x414004+80*i:06X}\n cmp #2')
        accept('bcc', f'ExistsDomain_{i}', 'OriginalValidate')
        put(f' cmp #1\n bne WorldBeginIdentity_Next_{i}\n lda.l $7FFAFC\n cmp #{i+1}')
        accept('bcs', f'Next_{i}', 'OriginalValidate')

    label('Success')
    put(' lda #$FFFF\n ldx #0')
    label('FillSeen')
    put(' sta.l $7FFB10,x\n inx\n inx\n cpx #16\n bcc WorldBeginIdentity_FillSeen')
    for name, value in (('Slot',127),('Side',8128),('View',10160),
                        ('Temporary',0x8000),('Index',128)):
        put(f' lda #{value}\n sta.l ${symbols["SourceWorldTick4086_"+name]:06X}')
    put(' ldx #10160\n clv\n cmp #128')
    label('Complete')
    put(f' jml ${symbols["SourceWorldTick4086_Branch_15"]:06X}')

    label('OriginalValidate')
    # Recreate the register/flag state after the original eight-word clear.
    # Guarded IRQ/NMI handlers preserve this context, including V.
    put(' lda #0\n ldx #16\n cpx #16')
    put(f' jml ${symbols["SourceWorldTick4086_Begin__validate"]:06X}')
    label('OriginalInit')
    # The original hook is reached through CMP Level,#2 / BCC, so C was 0.
    put(' clc\n lda #0\n sta.l $7FFAF4')
    put(f' jml ${RESUME_INITIALIZATION:06X}')
    return '\n'.join(lines)+'\n'


def patch_rom(rom: bytes, symbols: Mapping, helper: bytes) -> tuple[bytes, dict]:
    validate_parent(rom, symbols)
    if not isinstance(helper, bytes) or not helper or HELPER_START+len(helper) > HELPER_LIMIT:
        raise WorldBeginIdentityError('WORLD_BEGIN_HELPER_EXTENT')
    start = lorom_offset(HELPER_START)
    if rom[start:start+len(helper)] != bytes(len(helper)):
        raise WorldBeginIdentityError('WORLD_BEGIN_HELPER_NOT_EMPTY')
    hook = b'\x5C'+HELPER_START.to_bytes(3,'little')+b'\xEA'*3
    result = bytearray(rom)
    at = lorom_offset(HOOK_PC)
    result[at:at+7] = hook
    result[start:start+len(helper)] = helper
    changed = [i for i,(a,b) in enumerate(zip(rom,result)) if a != b]
    if not changed or any(not (at <= i < at+7 or start <= i < start+len(helper)) for i in changed):
        raise WorldBeginIdentityError('WORLD_BEGIN_UNEXPECTED_DIFF')
    return bytes(result), dict(schema='BYOR_WORLD_BEGIN_IDENTITY_PATCH_V1',
        experimental_only=True,default_builder_changed=False,
        parent_rom_sha256=PARENT_ROM_SHA256,
        rom_sha256=hashlib.sha256(result).hexdigest(),
        hook_pc=HOOK_PC,old_hook_hex=HOOK_BYTES.hex(),new_hook_hex=hook.hex(),
        helper_pc=HELPER_START,helper_bytes=len(helper),helper_end=HELPER_START+len(helper),
        helper_sha256=hashlib.sha256(helper).hexdigest(),changed_bytes=len(changed),
        original_init_resume_pc=RESUME_INITIALIZATION,
        validation_resume_pc=symbols['SourceWorldTick4086_Begin__validate'],
        after_validation_pc=symbols['SourceWorldTick4086_Branch_15'],
        source_cadence_and_input_unchanged=True,added_stack_bytes=0,
        production_concurrency_claimed=False)
