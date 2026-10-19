"""Bounded phase-11 grounded POST_UPDATE provider for the pinned 4086 world.

The host oracle describes the admitted inactive-air branch.  The emitted
provider composes the real empty-geometry adjust-base operator, a private clone
of the checked inactive-air gravity operator, and the real check_move operator.
The gravity clone differs only in admitting a zero `no_adjust_base` model flag
after the actual adjust-base operator has completed for the selected slot.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Mapping


ROOT = Path(__file__).resolve().parents[2]
U32 = 0xFFFF_FFFF


class GroundPostFault(ValueError):
    """The source frame is outside the checked native subset."""


@dataclass(frozen=True)
class GroundPostResult:
    status: str  # complete | pending | fault
    writes: tuple[str, ...] = ()
    reason: str = ""


def ground_post(*, ready: bool, state: int, phase: int, pending: int,
                fault: int, world_time: int, tick_time: int, slot: int,
                slot_live: bool, binding_ent: int, falling: int,
                velocity_y: int, altitude: int, base: int, toss_time: int,
                update_mark: int, frozen: bool, empty_geometry: bool,
                no_adjust_base: int) -> GroundPostResult:
    """Source-derived inactive-air oracle, including mark/freeze/toss rules."""
    for name, value in (("world_time", world_time), ("tick_time", tick_time),
                        ("toss_time", toss_time)):
        if type(value) is not int or not 0 <= value <= U32:
            raise GroundPostFault("GROUND_POST_U32_DOMAIN:" + name)
    if not ready or state != 2 or phase != 11 or pending != 1 or fault != 0:
        raise GroundPostFault("GROUND_POST_PHASE_GUARD")
    if world_time != tick_time or not 0 <= slot < 128 or not slot_live:
        raise GroundPostFault("GROUND_POST_WORLD_IDENTITY")
    if binding_ent != 0:
        return GroundPostResult("pending", reason="BINDING_ADJUST_PROVIDER_REQUIRED")
    if not empty_geometry:
        raise GroundPostFault("GROUND_POST_GEOMETRY_UNADMITTED")
    if type(no_adjust_base) is not int or not -(1 << 31) <= no_adjust_base < (1 << 31):
        raise GroundPostFault("GROUND_POST_ADJUST_BASE_FLAG")
    # Source `check_gravity` enters its active-air body only when not frozen,
    # the actor is airborne, and toss_time is due. A future toss still follows
    # the inactive mark path; freeze suppresses movement but still marks bit 3.
    active_air = bool(falling or velocity_y or altitude != base)
    if not frozen and active_air and toss_time <= world_time:
        return GroundPostResult("pending", reason="ACTIVE_AIR_OR_LANDING")
    mark = update_mark
    toss = toss_time
    if not frozen and toss <= world_time:
        toss = (world_time + 1) & U32
    if not mark & 8:
        mark |= 8
    writes = []
    if toss != toss_time:
        writes.append("toss_time")
    if mark != update_mark:
        writes.append("update_mark.bit3")
    return GroundPostResult("complete", tuple(writes))


_SYMBOLS = (
    "SourceWorldTick4086_Ready", "SourceWorldTick4086_State",
    "SourceWorldTick4086_Phase", "SourceWorldTick4086_Pending",
    "SourceWorldTick4086_Fault", "SourceWorldTick4086_Slot",
    "SourceWorldTick4086_TimeLo", "VmSourceWorld_Ready",
    "VmSourceWorld_Time", "VmSourceWorld_Count", "VmSourceWorld_PoolBase",
    "VmSourceWorld_SideBase", "SourceSelf4086_Ready",
    "SourceSelf4086_Active", "SourceSelf4086_Fault",
    "SourceSelf4086_GlobalLow", "SourceSelf4086_GlobalHigh",
    "SourceEmptyInitEnvironment4086_Models", "SourceAdjustBaseEmpty4086_RunPost",
    "SourceAdjustBaseEmpty4086_Status",
    "SourceCheckMove4086_Execute", "SourceFreeze4086_Query",
    "SourceFreeze4086_Ready",
    "SourceEmptyInitEnvironment4086_Query", "SourceModelEntityCopy4086_Ready",
    "SourceModelEntityCopy4086_Entities", "SourceAnimationPhysics4086_Ready",
    "SourceAnimationPhysics4086_Query", "SourceToss4086_Ready",
    "SourcePhysicsState4086_Ready", "SourceLifecycle4086_Ready",
    "SourceUpdateFrame4086_Ready", "SourcePostStationary4086_Ready",
    "SourcePostStationary4086_Status", "SourcePostStationary4086_Slot",
    "SourceGravityIdle4086_Ready", "SourceGravityIdle4086_Status",
    "SourceCheckMove4086_Status", "SOURCE_WORLD_POOL", "SOURCE_WORLD_SIDES",
    "SOURCE_WORLD_FREEZE", "SOURCE_WORLD_TOSS_TIMES", "SOURCE_ENTITY_PHYSICS",
)


def _address(symbols: Mapping[str, int], name: str) -> str:
    value = symbols[name]
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFF:
        raise ValueError("GROUND_POST_SYMBOL_" + name)
    return f"${value:06X}"


def emit(symbols: Mapping[str, int], binding_base: int = 0x7E7A00,
         check_move_label: str = "SourceCheckMove4086_Execute") -> str:
    """Emit the phase-11 grounded provider and its source-derived gravity clone.

    ``binding_base`` is the caller-owned 128x4-byte canonical binding-token
    extension in retired scene/video staging. Birth initializes the selected
    token to NULL before exists publication; binding writes must update this
    row and revoke this provider's closed profile.
    """
    if not isinstance(symbols, Mapping):
        raise ValueError("GROUND_POST_SYMBOLS")
    required = _SYMBOLS
    for name in required:
        if name not in symbols:
            raise ValueError("GROUND_POST_SYMBOL_" + name)
        _address(symbols, name)
    if type(binding_base) is not int or not 0 <= binding_base <= 0xFFFFFF - 128 * 4:
        raise ValueError("GROUND_POST_BINDING_BASE")
    if not isinstance(check_move_label, str) or not re.fullmatch(r"[A-Za-z_]\w*", check_move_label):
        raise ValueError("GROUND_POST_CHECK_MOVE_LABEL")

    # The source operator must be cloned, not reimplemented. Prefix its local
    # labels and state aliases; patch only the core no_adjust_base test to
    # accept zero after validating that AdjustBaseEmpty completed this slot.
    gravity_path = ROOT / "src/core/vm/vm_source_gravity_idle.pasm"
    gravity = gravity_path.read_text(encoding="utf-8")
    old = """ lda.l $40C026,x
 bmi SourceGravityIdle4086_RejectCore
 ora.l $40C024,x
 bne SourceGravityIdle4086_StickyBase
SourceGravityIdle4086_RejectCore:
.a16
.i16
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_StickyBase:
"""
    new = """ ; The owning provider has just run actual AdjustBaseEmpty for
 ; this slot and frame. Preserve the original positive sticky-base admission;
 ; the checked grounded profile also admits He-Man's authored zero flag.
 lda.l SourceAdjustBaseEmpty4086_Status
 cmp #2
 beq LiveGroundPost_Gravity_Adjusted
 jmp SourceGravityIdle4086_Bad
LiveGroundPost_Gravity_Adjusted:
 lda.l $40C026,x
 bmi SourceGravityIdle4086_StickyBase
 ora.l $40C024,x
 bne SourceGravityIdle4086_StickyBase
 bra SourceGravityIdle4086_StickyBase
SourceGravityIdle4086_StickyBase:
"""
    if old not in gravity:
        raise ValueError("GROUND_POST_GRAVITY_SOURCE_ANCHOR")
    gravity = gravity.replace(old, new, 1)
    gravity = gravity.replace("SourceGravityIdle4086_", "LiveGroundPost_Gravity_")
    # The replacement text above was authored before prefixing.
    gravity = gravity.replace("SourceAdjustBaseEmpty4086_Status", "SourceAdjustBaseEmpty4086_Status")

    # Reuse the accepted stationary-post wrapper sequence so it binds/restores
    # source self and publishes the B61A ready status only after all operators.
    post = (ROOT / "src/core/vm/vm_source_post_stationary.pasm").read_text(encoding="utf-8")
    run = post[post.index("SourcePostStationary4086_Execute:"):post.index("; A=service to issue")]
    run = run.replace("SourcePostStationary4086_", "LiveGroundPost_")
    run = run.replace("SourceGravityIdle4086_", "LiveGroundPost_Gravity_")
    run = run.replace("SourceCheckMove4086_Execute", check_move_label)
    run = run.replace("SourceAdjustBaseEmpty4086_", "SourceAdjustBaseEmpty4086_")
    phase_anchor = """LiveGroundPost_PhaseGood:
.a16
.i16
 lda.l SourceSelf4086_Ready
"""
    phase_guard = """LiveGroundPost_PhaseGood:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq LiveGroundPost_TickReady
 jmp LiveGroundPost_Bad
LiveGroundPost_TickReady:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq LiveGroundPost_TickPending
 jmp LiveGroundPost_Bad
LiveGroundPost_TickPending:
.a16
.i16
 lda.l SourceWorldTick4086_Fault
 beq LiveGroundPost_TickFaultClear
 jmp LiveGroundPost_Bad
LiveGroundPost_TickFaultClear:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 beq LiveGroundPost_TickTimeLo
 jmp LiveGroundPost_Bad
LiveGroundPost_TickTimeLo:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo+2
 cmp.l VmSourceWorld_Time+2
 beq LiveGroundPost_TickTimeGood
 jmp LiveGroundPost_Bad
LiveGroundPost_TickTimeGood:
.a16
.i16
 lda.l SourceSelf4086_Ready
"""
    if phase_anchor not in run:
        raise ValueError("GROUND_POST_PHASE_GUARD_ANCHOR")
    run = run.replace(phase_anchor, phase_guard, 1)
    # Before mutating state, bind the selected source token and require the
    # actual canonical binding.ent pointer to be NULL.
    needle = """LiveGroundPost_Bind:
.a16
.i16
 lda.l LiveGroundPost_Gravity_Status
"""
    insert = """LiveGroundPost_Bind:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 tax
 lda.l {binding_base:06X},x
 ora.l {binding_base + 2:06X},x
 beq LiveGroundPost_BindingNull
 lda #1
 ply
 plx
 plp
 clc
 rtl
LiveGroundPost_BindingNull:
 lda.l LiveGroundPost_Gravity_Status
"""
    if needle not in run:
        raise ValueError("GROUND_POST_POST_WRAPPER_ANCHOR")
    run = run.replace(needle, insert, 1)
    # Active-air/landing returns pending after actual source adjust_base and
    # before gravity marks or movement. The source executes adjust_base first.
    # The stationary wrapper computes its self binding after the save. Keep
    # this patch local to provider runtime by checking the selected canonical
    # row after it has installed SourceSelf.
    self_setup = """ lda #$41
 sta.l SourceSelf4086_GlobalHigh
 jsl SourceAdjustBaseEmpty4086_RunPost
"""
    active_test = """ lda #$41
 sta.l SourceSelf4086_GlobalHigh
 ; ent_post_update adjusts the base before check_gravity's active-air gate.
 jsl SourceAdjustBaseEmpty4086_RunPost
 bcc LiveGroundPost_AdjustBaseOK
 jmp LiveGroundPost_RestoreBad
LiveGroundPost_AdjustBaseOK:
 jsl SourceFreeze4086_Query
 bcc LiveGroundPost_FreezeOK
 jmp LiveGroundPost_RestoreBad
LiveGroundPost_FreezeOK:
 cmp #0
 beq LiveGroundPost_NotFrozen
 jmp LiveGroundPost_ActiveCandidateDone
LiveGroundPost_NotFrozen:
 ; Active falling, nonzero vertical velocity, or altitude/base mismatch needs
 ; the separate air/landing provider. Leave the phase outstanding atomically.
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l LiveGroundPost_Gravity_Aux
 tax
 lda.l SOURCE_ENTITY_PHYSICS,x
 ora.l SOURCE_ENTITY_PHYSICS+2,x
 ora.l SOURCE_ENTITY_PHYSICS+4,x
 ora.l SOURCE_ENTITY_PHYSICS+6,x
 bne LiveGroundPost_ActiveCandidate
 lda.l SourceSelf4086_GlobalLow
 sec
 sbc #$4000
 tax
 lda.l SOURCE_WORLD_POOL+12,x
 sta.l LiveGroundPost_Gravity_X
 lda.l SOURCE_WORLD_POOL+14,x
 sta.l LiveGroundPost_Gravity_X+2
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l LiveGroundPost_Gravity_Side
 asl a
 asl a
 clc
 adc.l LiveGroundPost_Gravity_Side
 tax
 lda.l SOURCE_WORLD_SIDES+44,x
 ora.l SOURCE_WORLD_SIDES+46,x
 bne LiveGroundPost_ActiveCandidate
 lda.l SOURCE_WORLD_SIDES+48,x
 cmp.l LiveGroundPost_Gravity_X
 bne LiveGroundPost_ActiveCandidate
 lda.l SOURCE_WORLD_SIDES+50,x
 cmp.l LiveGroundPost_Gravity_X+2
 bne LiveGroundPost_ActiveCandidate
 bra LiveGroundPost_ActiveCandidateDone
LiveGroundPost_ActiveCandidate:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 tax
 lda.l SOURCE_WORLD_TOSS_TIMES+2,x
 cmp.l VmSourceWorld_Time+2
 bcc LiveGroundPost_ActivePending
 bne LiveGroundPost_ActiveCandidateDone
 lda.l SOURCE_WORLD_TOSS_TIMES,x
 cmp.l VmSourceWorld_Time
 bcc LiveGroundPost_ActivePending
 beq LiveGroundPost_ActivePending
LiveGroundPost_ActiveCandidateDone:
 .a16
 .i16
"""
    if self_setup not in run:
        raise ValueError("GROUND_POST_OP_SEQUENCE_ANCHOR")
    # The entity physics row's first word is falling; word+4 is platform etc.
    # The two Y reads must be based on the already-computed canonical view and
    # side offsets. Compute them before the active predicate.
    run = run.replace(self_setup, active_test, 1)
    run = run.replace("LiveGroundPost_Execute:", "LiveGroundPost_Run:", 1)
    # Pending epilogue preserves registers and leaves B61A status zero.
    run += """LiveGroundPost_ActivePending:
.a16
.i16
 pla
 sta.l SourceSelf4086_GlobalLow
 pla
 sta.l SourceSelf4086_GlobalHigh
 lda #1
 ply
 plx
 plp
 clc
 rtl
"""
    # The clone needs explicit address aliases used by its unchanged source.
    clone = gravity
    # Export provider code with resolved canonical binding row; other
    # subsystem names remain linker-resolved in the assembled world image.
    text = ("; Bounded phase-11 grounded POST_UPDATE provider.\n" +
            "BOR_VT_DECIMAL = $02\n" +
            "LiveGroundPost_Ready = $40BFF8\n" +
            "LiveGroundPost_Status = $40BFFA\n" +
            "LiveGroundPost_Slot = $40BFFC\n" +
            run.replace("{binding_base:06X}", f"${binding_base:06X}")
               .replace("{binding_base + 2:06X}", f"${binding_base + 2:06X}") + clone + "\n")
    for name in required:
        text = text.replace(name, f"${symbols[name]:06X}")
    return text
