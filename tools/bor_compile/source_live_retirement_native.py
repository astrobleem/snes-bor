"""Guarded source-table preparation for one cold He-Man live session.

This module does not implement a general source kill.  It establishes the
existing relation/role storage only at a cold, exclusive preconstructor
boundary, validates the real constructor result, and preserves the source
``summonkill`` scalar already written for the one admitted He-Man actor. The ordinary
``SourceRetirement4086_ApplyNoEvents`` remains the only retirement operation.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping

from source_retirement_state import derive as retirement_requirements
from source_script_clone import derive as script_clone_profile
from source_model_core_4086 import derive as model_core_profile

RELATIONS = 0x409000
RELATION_BYTES = 128 * 64
ROLE_BASE = 0x43FD80
ROLE_BYTES = 32
ACTOR_BASE = 0x414000
ACTOR_STRIDE = 80
ACTOR_COUNT = 128
CORE_BASE = 0x40C000
CORE_STRIDE = 96
FLAGS_BASE = 0x43EB00
FLAGS_STRIDE = 32
WORK = 0x7E7700
MOTION = 0x7E7900
LEASE_GENERATION = 1
LIVE_MAGIC = 0xB6D0
MOTION_MAGIC = 0xB6E4
RETIRE_READY = 0xB4F8


def derive(source) -> dict:
    """Derive and pin the complete retirement-sensitive model registry."""
    retirement = retirement_requirements(source)
    scripts = script_clone_profile(source)
    cores = model_core_profile(source)
    rows = retirement.get("models", [])
    script_rows = scripts.get("models", [])
    core_rows = cores.get("models", [])
    if not (len(rows) == len(script_rows) == len(core_rows) == 16):
        raise ValueError("LIVE_RETIREMENT_REGISTRY_COUNT")
    models = []
    for index, (ret, script, core) in enumerate(zip(rows, script_rows, core_rows)):
        if not (ret.get("id") == script.get("id") == core.get("id") == index
                and ret.get("identity") == script.get("identity") == core.get("identity")
                and ret.get("source_sha256") == script.get("source_sha256") == core.get("source_sha256")):
            raise ValueError("LIVE_RETIREMENT_REGISTRY_IDENTITY")
        if ret.get("summonkill") != 1:
            raise ValueError("LIVE_RETIREMENT_SUMMONKILL_DOMAIN")
        if ret.get("onkill_required") or ret.get("clear_entry_scripts"):
            raise ValueError("LIVE_RETIREMENT_CALLBACK_REQUIRED")
        models.append({
            "id": index,
            "identity": ret["identity"],
            "source_sha256": ret["source_sha256"],
            "summonkill": ret["summonkill"],
            "onkill_required": False,
            "clear_entry_scripts": [],
            "script_initialized_mask": script.get("initialized_mask"),
            "callback_program": script.get("callback_program"),
            "source_type": core.get("fields", {}).get("type"),
        })
    heman = [m for m in models if m["identity"].casefold() == "he_man"]
    if len(heman) != 1 or heman[0]["id"] != 3 or heman[0]["script_initialized_mask"] != 1:
        raise ValueError("LIVE_RETIREMENT_HEMAN_PROFILE")
    # SourceCtorState's textbox selector reads core+$48 (hex), the 32-bit
    # `type` field, not decimal core+48/projectilehit. The admitted He-Man is
    # a player (type 1), which leaves the textbox role unset.
    if heman[0]["source_type"] != 1:
        raise ValueError("LIVE_RETIREMENT_HEMAN_SOURCE_TYPE")
    pak_sha = None
    source_path = getattr(source, "path", None)
    if source_path is not None:
        from pathlib import Path
        source_path = Path(source_path)
        if source_path.is_file():
            pak_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    registry_bytes = json.dumps(models, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema": "BYOR_SOURCE_LIVE_COLD_RETIREMENT_V1",
        "source_pak_sha256": pak_sha,
        "registry_sha256": hashlib.sha256(registry_bytes).hexdigest(),
        "registry_count": 16,
        "models": models,
        "heman_model_id": 3,
        "heman_initialized_mask": 1,
        "heman_summonkill": 1,
        "all_models_summonkill_1": True,
        "all_models_no_onkill_or_clear_entries": True,
        "physical_relation_layout": {
            "base": RELATIONS, "stride": 64, "count": 128, "bytes": RELATION_BYTES,
            "summonkill_offset": 36, "initialized_script_mask_offset": 44,
            "clear_entry_mask_offset": 48, "onkill_initialized_offset": 52,
        },
        "role_layout": {"base": ROLE_BASE, "bytes": ROLE_BYTES,
                         "cold_after_constructor": "ent_count=1; player0 token low/high words zero (unbound); all remaining role words zero",
                         "gameplay_after_birth_bind": {"count": 1, "player0_token": 0x414000,
                                                        "other_role_fields": [8, 32]}},
        "profile_scope": "No-event/no-minion SourceRetirement4086 only; full callback and damage retirement remains unsupported.",
        "runtime_admission_proven": False,
    }


def _address(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFF:
        raise ValueError("LIVE_RETIREMENT_ADDRESS:" + name)
    return value


def _target(value, name):
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 0xFFFFFF:
        return f"${value:06X}"
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z_]\w*", value):
        return value
    raise ValueError("LIVE_RETIREMENT_TARGET:" + name)


_REQUIRED = (
    "SourceForeignWork_Check",
    "SourceClock4086_Ready", "SourceClock4086_Due",
    "SourceWorldTick4086_Ready", "SourceWorldTick4086_State",
    "SourceWorldTick4086_Pending",
    "VmSourceWorld_Ready", "VmSourceWorld_PoolBase", "VmSourceWorld_SideBase",
    "VmSourceWorld_Count", "VmSourceWorld_TemplateCount",
    "SourceModelEntityCopy4086_Ready", "SourceModelEntityCopy4086_Entities",
    "SourceModelEntityCopy4086_Models",
    "SourceIdle4086_Ready", "SourceIdle4086_Status",
    "VmSourceVars_Ready", "VmSourceVars_Base", "VmSourceVars_Bank", "VmSourceVars_Count",
    "SourceSelf4086_Ready", "SourceSelf4086_Active", "SourceSelf4086_Fault",
    "SourceSelf4086_GlobalLow", "SourceSelf4086_GlobalHigh",
    "SourceUpdateFrame4086_CheckIdle", "SourceAnimationInit4086_CheckIdle",
    "SourceSelf4086_CheckIdle",
    "SourceVMRun4086_Busy", "VmSourceCallback_Active",
    "SourceCtorOwner4086_Phase", "SourceCtorOwner4086_Model",
    "SourceDefaultInit4086_OwnerSlot",
    "SourceRetirement4086_Ready", "SourceRetirement4086_Status",
    "LiveWorld_PreConstructor", "LiveWorld_Fault",
)


def _symbols(symbols):
    if not isinstance(symbols, Mapping):
        raise ValueError("LIVE_RETIREMENT_SYMBOL_MAP")
    absent = [name for name in _REQUIRED if name not in symbols]
    if absent:
        raise ValueError("LIVE_RETIREMENT_SYMBOLS_MISSING:" + ",".join(absent))
    return {name: _address(symbols[name], name) for name in _REQUIRED}


def _check(lines, address, value, fail, good):
    lines.extend((f" lda.l ${address:06X}", f" cmp #${value & 0xFFFF:04X}",
                  f" beq {good}", f" jmp {fail}", f"{good}:", ".a16", ".i16"))


def _zero(lines, address, fail, good):
    _check(lines, address, 0, fail, good)


def _lease(lines, sy, fail, generation=LEASE_GENERATION, epoch=0):
    suffix = len(lines)
    lines.extend((f" lda.l ${WORK:06X}", f" cmp #${LIVE_MAGIC:04X}",
                  f" beq LiveRetirement_OwnerMagic{suffix}", f" jmp {fail}",
                  f"LiveRetirement_OwnerMagic{suffix}:", ".a16", ".i16",
                  f" lda.l ${WORK+4:06X}", f" cmp #${generation:04X}",
                  f" beq LiveRetirement_GenLo{suffix}", f" jmp {fail}",
                  f"LiveRetirement_GenLo{suffix}:", ".a16", ".i16",
                  f" lda.l ${WORK+6:06X}", f" cmp #${epoch:04X}",
                  f" beq LiveRetirement_GenHi{suffix}", f" jmp {fail}",
                  f"LiveRetirement_GenHi{suffix}:", ".a16", ".i16",
                  f" ldx #${generation:04X}", f" ldy #${epoch:04X}",
                  f" jsl ${sy['SourceForeignWork_Check']:06X}",
                  f" bcc LiveRetirement_LeaseOk{suffix}", f" jmp {fail}",
                  f"LiveRetirement_LeaseOk{suffix}:", ".a16", ".i16"))


def _guard_work_start(lines, sy, *, fail, generation, epoch, motion_control,
                      require_zero_commits):
    _lease(lines, sy, fail, generation, epoch)
    if motion_control is not None:
        _zero(lines, motion_control, fail, f"LiveRetirement_MotionEmpty{len(lines)}")
    if require_zero_commits:
        _zero(lines, WORK + 8, fail, f"LiveRetirement_CommitLo{len(lines)}")
        _zero(lines, WORK + 10, fail, f"LiveRetirement_CommitHi{len(lines)}")


def _prologue(lines, label):
    lines.extend((f"{label}:", ".a16", ".i16", " php", " rep #$38", " phx", " phy",
                  " phb", " phd", " sep #$20", ".a8", " lda #0", " pha", " plb",
                  " rep #$20", ".a16", " lda #0", " tcd"))


def _return(lines, result, carry):
    lines.extend((f" lda #{result}", " pld", " plb", " ply", " plx", " plp",
                  " sec" if carry else " clc", " rtl"))


def _idle_guards(lines, sy, fail):
    for i, name in enumerate(("SourceUpdateFrame4086_CheckIdle",
                              "SourceAnimationInit4086_CheckIdle",
                              "SourceSelf4086_CheckIdle")):
        good = f"LiveRetirement_IdleGood{i}_{len(lines)}"
        lines.extend((f" jsl ${sy[name]:06X}", f" bcc {good}", f" jmp {fail}",
                      f"{good}:", ".a16", ".i16"))


def _actor_scan(lines, *, first_alive, fail, label_prefix):
    """Validate actor view exists words; slot 0 has expected state, others opposite."""
    if first_alive:
        _check(lines, ACTOR_BASE + 4, 1, fail, f"{label_prefix}_Slot0Alive")
        _zero(lines, ACTOR_BASE + 6, fail, f"{label_prefix}_Slot0AliveHigh")
    else:
        _zero(lines, ACTOR_BASE + 4, fail, f"{label_prefix}_Slot0Dead")
        _zero(lines, ACTOR_BASE + 6, fail, f"{label_prefix}_Slot0DeadHigh")
    lines.extend((" ldx #80", f"{label_prefix}_DeadLoop:",
                  f" lda.l ${ACTOR_BASE+4:06X},x", " cmp #0",
                  f" beq {label_prefix}_DeadNext", f" jmp {fail}",
                  f"{label_prefix}_DeadNext:", f" lda.l ${ACTOR_BASE+6:06X},x", " cmp #0",
                  f" beq {label_prefix}_DeadHighOk", f" jmp {fail}",
                  f"{label_prefix}_DeadHighOk:",
                  " txa", " clc", " adc #80", " tax",
                  f" cpx #${ACTOR_COUNT*ACTOR_STRIDE:04X}",
                  f" bcc {label_prefix}_DeadLoop"))


def _check_source_providers(lines, sy, fail, *, status, clock_started):
    _check(lines, sy["SourceRetirement4086_Ready"], 0 if status == 0 else RETIRE_READY,
           fail, f"LiveRetirement_Ready{status}_{len(lines)}")
    _check(lines, sy["SourceRetirement4086_Status"], status,
           fail, f"LiveRetirement_Status{status}_{len(lines)}")
    _check(lines, sy["SourceClock4086_Ready"], 0xB4C5 if clock_started else 0,
           fail, f"LiveRetirement_ClockReady{len(lines)}")
    _zero(lines, sy["SourceClock4086_Due"], fail, f"LiveRetirement_ClockDue{len(lines)}")
    _check(lines, sy["SourceWorldTick4086_Ready"], 0xB4D5,
           fail, f"LiveRetirement_WorldReady{len(lines)}")
    _zero(lines, sy["SourceWorldTick4086_State"], fail, f"LiveRetirement_WorldState{len(lines)}")
    _zero(lines, sy["SourceWorldTick4086_Pending"], fail, f"LiveRetirement_WorldPending{len(lines)}")
    _check(lines, sy["VmSourceWorld_Ready"], 0xB4A3,
           fail, f"LiveRetirement_SourceWorld{len(lines)}")
    _check(lines, sy["VmSourceWorld_PoolBase"], 0x4000,
           fail, f"LiveRetirement_PoolBase{len(lines)}")
    _check(lines, sy["VmSourceWorld_SideBase"], 0x6800,
           fail, f"LiveRetirement_SideBase{len(lines)}")
    _check(lines, sy["VmSourceWorld_Count"], ACTOR_COUNT,
           fail, f"LiveRetirement_PoolCount{len(lines)}")
    _check(lines, sy["VmSourceWorld_TemplateCount"], 16,
           fail, f"LiveRetirement_TemplateCount{len(lines)}")
    _check(lines, sy["SourceModelEntityCopy4086_Ready"], 0xB4EB,
           fail, f"LiveRetirement_ModelCopy{len(lines)}")
    _check(lines, sy["SourceModelEntityCopy4086_Entities"], ACTOR_COUNT,
           fail, f"LiveRetirement_EntityCount{len(lines)}")
    _check(lines, sy["SourceModelEntityCopy4086_Models"], 16,
           fail, f"LiveRetirement_ModelCount{len(lines)}")
    _check(lines, sy["SourceIdle4086_Ready"], 0xB4F3,
           fail, f"LiveRetirement_IdleReady{len(lines)}")
    _zero(lines, sy["SourceIdle4086_Status"], fail, f"LiveRetirement_IdleStatus{len(lines)}")
    _check(lines, sy["VmSourceVars_Ready"], 0xB4A4,
           fail, f"LiveRetirement_VarsReady{len(lines)}")
    _check(lines, sy["VmSourceVars_Base"], 0x8800,
           fail, f"LiveRetirement_VarsBase{len(lines)}")
    _check(lines, sy["VmSourceVars_Bank"], 0x41,
           fail, f"LiveRetirement_VarsBank{len(lines)}")
    _check(lines, sy["VmSourceVars_Count"], 384,
           fail, f"LiveRetirement_VarsCount{len(lines)}")
    _check(lines, sy["SourceSelf4086_Ready"], 0xB4F6,
           fail, f"LiveRetirement_SelfReady{len(lines)}")
    _zero(lines, sy["SourceSelf4086_Active"], fail, f"LiveRetirement_SelfActive{len(lines)}")
    _zero(lines, sy["SourceSelf4086_Fault"], fail, f"LiveRetirement_SelfFault{len(lines)}")
    _zero(lines, sy["SourceVMRun4086_Busy"], fail, f"LiveRetirement_VMRun{len(lines)}")
    _zero(lines, sy["VmSourceCallback_Active"], fail, f"LiveRetirement_Callback{len(lines)}")
    _idle_guards(lines, sy, fail)


def _verify_dead_relation_rows(lines, fail, prefix):
    # The preconstructor entry owns and clears this table. The postconstructor
    # validator checks that constructor initialization did not leave stale
    # references in any slot other than the live actor row.
    lines.extend((" ldx #64", f"{prefix}_RelationScan:",
                  f" lda.l ${RELATIONS:06X},x", " cmp #0",
                  f" beq {prefix}_RelationNext", f" jmp {fail}",
                  f"{prefix}_RelationNext:", " inx", " inx",
                  f" cpx #${RELATION_BYTES:04X}", f" bcc {prefix}_RelationScan"))


def _validate_live_actor(lines, sy, fail, *, expected_status, expected_motion_state=None):
    _actor_scan(lines, first_alive=True, fail=fail, label_prefix=f"LiveRetirement_Actor{len(lines)}")
    # Constructor owner history is the available canonical source model
    # identity; modeldata type alone cannot distinguish He-Man from another
    # player model. Its completed phase, model ID and actual chosen slot are
    # all checked together with the cloned animation mask.
    _check(lines, sy["SourceCtorOwner4086_Phase"], 2, fail,
           f"LiveRetirement_CtorDone{len(lines)}")
    _check(lines, sy["SourceCtorOwner4086_Model"], 3, fail,
           f"LiveRetirement_CtorModel{len(lines)}")
    _check(lines, sy["SourceDefaultInit4086_OwnerSlot"], 0, fail,
           f"LiveRetirement_CtorSlot{len(lines)}")
    _check(lines, CORE_BASE + 72, 1, fail, f"LiveRetirement_PlayerType{len(lines)}")
    # Live row relations are validated null for this sole unlinked player and
    # then preserved. The initialized mask itself is source constructor output.
    for offset in range(0, 32, 2):
        _zero(lines, RELATIONS + offset, fail, f"LiveRetirement_Row0Relation{offset}_{len(lines)}")
    _check(lines, RELATIONS + 44, 1, fail, f"LiveRetirement_AnimMask{len(lines)}")
    _zero(lines, RELATIONS + 48, fail, f"LiveRetirement_ClearMask{len(lines)}")
    _zero(lines, RELATIONS + 52, fail, f"LiveRetirement_OnkillMask{len(lines)}")
    # Successful source construction increments ent_count before it returns.
    # The preview is live even though spawnplayer has not bound player[0].ent.
    _check(lines, ROLE_BASE, 1, fail, f"LiveRetirement_RoleCount{len(lines)}")
    if expected_status == 0:
        # SourceCtorStateFinish can publish an optional textbox role at +24,
        # but He-Man's core type is 1 (not TEXT=128). It does not bind the
        # player role; spawnplayer binds that only after the later gameplay
        # constructor has returned.
        for offset in range(2, ROLE_BYTES, 2):
            _zero(lines, ROLE_BASE + offset, fail,
                  f"LiveRetirement_ColdRole{offset}_{len(lines)}")
    else:
        _zero(lines, ROLE_BASE + 2, fail, f"LiveRetirement_RoleCountHi{len(lines)}")
        _check(lines, ROLE_BASE + 4, 0x4000, fail, f"LiveRetirement_Player0Lo{len(lines)}")
        _check(lines, ROLE_BASE + 6, 0x0041, fail, f"LiveRetirement_Player0Hi{len(lines)}")
        for offset in range(8, ROLE_BYTES, 2):
            _zero(lines, ROLE_BASE + offset, fail, f"LiveRetirement_Role{offset}_{len(lines)}")
    # SourceSelf's engine-global may remain NULL or point to this one admitted
    # actor. Preserve either full valid state, and reject half pointers.
    global_null = f"LiveRetirement_GlobalNull{len(lines)}"
    global_good = f"LiveRetirement_GlobalGood{len(lines)}"
    lines.extend((f" lda.l ${sy['SourceSelf4086_GlobalHigh']:06X}", " cmp #0",
                  f" beq {global_null}", " cmp #$0041",
                  f" beq {global_good}", f" jmp {fail}",
                  f"{global_null}:", ".a16", ".i16",
                  f" lda.l ${sy['SourceSelf4086_GlobalLow']:06X}", " cmp #0",
                  f" beq {global_good}", f" jmp {fail}",
                  f"{global_good}:", ".a16", ".i16",
                  f" lda.l ${sy['SourceSelf4086_GlobalLow']:06X}", " cmp #0",
                  f" beq {global_good}_NullLow", " cmp #$4000",
                  f" beq {global_good}_Done", f" jmp {fail}",
                  f"{global_good}_NullLow:", ".a16", ".i16",
                  f" lda.l ${sy['SourceSelf4086_GlobalHigh']:06X}", " cmp #0",
                  f" beq {global_good}_Done", f" jmp {fail}",
                  f"{global_good}_Done:", ".a16", ".i16"))
    if expected_motion_state is not None:
        _check(lines, MOTION + 2, expected_motion_state, fail,
               f"LiveRetirement_MotionState{len(lines)}")


def emit(symbols, profile, *, preconstructor_return, fault_target="LiveWorld_Fault",
         work=WORK, motion=MOTION, lease_generation=LEASE_GENERATION, lease_epoch=0):
    """Emit a cold-owner guard, table initializer, and metadata validators.

    ``LiveRetirement_AcquireGuard`` replaces the old-init JML and admits only
    cold root ownership before entering the new live-world initializer.
    ``LiveRetirement_PreConstructor`` runs at the preconstructor continuation.
    On success it clears the
    relation table and role block while all 128 actor slots are still dead,
    then jumps to the original continuation supplied by the builder.

    ``LiveRetirement_ColdInit`` runs after the real He-Man preview constructor
    and cold picture publication, before any tick. It validates all providers
    and actual constructor/role rows, validates row0's source-derived
    summonkill scalar, and publishes B4F8 last.

    ``LiveRetirement_BirthMetadata`` validates the constructor-installed scalar
    for a fresh gameplay constructor while the handoff remains in BIRTH_PENDING and before
    it publishes GAMEPLAY. Result ABI is A=0 success / A=1 fault, C clear / set.
    """
    sy = _symbols(symbols)
    if not isinstance(profile, Mapping) or profile.get("schema") != "BYOR_SOURCE_LIVE_COLD_RETIREMENT_V1":
        raise ValueError("LIVE_RETIREMENT_PROFILE_SCHEMA")
    if (profile.get("registry_count") != 16 or profile.get("heman_model_id") != 3
            or profile.get("heman_initialized_mask") != 1
            or profile.get("heman_summonkill") != 1
            or profile.get("all_models_summonkill_1") is not True
            or profile.get("all_models_no_onkill_or_clear_entries") is not True):
        raise ValueError("LIVE_RETIREMENT_PROFILE_POLICY")
    work = _address(work, "work")
    motion = _address(motion, "motion")
    if work != WORK or motion != MOTION:
        raise ValueError("LIVE_RETIREMENT_FIXED_CONTROL_LAYOUT")
    if lease_generation != LEASE_GENERATION or lease_epoch != 0:
        raise ValueError("LIVE_RETIREMENT_LEASE_EPOCH")
    preconstructor_return = _target(preconstructor_return, "preconstructor_return")
    fault_target = _target(fault_target, "fault_target")
    lines = []

    # LiveWorld_PreConstructor clears WORK and motion storage. This durable
    # guard therefore executes at the old-init JML, before those resets. Any
    # existing root owner means re-entry and must fault without a write.
    lines.extend(("LiveRetirement_AcquireGuard:", ".a16", ".i16", " php", " rep #$38",
                  " pha", " phx", " phy", " phb", " phd", " sep #$20", ".a8",
                  " lda #0", " pha", " plb", " rep #$20", ".a16", " lda #0", " tcd"))
    _zero(lines, 0x7FFB88, "LiveRetirement_AcquireFault",
          "LiveRetirement_AcquireCold")
    lines.extend((" pld", " plb", " ply", " plx", " pla", " plp", " clc",
                  f" jml ${sy['LiveWorld_PreConstructor']:06X}",
                  "LiveRetirement_AcquireFault:", ".a16", ".i16", " pld", " plb",
                  " ply", " plx", " pla", " plp", " sec",
                  f" jml ${sy['LiveWorld_Fault']:06X}"))

    # Stage 1: this entry is called before constructor birth, after acquisition
    # has disabled the cold scene writer. It cannot run after an actor exists.
    _prologue(lines, "LiveRetirement_PreConstructor")
    _guard_work_start(lines, sy, fail="LiveRetirement_PreFault", generation=lease_generation,
                      epoch=lease_epoch, motion_control=motion, require_zero_commits=True)
    _zero(lines, sy["SourceClock4086_Ready"], "LiveRetirement_PreFault",
          f"LiveRetirement_PreClockCold{len(lines)}")
    _zero(lines, sy["SourceRetirement4086_Ready"], "LiveRetirement_PreFault",
          f"LiveRetirement_PreReadyCold{len(lines)}")
    _zero(lines, sy["SourceWorldTick4086_State"], "LiveRetirement_PreFault",
          f"LiveRetirement_PreTickState{len(lines)}")
    _zero(lines, sy["SourceWorldTick4086_Pending"], "LiveRetirement_PreFault",
          f"LiveRetirement_PreTickPending{len(lines)}")
    _zero(lines, sy["VmSourceCallback_Active"], "LiveRetirement_PreFault",
          f"LiveRetirement_PreCallback{len(lines)}")
    _zero(lines, sy["SourceVMRun4086_Busy"], "LiveRetirement_PreFault",
          f"LiveRetirement_PreVMRun{len(lines)}")
    _actor_scan(lines, first_alive=False, fail="LiveRetirement_PreFault",
                label_prefix="LiveRetirement_PreDead")
    # All checks precede the first write. This full table and roles are
    # unowned/unused at the constructor boundary, proven by all actor slots dead.
    lines.extend((" lda #0", " ldx #0", "LiveRetirement_PreClearRelations:",
                  f" sta.l ${RELATIONS:06X},x", " inx", " inx",
                  f" cpx #${RELATION_BYTES:04X}",
                  " bcc LiveRetirement_PreClearRelations",
                  " lda #0", " ldx #0", "LiveRetirement_PreClearRoles:",
                  f" sta.l ${ROLE_BASE:06X},x", " inx", " inx",
                  f" cpx #${ROLE_BYTES:04X}", " bcc LiveRetirement_PreClearRoles",
                  " lda #0", f" sta.l ${sy['SourceRetirement4086_Status']:06X}",
                  " lda #0", " pld", " plb", " ply", " plx", " plp", " clc",
                  f" jml {preconstructor_return}",
                  "LiveRetirement_PreFault:", ".a16", ".i16", " pld", " plb",
                  " ply", " plx", " plp", " sec", f" jml {fault_target}"))

    # Stage 2: completed preview constructor, cold publisher returned, but no
    # world tick has committed. The real constructor has already installed
    # the source-derived summonkill DWORD in this relation row; validate and
    # preserve it instead of rewriting live constructor-owned state.
    _prologue(lines, "LiveRetirement_ColdInit")
    _guard_work_start(lines, sy, fail="LiveRetirement_ColdBad", generation=lease_generation,
                      epoch=lease_epoch, motion_control=motion, require_zero_commits=True)
    _check_source_providers(lines, sy, "LiveRetirement_ColdBad", status=0, clock_started=True)
    _validate_live_actor(lines, sy, "LiveRetirement_ColdBad", expected_status=0)
    _verify_dead_relation_rows(lines, "LiveRetirement_ColdBad", "LiveRetirement_Cold")
    # SourceCtorState4086_Finish copies the two words at B5CI Row+8/+10
    # directly into relation-row +$24/+26. For the pinned He-Man source row,
    # that source-derived DWORD is summonkill=1; only publish retirement once
    # the constructor's value is verified intact.
    _check(lines, RELATIONS + 36, 1, "LiveRetirement_ColdBad",
           f"LiveRetirement_ColdSummonkillLo{len(lines)}")
    _zero(lines, RELATIONS + 38, "LiveRetirement_ColdBad",
          f"LiveRetirement_ColdSummonkillHi{len(lines)}")
    lines.extend((f" lda #0", f" sta.l ${sy['SourceRetirement4086_Status']:06X}",
                  f" lda #${RETIRE_READY:04X}", f" sta.l ${sy['SourceRetirement4086_Ready']:06X}",
                  "LiveRetirement_ColdPublished:", " lda #0", " pld", " plb", " ply", " plx", " plp", " clc", " rtl",
                  "LiveRetirement_ColdBad:", ".a16", ".i16", " lda #1", " pld", " plb",
                  " ply", " plx", " plp", " sec", " rtl"))

    # The actual source constructor clears relation row0 and repopulates the
    # source scalar from the same B5CI record. Validate it before the handoff
    # becomes GAMEPLAY; do not rewrite constructor-owned relation state.
    _prologue(lines, "LiveRetirement_BirthMetadata")
    _guard_work_start(lines, sy, fail="LiveRetirement_BirthBad", generation=lease_generation,
                      epoch=lease_epoch, motion_control=None, require_zero_commits=False)
    _check(lines, sy["SourceRetirement4086_Ready"], RETIRE_READY,
           "LiveRetirement_BirthBad", f"LiveRetirement_BirthReady{len(lines)}")
    _check(lines, sy["SourceRetirement4086_Status"], 2,
           "LiveRetirement_BirthBad", f"LiveRetirement_BirthStatus{len(lines)}")
    _check(lines, sy["SourceClock4086_Ready"], 0xB4C5,
           "LiveRetirement_BirthBad", f"LiveRetirement_BirthClock{len(lines)}")
    _zero(lines, sy["SourceClock4086_Due"], "LiveRetirement_BirthBad",
          f"LiveRetirement_BirthDue{len(lines)}")
    _zero(lines, sy["SourceWorldTick4086_State"], "LiveRetirement_BirthBad",
          f"LiveRetirement_BirthTickState{len(lines)}")
    _zero(lines, sy["SourceWorldTick4086_Pending"], "LiveRetirement_BirthBad",
          f"LiveRetirement_BirthTickPending{len(lines)}")
    _zero(lines, sy["VmSourceCallback_Active"], "LiveRetirement_BirthBad",
          f"LiveRetirement_BirthCallback{len(lines)}")
    _zero(lines, sy["SourceVMRun4086_Busy"], "LiveRetirement_BirthBad",
          f"LiveRetirement_BirthVMRun{len(lines)}")
    _check(lines, MOTION, MOTION_MAGIC, "LiveRetirement_BirthBad",
           f"LiveRetirement_BirthMotion{len(lines)}")
    _check(lines, MOTION + 2, 1, "LiveRetirement_BirthBad",
           f"LiveRetirement_BirthPending{len(lines)}")
    _validate_live_actor(lines, sy, "LiveRetirement_BirthBad", expected_status=2,
                         expected_motion_state=1)
    # The real constructor replays the same source state record. Require the
    # complete source DWORD and leave both words untouched.
    _check(lines, RELATIONS + 36, 1, "LiveRetirement_BirthBad",
           f"LiveRetirement_BirthSummonkillLo{len(lines)}")
    _zero(lines, RELATIONS + 38, "LiveRetirement_BirthBad",
          f"LiveRetirement_BirthSummonkillHi{len(lines)}")
    lines.extend(("LiveRetirement_BirthValidated:",
                  " lda #0", " pld", " plb", " ply", " plx", " plp", " clc", " rtl",
                  "LiveRetirement_BirthBad:", ".a16", ".i16", " lda #1", " pld", " plb",
                  " ply", " plx", " plp", " sec", " rtl"))
    return "\n".join(lines) + "\n"
