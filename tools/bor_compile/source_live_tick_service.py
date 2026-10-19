"""Callable real 4086 tick service for the one-player live-world owner.

The service is deliberately a *single call* boundary: it observes a fresh
hardware sample only when no clock debt exists, resumes an already-open source
world tick without refreshing its immutable input sample, and commits at most
one completed source tick.  The caller owns the WORK row and the canonical
foreign input-snapshot arena row.

WORK ABI (all 16-bit little-endian words):
  +00 owner tag B6D0; +02 owner state (1 running, 2 provider-pending, 3 sticky
  fault); +04/+06 generation dword (currently exactly 1); +08/+0A committed
  tick count; +0C last pending dispatcher phase (0 when none); +0E caller
  status; +10 reserved;
  +16 reentry/busy word (0 idle, 1 active); +18 service result; +20 service
  fault flag; +22 reserved.  Root must clear +16..+22 at bootstrap.

Entry preserves X/Y/DP/DBR/P and stack depth.  It establishes DBR=DP=0 for all
calls.  A returns 0=no due, 1=actual provider pending, 2=one committed and
sealed tick; carry alone indicates sticky fault.  Only the work row, input
snapshot, and latest snapshot are directly written here.  Source providers
retain their own documented writes.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

WORK_DEFAULT = 0x7E7700
LATEST_DEFAULT = 0x7E7800
OWNER_MAGIC = 0xB6D0
GENERATION = 1
ACTOR = 0x414000
ACTOR_BYTES = 80
SIDE = 0x416800
SIDE_BYTES = 64


def _address(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFF:
        raise ValueError("LIVE_TICK_ADDRESS:" + name)
    return value


def _target(value, name):
    """Format a far-call target supplied as a linked address or local label."""
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 0xFFFFFF:
        return f"${value:06X}"
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z_]\w*", value):
        return value
    raise ValueError("LIVE_TICK_PLAYER_SYMBOL:" + name)


def emit(symbols, player_symbols, work=WORK_DEFAULT, latest=LATEST_DEFAULT):
    """Emit a standalone local-label routine named ``LiveTick_Service``.

    ``symbols`` supplies actual assembled symbol addresses for the source
    clock, source world tick, input controller, and input snapshot source.
    ``player_symbols`` supplies the emitted ``PlayerHistory_Refresh`` entry;
    the canonical 6400-byte foreign arena layout supplies input_snapshot.
    The world dispatcher is intentionally a local link-time label
    ``LiveWorldDispatch_Run``.
    """
    if not isinstance(symbols, Mapping) or not isinstance(player_symbols, Mapping):
        raise ValueError("LIVE_TICK_SYMBOL_MAP")
    work = _address(work, "work")
    latest = _address(latest, "latest")
    if work + 24 > 0x1000000 or latest + 148 > 0x1000000:
        raise ValueError("LIVE_TICK_ROW_EXTENT")
    if work < latest + 148 and latest < work + 24:
        raise ValueError("LIVE_TICK_ROW_OVERLAP")
    for owned_lo, owned_hi in ((work, work + 24), (latest, latest + 148)):
        for source_lo, source_hi in ((ACTOR, ACTOR + ACTOR_BYTES),
                                     (SIDE, SIDE + SIDE_BYTES),
                                     (0x7FA000, 0x7FA000 + 6400)):
            if owned_lo < source_hi and source_lo < owned_hi:
                raise ValueError("LIVE_TICK_ROWS_OVERLAP_SOURCE")
    required = (
        "SourceClock4086_Ready", "SourceClock4086_Due",
        "SourceClock4086_TimeLo", "SourceClock4086_TimeHi", "SourceClock4086_Observe",
        "SourceWorldTick4086_Ready", "SourceWorldTick4086_State",
        "SourceWorldTick4086_Pending", "SourceWorldTick4086_Begin",
        "SourceWorldTick4086_Commit", "SourceInputController_Refresh",
        "VmSourceInput_Ready",
    )
    for name in required:
        if name not in symbols:
            raise ValueError("LIVE_TICK_SYMBOL:" + name)
        _address(symbols[name], name)
    if "PlayerHistory_Refresh" not in player_symbols:
        raise ValueError("LIVE_TICK_PLAYER_SYMBOL:PlayerHistory_Refresh")
    history = _target(player_symbols["PlayerHistory_Refresh"], "PlayerHistory_Refresh")
    from source_foreign_state_layout import layout
    regions = {r["name"]: r for r in layout(0x7FA000, 6400)["regions"]}
    input_snapshot = regions["input_snapshot"]["address"]
    if "input_snapshot" in player_symbols and player_symbols["input_snapshot"] != input_snapshot:
        raise ValueError("LIVE_TICK_NONCANONICAL_INPUT_SNAPSHOT")

    # All conditionals are relaxed through an inverse short branch plus JMP;
    # the service remains placement-independent in bank 48/other callers.
    lines = ["LiveTick_Service:", ".a16", ".i16",
             " php", " rep #$38", " phx", " phy", " phb", " phd",
             " sep #$20", ".a8", " lda #0", " pha", " plb",
             " rep #$20", ".a16", " lda #0", " tcd"]

    def put(*items): lines.extend(items)
    def label(name): put(name + ":", ".a16", ".i16")
    def branch(op, target): put(f" {op} {target}")

    # A reentrant call cannot borrow/overwrite the outer call's result slots.
    put(f" lda.l ${work + 16:06X}"); branch("bne", "LiveTick_Reentry")
    put(f" lda.l ${work:06X}"); put(f" cmp #${OWNER_MAGIC:04X}"); branch("bne", "LiveTick_Unowned")
    put(f" lda.l ${work + 2:06X}"); put(" cmp #3"); branch("beq", "LiveTick_Sticky")
    put(" cmp #1"); branch("beq", "LiveTick_OwnerStateGood")
    put(" cmp #2"); branch("bne", "LiveTick_OwnerFault")
    label("LiveTick_OwnerStateGood")
    put(f" lda.l ${work + 4:06X}"); put(f" cmp #${GENERATION:04X}"); branch("bne", "LiveTick_OwnerFault")
    put(f" lda.l ${work + 6:06X}"); put(" cmp #0"); branch("bne", "LiveTick_OwnerFault")
    put(f" lda.l ${symbols['SourceClock4086_Ready']:06X}"); put(" cmp #$B4C5"); branch("bne", "LiveTick_OwnerFault")
    put(f" lda.l ${symbols['SourceWorldTick4086_Ready']:06X}"); put(" cmp #$B4D5"); branch("bne", "LiveTick_OwnerFault")
    put(f" lda.l ${symbols['SourceWorldTick4086_Pending']:06X}")
    # Pending may only be 0/1. The owner’s state 1..4 is authoritative for
    # whether Begin has already happened; pending is checked by dispatcher.
    put(" cmp #2"); branch("bcs", "LiveTick_OwnerFault")
    put(f" lda.l ${work + 16:06X}"); put(" cmp #0"); branch("bne", "LiveTick_Reentry")
    put(" lda #1"); put(f" sta.l ${work + 16:06X}")
    put(f" lda.l ${symbols['SourceWorldTick4086_State']:06X}")
    put(" cmp #0"); branch("beq", "LiveTick_Idle")
    put(" cmp #5"); branch("bcs", "LiveTick_FaultOwned")
    put(f" lda.l ${work + 2:06X}"); put(" cmp #2"); branch("bne", "LiveTick_FaultOwned")
    put(f" lda.l ${symbols['SourceClock4086_Due']:06X}")
    put(" cmp #0"); branch("beq", "LiveTick_FaultOwned")
    put(" jmp LiveTick_Dispatch")

    label("LiveTick_Idle")
    put(f" lda.l ${work + 2:06X}"); put(" cmp #1"); branch("bne", "LiveTick_FaultOwned")
    put(f" lda.l ${symbols['SourceWorldTick4086_Pending']:06X}")
    put(" cmp #0"); branch("bne", "LiveTick_FaultOwned")
    put(f" lda.l ${symbols['SourceClock4086_Due']:06X}")
    put(" cmp #0"); branch("bne", "LiveTick_CatchUp")
    # Only the prior-Due==0 path observes a fresh physical sample.
    put(" lda #1", f" jsl ${symbols['SourceClock4086_Observe']:06X}")
    branch("bcs", "LiveTick_FaultOwned")
    put(" cmp #0"); branch("beq", "LiveTick_NoDue")
    put(f" lda.l ${symbols['SourceClock4086_TimeLo']:06X}"); put(" tax")
    put(f" lda.l ${symbols['SourceClock4086_TimeHi']:06X}"); put(" tay")
    put(" lda #1", f" jsl ${symbols['SourceInputController_Refresh']:06X}")
    branch("bcs", "LiveTick_FaultOwned")
    put(" ldx #0")
    label("LiveTick_CopyInput")
    put(f" lda.l ${symbols['VmSourceInput_Ready']:06X},x")
    put(f" sta.l ${input_snapshot:06X},x")
    put(" inx", " inx", " cpx #20"); branch("bcc", "LiveTick_CopyInput")
    put(f" jsl {history}"); branch("bcs", "LiveTick_FaultOwned")
    label("LiveTick_CatchUp")
    put(f" jsl ${symbols['SourceWorldTick4086_Begin']:06X}"); branch("bcs", "LiveTick_FaultOwned")

    label("LiveTick_Dispatch")
    put(f" lda.l ${work + 4:06X}", " tax",
        f" lda.l ${work + 6:06X}", " tay",
        " jsl LiveWorldDispatch_Run")
    branch("bcs", "LiveTick_FaultOwned")
    put(" cmp #0"); branch("beq", "LiveTick_Commit")
    # Dispatcher returns the real outstanding service phase (1..12).
    put(f" sta.l ${work + 12:06X}")
    put(" lda #2", f" sta.l ${work + 2:06X}")
    put(" lda #1", f" sta.l ${work + 18:06X}")
    put(" lda #0", f" sta.l ${work + 20:06X}")
    put(" jmp LiveTick_ReturnGood")

    label("LiveTick_Commit")
    put(f" jsl ${symbols['SourceWorldTick4086_Commit']:06X}"); branch("bcs", "LiveTick_FaultOwned")
    # Exactly one increment, after the source Commit has committed clock time.
    put(f" lda.l ${work + 8:06X}"); put(" inc a", f" sta.l ${work + 8:06X}")
    branch("bne", "LiveTick_CopyRows")
    put(f" lda.l ${work + 10:06X}"); put(" inc a", f" sta.l ${work + 10:06X}")
    label("LiveTick_CopyRows")
    put(" ldx #0")
    label("LiveTick_CopyActor")
    put(f" lda.l ${ACTOR:06X},x", f" sta.l ${latest:06X},x")
    put(" inx", " inx", f" cpx #{ACTOR_BYTES}"); branch("bcc", "LiveTick_CopyActor")
    put(" ldx #0")
    label("LiveTick_CopySide")
    put(f" lda.l ${SIDE:06X},x", f" sta.l ${latest + ACTOR_BYTES:06X},x")
    put(" inx", " inx", f" cpx #{SIDE_BYTES}"); branch("bcc", "LiveTick_CopySide")
    put(f" lda.l ${work + 8:06X}", f" sta.l ${latest + 144:06X}")
    put(f" lda.l ${work + 10:06X}", f" sta.l ${latest + 146:06X}")
    put(" lda #0", f" sta.l ${work + 12:06X}")
    put(" lda #1", f" sta.l ${work + 2:06X}")
    put(" lda #2", f" sta.l ${work + 18:06X}")
    put(" lda #0", f" sta.l ${work + 20:06X}")
    label("LiveTick_SealComplete")
    put(" jmp LiveTick_ReturnGood")

    label("LiveTick_NoDue")
    put(" lda #0", f" sta.l ${work + 18:06X}", f" sta.l ${work + 20:06X}")
    put(" jmp LiveTick_ReturnGood")

    label("LiveTick_FaultOwned")
    put(" lda #3", f" sta.l ${work + 2:06X}")
    put(" lda #0", f" sta.l ${work + 18:06X}")
    put(" lda #1", f" sta.l ${work + 20:06X}")
    put(" jmp LiveTick_ReturnFault")
    label("LiveTick_OwnerFault")
    put(" lda #3", f" sta.l ${work + 2:06X}")
    put(" lda #0", f" sta.l ${work + 18:06X}")
    put(" lda #1", f" sta.l ${work + 20:06X}")
    put(" jmp LiveTick_ReturnFault")
    label("LiveTick_Sticky")
    put(" lda #0", f" sta.l ${work + 18:06X}", f" sta.l ${work + 20:06X}")
    put(" jmp LiveTick_ReturnFault")
    label("LiveTick_Unowned")
    # No trust in an unowned row: return directly without writing it.
    put(" jmp LiveTick_Reentry")
    label("LiveTick_Reentry")
    put(" lda #0")
    put(" jmp LiveTick_ReturnFaultUnowned")

    label("LiveTick_ReturnGood")
    put(f" lda #0", f" sta.l ${work + 16:06X}")
    put(f" lda.l ${work + 18:06X}")
    # Pull the saved execution context before restoring the caller's P.  The
    # data-load flags are then discarded; only the declared carry is changed.
    put(" pld", " plb", " ply", " plx", " plp", " clc", " rtl")
    label("LiveTick_ReturnFault")
    put(f" lda #0", f" sta.l ${work + 16:06X}", " lda.l " + f"${work + 18:06X}",
        " pld", " plb", " ply", " plx", " plp", " sec", " rtl")
    label("LiveTick_ReturnFaultUnowned")
    put(" pld", " plb", " ply", " plx", " plp", " sec", " rtl")

    # Expand short conditionals defensively; absolute JMPs avoid code-placement
    # dependent 8-bit branch ranges.
    inv = {"beq": "bne", "bne": "beq", "bcs": "bcc", "bcc": "bcs"}
    out = []
    serial = 0
    for line in lines:
        m = re.fullmatch(r" (beq|bne|bcs|bcc) (LiveTick_\w+)", line)
        if not m:
            out.append(line)
            continue
        serial += 1
        skip = f"LiveTick_BranchSkip{serial}"
        out.extend((f" {inv[m.group(1)]} {skip}", f" jmp {m.group(2)}",
                    skip + ":", ".a16", ".i16"))
    return "\n".join(out) + "\n"
