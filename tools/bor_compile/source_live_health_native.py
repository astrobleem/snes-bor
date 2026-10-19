"""Pinned 4086 phase-9 health semantics and caller-owned row contract.

This module is the executable host oracle for the native leaf.  The native
backend supplies one record per live slot because several update_health
members (timers, guard state, MP mode/rates) are not present in the cached
model-core rows.  A pending result never mutates the record.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import MutableMapping


U32 = 0xFFFF_FFFF
I32_MIN = -0x8000_0000
I32_MAX = 0x7FFF_FFFF
ROW_FIELDS = (
    "health", "oldhealth", "mp", "oldmp", "maxmp", "mpstable",
    "mpstableval", "mprate", "mpdroprate", "chargerate", "mpswitch",
    "magic_type", "charging", "magictime", "mpchargetime",
    "guard_max", "guard_current", "guardrate", "blocking", "guardtime",
    "dot_active",
)
NATIVE_WORK_BYTES = 128
NATIVE_ROW_OFFSETS = {
    "ready": 0, "generation32": 4, "token32": 8, "source_profile_id": 12,
    "reserved": 14, "oldhealth_i32": 16, "oldmp_i32": 20,
    "dot_active_i32": 24,
}


class HealthFault(ValueError):
    """Malformed or stale ownership context; native result is C=1."""


@dataclass(frozen=True)
class HealthResult:
    status: str  # complete | pending | fault
    writes: tuple[str, ...] = ()
    reason: str = ""


def _u32(value: int) -> int:
    if type(value) is not int or not 0 <= value <= U32:
        raise HealthFault("HEALTH_U32_DOMAIN")
    return value


def _i32(value: int) -> int:
    if type(value) is not int or not I32_MIN <= value <= I32_MAX:
        raise HealthFault("HEALTH_I32_DOMAIN")
    return value


def _source_add(a: int, b: int) -> int:
    """Keep defined signed C arithmetic; overflow is not silently wrapped."""
    n = a + b
    if not I32_MIN <= n <= I32_MAX:
        raise HealthFault("HEALTH_SIGNED_OVERFLOW_UNMODELED")
    return n


def update_health(row: MutableMapping[str, int], *, now: int, game_speed: int,
                  ready: bool, world_state: int, phase: int, pending: int,
                  world_time: int, slot: int, live: bool, birth: int,
                  lifetime_end: int | None = None) -> HealthResult:
    """Apply phase 9 atomically to a caller-owned per-slot record.

    Preconditions mirror the dispatcher contract.  The world-time comparison
    is unsigned 32-bit. `lifetime_end`, when supplied, is an exclusive tick
    limit. No actor-name dispatch is performed.
    """
    now = _u32(now); world_time = _u32(world_time); birth = _u32(birth)
    if type(slot) is not int or not 0 <= slot < 128:
        raise HealthFault("HEALTH_SLOT_DOMAIN")
    if not ready or world_state != 1 or phase != 9 or pending != 1:
        raise HealthFault("HEALTH_WORLD_PHASE_GUARD")
    if now != world_time:
        raise HealthFault("HEALTH_WORLD_TIME_STALE")
    if not live:
        raise HealthFault("HEALTH_SLOT_NOT_LIVE")
    if birth == now:
        raise HealthFault("HEALTH_FRESH_BIRTH_EXCLUDED")
    if lifetime_end is not None:
        lifetime_end = _u32(lifetime_end)
        if now >= lifetime_end:
            raise HealthFault("HEALTH_LIFETIME_EXPIRED")
    if not isinstance(row, MutableMapping) or not set(ROW_FIELDS) <= set(row):
        raise HealthFault("HEALTH_ROW_INCOMPLETE")

    # DOT is an ordered source call. It must be completed before this leaf can
    # claim the phase; unknown active-DOT effects remain pending, write-free.
    if row["dot_active"]:
        return HealthResult("pending", reason="COMMON_DOT_NATIVE_PROVIDER_REQUIRED")

    s = {name: _i32(row[name]) for name in ROW_FIELDS if name not in
         ("magictime", "mpchargetime", "guardtime", "dot_active", "charging", "blocking",
          "magic_type")}
    s["magictime"] = _u32(row["magictime"])
    s["mpchargetime"] = _u32(row["mpchargetime"])
    s["guardtime"] = _u32(row["guardtime"])
    for flag in ("dot_active", "charging", "blocking"):
        if row[flag] not in (0, 1):
            raise HealthFault("HEALTH_FLAG_DOMAIN")
    if row["magic_type"] not in (0, 1, 2, 3, 4):
        raise HealthFault("HEALTH_MAGIC_TYPE_DOMAIN")
    if type(game_speed) is not int or not 1 <= game_speed <= 0x7FFF:
        raise HealthFault("HEALTH_GAME_SPEED_DOMAIN")
    if not 0 <= s["mpstable"] <= 4:
        raise HealthFault("HEALTH_MP_STABLE_DOMAIN")

    writes: dict[str, int] = {}
    if s["guard_max"] > 0 and now >= s["guardtime"]:
        rate = s["guardrate"]
        if row["blocking"]:
            rate = rate // 2 if rate >= 0 else -((-rate) // 2)
        current = _source_add(s["guard_current"], rate)
        writes["guard_current"] = min(current, s["guard_max"])
        writes["guardtime"] = (now + game_speed) & U32

    if row["magic_type"] == 0 and not row["charging"] and now >= s["magictime"]:
        mp = s["mp"]
        stable = s["mpstable"]
        if stable == 1 and mp < s["mpstableval"]:
            mp = _source_add(mp, s["mprate"])
        elif stable == 2 and mp > s["mpstableval"]:
            mp = _source_add(mp, -s["mpdroprate"])
        elif stable == 3:
            if mp < s["mpstableval"]:
                mp = _source_add(mp, s["mprate"])
            elif mp > s["mpstableval"]:
                mp = _source_add(mp, -s["mpdroprate"])
        elif stable == 4:
            switch = s["mpswitch"]
            if mp <= s["mpstableval"]:
                switch = 0
                writes["mpswitch"] = switch
            elif mp == s["maxmp"]:
                switch = 1
                writes["mpswitch"] = switch
            if switch == 1:
                mp = _source_add(mp, -s["mpdroprate"])
            elif switch == 0:
                mp = _source_add(mp, s["mprate"])
        else:  # mode 0 and invalid legacy values follow source's default arm
            mp = _source_add(mp, s["mprate"])
        writes["mp"] = min(mp, s["maxmp"])
        writes["magictime"] = (now + game_speed) & U32

    if row["charging"] and now >= s["mpchargetime"]:
        base_mp = writes.get("mp", s["mp"])
        writes["mp"] = min(_source_add(base_mp, s["chargerate"]), s["maxmp"])
        writes["mpchargetime"] = (now + game_speed // 4) & U32

    # update_health applies this ceiling after both timed regen and charging,
    # even when neither timer fired.
    final_mp = writes.get("mp", s["mp"])
    if final_mp > s["maxmp"]:
        writes["mp"] = s["maxmp"]

    # Display values converge after source MP work, exactly one point/tick.
    health = s["health"]
    oldhealth = s["oldhealth"]
    if oldhealth < health:
        writes["oldhealth"] = oldhealth + 1
    elif oldhealth > health:
        writes["oldhealth"] = oldhealth - 1
    mp = writes.get("mp", s["mp"])
    oldmp = s["oldmp"]
    if oldmp < mp:
        writes["oldmp"] = oldmp + 1
    elif oldmp > mp:
        writes["oldmp"] = oldmp - 1

    # Commit only after every branch and domain check completed.
    for field, value in writes.items():
        row[field] = value
    return HealthResult("complete", tuple(sorted(writes)))


def authored_model_inputs(source, identity: str = "He_Man") -> dict:
    """Read the actor's authored cached fields; expose engine defaults apart.

    Model data files do not author update_health's per-instance timers or
    rates. Those defaults are reported with the pinned loader provenance.
    """
    from source_model_core_4086 import derive as derive_core
    from source_profile import discover, document
    from compiler import key

    docs = {k: document(source, name) for k, (name, _) in source.index.items()
            if k.endswith(".txt")}
    structure = discover(source, docs)
    model = next((m for m in structure["models"]
                  if m["declaration"].lower() == identity.lower()), None)
    if model is None:
        raise ValueError("HEALTH_MODEL_NOT_FOUND:" + identity)
    fields = derive_core(source)["models"][model["registry_order"]]["fields"]
    source_doc = docs[key(model["source_path"])]
    directives = {r["directive"]: r["values"] for r in source_doc["directives"]}
    if "health" not in directives:
        raise ValueError("HEALTH_MODEL_HEALTH_UNAUTHORED")
    return {
        "identity": model["declaration"],
        "model_id": model["registry_order"],
        "source_path": model["source_path"],
        "source_sha256": source_doc["sha256"],
        "authored_health": fields["health"],
        "authored_maxmp": fields["mp"],
        "authored_guard_max": int(directives.get("guardpoints", ["0"])[0]),
        "loader_defaults": {
            "magic_type": 0, "mpstable": 0, "mpstableval": 0,
            "mprate": 2, "mpdroprate": 0, "chargerate": 2,
            "guardrate": 2, "guard_current_equals_max": True,
            "mpswitch": -1,
        },
        "loader_default_evidence": "pinned update_model/init_model: newchar mprate=2 except magic_type==1; chargerate=guardrate=2; guardpoints zero; mpswitch=-1",
    }


def emit_normal_zero_mp(work: int, symbols: dict, expected_generation: int = 1,
                        charging_address: int | None = None,
                        model_id: int = 3) -> str:
    """Emit the bounded single-player He_Man normal health leaf.

    The work row and compiled model profile are intentionally narrow: physical
    slot zero, authored guard/max-MP zero, normal magic type, stable mode zero,
    default MP rate two. Other slots, DOT and charging remain pending. All
    actor writes are staged in DP scratch until ownership, timers and arithmetic
    validate. `charging_address` is the caller-resolved canonical live flag.
    """
    if type(work) is not int or not 0 <= work <= 0x1000000 - 128:
        raise ValueError("LIVE_HEALTH_WORK_ADDRESS")
    if type(expected_generation) is not int or not 1 <= expected_generation <= 0xFFFF:
        raise ValueError("LIVE_HEALTH_GENERATION")
    if type(charging_address) is not int or not 0 <= charging_address <= 0xFFFFFF:
        raise ValueError("LIVE_HEALTH_CHARGING_ADDRESS_REQUIRED")
    if type(model_id) is not int or not 0 <= model_id <= 15:
        raise ValueError("LIVE_HEALTH_MODEL_ID")
    required = (
        "SourceForeignWork_Check", "SourceForeignWork_Generation",
        "SourceWorldTick4086_Ready", "SourceWorldTick4086_State",
        "SourceWorldTick4086_Phase", "SourceWorldTick4086_Pending",
        "SourceWorldTick4086_Fault", "SourceWorldTick4086_TimeLo",
        "SourceWorldTick4086_Slot",
        "VmSourceWorld_Ready", "VmSourceWorld_Count", "VmSourceWorld_Time",
        "SourceLifecycle4086_Ready",
    )
    for name in required:
        if name not in symbols:
            raise ValueError("LIVE_HEALTH_SYMBOL_" + name)

    lines: list[str] = []
    serial = 0

    def put(text: str) -> None:
        lines.extend(text.strip().splitlines())

    def label(name: str) -> None:
        put(f"LiveHealth_{name}:\n.a16\n.i16")

    def branch(op: str, target: str = "Fault") -> None:
        nonlocal serial
        serial += 1
        gate = f"LiveHealth_Guard{serial}"
        inverse = {"beq": "bne", "bne": "beq", "bcc": "bcs",
                   "bcs": "bcc", "bmi": "bpl", "bpl": "bmi",
                   "bvc": "bvs", "bvs": "bvc"}[op]
        put(f" {inverse} {gate}\n jmp LiveHealth_{target}\n{gate}:\n.a16\n.i16")

    def require(address: str | int, value: int) -> None:
        put(f" lda.l {address}\n cmp #${value:04X}")
        branch("bne")

    def cmp_ne(left: str, right: str) -> None:
        put(f" lda.l {left}\n cmp.l {right}")
        branch("bne")

    label("Run")
    put(""" php
    phb
    phd
    rep #$39
    phx
    phy
    tsc
    sec
    sbc #64
    tcs
    inc a
    tcd
    stx $2C
    sty $2E""")
    put(f" jsl {symbols['SourceForeignWork_Check']}")
    branch("bcs")
    require(work, 0xB6D1)
    put(f" lda.l {work}+4\n cmp #${expected_generation:04X}")
    branch("bne")
    require(work + 6, 0)
    put(f" lda.l {symbols['SourceForeignWork_Generation']}\n cmp.l {work}+4")
    branch("bne")
    put(f" lda.l {symbols['SourceForeignWork_Generation']}+2\n cmp.l {work}+6")
    branch("bne")
    put(f" lda.l {work}+12")
    branch("beq", "ProfileOK")
    put(" jmp LiveHealth_Pending")
    label("ProfileOK")
    require(work + 14, 0)
    require(symbols["SourceWorldTick4086_Ready"], 0xB4D5)
    require(symbols["SourceWorldTick4086_State"], 1)
    require(symbols["SourceWorldTick4086_Phase"], 9)
    require(symbols["SourceWorldTick4086_Pending"], 1)
    require(symbols["SourceWorldTick4086_Fault"], 0)
    require(symbols["VmSourceWorld_Ready"], 0xB4A3)
    put(f" lda.l {symbols['VmSourceWorld_Count']}\n cmp #1")
    branch("bcc", "Pending")
    put(f" lda.l {symbols['SourceWorldTick4086_Slot']}\n cmp #0")
    branch("bne", "Pending")
    for off in (0, 2):
        put(f" lda.l {symbols['SourceWorldTick4086_TimeLo']}+{off}\n cmp.l {symbols['VmSourceWorld_Time']}+{off}")
        branch("bne")
    require(symbols["SourceLifecycle4086_Ready"], 0xB4FB)
    require("$439048", model_id)
    require("$43904A", 0xB4FB)
    # Slot zero must still refer to the exact entity token captured by the
    # caller-owned row. The 41-bank tag is checked independently.
    cmp_ne("$414000", f"{work}+8")
    cmp_ne("$414002", f"{work}+10")
    require("$414002", 0x41)
    put(f" lda.l $416800\n cmp #{model_id}")
    branch("bne", "Pending")
    # Fixed actor profile is He_Man (profile ID zero), whose compiled model
    # data has max MP=0, guard max=0, stable mode=0, magic type=0, rate=2.
    require("$40C040", 0)
    require("$40C042", 0)
    # Active common_dot has no leaf yet and must leave all stores untouched.
    put(f" lda.l {work}+24\n ora.l {work}+26")
    branch("bne", "Pending")
    put(f" lda.l {charging_address}\n ora.l {charging_address + 2}")
    branch("bne", "Pending")

    # Snapshot actor inputs into DP locals. Signed MP addition by two is
    # checked for int32 overflow before any source row is changed.
    for address, low, high in (("$414024", 0, 2), ("$40C04C", 8, 10),
                               (symbols["SourceWorldTick4086_TimeLo"], 16, 18),
                               ("$42E010", 20, 22), (work + 16, 24, 26),
                               (work + 20, 28, 30)):
        put(f" lda.l {address}\n sta ${low:02X}\n lda.l {address}+2\n sta ${high:02X}")
    put(" stz $22")

    # Unsigned `time >= magictime`, matching C's unsigned timer fields.
    put(" lda $12\n cmp $16")
    branch("bcc", "SkipRegen")
    branch("bne", "Regen")
    put(" lda $10\n cmp $14")
    branch("bcc", "SkipRegen")
    label("Regen")
    put(" lda #1\n sta $22")
    put(" lda $08\n clc\n adc #2\n sta $08\n lda $0A\n adc #0\n sta $0A")
    branch("bvs")
    # Maximum MP is authored zero; positive result is clamped to zero.
    put(" lda $0A\n bmi LiveHealth_MpReady\n bne LiveHealth_MpZero\n lda $08\n beq LiveHealth_MpReady")
    label("MpZero")
    put(" lda #0\n sta $08\n sta $0A")
    label("MpReady")
    # Reset magictime to unsigned now + GAME_SPEED(200), with wrap.
    put(" lda $10\n clc\n adc #200\n sta $14\n lda $12\n adc #0\n sta $16")
    label("SkipRegen")
    # Unconditional source MP ceiling applies even when the regen timer is
    # not due. He_Man max MP is zero.
    put(" lda $0A\n bmi LiveHealth_MpCapped\n bne LiveHealth_CapMp\n lda $08\n beq LiveHealth_MpCapped")
    label("CapMp")
    put(" lda #0\n sta $08\n sta $0A")
    label("MpCapped")
    # oldhealth moves one point toward source health.
    put(" lda $1A\n eor #$8000\n sta $20\n lda $02\n eor #$8000\n cmp $20")
    branch("bcc", "HealthDown")
    branch("bne", "HealthUp")
    put(" lda $00\n cmp $18")
    branch("bcc", "HealthDown")
    branch("bne", "HealthUp")
    put(" jmp LiveHealth_HealthSame")
    label("HealthUp")
    put(" lda $18\n inc a\n sta $18\n bne LiveHealth_HealthSame\n lda $1A\n inc a\n sta $1A\n jmp LiveHealth_HealthSame")
    label("HealthDown")
    put(" lda $18\n bne LiveHealth_HealthDownLow\n lda $1A\n dec a\n sta $1A")
    label("HealthDownLow")
    put(" lda $18\n dec a\n sta $18")
    label("HealthSame")
    # oldmp moves one point toward final capped MP.
    put(" lda $1E\n eor #$8000\n sta $20\n lda $0A\n eor #$8000\n cmp $20")
    branch("bcc", "MpDown")
    branch("bne", "MpUp")
    put(" lda $08\n cmp $1C")
    branch("bcc", "MpDown")
    branch("bne", "MpUp")
    put(" jmp LiveHealth_Commit")
    label("MpUp")
    put(" lda $1C\n inc a\n sta $1C\n bne LiveHealth_Commit\n lda $1E\n inc a\n sta $1E\n jmp LiveHealth_Commit")
    label("MpDown")
    put(" lda $1C\n bne LiveHealth_MpDownLow\n lda $1E\n dec a\n sta $1E")
    label("MpDownLow")
    put(" lda $1C\n dec a\n sta $1C")

    # One commit point: canonical MP plus the two displayed convergence words
    # in the extension record. Health is read-only in this leaf.
    label("Commit")
    for source, target in ((8, "$40C04C"), (24, work + 16),
                           (28, work + 20)):
        put(f" lda ${source:02X}\n sta.l {target}\n lda ${source+2:02X}\n sta.l {target}+2")
    put(" lda $22\n beq LiveHealth_Complete\n lda $14\n sta.l $42E010\n lda $16\n sta.l $42E012")
    put(" jmp LiveHealth_Complete")
    label("Pending")
    put(" lda #1\n jmp LiveHealth_ReturnGood")
    label("Complete")
    put(" lda #0")
    label("ReturnGood")
    put(" tay\n tsc\n clc\n adc #64\n tcs\n tya\n ply\n plx\n pld\n plb\n plp\n clc\n rtl")
    label("Fault")
    put(" lda #0\n tsc\n clc\n adc #64\n tcs\n ply\n plx\n pld\n plb\n lda #0\n plp\n sec\n rtl")
    text = "\n".join(lines) + "\n"
    for name in required + ("SourceWorldTick4086_Slot",):
        text = text.replace(name, str(symbols[name]))
    return text


def bootstrap_row(*, health: int, mp: int, maxmp: int, now: int = 0,
                  guard_max: int = 0, guardrate: int = 2) -> dict[str, int]:
    """Explicit reset defaults; caller must seed authored model parameters."""
    row = dict.fromkeys(ROW_FIELDS, 0)
    row.update(health=health, oldhealth=health, mp=mp, oldmp=mp, maxmp=maxmp,
               mprate=2, mpdroprate=0, chargerate=2, guard_max=guard_max,
               guard_current=guard_max, guardrate=guardrate, mpswitch=-1,
               magictime=now, mpchargetime=now, guardtime=now)
    return row
