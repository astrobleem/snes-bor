"""Native selector -> source retirement -> fresh gameplay birth bridge.

The bridge owns one 64-byte control row in the audited retired-video gap
``[7E7900,7E7940)``.  It delegates selector policy to
``SourceSelectorLifecycle_*``, retirement to ``SourceRetirement4086`` and
birth to ``GameplayBirth_*``.  No actor-name or debug-time behavior exists.

The logical play-level clock is rebased to zero once, only after retirement
and before the source constructor. Physical SourceClock field/short counters,
last-observation snapshot, phase and hardware NMI/audio state are retained;
``SourceClock4086_Start`` is deliberately never called here because it clears
that observation state. While constructor work is pending, this bridge does
not run SourceWorldTick/LiveTick or manufacture any frame result.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

from source_player_input_4086 import NEWKEYS, PLAYKEYS, ROW_BYTES


CONTROL = 0x7E7900
CONTROL_BYTES = 64
SELECTOR_CONTROL = 0x7E79F0
SELECTOR_CONTROL_BYTES = 14
HANDOFF_MAGIC = 0xB6E4
BIRTH_ADAPTER_MAGIC = 0xB6E1
GENERATION = 1

STATE_SELECTOR = 0
STATE_BIRTH_PENDING = 1
STATE_GAMEPLAY = 2
STATE_FAULT = 3

# Control ABI (little-endian words).
OFF_MAGIC = 0
OFF_STATE = 2
OFF_BUSY = 4
OFF_RESULT = 6
OFF_SELECTOR_STATUS = 8
OFF_GENERATION = 10
OFF_BIRTH_STARTED = 12
OFF_RESERVED = 14
OFF_BIRTH_READY = 16
OFF_BIRTH_PHASE = 18
OFF_LAST_TICK = 20

ACTOR_BASE = 0x414000
ACTOR_BYTES = 80
ACTOR_ALIVE = ACTOR_BASE + 4
ANIMATING = 0x41F510
HISTORY_BASE = 0x7FA000
HISTORY_BYTES = 4 * ROW_BYTES
VM_RUN_BUSY = 0x7FFB32
LIVE_ROLE_COUNT_EXPECTED = 1
STAGE_X = 0x8000
STAGE_Y = 0x003A  # Source fixture emits decimal `ldy #58`.


def _address(value, name):
    if isinstance(value, bool):
        raise ValueError("SELECTOR_HANDOFF_ADDRESS:" + name)
    if isinstance(value, int):
        address = value
    elif isinstance(value, str) and re.fullmatch(r"(?:\$|0x)?[0-9A-Fa-f]{1,6}", value):
        address = int(value.lstrip("$"), 16) if value.startswith("$") else int(value, 0)
    else:
        raise ValueError("SELECTOR_HANDOFF_ADDRESS:" + name)
    if not 0 <= address <= 0xFFFFFF:
        raise ValueError("SELECTOR_HANDOFF_ADDRESS:" + name)
    return address


def _target(value, name):
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 0xFFFFFF:
        return f"${value:06X}"
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z_]\w*", value):
        return value
    raise ValueError("SELECTOR_HANDOFF_TARGET:" + name)


def derive_jump_id(source, *, model_name="He_Man"):
    """Derive the source engine's JUMP animation ID from loaded model config."""
    from source_profile import document, discover
    from source_animation_ids import configure, role_id

    docs = {k: document(source, name) for k, (name, _) in source.index.items()
            if k.endswith(".txt")}
    structure = discover(source, docs)
    rows = [m for m in structure["models"]
            if m["declaration"].casefold() == model_name.casefold()]
    if len(rows) != 1:
        raise ValueError("SELECTOR_HANDOFF_MODEL_IDENTITY")
    model = rows[0]
    models_doc = docs[next(k for k in docs
                           if k.casefold() == structure["models_path"].casefold())]
    config = configure(models_doc["directives"])
    jump = role_id(config, "jump")
    if not 0 <= jump <= 1024:
        raise ValueError("SELECTOR_HANDOFF_JUMP_ID")
    return dict(model_name=model["declaration"], model_source_path=model["source_path"],
                jump_animation_id=jump, authority="source_animation_ids.role_id(config,'jump')")


def validate_layout(*, control=CONTROL, selector_control=SELECTOR_CONTROL,
                    history_base=HISTORY_BASE):
    if control != CONTROL or control & 1 or control + CONTROL_BYTES > SELECTOR_CONTROL:
        raise ValueError("SELECTOR_HANDOFF_CONTROL_LEASE")
    if selector_control != SELECTOR_CONTROL or selector_control & 1:
        raise ValueError("SELECTOR_HANDOFF_SELECTOR_LEASE")
    if history_base != HISTORY_BASE or history_base & 0xFF:
        raise ValueError("SELECTOR_HANDOFF_HISTORY_LEASE")
    spans = ((control, control + CONTROL_BYTES),
             (selector_control, selector_control + SELECTOR_CONTROL_BYTES),
             (0x7E7680, 0x7E7700),       # health extension
             (0x7E7700, 0x7E7718),       # live-tick work
             (0x7E7800, 0x7E7894),       # sealed snapshot
             (0x7E7A00, 0x7E7C00),       # binding rows
             (0x7E7C00, 0x7E8040),       # movement/contact rows+controls
             (0x7E8080, 0x7E80E0),       # flat movement work
             (0x7E8100, 0x7E8340),       # live audio
             (0x7E8340, 0x7E9A60),       # warm presentation lease
             (history_base, history_base + HISTORY_BYTES))
    owned = spans[0]
    for span in spans[1:]:
        if owned[0] < span[1] and span[0] < owned[1]:
            raise ValueError("SELECTOR_HANDOFF_LAYOUT_OVERLAP")
    if history_base + HISTORY_BYTES > 0x1000000:
        raise ValueError("SELECTOR_HANDOFF_HISTORY_EXTENT")
    return dict(control=[control, control + CONTROL_BYTES],
                selector=[selector_control, selector_control + SELECTOR_CONTROL_BYTES],
                history=[history_base, history_base + HISTORY_BYTES])


def _required(symbols):
    names = (
        "SourceForeignWork_Check",
        "SourceClock4086_Ready", "SourceClock4086_Due", "SourceClock4086_TimeLo",
        "SourceWorldTick4086_Ready", "SourceWorldTick4086_State",
        "SourceWorldTick4086_Pending", "SourceWorldTick4086_TimeLo",
        "VmSourceWorld_Ready", "VmSourceWorld_Level",
        "VmSourceWorld_Time", "VmSourceInput_Tick",
        "VmSourceCallback_Active",
        "SourceUpdateFrame4086_CheckIdle", "SourceAnimationInit4086_CheckIdle",
        "SourceSelf4086_CheckIdle",
        "SourceRetirement4086_Status", "SourceRetirement4086_Slot",
        "SourceRetirement4086_ApplyNoEvents",
        "SourceDefaultInit4086_OwnerSlot", "VmNativeVariant_Result",
        "SourceDefaultPlayer4086_Ready", "SourceDefaultPlayer4086_Jump",
        "SourceCtorOwner4086_Phase", "SourceSpawnSlot4086_Ready",
        "SourceSpawnSlot4086_Model", "SourceDefaultChoice4086_Ready",
        "SourceDefaultChoice4086_Select", "SourceCtorState4086_Ready",
    )
    if not isinstance(symbols, Mapping):
        raise ValueError("SELECTOR_HANDOFF_SYMBOL_MAP")
    absent = [name for name in names if name not in symbols]
    if absent:
        raise ValueError("SELECTOR_HANDOFF_SYMBOLS_MISSING:" + ",".join(absent))
    return {name: _address(symbols[name], name) for name in names}


def emit(symbols, profile, *, tick_service="LiveTick_Service",
         control=CONTROL, selector_control=SELECTOR_CONTROL,
         history_base=HISTORY_BASE, stage_x=STAGE_X, stage_y=STAGE_Y,
         lease_generation=GENERATION, lease_epoch=0,
         retirement_initializer=None, retirement_birth=None):
    """Emit Motion_Init, Motion_Input and MotionTick_Service.

    ``profile`` is the source-derived gameplay-birth profile plus
    ``jump_animation_id`` from :func:`derive_jump_id`. The caller concatenates
    this fragment with the existing selector and gameplay-birth emitters.

    Result ABI: Motion_Input returns the actual selector status with C clear;
    unsupported navigation/escape remain statuses 5/6. MotionTick_Service
    returns 0=no due, 1=real provider/constructor pending, 2=one real tick
    committed (or constructor completed), C=1=fault. X/Y/DP/DBR/SP and P
    except carry are preserved.
    """
    sy = _required(symbols)
    layout = validate_layout(control=control, selector_control=selector_control,
                             history_base=history_base)
    tick_service = _target(tick_service, "LiveTick_Service")
    if (retirement_initializer is None) != (retirement_birth is None):
        raise ValueError("SELECTOR_HANDOFF_RETIREMENT_HOOK_PAIR")
    if retirement_initializer is not None:
        retirement_initializer = _target(retirement_initializer, "retirement initializer")
        retirement_birth = _target(retirement_birth, "retirement birth metadata")
    if not isinstance(profile, Mapping) or profile.get("schema") != "BYOR_SOURCE_GAMEPLAY_BIRTH_V1":
        raise ValueError("SELECTOR_HANDOFF_PROFILE_SCHEMA")
    if (profile.get("model_id") != 3
            or not isinstance(profile.get("stage_id"), int)
            or isinstance(profile.get("stage_id"), bool)
            or profile.get("stage_id") < 0
            or str(profile.get("model_name", "")).casefold() != "he_man"
            or str(profile.get("stage_path", "")).replace("\\", "/").casefold()
               != "data/levels/guile2.txt"
            or profile.get("uses_source_ctor_owner") is not True
            or profile.get("runtime_birth_proven") is not False
            or profile.get("absent_initial_roles") != []):
        raise ValueError("SELECTOR_HANDOFF_PROFILE_POLICY")
    jump_id = profile.get("jump_animation_id")
    if isinstance(jump_id, bool) or not isinstance(jump_id, int) or not 0 <= jump_id <= 1024:
        raise ValueError("SELECTOR_HANDOFF_JUMP_PROFILE")
    if (isinstance(stage_x, bool) or not isinstance(stage_x, int) or stage_x != STAGE_X
            or isinstance(stage_y, bool) or not isinstance(stage_y, int) or stage_y != STAGE_Y):
        raise ValueError("SELECTOR_HANDOFF_STAGE_CONTEXT")
    if lease_generation != GENERATION or lease_epoch != 0:
        raise ValueError("SELECTOR_HANDOFF_FOREIGN_EPOCH")

    # Source input history row fields are uint32 at canonical per-player offsets.
    history = layout["history"][0]
    phase = selector_control + 2
    code = [".a16", ".i16"]

    def put(*rows):
        code.extend(rows)

    def label(name):
        put(name + ":", ".a16", ".i16")

    serial = [0]
    def guard(op, target):
        serial[0] += 1
        skip = f"Motion_Guard{serial[0]}"
        inverse = {"beq": "bne", "bne": "beq", "bcc": "bcs", "bcs": "bcc"}[op]
        put(f" {inverse} {skip}", f" jmp {target}", skip + ":", ".a16", ".i16")

    def require(address, value, fail="Motion_FaultOwned"):
        serial[0] += 1
        good = f"Motion_RequireOk{serial[0]}"
        put(f" lda.l ${address:06X}", f" cmp #${value:04X}")
        guard("beq", good)
        put(f" jmp {fail}")
        label(good)

    def leasecheck(fail="Motion_FaultOwned"):
        serial[0] += 1
        ok = f"Motion_LeaseOk{serial[0]}"
        put(f" ldx #${lease_generation:04X}", f" ldy #${lease_epoch:04X}",
            f" jsl ${sy['SourceForeignWork_Check']:06X}")
        guard("bcc", ok)
        put(f" jmp {fail}")
        label(ok)

    def prologue(entry):
        label(entry)
        put(" php", " rep #$38", " phx", " phy", " phb", " phd",
            " sep #$20", ".a8", " lda #0", " pha", " plb",
            " rep #$20", ".a16", " lda #0", " tcd")

    def exit_good(result_address):
        put(f" lda.l ${result_address:06X}", " pld", " plb", " ply", " plx", " plp", " clc", " rtl")

    def exit_bad(result_address):
        put(f" lda.l ${result_address:06X}", " pld", " plb", " ply", " plx", " plp", " sec", " rtl")

    # Bootstrap must arrive with the 64-byte extension actually cleared by
    # LiveWorld acquisition. Reject any stale byte rather than silently reset.
    prologue("Motion_Init")
    leasecheck("Motion_FaultUnowned")
    put(" ldx #0")
    label("Motion_InitClearScan")
    put(f" lda.l ${control:06X},x")
    guard("beq", "Motion_InitClearNext")
    put(" jmp Motion_FaultUnowned")
    label("Motion_InitClearNext")
    put(" inx", " inx", f" cpx #${CONTROL_BYTES:04X}")
    guard("bne", "Motion_InitClearScan")
    put(f" lda.l ${selector_control:06X}")
    guard("beq", "Motion_InitSelectorClear")
    put(" jmp Motion_FaultUnowned")
    label("Motion_InitSelectorClear")
    for address, value in ((sy["SourceClock4086_Ready"], 0xB4C5),
                           (sy["SourceWorldTick4086_Ready"], 0xB4D5),
                           (sy["VmSourceWorld_Ready"], 0xB4A3)):
        require(address, value)
    for address in (sy["SourceClock4086_Due"], sy["SourceWorldTick4086_State"],
                    sy["SourceWorldTick4086_Pending"], sy["VmSourceCallback_Active"],
                    VM_RUN_BUSY):
        require(address, 0)
    require(sy["VmSourceWorld_Level"], 1)
    require(0x43FD80, LIVE_ROLE_COUNT_EXPECTED)
    put(f" lda.l ${ACTOR_ALIVE:06X}", " cmp #1")
    guard("beq", "Motion_InitPreviewLive")
    put(" jmp Motion_FaultOwned")
    label("Motion_InitPreviewLive")
    if retirement_initializer is not None:
        put(f" jsl {retirement_initializer}")
        guard("bcs", "Motion_FaultOwned")
    put(" jsl SourceSelectorLifecycle_Init")
    guard("bcc", "Motion_InitSelectorGood")
    put(" jmp Motion_FaultOwned")
    label("Motion_InitSelectorGood")
    put(f" lda #${HANDOFF_MAGIC:04X}", f" sta.l ${control+OFF_MAGIC:06X}",
        f" lda #${STATE_SELECTOR:04X}", f" sta.l ${control+OFF_STATE:06X}",
        f" lda #${GENERATION:04X}", f" sta.l ${control+OFF_GENERATION:06X}",
        " lda #0", f" sta.l ${control+OFF_BUSY:06X}", f" sta.l ${control+OFF_RESULT:06X}",
        f" sta.l ${control+OFF_SELECTOR_STATUS:06X}", f" sta.l ${control+OFF_BIRTH_STARTED:06X}",
        " lda #0", f" sta.l ${control+OFF_BIRTH_READY:06X}",
        f" sta.l ${control+OFF_BIRTH_PHASE:06X}", f" sta.l ${control+OFF_LAST_TICK:06X}")
    put(" lda #0", f" sta.l ${control+OFF_RESULT:06X}")
    exit_good(control + OFF_RESULT)

    # Outer-input hook: the real immutable snapshot/history are already fresh.
    # It only calls the source selector while preview state owns this phase.
    prologue("Motion_Input")
    leasecheck()
    require(control + OFF_MAGIC, HANDOFF_MAGIC, "Motion_FaultUnowned")
    require(control + OFF_GENERATION, GENERATION)
    # This is the fresh-input hook called from inside LiveTick_Service, after
    # MotionTick_Service has claimed the owner busy bit.
    require(control + OFF_BUSY, 1)
    put(f" lda.l ${control+OFF_STATE:06X}", f" cmp #${STATE_SELECTOR:04X}")
    guard("beq", "Motion_InputSelector")
    put(f" cmp #${STATE_BIRTH_PENDING:04X}")
    guard("beq", "Motion_InputNoop")
    put(f" cmp #${STATE_GAMEPLAY:04X}")
    guard("beq", "Motion_InputNoop")
    put(" jmp Motion_FaultOwned")
    label("Motion_InputSelector")
    put(f" lda.l ${ACTOR_ALIVE:06X}", " cmp #0")
    guard("beq", "Motion_InputDead")
    put(" cmp #1")
    guard("beq", "Motion_InputLive")
    put(" jmp Motion_FaultOwned")
    label("Motion_InputDead")
    put(" lda #0")
    guard("beq", "Motion_InputCallSelector")
    label("Motion_InputLive")
    put(f" lda.l ${ANIMATING:06X}", " beq Motion_InputNotAnimating", " lda #1", " bra Motion_InputAnimReady",
        "Motion_InputNotAnimating:", ".a16", ".i16", " lda #0", "Motion_InputAnimReady:", ".a16", ".i16",
        " ora #2")
    label("Motion_InputCallSelector")
    put(" jsl SourceSelectorLifecycle_Run")
    guard("bcs", "Motion_FaultOwned")
    put(f" sta.l ${control+OFF_SELECTOR_STATUS:06X}", f" sta.l ${control+OFF_RESULT:06X}")
    exit_good(control + OFF_RESULT)
    label("Motion_InputNoop")
    put(" lda #0", f" sta.l ${control+OFF_RESULT:06X}")
    exit_good(control + OFF_RESULT)

    # Single-tick/birth state service. LiveTick owns all normal selector and
    # gameplay clock/input/world writes. Birth is polled only in state 1.
    prologue("MotionTick_Service")
    leasecheck("Motion_FaultUnowned")
    require(control + OFF_MAGIC, HANDOFF_MAGIC, "Motion_FaultUnowned")
    require(control + OFF_GENERATION, GENERATION)
    require(control + OFF_BUSY, 0)
    put(" lda #1", f" sta.l ${control+OFF_BUSY:06X}",
        f" lda.l ${control+OFF_STATE:06X}", f" cmp #${STATE_SELECTOR:04X}")
    guard("beq", "Motion_TickLive")
    put(f" cmp #${STATE_GAMEPLAY:04X}")
    guard("beq", "Motion_TickLive")
    put(f" cmp #${STATE_BIRTH_PENDING:04X}")
    guard("beq", "Motion_BirthService")
    put(" jmp Motion_FaultOwned")

    label("Motion_TickLive")
    put(f" jsl {tick_service}")
    guard("bcs", "Motion_FaultOwned")
    put(f" sta.l ${control+OFF_RESULT:06X}", f" sta.l ${control+OFF_LAST_TICK:06X}",
        " cmp #2")
    guard("beq", "Motion_AfterLiveCommit")
    put(" jmp Motion_ReturnGood")
    label("Motion_AfterLiveCommit")
    put(f" lda.l ${control+OFF_STATE:06X}", f" cmp #${STATE_SELECTOR:04X}")
    guard("bne", "Motion_ReturnGood")
    put(f" lda.l ${selector_control+2:06X}", " cmp #3")
    guard("beq", "Motion_RetirePreview")
    put(" jmp Motion_ReturnGood")

    label("Motion_RetirePreview")
    for address in (sy["SourceClock4086_Due"], sy["SourceWorldTick4086_State"],
                    sy["SourceWorldTick4086_Pending"], sy["VmSourceCallback_Active"],
                    VM_RUN_BUSY):
        require(address, 0)
    # Idle validators are the callable source proof for frame, animation and
    # source-self execution state; a code label is never read as mutable data.
    for index, name in enumerate(("SourceUpdateFrame4086_CheckIdle",
                                  "SourceAnimationInit4086_CheckIdle",
                                  "SourceSelf4086_CheckIdle")):
        idle_good = f"Motion_RetireIdleGood{index}"
        put(f" jsl ${sy[name]:06X}")
        guard("bcc", idle_good)
        put(" jmp Motion_FaultOwned")
        label(idle_good)
    put(f" lda.l ${sy['SourceRetirement4086_Status']:06X}", " cmp #0")
    guard("beq", "Motion_RetireStatusGood")
    put(" cmp #2")
    guard("beq", "Motion_RetireStatusGood")
    put(" jmp Motion_FaultOwned")
    label("Motion_RetireStatusGood")
    put(" lda #0", f" sta.l ${sy['SourceRetirement4086_Slot']:06X}",
        f" jsl ${sy['SourceRetirement4086_ApplyNoEvents']:06X}")
    guard("bcc", "Motion_RetireApplied")
    put(" jmp Motion_FaultOwned")
    label("Motion_RetireApplied")
    require(sy["SourceRetirement4086_Status"], 2)
    require(0x43FD80, 0)
    put(f" lda.l ${ACTOR_ALIVE:06X}", " cmp #0")
    guard("beq", "Motion_RetiredDead")
    put(" jmp Motion_FaultOwned")
    label("Motion_RetiredDead")
    # The live-role count is now zero; the physical pool retains its fixed
    # capacity and is never mistaken for a one-entry allocation.
    require(0x43FD80, 0)
    # The lifecycle phase is authoritative history. A completed selector
    # exit reaches retirement only from phase 3; preserve that phase so the
    # real SourceSelectorLifecycle_Run observes preview_live=0 and advances
    # to phase 4. Clearing it here incorrectly sends the source owner back to
    # WAIT_ACCEPT, where a dead preview is an invalid input state.
    require(selector_control + 2, 3)
    put(" lda #0", " jsl SourceSelectorLifecycle_Run")
    guard("bcs", "Motion_FaultOwned")
    put(" cmp #4")
    guard("beq", "Motion_BirthPendingPublish")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthPendingPublish")
    put(f" lda #${STATE_BIRTH_PENDING:04X}", f" sta.l ${control+OFF_STATE:06X}",
        " lda #0", f" sta.l ${control+OFF_BIRTH_STARTED:06X}",
        f" sta.l ${control+OFF_RESULT:06X}")
    put(" lda #2", f" sta.l ${control+OFF_RESULT:06X}")
    put(" jmp Motion_ReturnGood")

    label("Motion_BirthService")
    for address, value in ((sy["SourceClock4086_Ready"], 0xB4C5),
                           (sy["SourceWorldTick4086_Ready"], 0xB4D5),
                           (sy["VmSourceWorld_Ready"], 0xB4A3),
                           (sy["SourceDefaultPlayer4086_Ready"], 0xB503),
                           (sy["SourceDefaultChoice4086_Ready"], 0xB4FA),
                           (sy["SourceCtorState4086_Ready"], 0xB5C2),
                           (sy["SourceSpawnSlot4086_Ready"], 0xB5A1)):
        require(address, value)
    for address in (sy["SourceClock4086_Due"], sy["SourceWorldTick4086_State"],
                    sy["SourceWorldTick4086_Pending"], sy["VmSourceCallback_Active"],
                    VM_RUN_BUSY):
        require(address, 0)
    # Before Setup has started, the actor slot must still be dead. A successful
    # SourceCtorOwner Begin may publish the real actor before returning A=1;
    # its later service is valid only with the started marker, a live slot, and
    # the constructor owner still in its explicit pending phase.
    put(f" lda.l ${control+OFF_BIRTH_STARTED:06X}", " cmp #0")
    guard("beq", "Motion_BirthNotStarted")
    put(" cmp #1")
    guard("beq", "Motion_BirthWasStarted")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthNotStarted")
    put(f" lda.l ${ACTOR_ALIVE:06X}", " cmp #0")
    guard("beq", "Motion_BirthBegin")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthWasStarted")
    put(f" lda.l ${ACTOR_ALIVE:06X}", " cmp #1")
    guard("beq", "Motion_BirthActorPublished")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthActorPublished")
    put(f" lda.l ${sy['SourceCtorOwner4086_Phase']:06X}", " cmp #1")
    guard("beq", "Motion_BirthContinue")
    put(" jmp Motion_FaultOwned")

    # The bounded play-level entry preserves absolute field observations: only
    # the logical time words and input-edge words are reset, after all debt and
    # source ticks are idle. The next real Observe catches up from LastFields.
    label("Motion_BirthBegin")
    # A completed tick commits world/input time T first, then the source clock
    # advances to T+1. Validate both pairs and that exact post-commit boundary
    # before rebasing; compare per word so CMP does not destroy ADC's carry.
    clock = sy["SourceClock4086_TimeLo"]
    world = sy["VmSourceWorld_Time"]
    tick = sy["SourceWorldTick4086_TimeLo"]
    input_tick = sy["VmSourceInput_Tick"]
    for index, (left, right) in enumerate(((clock, world), (tick, input_tick))):
        low_equal = f"Motion_BirthPairLowEqual{index}"
        high_equal = f"Motion_BirthPairHighEqual{index}"
        put(f" lda.l ${left:06X}", f" cmp.l ${right:06X}")
        guard("beq", low_equal)
        put(" jmp Motion_FaultOwned")
        label(low_equal)
        put(f" lda.l ${left+2:06X}", f" cmp.l ${right+2:06X}")
        guard("beq", high_equal)
        put(" jmp Motion_FaultOwned")
        label(high_equal)
    # Compute T+1 in X:Y before comparing either half. ADC's carry from the
    # low word is retained into the high word; wrap from FFFFFFFF to 0 is valid.
    put(f" clc", f" lda.l ${tick:06X}", " adc #1", " tax",
        f" lda.l ${tick+2:06X}", " adc #0", " tay",
        " txa", f" cmp.l ${clock:06X}")
    guard("beq", "Motion_BirthClockLowGood")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthClockLowGood")
    put(" tya", f" cmp.l ${clock+2:06X}")
    guard("beq", "Motion_BirthClockBoundaryGood")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthClockBoundaryGood")
    for time_address in (sy["SourceClock4086_TimeLo"], sy["VmSourceWorld_Time"],
                         sy["SourceWorldTick4086_TimeLo"], sy["VmSourceInput_Tick"]):
        put(" lda #0", f" sta.l ${time_address:06X}", f" sta.l ${time_address+2:06X}")
    put(" lda #0",
        f" sta.l ${history+NEWKEYS:06X}", f" sta.l ${history+NEWKEYS+2:06X}",
        f" sta.l ${history+PLAYKEYS:06X}", f" sta.l ${history+PLAYKEYS+2:06X}",
        f" sta.l ${sy['SourceDefaultPlayer4086_Jump']:06X}")
    put(f" lda #${jump_id:04X}", f" sta.l ${sy['SourceDefaultPlayer4086_Jump']:06X}",
        f" lda #${BIRTH_ADAPTER_MAGIC:04X}", f" sta.l ${control+OFF_BIRTH_READY:06X}",
        " lda #4", f" sta.l ${control+OFF_BIRTH_PHASE:06X}",
        f" ldx #${stage_x:04X}", f" ldy #${stage_y:04X}",
        " jsl GameplayBirth_Setup")
    guard("bcs", "Motion_FaultOwned")
    put(" cmp #0")
    guard("beq", "Motion_BirthVerify")
    put(" cmp #1")
    guard("beq", "Motion_BirthStarted")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthStarted")
    put(" lda #1", f" sta.l ${control+OFF_BIRTH_STARTED:06X}",
        " lda #1", f" sta.l ${control+OFF_RESULT:06X}", " jmp Motion_ReturnGood")

    label("Motion_BirthContinue")
    put(f" lda #${jump_id:04X}", f" sta.l ${sy['SourceDefaultPlayer4086_Jump']:06X}",
        f" ldx #${stage_x:04X}", f" ldy #${stage_y:04X}", " jsl GameplayBirth_Run")
    guard("bcs", "Motion_FaultOwned")
    put(" cmp #0")
    guard("beq", "Motion_BirthVerify")
    put(" cmp #1")
    guard("beq", "Motion_BirthStillPending")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthStillPending")
    put(" lda #1", f" sta.l ${control+OFF_RESULT:06X}", " jmp Motion_ReturnGood")

    # A birth publishes gameplay ownership only when the real constructor's
    # result phase is complete and its selected slot is exactly player slot 0.
    label("Motion_BirthVerify")
    put(f" lda.l ${sy['SourceCtorOwner4086_Phase']:06X}", " cmp #2")
    guard("beq", "Motion_BirthPhaseComplete")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthPhaseComplete")
    put(f" lda.l ${sy['SourceDefaultInit4086_OwnerSlot']:06X}", " cmp #0")
    guard("beq", "Motion_BirthCountGood")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthCountGood")
    put(f" lda.l ${ACTOR_ALIVE:06X}", " cmp #1")
    guard("beq", "Motion_BirthPublished")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthPublished")
    # `spawnplayer()` performs player[index].ent = smartspawn(&p) only after
    # the real constructor returns. SourceCtorOwner_Result has already
    # validated/published that actual return in VmNativeVariant_Result. Mirror
    # the post-return assignment into the checked retirement role map.
    put(f" lda.l ${sy['VmNativeVariant_Result']:06X}", " cmp #$0005")
    guard("beq", "Motion_BirthReturnTypeGood")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthReturnTypeGood")
    put(f" lda.l ${sy['VmNativeVariant_Result']+4:06X}", " cmp #$4000")
    guard("beq", "Motion_BirthTokenLowGood")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthTokenLowGood")
    put(f" lda.l ${sy['VmNativeVariant_Result']+6:06X}", " cmp #$0041")
    guard("beq", "Motion_BirthTokenHighGood")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthTokenHighGood")
    for address in (0x43FD82, 0x43FD84, 0x43FD86):
        require(address, 0)
    put(f" lda.l $43FD80", " cmp #1")
    guard("beq", "Motion_BirthRoleCountGood")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthRoleCountGood")
    put(" lda.l $41402C", " ora.l $41402E", " cmp #0")
    guard("beq", "Motion_BirthPlayerIndexGood")
    put(" jmp Motion_FaultOwned")
    label("Motion_BirthPlayerIndexGood")
    put(f" lda.l ${sy['VmNativeVariant_Result']+4:06X}", " sta.l $43FD84",
        f" lda.l ${sy['VmNativeVariant_Result']+6:06X}", " sta.l $43FD86")
    # This intentionally binds only player[0].ent from the actual returned
    # token and verifies the constructor's SourceCtorState_Player=0 publication
    # at entity.playerindex. The profile does not claim global
    # join/hasplayed/lives/weapnum or rush-reset state without canonical owners.
    if retirement_birth is not None:
        put(f" jsl {retirement_birth}")
        guard("bcs", "Motion_FaultOwned")
    put(f" lda #${STATE_GAMEPLAY:04X}", f" sta.l ${control+OFF_STATE:06X}",
        " lda #0", f" sta.l ${control+OFF_BIRTH_STARTED:06X}",
        f" sta.l ${control+OFF_RESULT:06X}", " lda #2",
        f" sta.l ${control+OFF_RESULT:06X}", " jmp Motion_ReturnGood")

    label("Motion_FaultOwned")
    put(f" lda #${STATE_FAULT:04X}", f" sta.l ${control+OFF_STATE:06X}",
        " lda #0", f" sta.l ${control+OFF_BUSY:06X}",
        f" sta.l ${control+OFF_RESULT:06X}", " lda #1",
        f" sta.l ${control+OFF_RESULT:06X}", " jmp Motion_ReturnFault")
    label("Motion_FaultUnowned")
    put(" lda #0", f" sta.l ${control+OFF_RESULT:06X}", " jmp Motion_ReturnFaultUnowned")
    label("Motion_ReturnGood")
    put(f" lda #0", f" sta.l ${control+OFF_BUSY:06X}")
    exit_good(control + OFF_RESULT)
    label("Motion_ReturnFault")
    exit_bad(control + OFF_RESULT)
    label("Motion_ReturnFaultUnowned")
    put(" pld", " plb", " ply", " plx", " plp", " sec", " rtl")

    return "\n".join(code) + "\n"
