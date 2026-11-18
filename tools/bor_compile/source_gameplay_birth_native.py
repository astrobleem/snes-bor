"""Source-derived request and driver for a fresh gameplay player birth.

    The setup entry writes only request scalars then begins SourceCtorOwner;
    the run entry services allocation/default initialization,
set_idle, and the published token to the existing source constructor.  A
caller must invoke Setup/Run only after its real preview-retirement owner has
reported BIRTH_PENDING, and must keep the checked stage context registers
available while Run is pending.
"""
from __future__ import annotations

import hashlib


def derive(source, *, model_name="He_Man", stage_path="DATA/LEVELS/GUILE2.TXT"):
    """Derive the player model, authored stage placement, and animation roles.

    This intentionally admits only the empty-terrain spawn profile already
    implemented by ``source_player_spawn_inputs``.  It does not prove runtime
    constructor completion; that is the native owner's job.
    """
    from compiler import key
    from source_profile import document, discover
    from source_player_spawn_inputs import derive as spawn_inputs
    from source_model_core_4086 import derive as core_inputs
    from source_animation_ids import configure, role_id

    docs = {k: document(source, name) for k, (name, _) in source.index.items()
            if k.endswith(".txt")}
    structure = discover(source, docs)
    wanted = key(stage_path)
    stages = spawn_inputs(source)["stages"]
    stage_rows = [row for row in stages if key(row["source_path"]) == wanted]
    if len(stage_rows) != 1:
        raise ValueError("GAMEPLAY_BIRTH_STAGE_IDENTITY")
    stage = stage_rows[0]
    if stage["diagnostics"] or stage["capability"] != "SOURCE_EMPTY_TERRAIN_SPAWN_INPUTS":
        raise ValueError("GAMEPLAY_BIRTH_EMPTY_STAGE_REQUIRED")
    if stage["scroll"] not in ("left", "right", "horizontal"):
        raise ValueError("GAMEPLAY_BIRTH_HORIZONTAL_STAGE_REQUIRED")
    player_rows = [row for row in stage["placements"] if row["index"] == 0]
    if len(player_rows) != 1:
        raise ValueError("GAMEPLAY_BIRTH_PLAYER_ZERO_PLACEMENT")

    models = [row for row in structure["models"]
              if row["declaration"].casefold() == model_name.casefold()]
    if len(models) != 1:
        raise ValueError("GAMEPLAY_BIRTH_MODEL_IDENTITY")
    model = models[0]
    core_rows = [row for row in core_inputs(source)["models"]
                 if row["source_path"].casefold() == model["source_path"].casefold()]
    if len(core_rows) != 1 or core_rows[0]["fields"]["type"] != 1:
        raise ValueError("GAMEPLAY_BIRTH_PLAYER_MODEL_REQUIRED")
    model_id = core_rows[0]["id"]

    model_doc = docs[key(model["source_path"])]
    animation_config = configure(docs[key(structure["models_path"])]["directives"])
    roles = {row["role"].casefold() for row in model["animations"]}
    if "idle" not in roles:
        raise ValueError("GAMEPLAY_BIRTH_IDLE_REQUIRED")
    unsupported_initial = sorted(roles.intersection({"spawn", "respawn", "pick"}))
    if unsupported_initial:
        raise ValueError("GAMEPLAY_BIRTH_INITIAL_ANIMATION_PRESENT:" + ",".join(unsupported_initial))
    walk_id = role_id(animation_config, "walk")
    idle_id = role_id(animation_config, "idle")
    placement = player_rows[0]
    if placement["flip"] not in (0, 1):
        raise ValueError("GAMEPLAY_BIRTH_DIRECTION_DOMAIN")

    return {
        "schema": "BYOR_SOURCE_GAMEPLAY_BIRTH_V1",
        "model_name": model["declaration"],
        "model_id": model_id,
        "model_source_path": model["source_path"],
        "model_source_sha256": model_doc["sha256"],
        "stage_path": stage["source_path"],
        "stage_id": stage["stage_id"],
        "stage_source_sha256": stage["source_sha256"],
        "stage_scroll": stage["scroll"],
        "source_pak_sha256": hashlib.sha256(source.path.read_bytes()).hexdigest()
        if hasattr(source, "path") and source.path.is_file() else None,
        "placement": {name: placement[name] for name in
                      ("index", "x_q16", "z_q16", "flip")},
        "walk_animation_id": walk_id,
        "idle_animation_id": idle_id,
        "default_choice_select": 0,
        "absent_initial_roles": unsupported_initial,
        "uses_source_ctor_owner": True,
        "runtime_birth_proven": False,
    }


def _put(lines, text):
    lines.extend(text.strip().splitlines())


def emit_setup(profile, sy, *, handoff_ready_address, handoff_phase_address,
               handoff_ready=0xB6E1, birth_pending=4,
               lease_generation=1, lease_epoch=0):
    """Emit guarded source request setup; no entity/animation row is written.

    Input: X/Y remain the caller's checked B5DC stage context. The profile's
    source-derived player-zero X/Z/direction and model are written only to
    SourceSpawnSlot/SourceCtorState request fields. Time is copied from the
    real logical world clock. The lifecycle handoff is read-only.
    """
    if profile.get("schema") != "BYOR_SOURCE_GAMEPLAY_BIRTH_V1":
        raise ValueError("GAMEPLAY_BIRTH_PROFILE_SCHEMA")
    if (profile.get("default_choice_select") != 0 or profile.get("runtime_birth_proven")
            or profile.get("absent_initial_roles") != []
            or not profile.get("uses_source_ctor_owner")):
        raise ValueError("GAMEPLAY_BIRTH_PROFILE_POLICY")
    if profile.get("stage_scroll") not in ("left", "right", "horizontal"):
        raise ValueError("GAMEPLAY_BIRTH_HORIZONTAL_STAGE_REQUIRED")
    p = profile["placement"]
    if p["index"] != 0 or p["flip"] not in (0, 1):
        raise ValueError("GAMEPLAY_BIRTH_PROFILE_PLACEMENT")
    required = ("SourceForeignWork_Check", "VmSourceWorld_Ready", "VmSourceWorld_Level",
                "VmSourceWorld_AdvanceX", "VmSourceWorld_AdvanceY", "VmSourceWorld_ScrollAxis",
                "SourceEnvironment4086_Ready", "SourceEnvironment4086_Stage",
                "SourceEnvironment4086_WallCount", "SourceCtorState4086_Ready",
                "SourceEmptyInitEnvironment4086_Ready", "SourceEmptyInitEnvironment4086_Stage",
                "SourceEmptyInitEnvironment4086_Status",
                "SourceCtorState4086_Status", "SourceSpawnSlot4086_Ready",
                "SourceCtorOwner4086_Begin", "SourceCtorOwner4086_Result",
                "SourceCtorOwner4086_Phase", "SourceDefaultChoice4086_Ready",
                "SourceDefaultPlayer4086_Ready")
    absent = [name for name in required if name not in sy]
    if absent:
        raise ValueError("GAMEPLAY_BIRTH_SYMBOLS_MISSING:" + ",".join(absent))
    lines = []
    _put(lines, "GameplayBirth_Setup:\n.a16\n.i16\n php\n rep #$38\n phx\n phy")
    _put(lines, f" phx\n phy\n ldx #{lease_generation}\n ldy #{lease_epoch}\n jsl {sy['SourceForeignWork_Check']}\n ply\n plx\n bcc GameplayBirth_SetupLeaseOk\n jmp GameplayBirth_SetupBad\nGameplayBirth_SetupLeaseOk:\n.a16\n.i16")
    _put(lines, f" lda.l ${handoff_ready_address:06X}\n cmp #${handoff_ready:04X}\n beq GameplayBirth_SetupReady\n jmp GameplayBirth_SetupBad\nGameplayBirth_SetupReady:\n.a16\n.i16")
    _put(lines, f" lda.l ${handoff_phase_address:06X}\n cmp #{birth_pending}\n beq GameplayBirth_SetupPending\n jmp GameplayBirth_SetupBad\nGameplayBirth_SetupPending:\n.a16\n.i16")
    for name, value in (("VmSourceWorld_Ready", 0xB4A3), ("VmSourceWorld_Level", 1),
                        ("SourceEnvironment4086_Ready", 0xB4D1),
                        ("SourceEnvironment4086_Stage", profile["stage_id"]),
                        ("SourceEnvironment4086_WallCount", 0),
                        ("SourceEmptyInitEnvironment4086_Ready", 0xB504),
                        ("SourceEmptyInitEnvironment4086_Stage", profile["stage_id"]),
                        ("VmSourceWorld_ScrollAxis", 0),
                        ("SourceCtorState4086_Ready", 0xB5C2),
                        ("SourceSpawnSlot4086_Ready", 0xB5A1),
                        ("SourceDefaultChoice4086_Ready", 0xB4FA),
                        ("SourceDefaultPlayer4086_Ready", 0xB503)):
        _put(lines, f" lda.l {sy[name]}\n cmp #${value:04X}\n beq GameplayBirth_SetupG{len(lines)}\n jmp GameplayBirth_SetupBad\nGameplayBirth_SetupG{len(lines)}:\n.a16\n.i16")
    # The actual owner defines status 0 as idle and status 2 as a successfully
    # completed query that is also idle. Preserve the B504/stage checks above;
    # reject running/fault/unknown states rather than resetting the owner.
    status = sy["SourceEmptyInitEnvironment4086_Status"]
    _put(lines, f" lda.l {status}\n cmp #0\n beq GameplayBirth_SetupEnvironmentIdle\n cmp #2\n beq GameplayBirth_SetupEnvironmentIdle\n jmp GameplayBirth_SetupBad\nGameplayBirth_SetupEnvironmentIdle:\n.a16\n.i16")
    for name in ("VmSourceWorld_AdvanceX", "VmSourceWorld_AdvanceY"):
        _put(lines, f" lda.l {sy[name]}\n ora.l {sy[name]}+2\n beq GameplayBirth_SetupCamera{len(lines)}\n jmp GameplayBirth_SetupBad\nGameplayBirth_SetupCamera{len(lines)}:\n.a16\n.i16")
    _put(lines, f" lda.l {sy['SourceCtorOwner4086_Phase']}\n cmp #0\n beq GameplayBirth_SetupOwnerIdle\n cmp #2\n beq GameplayBirth_SetupOwnerIdle\n jmp GameplayBirth_SetupBad\nGameplayBirth_SetupOwnerIdle:\n.a16\n.i16")
    _put(lines, f" lda.l {sy['SourceCtorState4086_Status']}\n cmp #3\n bne GameplayBirth_SetupStateGood\n jmp GameplayBirth_SetupBad\nGameplayBirth_SetupStateGood:\n.a16\n.i16")
    model = profile["model_id"]
    _put(lines, f" lda #${model:04X}\n sta.l {sy['SourceSpawnSlot4086_Model']}")
    for field, value in (("X", p["x_q16"]), ("Z", p["z_q16"]),
                         ("A", 0), ("Direction", p["flip"])):
        _put(lines, f" lda #${value & 0xFFFF:04X}\n sta.l {sy['SourceCtorState4086_'+field]}\n lda #${(value >> 16) & 0xFFFF:04X}\n sta.l {sy['SourceCtorState4086_'+field]}+2")
    _put(lines, f" lda #0\n sta.l {sy['SourceCtorState4086_Player']}\n sta.l {sy['SourceCtorState4086_Player']}+2")
    for target in ("SourceCtorState4086_Time", "SourceDefaultChoice4086_TimeLo",
                   "SourceDefaultPlayer4086_TimeLo"):
        _put(lines, f" lda.l {sy['VmSourceWorld_Time']}\n sta.l {sy[target]}\n lda.l {sy['VmSourceWorld_Time']}+2\n sta.l {sy[target.replace('TimeLo','TimeHi')]}" if target.endswith("TimeLo") else f" lda.l {sy['VmSourceWorld_Time']}\n sta.l {sy[target]}\n lda.l {sy['VmSourceWorld_Time']}+2\n sta.l {sy[target]}+2")
    _put(lines, f" lda #0\n sta.l {sy['SourceDefaultChoice4086_Select']}")
    # Begin distinguishes a new request from the previous preview's completed
    # phase 2. The real owner accepts phase 2 and performs a fresh slot choice.
    _put(lines, f" lda #{profile['walk_animation_id']}\n jsl {sy['SourceCtorOwner4086_Begin']}\n bcs GameplayBirth_SetupBad\n cmp #0\n beq GameplayBirth_SetupResult\n cmp #1\n beq GameplayBirth_SetupPendingReturn\n jmp GameplayBirth_SetupBad\nGameplayBirth_SetupResult:\n.a16\n.i16\n jsl {sy['SourceCtorOwner4086_Result']}\n bcs GameplayBirth_SetupBad\n lda #0\n bra GameplayBirth_SetupReturn\nGameplayBirth_SetupPendingReturn:\n.a16\n.i16\n lda #1\nGameplayBirth_SetupReturn:\n.a16\n.i16\n ply\n plx\n plp\n clc\n rtl\nGameplayBirth_SetupBad:\n.a16\n.i16\n lda #0\n ply\n plx\n plp\n sec\n rtl")
    return "\n".join(lines) + "\n"


def emit_run(sy, *, walk_animation_id, handoff_ready_address,
             handoff_phase_address, handoff_ready=0xB6E1, birth_pending=4,
             frame_owner_label="SourceFrameOwner4086_Run",
             lease_generation=1, lease_epoch=0):
    """Emit an A0-complete/A1-pending/C-fault constructor service driver.

    Called only after Setup returned pending. It does not synthesize frame ACKs.
    Actual frame execution and any external
    event remain under SourceFrameOwner and the caller's event service. The
    source constructor's Result entry is the sole result publisher.
    """
    if not 0 <= walk_animation_id <= 1024:
        raise ValueError("GAMEPLAY_BIRTH_WALK_ID")
    required = ("SourceForeignWork_Check", "SourceCtorOwner4086_Phase",
                "SourceCtorOwner4086_Continue", "SourceCtorOwner4086_Result",
                "SourceAnimationInit4086_Issued", "SourceAnimationInit4086_StartFrame",
                "VmSourceWorld_Time", "SourceCtorState4086_Time",
                "SourceDefaultChoice4086_TimeLo", "SourceDefaultChoice4086_TimeHi",
                "SourceDefaultPlayer4086_TimeLo", "SourceDefaultPlayer4086_TimeHi")
    absent = [name for name in required if name not in sy]
    if absent:
        raise ValueError("GAMEPLAY_BIRTH_SYMBOLS_MISSING:" + ",".join(absent))
    lines = []
    _put(lines, "GameplayBirth_Run:\n.a16\n.i16\n php\n rep #$38\n phx\n phy")
    _put(lines, f" phx\n phy\n ldx #{lease_generation}\n ldy #{lease_epoch}\n jsl {sy['SourceForeignWork_Check']}\n ply\n plx\n bcc GameplayBirth_RunLeaseOk\n jmp GameplayBirth_RunFault\nGameplayBirth_RunLeaseOk:\n.a16\n.i16")
    _put(lines, f" lda.l ${handoff_ready_address:06X}\n cmp #${handoff_ready:04X}\n beq GameplayBirth_RunReady\n jmp GameplayBirth_RunFault\nGameplayBirth_RunReady:\n.a16\n.i16")
    _put(lines, f" lda.l ${handoff_phase_address:06X}\n cmp #{birth_pending}\n beq GameplayBirth_RunPending\n jmp GameplayBirth_RunFault\nGameplayBirth_RunPending:\n.a16\n.i16")
    _put(lines, f" lda.l {sy['SourceCtorOwner4086_Phase']}\n cmp #1\n beq GameplayBirth_RunService\n cmp #2\n beq GameplayBirth_RunCompleteReturn\n jmp GameplayBirth_RunFault\nGameplayBirth_RunService:\n.a16\n.i16")
    _put(lines, f" lda.l {sy['SourceAnimationInit4086_Issued']}\n cmp #1\n beq GameplayBirth_RunFrame\n jsl {sy['SourceAnimationInit4086_StartFrame']}\n bcs GameplayBirth_RunFault")
    _put(lines, "GameplayBirth_RunFrame:\n.a16\n.i16")
    _put(lines, f" jsl {frame_owner_label}\n bcs GameplayBirth_RunFault\n cmp #0\n beq GameplayBirth_RunContinue\n cmp #$8001\n beq GameplayBirth_RunPendingReturn\n jmp GameplayBirth_RunPendingReturn")
    _put(lines, "GameplayBirth_RunContinue:\n.a16\n.i16")
    # SourceCtorOwner's contract requires B503 time and stage context to be
    # republished before each Continue. X/Y remain the checked stage context.
    _put(lines, f" lda.l {sy['VmSourceWorld_Time']}\n sta.l {sy['SourceCtorState4086_Time']}\n sta.l {sy['SourceDefaultChoice4086_TimeLo']}\n sta.l {sy['SourceDefaultPlayer4086_TimeLo']}\n lda.l {sy['VmSourceWorld_Time']}+2\n sta.l {sy['SourceCtorState4086_Time']}+2\n sta.l {sy['SourceDefaultChoice4086_TimeHi']}\n sta.l {sy['SourceDefaultPlayer4086_TimeHi']}\n jsl {sy['SourceCtorOwner4086_Continue']}\n bcs GameplayBirth_RunFault\n cmp #0\n beq GameplayBirth_RunPublish\n cmp #1\n beq GameplayBirth_RunPendingReturn\n jmp GameplayBirth_RunFault")
    _put(lines, f"GameplayBirth_RunPublish:\n.a16\n.i16\n jsl {sy['SourceCtorOwner4086_Result']}\n bcs GameplayBirth_RunFault\n lda #0\n bra GameplayBirth_RunReturn\nGameplayBirth_RunCompleteReturn:\n.a16\n.i16\n lda #0\n bra GameplayBirth_RunReturn\nGameplayBirth_RunPendingReturn:\n.a16\n.i16\n lda #1\n bra GameplayBirth_RunReturn\nGameplayBirth_RunFault:\n.a16\n.i16\n lda #0")
    _put(lines, "GameplayBirth_RunReturn:\n.a16\n.i16\n ply\n plx\n plp\n ; Keep all entry flags except provider carry.\n clc\n rtl")
    # Carry fault is emitted separately so it cannot be lost to the common clc.
    # The fault path restores saved context and then returns with C=1.
    fault = lines.index("GameplayBirth_RunFault:")
    return_text = "\n".join(lines)
    return_text = return_text.replace("GameplayBirth_RunFault:\n.a16\n.i16\n lda #0\nGameplayBirth_RunReturn:",
                                      "GameplayBirth_RunFault:\n.a16\n.i16\n lda #0\n ply\n plx\n plp\n sec\n rtl\nGameplayBirth_RunReturn:")
    return return_text + "\n"


def emit(profile, sy, *, handoff_ready_address, handoff_phase_address,
         handoff_ready=0xB6E1, birth_pending=4,
         frame_owner_label="SourceFrameOwner4086_Run",
         lease_generation=1, lease_epoch=0):
    return emit_setup(profile, sy, handoff_ready_address=handoff_ready_address,
                      handoff_phase_address=handoff_phase_address,
                      handoff_ready=handoff_ready, birth_pending=birth_pending,
                      lease_generation=lease_generation, lease_epoch=lease_epoch) + emit_run(
        sy, walk_animation_id=profile["walk_animation_id"],
        handoff_ready_address=handoff_ready_address,
        handoff_phase_address=handoff_phase_address,
        handoff_ready=handoff_ready, birth_pending=birth_pending,
        frame_owner_label=frame_owner_label, lease_generation=lease_generation,
        lease_epoch=lease_epoch)
