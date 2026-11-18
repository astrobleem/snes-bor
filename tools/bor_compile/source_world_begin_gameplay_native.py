"""Gameplay-only wrapper for the frozen, rejected V28 identity experiment.

V28 changed selector timing and reached preview retirement with clock credits
still due. This experiment leaves the retirement/clock rules intact and uses
the shortcut only after the checked gameplay handoff. Other states replay the
original validator. It changes no default builder.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import source_world_begin_identity_native as base
from source_world_begin_identity_native import (WorldBeginIdentityError,
    PARENT_ROM_SHA256, HOOK_PC, HOOK_BYTES, RESUME_INITIALIZATION,
    HELPER_START, HELPER_LIMIT, lorom_offset)

BASE_EMITTER_SHA256 = '4ff9c966cc24023ad8559edf1ca531b83d2061648a3b1852ffe9e2b6655da6d9'
MOTION_READY = 0x7E7900
MOTION_STATE = 0x7E7902
MOTION_MAGIC = 0xB6E4
GAMEPLAY_STATE = 2


def checked_symbols(symbols):
    result = base.checked_symbols(symbols)
    for name,value in (('Motion_Guard141',0x2B9078),
            ('LiveRetirement_BirthMetadata',0x2B969D)):
        if type(result.get(name)) is not int or result[name] != value:
            raise WorldBeginIdentityError('WORLD_BEGIN_GAMEPLAY_SYMBOL:'+name)
    if hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest() != BASE_EMITTER_SHA256:
        raise WorldBeginIdentityError('WORLD_BEGIN_GAMEPLAY_BASE_EMITTER')
    return result


def validate_parent(rom,symbols):
    symbols = checked_symbols(symbols)
    base.validate_parent(rom,symbols)
    # State 2 is published only after the checked birth-metadata call returns
    # without carry. Bind the exact branch and state store in this parent.
    at = lorom_offset(symbols['Motion_Guard141'])
    expected = bytes.fromhex('229D962B90034C9490A902008F02797E')
    if rom[at-9:at+7] != expected:
        raise WorldBeginIdentityError('WORLD_BEGIN_GAMEPLAY_HANDOFF_ANCHOR')
    return symbols


def emit(symbols):
    symbols = checked_symbols(symbols)
    text = base.emit(symbols)
    entry = 'WorldBeginIdentity_Entry:\n.a16\n.i16\n'
    assert text.count(entry) == 1
    # This is only a cheap negative prefilter. Eligibility is checked again
    # after all five original owned-ISR predicates; it grants no ownership.
    prefilter = ''' lda.l $7E7902
 cmp #2
 beq WorldBeginIdentity_GameplayHint
 jmp WorldBeginIdentity_OriginalInit
WorldBeginIdentity_GameplayHint:
.a16
.i16
'''
    text = text.replace(entry,entry+prefilter)
    initialize = 'WorldBeginIdentity_Initialize:\n.a16\n.i16\n'
    assert text.count(initialize) == 1
    guard = ''' lda.l $7E7900
 cmp #$B6E4
 beq WorldBeginIdentity_GameplayOwner
 jmp WorldBeginIdentity_OriginalInit
WorldBeginIdentity_GameplayOwner:
.a16
.i16
 lda.l $7E7902
 cmp #2
 beq WorldBeginIdentity_GameplayActive
 jmp WorldBeginIdentity_OriginalInit
WorldBeginIdentity_GameplayActive:
.a16
.i16
'''
    return text.replace(initialize,guard+initialize)


def patch_rom(rom,symbols,helper):
    validate_parent(rom,symbols)
    result,detail = base.patch_rom(rom,symbols,helper)
    detail.update(schema='BYOR_WORLD_BEGIN_GAMEPLAY_PATCH_V1',
        gameplay_handoff_magic=MOTION_MAGIC,gameplay_handoff_ready_address=MOTION_READY,
        gameplay_handoff_state_address=MOTION_STATE,gameplay_handoff_state=GAMEPLAY_STATE,
        selector_and_birth_states_use_original_validator=True,
        negative_prefilter_grants_no_ownership=True,
        all_five_original_owned_guards_retained=True,
        clock_credit_and_retirement_guards_unchanged=True,
        frozen_v28_emitter_sha256=BASE_EMITTER_SHA256)
    return result,detail
